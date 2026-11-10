"""Microsserviço de Usuários (porta 8004): cadastro, login e perfis.

Perfis: cliente (compra e vê os próprios pedidos) e administrador
(gerencia produtos e todos os pedidos). O login devolve um token
assinado; o gateway pergunta a este serviço se o token é válido.
"""
import sqlite3
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from usuarios.dominio import emitir_token, ler_token
from usuarios.repositorio import RepositorioUsuarios

app = FastAPI(title="Serviço de Usuários")
repo = RepositorioUsuarios()


class CadastroEntrada(BaseModel):
    nome: str
    email: str
    senha: str


class LoginEntrada(BaseModel):
    email: str
    senha: str


@app.get("/saude")
def saude():
    return {"servico": "usuarios", "status": "ok"}


@app.post("/cadastro")
def cadastrar(dados: CadastroEntrada):
    nome, email = dados.nome.strip(), dados.email.strip().lower()
    if not nome:
        raise HTTPException(400, "Informe o seu nome.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Informe um e-mail válido.")
    if len(dados.senha) < 6:
        raise HTTPException(400, "A senha precisa ter pelo menos 6 caracteres.")
    try:
        usuario = repo.criar("cliente", nome, email, dados.senha)  # todo cadastro novo é cliente
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe uma conta com esse e-mail.")
    return {"token": emitir_token(usuario), "usuario": usuario.para_dict()}


class PerfilEntrada(BaseModel):
    perfil: str


@app.get("/usuarios")
def listar_usuarios():
    """Lista as contas (o gateway só deixa o administrador chegar aqui)."""
    return [u.para_dict() for u in repo.listar()]


@app.put("/usuarios/{id}/perfil")
def mudar_perfil(id: int, dados: PerfilEntrada):
    if dados.perfil not in ("cliente", "administrador"):
        raise HTTPException(400, "Perfil inválido.")
    usuario = repo.buscar_por_id(id)
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    if usuario.perfil == "administrador" and dados.perfil == "cliente" and repo.contar_administradores() <= 1:
        raise HTTPException(409, "Este é o único administrador. Promova outra conta antes de rebaixá-lo.")
    return repo.mudar_perfil(id, dados.perfil).para_dict()


@app.post("/login")
def entrar(dados: LoginEntrada):
    usuario = repo.buscar_por_email(dados.email.strip().lower())
    if not usuario or not usuario.senha_confere(dados.senha):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return {"token": emitir_token(usuario), "usuario": usuario.para_dict()}


@app.get("/eu")
def quem_sou_eu(authorization: Optional[str] = Header(None)):
    """Valida o token e devolve o usuário dono dele (o gateway usa isto)."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    uid = ler_token(token) if token else None
    usuario = repo.buscar_por_id(uid) if uid else None
    if not usuario:
        raise HTTPException(401, "Sessão inválida ou expirada. Entre de novo.")
    resposta = usuario.para_dict()
    resposta["pode_gerenciar_catalogo"] = usuario.pode_gerenciar_catalogo()
    return resposta
