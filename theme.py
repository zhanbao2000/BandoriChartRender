from abc import ABC

from PIL import ImageFont

from .resource import FontResourceMangaer

# size configuration
# you can refer to the CAD files: chart_bar.dwg and chart_full.dwg

width_divider = height_divider = 1  # divider size of bar, beat, and lane
width_simultaneous_line = 1  # width of simultaneous line
width_lane = 14  # width of single lane
width_track = width_lane * 7  # width of track, including 7 lanes
width_track_outline = 7  # width of track outline (on the left side of the 0th and the right side of the 6th)
width_track_extra = 50  # width of comment area, on the left of the track, used to write bar info, bpm changes, skill note and other info
width_note_resize = width_lane + width_divider * 8  # width of note when resizing
width_song_jacket = height_song_jacket = 240  # width and height of song jacket (square)

height_beat = 96  # height of single beat
height_bar = height_beat * 4  # height of single bar, including 4 beats
height_bar_extra = width_lane  # addtional area when cutting segment

margin = width_lane  # margin of the image
margin_song_jacket = margin * 2  # margin of song jacket
back_projection_factor = 1.8  # factor of back projection when resizing image

flick_top_offset = (0, 10)
flick_directional_offset_x, flick_directional_offset_y = (-5, 0)


class BaseTheme(ABC):
    transparent_color = (255, 255, 255, 0)
    track_background_color = (0, 0, 0, 190)

    divider_lane_color = divider_beat_color = (51, 255, 255, 100)
    divider_bar_color = (204, 255, 255, 210)

    slide_color = (75, 227, 113, 190)
    slide_outline_color = (75, 227, 113, 120)  # for anti-aliasing

    simultaneous_line_color = (255, 255, 255, 180)

    bpm_color = (51, 204, 255, 255)
    time_color = (255, 255, 255, 255)
    skill_color = (255, 209, 0, 255)
    skill_layer_outline_color = (255, 209, 0, 120)
    skill_layer_fill_color = (255, 209, 0, 50)
    fever_color = (255, 58, 114, 255)
    fever_layer_outline_color = (242, 126, 231, 120)
    fever_layer_fill_color = (242, 126, 231, 30)

    meta_text_color = (255, 255, 255, 255)
    meta_difficulty_color = [
        (48, 81, 250, 190),  # easy
        (25, 183, 26, 190),  # normal
        (255, 164, 27, 190),  # hard
        (238, 62, 64, 190),  # expert
        (239, 47, 156, 190),  # special
    ]

    font_comment_bpm = ImageFont.truetype(str(FontResourceMangaer.font_arial_bd), 16)
    font_comment_bar = ImageFont.truetype(str(FontResourceMangaer.font_arial_bd), 12)
    font_comment_skill_fever = ImageFont.truetype(str(FontResourceMangaer.font_arial_bd), 14)
    font_meta = ImageFont.truetype(str(FontResourceMangaer.font_a_otf_shingopro_medium_2), 36)
    font_meta_title = ImageFont.truetype(str(FontResourceMangaer.font_a_otf_shingopro_medium_2), 42)
    font_slogan = ImageFont.truetype(str(FontResourceMangaer.font_arial_bd), 36)
