"""Persistência do Catálogo (SQLite próprio do serviço)."""
from comum.banco import BancoSQLite
from catalogo.dominio import criar_produto


class RepositorioProdutos:
    def __init__(self):
        self.banco = BancoSQLite("catalogo.db")
        self.banco.executar(
            """CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT,
                preco REAL NOT NULL,
                estoque INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                peso_kg REAL DEFAULT 0
            )"""
        )
        self._popular_exemplos()

    def _popular_exemplos(self):
        if self.banco.consultar_um("SELECT id FROM produtos LIMIT 1"):
            return
        exemplos = [
            {"nome": "Mouse Gamer", "preco": 89.90, "estoque": 20, "categoria": "Informática", "peso_kg": 0.3},
            {"nome": "Teclado Mecânico", "preco": 249.90, "estoque": 10, "categoria": "Informática", "peso_kg": 0.9},
            {"nome": "Fone Bluetooth", "preco": 159.00, "estoque": 15, "categoria": "Áudio", "peso_kg": 0.2},
            {"nome": "Monitor 24 pol", "preco": 899.00, "estoque": 5, "categoria": "Informática", "peso_kg": 4.5},
            {"nome": "E-book Python", "preco": 39.90, "estoque": 0, "categoria": "Livros", "tipo": "digital"},
        ]
        for dados in exemplos:
            self.salvar(criar_produto(dados))

    def _montar(self, linha):
        return criar_produto(linha, id=linha["id"])

    def listar(self, busca=None):
        if busca:
            linhas = self.banco.consultar(
                "SELECT * FROM produtos WHERE LOWER(nome) LIKE ? ORDER BY nome",
                (f"%{busca.lower()}%",),
            )
        else:
            linhas = self.banco.consultar("SELECT * FROM produtos ORDER BY nome")
        return [self._montar(l) for l in linhas]

    def buscar_por_id(self, id):
        linha = self.banco.consultar_um("SELECT * FROM produtos WHERE id = ?", (id,))
        return self._montar(linha) if linha else None

    def salvar(self, produto):
        """Insere (id None) ou atualiza o produto."""
        peso = getattr(produto, "peso_kg", 0.0)
        if produto.id is None:
            produto.id = self.banco.executar(
                "INSERT INTO produtos (nome, categoria, preco, estoque, tipo, peso_kg) VALUES (?,?,?,?,?,?)",
                (produto.nome, produto.categoria, produto.preco, produto.estoque, produto.tipo, peso),
            )
        else:
            self.banco.executar(
                "UPDATE produtos SET nome=?, categoria=?, preco=?, estoque=?, tipo=?, peso_kg=? WHERE id=?",
                (produto.nome, produto.categoria, produto.preco, produto.estoque, produto.tipo, peso, produto.id),
            )
        return produto

    def remover(self, id):
        self.banco.executar("DELETE FROM produtos WHERE id = ?", (id,))
