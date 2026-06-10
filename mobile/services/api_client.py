import json
import os

from kivy.logger import Logger
import requests


class APIClient:
    DEFAULT_BASE_URL = "http://192.168.1.100:8000"
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

        response = cls.session.post(
            f"{base_url}/auth/login/",
            json={"username": cls.APP_USERNAME, "password": cls.APP_PASSWORD},
            timeout=30,
        )
        cls.raise_for_error(response, "/auth/login/")
        cls.authenticated_base_url = base_url
        Logger.info("APIClient: aplicativo autenticado automaticamente como BIPE")

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

            raise RuntimeError(detail or f"Erro HTTP {response.status_code} ao acessar {path}.")

    @classmethod
    def request(cls, method, path, **kwargs):
        cls.authenticate()
        url = f"{cls.get_base_url()}{path}"
        response = cls.session.request(method, url, timeout=30, **kwargs)

        if response.status_code == 401:
            cls.authenticate(force=True)
            response = cls.session.request(method, url, timeout=30, **kwargs)

        cls.raise_for_error(response, path)
        return response

    @staticmethod
    def ler_codigo_barras(codigo_barras):
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
    def list_notas():
        response = APIClient.request("GET", "/notas/")
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
