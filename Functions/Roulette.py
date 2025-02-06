
import re,json,requests,random,urllib.parse

from nextcord import Interaction,embeds,ui,TextInputStyle,SelectOption,Color
from nextcord.ui import View

from quickchart import QuickChart

from Functions.Search import NyaaSearchView
from Functions.LogsJson import json_read,json_write,logger

MAXSTRINGLEN = 12
#regioon views

class StringInputModal(ui.Modal):
    def __init__(self, selected_type, data, file_path="roulette_options"):
        super().__init__(title="Edit Roulette Wheel")
        self.selected_type = selected_type
        self.data = data
        self.file_path = file_path

        # Wheel name input
        self.name_input = ui.TextInput(
            label="Wheel Name",
            placeholder="Enter wheel name" if selected_type == "Add New Wheel" else selected_type,
            default_value=selected_type if selected_type != "Add New Wheel" else "",
            min_length=1,
            max_length=100,
        )
        self.add_item(self.name_input)

        # Options input
        self.options_input = ui.TextInput(
            label="Wheel Options",
            placeholder="Enter options (comma-separated)",
            default_value=self.data.get(selected_type, {}).get("options", "") if selected_type != "Add New Wheel" else "",
            min_length=1,
            max_length=1000,
            style=TextInputStyle.paragraph,
        )
        self.add_item(self.options_input)

    async def callback(self, interaction: Interaction):
        # Validate inputs
        wheel_name = self.name_input.value.strip().lower()
        options_input = self.options_input.value.strip()

        # Check for valid inputs
        if not wheel_name:
            await interaction.response.send_message("Wheel name cannot be empty.", ephemeral=True)
            return

        if "," not in options_input:
            await interaction.response.send_message("Options must be comma-separated.", ephemeral=True)
            return

        # Parse input options
        input_options = [opt.strip() for opt in options_input.split(",")]

        # Retrieve existing wheel data or initialize new data
        existing_wheel = self.data.get(self.selected_type, {})
        existing_options = existing_wheel.get("options", "").split(", ")
        existing_episodes = existing_wheel.get("episodes", [])

        # Normalize existing options for comparison
        normalized_existing = {re.sub(r'\|\d+$', '', opt): i for i, opt in enumerate(existing_options)}

        updated_episodes = []
        updated_options = []

        # Process each input option
        for opt in input_options:
            match = re.match(r'^(.*?)(\|\d+)?$', opt)
            base_opt = match.group(1).strip()  # Option without the amount number
            # provided_episode = int(match.group(2)[1:]) if match.group(2) else None  # Extract provided amount count

            if base_opt in normalized_existing:
                # Option exists: retain its original episode count
                existing_index = normalized_existing[base_opt]
                updated_episodes.append(existing_episodes[existing_index])
            else:
                # Option is new: add it with an episode count of 1
                updated_episodes.append(1)

            # Always append the input option as-is to `options`
            updated_options.append(opt)

        # Update wheel data
        if self.selected_type != "Add New Wheel" and self.selected_type != wheel_name:
            # If renaming, remove old key
            self.data.pop(self.selected_type, None)

        # Create or update the wheel entry
        self.data[wheel_name] = {
            "options": ", ".join(updated_options),
            "episodes": updated_episodes
        }

        # Write updated data to file
        try:
            json_write(self.data, self.file_path)
            logger.info(f"wheel was edited with options: {updated_options} and episodes: {updated_episodes}")
            await interaction.response.send_message(
                f"Successfully {'updated' if self.selected_type != 'Add New Wheel' else 'added'} wheel '{wheel_name}'", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"Error saving wheel: {str(e)}", ephemeral=True)

