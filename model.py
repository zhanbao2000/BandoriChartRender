import datetime
from enum import Enum, IntEnum
from typing import Optional, Annotated, Union, Literal

from pydantic import BaseModel, Field


class Connection(BaseModel):
    lane: float
    beat: float
    hidden: Optional[bool] = None
    flick: Optional[bool] = None
    charge: Optional[bool] = None
    skill: Optional[bool] = None


class NoteType(str, Enum):
    BPM = 'BPM'
    System = 'System'
    Single = 'Single'
    Long = 'Long'
    Directional = 'Directional'
    Slide = 'Slide'


class Direction(str, Enum):
    Left = 'Left'
    Right = 'Right'


class DifficultyInt(IntEnum):
    Easy = 0
    Normal = 1
    Hard = 2
    Expert = 3
    Special = 4


class Language(IntEnum):
    Japanese = 0
    English = 1
    ChineseTraditional = 2
    ChineseSimplified = 3
    Korean = 4


class BPM(BaseModel):
    type: Literal[NoteType.BPM] = NoteType.BPM
    bpm: int
    beat: float


class Command(BaseModel):
    type: Literal[NoteType.System] = NoteType.System
    data: str
    beat: float


class Single(BaseModel):
    type: Literal[NoteType.Single] = NoteType.Single
    lane: int
    beat: float
    skill: Optional[bool] = None
    flick: Optional[bool] = None
    charge: Optional[bool] = None


class Directional(BaseModel):
    type: Literal[NoteType.Directional] = NoteType.Directional
    beat: float
    lane: int
    direction: Direction
    width: int


class Slide(BaseModel):
    type: Literal[NoteType.Slide, NoteType.Long]
    connections: list[Connection]


NoteBase = Annotated[Union[BPM, Command, Single, Directional, Slide], Field(discriminator='type')]
LaneLocated = Union[Single, Connection, Directional]


class ChartMeta(BaseModel):
    id: int  # song_id or post_id
    title: str
    level: int
    difficulty: Optional[DifficultyInt]
    release: datetime.datetime
    is_official: bool
    total_notes: Optional[int] = None  # only for official
    artist: Optional[str] = None  # band or singer
    chart_designer: Optional[str] = None  # only for user post
    lyricist: Optional[str] = None  # only for official
    composer: Optional[str] = None  # only for official
    arranger: Optional[str] = None  # only for official


class Chart(BaseModel):
    __root__: list[NoteBase]


class UserPost(BaseModel):
    class Post(BaseModel):
        class Content(BaseModel):
            data: Optional[str] = None
            type: str

        class Author(BaseModel):
            class Title(BaseModel):
                id: int
                type: str
                server: int

            username: str
            nickname: Optional[str]
            titles: Optional[list[Title]]

        class Tag(BaseModel):
            type: str
            data: str

        class Song(BaseModel):
            type: str
            audio: str
            cover: str

        categoryName: str
        categoryId: str
        title: str
        song: Song
        artists: str
        diff: int
        level: int
        chart: Chart
        content: list[Content]
        time: int
        author: Author
        likes: int
        liked: bool
        tags: list[Tag]

    result: bool
    post: Post


class BestdoriSongMeta(BaseModel):
    """
    https://bestdori.com/api/songs/359.json
    copid from package bestdori
    """

    class Tag(str, Enum):
        Normal = 'normal'
        Anime = 'anime'
        TieUp = 'tie_up'

    class BPM(BaseModel):
        bpm: float
        start: float
        end: float

    class Achievement(BaseModel):
        musicId: int  # 359
        achievementType: str  # "score_rank_b"
        rewardType: str  # "practice_ticket"
        rewardId: Optional[int]  # 2
        quantity: int  # 1

    class Difficulty(BaseModel):
        class MultiLiveScoreMap(BaseModel):
            musicId: int  # 359
            musicDifficulty: str  # "easy"
            multiLiveDifficultyId: int  # 2001
            multiLiveDifficultyType: str  # "daredemo"
            scoreS: int  # 3321000
            scoreA: int  # 2214000
            scoreB: int  # 1107000
            scoreC: int  # 184500
            scoreSS: int  # 4428000
            scoreSSS: Optional[int]  # 0

        playLevel: int  # 11
        multiLiveScoreMap: dict[int, MultiLiveScoreMap]
        notesQuantity: int  # 1000
        scoreC: int  # 36900
        scoreB: int  # 221400
        scoreA: int  # 442800
        scoreS: int  # 664200
        scoreSS: int  # 885600

    bgmId: str  # "bgm359"
    bgmFile: str  # "359_hell_or_hell"
    tag: Tag  # "normal"
    bandId: int  # 18
    achievements: list[Achievement]
    jacketImage: list[str]  # ["359_hell_or_hell"]
    seq: int  # 712
    musicTitle: list[Optional[str]]  # ["HELL! or HELL?", ...]
    lyricist: list[Optional[str]]  # ["織田あすか（Elements Garden）", ...]
    composer: list[Optional[str]]  # ["菊田大介（Elements Garden）", ...]
    arranger: list[Optional[str]]  # ["菊田大介（Elements Garden）", ...]
    howToGet: list[Optional[str]]  # ["楽曲プレゼントを受け取る", ...]
    publishedAt: list[Optional[datetime.datetime]]  # ["1632031200000", ...]
    closedAt: list[Optional[datetime.datetime]]  # ["4121982000000", ...]
    difficulty: dict[DifficultyInt, Difficulty]
    length: float  # 108.504
    notes: dict[DifficultyInt, int]  # {"0": 196, "1": 338, "2": 598, "3": 999, "4": 1196}
    bpm: dict[DifficultyInt, list[BPM]]


class Bands(BaseModel):
    """
    https://bestdori.com/api/bands/all.1.json
    copid from package bestdori
    """

    class BandName(BaseModel):
        bandName: list[Optional[str]]

    __root__: dict[int, BandName]
