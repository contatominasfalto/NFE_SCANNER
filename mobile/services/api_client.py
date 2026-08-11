import json
import os

from kivy.logger import Logger
import requests


class APIError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    DEFAULT_BASE_URL = "https://nfe-scanner-api.onrender.com"
    APP_USERNAME = "BIPE"
    APP_PASSWORD = "BIPE"
    session = requests.Session()
    authenticated_base_url = None

    @staticmethod
    def get_base_url():
        env_url = os.environ.get("NFE_API_URL")
        if env_url:
            return env_url.rstrip("/")

        mobile_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(mobile_dir, "api_config.json")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as config_file:
                    data = json.load(config_file)
                return data.get("base_url", APIClient.DEFAULT_BASE_URL).rstrip("/")
            except Exception as error:
                Logger.warning(f"APIClient: erro ao ler api_config.json: {error}")

        return APIClient.DEFAULT_BASE_URL

    @classmethod
    def authenticate(cls, force=False):
        base_url = cls.get_base_url()
        if not force and cls.authenticated_base_url == base_url:
            return

        if force or cls.authenticated_base_url != base_url:
            cls.session.cookies.clear()

        try:
            response = cls.session.post(
                f"{base_url}/auth/login/",
                json={"username": cls.APP_USERNAME, "password": cls.APP_PASSWORD},
                timeout=30,
            )
        except requests.exceptions.RequestException as error:
            raise APIError(cls.connection_error_message(base_url, error)) from error
        cls.raise_for_error(response, "/auth/login/")
        cls.authenticated_base_url = base_url
        Logger.info("APIClient: aplicativo autenticado automaticamente como BIPE")

    @staticmethod
    def connection_error_message(base_url, error):
        return (
            f"Nao foi possivel conectar ao servidor da API em {base_url}. "
            "Confira se o backend esta rodando com --host 0.0.0.0, se o celular esta na mesma rede "
            "ou se o DDNS e a porta 8000 estao liberados no roteador/firewall. "
            f"Detalhe: {error}"
        )

    @staticmethod
    def raise_for_error(response, path):
        if not response.ok:
            detail = None
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = response.text.strip()

            if isinstance(detail, list):
                messages = []
                for item in detail:
                    location = ".".join(str(part) for part in item.get("loc", [])[1:])
                    message = item.get("msg", "valor invalido")
                    messages.append(f"{location}: {message}" if location else message)
                detail = "; ".join(messages)

            raise APIError(
                detail or f"Erro HTTP {response.status_code} ao acessar {path}.",
                response.status_code,
            )

    @classmethod
    def request(cls, method, path, **kwargs):
        cls.authenticate()
        url = f"{cls.get_base_url()}{path}"
        try:
            response = cls.session.request(method, url, timeout=30, **kwargs)
        except requests.exceptions.RequestException as error:
            raise APIError(cls.connection_error_message(cls.get_base_url(), error)) from error

        if response.status_code == 401:
            cls.authenticate(force=True)
            try:
                response = cls.session.request(method, url, timeout=30, **kwargs)
            except requests.exceptions.RequestException as error:
                raise APIError(cls.connection_error_message(cls.get_base_url(), error)) from error

        cls.raise_for_error(response, path)
        return response

    @staticmethod
    def ler_codigo_barras(codigo_barras):
        APIClient.sync_pending_errors()
        response = APIClient.request(
            "POST",
            "/barcode-nf/",
            json={"codigo_barras": codigo_barras},
        )
        return response.json()

    @staticmethod
    def save_nota(nota_data):
        response = APIClient.request("POST", "/notas/", json=nota_data)
        return response.json()

    @staticmethod
    def save_nota_com_fallback(nota_data):
        return APIClient.save_nota(nota_data)

    @staticmethod
    def save_nota_erro_com_fallback(erro_data):
        raise APIError("Nota nao salva: a chave precisa ser validada pela API fiscal antes do cadastro.")

    @staticmethod
    def get_pending_errors_path():
        configured_path = os.environ.get("NFE_PENDING_ERRORS_PATH")
        if configured_path:
            return configured_path
        try:
            from kivy.app import App

            app = App.get_running_app()
            base_dir = app.user_data_dir if app else os.path.join(os.path.expanduser("~"), ".nfe_scanner")
        except Exception:
            base_dir = os.path.join(os.path.expanduser("~"), ".nfe_scanner")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "pending_save_errors.json")

    @staticmethod
    def load_pending_errors():
        path = APIClient.get_pending_errors_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as pending_file:
                data = json.load(pending_file)
            return data if isinstance(data, list) else []
        except Exception as error:
            Logger.warning(f"APIClient: erro ao ler fila de falhas: {error}")
            return []

    @staticmethod
    def save_pending_errors(errors):
        path = APIClient.get_pending_errors_path()
        with open(path, "w", encoding="utf-8") as pending_file:
            json.dump(errors, pending_file, ensure_ascii=True, indent=2)

    @staticmethod
    def queue_pending_error(erro_data):
        errors = APIClient.load_pending_errors()
        errors = [item for item in errors if item.get("chave_acesso") != erro_data.get("chave_acesso")]
        errors.append(erro_data)
        APIClient.save_pending_errors(errors)
        Logger.warning(f"APIClient: falha enfileirada para sincronizacao: {erro_data.get('chave_acesso')}")

    @staticmethod
    def sync_pending_errors():
        errors = APIClient.load_pending_errors()
        if not errors:
            return
        APIClient.save_pending_errors([])
        Logger.warning("APIClient: fila antiga de notas com erro descartada; app salva apenas notas validadas.")

    @staticmethod
    def list_notas(skip=0, limit=100, data_cadastro_inicio=None, data_cadastro_fim=None):
        APIClient.sync_pending_errors()
        params = {"skip": skip, "limit": limit}
        if data_cadastro_inicio:
            params["data_cadastro_inicio"] = data_cadastro_inicio
        if data_cadastro_fim:
            params["data_cadastro_fim"] = data_cadastro_fim
        response = APIClient.request("GET", "/notas/", params=params)
        return response.json()

    @staticmethod
    def gerar_relatorio(filtros, formato="xml"):
        params = {
            "nota_id": filtros.get("nota_id"),
            "data_inicio": filtros.get("data_inicio"),
            "data_fim": filtros.get("data_fim"),
            "fornecedor": filtros.get("fornecedor"),
            "valor_min": filtros.get("valor_min"),
            "valor_max": filtros.get("valor_max"),
            "formato": formato,
        }

        return APIClient.request("POST", "/relatorio/", params=params)

    @staticmethod
    def gerar_xml_nota(nota_id):
        return APIClient.gerar_relatorio({"nota_id": nota_id}, "xml")
