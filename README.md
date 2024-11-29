
# XyBot

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/ "License File")
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/ "Python dwonload")
[![Nextcord](https://img.shields.io/badge/Nextcord-v2.6-blue)](https://github.com/nextcord/nextcord)
[![mafic](https://img.shields.io/badge/Mafic-v2.10-purple)](https://github.com/nextcord/nextcord)
[![Lavalink](https://img.shields.io/badge/Lavalink-4.0.8-orange)](https://github.com/lavalink-devs/Lavalink)

__XyBot__ is a custom Discord bot built using [nextcord](https://github.com/nextcord/nextcord) and [mafic](https://github.com/ooliver1/mafic).

This project was created for my personal Discord server but is open for others to explore and learn from—mistakes and all! Whether you're seeking inspiration, troubleshooting tips, or just want to peek at some code, I hope XyBot proves helpful.


### Features

- 🎵 **YouTube Streaming**: Play your favorite music directly from YouTube.
- 📡 **Anime/TV RSS Feeds**: Stay updated with the latest anime and TV releases.
- 🔍 **Nyaa Search**: Find torrents easily using Nyaa's search engine.
- 🎲 **Random Roulette**: A randomizer feature to add excitement to your server.


### Table of Contents
- [Features](#features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
- [Usage](#usage)
- [License](#license)
## Getting started

Follow these steps to set up XyBot:  

- As this is a python bot a python interperter is required which can be found [here](https://www.python.org/downloads/).
- The libraries required can be installed by running `pip install -r requirements.txt`.
- This bot is using a local lavalink. Download the latest verison of Lavalink.jar [here](https://github.com/lavalink-devs/Lavalink/releases).
- Lavalink needs a server configuration as a application.yml. There is an example [here](https://lavalink.dev/configuration/).
- To allow the bot to use youtube a lavalink plugin is needed from [here](https://github.com/lavalink-devs/youtube-source). 
  - Follow the instructions on how to install the puglin there.
- In the default folder there is a .env file, on first run it will be copied to the main directory if not created manually as stated below.

### Prerequisites

1. **Python Interpreter**  
   - Download and install Python from [here](https://www.python.org/downloads/).  

2. **Install Dependencies**  
   - Run the following command to install the required libraries:  
     ```bash  
     pip install -r requirements.txt  
     ```  

3. **Lavalink Setup**  
   - **Download Lavalink**: Get the latest `Lavalink.jar` file from [here](https://github.com/lavalink-devs/Lavalink/releases).  
   - **Configure Lavalink**: Lavalink requires a `application.yml` configuration file. You can find an example configuration [here](https://lavalink.dev/configuration/).  
   - **YouTube Plugin**: To enable YouTube support, download the YouTube source plugin from [here](https://github.com/lavalink-devs/youtube-source) and follow the installation instructions.  

4. **Environment File**  
   - The bot requires a `.env` file for configuration. On the first run, if a `.env` file is not manually created, the bot will copy a default version to the main directory.  

### Environment Variables

Add the following environment variables to your `.env` file:  

- `TOKEN` - Your Discord bot token.  
- `channel_id` - The channel ID for announcements, like birthdays and RSS feeds.  
- `port` - Lavalink server port.  
- `pass` - Lavalink server password.  




## Usage

Here are some commands the bot supports:

| Command                        | Description                                 |
|--------------------------------|---------------------------------------------|
| `/play <url>`                  | Plays music from a YouTube link or a search.|
| `/feed add`                    | Adds a new RSS feed to track.               |
| `/nyaa <term>`                 | Searches Nyaa for the specified term.       |
| `/roulette (option1,option2)`  | Spins the roulette for a random pick.       |

Type `/help` in your Discord server to see all available commands.

## License

This project is licensed under the MIT License. See the [MIT](https://choosealicense.com/licenses/mit/) file for details.  

---

