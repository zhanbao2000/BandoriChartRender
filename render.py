from io import BytesIO
from math import ceil
from pathlib import Path
from typing import Optional, Union

from PIL import Image, ImageDraw

from .chart import (
    get_max_beat, get_notes_for_type, get_all_skill_notes, get_fever_command_tuple,
    is_note_should_black, is_note_skill, is_note_flick,
    pairwise,
    get_grouped_notes_by_beat, get_time_elapsed, get_beat_elapsed, get_combo_before, get_min_max_bpm, get_total_combo,
)
from .model import Chart, Single, LaneLocated, Directional, Direction, Connection, BPM, Slide, Command, ChartMeta
from .resource import InGameResourceManager as IGRMngr
from .theme import (
    BaseTheme,
    width_divider, height_divider,
    width_simultaneous_line,
    width_lane,
    width_track,
    width_track_outline,
    width_track_extra,
    width_note_resize,
    width_song_jacket, height_song_jacket,
    height_bar, height_beat,
    height_bar_extra,
    margin,
    margin_song_jacket,
    back_projection_factor,
    flick_top_offset,
    flick_directional_offset_x, flick_directional_offset_y,
)
from .utils import second_to_sexagesimal


def resize_as_width(image: Image.Image, target_width: int, back_projection: Optional[bool] = False) -> Image.Image:
    """
    Resize an image to a given width.

    If using back projection, the height of the image will be multiplied by a
    factor to restore the projected image.
    """
    target_height = int(image.height * target_width / image.width)
    if back_projection:
        return image.resize((target_width, int(target_height * back_projection_factor)))
    return image.resize((target_width, target_height))


def get_height_from_cartesian(height_track: int, y: float, object_height: Optional[float] = None) -> int:
    """
    In the Cartesian coordinate system, X is the distance from the left
    boundary and Y is the distance from the lower boundary. However, in the
    Pillow coordinate system, Y is the distance from the upper boundary.

    This function converts coordinates between Cartesian and Pillow coordinate
    systems. 'object_height' is the height of the object whose coordinates
    are to be converted, and when this value is specified, objects with height
    can be converted to the correct coordinates.

    Copy from ArcaeaChartRender.
    """
    return int(height_track - y - object_height if object_height else height_track - y)


def open_image_resized(path: Path, target_width: int = width_note_resize, back_projection: Optional[bool] = True) -> Image.Image:
    """
    Open an image and resize it to a given width.

    If using back projection, the height of the image will be multiplied by a
    factor to restore the projected image.
    """
    return resize_as_width(Image.open(path).convert('RGBA'), target_width, back_projection)


