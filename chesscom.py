import aiohttp


class ChessComError(Exception):
    def __init__(self, status_code: int):
        self.message = f"Chess.com Request failed with status code: {status_code}"
        self.status_code = status_code
        super().__init__(self.message)


async def get_player_stats(username: str) -> dict:
    username = username.lower()
    async with aiohttp.ClientSession() as session:
        url = f"https://api.chess.com/pub/player/{username}/stats"
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise(ChessComError(response.status))


async def get_player_profile(username: str) -> dict:
    username = username.lower()
    async with aiohttp.ClientSession() as session:
        url = f"https://api.chess.com/pub/player/{username}"
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise(ChessComError(response.status))
