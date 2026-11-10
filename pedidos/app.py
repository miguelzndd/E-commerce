"""Microsserviço de Pedidos (porta 8002).

É o orquestrador: ao criar um pedido ele chama o Catálogo (reservar
estoque) e o serviço de Pagamentos (cobrar). Se algo falhar no meio do
caminho, desfaz o que já fez (devolve o estoque).
"""
from typing import List, Optional
from urllib.parse import unquote

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from comum.cliente_http import (
    URL_CATALOGO, URL_PAGAMENTOS, ClienteServico, ErroServico,
)
from pedidos.dominio import ItemPedido, Pedido
from pedidos.repositorio import RepositorioPedidos

app = FastAPI(title="Serviço de Pedidos")
repo = RepositorioPedidos()
catalogo = ClienteServico(URL_CATALOGO)
pagamentos = ClienteServico(URL_PAGAMENTOS)


class ItemEntrada(BaseModel):
    produto_id: int
    quantidade: int


class PedidoEntrada(BaseModel):
    itens: List[ItemEntrada]
    metodo_pagamento: str  # cartao | pix | boleto
    parcelas: int = 1
    numero_cartao: Optional[str] = ""


class Identidade:
    """Quem está fazendo a chamada. O gateway valida o token e envia estes cabeçalhos."""

    def __init__(self, id, nome, perfil):
        self.id, self.nome, self.perfil = id, nome, perfil

    @property
    def admin(self):
        return self.perfil == "administrador"

    def pode_ver(self, pedido):
        return self.admin or pedido.usuario_id == self.id


def identificar(x_usuario_id, x_usuario_nome, x_usuario_perfil):
    if not x_usuario_id or not x_usuario_id.isdigit():
        raise HTTPException(401, "Faça login para continuar.")
    return Identidade(int(x_usuario_id), unquote(x_usuario_nome or ""), x_usuario_perfil or "cliente")


def _pedido_do_usuario(id, quem):
    pedido = repo.buscar_por_id(id)
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado.")
    if not quem.pode_ver(pedido):
        raise HTTPException(403, "Você não tem acesso a este pedido.")
    return pedido


def _devolver_estoque(reservados):
    """Desfaz reservas já feitas no catálogo (compensação)."""
    for produto_id, quantidade in reservados:
        try:
            catalogo.post(f"/produtos/{produto_id}/devolver", {"quantidade": quantidade})
        except ErroServico:
            pass  # em um sistema real, isso iria para uma fila de retentativa


@app.get("/saude")
def saude():
    return {"servico": "pedidos", "status": "ok"}


@app.post("/pedidos")
def criar_pedido(
    dados: PedidoEntrada,
    x_usuario_id: Optional[str] = Header(None),
    x_usuario_nome: Optional[str] = Header(None),
    x_usuario_perfil: Optional[str] = Header(None),
):
    quem = identificar(x_usuario_id, x_usuario_nome, x_usuario_perfil)
    if not dados.itens:
        raise HTTPException(400, "O pedido precisa de pelo menos um item.")

    itens = []
    reservados = []  # (produto_id, quantidade) já reservados no catálogo

    # 1) Reservar estoque de cada item no Catálogo
    try:
        for entrada in dados.itens:
            if entrada.quantidade <= 0:
                raise HTTPException(400, "Quantidade inválida.")
            produto = catalogo.get(f"/produtos/{entrada.produto_id}")
            catalogo.post(f"/produtos/{entrada.produto_id}/reservar", {"quantidade": entrada.quantidade})
            reservados.append((entrada.produto_id, entrada.quantidade))
            itens.append(ItemPedido(
                produto["id"], produto["nome"], produto["preco"],
                entrada.quantidade, produto["frete_unitario"],
            ))
    except ErroServico as erro:
        _devolver_estoque(reservados)
        raise HTTPException(erro.status or 502, erro.mensagem)
    except HTTPException:
        _devolver_estoque(reservados)
        raise

    pedido = Pedido(quem.nome, itens, usuario_id=quem.id)
    pedido.metodo_pagamento = dados.metodo_pagamento
    repo.salvar(pedido)  # gera o id do pedido

    # 2) Cobrar no serviço de Pagamentos
    try:
        pagamento = pagamentos.post("/pagamentos", {
            "pedido_id": pedido.id,
            "valor": pedido.total(),
            "metodo": dados.metodo_pagamento,
            "parcelas": dados.parcelas,
            "numero_cartao": dados.numero_cartao or "",
        })
    except ErroServico as erro:
        _devolver_estoque(reservados)
        pedido.status = "falhou"
        repo.salvar(pedido)
        raise HTTPException(erro.status or 502, f"Falha no pagamento: {erro.mensagem}")

    pedido.pagamento_id = pagamento["id"]
    if pagamento["status"] == "aprovado":
        pedido.status = "pago"
        pedido.total_pago = pagamento["valor_final"]
    else:
        pedido.status = "pagamento_recusado"
        _devolver_estoque(reservados)  # recusado: devolve o estoque

    repo.salvar(pedido)
    resposta = pedido.para_dict()
    resposta["mensagem_pagamento"] = pagamento["detalhe"]
    return resposta


@app.get("/pedidos")
def listar(
    x_usuario_id: Optional[str] = Header(None),
    x_usuario_nome: Optional[str] = Header(None),
    x_usuario_perfil: Optional[str] = Header(None),
):
    quem = identificar(x_usuario_id, x_usuario_nome, x_usuario_perfil)
    pedidos = repo.listar() if quem.admin else repo.listar(usuario_id=quem.id)
    return [p.para_dict() for p in pedidos]


@app.get("/pedidos/{id}")
def detalhar(
    id: int,
    x_usuario_id: Optional[str] = Header(None),
    x_usuario_nome: Optional[str] = Header(None),
    x_usuario_perfil: Optional[str] = Header(None),
):
    quem = identificar(x_usuario_id, x_usuario_nome, x_usuario_perfil)
    return _pedido_do_usuario(id, quem).para_dict()


@app.post("/pedidos/{id}/avancar")
def avancar(
    id: int,
    x_usuario_id: Optional[str] = Header(None),
    x_usuario_nome: Optional[str] = Header(None),
    x_usuario_perfil: Optional[str] = Header(None),
):
    quem = identificar(x_usuario_id, x_usuario_nome, x_usuario_perfil)
    if not quem.admin:
        raise HTTPException(403, "Só o administrador pode avançar o status do pedido.")
    pedido = _pedido_do_usuario(id, quem)
    try:
        pedido.avancar()
    except ValueError as erro:
        raise HTTPException(409, str(erro))
    repo.salvar(pedido)
    return pedido.para_dict()


@app.post("/pedidos/{id}/cancelar")
def cancelar(
    id: int,
    x_usuario_id: Optional[str] = Header(None),
    x_usuario_nome: Optional[str] = Header(None),
    x_usuario_perfil: Optional[str] = Header(None),
):
    quem = identificar(x_usuario_id, x_usuario_nome, x_usuario_perfil)
    pedido = _pedido_do_usuario(id, quem)  # cliente só cancela o próprio pedido
    try:
        pedido.cancelar()
    except ValueError as erro:
        raise HTTPException(409, str(erro))

    # estorna o pagamento e devolve o estoque
    try:
        pagamentos.post(f"/pagamentos/{pedido.pagamento_id}/estornar")
    except ErroServico as erro:
        raise HTTPException(erro.status or 502, f"Não foi possível estornar: {erro.mensagem}")
    _devolver_estoque([(i.produto_id, i.quantidade) for i in pedido.itens])

    repo.salvar(pedido)
    return pedido.para_dict()
