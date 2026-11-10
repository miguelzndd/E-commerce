"""Microsserviço de Pagamentos (porta 8003)."""
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from comum.banco import BancoSQLite
from pagamentos.dominio import criar_pagamento

app = FastAPI(title="Serviço de Pagamentos")

banco = BancoSQLite("pagamentos.db")
banco.executar(
    """CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        metodo TEXT,
        valor REAL,
        valor_final REAL,
        status TEXT,
        detalhe TEXT
    )"""
)


class PagamentoEntrada(BaseModel):
    pedido_id: int
    valor: float
    metodo: str  # cartao | pix | boleto
    parcelas: int = 1
    numero_cartao: Optional[str] = ""


@app.get("/saude")
def saude():
    return {"servico": "pagamentos", "status": "ok"}


@app.post("/pagamentos")
def pagar(dados: PagamentoEntrada):
    try:
        pagamento = criar_pagamento(dados.model_dump())
    except ValueError as erro:
        raise HTTPException(400, str(erro))

    pagamento.processar()  # polimorfismo: cada método aplica a sua regra
    pagamento.id = banco.executar(
        "INSERT INTO pagamentos (pedido_id, metodo, valor, valor_final, status, detalhe) VALUES (?,?,?,?,?,?)",
        (pagamento.pedido_id, pagamento.metodo, pagamento.valor,
         pagamento.valor_final, pagamento.status, pagamento.detalhe),
    )
    return pagamento.para_dict()


@app.get("/pagamentos/{id}")
def detalhar(id: int):
    linha = banco.consultar_um("SELECT * FROM pagamentos WHERE id = ?", (id,))
    if not linha:
        raise HTTPException(404, "Pagamento não encontrado.")
    return linha


@app.post("/pagamentos/{id}/estornar")
def estornar(id: int):
    linha = banco.consultar_um("SELECT * FROM pagamentos WHERE id = ?", (id,))
    if not linha:
        raise HTTPException(404, "Pagamento não encontrado.")
    if linha["status"] != "aprovado":
        raise HTTPException(409, "Só é possível estornar pagamentos aprovados.")
    banco.executar(
        "UPDATE pagamentos SET status='estornado', detalhe='Pagamento estornado.' WHERE id=?", (id,)
    )
    return banco.consultar_um("SELECT * FROM pagamentos WHERE id = ?", (id,))
