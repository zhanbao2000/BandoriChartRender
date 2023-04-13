from io import BytesIO
from math import ceil
from pathlib import Path
from typing import Optional

from pydantic import parse_obj_as

from .model import Chart, UserPost, BestdoriSongMeta, Bands, Language, ChartMeta, DifficultyInt
from .utils import get_client

difficulty_literal = ['easy', 'normal', 'hard', 'expert', 'special']
assets = Path(__file__).parent / 'assets'
cached_songs: dict[int, BestdoriSongMeta] = {}  # song_id: song
cached_bands: dict[int, str] = {}  # band_id: band_name


class InGameResourceManager(object):
    background = assets / 'liveBG_normal.png'
    default_jacket = assets / 'default_jacket.png'

    normal = assets / 'note_normal_3.png'
    normal_16 = assets / 'note_normal_16_3.png'
    skill = assets / 'note_skill_3.png'
    long = assets / 'note_long_3.png'
    connection = assets / 'note_slide_among.png'
    flick = assets / 'note_flick_3.png'
    flick_top = assets / 'note_flick_top.png'
    flick_left = assets / 'note_flick_l_3.png'
    flick_right = assets / 'note_flick_r_3.png'
    flick_left_top = assets / 'note_flick_top_l.png'
    flick_right_top = assets / 'note_flick_top_r.png'


class FontResourceMangaer(object):
    font_arial_bd = assets / 'arialbd.ttf'
    font_a_otf_shingopro_medium_2 = assets / 'A-OTF-ShinGoPro-Medium-2.otf'


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


async def get_song_jacket(url: str) -> BytesIO:
    try:
        async with get_client() as client:
            response = await client.get(url)
            response.raise_for_status()
        return BytesIO(response.content)
    except Exception:  # noqa
        with open(InGameResourceManager.default_jacket, 'rb') as f:
            return BytesIO(f.read())


async def get_song_official(song_id: int) -> BestdoriSongMeta:
    if song_id in cached_songs:
        return cached_songs[song_id]

    async with get_client() as client:
        response = await client.get(f'https://bestdori.com/api/songs/{song_id}.json')
        response.raise_for_status()

    cached_songs.update({song_id: parse_obj_as(BestdoriSongMeta, response.json())})
    return cached_songs[song_id]


def get_band_name_from_list(band_name_list: list[str]) -> Optional[str]:
    return (
            band_name_list[Language.Japanese] or
            band_name_list[Language.ChineseSimplified] or
            band_name_list[Language.ChineseTraditional] or
            band_name_list[Language.English] or
            band_name_list[Language.Korean]
    )


async def get_band_official(band_id: int) -> str:
    if band_id in cached_bands:
        return cached_bands[band_id]

    async with get_client() as client:
        response = await client.get('https://bestdori.com/api/bands/all.1.json')
        response.raise_for_status()

    bands = parse_obj_as(Bands, response.json()).__root__
    cached_bands.update({_band_id: get_band_name_from_list(_band_name_list.bandName) for _band_id, _band_name_list in bands.items()})
    return cached_bands[band_id]


def get_song_jacket_url_official(song_id: int, jacket_name: str) -> str:
    jacket_pack_id = ceil(song_id / 10) * 10

    return (f'https://bestdori.com/'
            f'assets/jp/musicjacket/musicjacket{jacket_pack_id}_rip/'
            f'assets-star-forassetbundle-startapp-musicjacket-musicjacket{jacket_pack_id}-{jacket_name}-thumb.png')


async def generate_song_meta_official(meta: BestdoriSongMeta, song_id: int, difficulty: DifficultyInt) -> ChartMeta:
    return ChartMeta(
        id=song_id,
        title=meta.musicTitle[Language.Japanese],
        level=meta.difficulty[difficulty].playLevel,
        difficulty=DifficultyInt(difficulty),
        release=meta.publishedAt[Language.Japanese],
        is_official=True,
        artist=await get_band_official(meta.bandId),
        lyricist=meta.lyricist[Language.Japanese],
        composer=meta.composer[Language.Japanese],
        arranger=meta.arranger[Language.Japanese],
    )


def generate_song_meta_user_post(post: UserPost.Post, post_id: int) -> ChartMeta:
    return ChartMeta(
        id=post_id,
        title=post.title,
        level=post.level,
        release=post.time,
        is_official=False,
        artist=post.artists,
        chart_designer=post.author.nickname or post.author.username,
    )