class Render(object):

    def __init__(self, chart: Chart, meta: ChartMeta, jacket: Optional[BytesIO] = None):
        self._chart = chart
        self._meta = meta
        self._jacket = jacket

        # round up to an integer multiple of 4, and an extra 1 bar
        self._last_beat = ceil(get_max_beat(chart) / 4 + 1) * 4
        self._h = height_beat * self._last_beat + height_bar_extra * 2
        self._w = width_track_extra + width_track + width_divider + width_track_outline

        self._cache()
        self._render()

    def _cache(self):
        self._cached_bpm_list = list(get_notes_for_type(self._chart, BPM))
        self._cached_single_directional_list = list(get_notes_for_type(self._chart, (Single, Directional)))
        self._cached_slide_list = list(get_notes_for_type(self._chart, Slide))
        self._cached_command_list = list(get_notes_for_type(self._chart, Command))

    def _render(self):
        self.theme = BaseTheme
        self.im = Image.new('RGBA', (self._w, self._h), self.theme.transparent_color)

        self._comment_bpm_changing()
        self._comment_bar()

        self._draw_and_comment_skill()
        self._draw_and_comment_fever()

        self._draw_dividers()
        self._draw_simultaneous_line()
        self._draw_note_single_all()
        self._draw_note_directional_all()
        self._draw_slide_all()
        self._draw_slide_connections_all()

        self._post_processing_segment()
        self._post_processing_background()
        if self._jacket:
            self._post_processing_song_jacket()
        self._post_processing_song_meta()
        self._post_processing_add_slogan()

    def _locate_note(self, note: LaneLocated, offset: tuple[int, int] = (0, 0)) -> tuple[int, int]:
        """Locate the exact position of this note on the image based on its lane value."""
        return (
            int(width_track_extra + width_divider + width_lane * note.lane + width_lane / 2) + offset[0],
            get_height_from_cartesian(self._h, height_bar_extra - height_divider + height_beat * note.beat, offset[1])
        )

    def _locate_note_with_size(self, note: LaneLocated, note_image: Image.Image, offset: tuple[int, int] = (0, 0)) -> tuple[int, int]:
        """Locate the exact position of this note on the image based on its lane value and the size of the note."""
        x, y = self._locate_note(note, offset)
        return (
            x - note_image.width // 2,
            y - note_image.height // 2
        )

    def _locate_slide_parallelogram(self, start: Connection, end: Connection, offset: tuple[int, int] = (0, 0)) -> list[tuple[int, int]]:
        """Locate the exact position of the parallelogram in the image based on the lane value at the start and end of the slide."""
        x1 = int(width_track_extra + width_lane * start.lane)
        x2 = int(width_track_extra + width_lane * end.lane)
        y1 = get_height_from_cartesian(self._h, height_bar_extra + height_beat * start.beat)
        y2 = get_height_from_cartesian(self._h, height_bar_extra + height_beat * end.beat)
        return [
            (x1 + offset[0], y1 + offset[1]),
            (x2 + offset[0], y2 + offset[1]),
            (x2 + offset[0] + width_lane, y2 + offset[1]),
            (x1 + offset[0] + width_lane, y1 + offset[1]),
        ]

    def _locate_comment(self, beat: float, offset: tuple[int, int] = (0, 0)) -> tuple[int, int]:
        """Locate comment text position."""
        return (
            int(width_track_extra) + offset[0],
            get_height_from_cartesian(self._h, height_bar_extra + height_divider + height_beat * beat + offset[1])
        )

    def _locate_layer(self, beat_start: float, beat_end: float, offset: tuple[int, int] = (0, 0)) -> tuple[int, int, int, int]:
        """Locate layer rectangle position."""
        return (
            int(width_track_extra) + offset[0],
            get_height_from_cartesian(self._h, height_bar_extra + height_beat * beat_start + offset[1]),
            int(width_track_extra + width_track) + offset[0],
            get_height_from_cartesian(self._h, height_bar_extra + height_beat * beat_end + offset[1])
        )

    def _comment_bpm_changing(self):
        draw = ImageDraw.Draw(self.im)
        font = self.theme.font_comment_bpm

        for bpm in self._cached_bpm_list:
            draw.text(
                self._locate_comment(bpm.beat, (-font.size // 4, -font.size // 2)), f'{bpm.bpm} >',
                fill=self.theme.bpm_color, anchor='rs', font=font
            )

    def _comment_bar(self):
        draw = ImageDraw.Draw(self.im)
        font = self.theme.font_comment_bar
        bar_count = ceil(self._last_beat / 4)

        for bar in range(bar_count):
            # time elapsed
            draw.text(
                self._locate_comment(bar * 4, (-5, height_bar_extra)), second_to_sexagesimal(get_time_elapsed(self._cached_bpm_list, bar * 4)),
                fill=self.theme.time_color, anchor='rs', font=font
            )
            # combo
            draw.text(
                self._locate_comment(bar * 4, (-5, height_bar_extra * 2)),
                str(get_combo_before(bar * 4, self._cached_single_directional_list, self._cached_slide_list)),
                fill=self.theme.time_color, anchor='rs', font=font
            )
            # bar count
            draw.text(
                self._locate_comment(bar * 4, (-5, height_bar_extra * 3)), f'[{bar}]',
                fill=self.theme.time_color, anchor='rs', font=font
            )

    def _draw_and_comment_skill(self):
        draw = ImageDraw.Draw(self.im)

        for index, note in enumerate(get_all_skill_notes(self._chart)):
            beat_start = note.beat
            beat_start_time = get_time_elapsed(self._cached_bpm_list, beat_start)
            beat_end_5 = get_beat_elapsed(self._cached_bpm_list, beat_start_time + 5)
            beat_end_7 = get_beat_elapsed(self._cached_bpm_list, beat_start_time + 7)
            beat_end_8 = get_beat_elapsed(self._cached_bpm_list, beat_start_time + 8)

            draw.rectangle((self._locate_layer(beat_start, beat_end_5)),
                           fill=self.theme.skill_layer_fill_color, outline=self.theme.skill_layer_outline_color)
            draw.rectangle((self._locate_layer(beat_end_5, beat_end_7)),
                           fill=self.theme.skill_layer_fill_color, outline=self.theme.skill_layer_outline_color)
            draw.rectangle((self._locate_layer(beat_end_7, beat_end_8)),
                           fill=self.theme.skill_layer_fill_color, outline=self.theme.skill_layer_outline_color)

            draw.text(self._locate_comment(beat_start, (-5, 0)), f'#{index + 1}',
                      fill=self.theme.skill_color, anchor='rs', font=self.theme.font_comment_skill_fever)
            draw.text(self._locate_comment(beat_end_5, (-5, 0)), f'#{index + 1} +5s',
                      fill=self.theme.skill_color, anchor='rs', font=self.theme.font_comment_skill_fever)
            draw.text(self._locate_comment(beat_end_7, (-5, 0)), f'#{index + 1} +7s',
                      fill=self.theme.skill_color, anchor='rs', font=self.theme.font_comment_skill_fever)
            draw.text(self._locate_comment(beat_end_8, (-5, 0)), f'#{index + 1} +8s',
                      fill=self.theme.skill_color, anchor='rs', font=self.theme.font_comment_skill_fever)

    def _draw_and_comment_fever(self):
        im_fever = Image.new('RGBA', (self._w, self._h), color=self.theme.transparent_color)
        draw = ImageDraw.Draw(im_fever)
        if all(fevers := get_fever_command_tuple(self._cached_command_list)):
            fever_ready, fever_start, fever_end = fevers
        else:
            return

        draw.rectangle(self._locate_layer(fever_ready.beat, fever_start.beat),
                       fill=self.theme.fever_layer_fill_color, outline=self.theme.fever_layer_outline_color)
        draw.rectangle(self._locate_layer(fever_start.beat, fever_end.beat),
                       fill=self.theme.fever_layer_fill_color, outline=self.theme.fever_layer_outline_color)

        draw.text(self._locate_comment(fever_ready.beat, (-5, 0)), 'Ready',
                  fill=self.theme.fever_color, anchor='rs', font=self.theme.font_comment_skill_fever)
        draw.text(self._locate_comment(fever_start.beat, (-5, 0)), 'Start',
                  fill=self.theme.fever_color, anchor='rs', font=self.theme.font_comment_skill_fever)
        draw.text(self._locate_comment(fever_end.beat, (-5, 0)), 'End',
                  fill=self.theme.fever_color, anchor='rs', font=self.theme.font_comment_skill_fever)

        self.im.alpha_composite(im_fever)

    def _draw_dividers(self):
        im_divider = Image.new('RGBA', self.im.size, self.theme.transparent_color)
        draw = ImageDraw.Draw(im_divider)

        # lane divider
        for offset in range(8):
            x1 = x2 = width_track_extra + offset * width_lane
            draw.line((x1, 0, x2, self._h), fill=self.theme.divider_lane_color)

        # beat divider
        for offset in range(self._last_beat + 1):
            x2 = self._w - width_track_outline - width_divider
            y1 = y2 = height_bar_extra + offset * height_beat
            draw.line((width_track_extra, y1, x2, y2), fill=self.theme.divider_beat_color)

        # bar divider
        for offset in range(self._last_beat // 4 + 1):
            x1 = width_track_extra - width_track_outline
            y1 = y2 = height_bar_extra + offset * height_bar
            draw.line((x1, y1, self._w, y2), fill=self.theme.divider_bar_color)

        self.im.alpha_composite(im_divider)

    def _draw_simultaneous_line(self):
        im_simultaneous_line = Image.new('RGBA', self.im.size, self.theme.transparent_color)
        draw = ImageDraw.Draw(im_simultaneous_line)
        offset = (0, width_simultaneous_line)

        for beat, grouped_notes in get_grouped_notes_by_beat(self._chart):
            notes = list(grouped_notes)
            if len(notes) == 1:
                continue
            for note1, note2 in pairwise(notes):  # some fan-made charts have more than 2 notes in a beat (?)
                draw.line(
                    (self._locate_note(note1, offset), self._locate_note(note2, offset)),
                    fill=self.theme.simultaneous_line_color, width=width_simultaneous_line
                )

        self.im.alpha_composite(im_simultaneous_line)

    def _draw_note_single(self, note: Union[Single, Connection], im_note: Image.Image):
        self.im.alpha_composite(im_note, self._locate_note_with_size(note, im_note))

        if is_note_flick(note):
            im_flick_top = open_image_resized(IGRMngr.flick_top, target_width=width_lane, back_projection=False)
            self.im.alpha_composite(im_flick_top, self._locate_note_with_size(note, im_flick_top, flick_top_offset))

    def _draw_note_single_all(self):
        im_normal = open_image_resized(IGRMngr.normal)
        im_flick = open_image_resized(IGRMngr.flick)
        im_skill = open_image_resized(IGRMngr.skill)
        im_normal_16 = open_image_resized(IGRMngr.normal_16)

        for single in get_notes_for_type(self._chart, Single):
            if is_note_flick(single):
                im_note = im_flick
            elif is_note_skill(single):
                im_note = im_skill
            elif is_note_should_black(single):
                im_note = im_normal_16
            else:
                im_note = im_normal

            self._draw_note_single(single, im_note)

    def _draw_note_directional_all(self):
        im_left = open_image_resized(IGRMngr.flick_left)
        im_right = open_image_resized(IGRMngr.flick_right)
        im_left_top = open_image_resized(IGRMngr.flick_left_top, target_width=width_lane, back_projection=False)
        im_right_top = open_image_resized(IGRMngr.flick_right_top, target_width=width_lane, back_projection=False)

        for directional in get_notes_for_type(self._chart, Directional):
            if directional.direction == Direction.Left:
                im_directional = im_left
                im_directional_top = im_left_top
                factor = -1
            else:
                im_directional = im_right
                im_directional_top = im_right_top
                factor = 1

            for width in range(directional.width):
                self.im.alpha_composite(im_directional, self._locate_note_with_size(directional, im_directional, (width * width_lane * factor, 0)))

            self.im.alpha_composite(im_directional_top, self._locate_note_with_size(
                directional, im_directional_top,
                ((directional.width * width_lane + flick_directional_offset_x) * factor, flick_directional_offset_y)
            ))

    def _draw_slide_all(self):
        im_slide = Image.new('RGBA', self.im.size, self.theme.transparent_color)
        draw = ImageDraw.Draw(im_slide)

        for slide in self._cached_slide_list:
            for start, end in pairwise(slide.connections):
                draw.polygon(self._locate_slide_parallelogram(start, end), fill=self.theme.slide_color)

        self.im.alpha_composite(im_slide)

    def _draw_slide_connections_all(self):
        im_flick = open_image_resized(IGRMngr.flick)
        im_skill = open_image_resized(IGRMngr.skill)
        im_long = open_image_resized(IGRMngr.long)
        im_connection = open_image_resized(IGRMngr.connection)

        for slide in self._cached_slide_list:
            for index, connection in enumerate(slide.connections):
                if connection.hidden:
                    continue
                elif is_note_flick(connection):
                    im_note = im_flick
                elif is_note_skill(connection):
                    im_note = im_skill
                elif index == 0 or index == len(slide.connections) - 1:
                    im_note = im_long
                else:
                    im_note = im_connection
                self._draw_note_single(connection, im_note)

    def _post_processing_segment(self):
        segment_count = ceil(self._last_beat / 16)
        segment_height = height_bar * 4
        size = (self._w * segment_count, segment_height + height_bar_extra * 2)
        im_tiled_segments = Image.new('RGBA', size, self.theme.transparent_color)

        for i in range(segment_count):
            box = (
                0, get_height_from_cartesian(self._h, (i + 1) * segment_height + height_bar_extra * 2),
                self._w, get_height_from_cartesian(self._h, i * segment_height)
            )
            im_tiled_segments.alpha_composite(self.im.crop(box), (i * self._w, 0))

        self.im = im_tiled_segments

    def _post_processing_background(self):
        bg_size = (
            self.im.width + 2 * margin,
            self.im.height + 2 * margin + 2 * margin_song_jacket + height_song_jacket
        )
        bg = Image.open(IGRMngr.background).convert('RGBA')
        bg_black_layer = Image.new('RGBA', bg_size, self.theme.track_background_color)
        bg = bg.crop((0, 0, bg.width, bg.height // 2)).resize(bg_size)  # crop unwanted bottom part

        bg.alpha_composite(bg_black_layer, (0, 0))
        bg.alpha_composite(self.im, (margin, margin))

        draw = ImageDraw.Draw(bg)
        draw.rectangle(
            ((0, self.im.height + 2 * margin), (bg.width, bg.height)),
            self.theme.meta_difficulty_color[self._meta.difficulty or 3]
        )

        self.im = bg

    def _post_processing_song_jacket(self):
        im_jacket = Image.open(self._jacket).convert('RGBA').resize((width_song_jacket, height_song_jacket))
        self.im.paste(im_jacket, (margin_song_jacket, self.im.height - margin_song_jacket - height_song_jacket))

    def _post_processing_song_meta(self):
        draw = ImageDraw.Draw(self.im)
        font = self.theme.font_meta
        height_first_line = self.im.height - margin_song_jacket - height_song_jacket
        width_first_key_column = width_song_jacket + 2 * margin_song_jacket
        width_first_value_column = width_first_key_column + font.getsize('Chart Designer ')[0]
        width_second_key_column = width_first_key_column + self.im.width // 2
        width_second_value_column = width_second_key_column + font.getsize('Notes     ')[0]
        line_spacing = font.size * 1.4

        # title, artist, chart designer, lyricist, composer, arranger
        draw.text((width_first_key_column, height_first_line - line_spacing * 0.2),
                  f'[{self._meta.id}] {self._meta.title}', self.theme.meta_text_color, font=self.theme.font_meta_title)
        if self._meta.artist:  # both official and user post
            draw.text((width_first_key_column, height_first_line + line_spacing * 1),
                      'Artist', self.theme.meta_text_color, font=font)
            draw.text((width_first_value_column, height_first_line + line_spacing * 1),
                      f'{self._meta.artist}', self.theme.meta_text_color, font=font)
        if self._meta.chart_designer:  # only for user post
            draw.text((width_first_key_column, height_first_line + line_spacing * 2),
                      'Chart Designer', self.theme.meta_text_color, font=font)
            draw.text((width_first_value_column, height_first_line + line_spacing * 2),
                      f'{self._meta.chart_designer}', self.theme.meta_text_color, font=font)
        if self._meta.lyricist:  # only for official
            draw.text((width_first_key_column, height_first_line + line_spacing * 2),
                      'Lyricist', self.theme.meta_text_color, font=font)
            draw.text((width_first_value_column, height_first_line + line_spacing * 2),
                      f'{self._meta.lyricist}', self.theme.meta_text_color, font=font)
        if self._meta.composer:  # only for official
            draw.text((width_first_key_column, height_first_line + line_spacing * 3),
                      'Composer', self.theme.meta_text_color, font=font)
            draw.text((width_first_value_column, height_first_line + line_spacing * 3),
                      f'{self._meta.composer}', self.theme.meta_text_color, font=font)
        if self._meta.arranger:  # only for official
            draw.text((width_first_key_column, height_first_line + line_spacing * 4),
                      'Arranger', self.theme.meta_text_color, font=font)
            draw.text((width_first_value_column, height_first_line + line_spacing * 4),
                      f'{self._meta.arranger}', self.theme.meta_text_color, font=font)

        # level, bpm, notes, duration
        min_bpm, max_bpm = get_min_max_bpm(self._chart)
        bpm_literal = f'{min_bpm} - {max_bpm}' if min_bpm != max_bpm else f'{min_bpm}'
        total_notes = self._meta.total_notes or get_total_combo(self._cached_single_directional_list, self._cached_slide_list)
        draw.text((width_second_key_column, height_first_line),
                  'Level', self.theme.meta_text_color, font=font)
        draw.text((width_second_value_column, height_first_line),
                  f'[{self._meta.difficulty.name}] {self._meta.level}' if self._meta.is_official else f'[Fan-Made] {self._meta.level}',
                  self.theme.meta_text_color, font=font)
        draw.text((width_second_key_column, height_first_line + line_spacing * 1),
                  'BPM', self.theme.meta_text_color, font=font)
        draw.text((width_second_value_column, height_first_line + line_spacing * 1),
                  bpm_literal, self.theme.meta_text_color, font=font)
        draw.text((width_second_key_column, height_first_line + line_spacing * 2),
                  'Notes', self.theme.meta_text_color, font=font)
        draw.text((width_second_value_column, height_first_line + line_spacing * 2),
                  f'{total_notes}', self.theme.meta_text_color, font=font)

    def _post_processing_add_slogan(self):
        draw = ImageDraw.Draw(self.im)
        draw.text((self.im.width - margin, self.im.height - margin),
                  'Generated by BandoriChartRender', self.theme.meta_text_color, font=self.theme.font_slogan, anchor='rs')

    def save(self, path: str, **kwargs) -> None:
        self.im.save(path, **kwargs)

    def show(self) -> None:
        self.im.show()

    def to_bytes_io(self) -> BytesIO:
        io = BytesIO()
        self.im.save(io, 'PNG')
        io.seek(0)
        return io
