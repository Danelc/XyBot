import operator,time,random,asyncio

from nextcord import Interaction,Embed,Color,ui,TextInput,ButtonStyle

from datetime import datetime

from Functions.LogsJson import json_read,json_write,logger


async def event_loop(bot,channel:int):
    while True:
        next_sec= next_event_delta()
        days, hours = convert_seconds(next_sec)
        logger.info(f"Next event in {next_sec} seconds ({days} days and {hours} hours)")
        await asyncio.sleep(next_sec)
        embed = await event_update()
        if embed:
            await bot.get_channel(channel).send(embed=embed)


class BirthdayModal(ui.Modal):
    def __init__(self, title: str, user_name: str, is_update: bool, previous_date: str = None):
        self.user_name = user_name
        self.is_update = is_update
        modal_title = "Update Birthday" if is_update else "Add Birthday"
        super().__init__(title=modal_title)

        placeholder = previous_date if is_update else "e.g., 25-12-2000"
        # Create the TextInput with the required label parameter
        self.birthday_input = ui.TextInput(
            label="Enter your birthday (DD-MM-YYYY):",
            custom_id="birthday_input",
            min_length=10,
            max_length=10,
            placeholder=placeholder,
            required=True
        )
        self.add_item(self.birthday_input)

    async def callback(self, interaction: Interaction):
        try:
            # Get the input and validate the date
            new_date_str = self.birthday_input.value
            new_date = datetime.strptime(new_date_str, "%d-%m-%Y")

            # Convert the date to a UNIX timestamp
            new_timestamp = int(new_date.timestamp())

            # Fetch and update data
            data = json_read("Events")
            if self.is_update:
                # Update the user's birthday
                for event in data:
                    if event['title'] == self.user_name:
                        event['time'] = new_timestamp
                        break
            else:
                # Add a new birthday
                data.append({"type": "birthday", "title": self.user_name, "time": new_timestamp})

            json_write("Events", data)

            await interaction.response.send_message(
                f"Your birthday has been {'updated' if self.is_update else 'added'} to {new_date.strftime('%d-%m-%Y')}!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "Invalid date format. Please use DD-MM-YYYY.", ephemeral=True
            )

class BirthdayView(ui.View):
    """
    A view that presents a button for adding or updating a user's birthday.

    Attributes:
        has_birthday (bool): Indicates if the user already has a birthday entry.
        user_name (str): The name of the user.
        previous_date (str, optional): The previous birthday date if updating.
    """
    def __init__(self, has_birthday: bool, user_name: str, previous_date: str = None):
        super().__init__()
        self.has_birthday = has_birthday
        self.user_name = user_name
        self.previous_date = previous_date
        
        # Create the button with appropriate label and style
        self.birthday_button = ui.Button(
            label="Update Birthday" if has_birthday else "Add Birthday",
            style=ButtonStyle.green if has_birthday else ButtonStyle.blurple,
            custom_id="update_or_add_birthday"
        )
        self.birthday_button.callback = self.update_or_add_birthday
        self.add_item(self.birthday_button)

    async def update_or_add_birthday(self, interaction: Interaction):
        modal = BirthdayModal(
            title="Birthday Entry",
            user_name=self.user_name,
            is_update=self.has_birthday,
            previous_date=self.previous_date
        )
        await interaction.response.send_modal(modal)

async def birthdays(inter: Interaction):
    data = json_read("Events")
    user_name = inter.user.name
    user_mention = f"<@{inter.user.id}>"  # Add mention format

    # Check if the user already has a birthday in the list
    # Look for both username and mention format
    user_birthday = next(
        (event for event in data if event['title'] in [user_name, user_mention]), 
        None
    )
    previous_date = None

    if user_birthday:
        # Format the previous date for the placeholder
        previous_date = datetime.fromtimestamp(user_birthday['time']).strftime("%d-%m-%Y")

    birthday_events = [event for event in data if event['type'] == 'birthday']

    # Create the embed for displaying birthdays
    embed = Embed(title="🎂 Upcoming Birthdays:", color=Color.blue())

    # Prepare and sort the list of birthdays
    if birthday_events:
        birthday_list = [
            (datetime.fromtimestamp(event['time']), event['title'])
            for event in birthday_events
        ]
        birthday_list.sort(key=operator.itemgetter(0))

        description = ""
        for i, (date, name) in enumerate(birthday_list, start=1):
            description += (
                f"**{i}. {name}** - <t:{int(date.timestamp())}:D> "
                f"(<t:{int(date.timestamp())}:R>)\n\n"
            )
        embed.description = description.strip()
    else:
        embed.description = "No birthdays found."

    # Determine the button text and create the view
    view = BirthdayView(
        has_birthday=bool(user_birthday),
        user_name=user_mention,  # Use mention format for consistency
        previous_date=previous_date
    )

    await inter.response.send_message(embed=embed, view=view, ephemeral=True)
