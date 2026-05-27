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
from ui import BG, MUTED, PRIMARY, TEXT, WHITE, outline_button, primary_button, section_card


class ReportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)

        root.add_widget(
            MDTopAppBar(
                title="Gerar XML",
                elevation=0,
                md_bg_color=PRIMARY,
                specific_text_color=WHITE,
                left_action_items=[["arrow-left", lambda *_: self.voltar(None)]],
            )
        )

        scroll = ScrollView()

        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=dp(20),
            spacing=dp(14),
        )

        intro = section_card()
        intro.add_widget(
            MDLabel(
                text="Gerar XML das notas fiscais",
                font_style="H6",
                bold=True,
                theme_text_color="Custom",
                text_color=TEXT,
                size_hint_y=None,
                height=dp(32),
            )
        )

        intro_text = MDLabel(
            text="Filtre as notas por periodo, fornecedor e valor minimo. O sistema ira gerar um arquivo XML com os dados completos cadastrados no banco.",
            font_style="Body2",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height=dp(72),
        )
        intro_text.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        intro.add_widget(intro_text)

        content.add_widget(intro)

        filters = section_card()

        self.data_inicio = self.build_field("Data inicio", "YYYY-MM-DD")
        self.data_fim = self.build_field("Data fim", "YYYY-MM-DD")
        self.fornecedor = self.build_field("Fornecedor", "Todos")
        self.valor_min = self.build_field("Valor minimo", "0.00", input_filter="float")

        for field in [
            self.data_inicio,
            self.data_fim,
            self.fornecedor,
            self.valor_min,
        ]:
            filters.add_widget(field)

        content.add_widget(filters)

        content.add_widget(
            primary_button(
                "Gerar XML",
                "file-code-outline",
                self.gerar,
            )
        )

        content.add_widget(
            outline_button(
                "Voltar ao inicio",
                "arrow-left",
                self.voltar,
            )
        )

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def build_field(self, label, hint, input_filter=None):
        return MDTextField(
            helper_text=label,
            helper_text_mode="persistent",
            hint_text=hint,
            mode="rectangle",
            input_filter=input_filter,
            size_hint_y=None,
            height=dp(78),
        )

    def gerar(self, instance):
        filtros = {
            "data_inicio": self.data_inicio.text.strip() or None,
            "data_fim": self.data_fim.text.strip() or None,
            "fornecedor": self.fornecedor.text.strip() or None,
            "valor_min": float(self.valor_min.text) if self.valor_min.text else None,
            "valor_max": None,
        }

        try:
            response = APIClient.gerar_relatorio(filtros, "xml")

            filename = "notas_fiscais.xml"

            with open(filename, "wb") as file_obj:
                file_obj.write(response.content)

            self.show_dialog(
                "XML gerado",
                f"Arquivo XML salvo como {filename}.",
            )

        except Exception as error:
            self.show_dialog("Erro ao gerar XML", str(error))

    def voltar(self, instance):
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