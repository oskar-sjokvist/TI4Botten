# TI4Botten

A Discord bot for Twilight Imperium 4th Edition, featuring faction randomization and more.

## Features
- Randomly select TI4 factions, optionally filtered by expansion/source
- Discord command interface
- Extensible bot architecture

## Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/fsharpasharp/TI4Botten.git
   cd TI4Botten
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Add your Discord bot token to a file named `.token` in the project root.

## Usage
Run the bot:
```sh
python app.py
```

## Project Structure
- `app.py` — Main entrypoint for the bot
- `src/bot.py` — Bot and command definitions
- `src/factions.py` — Faction logic and data loading
- `tests/` — Test suite

## Contributing
Pull requests and issues are welcome!