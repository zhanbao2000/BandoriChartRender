from pydantic import parse_obj_as

from .model import Chart, UserPost
from .utils import get_client

difficulty_literal = ['easy', 'normal', 'hard', 'expert', 'special']


async def get_chart_official(song_id: int, difficulty: int) -> Chart:
    async with get_client() as client:
        response = await client.get(f'https://bestdori.com/api/charts/{song_id}/{difficulty_literal[difficulty]}.json')
        response.raise_for_status()
        return parse_obj_as(Chart, response.json())


async def get_chart_user_post(post_id: int) -> UserPost:
    async with get_client() as client:
        response = await client.get(f'https://bestdori.com/api/post/details?id={post_id}')
        response.raise_for_status()
        return UserPost(**response.json())
