#!/usr/bin/python3

import discord
import logging
import sys

from src.bot import Bot

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
)


def main():
    try:
        with open(".token", "r") as f:
            token = f.read().strip()
    except FileNotFoundError:
        logging.error(
            ".token file not found. Please provide your Discord bot token in a .token file."
        )
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to read .token file: {e}")
        sys.exit(1)

    logging.info("Starting bot...")

    intents = discord.Intents.default()
    intents.message_content = True
    intents.messages = True
    bot = Bot(intents=intents)
    try:
        bot.run(token)
    except Exception as e:
        logging.error(f"Bot encountered an error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
