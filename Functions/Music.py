import nextcord
from nextcord import Interaction,ui,ButtonStyle,SlashOption,Member,Activity,ActivityType,embeds,TextInputStyle
from nextcord.abc import Connectable
import random
from mafic import Player,Playlist, Track

from Functions.LogsJson import json_read,json_write,logger
#region types

class QueuedTrack:
    def __init__(self, track: Track, start_time: int = 0, end_time: int = 0, volume: int = 100):
        self.track = track
        self.start_time = start_time
        self.end_time = end_time if end_time > 0 else track.length
        self.volume = volume

class MyPlayer(Player):
    def __init__(self, client, channel: Connectable) -> None:
        super().__init__(client, channel)
        self.queue: list[QueuedTrack] = []
        self.volume: int = 100

    async def set_volume(self, volume: float):
        self.volume = max(0, min(200, volume))
        await super().set_volume(self.volume)
        logger.info(f"volume set to: {self.volume}")

    def enqueue_track(self, track: Track, start_time: int = 0, end_time: int = 0, volume: int=None):
        queued_track = QueuedTrack(track, start_time, end_time, self.volume if volume == None else volume)
        self.queue.append(queued_track)

    async def play_next_track(self,bot):
        if self.queue:
            next_track = self.queue.pop(0)
            await super().play(next_track.track, start_time=next_track.start_time, end_time=next_track.end_time, volume=next_track.volume)
            await bot.change_presence(activity=Activity(type=ActivityType.listening, name=next_track.track.title))

#endregion

#region views

