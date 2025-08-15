import discord
import discord.ext.test as dpytest
import pytest
import pytest_asyncio
from src.bot import Bot


@pytest_asyncio.fixture(autouse=True)
async def bot():
    intents = discord.Intents.default()
    intents.members = True
    intents.messages = True
    intents.message_content = True
    bot = Bot(intents)

    await bot.setup_hook()
    await bot._async_setup_hook()  # setup the loop

    dpytest.configure(bot, members=2)

    yield bot
    await dpytest.empty_queue()


@pytest.mark.asyncio
async def test_help():
    await dpytest.message("!hello")
    assert dpytest.verify().message().contains().content("Hello!")


@pytest.mark.asyncio
async def test_factions():
    await dpytest.message("!factions 3")
    # The response should mention random factions and the number requested
    assert dpytest.verify().message().contains().content("Here are 3 random factions:")
