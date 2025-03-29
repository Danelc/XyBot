
import asyncio
import datetime
import logging,logging.handlers
import json,typing

import traceback
from os import getenv
import os
from typing import Any

from dotenv import load_dotenv, find_dotenv

import nextcord
from nextcord import Intents, Interaction,SlashOption,Forbidden
from nextcord.ext import commands,tasks,application_checks
from mafic import NodePool, TrackEndEvent

import Functions.Music as Music,Functions.Feeds as Feeds,Functions.Events as Events,Functions.Search as Search,Functions.Roulette as Roulette, Functions.Schedule as Schedule
from Functions.Music import MyPlayer
from Functions.LogsJson import json_read,json_write,logger

nextcord_logger = logging.getLogger("nextcord")
nextcord_logger.setLevel(logging.INFO)
mafic_logger = logging.getLogger("mafic")
mafic_logger.setLevel(logging.INFO)



dotenv_path = find_dotenv()
if not dotenv_path:
    logging.error(".env file not found. Please create one using default template.")

load_dotenv(dotenv_path)

class InvalidEnv(Exception):
    pass

try:
    announcements_channel_id = int(getenv("announcements_channel_id"))
    weeb_channel_id = int(getenv("weeb_channel_id"))
    tv_channel_id = int(getenv("weeb_channel_id"))
    glazer_vc = int(getenv("weeb_channel_id"))
except:
    raise InvalidEnv(".env file is not initialized. Please enter your token and channel IDs. Feeds and non command function WILL fail.")