async def event_update() -> Embed | None:
    data = json_read("Events")
    current_time = int(time.time())
    current_year = datetime.now().year
    event_list = []
    updated_data = []  # To hold events that are still valid

    for entry in data:
        # Ignore events marked as "past"
        if entry.get('snooze') == "past":
            continue

        if entry['time'] <= current_time:
            # Process current or overdue events
            event_list.append(entry)

            if entry['type'] == 'birthday':
                # Update birthday for next year
                date = datetime.fromtimestamp(entry['time'])
                try:
                    next_birthday = date.replace(year=datetime.now().year + 1)
                except ValueError:  # Handle Feb 29 for non-leap years
                    next_birthday = date.replace(year=datetime.now().year + 1, day=28)
                entry['time'] = int(next_birthday.timestamp())
                updated_data.append(entry)

            elif entry['type'] == 'poll_result':
                # Mark poll result as past
                # entry['snooze'] = "past"
                # Do not append to updated_data, effectively removing it
                continue

        else:
            # Keep future events as-is
            updated_data.append(entry)

    # Save updated events back to the file
    json_write(updated_data, "Events")
    if event_list:
        # Separate logic for birthdays and other events
        birthday_events = [event for event in event_list if event['type'] == 'birthday']
        other_events = [event for event in event_list if event['type'] != 'birthday']
        
        description = ""
        
        # Handle birthday events
        if birthday_events:
            birthday_messages = []
            for i, birthday in enumerate(birthday_events, 1):
                mentions = ' '.join(f'<@{mention}>' for mention in birthday.get('mention', []))
                birthday_time = int(datetime.fromtimestamp(birthday['time']).replace(year=current_year).timestamp())
                birthday_message = (
                    f"**Happy Birthday {birthday['title']}!**\n"
                    f"<t:{birthday_time}:D>\n"
                    f"{bDay_haiku()}\n"
                    f"{mentions}"
                )
                birthday_messages.append(birthday_message)
                logger.info(f"Birthday message created for: {birthday['title']}")
            
            description += "🎂 **Birthdays** 🎂\n\n" + "\n\n".join(birthday_messages) + "\n\n"
        
        # Handle other events
        if other_events:
            for i, event in enumerate(other_events, 1):
                mentions = ' '.join(f'<@{mention}>' for mention in event.get('mention', []))
                event_time = int(event['time'])
                description += (
                    f"**{i}. {event['title']}**\n"
                    f"<t:{event_time}:F>\n"
                    f"{event['desc']}\n"
                    f"{mentions}\n\n"
                )
        
        if description:
            logger.info(f"Created event message for: {[e['title'] for e in event_list]}")
            return Embed(title="📅 Upcoming Events!", description=description.strip(), color=Color.green())
    
    return None

def bDay_haiku():
    Haiku_list = ['May this day be filled\nwith wonder and surprises.\nBut only good ones.',
                  'Hope you\'re surrounded\nby people and things you love\non your special day.',
                  'It is your birthday!\nDrop everything and have cake.\nYou don\'t have to share.',
                  'Wishing you the best\non your 80th birthday.\nDid I get that right?',
                  'Years may come and go\nbut our friends and memories...\nwhat was I saying?',
                  'Wow, it\'s your birthday\nso let the wild rumpus start!\nThe boys can clean up.',
                  'Facebook is saying\nit is your birthday today.\nAnd they wouldn\'t lie.',
                  'So it\'s your bithday.\nThat reminds me of a joke\nabout old people.',
                  'Pause and reflect as\nWe take time to celebrate\nThe day of your birth.',
                  'So, it\'s your birthday!\nMake sure you do something fun.\nYou won\'t feel so old.',
                  'Happiest Birthday!\nI would offer to sing, but -\nnobody wants that.',
                  'Today is the day\nwe celebrate our dear friend.\nAt least for a while.',
                  'I would sing for you\nbut the Birthday Song is still\nunder copyright.',
                  'Hey it\'s your birthday\nOne year older than before\nPlease don\'t break your hip',
                  'One more year passes\nI\'m running out of ideas\nfor birthday haikus',
                  'Only moments left\nTo wish you happy birthday!\nI did not forget!',
                  'Birthday wishes made to you\nThis is your gift by the way\nSo enjoy it now',
                  'It is your birthday,\nYou probably will eat cake,\nwith a fork or spoon.',
                  'You\'re an awesome dude..\nHave an awesome day to match!\nBut drink a lot too!',
                  'Have a great birthday\nThis dude freaking rocks a lot\nEnjoy your day today!']
    return Haiku_list[random.randint(0, len(Haiku_list) - 1)]

def next_event_delta()->int:
    '''returns the seconds untill the closest snooze. returns None if there are no events'''
    data = json_read("Events")
    if len(data) == 0:
        return None
    
    min_time = None
    current_time = int(time.time())

    for entry in data:
        less_time = 0
        match entry['snooze']:
            case 'week':
                less_time = 604800
            case 'day':
                less_time = 86400
            case 'hour':
                less_time = 3600
        delta = (entry['time'] - less_time - current_time)
        if min_time is None or (min_time > delta and entry['snooze'] != 'past'):
            min_time = delta
    return min_time if min_time and min_time > 0 else None

def convert_seconds(seconds):
    days = seconds // 86400  # 1 day = 86400 seconds
    hours = (seconds % 86400) // 3600  # 1 hour = 3600 seconds
    return days, hours