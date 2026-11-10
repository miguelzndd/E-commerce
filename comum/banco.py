"""Componente comum: acesso a um banco SQLite.

Cada microsserviço cria a sua própria instância apontando para o seu
próprio arquivo .db (um banco por serviço). Nenhum serviço lê o banco
de outro: a comunicação entre eles é sempre por HTTP.
"""
import os
import sqlite3


class BancoSQLite:
    def __init__(self, nome_arquivo):
        pasta = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados")
        os.makedirs(pasta, exist_ok=True)
        self.__caminho = os.path.join(pasta, nome_arquivo)  # atributo privado (encapsulamento)

    def _conectar(self):
        conexao = sqlite3.connect(self.__caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def executar(self, sql, parametros=()):
        """Executa INSERT/UPDATE/DELETE e devolve o id da última linha."""
        conexao = self._conectar()
        try:
            cursor = conexao.execute(sql, parametros)
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

    def consultar(self, sql, parametros=()):
        """Executa um SELECT e devolve uma lista de dicionários."""
        conexao = self._conectar()
        try:
            linhas = conexao.execute(sql, parametros).fetchall()
            return [dict(linha) for linha in linhas]
        finally:
            conexao.close()

    def consultar_um(self, sql, parametros=()):
        resultado = self.consultar(sql, parametros)
        return resultado[0] if resultado else None
