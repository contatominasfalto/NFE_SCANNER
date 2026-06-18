from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from pathlib import Path

from screens.confirm_screen import ConfirmScreen
from screens.list_screen import ListScreen
from screens.scan_screen import ScanScreen
from services.api_client import APIClient
from ui import BG, INFO, PRIMARY, SURFACE, TEXT, MUTED, outline_button, primary_button, section_card, wrap_label


if platform not in ("android", "ios"):
    Window.size = (390, 760)
BASE_DIR = Path(__file__).resolve().parent

Window.clearcolor = (0.97, 0.97, 0.96, 1)


KV = """
ScreenManager:
    HomeScreen:
        name: "home"

    ScanScreen:
        name: "scan"

    ConfirmScreen:
        name: "confirm"

    ListScreen:
        name: "list"

"""


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        root.add_widget(
            MDTopAppBar(
                title="Minasfalto NF-e",
                elevation=0,
                md_bg_color=PRIMARY,
                specific_text_color=TEXT,
            )
        )

        scroll = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=(dp(16), dp(16), dp(16), dp(24)),
            spacing=dp(14),
        )

        hero = section_card()
        hero.radius = [18, 18, 18, 18]
        hero.padding = dp(16)
        hero.spacing = dp(8)
        hero.md_bg_color = SURFACE
        hero.add_widget(
            Image(
                source=str(BASE_DIR / "assets" / "logo.jpg"),
                size_hint_y=None,
                height=dp(86),
                allow_stretch=True,
                keep_ratio=True,
            )
        )
        hero.add_widget(wrap_label("MINASFALTO", font_style="H5", color=TEXT, bold=True, halign="center"))
        hero.add_widget(
            wrap_label(
                "Scanner de NF-e para controle, conferencia e relatorios internos.",
                font_style="Body1",
                color=MUTED,
                halign="center",
            )
        )
        hero.add_widget(
            wrap_label(
                f"API: {APIClient.get_base_url()}",
                font_style="Caption",
                color=PRIMARY,
                bold=True,
                halign="center",
            )
        )
        content.add_widget(hero)

        content.add_widget(wrap_label("Acoes principais", font_style="Subtitle1", color=TEXT, bold=True, height=32))

        actions = section_card()
        actions.padding = dp(12)
        actions.spacing = dp(10)
        actions.md_bg_color = SURFACE
        local_buttons = MDBoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(50))
        local_buttons.add_widget(primary_button("CDMA", "", lambda *_: self.start_scan("CDMA")))
        local_buttons.add_widget(primary_button("PRU", "", lambda *_: self.start_scan("PRU")))
        actions.add_widget(local_buttons)
        actions.add_widget(outline_button("Notas escaneadas", "", lambda *_: self.open_list()))
        content.add_widget(actions)

        flow = section_card()
        flow.elevation = 0
        flow.padding = dp(16)
        flow.spacing = dp(6)
        flow.md_bg_color = INFO
        flow.add_widget(wrap_label("Fluxo recomendado", font_style="Subtitle2", color=TEXT, bold=True, height=28))
        flow.add_widget(
            wrap_label(
                "1. Escolha CDMA ou PRU\\n2. Leia pela camera ou digite a chave\\n3. Confira e salve a nota",
                font_style="Body2",
                color=MUTED,
            )
        )
        content.add_widget(flow)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def start_scan(self, local):
        app = MDApp.get_running_app()
        app.iniciar_leitura(local)

    def open_list(self):
        self.manager.current = "list"


class NFeApp(MDApp):
    primary_color = (0.95, 0.57, 0.16, 1)
    accent_color = (0.20, 0.20, 0.22, 1)
    bg_color = (0.97, 0.97, 0.96, 1)
    surface_color = (1, 1, 1, 1)
    info_color = (1.0, 0.95, 0.87, 1)
    border_color = (0.86, 0.84, 0.80, 1)
    text_color = (0.16, 0.16, 0.18, 1)
    muted_text_color = (0.40, 0.40, 0.42, 1)
    white = (1, 1, 1, 1)
    soft_white = (1.0, 0.95, 0.87, 1)
    logo_path = str(BASE_DIR / "assets" / "logo.jpg")
    api_base_url_label = f"API: {APIClient.get_base_url()}"

    def build(self):
        self.title = "NF-e Scanner"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.accent_palette = "Gray"
        return Builder.load_string(KV)

    def iniciar_leitura(self, local):
        self.root.get_screen("scan").set_local(local)
        self.root.current = "scan"

    def on_resume(self):
        if self.root and self.root.current == "scan":
            Clock.schedule_once(self.root.get_screen("scan").verificar_retorno_camera, 0.8)
        return True


if __name__ == "__main__":
    NFeApp().run()
