from kivy.app import App
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

from services.api_client import APIClient
from ui import ACCENT, BG, DANGER, MUTED, PRIMARY, TEXT, WHITE, outline_button, primary_button, section_card


class ConfirmScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.foto_path = None
        self.ocr_data = {}
        self.dialog = None
        self.campos = {}
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        root.add_widget(
            MDTopAppBar(
                title="Conferir dados da nota",
                elevation=0,
                md_bg_color=PRIMARY,
                specific_text_color=WHITE,
                left_action_items=[["arrow-left", lambda *_: self.cancelar(None)]],
            )
        )

        scroll = ScrollView()
        form = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=dp(20),
            spacing=dp(14),
        )

        intro = section_card(104)
        intro.add_widget(
            MDLabel(
                text="Revise antes de salvar",
                font_style="H6",
                bold=True,
                theme_text_color="Custom",
                text_color=TEXT,
                size_hint_y=None,
                height=dp(30),
            )
        )
        intro.add_widget(
            MDLabel(
                text="O OCR pode errar numeros e valores. Confira os campos principais antes de enviar para o banco.",
                font_style="Body2",
                theme_text_color="Custom",
                text_color=MUTED,
            )
        )
        form.add_widget(intro)

        fields = [
            ("numero_nf", "Numero da NF", "Ex.: 12345", False),
            ("serie", "Serie", "Ex.: 1", False),
            ("data_emissao", "Data de emissao", "YYYY-MM-DD", False),
            ("cnpj_fornecedor", "CNPJ do fornecedor", "00.000.000/0000-00", False),
            ("nome_fornecedor", "Fornecedor", "Razao social", False),
            ("valor_total", "Valor total", "0,00", False),
            ("chave_acesso", "Chave de acesso", "44 digitos", True),
            ("observacao", "Observacao", "Informacoes adicionais", True),
        ]

        card = section_card()
        for key, label, hint, multiline in fields:
            field = MDTextField(
                hint_text=hint,
                helper_text=label,
                helper_text_mode="persistent",
                mode="rectangle",
                multiline=multiline,
                size_hint_y=None,
                height=dp(88 if multiline else 64),
            )
            self.campos[key] = field
            card.add_widget(field)
        form.add_widget(card)

        actions = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(10),
            padding=(0, dp(2), 0, 0),
        )
        actions.add_widget(outline_button("Cancelar", "close", self.cancelar))
        actions.add_widget(primary_button("Salvar nota", "content-save-outline", self.salvar_nota))
        form.add_widget(actions)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def set_foto_path(self, path):
        self.foto_path = path
        self.processar_ocr()

    def processar_ocr(self):
        try:
            self.ocr_data = APIClient.ocr_nf(self.foto_path)
            for campo, valor in self.ocr_data.items():
                if campo in self.campos:
                    self.campos[campo].text = str(valor or "")
        except Exception as error:
            self.show_dialog("Erro no OCR", f"Nao foi possivel processar a imagem.\n\n{error}")

    def build_payload(self):
        valor_text = self.campos["valor_total"].text.strip().replace(".", "").replace(",", ".")
        try:
            valor_total = float(valor_text or 0)
        except ValueError:
            valor_total = 0.0

        return {
            "numero_nf": self.campos["numero_nf"].text.strip(),
            "serie": self.campos["serie"].text.strip(),
            "data_emissao": self.campos["data_emissao"].text.strip(),
            "cnpj_fornecedor": self.campos["cnpj_fornecedor"].text.strip(),
            "nome_fornecedor": self.campos["nome_fornecedor"].text.strip(),
            "valor_total": valor_total,
            "chave_acesso": self.campos["chave_acesso"].text.strip() or None,
            "observacao": self.campos["observacao"].text.strip() or None,
            "caminho_arquivo_imagem": self.ocr_data.get("caminho_arquivo_imagem"),
        }

    def salvar_nota(self, instance):
        try:
            APIClient.save_nota(self.build_payload())
            App.get_running_app().root.current = "list"
        except Exception as error:
            self.show_dialog("Erro ao salvar", str(error))

    def cancelar(self, instance):
        self.manager.current = "home"

    def show_dialog(self, title, message):
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    theme_text_color="Custom",
                    text_color=PRIMARY,
                    on_release=lambda *_: self.dialog.dismiss(),
                )
            ],
        )
        self.dialog.open()
