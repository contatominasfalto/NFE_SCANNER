from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp
from pathlib import Path

from screens.confirm_screen import ConfirmScreen
from screens.list_screen import ListScreen
from screens.scan_screen import ScanScreen
from services.api_client import APIClient


Window.size = (390, 760)
BASE_DIR = Path(__file__).resolve().parent

Window.clearcolor = (0.97, 0.97, 0.96, 1)


KV = """
#:import FitImage kivymd.uix.fitimage.FitImage

ScreenManager:
    Screen:
        name: "home"

        MDBoxLayout:
            orientation: "vertical"
            md_bg_color: app.bg_color

            MDTopAppBar:
                title: "Minasfalto NF-e"
                elevation: 0
                md_bg_color: app.primary_color
                specific_text_color: app.text_color

            ScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: "20dp", "18dp", "20dp", "28dp"
                    spacing: "16dp"

                    MDCard:
                        orientation: "vertical"
                        size_hint_y: None
                        height: "228dp"
                        radius: [18, 18, 18, 18]
                        elevation: 1
                        padding: "20dp"
                        spacing: "10dp"
                        md_bg_color: app.surface_color

                        FitImage:
                            source: app.logo_path
                            size_hint_y: None
                            height: "88dp"
                            radius: [10, 10, 10, 10]

                        MDLabel:
                            text: "MINASFALTO"
                            theme_text_color: "Custom"
                            text_color: app.text_color
                            font_style: "H5"
                            bold: True
                            halign: "center"
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDLabel:
                            text: "Scanner de NF-e para controle, conferencia e relatorios internos."
                            theme_text_color: "Custom"
                            text_color: app.muted_text_color
                            font_style: "Body1"
                            halign: "center"
                            size_hint_y: None
                            height: self.texture_size[1] + dp(8)

                        MDLabel:
                            text: app.api_base_url_label
                            theme_text_color: "Custom"
                            text_color: app.primary_color
                            font_style: "Caption"
                            bold: True
                            halign: "center"
                            size_hint_y: None
                            height: self.texture_size[1]

                    MDLabel:
                        text: "Acoes principais"
                        theme_text_color: "Custom"
                        text_color: app.text_color
                        font_style: "Subtitle1"
                        bold: True
                        size_hint_y: None
                        height: self.texture_size[1] + dp(4)

                    MDCard:
                        orientation: "vertical"
                        size_hint_y: None
                        height: "174dp"
                        radius: [16, 16, 16, 16]
                        elevation: 1
                        padding: "12dp"
                        spacing: "10dp"
                        md_bg_color: app.surface_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            size_hint_y: None
                            height: "52dp"

                            MDFillRoundFlatButton:
                                text: "CDMA"
                                size_hint_x: 1
                                height: "52dp"
                                md_bg_color: app.primary_color
                                text_color: app.text_color
                                on_release: app.iniciar_leitura("CDMA")

                            MDFillRoundFlatButton:
                                text: "PRU"
                                size_hint_x: 1
                                height: "52dp"
                                md_bg_color: app.primary_color
                                text_color: app.text_color
                                on_release: app.iniciar_leitura("PRU")

                        MDRectangleFlatIconButton:
                            icon: "file-document-outline"
                            text: "Notas escaneadas"
                            size_hint_x: 1
                            height: "52dp"
                            theme_text_color: "Custom"
                            text_color: app.accent_color
                            line_color: app.border_color
                            icon_color: app.accent_color
                            on_release: app.root.current = "list"

                    MDCard:
                        orientation: "vertical"
                        size_hint_y: None
                        height: "116dp"
                        radius: [16, 16, 16, 16]
                        elevation: 0
                        padding: "16dp"
                        spacing: "6dp"
                        md_bg_color: app.info_color

                        MDLabel:
                            text: "Fluxo recomendado"
                            theme_text_color: "Custom"
                            text_color: app.text_color
                            font_style: "Subtitle2"
                            bold: True
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDLabel:
                            text: "1. Escaneie a nota  2. Confira os campos  3. Salve e gere relatorios"
                            theme_text_color: "Custom"
                            text_color: app.muted_text_color
                            font_style: "Body2"
                            size_hint_y: None
                            height: self.texture_size[1] + dp(8)

    ScanScreen:
        name: "scan"

    ConfirmScreen:
        name: "confirm"

    ListScreen:
        name: "list"

"""


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


if __name__ == "__main__":
    NFeApp().run()
