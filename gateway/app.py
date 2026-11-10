"""API Gateway (porta 8000): ponto de entrada único da Pocket.

O gateway também entrega a interface web (pasta web/) em http://127.0.0.1:8000.
A página fala só com o gateway. Ele recebe chamadas no formato
    /api/<servico>/<caminho>
e encaminha para o microsserviço certo:
    /api/catalogo/produtos   ->  Catálogo   /produtos
    /api/pedidos/pedidos     ->  Pedidos    /pedidos
    /api/pagamentos/...      ->  Pagamentos /...

A comunicação entre serviços (Pedidos -> Catálogo, Pedidos -> Pagamentos)
continua direta, sem passar pelo gateway.
"""
import os
from urllib.parse import quote

import requests
from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from comum.cliente_http import URL_CATALOGO, URL_PAGAMENTOS, URL_PEDIDOS, URL_USUARIOS

app = FastAPI(title="API Gateway")

PASTA_WEB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")

DESTINOS = {
    "catalogo": URL_CATALOGO,
    "pedidos": URL_PEDIDOS,
    "pagamentos": URL_PAGAMENTOS,
    "usuarios": URL_USUARIOS,
}

PUBLICO, LOGADO, ADMIN = "publico", "logado", "administrador"


def nivel_exigido(servico, metodo, caminho):
    """Quem pode chamar cada rota: qualquer pessoa, usuário logado ou administrador."""
    if servico == "usuarios":
        if metodo == "POST" and caminho in ("login", "cadastro"):
            return PUBLICO
        if metodo == "GET" and caminho == "eu":
            return LOGADO
        return ADMIN
    if servico == "catalogo":
        return PUBLICO if metodo == "GET" else ADMIN
    if servico == "pedidos":
        return ADMIN if caminho.endswith("/avancar") else LOGADO
    return ADMIN  # pagamentos: só uso administrativo (Pedidos fala direto com ele)


def identificar(authorization):
    """Pergunta ao serviço de Usuários quem é o dono do token. Devolve (usuario, erro)."""
    if not authorization:
        return None, JSONResponse({"detail": "Faça login para continuar."}, status_code=401)
    try:
        r = requests.get(URL_USUARIOS + "/eu", headers={"Authorization": authorization}, timeout=3)
    except requests.exceptions.RequestException:
        return None, JSONResponse({"detail": "Serviço indisponível: usuarios"}, status_code=503)
    if r.status_code != 200:
        return None, JSONResponse({"detail": "Sessão inválida ou expirada. Entre de novo."}, status_code=401)
    return r.json(), None


@app.get("/saude")
def saude():
    """Mostra se o gateway e cada serviço por trás dele estão respondendo."""
    estado = {}
    for nome, url in DESTINOS.items():
        try:
            requests.get(url + "/saude", timeout=2).raise_for_status()
            estado[nome] = "ok"
        except requests.exceptions.RequestException:
            estado[nome] = "indisponivel"
    return {"servico": "gateway", "status": "ok", "servicos": estado}


@app.api_route("/api/{servico}/{caminho:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def encaminhar(servico: str, caminho: str, request: Request):
    destino = DESTINOS.get(servico)
    if destino is None:
        return JSONResponse({"detail": f"Serviço desconhecido: {servico}"}, status_code=404)

    nivel = nivel_exigido(servico, request.method, caminho)
    usuario = None
    if nivel != PUBLICO:
        usuario, erro = await run_in_threadpool(identificar, request.headers.get("authorization"))
        if erro:
            return erro
        if nivel == ADMIN and usuario["perfil"] != "administrador":
            return JSONResponse({"detail": "Acesso restrito ao administrador."}, status_code=403)

    corpo = await request.body()
    cabecalhos = {"Content-Type": request.headers.get("content-type", "application/json")}
    if servico == "usuarios" and request.headers.get("authorization"):
        cabecalhos["Authorization"] = request.headers["authorization"]
    if usuario:  # identidade que os serviços de dentro podem confiar (vem só do gateway)
        cabecalhos["X-Usuario-Id"] = str(usuario["id"])
        cabecalhos["X-Usuario-Nome"] = quote(usuario["nome"])
        cabecalhos["X-Usuario-Perfil"] = usuario["perfil"]
    try:
        resposta = await run_in_threadpool(
            requests.request,
            request.method,
            f"{destino}/{caminho}",
            params=dict(request.query_params),
            data=corpo,
            headers=cabecalhos,
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return JSONResponse({"detail": f"Serviço indisponível: {servico}"}, status_code=503)

    return Response(
        content=resposta.content,
        status_code=resposta.status_code,
        media_type=resposta.headers.get("content-type", "application/json"),
    )


# Interface web: a página da loja é entregue pelo próprio gateway em "/".
# Fica por último para não esconder as rotas /saude e /api/...
app.mount("/", StaticFiles(directory=PASTA_WEB, html=True), name="web")
