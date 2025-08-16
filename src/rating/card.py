import discord

def stats_card(name: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"{name} profile",
        description="",
        color=discord.Color.blue()
    )

    embed.set_author(name="Jan's Bot", icon_url=ctx.author.avatar.url)
    embed.add_field(name="Field 1", value="Some information here", inline=True)
    embed.add_field(name="Field 2", value="More info, inline field", inline=True)
    embed.add_field(name="Field 3", value="Another inline field", inline=True)
    return embed
    embed.set_footer(text="This is the footer text")

