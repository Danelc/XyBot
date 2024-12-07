
from nextcord import Interaction,SelectOption,ui,ButtonStyle,embeds

import feedparser,typing,requests,json,pytz
from datetime import datetime,timedelta

from Functions.LogsJson import json_read,json_write,logger

MAXELEMENTINPAGE = 25

#region views

class FeedDropdown(ui.Select):
    def __init__(self, options: list[SelectOption], action: str, inter: Interaction):
        super().__init__(
            placeholder=f"Select an entry to {action}",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.action = action
        self.inter = inter

    async def callback(self, interaction: Interaction):
        data = json_read("Data")
        anime_feed = data.get("anime", [])
        tv_feed = data.get("tv", [])
        entry = self.values[0]

        # Disable the dropdown and buttons        
        self.disabled = True
        for child in self.view.children:
            if isinstance(child, (ui.Button, ui.Select)):
                child.disabled = True

        
        # Update the interaction's response with the disabled dropdown and buttons
        await self.inter.edit_original_message(view=self.view)

        if self.action == "Subscribe":
            for thing in anime_feed + tv_feed:
                if entry.lower() == thing.get("title"):
                    # Ensure `mentions` key exists and is a list
                    mentions = thing.setdefault("mentions", [])
                    user_id = interaction.user.id
                    nickname = interaction.user.display_name

                    if user_id in mentions:
                        # Unsubscribe
                        mentions.remove(user_id)
                        json_write(data, "Data")
                        await interaction.response.send_message(f"{nickname} has unsubscribed from updates for **{entry.title()}**.")
                        logger.info(f"{user_id} ({nickname}) unsubscribed from {entry}.")
                    else:
                        # Subscribe
                        mentions.append(user_id)
                        json_write(data, "Data")
                        await interaction.response.send_message(f"{nickname} has subscribed to updates for **{entry.title()}**.")
                        logger.info(f"{user_id} ({nickname}) subscribed to {entry}.")
                    break
            else:
                await interaction.response.send_message(f"Could not find {entry} in the feed.")
        if self.action == "Remove":
            found = False
            for thing in anime_feed:
                if entry.lower() == thing.get("title"):
                    anime_feed.remove(thing)
                    data["anime"] = anime_feed
                    json_write(data, "Data")
                    found = True
                    break
            
            if found:
                await interaction.response.send_message(f"Removed {entry} from the Anime feed successfully")
                logger.info(f"Removed {entry} from the anime feed")
            else:
                await interaction.response.send_message(f"Could not find {entry} in the Anime feed.")
        
        elif self.action == "Add":
            if not any(entry.lower() == thing.get("title") for thing in anime_feed):
                anime_feed.append({"title": entry.lower(), "episode": 0})
                data["anime"] = anime_feed
                json_write(data, "Data")
                await interaction.response.send_message(f"Added {entry} to the Anime feed successfully")
                logger.info(f"Added {entry} to the anime feed")
            else:
                await interaction.response.send_message(f"{entry} is already in the Anime feed.")
        

class FeedView(ui.View):
    def __init__(self, action: str, inter: Interaction, options: list[SelectOption], page: int = 1):
        super().__init__(timeout=180)
        self.action = action
        self.inter = inter
        self.page = page
        self.options = options
        self.items_per_page = MAXELEMENTINPAGE
        self.total_pages = (len(options) // self.items_per_page) + (1 if len(options) % self.items_per_page > 0 else 0)

        # Add the dropdown for the current page
        self.dropdown = FeedDropdown(self.options[(self.page - 1) * self.items_per_page : self.page * self.items_per_page], action, inter)
        self.add_item(self.dropdown)

        # Add navigation buttons if there are multiple pages
        if self.total_pages > 1:
            if self.page > 1:
                self.add_item(ui.Button(label="Previous", style=ButtonStyle.primary, custom_id="previous"))
            if self.page < self.total_pages:
                self.add_item(ui.Button(label="Next", style=ButtonStyle.primary, custom_id="next"))

    async def interaction_check(self, interaction: Interaction)->bool:
        # Only handle button interactions here
        if not interaction.data.get("custom_id") in ["previous", "next"]:
            return True  # Let the dropdown handle its own interaction
            
        if interaction.data["custom_id"] == "previous" and self.page > 1:
            self.page -= 1
            await self.update_view(interaction)
            return True
        elif interaction.data["custom_id"] == "next" and self.page < self.total_pages:
            self.page += 1
            await self.update_view(interaction)
            return True
        return False

    async def update_view(self, interaction: Interaction):
        # Rebuild the view with the updated page and options
        options = self.options
        view = FeedView(self.action, self.inter, options, self.page)
        # Edit the message to update the view
        await interaction.response.edit_message(view=view)

#region commands

async def feed(inter: Interaction, action: typing.Literal['Show', 'Add', 'Remove', 'Un/Subscirbe', 'Update'] = "Show"):
    """Manage the anime release feed."""
    if action.lower() == "show":
        data = json_read("Data")
        user_id = inter.user.id  # ID of the user running the command
        anime_feed = data.get("anime", [])
        tv_feed = data.get("tv", [])

        # Format anime feed with subscribe tags
        anime_list = [
            f"**{i + 1}.** {item['title'].title()} - Episode {item['episode']} "
            + ("(Subscribed)" if user_id in item.get("mentions", []) else "")
            for i, item in enumerate(anime_feed)
        ]

        # Format TV feed with subscribe tags
        tv_list = [
            f"**{i + 1}.** {item['title'].title()} - Episode {item['episode']} "
            + ("(Subscribed)" if user_id in item.get("mentions", []) else "")
            for i, item in enumerate(tv_feed)
        ]
        
        anime_section = "**Anime Feed:**\n" + ("\n".join(anime_list) if anime_list else "No entries in the Anime feed.")
        tv_section = "\n\n**TV Feed:**\n" + ("\n".join(tv_list) if tv_list else "No entries in the TV feed.")

        content = anime_section + tv_section# "**Anime Feed:**\n" + "\n".join(anime_list) + "\n\n**TV Feed:**\n" + "\n".join(tv_list)
        await inter.send(content or "No data available in the feeds.", ephemeral=True)
    
    elif action.lower() == "add":
        rss_feed = feedparser.parse("https://subsplease.org/rss/?t&r=1080").entries
        data = json_read("Data")
        anime_titles = {item["title"] for item in data.get("anime", [])}
        
        # Filter out titles already in the JSON file
        unique_titles = sorted(set(
            entry.get("title").split(" - ")[0].lower()
            .replace("[subsplease]", "")
            .strip()
            for entry in rss_feed
        ) - anime_titles)

        options = [SelectOption(label=title.title(), value=title) for title in unique_titles]
        
        if not options:
            await inter.send("No new anime series available to add.")
        else:
            await inter.send("Select an anime series to add:", view=FeedView("Add", inter, options), ephemeral=True)


    elif action.lower() == "remove":
        data = json_read("Data")
        anime_feed = data.get("anime", [])
        options = [SelectOption(label=item.get("title").title(), value=item.get("title")) for item in anime_feed]
        if not options:
            await inter.send("The Anime feed is empty, nothing to remove.")
        else:
            await inter.send("Select an Anime series to remove:", view=FeedView("Remove", inter, options),ephemeral=True)

    elif action.lower() == "update":
        embed = await feed_update() or embeds.Embed(title="Nothing new, sowwy.")
        await inter.send(embed=embed)

    elif action.lower() == "un/subscribe":
        data = json_read("Data")
        anime_feed = data.get("anime", [])
        tv_feed = data.get("tv", [])
        
        options = []
        user_id = inter.user.id

        for item in anime_feed + tv_feed:
            title = item["title"].title()
            mentions = item.get("mentions", [])
            label = f"{title} (Subscribed)" if user_id in mentions else title
            options.append(SelectOption(label=label, value=item["title"]))

        if not options:
            await inter.send("There are no entries available to subscribe to.")
        else:
            await inter.send("Select an entry to subscribe/unsubscribe:", view=FeedView("Subscribe", inter, options), ephemeral=True)
    else:
        await inter.send("Invalid action! Use Show, Add, Remove, Update, or Subscribe.")

#region functions

async def feed_update():
    rss_feed = feedparser.parse("https://subsplease.org/rss/?t&r=1080").entries
    rss_feed.reverse()
    data = json_read("Data")
    anime_data = data.get("anime", [])
    result = []

    for entry in rss_feed:
        entry_published_date = datetime.strptime(entry["published"], "%a, %d %b %Y %H:%M:%S %z")
        for comp in anime_data:
            if comp.get("title") in entry.get("title").lower():
                index = entry.get("title").rfind('- ')
                rss_episode = "Finished Airing." if index == -1 else entry.get("title")[index + 2:].split(' ')[0]
                #handle published date
                pubDate = comp.get("pubDate")
                if pubDate:
                    pubDate = datetime.strptime(pubDate, "%Y-%m-%dT%H:%M:%S%z")
                else:
                    pubDate = datetime.min.replace(tzinfo=pytz.utc)
                if (
                    str(comp["episode"]) != str(rss_episode.split('v')[0])
                    and entry_published_date > pubDate
                ):
                    result.append({
                        "title": entry.get("title"),
                        "link": entry.get("link").replace('torrent', 'magnet'),
                        "mentions": comp.get("mentions", [])  # Include mentions if available
                    })
                    comp["episode"] = str(rss_episode)
                    comp["pubDate"] = entry_published_date.isoformat()
                break

    if result:
        data["anime"] = anime_data
        json_write(data, "Data")
        list_links = []
        for i, t in enumerate(result):
            mentions = "".join(f"<@{user_id}>" for user_id in t["mentions"])
            if mentions:
                mentions = "\n"+mentions
            list_links.append(
                f"**{i + 1}.** [{t['title']}]({t['link']}) {mentions}"
            )
        logger.info(f"new anime RSS release: {list_links}")
        return embeds.Embed(title="A new Anime episode has been released!", description="\n".join(list_links))


    
async def tv_update():
    rss_feed = feedparser.parse("https://showrss.info/user/278057.rss?magnets=true&namespaces=true&name=clean&quality=fhd&re=null").entries
    data = json_read("Data")
    tv_data = data.get("tv", [])
    result = []

    for entry in rss_feed:
        entry_published_date = datetime.strptime(entry["published"], "%a, %d %b %Y %H:%M:%S %z")
        for comp in tv_data:
            if comp.get("title") in entry.get("title").lower():
                index = entry.get("title").rfind('x')
                rss_episode = entry["title"][index + 1:].split(' ')[0]
                #handle published date
                pubDate = comp.get("pubDate")
                if pubDate:
                    pubDate = datetime.strptime(pubDate, "%Y-%m-%dT%H:%M:%S%z")
                else:
                    pubDate = datetime.min.replace(tzinfo=pytz.utc)
                if (
                    str(comp["episode"]) < str(rss_episode.split('v')[0])
                    # and entry_published_date > datetime.now(pytz.utc) - timedelta(days=3)
                    and entry_published_date > pubDate
                ):
                    result.append(entry)
                    result.append({
                        "title": entry.get("title"),
                        "link": entry.get("link"),
                        "mentions": comp.get("mentions", [])  # Include mentions if available
                    })
                    comp["episode"] = str(rss_episode)
                    comp["pubDate"] = entry_published_date.isoformat()
                break

    if result:
        data["tv"] = tv_data
        json_write(data, "Data")
        list_links = []
        for i, t in enumerate(result):
            mentions = "".join(f"<@{user_id}>" for user_id in t["mentions"])
            if mentions:
                mentions = "\n"+mentions
            list_links.append(
                f"**{i + 1}.** [{t['title']}]({t['link']}) {mentions}"
            )
        logger.info(f"new TV RSS release: {list_links}")
        return embeds.Embed(title="A new TV episode has been released!", description="\n".join(list_links))
    
def magnet_short(magnet_url:str):
    # parameters = {
    #     "m" : magnet_url
    # }
    # response = requests.get("http://mgnet.me/api/create",params=parameters)
    # return response.json()["shorturl"]
    apiUrl = "https://tormag.ezpz.work/api/api.php?action=insertMagnets"
    data = {"magnets": 
            [
                magnet_url
            ]
    }
    resp = requests.post(apiUrl, json=data)
    responseJson = json.loads(resp.text)
    if "magnetEntries" in responseJson:
        links = responseJson["magnetEntries"]
        if links:
            logger.info(f"Shortened a magnet link(10 max daily)")
            return links[0]
    else:
        return responseJson["message"]