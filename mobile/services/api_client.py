import json
import os

from kivy.logger import Logger
import requests


class APIClient:
    DEFAULT_BASE_URL = "http://192.168.1.100:8000"

    @staticmethod
    def get_base_url():
        env_url = os.environ.get("NFE_API_URL")
        if env_url:
            return env_url.rstrip("/")

        config_path = os.path.join(os.getcwd(), "api_config.json")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as config_file:
                    data = json.load(config_file)
                return data.get("base_url", APIClient.DEFAULT_BASE_URL).rstrip("/")
            except Exception as error:
                Logger.warning(f"APIClient: erro ao ler api_config.json: {error}")

        return APIClient.DEFAULT_BASE_URL

    @staticmethod
    def request(method, path, **kwargs):
        url = f"{APIClient.get_base_url()}{path}"
        response = requests.request(method, url, timeout=30, **kwargs)
        response.raise_for_status()
        return response

    @staticmethod
    def ocr_nf(image_path):
        with open(image_path, "rb") as file_obj:
            files = {"file": ("nota.jpg", file_obj, "image/jpeg")}
            response = APIClient.request("POST", "/ocr-nf/", files=files)
        return response.json()

    @staticmethod
    def save_nota(nota_data):
        response = APIClient.request("POST", "/notas/", json=nota_data)
        return response.json()

    @staticmethod
    def upload_nf(image_path):
        with open(image_path, "rb") as file_obj:
            files = {"file": ("nota.jpg", file_obj, "image/jpeg")}
            response = APIClient.request("POST", "/upload-nf/", files=files)
        return response.json()

    @staticmethod
    def list_notas():
        response = APIClient.request("GET", "/notas/")
        return response.json()

    @staticmethod
    def gerar_relatorio(filtros, formato="xml"):
        params = {
            "data_inicio": filtros.get("data_inicio"),
            "data_fim": filtros.get("data_fim"),
            "fornecedor": filtros.get("fornecedor"),
            "valor_min": filtros.get("valor_min"),
            "valor_max": filtros.get("valor_max"),
            "formato": formato,
        }

        return APIClient.request("POST", "/relatorio/", params=params)