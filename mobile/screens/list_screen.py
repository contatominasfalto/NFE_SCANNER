from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

from services.api_client import APIClient
from ui import ACCENT, BG, MUTED, PRIMARY, SURFACE, TEXT, WHITE, outline_button


class ListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notas = []
        self.dialog = None
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        root.add_widget(
            MDTopAppBar(
                title="Notas escaneadas",
                elevation=0,
                md_bg_color=PRIMARY,
                specific_text_color=WHITE,
                left_action_items=[["arrow-left", lambda *_: self.voltar(None)]],
                right_action_items=[["refresh", lambda *_: self.carregar_notas()]],
            )
        )

        content = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
        )

        self.search_input = MDTextField(
            hint_text="Pesquisar por numero, fornecedor ou CNPJ",
            mode="rectangle",
            size_hint_y=None,
            height=dp(56),
        )
        self.search_input.bind(text=lambda *_: self.render_notas())
        content.add_widget(self.search_input)

        self.status_label = MDLabel(
            text="Carregando notas...",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height=dp(24),
        )
        content.add_widget(self.status_label)

        self.scroll = ScrollView()
        self.lista_layout = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(10),
            padding=(0, 0, 0, dp(8)),
        )
        self.scroll.add_widget(self.lista_layout)
        content.add_widget(self.scroll)
        content.add_widget(outline_button("Voltar ao inicio", "arrow-left", self.voltar))

        root.add_widget(content)
        self.add_widget(root)

    def on_pre_enter(self):
        self.carregar_notas()

    def carregar_notas(self):
        try:
            self.notas = APIClient.list_notas()
            self.render_notas()
        except Exception as error:
            self.notas = []
            self.status_label.text = "Nao foi possivel carregar as notas."
            self.show_dialog("Erro ao listar notas", str(error))

    def render_notas(self):
        self.lista_layout.clear_widgets()
        query = self.search_input.text.lower().strip()
        notas = [
            nota
            for nota in self.notas
            if not query
            or query in str(nota.get("numero_nf", "")).lower()
            or query in str(nota.get("nome_fornecedor", "")).lower()
            or query in str(nota.get("cnpj_fornecedor", "")).lower()
        ]

        self.status_label.text = f"{len(notas)} nota(s) encontrada(s)"

        if not notas:
            empty = MDCard(
                orientation="vertical",
                radius=[16, 16, 16, 16],
                elevation=0,
                padding=dp(18),
                md_bg_color=SURFACE,
                size_hint_y=None,
                height=dp(96),
            )
            empty.add_widget(
                MDLabel(
                    text="Nenhuma nota para exibir",
                    halign="center",
                    font_style="Body1",
                    theme_text_color="Custom",
                    text_color=MUTED,
                )
            )
            self.lista_layout.add_widget(empty)
            return

        for nota in notas:
            self.lista_layout.add_widget(self.build_nota_card(nota))

    def build_nota_card(self, nota):
        numero = nota.get("numero_nf") or "Sem numero"
        fornecedor = nota.get("nome_fornecedor") or "Fornecedor nao informado"
        valor = nota.get("valor_total") or 0
        data = str(nota.get("data_emissao") or "")[:10]

        card = MDCard(
            orientation="vertical",
            radius=[16, 16, 16, 16],
            elevation=1,
            padding=dp(14),
            spacing=dp(4),
            md_bg_color=SURFACE,
            size_hint_y=None,
            height=dp(112),
            ripple_behavior=True,
        )
        card.bind(on_release=lambda *_: self.ver_detalhe(nota))
        card.add_widget(
            MDLabel(
                text=f"NF {numero}",
                font_style="Subtitle1",
                bold=True,
                theme_text_color="Custom",
                text_color=TEXT,
                size_hint_y=None,
                height=dp(28),
            )
        )
        card.add_widget(
            MDLabel(
                text=fornecedor,
                font_style="Body2",
                theme_text_color="Custom",
                text_color=MUTED,
                size_hint_y=None,
                height=dp(24),
                shorten=True,
            )
        )
        card.add_widget(
            MDLabel(
                text=f"R$ {valor}    {data}",
                font_style="Body2",
                bold=True,
                theme_text_color="Custom",
                text_color=ACCENT,
            )
        )
        return card

    def ver_detalhe(self, nota):
        message = (
            f"Numero: {nota.get('numero_nf', '')}\n"
            f"Fornecedor: {nota.get('nome_fornecedor', '')}\n"
            f"CNPJ: {nota.get('cnpj_fornecedor', '')}\n"
            f"Valor: R$ {nota.get('valor_total', '')}\n"
            f"Data: {nota.get('data_emissao', '')}"
        )
        self.show_dialog("Detalhes da nota", message)

    def show_dialog(self, title, message):
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="FECHAR",
                    theme_text_color="Custom",
                    text_color=PRIMARY,
                    on_release=lambda *_: self.dialog.dismiss(),
                )
            ],
        )
        self.dialog.open()

    def voltar(self, instance):
        self.manager.current = "home"
