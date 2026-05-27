from kivy.metrics import dp
from kivymd.uix.button import MDFillRoundFlatIconButton, MDRectangleFlatIconButton
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
    button = MDFillRoundFlatIconButton(
        text=text,
        icon=icon,
        size_hint_x=1,
        height=dp(48),
        md_bg_color=PRIMARY,
        text_color=TEXT,
        icon_color=TEXT,
    )
    button.bind(on_release=callback)
    return button


def outline_button(text, icon, callback):
    button = MDRectangleFlatIconButton(
        text=text,
        icon=icon,
        size_hint_x=1,
        height=dp(48),
        theme_text_color="Custom",
        text_color=ACCENT,
        line_color=BORDER,
        icon_color=ACCENT,
    )
    button.bind(on_release=callback)
    return button
