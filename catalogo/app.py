"""Microsserviço de Catálogo (porta 8001)."""
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from catalogo.dominio import criar_produto
from catalogo.repositorio import RepositorioProdutos

app = FastAPI(title="Serviço de Catálogo")
repo = RepositorioProdutos()


class ProdutoEntrada(BaseModel):
    nome: str
    preco: float
    estoque: int = 0
    categoria: str = "Geral"
    tipo: str = "fisico"  # fisico | digital
    peso_kg: float = 1.0


class Quantidade(BaseModel):
    quantidade: int


def _obter(id):
    produto = repo.buscar_por_id(id)
    if not produto:
        raise HTTPException(404, "Produto não encontrado.")
    return produto


@app.get("/saude")
def saude():
    return {"servico": "catalogo", "status": "ok"}


@app.get("/produtos")
def listar(busca: Optional[str] = None):
    return [p.para_dict() for p in repo.listar(busca)]


@app.get("/produtos/{id}")
def detalhar(id: int):
    return _obter(id).para_dict()


@app.post("/produtos")
def criar(dados: ProdutoEntrada):
    try:
        produto = criar_produto(dados.model_dump())
    except ValueError as erro:
        raise HTTPException(400, str(erro))
    return repo.salvar(produto).para_dict()


@app.put("/produtos/{id}")
def atualizar(id: int, dados: ProdutoEntrada):
    _obter(id)
    try:
        produto = criar_produto(dados.model_dump(), id=id)
    except ValueError as erro:
        raise HTTPException(400, str(erro))
    return repo.salvar(produto).para_dict()


@app.delete("/produtos/{id}")
def remover(id: int):
    _obter(id)
    repo.remover(id)
    return {"removido": id}


@app.post("/produtos/{id}/reservar")
def reservar(id: int, corpo: Quantidade):
    """Chamado pelo serviço de Pedidos: baixa o estoque."""
    produto = _obter(id)
    try:
        produto.reservar(corpo.quantidade)
    except ValueError as erro:
        raise HTTPException(409, str(erro))
    repo.salvar(produto)
    return produto.para_dict()


@app.post("/produtos/{id}/devolver")
def devolver(id: int, corpo: Quantidade):
    """Chamado pelo serviço de Pedidos: devolve o estoque (cancelamento/recusa)."""
    produto = _obter(id)
    produto.devolver(corpo.quantidade)
    repo.salvar(produto)
    return produto.para_dict()