leave_users_links = None

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ready_ran = False
        self.pool = NodePool(self)

    async def connect_lavalink(self, max_retries=5, delay=10):
        """Tries to connect to Lavalink with retries."""
        for attempt in range(1, max_retries + 1):
            try:
                await self.pool.create_node(
                    host="localhost",
                    port=int(getenv("port")),
                    label="MAIN",
                    password=getenv("pass"),
                )
                logger.info("Lavalink node connected successfully.")
                return  # Exit loop on success
            except Exception as e:
                logger.error(f"Lavalink connection failed (Attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)  # Wait before retrying
                else:
                    logger.critical("Max Lavalink connection retries reached. Giving up.")

    async def on_ready(self):
        if self.ready_ran:
            logger.info("ReLogged in as " + self.user.name)
            return

        await self.connect_lavalink()

        logger.info("Logged in as " + self.user.name)
        logger.info("Guilds: " + str(self.guilds))

        global leave_users_links
        leave_users_links = load_leave_users_links()

        if not hour_loop.is_running():
            hour_loop.start()

        self.loop.create_task(Events.event_loop(self, announcements_channel_id))
        self.ready_ran = True

bot = Bot(intents=Intents(guilds=True, voice_states=True))
        
def is_shadow():
    async def predicate(interaction: nextcord.Interaction) -> bool:
        return True#await is_member_in_guild(interaction.user.id,getenv("Guild_id"))
    return application_checks.check(predicate)

#region music

@bot.slash_command(name="join", description="Join your current voice channel or channel of choice.",dm_permission=False)
@is_shadow()
async def join(
    inter: Interaction[Bot], 
    channel: nextcord.VoiceChannel = SlashOption(
        name="channel",
        description="The voice channel to join",
        required=False,
        default=None
        )
    ):
    await Music.join(inter,channel)

@bot.slash_command(name="leave", description="Finish up an leave the channel.",dm_permission=False)
@is_shadow()
async def leave(inter: Interaction[Bot]):
    """Leave the voice channel and finish any tracks."""
    await Music.leave(inter,bot)

@bot.slash_command(name="skip", description="Skip the current track for a better one...",dm_permission=False)
@is_shadow()
async def skip(inter: Interaction[Bot]):
    """Skip the current song."""
    await Music.skip(inter)
    
@bot.slash_command(name="queue", description="Show the current track queue.",dm_permission=False)
async def queue(inter: Interaction[Bot]):
    """Get a list of the current queue"""
    await Music.queue(inter)

@bot.slash_command(name="direct_play", description="play the first track that comes up, with the options to add a start and end time.",dm_permission=False)
async def direct_play(
    inter: Interaction[Bot], 
    query: str, 
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
    await Music.direct_play(inter,query,bot,start,end)
    
@bot.slash_command(name="play", description="Search for a song or playlist and play it", dm_permission=False)
@is_shadow()
async def play(interaction: Interaction[Bot], *, query: str):
    await Music.play(interaction,query=query,bot=bot)

@bot.slash_command(name="now_playing", description="Show controls and status for the current track.",dm_permission=False)
@is_shadow()
async def now_playing(inter: Interaction[Bot]):
    """Display information about the currently playing track."""
    await Music.now_playing(inter)

#endregion

#region special
@bot.slash_command(name="glazer", description="Change the glazer channel year, leave year empty to advance a single year")
async def glazer(interaction: nextcord.Interaction, year: str = None):
    if interaction.user.id != 134769648234266624 and interaction.user.id != 571733232404529162:
        await interaction.response.send_message("Access denied, fucko.", ephemeral=True)
        return
    if not glazer_vc:
        interaction.send("glazer channel ID is not set please check .env", ephemeral=True)
        logging.warning("glazer command used with no vc ID set!")
        return
    if year is not None:
        if not year.isnumeric():
            await interaction.send("The year that you gave me is invalid.", ephemeral=True)
            return
        await bot.get_channel(glazer_vc).edit(name=f"Fine {year}'s Classics")
    else:
        channel = bot.get_channel(glazer_vc)
        title = channel.name
        title = title[5:]
        title = title[:title.find("'")]
        if not title.isnumeric():
            await interaction.send("Couldn't find the year, try to set it manually", ephemeral=True)
            return
        year = int(title) + 1
        await channel.edit(name=f"Fine {year}'s Classics")
        
    await interaction.send(f"Channel updated to be the year {year}", ephemeral=True)
    logging.info(f"glazer channel updated to the year {year}")

    
#endregion    
    
#region feed

@bot.slash_command(name="feed", description="Manage the anime release feed.", dm_permission=False)
async def feed(inter: Interaction[Bot], action: typing.Literal['Show', 'Add', 'Remove', 'Un/Subscribe', 'Update'] = "Show"):
    """Manage the anime release feed."""
    await Feeds.feed(inter,action,bot.get_channel(weeb_channel_id))
    
    
@tasks.loop(hours=1)
async def hour_loop():
    """check both feeds every hour starting from startup"""
    embed = await Feeds.feed_update(bot.get_channel(weeb_channel_id))
    if embed:
        await bot.get_channel(weeb_channel_id).send(embed=embed)
    embed = await Feeds.tv_update(bot.get_channel(tv_channel_id))
    if embed:
        await bot.get_channel(tv_channel_id).send(embed=embed)
    # global message
    
    message_id = await update_img(announcements_channel_id)
    logger.info(f"Feeds checked.")

#endregion

#region birdays
@bot.slash_command(name="birthdays", description="Show all birthdays")
async def birthdays(inter: Interaction[Bot]):
    await Events.birthdays(inter)

#endregion

#region Nyaa
@bot.slash_command(name="nyaa", description="Search for torrents on Nyaa.si", dm_permission=False)
async def nyaa(
    inter: Interaction, 
    query: str = nextcord.SlashOption(
        name="query",
        description="Enter the search query (e.g., anime name)",
        required=True  
    ),
    resolution: str = nextcord.SlashOption(
        name="resolution",
        description="Select the resolution",
        choices=["1080p", "720p", "480p"],  
        default="1080p"  
    ),
    sort: str = nextcord.SlashOption(
        name="sort",
        description="Select the sort type",
        choices=["date", "leechers", "seeders", "size", "downloads"],  
        default="seeders"  
    )
):
    """Searches for torrents on Nyaa.si and displays the results in an embed."""
    await Search.nyaa(inter, query, resolution, sort)
    

#endregion

#region roulette

@bot.slash_command(name="roulette", description="Roulette: Randomly pick from a list, use |number to duplicate options.",dm_permission=False)
@is_shadow()
async def roulette(interaction: Interaction[Bot], choices: str):
    """random option chooser from str sperated by commas duplicate options with copies after |

    Parameters
    ----------
    inter: Interaction
        The interaction object
    choices: str
        list the options with a comma inbetween each choice and | to add multiple of a choice
    """
    await Roulette.roulette(interaction,choices)
    
@bot.slash_command(name="auto_roulette", description="Run and automatic roulette with the given wheel", dm_permission=False)
@is_shadow()
async def auto_roulette(interaction: Interaction[Bot],edit:bool=False):
    await interaction.send("Please select a wheel to edit:" if edit else "select a roulette wheel:",view=Roulette.StringInputView(edit),ephemeral=False)

@bot.slash_command(name="schedule", description="check and edit your schedule", dm_permission=False)
@is_shadow()
async def schedule(interaction: Interaction[Bot], user:nextcord.Member = SlashOption(
        name="user",
        description="What user to check the schedule of",
        required=False,
        default=None
        )):
    data = json_read("Schedule")
    if user:
        user_id = user.id 
    else:
        user_id = interaction.user.id
    user_data = data.get(f"{user_id}")#, {day: [False] * 24 for day in Schedule.days})
    if not user_data:
        if user_id != interaction.user.id:
            await interaction.send(f"{user.mention} doesnt have a schedule yet.",ephemeral=True)
            return
        else:
            user_data = {day: [False] * 24 for day in Schedule.days}
    view = None if user_id != interaction.user.id else Schedule.DaySelectionView(user_id, user_data)
    table_message = Schedule.DaySelectionView(user_id, user_data).generate_schedule_table()
    if view:
        await interaction.send(f"Your schedule:\n{table_message}" if user_id == interaction.user.id else f"{user.mention} schedule:\n{table_message}",view=view ,ephemeral=True)
    else:
        await interaction.send(f"Your schedule:\n{table_message}" if user_id == interaction.user.id else f"{user.mention} schedule:\n{table_message}" ,ephemeral=True)

#endregion
# 
# region functions    

async def is_member_in_guild(member_id: int, guild_id: int) -> bool:
    """
    Check if a member is in a specific guild.

    Parameters:
    member_id (int): The ID of the member to check
    guild_id (int): The ID of the guild to check

    Returns:
    bool: True if the member is in the guild, False otherwise
    """
    try:
        guild = await bot.fetch_guild(guild_id)
    except Forbidden:
        print(f"the guild {guild_id} is forbidden")
        return False
    if not guild:
        print(f"the guild {guild_id} is not found")
        return False  # Guild not found
    
    member = await guild.fetch_member(member_id)
    return member is not None

def load_leave_users_links():
    file_path = os.path.join(os.path.dirname(__file__), 'links')
    try:
        data=json_read(file_path)
        # Convert keys to integers
        return {int(k): v for k, v in data.items()}
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using empty dictionary.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: {file_path} is not a valid JSON file. Using empty dictionary.")
        return {}
    
#region events

@bot.listen()
async def on_track_end(event: TrackEndEvent):
    assert isinstance(event.player, MyPlayer)
    if event.player.queue:

        await event.player.play_next_track(bot)
    else:
        await event.player.disconnect()
        await event.player.guild.change_voice_state(channel=None)
        await bot.change_presence(activity=None)

@bot.event
async def on_voice_state_update(member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
    if member == bot.user and before.channel and not after.channel:
        await bot.change_presence(activity=None)
        if isinstance(before.channel.guild.voice_client, MyPlayer):
            before.channel.guild.voice_client.queue.clear()
        return

    global leave_users_links
    
    async def stop_and_handle_queue(player: MyPlayer):
        """Helper function to handle stopping and queue management"""
        # await player.pause()
        # tracks = await player.fetch_tracks("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        # player.enqueue_track(tracks[0],end_time=60000,volume=50)
        
        if player.current:
            logger.info(f"Stopping track cause user returned: {player.current.uri}")
        else:
            logger.info("No current track to stop.")
        await player.stop()
        await player.disconnect()

    def get_track_owner(current_track):
        if not current_track:
            return None
        for user_id, data in leave_users_links.items():
            if data["url"] == current_track.uri:
                return user_id
        return None

    async def should_stop_leave_sound(channel, member_id):
        if member_id not in leave_users_links:
            return False
        return member_id in channel.voice_states

    async def delayed_presence_check(player: MyPlayer, channel, member_id, delay=0.5):
        """Perform a delayed check to see if user has joined and stop playback if needed"""
        await asyncio.sleep(delay)
        if await should_stop_leave_sound(channel, member_id):
            await stop_and_handle_queue(player)
            return

    if after.channel:
        player: MyPlayer = after.channel.guild.voice_client
        
        if not player and member == bot.user:
            for user_id in leave_users_links:
                if user_id in after.channel.voice_states:
                    return

        if player and player.channel == after.channel:
            current_track = player.current
            current_track_owner = get_track_owner(current_track)
            
            if (member.id in leave_users_links and current_track and 
                current_track.uri == leave_users_links[member.id]['url']) or \
               (member == bot.user and current_track_owner and 
                current_track_owner in after.channel.voice_states):
                await stop_and_handle_queue(player)
                return
    
    if member.id in leave_users_links:
        if before.channel and (not after.channel or after.afk) and len(before.channel.voice_states) > 0:
            member_is_listening = any(vm in leave_users_links and vm != member.id for vm in before.channel.voice_states)
            
            if member_is_listening:
                if await should_stop_leave_sound(before.channel, member.id):
                    return
                    
                if not before.channel.guild.voice_client:
                    await before.channel.connect(cls=MyPlayer)
                
                player: MyPlayer = before.channel.guild.voice_client
                if not player or not player.current:
                    tracks = await player.fetch_tracks(leave_users_links[member.id]["url"])
                    if tracks:
                        if not player:
                            await before.channel.connect(cls=MyPlayer)
                            player = before.channel.guild.voice_client
                        
                        if await should_stop_leave_sound(before.channel, member.id):
                            return
                            
                        await player.play(
                            tracks[0],
                            start_time=leave_users_links[member.id]["start"],
                            end_time=leave_users_links[member.id]["end"] if leave_users_links[member.id]["end"] != 0 else None
                        )
                    
                        # Schedule a delayed check
                        asyncio.create_task(delayed_presence_check(player, before.channel, member.id))
                    else:
                        logger.warning(f"Failed to fetch tracks for {leave_users_links[member.id]['url']}")
                        await player.disconnect()    
@bot.event
async def on_application_command_error(inter: Interaction[Bot], error: Exception):
    if isinstance(error, nextcord.errors.ApplicationCheckFailure):
            await inter.send("Looks like this command is not for peasants :(\nBut worry not! as all you have to do to become sigma male is to join the Shadow_Wyverns server!", ephemeral=True)
    else:
        traceback.print_exception(type(error), error, error.__traceback__)
        await inter.send(f"An error occurred: {error}")

@bot.event
async def on_node_ready(node):
    logger.info(f"Node {node.label} is ready!")
    
#region basic commands
@bot.slash_command(name="help", description="Displays the bot's command list.")
async def help_command(interaction: nextcord.Interaction):
    embed = nextcord.Embed(
        title="Help - Command List",
        description="Here are the available commands:",
        color=nextcord.Color.blurple()
    )

    # Loop through registered application commands
    for command in bot.get_application_commands():
        embed.add_field(
            name=f"/{command.name}",
            value=command.description or "No description provided.",
            inline=False
        )

    embed.set_footer(text="Use /<command> to execute a command.")
    await interaction.response.send_message(embed=embed,ephemeral=True)

async def update_img(channel_id:int)->int:
    unique_suffix = f"?t={datetime.datetime.now(datetime.timezone.utc).timestamp()}"
    updated_image_url1 = "https://www.banskoski.com/ext/webcams/livecam-1.jpg" + unique_suffix
    updated_image_url2 = "https://www.banskoski.com/ext/webcams/livecam-5.jpg" + unique_suffix
    data = json_read("Data")
    channel = bot.get_channel(channel_id)
    message_id = data["message_id"]
    if message_id and await validate_message(channel, message_id) :
        message = await bot.get_channel(channel_id).fetch_message(message_id)
    else:
        # Message doesn't exist or ID is None; create a new message
        message = await channel.send("\n".join([updated_image_url1,updated_image_url2]))
        logger.warning("could not find message. sending new message!")
        # Save the new message ID
        data["message_id"] = message.id
        json_write(data)
    try:
        await message.edit(content="\n".join([updated_image_url1,updated_image_url2]))
    except:
        #  message = await bot.get_channel(channel_id).send("\n".join([updated_image_url1,updated_image_url2]))
        logger.warning("failed to get message for images!")
    return message.id

async def validate_message(channel, message_id):
    """a check if the message is fetachable"""
    try:
        # Try fetching the message by its ID
        await channel.fetch_message(message_id)
        return True
    except nextcord.NotFound:
        # Message doesn't exist
        return False
    
@hour_loop.before_loop
async def before_hour_loop():
    # Calculate the time until the next whole hour
    now = datetime.datetime.now()
    next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    wait_time = (next_hour - now).total_seconds()

    logger.info(f"Waiting {wait_time} seconds until the next whole hour.")
    await asyncio.sleep(wait_time)    
    
STATS = """```
Uptime: {uptime}
Memory: {used:.0f}MiB : {free:.0f}MiB / {allocated:.0f}MiB -- {reservable:.0f}MiB
CPU: {system_load:.2f}% : {lavalink_load:.2f}%
Players: {player_count}
Playing Players: {playing_player_count}
```"""

@bot.slash_command(name="stats", description="check the stats of the bot.")
async def stats(inter: Interaction):
    node = bot.pool.nodes[0]

    stats = node.stats

    if not stats:
        return await inter.send("No stats available.")
    
    formStats=STATS.format(
            uptime=stats.uptime,
            used=stats.memory.used / 1024 / 1024,
            free=stats.memory.free / 1024 / 1024,
            allocated=stats.memory.allocated / 1024 / 1024,
            reservable=stats.memory.reservable / 1024 / 1024,
            system_load=stats.cpu.system_load * 100,
            lavalink_load=stats.cpu.lavalink_load * 100,
            player_count=stats.player_count,
            playing_player_count=stats.playing_player_count,
        )
    logger.info(formStats)
    await inter.send(formStats)
    return None

try:
    bot.run(getenv("TOKEN"))
except:
    logging.critical("bot failed to run. check .env token.")