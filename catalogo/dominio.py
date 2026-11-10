"""Domínio do Catálogo: classes de produto (POO).

- Herança: ProdutoFisico e ProdutoDigital herdam de Produto.
- Polimorfismo: cada tipo calcula frete e controle de estoque do seu jeito.
- Encapsulamento: preço e estoque só mudam por métodos que validam as regras.
"""


class Produto:
    tipo = "generico"

    def __init__(self, nome, preco, estoque=0, categoria="Geral", id=None):
        self.id = id
        self.nome = nome
        self.categoria = categoria
        self.__preco = 0.0
        self.__estoque = 0
        self.definir_preco(preco)
        self.__estoque = max(int(estoque), 0)

    # --- encapsulamento ---
    @property
    def preco(self):
        return self.__preco

    @property
    def estoque(self):
        return self.__estoque

    def definir_preco(self, preco):
        if preco < 0:
            raise ValueError("O preço não pode ser negativo.")
        self.__preco = float(preco)

    def definir_estoque(self, quantidade):
        if quantidade < 0:
            raise ValueError("O estoque não pode ser negativo.")
        self.__estoque = int(quantidade)

    def reservar(self, quantidade):
        """Tira unidades do estoque (usado quando um pedido é criado)."""
        if quantidade <= 0:
            raise ValueError("Quantidade inválida.")
        if self.controla_estoque() and quantidade > self.__estoque:
            raise ValueError(
                f"Estoque insuficiente de '{self.nome}' (disponível: {self.__estoque})."
            )
        if self.controla_estoque():
            self.__estoque -= quantidade

    def devolver(self, quantidade):
        """Devolve unidades ao estoque (pedido cancelado ou pagamento recusado)."""
        if self.controla_estoque():
            self.__estoque += quantidade

    # --- polimorfismo: sobrescrito nas subclasses ---
    def controla_estoque(self):
        return True

    def frete_unitario(self):
        return 0.0

    def para_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "categoria": self.categoria,
            "preco": self.preco,
            "estoque": self.estoque,
            "tipo": self.tipo,
            "peso_kg": getattr(self, "peso_kg", 0.0),
            "frete_unitario": self.frete_unitario(),
        }


class ProdutoFisico(Produto):
    tipo = "fisico"

    def __init__(self, nome, preco, estoque=0, categoria="Geral", peso_kg=1.0, id=None):
        super().__init__(nome, preco, estoque, categoria, id)
        self.peso_kg = float(peso_kg)

    def frete_unitario(self):
        # frete fixo de R$ 10 + R$ 2 por kg
        return 10.0 + 2.0 * self.peso_kg


class ProdutoDigital(Produto):
    tipo = "digital"

    def controla_estoque(self):
        return False  # estoque ilimitado

    def frete_unitario(self):
        return 0.0  # não tem entrega


def criar_produto(dados, id=None):
    """Fábrica: escolhe a subclasse certa de acordo com o tipo."""
    tipo = dados.get("tipo", "fisico")
    if tipo == "digital":
        return ProdutoDigital(
            dados["nome"], dados["preco"], dados.get("estoque", 0),
            dados.get("categoria", "Geral"), id,
        )
    return ProdutoFisico(
        dados["nome"], dados["preco"], dados.get("estoque", 0),
        dados.get("categoria", "Geral"), dados.get("peso_kg", 1.0), id,
    )
