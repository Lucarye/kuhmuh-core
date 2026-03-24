from .command.command_cog import GroupFinderCommandCog


async def setup(bot):
    await bot.add_cog(GroupFinderCommandCog(bot))