import logging

from . import model as messagebox_model
from ..game import model as game_model
from ..game import controller as game_controller

from sqlalchemy.orm import Session
from discord import DMChannel
from discord.ext import commands
from sqlalchemy import Engine, select

from typing import Optional

class DirectMessage(commands.Cog):
    """Cog containing DM related commands."""

    def __init__(self,  engine: Engine) -> None:
        self.engine = engine

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("DirectMessage cog loaded")

    def message_base(self, ctx: commands.Context, message_prop: str, game_id: Optional[int] = None, message : Optional[str] = None) -> Optional[str]:
        try:
        # Check if command is used in DMs
            if not isinstance(ctx.channel, DMChannel):
                # Return quietly
                return
            
            if not message:
                return "Provide a win-message"

            with Session(self.engine) as session:

                if game_id is None:
                    game = session.query(game_model.Game).order_by(game_model.Game.game_id.desc()).first()
                else:
                    game = session.query(game_model.Game).filter_by(game_id=game_id).first()
                if not game:
                    return "No game found."

                player = session.get(game_model.Player, ctx.author.id)
                if not player:
                    return f"Player is not part of game"
                messagebox = session.query(messagebox_model.MessageBox).filter_by(game_id=game.game_id, player_id=player.player_id).first()

                if not messagebox:
                    messagebox = messagebox_model.MessageBox(game_id=game.game_id, player_id=player.player_id)
                setattr(messagebox, message_prop, message)
                session.add(messagebox)
                session.commit()
                return f"You set the following win message: '{message}'."
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            return f"Error occurred"

    @commands.command()
    async def win_message(self, ctx: commands.Context, game_id: Optional[int] = None, *, message : Optional[str] = None) -> None:
        ret = self.message_base(ctx, "win_message", game_id, message)
        if ret:
            await ctx.send(ret)


    @commands.command()
    async def lose_message(self, ctx: commands.Context, game_id: Optional[int] = None, *, message : Optional[str] = None) -> None:
        ret = self.message_base(ctx, "lose_message", game_id, message)
        if ret:
            await ctx.send(ret)
