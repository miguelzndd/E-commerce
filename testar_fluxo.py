"""Teste de ponta a ponta dos microsserviços (os quatro e o gateway precisam estar no ar).

Uso:  python testar_fluxo.py
"""
import uuid

from comum.cliente_http import (
    URL_CATALOGO, URL_GATEWAY, URL_PAGAMENTOS, URL_PEDIDOS, URL_USUARIOS, ClienteServico, ErroServico,
)

anonimo = ClienteServico(URL_GATEWAY)
catalogo = ClienteServico(URL_CATALOGO)
pagamentos = ClienteServico(URL_PAGAMENTOS)
pedidos_direto = ClienteServico(URL_PEDIDOS)
usuarios = ClienteServico(URL_USUARIOS)

falhas = 0


def verificar(descricao, condicao):
    global falhas
    print(("  [OK]    " if condicao else "  [FALHA] ") + descricao)
    if not condicao:
        falhas += 1


def codigo_erro(funcao):
    """Executa a chamada e devolve o status HTTP do erro (None se não deu erro)."""
    try:
        funcao()
    except ErroServico as e:
        return e.status
    return None


def estoque(produto_id):
    return catalogo.get(f"/produtos/{produto_id}")["estoque"]


def logado(token):
    return ClienteServico(URL_GATEWAY, cabecalhos={"Authorization": f"Bearer {token}"})


print("1) Serviços no ar")
for nome, cliente in [("catálogo", catalogo), ("pagamentos", pagamentos), ("pedidos", pedidos_direto), ("usuários", usuarios)]:
    verificar(f"serviço de {nome} responde", cliente.get("/saude")["status"] == "ok")

print("2) Login e perfis")
sufixo = uuid.uuid4().hex[:8]
entrada = anonimo.post("/api/usuarios/login", {"email": "mats@ufal.com", "senha": "TJAGSMVTAFGJP"})
admin = logado(entrada["token"])
verificar("administrador padrão entra com sucesso", entrada["usuario"]["perfil"] == "administrador")
verificar("senha errada é recusada (401)", codigo_erro(lambda: anonimo.post("/api/usuarios/login", {"email": "mats@ufal.com", "senha": "errada"})) == 401)
maria_cad = anonimo.post("/api/usuarios/cadastro", {"nome": "Maria", "email": f"maria{sufixo}@teste.com", "senha": "senha123"})
maria = logado(maria_cad["token"])
verificar("cadastro cria conta com perfil cliente", maria_cad["usuario"]["perfil"] == "cliente")
verificar("e-mail repetido é recusado (409)", codigo_erro(lambda: anonimo.post("/api/usuarios/cadastro", {"nome": "Maria", "email": f"maria{sufixo}@teste.com", "senha": "senha123"})) == 409)
verificar("senha curta é recusada (400)", codigo_erro(lambda: anonimo.post("/api/usuarios/cadastro", {"nome": "X", "email": f"x{sufixo}@teste.com", "senha": "123"})) == 400)
verificar("rota /eu devolve o usuário logado", maria.get("/api/usuarios/eu")["nome"] == "Maria")
joao_cad = anonimo.post("/api/usuarios/cadastro", {"nome": "João", "email": f"joao{sufixo}@teste.com", "senha": "senha123"})
joao_token, joao_id = joao_cad["token"], joao_cad["usuario"]["id"]
joao = logado(joao_token)
verificar("sem login, pedidos exige autenticação (401)", codigo_erro(lambda: anonimo.get("/api/pedidos/pedidos")) == 401)
verificar("token inválido é recusado (401)", codigo_erro(lambda: logado("token.falso").get("/api/pedidos/pedidos")) == 401)
verificar("catálogo pode ser visto sem login", isinstance(anonimo.get("/api/catalogo/produtos"), list))
verificar("cliente não cria produto (403)", codigo_erro(lambda: maria.post("/api/catalogo/produtos", {"nome": "Invasor", "preco": 1.0})) == 403)
verificar("cliente não acessa pagamentos pelo gateway (403)", codigo_erro(lambda: maria.get("/api/pagamentos/pagamentos/1")) == 403)
verificar("pedidos sem identificação são recusados direto no serviço (401)", codigo_erro(lambda: pedidos_direto.get("/pedidos")) == 401)

