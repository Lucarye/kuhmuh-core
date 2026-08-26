from .logging_cog import LoggingCog


async def setup(bot):
    await bot.add_cog(LoggingCog(bot))