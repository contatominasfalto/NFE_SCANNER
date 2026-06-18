from kivy.metrics import dp
from kivy.uix.button import Button
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel


PRIMARY = (0.95, 0.57, 0.16, 1)
ACCENT = (0.20, 0.20, 0.22, 1)
BG = (0.97, 0.97, 0.96, 1)
SURFACE = (1, 1, 1, 1)
INFO = (1.0, 0.95, 0.87, 1)
BORDER = (0.86, 0.84, 0.80, 1)
TEXT = (0.16, 0.16, 0.18, 1)
MUTED = (0.40, 0.40, 0.42, 1)
WHITE = (1, 1, 1, 1)
DANGER = (0.86, 0.23, 0.22, 1)


def title_label(text):
    return MDLabel(
        text=text,
        font_style="H6",
        bold=True,
        theme_text_color="Custom",
        text_color=TEXT,
        size_hint_y=None,
        height=dp(34),
    )


def body_label(text, height=28):
    return MDLabel(
        text=text,
        font_style="Body2",
        theme_text_color="Custom",
        text_color=MUTED,
        size_hint_y=None,
        height=dp(height),
    )


def wrap_label(text, font_style="Body2", color=MUTED, height=None, bold=False, halign="left"):
    fixed_height = dp(height) if height is not None else None
    label = MDLabel(
        text=text,
        font_style=font_style,
        bold=bold,
        theme_text_color="Custom",
        text_color=color,
        halign=halign,
        size_hint_y=None,
    )
    label.bind(width=lambda instance, value: setattr(instance, "text_size", (value, None)))
    if fixed_height is None:
        label.bind(texture_size=lambda instance, value: setattr(instance, "height", value[1] + dp(6)))
    else:
        label.height = fixed_height
    return label


def section_card(height=None):
    card = MDCard(
        orientation="vertical",
        radius=[16, 16, 16, 16],
        elevation=1,
        padding=dp(16),
        spacing=dp(10),
        md_bg_color=SURFACE,
        size_hint_y=None,
    )
    if height is not None:
        card.height = dp(height)
    else:
        card.bind(minimum_height=card.setter("height"))
    return card


def primary_button(text, icon, callback):
    button = Button(
        text=text,
        size_hint_x=1,
        size_hint_y=None,
        height=dp(48),
        background_normal="",
        background_down="",
        background_color=PRIMARY,
        color=TEXT,
        bold=True,
    )
    button.bind(on_release=callback)
    return button


def outline_button(text, icon, callback):
    button = Button(
        text=text,
        size_hint_x=1,
        size_hint_y=None,
        height=dp(48),
        background_normal="",
        background_down="",
        background_color=(1, 1, 1, 1),
        color=ACCENT,
    )
    button.bind(on_release=callback)
    return button
