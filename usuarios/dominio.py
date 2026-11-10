"""Domínio de Usuários (POO).

Cliente e Administrador herdam de Usuario. Cada perfil responde de um
jeito às perguntas "pode gerenciar o catálogo?" e "vê todos os pedidos?"
(polimorfismo). A senha nunca é guardada: só o hash dela.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

SEGREDO = os.getenv("USUARIOS_SEGREDO", "pocket-segredo-de-desenvolvimento").encode()
VALIDADE_TOKEN_SEGUNDOS = 8 * 60 * 60  # 8 horas
ITERACOES = 120_000


def gerar_hash(senha):
    """Devolve 'sal$hash' (PBKDF2-SHA256) para guardar no banco."""
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), ITERACOES).hex()
    return f"{sal}${h}"


def conferir_senha(senha, guardado):
    sal, _, h = guardado.partition("$")
    calculado = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), ITERACOES).hex()
    return hmac.compare_digest(calculado, h)


class Usuario:
    perfil = "usuario"

    def __init__(self, nome, email, senha_hash, id=None):
        self.id = id
        self.nome = nome
        self.email = email
        self.__senha_hash = senha_hash  # atributo privado (encapsulamento)

    @property
    def senha_hash(self):
        return self.__senha_hash

    def senha_confere(self, senha):
        return conferir_senha(senha, self.__senha_hash)

    def pode_gerenciar_catalogo(self):
        return False

    def ve_todos_os_pedidos(self):
        return False

    def para_dict(self):
        return {"id": self.id, "nome": self.nome, "email": self.email, "perfil": self.perfil}


class Cliente(Usuario):
    perfil = "cliente"


class Administrador(Usuario):
    perfil = "administrador"

    def pode_gerenciar_catalogo(self):
        return True

    def ve_todos_os_pedidos(self):
        return True


def criar_usuario(perfil, nome, email, senha_hash, id=None):
    """Fábrica: devolve a subclasse certa para o perfil guardado."""
    classes = {"cliente": Cliente, "administrador": Administrador}
    if perfil not in classes:
        raise ValueError(f"Perfil inválido: {perfil}")
    return classes[perfil](nome, email, senha_hash, id=id)


# ---------- token assinado (sem biblioteca externa) ----------
def _b64(dados):
    return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def _desb64(texto):
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def emitir_token(usuario):
    corpo = {"uid": usuario.id, "exp": int(time.time()) + VALIDADE_TOKEN_SEGUNDOS}
    parte = _b64(json.dumps(corpo).encode())
    assinatura = _b64(hmac.new(SEGREDO, parte.encode(), hashlib.sha256).digest())
    return f"{parte}.{assinatura}"


def ler_token(token):
    """Devolve o id do usuário se o token é válido e não expirou; senão None."""
    try:
        parte, assinatura = token.split(".", 1)
        esperado = _b64(hmac.new(SEGREDO, parte.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(assinatura, esperado):
            return None
        corpo = json.loads(_desb64(parte))
        if corpo["exp"] < time.time():
            return None
        return corpo["uid"]
    except (ValueError, KeyError, TypeError):
        return None
