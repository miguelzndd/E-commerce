"""Persistência de Usuários (SQLite próprio do serviço)."""
from comum.banco import BancoSQLite
from usuarios.dominio import criar_usuario, gerar_hash

import os

# Administrador primário (criado na primeira execução). Dá para trocar por variável de ambiente.
ADMIN_NOME = os.environ.get("POCKET_ADMIN_NOME", "Mats")
ADMIN_EMAIL = os.environ.get("POCKET_ADMIN_EMAIL", "mats@ufal.com").strip().lower()
ADMIN_SENHA = os.environ.get("POCKET_ADMIN_SENHA", "TJAGSMVTAFGJP")


class RepositorioUsuarios:
    def __init__(self):
        self.banco = BancoSQLite("usuarios.db")
        self.banco.executar(
            """CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL
            )"""
        )
        self._criar_admin_padrao()

    def _criar_admin_padrao(self):
        existe = self.banco.consultar_um("SELECT id FROM usuarios WHERE perfil = 'administrador'")
        if not existe:
            self.banco.executar(
                "INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (?,?,?,?)",
                (ADMIN_NOME, ADMIN_EMAIL, gerar_hash(ADMIN_SENHA), "administrador"),
            )

    def _montar(self, linha):
        return criar_usuario(linha["perfil"], linha["nome"], linha["email"], linha["senha_hash"], id=linha["id"])

    def criar(self, perfil, nome, email, senha):
        id = self.banco.executar(
            "INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (?,?,?,?)",
            (nome, email, gerar_hash(senha), perfil),
        )
        return self.buscar_por_id(id)

    def buscar_por_email(self, email):
        linha = self.banco.consultar_um("SELECT * FROM usuarios WHERE email = ?", (email,))
        return self._montar(linha) if linha else None

    def buscar_por_id(self, id):
        linha = self.banco.consultar_um("SELECT * FROM usuarios WHERE id = ?", (id,))
        return self._montar(linha) if linha else None

    def listar(self):
        linhas = self.banco.consultar("SELECT * FROM usuarios ORDER BY perfil, nome")
        return [self._montar(l) for l in linhas]

    def contar_administradores(self):
        return self.banco.consultar_um("SELECT COUNT(*) AS n FROM usuarios WHERE perfil = 'administrador'")["n"]

    def mudar_perfil(self, id, perfil):
        self.banco.executar("UPDATE usuarios SET perfil = ? WHERE id = ?", (perfil, id))
        return self.buscar_por_id(id)
