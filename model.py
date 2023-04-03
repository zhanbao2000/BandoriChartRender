from enum import Enum
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


class BPM(BaseModel):
    type: Literal[NoteType.BPM] = NoteType.BPM
    bpm: int
    beat: float


class System(BaseModel):
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


class Long(BaseModel):
    type: Literal[NoteType.Long] = NoteType.Long
    connections: list[Connection]


class Directional(BaseModel):
    type: Literal[NoteType.Directional] = NoteType.Directional
    beat: float
    lane: int
    direction: Direction
    width: int


class Slide(BaseModel):
    type: Literal[NoteType.Slide] = NoteType.Slide
    connections: list[Connection]


NoteBase = Annotated[Union[BPM, System, Single, Long, Directional, Slide], Field(discriminator='type')]


class Chart(BaseModel):
    __root__: list[NoteBase]


class Content(BaseModel):
    data: Optional[str] = None
    type: str


class Author(BaseModel):
    username: str
    nickname: Optional[str]
    titles: Optional[str]


class Tag(BaseModel):
    type: str
    data: str


class Song(BaseModel):
    type: str
    audio: str
    cover: str


class Post(BaseModel):
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


class UserPost(BaseModel):
    result: bool
    post: Post
