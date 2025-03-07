import asyncio
import nextcord

from datetime import datetime, timedelta, time

from Functions.LogsJson import json_read,json_write,logger
from Functions.Events import wake_event_loop
data_file= "Schedule"
# Days of the week
days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Main View for selecting days of the week
class DaySelectionView(nextcord.ui.View):
    def __init__(self, user_id, user_data=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.user_data = user_data or json_read(data_file).get(str(user_id), {day: [False] * 24 for day in days})
        

        for day in days:
            self.add_item(DayButton(day, self.user_id, self.user_data))

        self.add_item(ConfirmButton(self.user_id, self.user_data))
    def generate_schedule_table(self):
        # hours = [ str(hour).zfill(2) for hour in range(24)]  # Column headers for hours
        # table = "🕒 | " + " | ".join(hours) + " |\n"  # Add header row
        table = "🕒 | 00 | 01  | 02  | 03 | 04  | 05  | 06 | 07  | 08 | 09 | 10  | 11  | 12 | 13  | 14  | 15 | 16 | 17  | 18 | 19  | 20 | 21 | 22  | 23  |\n"
        # table += "▬▬▬▬|" + "▬▬▬▬|" * 24 + "\n"  # Add separator line
        table += "▬▬▬▬|▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬▬|▬▬▬▬▬|▬▬▬▬|▬▬▬▬|\n"

        for day in days:
            row = f"{day[:3]} | "  # Abbreviated day names for rows
            row += " | ".join("✅" if self.user_data[day][hour] else "❌" for hour in range(24))+ " |"
            table += row + "\n"

        return f"```\n{table}```"

    async def update_message(self, interaction):
        table_message = self.generate_schedule_table()
        await interaction.response.edit_message(content=f"Select a day and view your schedule:\n{table_message}", view=self)

# Button for days of the week
class DayButton(nextcord.ui.Button):
    def __init__(self, day, user_id, user_data):
        super().__init__(label=day, style=nextcord.ButtonStyle.primary)
        self.day = day
        self.user_id = user_id
        self.user_data = user_data

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.edit_message(content=f"Select hours for {self.day}",
                                                view=HourSelectionView(self.day, self.user_id, self.user_data))

# Confirm Button to save data
class ConfirmButton(nextcord.ui.Button):
    def __init__(self, user_id, user_data):
        super().__init__(label="Confirm", style=nextcord.ButtonStyle.success)
        self.user_id = user_id
        self.user_data = user_data

    async def callback(self, interaction: nextcord.Interaction):
        data = json_read(data_file)
        data[str(self.user_id)] = self.user_data
        json_write(data,data_file)
        await interaction.response.edit_message(content="Your schedule has been saved!", view=None)

# Hour Selection View
class HourSelectionView(nextcord.ui.View):
    def __init__(self, day, user_id, user_data):
        super().__init__(timeout=None)
        self.day = day
        self.user_id = user_id
        self.user_data = user_data

        for hour in range(24):
            self.add_item(HourToggleButton(hour, self.day, self.user_data))

        self.add_item(BackButton(self.user_id, self.user_data))

# Hour Toggle Button
class HourToggleButton(nextcord.ui.Button):
    def __init__(self, hour, day, user_data):
        is_enabled = user_data[day][hour]
        label = f"{hour}:00"
        emoji = "✅" if is_enabled else "❌"
        super().__init__(label=label, emoji=emoji, style=nextcord.ButtonStyle.secondary)
        self.hour = hour
        self.day = day
        self.user_data = user_data

    async def callback(self, interaction: nextcord.Interaction):
        self.user_data[self.day][self.hour] = not self.user_data[self.day][self.hour]
        self.emoji = "✅" if self.user_data[self.day][self.hour] else "❌"
        await interaction.response.edit_message(view=self.view)

# Back Button
class BackButton(nextcord.ui.Button):
    def __init__(self, user_id, user_data):
        super().__init__(label="Back", style=nextcord.ButtonStyle.danger)
        self.user_id = user_id
        self.user_data = user_data

    async def callback(self, interaction: nextcord.Interaction):
        view = DaySelectionView(self.user_id, self.user_data)
        await view.update_message(interaction)
        # await interaction.response.edit_message(content="Select a day:",
                                                # view=DaySelectionView(self.user_id,self.user_data))
        

def intersect_schedules(user_ids):
    """
    Returns the intersecting schedule for a list of user IDs.
    Skips users with no schedule and returns their IDs as well.
    
    :param user_ids: List of user IDs to intersect schedules.
    :return: A tuple containing:
        - A dictionary with the intersected schedule.
        - A list of user IDs that were skipped due to missing schedules.
    """
    # Load data from the JSON file
    data = json_read(data_file)

    # Initialize the intersection schedule
    intersection = {day: [True] * 24 for day in days}
    skipped_users = []

    # Process each user's schedule
    valid_users = 0  # Track number of users with valid schedules
    for user_id in user_ids:
        user_schedule = data.get(str(user_id))

        if user_schedule is None:
            # If schedule is missing, add to skipped list
            skipped_users.append(user_id)
            continue

        # Intersect schedules day by day
        valid_users += 1
        for day in days:
            for hour in range(24):
                intersection[day][hour] = intersection[day][hour] and user_schedule[day][hour]

    # If no valid schedules found, reset the intersection to empty
    if valid_users == 0:
        intersection = {day: [False] * 24 for day in days}

    return intersection, skipped_users

def get_available_slots(schedule, skip_days=1, max_slots=5):
    """
    Finds available date and time slots based on the schedule and current date.
    
    :param schedule: Dictionary with days as keys and lists of 24 booleans for availability.
    :param skip_days: Number of days to skip from the current date.
    :param max_slots: Maximum number of available slots to return.
    :return: List of tuples with available dates and hours [(date, hour), ...].
    """
    today = datetime.now().date()
    start_date = today + timedelta(days=skip_days)
    current_time = datetime.now().time()

    # Mapping weekdays to the schedule dictionary
    weekday_to_day = {i: day for i, day in enumerate(days)}
    available_slots = []

    # Iterate through days starting from the current date
    for day_offset in range(7 * 10):  # Search up to 10 weeks ahead
        current_date = start_date + timedelta(days=day_offset)
        weekday_index = (current_date.weekday() + 1) % 7  # Adjust weekday index for Sunday-starting weeks
        current_day_name = weekday_to_day[weekday_index]

        # Skip if the day is not in the schedule
        if current_day_name not in schedule:
            continue

        # Check hours for the current day
        for hour in range(24):
            # Skip past hours if checking today
            if current_date == today and hour <= current_time.hour:
                continue

            if schedule[current_day_name][hour]:
                available_slots.append((current_date, hour))

            if len(available_slots) >= max_slots:
                return available_slots

    return available_slots

async def schedule_poll(channel, title, mentions, schedule, skipped_users, max_slots=5, timeout= 24*60*60):
    """
    Create a poll for the available time slots and send results after a timeout.

    :param channel: The Discord channel to send the poll.
    :param title: Title of the poll (e.g., anime episode name).
    :param mentions: Mentions of the users in the poll.
    :param schedule: Intersected schedule to derive time slots from.
    :param skipped_users: List of user IDs whose schedules were missing.
    :param max_slots: Maximum number of slots to display in the poll.
    :param timeout: Time in seconds for the poll to remain active (default: 24 hours).
    """
    # Find closest available slots starting from the next day
    available_slots = get_available_slots(schedule, skip_days=1, max_slots=max_slots)
    if not available_slots:
        await channel.send(f"⛔ No common times available for **{title}**.")
        return

    # Current time and timeout end timestamp
    poll_end_time = datetime.now() + timedelta(seconds=timeout)
    poll_end_timestamp = int(poll_end_time.timestamp())  # Unix timestamp for Discord formatting

    # Build poll options with Discord timestamps
    options = [f"<t:{int(datetime.combine(slot[0], time(hour=slot[1])).timestamp())}:F>" for slot in available_slots]
    description = "\n".join([f"{i + 1}. {option}" for i, option in enumerate(options)])

    # Build mentions and skipped users text
    mentions_text = " ".join([f"<@{user_id}>" for user_id in mentions])
    skipped_text = (
        f"\n\n⚠️ **The following users' schedules were not considered:** "
        + ", ".join([f"<@{user_id}>" for user_id in skipped_users])
        if skipped_users
        else ""
    )

    # Send poll message with poll end time
    poll_message = await channel.send(
        f"📅 **Poll for {title}**\n{mentions_text}{skipped_text}\n\n"
        f"**Vote for your preferred time:**\n{description}\n\n"
        f"⏳ **Poll ends at:** <t:{poll_end_timestamp}:F> (<t:{poll_end_timestamp}:R>)"
    )

    # Add reactions for voting
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    poll_emojis = emojis[:len(options)]
    for emoji in poll_emojis:
        await poll_message.add_reaction(emoji)

    # Wait for poll timeout
    await asyncio.sleep(timeout)

    # Fetch message again to count reactions
    poll_message = await channel.fetch_message(poll_message.id)
    reactions = {reaction.emoji: reaction.count - 1 for reaction in poll_message.reactions if reaction.emoji in poll_emojis}

    # Remove all reactions
    try:
        await poll_message.clear_reactions()
    except nextcord.Forbidden:
        # Bot lacks permissions to clear reactions
        logger.error("Bot lacks permissions to clear poll reactions")

    
    # Check if all reaction counts are zero (or just 1, which is the bot's own reaction)
    if all(count == 0 for count in reactions.values()):
        await channel.send(f"❌ **Poll Results for {title}**\nNo votes were received.")
    else:
        most_voted = max(reactions, key=reactions.get)
        selected_time = options[poll_emojis.index(most_voted)]
        chosen_slot= available_slots[poll_emojis.index(most_voted)]
        event_time = int(datetime.combine(chosen_slot[0], time(hour=chosen_slot[1])).timestamp())

        # Add the event
        add_poll_event(
            title=title,
            time=event_time,
            desc=f"The chosen time to watch this epsiode is:{selected_time}, which is right now!",
            mentions=mentions 
        )
        await channel.send(f"✅ **Poll Results for {title}**\nThe most voted time is: <t:{event_time}:F>.")

def add_poll_event(title: str, time: int, desc: str, mentions: list[int]):
    """Adds a new event to the Events.json file."""
    data = json_read("Events")
    new_event = {
        "type": "poll_result",
        "title": title,
        "time": time,
        "desc": desc,
        "mention": mentions,
        "snooze": "actual"
    }
    data.append(new_event)
    json_write(data, "Events")
    logger.info(f"Added new poll event: {new_event}")
    wake_event_loop()  # Wake up the event loop to process the new event
    logger.info("poll added, event loop woken up")
