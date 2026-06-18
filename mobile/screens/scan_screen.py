from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
import re

from services.api_client import APIClient
from ui import BG, INFO, MUTED, PRIMARY, TEXT, WHITE, body_label, outline_button, primary_button, section_card, wrap_label


class ScanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chave_acesso = None
        self.local = None
        self.scanner_listeners = []
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
        content.add_widget(outline_button("Validar codigo digitado", "barcode-scan", self.processar_codigo_barras))
        content.add_widget(outline_button("Voltar ao inicio", "arrow-left", self.voltar))

        scroll.add_widget(content)
        root.add_widget(scroll)
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
        self.barcode_input.focus = False

    def set_local(self, local):
        self.local = local
        self.local_label.text = local
        self.preparar_nova_leitura()

    def limpar_local(self):
        self.local = None
        self.local_label.text = "Nao selecionado"

    def iniciar_leitura_camera(self, instance):
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

        try:
            result = APIClient.ler_codigo_barras(chave_acesso)
            self.chave_acesso = result["chave_acesso"]
            self.status_label.text = "Nota consultada. Abrindo conferencia..."
            Clock.schedule_once(lambda *_: self.ir_confirmar(result["nota"]), 0.3)
        except Exception as error:
            self.chave_acesso = chave_acesso
            self.status_label.text = "API fiscal indisponivel. Abrindo registro de erro..."
            nota_erro = {
                "chave_acesso": chave_acesso,
                "erro_consulta": str(error),
            }
            Clock.schedule_once(lambda *_: self.ir_confirmar(nota_erro), 0.3)

    def ir_confirmar(self, nota_data):
        nota_data = dict(nota_data)
        nota_data["local"] = self.local
        self.manager.get_screen("confirm").set_nota_data(nota_data)
        self.manager.current = "confirm"

    def voltar(self, instance):
        self.limpar_local()
        self.manager.current = "home"
