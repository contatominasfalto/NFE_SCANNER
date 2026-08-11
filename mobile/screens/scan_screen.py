from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
import re
from threading import Thread

from services.api_client import APIClient, APIError
from ui import (
    BG,
    DANGER_SOFT,
    DANGER_TEXT,
    INFO,
    MUTED,
    PRIMARY,
    SUCCESS_SOFT,
    SUCCESS_TEXT,
    TEXT,
    WHITE,
    body_label,
    primary_button,
    section_card,
    soft_button,
    wrap_label,
)


class ScanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chave_acesso = None
        self.local = None
        self.scanner_listeners = []
        self.validando = False
        self.bipes_sequencia = 0
        self.dialog = None
        self.loading_event = None
        self.build_ui()

    def build_ui(self):
        screen_root = FloatLayout()
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        screen_root.add_widget(root)

        root.add_widget(
            MDTopAppBar(
                title="Bipar NF-e",
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
            padding=dp(16),
            spacing=dp(12),
        )

        hero = section_card()
        hero.radius = [18, 18, 18, 18]
        hero.padding = dp(16)
        hero.spacing = dp(8)
        hero.md_bg_color = INFO
        hero.add_widget(
            wrap_label(
                "Leia o codigo de barras da NF-e",
                font_style="H6",
                color=TEXT,
                bold=True,
                height=32,
            )
        )
        hero.add_widget(
            wrap_label(
                (
                    "Use a camera do celular para ler o codigo. Se a camera nao conseguir "
                    "capturar, digite ou cole a chave de acesso manualmente."
                ),
                font_style="Body2",
                color=MUTED,
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

        self.status_label = body_label("Pronto para bipar a nota fiscal.", 88)
        content.add_widget(self.status_label)
        self.camera_button = primary_button("Abrir leitor pela camera", "camera", self.iniciar_leitura_camera)
        content.add_widget(self.camera_button)
        self.validate_button = soft_button(
            "Validar codigo digitado",
            "barcode-scan",
            self.processar_codigo_barras,
            SUCCESS_SOFT,
            SUCCESS_TEXT,
        )
        content.add_widget(self.validate_button)
        content.add_widget(soft_button("Voltar ao inicio", "arrow-left", self.voltar, DANGER_SOFT, DANGER_TEXT))

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.screen_root = screen_root
        self.loading_overlay = self.criar_overlay_validacao()
        self.add_widget(screen_root)

    def criar_overlay_validacao(self):
        overlay = FloatLayout(size_hint=(1, 1), opacity=0, disabled=True)
        with overlay.canvas.before:
            Color(0, 0, 0, 0.45)
            overlay.bg_rect = Rectangle(pos=overlay.pos, size=overlay.size)
        overlay.bind(
            pos=lambda instance, value: setattr(instance.bg_rect, "pos", value),
            size=lambda instance, value: setattr(instance.bg_rect, "size", value),
        )

        card = MDCard(
            orientation="vertical",
            radius=[12, 12, 12, 12],
            elevation=4,
            padding=dp(20),
            spacing=dp(14),
            md_bg_color=WHITE,
            size_hint=(None, None),
            size=(dp(280), dp(190)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.loading_bar_value = 8
        self.loading_bar = FloatLayout(size_hint_y=None, height=dp(8))
        with self.loading_bar.canvas.before:
            Color(1.0, 0.91, 0.80, 1)
            self.loading_track_rect = Rectangle(pos=self.loading_bar.pos, size=self.loading_bar.size)
            Color(*PRIMARY)
            self.loading_fill_rect = Rectangle(pos=self.loading_bar.pos, size=(0, dp(8)))
        self.loading_bar.bind(pos=self.atualizar_loading_bar, size=self.atualizar_loading_bar)
        card.add_widget(self.loading_bar)
        card.add_widget(
            MDLabel(
                text="Validando nota na API...",
                font_style="H6",
                bold=True,
                halign="center",
                theme_text_color="Custom",
                text_color=TEXT,
                size_hint_y=None,
                height=dp(34),
            )
        )
        card.add_widget(
            MDLabel(
                text="Aguarde a conferencia terminar.",
                font_style="Body2",
                halign="center",
                theme_text_color="Custom",
                text_color=MUTED,
                size_hint_y=None,
                height=dp(34),
            )
        )
        overlay.add_widget(card)
        return overlay

    def mostrar_validacao_api(self, ativo):
        self.validando = ativo
        if ativo and not self.loading_overlay.parent:
            self.screen_root.add_widget(self.loading_overlay)
            self.iniciar_loading_bar()
        elif not ativo and self.loading_overlay.parent:
            self.screen_root.remove_widget(self.loading_overlay)
            self.parar_loading_bar()
        self.loading_overlay.opacity = 1 if ativo else 0
        self.loading_overlay.disabled = not ativo
        self.barcode_input.disabled = ativo
        self.camera_button.disabled = ativo
        self.validate_button.disabled = ativo

    def iniciar_loading_bar(self):
        self.loading_bar_value = 8
        self.atualizar_loading_bar()
        if not self.loading_event:
            self.loading_event = Clock.schedule_interval(self.animar_loading_bar, 0.03)

    def parar_loading_bar(self):
        if self.loading_event:
            self.loading_event.cancel()
            self.loading_event = None
        self.loading_bar_value = 0
        self.atualizar_loading_bar()

    def animar_loading_bar(self, interval):
        self.loading_bar_value = 8 if self.loading_bar_value >= 100 else self.loading_bar_value + 2.5
        self.atualizar_loading_bar()

    def atualizar_loading_bar(self, *args):
        self.loading_track_rect.pos = self.loading_bar.pos
        self.loading_track_rect.size = self.loading_bar.size
        self.loading_fill_rect.pos = self.loading_bar.pos
        self.loading_fill_rect.size = (
            self.loading_bar.width * (self.loading_bar_value / 100),
            self.loading_bar.height,
        )

    def on_pre_enter(self):
        self.preparar_nova_leitura()

    def preparar_nova_leitura(self):
        self.mostrar_validacao_api(False)
        self.chave_acesso = None
        self.barcode_input.text = ""
        if self.local:
            self.status_label.text = f"Pronto para bipar para {self.local}."
        else:
            self.status_label.text = "Selecione um local antes de bipar."
        self.barcode_input.focus = False

    def set_local(self, local):
        self.local = local
        self.local_label.text = local
        self.bipes_sequencia = 0
        self.preparar_nova_leitura()

    def limpar_local(self):
        self.local = None
        self.local_label.text = "Nao selecionado"
        self.bipes_sequencia = 0

    def registrar_nota_bipada(self):
        self.bipes_sequencia += 1

    def iniciar_leitura_camera(self, instance):
        if self.validando:
            return
        self.fechar_teclado()
        self.barcode_input.focus = False
        if not self.local:
            self.status_label.text = "Volte e selecione o local antes da leitura."
            return

        if platform != "android":
            self.status_label.text = "A camera para leitura esta disponivel apenas no Android."
            self.barcode_input.focus = False
            return

        self.status_label.text = "Abrindo scanner interno..."
        self.camera_button.disabled = True
        Clock.schedule_once(lambda *_: self.abrir_scanner_interno(), 0.15)

    def fechar_teclado(self):
        self.barcode_input.focus = False
        try:
            Window.release_all_keyboards()
        except Exception:
            pass

        if platform != "android":
            return

        try:
            from jnius import autoclass

            Context = autoclass("android.content.Context")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            InputMethodManager = autoclass("android.view.inputmethod.InputMethodManager")
            activity = PythonActivity.mActivity
            input_method = activity.getSystemService(Context.INPUT_METHOD_SERVICE)
            decor_view = activity.getWindow().getDecorView()
            input_method.hideSoftInputFromWindow(decor_view.getWindowToken(), InputMethodManager.HIDE_NOT_ALWAYS)
        except Exception:
            pass

    def abrir_scanner_interno(self):
        try:
            from jnius import PythonJavaClass, autoclass, java_method

            Barcode = autoclass("com.google.mlkit.vision.barcode.common.Barcode")
            GmsBarcodeScannerOptionsBuilder = autoclass(
                "com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions$Builder"
            )
            GmsBarcodeScanning = autoclass("com.google.mlkit.vision.codescanner.GmsBarcodeScanning")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            screen = self

            class ScanSuccessListener(PythonJavaClass):
                __javainterfaces__ = ["com/google/android/gms/tasks/OnSuccessListener"]
                __javacontext__ = "app"

                @java_method("(Ljava/lang/Object;)V")
                def onSuccess(self, barcode):
                    raw_value = barcode.getRawValue() if barcode else None
                    Clock.schedule_once(lambda *_: screen.processar_codigo_lido(raw_value), 0)

            class ScanCanceledListener(PythonJavaClass):
                __javainterfaces__ = ["com/google/android/gms/tasks/OnCanceledListener"]
                __javacontext__ = "app"

                @java_method("()V")
                def onCanceled(self):
                    Clock.schedule_once(lambda *_: screen.informar_leitura_cancelada(), 0)

            class ScanFailureListener(PythonJavaClass):
                __javainterfaces__ = ["com/google/android/gms/tasks/OnFailureListener"]
                __javacontext__ = "app"

                @java_method("(Ljava/lang/Exception;)V")
                def onFailure(self, exception):
                    Clock.schedule_once(lambda *_: screen.informar_falha_leitura(exception), 0)

            options = (
                GmsBarcodeScannerOptionsBuilder()
                .setBarcodeFormats(
                    Barcode.FORMAT_CODE_128,
                    Barcode.FORMAT_ITF,
                    Barcode.FORMAT_EAN_13,
                    Barcode.FORMAT_EAN_8,
                    Barcode.FORMAT_UPC_A,
                    Barcode.FORMAT_UPC_E,
                )
                .enableAutoZoom()
                .build()
            )
            scanner = GmsBarcodeScanning.getClient(PythonActivity.mActivity, options)
            success_listener = ScanSuccessListener()
            canceled_listener = ScanCanceledListener()
            failure_listener = ScanFailureListener()
            self.scanner_listeners = [success_listener, canceled_listener, failure_listener]
            scanner.startScan().addOnSuccessListener(success_listener).addOnCanceledListener(
                canceled_listener
            ).addOnFailureListener(failure_listener)
            self.status_label.text = "Scanner interno aberto. Aguardando leitura do codigo."
        except Exception as error:
            self.camera_button.disabled = False
            self.status_label.text = (
                "Nao foi possivel abrir o scanner interno. "
                f"Digite a chave manualmente. Detalhe: {error}"
            )
            self.barcode_input.focus = False

    def processar_codigo_lido(self, codigo_lido):
        self.camera_button.disabled = False
        self.scanner_listeners = []
        chave_acesso = self.extrair_chave_acesso(codigo_lido)
        if not chave_acesso:
            self.status_label.text = "Leitura capturada, mas nao encontrei uma chave NF-e com 44 digitos."
            self.barcode_input.focus = False
            return

        self.barcode_input.text = chave_acesso
        self.status_label.text = "Codigo capturado pela camera. Validando nota..."
        Clock.schedule_once(lambda *_: self.processar_codigo_barras(self.barcode_input), 0.1)

    def informar_leitura_cancelada(self):
        self.camera_button.disabled = False
        self.scanner_listeners = []
        self.status_label.text = "Leitura cancelada. Voce pode digitar a chave manualmente."
        self.barcode_input.focus = False

    def informar_falha_leitura(self, exception):
        self.camera_button.disabled = False
        self.scanner_listeners = []
        self.status_label.text = f"Falha no scanner interno. Digite a chave manualmente. Detalhe: {exception}"
        self.barcode_input.focus = False

    @staticmethod
    def extrair_chave_acesso(codigo):
        digitos = re.sub(r"\D", "", str(codigo or ""))
        match = re.search(r"\d{44}", digitos)
        return match.group(0) if match else None

    def processar_codigo_barras(self, instance):
        if self.validando:
            return

        if not self.local:
            self.status_label.text = "Volte e selecione o local antes da leitura."
            return

        codigo_barras = self.barcode_input.text.strip()
        if not codigo_barras:
            self.status_label.text = "Bipe ou digite a chave de acesso da NF-e."
            self.barcode_input.focus = True
            return

        chave_acesso = self.extrair_chave_acesso(codigo_barras)
        if not chave_acesso:
            self.status_label.text = "Codigo invalido: a chave deve conter exatamente 44 digitos."
            self.barcode_input.select_all()
            self.barcode_input.focus = True
            return
        self.barcode_input.text = chave_acesso
        self.status_label.text = "Validando nota na API. Aguarde..."
        self.mostrar_validacao_api(True)
        Thread(target=self.validar_codigo_na_api, args=(chave_acesso,), daemon=True).start()

    def validar_codigo_na_api(self, chave_acesso):
        try:
            result = APIClient.ler_codigo_barras(chave_acesso)
            Clock.schedule_once(lambda *_: self.concluir_validacao_api(result), 0)
        except APIError as error:
            if error.status_code == 404:
                Clock.schedule_once(lambda *_: self.informar_chave_desconhecida(chave_acesso), 0)
                return
            detalhe = str(error)
            Clock.schedule_once(lambda *_, detalhe=detalhe: self.informar_falha_validacao(detalhe), 0)
        except Exception as error:
            detalhe = str(error)
            Clock.schedule_once(lambda *_, detalhe=detalhe: self.informar_falha_validacao(detalhe), 0)

    def informar_chave_desconhecida(self, chave_acesso):
        self.mostrar_validacao_api(False)
        total = self.bipes_sequencia
        nota_texto = "nota bipada" if total == 1 else "notas bipadas"
        self.status_label.text = "Chave de nota desconhecida pela API."
        self.barcode_input.text = chave_acesso
        self.barcode_input.cancel_selection()
        self.barcode_input.focus = False
        self.show_dialog(
            "Chave desconhecida pela API",
            (
                "A chave lida nao foi reconhecida pela API fiscal.\n\n"
                f"Total desta sequencia: {total} {nota_texto}."
            ),
            on_ok=self.encerrar_para_inicio,
        )

    def concluir_validacao_api(self, result):
        self.chave_acesso = result["chave_acesso"]
        self.status_label.text = "Nota consultada. Abrindo conferencia..."
        Clock.schedule_once(lambda *_: self.ir_confirmar(result["nota"]), 0.3)

    def concluir_validacao_com_erro(self, chave_acesso, nota_erro):
        self.informar_falha_validacao(nota_erro.get("erro_consulta") or "Falha ao validar a chave na API fiscal.")

    def informar_falha_validacao(self, detalhe):
        self.mostrar_validacao_api(False)
        total = self.bipes_sequencia
        nota_texto = "nota bipada" if total == 1 else "notas bipadas"
        self.status_label.text = "Nota nao validada pela API fiscal."
        self.show_dialog(
            "Falha na validacao da API",
            (
                "A nota nao foi salva porque a validacao na API fiscal nao foi concluida.\n\n"
                f"Detalhe: {detalhe}\n\n"
                f"Total desta sequencia: {total} {nota_texto}."
            ),
            on_ok=self.encerrar_para_inicio,
        )

    def ir_confirmar(self, nota_data):
        self.mostrar_validacao_api(False)
        nota_data = dict(nota_data)
        nota_data["local"] = self.local
        self.manager.get_screen("confirm").set_nota_data(nota_data)
        self.manager.current = "confirm"

    def voltar(self, instance):
        self.limpar_local()
        self.manager.current = "home"

    def encerrar_para_inicio(self):
        self.limpar_local()
        self.manager.current = "home"

    def show_dialog(self, title, message, on_ok=None):
        if self.dialog:
            self.dialog.dismiss()

        def confirmar(*_):
            self.dialog.dismiss()
            if on_ok:
                on_ok()

        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    theme_text_color="Custom",
                    text_color=PRIMARY,
                    on_release=confirmar,
                )
            ],
        )
        self.dialog.open()
