import discord
from functools import wraps


def is_me(func):
    @wraps(func)
    async def wrapper(*args):
        if args[0].author.id != 325713620879147010:
            return
        await func(*args)
    return wrapper

