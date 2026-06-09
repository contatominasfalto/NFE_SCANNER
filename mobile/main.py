from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRectangleFlatIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from pathlib import Path

from screens.confirm_screen import ConfirmScreen
from screens.list_screen import ListScreen
from screens.scan_screen import ScanScreen


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
                            text: "API local: 127.0.0.1:8000"
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

                        MDFillRoundFlatIconButton:
                            icon: "barcode-scan"
                            text: "Bipar nota"
                            size_hint_x: 1
                            height: "52dp"
                            md_bg_color: app.primary_color
                            text_color: app.text_color
                            icon_color: app.text_color
                            on_release: app.abrir_selecao_setor()

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
    SETORES = ("A1BR", "A1BR/PRU", "A2BR")
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setor_dialog = None
        self.setor_selecionado = None
        self.setor_buttons = {}
        self.continuar_setor_button = None

    def build(self):
        self.title = "NF-e Scanner"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.accent_palette = "Gray"
        return Builder.load_string(KV)

    def abrir_selecao_setor(self):
        self.setor_selecionado = None
        self.setor_buttons = {}

        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(12),
        )
        content.add_widget(
            MDLabel(
                text="Selecione onde o material das notas sera alocado.",
                font_style="Body1",
                theme_text_color="Custom",
                text_color=self.muted_text_color,
                size_hint_y=None,
                height=dp(48),
            )
        )

        for setor in self.SETORES:
            button = MDRectangleFlatIconButton(
                text=setor,
                icon="checkbox-blank-outline",
                size_hint_x=1,
                height=dp(48),
                theme_text_color="Custom",
                text_color=self.accent_color,
                icon_color=self.accent_color,
                line_color=self.border_color,
            )
            button.bind(on_release=lambda _, value=setor: self.selecionar_setor(value))
            self.setor_buttons[setor] = button
            content.add_widget(button)

        self.continuar_setor_button = MDFlatButton(
            text="CONTINUAR",
            disabled=True,
            theme_text_color="Custom",
            text_color=self.primary_color,
            on_release=lambda *_: self.confirmar_setor(),
        )
        self.setor_dialog = MDDialog(
            title="Centro de custo",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    theme_text_color="Custom",
                    text_color=self.accent_color,
                    on_release=lambda *_: self.setor_dialog.dismiss(),
                ),
                self.continuar_setor_button,
            ],
        )
        self.setor_dialog.open()

    def selecionar_setor(self, setor):
        self.setor_selecionado = setor
        self.continuar_setor_button.disabled = False
        for value, button in self.setor_buttons.items():
            selected = value == setor
            button.icon = "check-circle-outline" if selected else "checkbox-blank-outline"
            button.text_color = self.primary_color if selected else self.accent_color
            button.icon_color = self.primary_color if selected else self.accent_color
            button.line_color = self.primary_color if selected else self.border_color

    def confirmar_setor(self):
        if not self.setor_selecionado:
            return
        self.root.get_screen("scan").set_centro_custo(self.setor_selecionado)
        self.setor_dialog.dismiss()
        self.root.current = "scan"


if __name__ == "__main__":
    NFeApp().run()
