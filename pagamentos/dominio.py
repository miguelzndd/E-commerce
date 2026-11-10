"""Domínio de Pagamentos (POO).

Pagamento é uma classe abstrata. Cada forma de pagamento (cartão, Pix,
boleto) herda dela e implementa o seu próprio processar() — polimorfismo:
o serviço chama pagamento.processar() sem saber qual é o tipo concreto.

Os pagamentos são simulados (não há operadora real).
"""
from abc import ABC, abstractmethod


class Pagamento(ABC):
    metodo = "generico"

    def __init__(self, pedido_id, valor, id=None):
        self.id = id
        self.pedido_id = pedido_id
        self.valor = float(valor)
        self.valor_final = float(valor)
        self.status = "pendente"  # pendente | aprovado | recusado | estornado
        self.detalhe = ""

    @abstractmethod
    def processar(self):
        """Aplica as regras do método e define status, valor_final e detalhe."""

    def estornar(self):
        if self.status != "aprovado":
            raise ValueError("Só é possível estornar pagamentos aprovados.")
        self.status = "estornado"
        self.detalhe = "Pagamento estornado."

    def para_dict(self):
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "metodo": self.metodo,
            "valor": self.valor,
            "valor_final": self.valor_final,
            "status": self.status,
            "detalhe": self.detalhe,
        }


class PagamentoCartao(Pagamento):
    metodo = "cartao"
    LIMITE_SIMULADO = 5000.0

    def __init__(self, pedido_id, valor, parcelas=1, numero_cartao="", id=None):
        super().__init__(pedido_id, valor, id)
        self.parcelas = int(parcelas)
        self.numero_cartao = numero_cartao

    def processar(self):
        digitos = "".join(c for c in self.numero_cartao if c.isdigit())
        if len(digitos) < 12:
            self.status, self.detalhe = "recusado", "Número de cartão inválido."
        elif not 1 <= self.parcelas <= 12:
            self.status, self.detalhe = "recusado", "Parcelas devem ser de 1 a 12."
        elif digitos.endswith("0000"):
            self.status, self.detalhe = "recusado", "Cartão recusado pela operadora (simulação)."
        elif self.valor > self.LIMITE_SIMULADO:
            self.status, self.detalhe = "recusado", "Limite do cartão excedido (simulação)."
        else:
            self.status = "aprovado"
            valor_parcela = self.valor / self.parcelas
            self.detalhe = f"Aprovado em {self.parcelas}x de R$ {valor_parcela:.2f} (cartão final {digitos[-4:]})."


class PagamentoPix(Pagamento):
    metodo = "pix"
    DESCONTO = 0.05

    def processar(self):
        self.valor_final = round(self.valor * (1 - self.DESCONTO), 2)
        self.status = "aprovado"
        self.detalhe = "Aprovado via Pix com 5% de desconto."


class PagamentoBoleto(Pagamento):
    metodo = "boleto"

    def processar(self):
        self.status = "aprovado"
        self.detalhe = "Boleto compensado (simulação)."


def criar_pagamento(dados):
    """Fábrica: devolve a subclasse correspondente ao método escolhido."""
    metodo = dados["metodo"]
    if metodo == "cartao":
        return PagamentoCartao(
            dados["pedido_id"], dados["valor"],
            dados.get("parcelas", 1), dados.get("numero_cartao", ""),
        )
    if metodo == "pix":
        return PagamentoPix(dados["pedido_id"], dados["valor"])
    if metodo == "boleto":
        return PagamentoBoleto(dados["pedido_id"], dados["valor"])
    raise ValueError(f"Método de pagamento desconhecido: {metodo}")