class StringInputView(ui.View):
    def __init__(self, edit):
        super().__init__()  # Add explicit timeout
        self.edit = edit
        self.file_path = "roulette_options"
        try:
            self.data = json_read(self.file_path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.data = {}
            print(f"Error loading JSON: {e}")

        self.options = [
            SelectOption(label=key, description=value["options"] if isinstance(value, dict) else "")
            for key, value in self.data.items()
        ]
        if edit:
            self.options.insert(0, SelectOption(label="Add New Wheel", description="Your new rule here :)"))
            
        self.type_input = ui.Select(
            placeholder="Select an option",
            options=self.options
        )
        self.type_input.callback = self.on_type_input_change
        self.add_item(self.type_input)

    async def on_type_input_change(self, interaction: Interaction):
        try:
            selected_type = self.type_input.values[0]
            
            # Disable the select menu to prevent multiple selections
            self.type_input.disabled = True
            self.type_input.placeholder = selected_type
            await interaction.message.edit(view=self)

            if self.edit:
                modal = StringInputModal(selected_type, self.data, self.file_path)
                logger.info(f"roullete wheel: {selected_type} was chosen to edit.")
                await interaction.response.send_modal(modal)
            else:
                # Handle roulette logic in a more controlled way
                logger.info(f"roullete wheel: {selected_type} was chosen to run.")
                await self.handle_roulette(interaction, selected_type)
                
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    async def handle_roulette(self, interaction: Interaction, selected_type):
        try:
            # Defer the response immediately
            await interaction.response.defer()

            entry = self.data.get(selected_type, {})
            options_raw = entry.get("options", "")
            episodes = entry.get("episodes", [])

            options = options_raw.split(", ")
            options_with_episodes = [
                f"{option.split('|')[0]} (episode {episodes[index]})|{option.split('|')[1]}"
                for index, option in enumerate(options)
            ]

            # call roulette function
            roulette_message = await roulette(interaction, choices=", ".join(options_with_episodes))

            if roulette_message and roulette_message.embeds:
                result = roulette_message.embeds[0].title.split(' (')[0]
                chosen_index = [s.split('|')[0] for s in options].index(result.lower())

                if chosen_index is not None:
                    episodes[chosen_index] += 1
                    self.data[selected_type]["episodes"] = episodes
                    self.data[selected_type]['options']=", ".join([
                        f"{option.split('|')[0]}|1" if index == chosen_index else f"{option.split('|')[0]}|{int(option.split('|')[1]) + 1}" 
                        for index, option in enumerate(options)
                    ])
                    json_write(self.data, self.file_path)
                    
                    await interaction.followup.send(
                        f"The updated options are: {self.data[selected_type]['options']}", 
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send("Couldn't match the result with an option.", ephemeral=True)
            else:
                await interaction.followup.send("Couldn't determine the roulette result.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"An error occurred while running the roulette: {str(e)}", ephemeral=True)

#region commands
async def roulette(interaction: Interaction, choices: str):
    """random option chooser from str sperated by commas duplicate options with copies after |

    Parameters
    ----------
    inter: Interaction
        The interaction object
    choices: str
        list the options with a comma inbetween each choice and | to add multiple of a choice
    """
    if ',' in choices:
        opt = choices.split(",")
        opt = list(map(to_format, filter(None, opt)))
        opt = multiple_list(opt)
        if len(opt) > 1:
            response = requests.get(f"https://www.randomnumberapi.com/api/v1.0/random?min=0&max={len(opt)}&count=1")
            Rnum = json.loads(response.content)[0]
            choosen = (Rnum + random.randint(0, len(opt) - 1))%len(opt)
            congratz:str = opt[choosen]#random.randint(0, len(opt) - 1)
            percent = (opt.count(congratz) / len(opt)) * 100
            opt = ["👑" + congratz if item == congratz else item for item in opt]
            strings , freq = count_unique_strings(opt)
            img_url=Pie_Chart(strings,freq,congratz)#f"https://quickchart.io/chart/render/sf-e4e024c4-0794-400c-b59b-a342db077611?title=Rolling%20for%20{interaction.user.display_name}&labels={','.join(strings)}&data1={','.join(freq)}"#Pie_Chart(strings,freq)#f"https://quickchart.io/chart/render/zm-cd282127-2f35-4797-8a82-0dbc463a95fc?title=Rolling%20for%20{interaction.user.display_name}&labels={','.join(strings)}&data1={','.join(freq)}"   
            embed = embeds.Embed(
                title=congratz,
                description=f"with a chance of {percent}%",
                color=interaction.user.color or Color.random()
            ).set_image(url=img_url)
            view = View()
            if len([s for s in opt if ' (episode ' not in s.lower()]) == 0 :#if all options have (episode 
                match = re.search(r'\(episode (\d+)\)', opt[choosen].lower())
                epi = str(match.group(1)).zfill(2) if match else ""
                view = NyaaSearchView(congratz.split(' (')[0]+f" {epi}",sort="seeders")
            logger.info(f"ran roulette with options: {choices}, and {congratz} was chosen.")
            message = await interaction.send(f"Ccongraawrasffisakgfjpgasdtulations! The Chosen option is:",
                                                    embed=embed,view=view)
            view.message = message
            return message
            
    await interaction.send("I kinda didn't find any commas in your choices.")

#region functions

def count_unique_strings(input_list):
    """
    Count the frequency of unique strings in a list.
    
    Args:
        input_list (list): List of strings to analyze
        
    Returns:
        tuple: (unique_strings, frequencies) where:
            - unique_strings is a list of unique strings
            - frequencies is a list of corresponding counts
    """
    # Create a dictionary to store counts
    count_dict = {}
    
    # Count occurrences of each string
    for item in input_list:
        if item in count_dict:
            count_dict[item] += 1
        else:
            count_dict[item] = 1
    
    # Create separate lists for strings and their counts
    unique_strings = list(count_dict.keys())
    frequencies = [count_dict[s] for s in unique_strings]
    return unique_strings, frequencies

def to_format(words: str):
    return words.strip().title()

def multiple_list(lst: list) -> list:
    expand_list = []
    for i in lst:
        # Split the string on "|" to separate the value and multiplier
        parts = i.split('|')
        value = parts[0].strip()  # Extract the main value, trim whitespace
        
        # Check if there's a multiplier and it's valid
        if len(parts) == 2 and parts[1].strip().isnumeric():
            amount = int(parts[1].strip())
            if amount > 0:
                expand_list.extend([value] * amount)  # Duplicate `value` `amount` times
                continue
        
        # If no valid multiplier, just append the original item
        expand_list.append(value)
        
    return expand_list

def add_newlines_at_spaces(input_string, max_chars_per_line):
    """
    Add a newline character at the nearest space after every few characters in a single string.

    Parameters:
    input_string (str): The string to process.
    max_chars_per_line (int): The maximum number of characters per line before adding a newline.

    Returns:
    str: The processed string with newlines.
    """
    words = input_string.split()
    lines = []
    current_line = ""

    for word in words:
        # Check if adding the word would exceed the limit
        if len(current_line) + len(word) + 1 > max_chars_per_line:
            lines.append(current_line.strip())  # Add the current line to the list
            current_line = word  # Start a new line with the current word
        else:
            # Add the word to the current line
            current_line += (" " if current_line else "") + word

    # Add the last line if not empty
    if current_line:
        lines.append(current_line.strip())

    return "\n".join(lines)

def process_list_of_strings(strings, max_chars_per_line):
    """
    Process each string in the list to add newlines at spaces after a specified number of characters.

    Parameters:
    strings (list): A list of strings to process.
    max_chars_per_line (int): The maximum number of characters per line before adding a newline.

    Returns:
    list: A list of processed strings with newlines.
    """
    return [add_newlines_at_spaces(s, max_chars_per_line) for s in strings]

def Pie_Chart(labels, data, winner):
    qc = QuickChart()
    qc.background_color = "#313338"
    qc.width = 500
    qc.height = 300
    qc.version = '2'
    
    # Create the base config as a dictionary
    qc_config_string = """{
  "type": "outlabeledPie",
  "data": {
    "labels": ["ONE", "TWO", "THREE", "FOUR", "FIVE"],
    "datasets": [{
        "backgroundColor": ["#FF3784", "#36A2EB", "#4BC0C0", "#F77825", "#9966FF"],
        "borderColor": "#FFFFFF",
        "borderWidth": 2,
        "data": [1, 2, 3, 4, 5]
    }]
  },
  "options": {
    "plugins": {
      "legend": false,
      "outlabels": {
        "text": "%l (%v, %p)",
        "color": "white",
        "shadowColor": "white",
        "shadowBlur": 6,
        "stretch": 35,
        "font": {
          "resizable": true,
          "minSize": 18,
          "maxSize": 25,
          "multiLine": true
        }
      }
    }
  }
}
"""
    # Parse the JSON string into a dictionary
    config_dict = json.loads(qc_config_string)
    
    # Update the labels and data in the chart
    config_dict['data']['labels'] = process_list_of_strings(labels,MAXSTRINGLEN)
    config_dict['data']['datasets'][0]['data'] = data

    # Update the color of the winner's slice
    pallete = ["#FF3784", "#36A2EB", "#4BC0C0", "#F77825", "#9966FF"]
    wcolor = pallete[labels.index("👑" + winner)]

    # Set the title and its color (now done in the JSON config)
    config_dict['options']['plugins']['title'] = {
        "display": True,
        "text": f"Winner: {winner}",
        "color": wcolor,
        "font": {
            "size": 24,
            "weight": "bold"
        }
    }

    # Convert the updated dictionary back to a compact JSON string
    updated_config_string = json.dumps(config_dict, separators=(',', ':'))

    # Now, append the title text as a URL query parameter (so it can dynamically change)
    base_url = "https://quickchart.io/chart?"
    url_with_title = f"{base_url}c={urllib.parse.quote_plus(updated_config_string)}&title={urllib.parse.quote(winner)}"

    return url_with_title

# def Pie_Chart(labels,data,winner):
#     # def update_labels_and_data(config, new_labels, new_data):
#     #     config['data']['labels'] = new_labels
#     #     config['data']['datasets'][0]['data'] = new_data
#     #     return config
#     qc = QuickChart()
#     qc.background_color= "#313338"
#     qc.width = 500
#     qc.height = 300
#     qc.version = '2'
    
#     # Create the config as a dictionary
#     qc_config_string = """{
#   "type": "outlabeledPie",
#   "data": {
#     "labels": ["ONE", "TWO", "THREE", "FOUR", "FIVE"],
#     "datasets": [{
#         "backgroundColor": ["#FF3784", "#36A2EB", "#4BC0C0", "#F77825", "#9966FF"],
#         "borderColor": "#FFFFFF",
#         "borderWidth": 2,
#         "data": [1, 2, 3, 4, 5]
#     }]
#   },
#   "options": {
#     "plugins": {
#       "title": {
#         "display": true,
#         "text": "Winner: ONE",  
#         "color": "#FFFFFF",  
#         "font": {
#           "size": 20
#         }
#       },
#       "backgroundImageUrl": "https://cdn.pixabay.com/photo/2017/08/30/01/05/milky-way-2695569__340.jpg",
#       "legend": false,
#       "outlabels": {
#         "text": "%l (%v, %p)",
#         "color": "white",
#         "shadowColor": "white",
#         "shadowBlur": 6,
#         "stretch": 35,
#         "font": {
#           "resizable": true,
#           "minSize": 18,
#           "maxSize": 25
#         }
#       }
#     }
#   }
# }
# """

#     # Parse the JSON string into a dictionary
#     config_dict = json.loads(qc_config_string)
#     pallete = ["#FF3784", "#36A2EB", "#4BC0C0", "#F77825", "#9966FF"]
#     wcolor = pallete[labels.index("👑" +winner)]
#     # Update the labels and data in the dictionary
#     config_dict['data']['labels'] = labels
#     config_dict['data']['datasets'][0]['data'] = data
#     # config_dict['options']['plugins']['title']['text'] ="Winner: "+ winner
#     # config_dict['options']['plugins']['title']['color']= wcolor
#     # Convert the updated dictionary back to a JSON string
#     updated_config_string = json.dumps(config_dict, indent=2)
#     return "https://quickchart.io/chart?c=" + urllib.parse.quote_plus(updated_config_string)