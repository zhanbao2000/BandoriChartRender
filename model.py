from typing import Optional

from pydantic import BaseModel


class Connection(BaseModel):
    lane: float
    beat: float
    hidden: Optional[bool] = None
    flick: Optional[bool] = None
    charge: Optional[bool] = None
    skill: Optional[bool] = None


class Note(BaseModel):
    type: str
    bpm: Optional[int] = None
    beat: Optional[float] = None
    data: Optional[str] = None
    connections: Optional[list[Connection]] = None
    lane: Optional[int] = None
    direction: Optional[str] = None
    width: Optional[int] = None
    skill: Optional[bool] = None
    flick: Optional[bool] = None
    charge: Optional[bool] = None


class Chart(BaseModel):
    __root__: list[Note]


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
