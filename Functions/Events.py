import operator,time,random,asyncio

from nextcord import Interaction,Embed,Color

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

async def birthdays(inter: Interaction):
    data = json_read("Events")
    birthday_events = [event for event in data if event['type'] == 'birthday']
    
    if not birthday_events:
        await inter.response.send_message("No birthdays found in the events list.", ephemeral=True)
        return

    # Convert Unix timestamps to datetime objects and sort
    birthday_list = []
    for event in birthday_events:
        event_date = datetime.fromtimestamp(event['time'])
        birthday_list.append((event_date, event['title']))

    birthday_list.sort(key=operator.itemgetter(0))

    # Create the embed
    embed = Embed(title="🎂Upcoming Birthdays:", color=Color.blue())

    # Create the description
    description = ""
    i=1
    for date, name in birthday_list:
        description += f"**{i}.{name}** - <t:{int(date.timestamp())}:D> (<t:{int(date.timestamp())}:R>) \n\n"
        i+=1

    embed.description = description.strip()

    await inter.response.send_message(embed=embed)

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