print("2b) Gestão de usuários (só administrador)")
verificar("cliente não lista usuários (403)", codigo_erro(lambda: maria.get("/api/usuarios/usuarios")) == 403)
verificar("cliente não se promove (403)", codigo_erro(lambda: maria.put(f"/api/usuarios/usuarios/{maria_cad['usuario']['id']}/perfil", {"perfil": "administrador"})) == 403)
verificar("administrador lista usuários", any(u["email"] == f"maria{sufixo}@teste.com" for u in admin.get("/api/usuarios/usuarios")))
promovido = admin.put(f"/api/usuarios/usuarios/{joao_id}/perfil", {"perfil": "administrador"})
verificar("administrador promove João", promovido["perfil"] == "administrador")
produto_joao = logado(joao_token).post("/api/catalogo/produtos", {"nome": "Do João", "preco": 1.0})
verificar("João agora cria produto", produto_joao["id"] is not None)
admin.delete(f"/api/catalogo/produtos/{produto_joao['id']}")
verificar("administrador rebaixa João", admin.put(f"/api/usuarios/usuarios/{joao_id}/perfil", {"perfil": "cliente"})["perfil"] == "cliente")
verificar("João rebaixado perde o acesso (403)", codigo_erro(lambda: logado(joao_token).post("/api/catalogo/produtos", {"nome": "X", "preco": 1.0})) == 403)
admin_id = admin.get("/api/usuarios/eu")["id"]
verificar("não rebaixa o único administrador (409)", codigo_erro(lambda: admin.put(f"/api/usuarios/usuarios/{admin_id}/perfil", {"perfil": "cliente"})) == 409)
verificar("perfil inválido é recusado (400)", codigo_erro(lambda: admin.put(f"/api/usuarios/usuarios/{joao_id}/perfil", {"perfil": "dono"})) == 400)

print("3) Catálogo (CRUD, só administrador altera)")
novo = admin.post("/api/catalogo/produtos", {"nome": "Produto Teste", "preco": 100.0, "estoque": 10, "peso_kg": 1.0})
verificar("administrador cria produto", novo["id"] is not None)
verificar("frete do produto físico = 10 + 2*peso = 12", novo["frete_unitario"] == 12.0)
digital = admin.post("/api/catalogo/produtos", {"nome": "Curso Teste", "preco": 50.0, "tipo": "digital"})
verificar("produto digital tem frete 0", digital["frete_unitario"] == 0.0)
verificar("busca por nome encontra o produto", any(p["id"] == novo["id"] for p in anonimo.get("/api/catalogo/produtos", {"busca": "teste"})))
atualizado = admin.put(f"/api/catalogo/produtos/{novo['id']}", {"nome": "Produto Teste", "preco": 120.0, "estoque": 10, "peso_kg": 1.0})
verificar("preço atualizado", atualizado["preco"] == 120.0)
pid = novo["id"]

print("4) Compra com Pix (aprovada, 5% de desconto)")
p1 = maria.post("/api/pedidos/pedidos", {"itens": [{"produto_id": pid, "quantidade": 2}], "metodo_pagamento": "pix"})
verificar("pedido ficou 'pago'", p1["status"] == "pago")
verificar("pedido guarda o nome do cliente logado", p1["cliente"] == "Maria")
verificar("total = 2*120 + 2*12 = 264", p1["total"] == 264.0)
verificar("valor pago com desconto = 250.80", p1["total_pago"] == 250.80)
verificar("estoque baixou de 10 para 8", estoque(pid) == 8)

print("5) Pedidos de cada usuário")
verificar("Maria vê o próprio pedido", any(p["id"] == p1["id"] for p in maria.get("/api/pedidos/pedidos")))
verificar("João não vê o pedido da Maria na lista", all(p["id"] != p1["id"] for p in joao.get("/api/pedidos/pedidos")))
verificar("João não abre o pedido da Maria (403)", codigo_erro(lambda: joao.get(f"/api/pedidos/pedidos/{p1['id']}")) == 403)
verificar("João não cancela o pedido da Maria (403)", codigo_erro(lambda: joao.post(f"/api/pedidos/pedidos/{p1['id']}/cancelar")) == 403)
verificar("administrador vê o pedido da Maria", any(p["id"] == p1["id"] for p in admin.get("/api/pedidos/pedidos")))

