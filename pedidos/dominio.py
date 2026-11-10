"""Domínio de Pedidos (POO).

O Pedido controla o próprio ciclo de vida: só pode mudar de status
seguindo as transições permitidas (encapsulamento das regras).
"""


class ItemPedido:
    def __init__(self, produto_id, nome, preco_unitario, quantidade, frete_unitario=0.0):
        self.produto_id = produto_id
        self.nome = nome
        self.preco_unitario = float(preco_unitario)
        self.quantidade = int(quantidade)
        self.frete_unitario = float(frete_unitario)

    def subtotal(self):
        return self.preco_unitario * self.quantidade

    def frete(self):
        return self.frete_unitario * self.quantidade

    def para_dict(self):
        return {
            "produto_id": self.produto_id,
            "nome": self.nome,
            "preco_unitario": self.preco_unitario,
            "quantidade": self.quantidade,
            "subtotal": self.subtotal(),
        }


class Pedido:
    # status -> próximo status permitido ao avançar
    PROXIMO = {"pago": "enviado", "enviado": "entregue"}
    # status em que o cancelamento ainda é permitido
    CANCELAVEIS = ("pago",)

    def __init__(self, cliente, itens, id=None, usuario_id=None):
        self.id = id
        self.usuario_id = usuario_id  # dono do pedido (serviço de Usuários)
        self.cliente = cliente
        self.itens = itens
        self.status = "criado"
        self.metodo_pagamento = ""
        self.pagamento_id = None
        self.total_pago = 0.0

    def subtotal(self):
        return sum(i.subtotal() for i in self.itens)

    def frete(self):
        return sum(i.frete() for i in self.itens)

    def total(self):
        return self.subtotal() + self.frete()

    def pode_cancelar(self):
        return self.status in self.CANCELAVEIS

    def avancar(self):
        if self.status not in self.PROXIMO:
            raise ValueError(f"Pedido com status '{self.status}' não pode avançar.")
        self.status = self.PROXIMO[self.status]

    def cancelar(self):
        if not self.pode_cancelar():
            raise ValueError(f"Pedido com status '{self.status}' não pode ser cancelado.")
        self.status = "cancelado"

    def para_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "cliente": self.cliente,
            "status": self.status,
            "itens": [i.para_dict() for i in self.itens],
            "subtotal": self.subtotal(),
            "frete": self.frete(),
            "total": self.total(),
            "metodo_pagamento": self.metodo_pagamento,
            "pagamento_id": self.pagamento_id,
            "total_pago": self.total_pago,
        }
