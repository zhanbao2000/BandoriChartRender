from typing import Union

from .model import DifficultyInt
from .render import Render
from .resource import (
    get_chart_official,
    get_chart_user_post,
    get_song_jacket_url_official,
    get_song_jacket,
    get_song_official,
    generate_song_meta_official,
    generate_song_meta_user_post
)


async def render_chart_official(song_id: int, difficulty: Union[DifficultyInt, int]) -> Render:
    chart = await get_chart_official(song_id, difficulty)
    song = await get_song_official(song_id)
    jacket = await get_song_jacket(get_song_jacket_url_official(song_id, song.jacketImage[0]))
    meta = await generate_song_meta_official(song, song_id, difficulty)

    return Render(chart, meta, jacket)


async def render_chart_user_post(post_id: int) -> Render:
    post = (await get_chart_user_post(post_id)).post
    chart = post.chart
    jacket = await get_song_jacket(post.song.cover)
    meta = generate_song_meta_user_post(post, post_id)

    return Render(chart, meta, jacket)


__all__ = [
    'render_chart_official',
    'render_chart_user_post'
]
