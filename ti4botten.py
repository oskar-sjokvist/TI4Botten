#!/usr/bin/python3

import discord
import logging
import sys

from bot import Bot

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
)

def main():
    try:
        with open('.token', 'r') as f:
            token = f.read().strip()
        logging.info("Starting bot...")

        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        bot = Bot(intents=intents)
        bot.run(token)

    except Exception as e:
        logging.error(f"Error bot: {e}")

if __name__ == "__main__":
    main()
