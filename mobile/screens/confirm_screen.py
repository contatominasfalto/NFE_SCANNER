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
from ui import (
    BG,
    DANGER_SOFT,
    DANGER_TEXT,
    MUTED,
    PRIMARY,
    SUCCESS_SOFT,
    SUCCESS_TEXT,
    TEXT,
    WHITE,
    outline_button,
    primary_button,
    section_card,
    soft_button,
    wrap_label,
)


class ConfirmScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.campos = {}
        self.erro_consulta = None
        self.build_ui()

    def build_ui(self):
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        self.toolbar = MDTopAppBar(
            title="Conferir dados da nota",
            elevation=0,
            md_bg_color=PRIMARY,
            specific_text_color=WHITE,
            left_action_items=[["arrow-left", lambda *_: self.cancelar(None)]],
        )
        root.add_widget(self.toolbar)

        scroll = ScrollView()
        form = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=dp(16),
            spacing=dp(12),
        )

        intro = section_card()
        self.intro_title = wrap_label(
            "Revise antes de salvar",
            font_style="H6",
            color=TEXT,
            bold=True,
            height=30,
        )
        intro.add_widget(self.intro_title)
        self.intro_text = wrap_label(
            "Confira os campos da nota antes de enviar para o banco.",
            font_style="Body2",
            color=MUTED,
        )
        intro.add_widget(self.intro_text)
        form.add_widget(intro)

        fields = [
            ("local", "Local", False),
            ("chave_acesso", "Chave NF", True),
            ("data_emissao", "Data de emissao", False),
            ("numero_nf", "Numero da NF", False),
            ("serie", "Serie", False),
            ("produto", "Produto", True),
            ("quantidade", "Quantidade / Peso liquido", False),
            ("transportador", "Transportador", False),
            ("faturista", "Faturista", False),
            ("lider_operacional", "Lider operacional", False),
            ("cnpj_fornecedor", "CNPJ do fornecedor", False),
            ("nome_fornecedor", "Fornecedor", False),
            ("valor_total", "Valor total", False),
            ("observacao", "Observacao / Informacao adicional", True),
        ]

        card = section_card()
        card.spacing = dp(12)
        for key, label, multiline in fields:
            field = MDTextField(
                hint_text=label,
                mode="rectangle",
                multiline=multiline,
                disabled=key in ("local", "faturista"),
                size_hint_y=None,
                height=dp(120 if key == "observacao" else 78 if multiline else 54),
            )
            self.campos[key] = field
            card.add_widget(field)
        form.add_widget(card)

        actions = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(10),
            padding=(0, dp(2), 0, 0),
        )
        self.primary_action = primary_button("Salvar e proxima", "barcode-scan", self.salvar_e_proxima)
        self.finish_action = soft_button(
            "Salvar e finalizar",
            "check-circle-outline",
            self.salvar_e_finalizar,
            SUCCESS_SOFT,
            SUCCESS_TEXT,
        )
        actions.add_widget(self.primary_action)
        actions.add_widget(self.finish_action)
        actions.add_widget(soft_button("Cancelar", "close", self.cancelar, DANGER_SOFT, DANGER_TEXT))
        form.add_widget(actions)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def set_nota_data(self, nota_data):
        chave_acesso = nota_data.get("chave_acesso")
        if not chave_acesso:
            self.show_dialog("Chave invalida", "Nenhuma chave de acesso foi recebida.")
            self.manager.current = "scan"
            return
        if not nota_data.get("local"):
            self.show_dialog(
                "Local nao selecionado",
                "Volte ao inicio, escolha o local e realize a leitura novamente.",
            )
            self.manager.current = "home"
            return

        self.preencher_campos(nota_data)

        self.erro_consulta = nota_data.get("erro_consulta")
        if self.erro_consulta:
            self.intro_title.text = "Consulta fiscal nao concluida"
            self.intro_text.text = (
                "A chave sera registrada no painel e os demais campos serao marcados como ERRO."
            )
        else:
            self.intro_title.text = "Nota fiscal consultada"
            self.intro_text.text = (
                "Confira os dados retornados pela API. Use Salvar e proxima para gravar "
                "e voltar ao leitor, ou Salvar e finalizar para encerrar."
            )

    def preencher_campos(self, nota_data):
        self.limpar_campos()
        self.campos["faturista"].text = "BIPE"
        for campo, valor in nota_data.items():
            if campo in self.campos:
                self.campos[campo].text = str(valor or "")

    def limpar_campos(self):
        for field in self.campos.values():
            field.text = ""

    def atualizar_progresso(self):
        self.intro_title.text = "Revise antes de salvar"
        self.intro_text.text = (
            "Confira esta nota. Use Salvar e proxima para gravar e voltar ao leitor, "
            "ou Salvar e finalizar para encerrar o processo."
        )

    def build_payload(self):
        local = self.campos["local"].text.strip() or None

        valor_text = self.campos["valor_total"].text.strip()
        if "," in valor_text:
            valor_text = valor_text.replace(".", "").replace(",", ".")
        try:
            valor_total = float(valor_text or 0)
        except ValueError:
            valor_total = 0.0
        quantidade_text = self.campos["quantidade"].text.strip().replace(",", ".")
        try:
            quantidade = float(quantidade_text) if quantidade_text else None
        except ValueError:
            quantidade = None

        return {
            "numero_nf": self.campos["numero_nf"].text.strip(),
            "serie": self.campos["serie"].text.strip(),
            "data_emissao": self.campos["data_emissao"].text.strip(),
            "cnpj_fornecedor": self.campos["cnpj_fornecedor"].text.strip(),
            "nome_fornecedor": self.campos["nome_fornecedor"].text.strip(),
            "valor_total": valor_total,
            "chave_acesso": self.campos["chave_acesso"].text.strip() or None,
            "local": local,
            "produto": self.campos["produto"].text.strip() or None,
            "quantidade": quantidade,
            "transportador": self.campos["transportador"].text.strip() or None,
            "faturista": "BIPE",
            "lider_operacional": self.campos["lider_operacional"].text.strip() or None,
            "observacao": self.campos["observacao"].text.strip() or None,
            "caminho_arquivo_imagem": None,
        }

    def salvar_nota_atual(self):
        payload = self.build_payload()
        if self.erro_consulta:
            return APIClient.save_nota_erro_com_fallback(
                {
                    "chave_acesso": payload["chave_acesso"],
                    "local": payload["local"],
                    "detalhe": self.erro_consulta,
                }
            )
        return APIClient.save_nota_com_fallback(payload)

    def salvar_e_proxima(self, instance):
        try:
            self.salvar_nota_atual()
            self.preparar_leitor_para_proxima()
        except Exception as error:
            self.show_dialog("Erro ao salvar", str(error))

    def salvar_e_finalizar(self, instance):
        try:
            self.salvar_nota_atual()
            self.manager.get_screen("scan").limpar_local()
            App.get_running_app().root.current = "list"
        except Exception as error:
            self.show_dialog("Erro ao salvar", str(error))

    def preparar_leitor_para_proxima(self):
        self.manager.current = "scan"
        scan_screen = self.manager.get_screen("scan")
        scan_screen.preparar_nova_leitura()

    def cancelar(self, instance):
        self.manager.get_screen("scan").limpar_local()
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
