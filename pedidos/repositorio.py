"""Persistência de Pedidos (SQLite próprio do serviço)."""
from comum.banco import BancoSQLite
from pedidos.dominio import ItemPedido, Pedido


class RepositorioPedidos:
    def __init__(self):
        self.banco = BancoSQLite("pedidos.db")
        self.banco.executar(
            """CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                status TEXT NOT NULL,
                metodo_pagamento TEXT,
                pagamento_id INTEGER,
                total_pago REAL DEFAULT 0
            )"""
        )
        colunas = [c["name"] for c in self.banco.consultar("PRAGMA table_info(pedidos)")]
        if "usuario_id" not in colunas:  # bancos criados antes do login
            self.banco.executar("ALTER TABLE pedidos ADD COLUMN usuario_id INTEGER")
        self.banco.executar(
            """CREATE TABLE IF NOT EXISTS itens_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                nome TEXT,
                preco_unitario REAL,
                frete_unitario REAL,
                quantidade INTEGER
            )"""
        )

    def salvar(self, pedido):
        if pedido.id is None:
            pedido.id = self.banco.executar(
                "INSERT INTO pedidos (usuario_id, cliente, status, metodo_pagamento, pagamento_id, total_pago) VALUES (?,?,?,?,?,?)",
                (pedido.usuario_id, pedido.cliente, pedido.status, pedido.metodo_pagamento, pedido.pagamento_id, pedido.total_pago),
            )
            for item in pedido.itens:
                self.banco.executar(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, nome, preco_unitario, frete_unitario, quantidade) VALUES (?,?,?,?,?,?)",
                    (pedido.id, item.produto_id, item.nome, item.preco_unitario, item.frete_unitario, item.quantidade),
                )
        else:
            self.banco.executar(
                "UPDATE pedidos SET status=?, metodo_pagamento=?, pagamento_id=?, total_pago=? WHERE id=?",
                (pedido.status, pedido.metodo_pagamento, pedido.pagamento_id, pedido.total_pago, pedido.id),
            )
        return pedido

    def _montar(self, linha):
        itens_db = self.banco.consultar("SELECT * FROM itens_pedido WHERE pedido_id = ?", (linha["id"],))
        itens = [
            ItemPedido(i["produto_id"], i["nome"], i["preco_unitario"], i["quantidade"], i["frete_unitario"])
            for i in itens_db
        ]
        pedido = Pedido(linha["cliente"], itens, id=linha["id"], usuario_id=linha["usuario_id"])
        pedido.status = linha["status"]
        pedido.metodo_pagamento = linha["metodo_pagamento"] or ""
        pedido.pagamento_id = linha["pagamento_id"]
        pedido.total_pago = linha["total_pago"] or 0.0
        return pedido

    def buscar_por_id(self, id):
        linha = self.banco.consultar_um("SELECT * FROM pedidos WHERE id = ?", (id,))
        return self._montar(linha) if linha else None

    def listar(self, usuario_id=None):
        """Todos os pedidos; com usuario_id, só os desse usuário."""
        if usuario_id is None:
            linhas = self.banco.consultar("SELECT * FROM pedidos ORDER BY id DESC")
        else:
            linhas = self.banco.consultar("SELECT * FROM pedidos WHERE usuario_id = ? ORDER BY id DESC", (usuario_id,))
        return [self._montar(l) for l in linhas]
