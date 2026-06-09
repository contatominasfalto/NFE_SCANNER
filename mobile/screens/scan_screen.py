from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

from services.api_client import APIClient
from ui import BG, INFO, MUTED, PRIMARY, TEXT, WHITE, body_label, outline_button, primary_button


class ScanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chave_acesso = None
        self.local = None
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)

        root.add_widget(
            MDTopAppBar(
                title="Bipar NF-e",
                elevation=0,
                md_bg_color=PRIMARY,
                specific_text_color=WHITE,
                left_action_items=[["arrow-left", lambda *_: self.voltar(None)]],
            )
        )

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
                text="Leia o codigo de barras da NF-e",
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
                text=(
                    "Use o leitor como em uma bipagem de supermercado. A chave de acesso "
                    "sera capturada e validada automaticamente ao receber Enter."
                ),
                font_style="Body1",
                theme_text_color="Custom",
                text_color=MUTED,
            )
        )
        content.add_widget(hero)

        local_card = MDCard(
            orientation="horizontal",
            radius=[8, 8, 8, 8],
            elevation=0,
            padding=(dp(14), dp(10)),
            md_bg_color=PRIMARY,
            size_hint_y=None,
            height=dp(64),
        )
        local_card.add_widget(
            MDLabel(
                text="Local",
                font_style="Caption",
                bold=True,
                theme_text_color="Custom",
                text_color=TEXT,
            )
        )
        self.local_label = MDLabel(
            text="Nao selecionado",
            font_style="H6",
            bold=True,
            halign="right",
            theme_text_color="Custom",
            text_color=TEXT,
        )
        local_card.add_widget(self.local_label)
        content.add_widget(local_card)

        self.barcode_input = MDTextField(
            hint_text="Chave de acesso com 44 digitos",
            helper_text="Aguardando leitura do codigo de barras",
            helper_text_mode="persistent",
            mode="rectangle",
            multiline=False,
            size_hint_y=None,
            height=dp(72),
        )
        self.barcode_input.bind(on_text_validate=self.processar_codigo_barras)
        content.add_widget(self.barcode_input)

        self.status_label = body_label("Pronto para bipar a nota fiscal.", 44)
        content.add_widget(self.status_label)
        content.add_widget(primary_button("Validar codigo", "barcode-scan", self.processar_codigo_barras))
        content.add_widget(outline_button("Voltar ao inicio", "arrow-left", self.voltar))
        content.add_widget(MDBoxLayout())

        root.add_widget(content)
        self.add_widget(root)

    def on_pre_enter(self):
        self.preparar_nova_leitura()

    def preparar_nova_leitura(self):
        self.chave_acesso = None
        self.barcode_input.text = ""
        if self.local:
            self.status_label.text = f"Pronto para bipar para {self.local}."
        else:
            self.status_label.text = "Selecione um local antes de bipar."
        Clock.schedule_once(lambda *_: setattr(self.barcode_input, "focus", True), 0.2)

    def set_local(self, local):
        self.local = local
        self.local_label.text = local
        self.preparar_nova_leitura()

    def limpar_local(self):
        self.local = None
        self.local_label.text = "Nao selecionado"

    def processar_codigo_barras(self, instance):
        if not self.local:
            self.status_label.text = "Volte e selecione o local antes da leitura."
            return

        codigo_barras = self.barcode_input.text.strip()
        if not codigo_barras:
            self.status_label.text = "Bipe ou digite a chave de acesso da NF-e."
            self.barcode_input.focus = True
            return

        try:
            result = APIClient.ler_codigo_barras(codigo_barras)
            self.chave_acesso = result["chave_acesso"]
            self.status_label.text = "Nota consultada. Abrindo conferencia..."
            Clock.schedule_once(lambda *_: self.ir_confirmar(result["nota"]), 0.3)
        except Exception as error:
            self.status_label.text = f"Codigo invalido: {error}"
            self.barcode_input.select_all()
            self.barcode_input.focus = True

    def ir_confirmar(self, nota_data):
        nota_data = dict(nota_data)
        nota_data["local"] = self.local
        self.manager.get_screen("confirm").set_nota_data(nota_data)
        self.manager.current = "confirm"

    def voltar(self, instance):
        self.limpar_local()
        self.manager.current = "home"