class YtChoice(ui.View):
    def __init__(self, results, is_playlist=False):
        super().__init__()
        self.value = None
        self.results = results
        self.is_playlist = is_playlist

        # Unicode numbers for emojis
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

        # Dynamically create buttons based on the number of results
        for i, result in enumerate(results[:5], start=1):  # Limit to 5
            self.add_item(
                ui.Button(
                    label=f"Play {result.title[:15]}...",  # Shortened title
                    style=ButtonStyle.blurple,
                    emoji=number_emojis[i - 1],
                    custom_id=f"choice_{i}"
                )
            )

        if self.is_playlist:
            # Add "Play All" button if it's a playlist
            self.add_item(
                ui.Button(
                    label="Play All",
                    style=ButtonStyle.green,
                    emoji="🎶",
                    custom_id="choice_all"
                )
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
    # Check the `custom_id` of the button that triggered the interaction
        custom_id = interaction.data["custom_id"]

        if custom_id.startswith("choice_"):
            if custom_id == "choice_all":
                self.value = "all"
            else:
                index = int(custom_id.split("_")[1]) - 1
                self.value = index + 1
            self.stop()
            return True  # Allow the interaction
        return False  # Ignore interactions from unknown sources
    
class QueueView(ui.View):
    def __init__(self, player: MyPlayer, interaction: Interaction):
        super().__init__(timeout=60)  # The view will deactivate after 60 seconds
        self.player = player
        self.interaction = interaction
        self.message = None

    @ui.button(label="Shuffle", style=ButtonStyle.primary,emoji="🔀") #emoji=":twisted_rightwards_arrows:",
    async def shuffle_button(self, button: ui.Button, interaction: Interaction):
        random.shuffle(self.player.queue)
        await interaction.response.defer()
        await self.update_queue_display()

    async def update_queue_display(self):
        embed = create_queue_embed(self.player)
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            await self.interaction.edit_original_message(embed=embed, view=self)
    async def on_timeout(self):
        # Remove the buttons when the view times out
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

class SeekModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Seek to Time")
        self.view = view
        self.time_input = ui.TextInput(
            label="Enter time (e.g., '1:30' or '90')",
            placeholder="minutes:seconds or total seconds",
            required=True,
            style=TextInputStyle.short
        )
        self.add_item(self.time_input)

    async def callback(self, interaction: Interaction):
        time_str = self.time_input.value
        try:
            if ':' in time_str:
                seek_ms = format_millisecs(time_str)
            else:
                seek_ms = int(time_str) * 1000  # Convert seconds to milliseconds

            if seek_ms < 0 or seek_ms > self.view.player.current.length:
                await interaction.response.send_message(f"Invalid seek time. The track is {length_format(self.view.player.current.length)} long.", ephemeral=True)
                return

            await self.view.player.seek(seek_ms)
            await self.view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("Invalid time format. Please use 'minutes:seconds' or total seconds.", ephemeral=True)



class NowPlayingView(ui.View):
    def __init__(self, player: MyPlayer):
        super().__init__(timeout=300)  # The view will deactivate after 5 minutes
        self.player = player
        self.interaction: Interaction | None = None  # Store interaction for ephemeral updates
        self.update_play_pause_button()

    def update_play_pause_button(self):
        button = [x for x in self.children if x.custom_id == "play_pause"][0]
        button.emoji = "⏸️" if not self.player.paused else "▶️"

    def check_links(self, url):
        # file_path = os.path.join(os.path.dirname(__file__), 'links.json')
        # with open(file_path, 'r') as f:
        #     data = json.load(f)
        data = json_read("links")
        for _, info in data.items():
            if info["url"] == url:
                return True
        return False

    async def update_embed(self, interaction: Interaction):
        track = self.player.current
        if not track:
            return
        
        is_leave = self.check_links(track.uri)
        bar = create_progress_bar(self.player.position / track.length)
        emoji = "⏸️" if self.player.paused else "▶️"
        volume_emoji = get_volume_emoji(self.player.volume)  # Get the appropriate volume emoji

        embed = (
            nextcord.Embed(title=f"{track.title}", url=track.uri)
            if not is_leave else
            nextcord.Embed(title="[REDACTED]")
        )
        if not is_leave:
            embed.set_thumbnail(track.artwork_url)
            embed.set_footer(text=f"By: {track.author}")
        else:
            embed.set_thumbnail("https://i.ytimg.com/vi/9N_CKQ5kPkE/maxresdefault.jpg")
            embed.set_footer(text="By: █████ ███")

        if self.player.volume != 100:
            embed.description = f"{emoji}{bar}``[{length_format(self.player.position)}/{length_format(track.length)}]``{volume_emoji}{self.player.volume}%"
        else:
            embed.description = f"{emoji}{bar}``[{length_format(self.player.position)}/{length_format(track.length)}]``{volume_emoji}"

        # Handle ephemeral messaging
        if self.interaction:
            try:
                await self.interaction.edit_original_message(embed=embed, view=self)
            except nextcord.NotFound:
                # If the original interaction is expired or message is gone
                pass
        elif interaction:
            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
            self.interaction = interaction

    @ui.button(emoji="⏯️", style=ButtonStyle.primary, custom_id="play_pause")
    async def play_pause_button(self, button: ui.Button, interaction: Interaction):
        if self.player.paused:
            await self.player.resume()
            await interaction.response.defer()
        else:
            await self.player.pause()
            await interaction.response.defer()

        self.update_play_pause_button()
        await self.update_embed(interaction)

    @ui.button(emoji="⏩", style=ButtonStyle.secondary, custom_id="seek")
    async def seek_button(self, button: ui.Button, interaction: Interaction):
        seek_modal = SeekModal(self)
        await interaction.response.send_modal(seek_modal)

    @ui.button(emoji="⏭️", style=ButtonStyle.secondary)
    async def skip_button(self, button: ui.Button, interaction: Interaction):
        if self.player.queue:
            await self.player.stop()
            await interaction.response.defer()
            await self.update_embed(interaction)
        else:
            await interaction.response.send_message("No more tracks in the queue.", ephemeral=True)

    @ui.button(emoji="🔊", style=ButtonStyle.secondary)
    async def volume_button(self, button: ui.Button, interaction: Interaction):
        volume_modal = VolumeModal(self)
        await interaction.response.send_modal(volume_modal)

    async def on_timeout(self):
        # Remove the buttons when the view times out
        for item in self.children:
            item.disabled = True
        if self.interaction:
            try:
                await self.interaction.edit_original_message(view=self)
            except nextcord.NotFound:
                pass
class VolumeModal(ui.Modal):
    def __init__(self, view: NowPlayingView):
        super().__init__(title="Set Volume")
        self.view = view
        self.volume_input = ui.TextInput(
            label="Volume (0-100)",
            placeholder="Enter a number between 0 and 100",
            required=True,
            min_length=1,
            max_length=3
        )
        self.add_item(self.volume_input)

    async def callback(self, interaction: Interaction):
        try:
            volume = int(self.volume_input.value)
            volume = max(0, min(200, volume))  # Ensure volume is between 0 and 200
            await self.view.player.set_volume(volume)
            await self.view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message("Invalid volume. Please enter a number between 0 and 100.", ephemeral=True)
#endregion

#region commands   
 
async def join(
inter: Interaction, 
channel: nextcord.VoiceChannel = SlashOption(
    name="channel",
    description="The voice channel to join",
    required=False,
    default=None
)
):
    """Join a voice channel."""
    assert isinstance(inter.user, Member)

    if channel is None:
        if not inter.user.voice or not inter.user.voice.channel:
            return await inter.response.send_message("You are not in a voice channel and didn't specify a channel to join.", ephemeral=True)
        channel = inter.user.voice.channel
    
    # Check if the bot has permission to join the channel
    if not channel.permissions_for(inter.guild.me).connect:
        return await inter.response.send_message(f"I don't have permission to join {channel.mention}.", ephemeral=True)

    # This apparently **must** only be `Client`.
    await channel.connect(cls=MyPlayer)  # pyright: ignore[reportGeneralTypeIssues]
    await inter.response.send_message(f"Joined {channel.mention}.")

async def leave(inter: Interaction,bot):
    """Leave the voice channel and finish any tracks."""
    assert inter.guild is not None
    
    if not inter.guild.voice_client:
        return await inter.response.send_message("I'm not in a voice channel.", ephemeral=True)
    
    player: MyPlayer = inter.guild.voice_client  # pyright: ignore[reportGeneralTypeIssues]
    
    # Stop the current track if it's playing
    if player.current:
        await player.stop()
    
    # Clear the queue
    player.queue.clear()
    
    # Disconnect from the voice channel
    await player.disconnect()
    
    # Clear the bot's presence
    await bot.change_presence(activity=None,status=None)
    
    # Send a confirmation message
    await inter.response.send_message("Bye tamut.")

    # If the bot is still in the voice channel for some reason, force it to leave
    if inter.guild.voice_client:
        await inter.guild.voice_client.disconnect(force=True)

async def skip(inter: Interaction):
    """Skip the current song."""
    assert inter.guild is not None
    if not inter.guild.voice_client:
        return await inter.send("I am not playing anything.")
    
    player: MyPlayer = inter.guild.voice_client  # pyright: ignore[reportGeneralTypeIssues]
    
    if not player.current:
        return await inter.send("There's no track currently playing.")
    if len(player.queue) > 0:
        await inter.send(f"Skipped! Now playing: [{player.queue[0].track.title}]({player.queue[0].track.uri})")
    else:
        await inter.send(f"Skipped! Nothing more to play, goodbye")
    # Skip the current track
    await player.stop()
    logger.info("skipped track.")

async def queue(inter: Interaction):
    """Get a list of the current queue"""
    player: MyPlayer = inter.guild.voice_client  # pyright: ignore[reportGeneralTypeIssues]
    
    if player is None or not player.queue:
        return await inter.send("No tracks in queue.", ephemeral=True)
    
    embed = create_queue_embed(player)
    view = QueueView(player, inter)
    await inter.send(embed=embed, view=view, ephemeral=True)
    view.message = await inter.original_message()

async def direct_play(
    inter: Interaction, 
    query: str, 
    bot,
    start: str = SlashOption(description="Start time formated as HH:MM:SS", required=False, default=None),
    end: str = SlashOption(description="End time formated as HH:MM:SS", required=False, default=None)
    
):
    """Play a song with optional start and end times.

    Parameters
    ----------
    inter : Interaction[Bot]
        The interaction object
    query : str
        The song to search or play
    start : int, optional
        Start time in seconds, by default 0
    end : int, optional
        End time in seconds, by default 0 (play until the end)
    """
    assert inter.guild is not None

    if not inter.guild.voice_client:
        await join(inter,None)

    player: MyPlayer = inter.guild.voice_client  # pyright: ignore[reportGeneralTypeIssues]
    if player == None:
        return 
    tracks = await player.fetch_tracks(query)

    if not tracks:
        return await inter.send("No tracks found.")
    
    response = ""
    if isinstance(tracks, Playlist):
        totalms = sum(qtrack.length for qtrack in tracks.tracks)
        response = f"Adding Playlist: {tracks.name} (Length: {length_format(totalms)})\n"
        tracks = tracks.tracks
        if len(tracks) > 1:
            player.queue.extend(QueuedTrack(t) for t in tracks[1:])

    track = tracks[0]

    # Convert start and end times to milliseconds
    start_ms = format_millisecs(start) if start != None else None
    end_ms = format_millisecs(end) if end != None else None

    if player.current:
        player.enqueue_track(track,start_ms,end_ms)
        response += f"Added to queue: [{track.title}]({track.uri}) (Length: {length_format(track.length)})"
        logger.info(f"Directly added to queue: {track.uri}")
    else:
        await player.play(track,start_time=start_ms,end_time=end_ms,volume=player.volume)
        await inter.guild.change_voice_state(channel=inter.user.voice.channel,self_mute=False, self_deaf=True)
        response += f"Now playing: [{track.title}]({track.uri}) (Length: {length_format(track.length)})"
        logger.info(f"Now directly playing: {track.uri}")
        await bot.change_presence(activity=Activity(type=ActivityType.listening, name=track.title))

    if start_ms and start_ms > 0:
        response += f" starting from {length_format(start_ms)}"
    if end_ms and end_ms > 0:
        response += f" ending at {length_format(end_ms)}"

    await inter.send(response)

async def play(interaction: Interaction, *, query: str,bot):
    assert interaction.guild is not None

    if not interaction.guild.voice_client:
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        try:
            await interaction.user.voice.channel.connect(cls=MyPlayer)
        except Exception as e:
            return await interaction.response.send_message(f"Failed to join voice channel: {str(e)}", ephemeral=True)

    player: MyPlayer = interaction.guild.voice_client

    await interaction.response.defer(ephemeral=True, with_message="Searching for your song/playlist on YouTube...")

    try:
        results = await player.fetch_tracks(query)
    except Exception as e:
        await interaction.followup.send(f"Error loading track: {str(e)}", ephemeral=True)
        await player.disconnect()
        return

    if not results:
        return await interaction.followup.send("No results found.", ephemeral=True)

    # results = results if isinstance(results, list) else results.tracks
    
    if isinstance(results,Playlist):
        plist = results
        results = results.tracks
        totalms = sum(qtrack.length for qtrack in plist.tracks)
        is_playlist=True
    else:
        results = results[:5]   
        is_playlist=False  
    # is_playlist = hasattr(results[0], "tracks")  # Check if the result is a playlist
    # results = results[:5] if not is_playlist else results[0].tracks[:5]  # Limit playlist results

    embed = embeds.Embed(title=f"Search results for `{query}`")
    if is_playlist:
        embed.description = f"Playlist: {plist.name} ({len(results)} tracks)({length_format(totalms)})"
    # else:
    for i, result in enumerate(results[:5], start=1):
        embed.add_field(
            name=f"{i}. {result.title}",
            value=f"By [{result.author}]({result.uri})",
            inline=False,
        )

    view = YtChoice(results, is_playlist=is_playlist)
    message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    await view.wait()
    await message.edit(view=None)

    if view.value is None:
        return await interaction.followup.send("Search timed out.", ephemeral=True)
    
    if not interaction.guild.voice_client:
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        try:
            await interaction.user.voice.channel.connect(cls=MyPlayer)
        except Exception as e:
            return await interaction.response.send_message(f"Failed to join voice channel: {str(e)}", ephemeral=True)
        player: MyPlayer = interaction.guild.voice_client
        
    response = ""

    if view.value == "all":  # Play all tracks in the playlist
        if len(results) > 1:
            player.queue.extend(QueuedTrack(t) for t in results[1:])
        
        response = f"Added {len(results)} tracks to the queue from {plist.name}! For a total of {length_format(totalms)}\n"
        logger.info(f"Added playlist {plist.name}")
        selected_track = results[0]
    else:  # Play a specific track
        selected_track = results[view.value - 1]

    if player.current:
        player.enqueue_track(selected_track)
        response += f"Added to queue: [{selected_track.title}]({selected_track.uri}) (Length: {length_format(selected_track.length)})"
        logger.info(f"enqued {selected_track.uri}")
    else:
        await player.play(selected_track)
        response += f"Now playing: [{selected_track.title}]({selected_track.uri}) (Length: {length_format(selected_track.length)})"
        logger.info(f"Now playing: {selected_track.uri}")
        await bot.change_presence(activity=Activity(type=ActivityType.listening, name=selected_track.title))

    await interaction.followup.send(response)

async def now_playing(inter: Interaction):
    """Display information about the currently playing track."""
    assert inter.guild is not None

    if not inter.guild.voice_client:
        return await inter.send("I'm not connected to a voice channel.", ephemeral=True)

    player: MyPlayer = inter.guild.voice_client  # pyright: ignore[reportGeneralTypeIssues]

    if not player.current:
        return await inter.send("No track is currently playing.", ephemeral=True)

    view = NowPlayingView(player)
    await view.update_embed(inter)
    logger.info("Opened now playing view")

#endregion

#region functions

def create_queue_embed(player: MyPlayer) -> nextcord.Embed:
    lis = player.queue
    totalms = sum(qtrack.track.length for qtrack in lis)
    from SigmaBot import leave_users_links

    
    leave_users_urls = {info["url"] for info in leave_users_links.values()}
    
    tracks = []
    for i, t in enumerate(lis[:10], start=1):
        tr = t.track
        title = "REDACTED" if tr.uri in leave_users_urls else f"[{tr.title}]({tr.uri}) by {tr.author}"
        tracks.append(f"**{i}.** {title}")
    
    queue_info = "\n".join(tracks)
    total_info = f"\n**Total Track amount: {len(lis)}, and a total playtime of {length_format(totalms)}.**"
    
    return nextcord.Embed(title="Current Queue", description=queue_info + total_info)

def length_format(milli: int):
    """gets amount of miliseconds and writes them in a user format i.e '1:23:45'"""
    secs = int(milli / 1000)
    minutes = int(secs / 60)
    secs = secs % 60
    hour = int(minutes / 60)
    minutes = minutes % 60
    stri = ''
    if hour > 0:
        stri = str(hour) + ":"
    if minutes > 9:
        stri = stri + str(minutes)
    else:
        stri = stri + "0" + str(minutes)
    if secs > 9:
        stri = stri + ":" + str(secs)
    else:
        stri = stri + ":0" + str(secs)
    #  stri=stri+str(minutes)+":"+str(secs)
    return stri

def format_millisecs(time_obj: str):
    """reads a user time format and converts it into an amount of miliseconds"""
    time_obj = time_obj.split(":")
    time_obj.reverse()
    milisecs = int(time_obj[0]) * 1000
    if len(time_obj) > 1:
        milisecs += int(time_obj[1]) * 60000
    if len(time_obj) > 2:
        milisecs += int(time_obj[2]) * 3600000
    return milisecs

def get_volume_emoji(volume: float) -> str:
    if volume == 0:
        return "🔇"  # muted
    elif volume < 33:
        return "🔈"  # low volume
    elif volume < 67:
        return "🔉"  # medium volume
    elif volume <=100:
        return "🔊"  # high volume
    else:
        return ":ear_with_hearing_aid:" #hearing aid
    
def create_progress_bar(progress: float, length: int = 16) -> str:
    """
    Create a progress bar string.

    Parameters:
    progress (float): A value between 0 and 1 representing the progress.
    length (int): The total length of the progress bar. Default is 20.

    Returns:
    str: A string representing the progress bar.
    """
    if not 0 <= progress <= 1:
        raise ValueError("Progress must be between 0 and 1")

    # Calculate the position of the progress indicator
    position = int(progress * length)

    # Create the progress bar
    bar = "▬" * length
    
    # Replace the character at the calculated position with the progress indicator
    if position > 0:
        bar = bar[:position-1] + ":radio_button:" + bar[position:]
    else:
        bar = ":radio_button:" + bar[1:]

    return bar

#endregion
    