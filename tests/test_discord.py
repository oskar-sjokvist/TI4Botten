import discord
import discord.ext.test as dpytest
import pytest
import pytest_asyncio
from bot import Bot

@pytest_asyncio.fixture()
async def bot():
    intents = discord.Intents.default()
    intents.members = True
    intents.messages = True
    intents.message_content = True
    bot = Bot(intents)

    await bot.setup_hook()
    await bot._async_setup_hook()

    dpytest.configure(bot, members=2)

    yield bot
    await dpytest.empty_queue()


@pytest.mark.asyncio
async def test_help(bot):
    await dpytest.message("!hello")
    assert dpytest.verify().message().contains().content("Hello!")

