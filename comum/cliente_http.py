"""Componente comum: cliente HTTP para um serviço chamar outro (ou a interface chamar os serviços)."""
import os

import requests


class ErroServico(Exception):
    """Erro devolvido por um serviço ou falha de comunicação com ele."""

    def __init__(self, mensagem, status=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class ClienteServico:
    def __init__(self, url_base, timeout=5, cabecalhos=None):
        self.url_base = url_base.rstrip("/")
        self.timeout = timeout
        self.cabecalhos = cabecalhos or {}  # ex.: {"Authorization": "Bearer ..."}

    def _requisicao(self, metodo, caminho, **kwargs):
        try:
            resposta = requests.request(
                metodo, self.url_base + caminho, timeout=self.timeout, headers=self.cabecalhos, **kwargs
            )
        except requests.exceptions.RequestException:
            raise ErroServico(f"Serviço indisponível: {self.url_base}", status=503)

        if resposta.status_code >= 400:
            try:
                detalhe = resposta.json().get("detail", resposta.text)
            except ValueError:
                detalhe = resposta.text
            raise ErroServico(str(detalhe), status=resposta.status_code)
        return resposta.json()

    def get(self, caminho, params=None):
        return self._requisicao("GET", caminho, params=params)

    def post(self, caminho, corpo=None):
        return self._requisicao("POST", caminho, json=corpo or {})

    def put(self, caminho, corpo=None):
        return self._requisicao("PUT", caminho, json=corpo or {})

    def delete(self, caminho):
        return self._requisicao("DELETE", caminho)


# Endereços dos serviços. Local: portas fixas. No Docker Compose, as variáveis
# de ambiente trocam 127.0.0.1 pelo nome do container (ex.: http://catalogo:8001).
URL_GATEWAY = os.getenv("URL_GATEWAY", "http://127.0.0.1:8000")
URL_CATALOGO = os.getenv("URL_CATALOGO", "http://127.0.0.1:8001")
URL_PEDIDOS = os.getenv("URL_PEDIDOS", "http://127.0.0.1:8002")
URL_PAGAMENTOS = os.getenv("URL_PAGAMENTOS", "http://127.0.0.1:8003")
URL_USUARIOS = os.getenv("URL_USUARIOS", "http://127.0.0.1:8004")
