from nextcord import Interaction,SlashOption,Embed,ButtonStyle,ui

from datetime import datetime

import nyaapy.anime_site as Nyaa
from Functions.LogsJson import logger
#region views
class NyaaSearchView(ui.View):
    def __init__(self, query, resolution="1080p", sort="seeders"):
        super().__init__(timeout=60)  # Auto-remove after 60 seconds
        self.query = query
        self.resolution = resolution
        self.sort = sort
        self.message = None

    @ui.button(label="Search Nyaa", style=ButtonStyle.primary,emoji="📥")
    async def search_nyaa(self, button: ui.Button, interaction: Interaction):
        # Disable the button to prevent multiple clicks
        button.disabled = True
        await interaction.response.edit_message(view=self)

        # Run the Nyaa search command
        await nyaa(interaction, self.query, resolution=self.resolution, sort=self.sort)
        
        # Remove the view after use
        await interaction.edit_original_message(view=None)

    async def on_timeout(self):
        # Remove the view if no interaction occurs within the timeout
        try:
            await self.message.edit(view=None)
        except:
            pass
#endregion

#region commands
async def nyaa(inter: Interaction, query: str,resolution: str = SlashOption(
        name="resolution",
        description="Select the resolution",
        choices=["1080p", "720p", "480p"],  # Define the choices here
        default="1080p"  # Default value if no option is selected
    ),sort:str = SlashOption(
        name="sort",
        description="Select the sort type",
        choices=["date", "leechers", "seeders", "size", "downloads"],  # Define the choices here
        default="seeders"  # Default value if no option is selected
    ) ):
    """Searches for torrents on Nyaa.si and displays the results in an embed."""
    await inter.response.defer()  # Defer response to allow for processing
    
    nyaa = Nyaa.AnimeTorrentSite
    sort = "id" if sort == "date" else sort
    try:
        results = nyaa.search(query+f" [{resolution}]",category=1,subcategory=2,sort=sort)
        logger.info(f"Nyaa serch was used with: {query} at {resolution} with {sort} as a sort.")
        if sort == "seeders":
            results.sort(key=lambda result: int(result.seeders), reverse=True)
        if not results:
            await inter.followup.send("No results found for your query.")
            return
       
        embed = Embed(
            title=f"🔍 Nyaa Search Results for: **{query}**",
            url=f"https://nyaa.si/?f=0&c=1_2&q={query.replace(' ', '+')+f'+[{resolution}]'}",
            description="Top search results for your query on Nyaa.si:",
            color=0x1D8FE2
        )

        for result in results[:5]:  # Limit to top 5 results
            seeders = int(result.seeders)
            leechers = int(result.leechers)

            # Determine torrent health color
            if seeders > leechers * 2:  # High health
                health_color = "🟢"
            elif seeders >= leechers:  # Moderate health
                health_color = "🟡"
            else:  # Poor health
                health_color = "🔴"
            embed.add_field(
                name=f"`📁{health_color} {result.name}`",
                value=(
                    f"**🗂 Size:** {result.size} | [🔗 Page]({result.url}) | 🗓️{format_rss_date(result.date)}\n"
                    f"**📊 Seeds:** {result.seeders} | **📉 Leechers:** {result.leechers}\n"
                    f"[📥 Torrent Link]({result.download_url}) | [🧲 Magnet Link]({result.url+'/magnet'})"
                ),
                inline=False
            )
        embed.set_footer(text="Powered by NyaaPy | Results from Nyaa.si", icon_url="https://nyaa.si/static/favicon.png")
       
        await inter.followup.send(embed=embed)

    except Exception as e:
        await inter.followup.send(f"An error occurred: {str(e)}")

#endregion

#region functions

def format_rss_date(date_string):#for nyaa rss format
    """
    Converts a date string to a more human-readable format.
    """
    # Parse the input date string
    parsed_date = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
    
    # Format the parsed date into a readable string
    readable_date = parsed_date.strftime('%A, %d %B %Y at %H:%M:%S %Z')
    
    return readable_date