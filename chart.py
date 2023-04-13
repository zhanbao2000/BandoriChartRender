from itertools import tee, chain, groupby
from typing import Union, TypeVar, Iterator, Iterable, Optional

from .model import Chart, Slide, LaneLocated, Single, Directional, Connection, BPM, NoteBase, Command

_T = TypeVar('_T', bound=NoteBase)


def get_max_beat(chart: Chart) -> float:
    """Get the max beat of a chart."""
    return max(
        note.connections[-1].beat
        if isinstance(note, Slide)
        else note.beat
        for note in chart.__root__
    )


def get_notes_for_type(chart: Chart, note_type: Union[type[_T], tuple[type[NoteBase], ...]]) -> Iterator[_T]:
    """(Non-recursive) Get all notes of a given type(s)."""
    yield from (note for note in chart.__root__ if isinstance(note, note_type))


def get_all_skill_notes(chart: Chart) -> Iterator[Single]:
    """Get all skill notes."""
    yield from sorted(
        filter(
            lambda note: note.skill,
            chain(
                get_notes_for_type(chart, Single),
                get_endpoints_for_slide(chart)
            )
        ),
        key=lambda note: note.beat
    )


def get_endpoints_for_slide(chart: Chart) -> Iterator[Connection]:
    """Get all endpoints (head or tail) of a slide note."""
    yield from chain.from_iterable(
        (note.connections[0], note.connections[-1])
        for note in get_notes_for_type(chart, Slide)
    )


def is_note_should_black(note: LaneLocated) -> bool:
    """Check if a note should be rendered as black."""
    return note.beat % 0.5 != 0


def is_note_flick(note: LaneLocated) -> bool:
    """Check if a note is a flick note."""
    return note.flick is True


def is_note_skill(note: LaneLocated) -> bool:
    """Check if a note is a skill note."""
    return note.skill is True


def get_note_beat(note: LaneLocated) -> float:
    """Get the beat of a note."""
    return note.beat


def get_fever_command_tuple(command_list: list[Command]) -> tuple[Optional[Command], ...]:
    """Get the fever ready, start and end command from a list of system notes."""
    fever_ready, fever_start, fever_end = None, None, None

    for command in command_list:
        if command.data == 'cmd_fever_ready.wav':
            fever_ready = command
        elif command.data == 'cmd_fever_start.wav':
            fever_start = command
        elif command.data == 'cmd_fever_end.wav':
            fever_end = command

    return fever_ready, fever_start, fever_end


def pairwise(iterable: Iterable[_T]) -> Iterator[tuple[_T, _T]]:
    """pairwise(ABCDEFG) --> AB BC CD DE EF FG. For Python 3.10+, use itertools.pairwise directly."""
    a, b = tee(iterable)
    next(b, None)
    yield from zip(a, b)


def get_grouped_notes_by_beat(chart: Chart) -> Iterator[tuple[float, Iterator[LaneLocated]]]:
    """Group notes if they are on the same beat."""
    notes = chain(
        get_notes_for_type(chart, (Single, Directional)),
        get_endpoints_for_slide(chart)
    )
    yield from groupby(sorted(notes, key=get_note_beat), get_note_beat)


def get_time_elapsed(bpms: list[BPM], beat: float) -> float:
    """Get the elapsed time of a beat."""
    current_time = 0.0
    current_bpm = bpms[0].bpm
    current_beat = 0.0

    for bpm in bpms:
        if bpm.beat > beat:
            break

        current_time += (bpm.beat - current_beat) * 60 / current_bpm
        current_bpm = bpm.bpm
        current_beat = bpm.beat

    current_time += (beat - current_beat) * 60 / current_bpm

    return current_time


def get_beat_elapsed(bpms: list[BPM], time: float) -> float:
    """Get the elapsed beat of a time."""
    current_time = 0.0
    current_bpm = bpms[0].bpm
    current_beat = 0.0

    for bpm in bpms:
        if current_time + (bpm.beat - current_beat) * 60 / current_bpm > time:
            break

        current_time += (bpm.beat - current_beat) * 60 / current_bpm
        current_bpm = bpm.bpm
        current_beat = bpm.beat

    current_beat += (time - current_time) * current_bpm / 60

    return current_beat


def get_combo_before(beat: float, note_list_single_directional: list[Union[Single, Directional]], note_list_slide: list[Slide]) -> int:
    """Get the total combo before given beat."""
    result = 0

    # Single, Directional
    result += sum(
        single_or_directional.beat < beat
        for single_or_directional in note_list_single_directional
    )
    # Slide
    result += sum(
        connection.beat < beat
        for slide in note_list_slide
        for connection in slide.connections if not connection.hidden
    )

    return result


def get_min_max_bpm(bpms: list[BPM]) -> tuple[float, float]:
    """Get the max and min BPM of a chart."""
    bpms = sorted(bpms, key=lambda bpm: bpm.bpm)
    return bpms[0].bpm, bpms[-1].bpm
