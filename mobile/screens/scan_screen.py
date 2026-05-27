from datetime import datetime

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from plyer import camera

from ui import BG, INFO, MUTED, PRIMARY, TEXT, WHITE, body_label, outline_button, primary_button


class ScanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.foto_path = None
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)

        toolbar = MDTopAppBar(
            title="Escanear NF-e",
            elevation=0,
            md_bg_color=PRIMARY,
            specific_text_color=WHITE,
            left_action_items=[["arrow-left", lambda *_: self.voltar(None)]],
        )
        root.add_widget(toolbar)

        content = MDBoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(16),
        )

        hero = MDCard(
            orientation="vertical",
            radius=[18, 18, 18, 18],
            elevation=1,
            padding=dp(20),
            spacing=dp(8),
            md_bg_color=INFO,
            size_hint_y=None,
            height=dp(174),
        )
        hero.add_widget(
            MDLabel(
                text="Capture a nota fiscal",
                font_style="H6",
                bold=True,
                theme_text_color="Custom",
                text_color=TEXT,
                size_hint_y=None,
                height=dp(32),
            )
        )
        hero.add_widget(
            MDLabel(
                text="Posicione a nota em local iluminado, enquadre o documento inteiro e evite sombras sobre os valores.",
                font_style="Body1",
                theme_text_color="Custom",
                text_color=MUTED,
            )
        )
        content.add_widget(hero)

        self.status_label = body_label("Pronto para abrir a camera.", 44)
        content.add_widget(self.status_label)
        content.add_widget(primary_button("Abrir camera", "camera-outline", self.tirar_foto))
        content.add_widget(outline_button("Voltar ao inicio", "arrow-left", self.voltar))
        content.add_widget(MDBoxLayout())

        root.add_widget(content)
        self.add_widget(root)

    def tirar_foto(self, instance):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.foto_path = f"/storage/emulated/0/nfe_{timestamp}.jpg"

        try:
            camera.take_picture(self.foto_path, self.on_complete)
            self.status_label.text = "Foto capturada. Processando OCR..."
        except Exception as error:
            self.status_label.text = f"Nao foi possivel abrir a camera: {error}"

    def on_complete(self):
        self.status_label.text = "Foto salva. Enviando para conferencia..."
        Clock.schedule_once(self.ir_confirmar, 0.8)

    def ir_confirmar(self, dt):
        self.manager.get_screen("confirm").set_foto_path(self.foto_path)
        self.manager.current = "confirm"

    def voltar(self, instance):
        self.manager.current = "home"
