import os
import re

from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
from plyer import storagepath

from services.api_client import APIClient
from ui import ACCENT, BG, MUTED, PRIMARY, SURFACE, TEXT, WHITE, outline_button, primary_button, wrap_label


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
            padding=dp(14),
            spacing=dp(10),
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
            or query in str(nota.get("local", "")).lower()
            or query in str(nota.get("produto", "")).lower()
            or query in str(nota.get("transportador", "")).lower()
        ]
        notas.sort(
            key=lambda nota: (
                str(nota.get("data_cadastro") or ""),
                int(nota.get("id") or 0),
            ),
            reverse=True,
        )

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
            spacing=dp(6),
            md_bg_color=SURFACE,
            size_hint_y=None,
            ripple_behavior=True,
        )
        card.bind(minimum_height=card.setter("height"))
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
            wrap_label(fornecedor, font_style="Body2", color=MUTED)
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
        if self.dialog:
            self.dialog.dismiss()

        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(14),
        )
        header = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(4),
        )
        header.add_widget(
            MDLabel(
                text="Detalhes da nota",
                font_style="H6",
                bold=True,
                theme_text_color="Custom",
                text_color=TEXT,
                size_hint_y=None,
                height=dp(48),
            )
        )
        content.add_widget(header)

        detalhe = wrap_label(
            (
                f"Numero: {nota.get('numero_nf', '')}\n"
                f"Fornecedor: {nota.get('nome_fornecedor', '')}\n"
                f"CNPJ: {nota.get('cnpj_fornecedor', '')}\n"
                f"Local: {nota.get('local') or 'Nao informado'}\n"
                f"Produto: {nota.get('produto') or 'Nao informado'}\n"
                f"Quantidade: {nota.get('quantidade') or 'Nao informada'}\n"
                f"Transportador: {nota.get('transportador') or 'Nao informado'}\n"
                f"Faturista: {nota.get('faturista') or 'BIPE'}\n"
                f"Lider operacional: {nota.get('lider_operacional') or 'Nao informado'}\n"
                f"Valor: R$ {nota.get('valor_total', '')}\n"
                f"Data emissao: {nota.get('data_emissao', '')}\n"
                f"Data/hora do bip: {nota.get('data_cadastro', '')}"
            ),
            font_style="Body1",
            color=MUTED,
        )
        content.add_widget(detalhe)
        content.add_widget(
            primary_button(
                "Gerar XML",
                "file-code-outline",
                lambda *_: self.gerar_xml_nota(nota),
            )
        )

        self.dialog = MDDialog(
            type="custom",
            content_cls=content,
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

    def gerar_xml_nota(self, nota):
        nota_id = nota.get("id")
        numero = nota.get("numero_nf") or nota_id

        if not nota_id:
            self.show_dialog("Erro ao gerar XML", "Nota sem ID para gerar o XML.")
            return

        try:
            response = APIClient.gerar_xml_nota(nota_id)
            filename = self.build_xml_filename(numero)
            filepath = self.save_xml_to_downloads(filename, response.content)

            self.show_dialog("XML gerado", f"Arquivo XML salvo em:\n{filepath}")
        except Exception as error:
            self.show_dialog("Erro ao gerar XML", str(error))

    def save_xml_to_downloads(self, filename, content):
        if platform == "android":
            try:
                return self.save_xml_to_android_downloads(filename, content)
            except Exception:
                pass

        downloads_dir = self.get_downloads_dir()
        filepath = os.path.join(downloads_dir, filename)

        with open(filepath, "wb") as file_obj:
            file_obj.write(content)

        return filepath

    def save_xml_to_android_downloads(self, filename, content):
        from android import mActivity
        from jnius import autoclass

        BuildVersion = autoclass("android.os.Build$VERSION")
        Environment = autoclass("android.os.Environment")

        if BuildVersion.SDK_INT < 29:
            downloads_dir = self.get_downloads_dir()
            filepath = os.path.join(downloads_dir, filename)
            with open(filepath, "wb") as file_obj:
                file_obj.write(content)
            return filepath

        ContentValues = autoclass("android.content.ContentValues")
        Downloads = autoclass("android.provider.MediaStore$Downloads")
        MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")

        values = ContentValues()
        values.put(MediaColumns.DISPLAY_NAME, filename)
        values.put(MediaColumns.MIME_TYPE, "application/xml")
        values.put(MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
        values.put(MediaColumns.IS_PENDING, 1)

        resolver = mActivity.getContentResolver()
        uri = resolver.insert(Downloads.EXTERNAL_CONTENT_URI, values)
        if uri is None:
            raise RuntimeError("Nao foi possivel criar o arquivo em Downloads.")

        output_stream = resolver.openOutputStream(uri)
        try:
            output_stream.write(bytearray(content))
        finally:
            output_stream.close()

        values.clear()
        values.put(MediaColumns.IS_PENDING, 0)
        resolver.update(uri, values, None, None)

        return f"{Environment.DIRECTORY_DOWNLOADS}/{filename}"

    def get_downloads_dir(self):
        try:
            downloads_dir = storagepath.get_downloads_dir()
        except Exception:
            downloads_dir = None

        if not downloads_dir or downloads_dir.startswith("Method not implemented"):
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    def build_xml_filename(self, numero):
        safe_numero = re.sub(r"[^A-Za-z0-9_-]+", "_", str(numero)).strip("_")
        return f"nota_fiscal_{safe_numero or 'sem_numero'}.xml"

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