print("6) Cancelamento (estorno + devolução de estoque)")
c = maria.post(f"/api/pedidos/pedidos/{p1['id']}/cancelar")
verificar("pedido ficou 'cancelado'", c["status"] == "cancelado")
verificar("estoque voltou para 10", estoque(pid) == 10)
verificar("pagamento ficou 'estornado'", pagamentos.get(f"/pagamentos/{p1['pagamento_id']}")["status"] == "estornado")
verificar("cancelar de novo é bloqueado (409)", codigo_erro(lambda: maria.post(f"/api/pedidos/pedidos/{p1['id']}/cancelar")) == 409)

print("7) Cartão recusado (estoque deve ser devolvido)")
p2 = joao.post("/api/pedidos/pedidos", {"itens": [{"produto_id": pid, "quantidade": 3}],
                                         "metodo_pagamento": "cartao", "parcelas": 3, "numero_cartao": "4111111111110000"})
verificar("pedido ficou 'pagamento_recusado'", p2["status"] == "pagamento_recusado")
verificar("estoque continua 10", estoque(pid) == 10)

print("8) Cartão aprovado parcelado")
p3 = joao.post("/api/pedidos/pedidos", {"itens": [{"produto_id": pid, "quantidade": 1}],
                                         "metodo_pagamento": "cartao", "parcelas": 4, "numero_cartao": "4111111111111111"})
verificar("pedido ficou 'pago'", p3["status"] == "pago")
verificar("mensagem cita 4x", "4x" in p3["mensagem_pagamento"])

print("9) Estoque insuficiente")
verificar("pedido com estoque insuficiente é recusado (409)", codigo_erro(lambda: maria.post("/api/pedidos/pedidos", {"itens": [{"produto_id": pid, "quantidade": 999}], "metodo_pagamento": "pix"})) == 409)
verificar("estoque não foi alterado (9 após compra de 1)", estoque(pid) == 9)

print("10) Ciclo de vida do pedido (só o administrador avança)")
verificar("cliente não avança o status (403)", codigo_erro(lambda: joao.post(f"/api/pedidos/pedidos/{p3['id']}/avancar")) == 403)
a = admin.post(f"/api/pedidos/pedidos/{p3['id']}/avancar")
b = admin.post(f"/api/pedidos/pedidos/{p3['id']}/avancar")
verificar("pago -> enviado -> entregue", (a["status"], b["status"]) == ("enviado", "entregue"))
verificar("pedido entregue não pode ser cancelado (409)", codigo_erro(lambda: joao.post(f"/api/pedidos/pedidos/{p3['id']}/cancelar")) == 409)

print("11) Produto digital (sem controle de estoque)")
pd = maria.post("/api/pedidos/pedidos", {"itens": [{"produto_id": digital["id"], "quantidade": 5}], "metodo_pagamento": "boleto"})
verificar("compra de digital aprovada, sem frete", pd["status"] == "pago" and pd["frete"] == 0.0)

print("12) API Gateway (entrada única)")
saude = anonimo.get("/saude")
verificar("gateway enxerga os 4 serviços", len(saude["servicos"]) == 4 and all(v == "ok" for v in saude["servicos"].values()))
verificar("serviço desconhecido devolve 404", codigo_erro(lambda: anonimo.get("/api/inexistente/x")) == 404)
verificar("erro do serviço chega ao cliente (404)", codigo_erro(lambda: anonimo.get("/api/catalogo/produtos/999999")) == 404)

# limpeza dos produtos criados pelo teste
admin.delete(f"/api/catalogo/produtos/{pid}")
admin.delete(f"/api/catalogo/produtos/{digital['id']}")

print()
print("TODOS OS TESTES PASSARAM" if falhas == 0 else f"{falhas} TESTE(S) FALHARAM")
raise SystemExit(1 if falhas else 0)
