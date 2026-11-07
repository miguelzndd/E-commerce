"""Teste de ponta a ponta dos microsserviços (os três precisam estar no ar).

Uso:  python testar_fluxo.py
"""
from comum.cliente_http import (
    URL_CATALOGO, URL_GATEWAY, URL_PAGAMENTOS, URL_PEDIDOS, ClienteServico, ErroServico,
)

gateway = ClienteServico(URL_GATEWAY)
catalogo = ClienteServico(URL_CATALOGO)
pedidos = ClienteServico(URL_PEDIDOS)
pagamentos = ClienteServico(URL_PAGAMENTOS)

falhas = 0


def verificar(descricao, condicao):
    global falhas
    print(("  [OK]    " if condicao else "  [FALHA] ") + descricao)
    if not condicao:
        falhas += 1


def estoque(produto_id):
    return catalogo.get(f"/produtos/{produto_id}")["estoque"]


print("1) Serviços no ar")
for nome, cliente in [("catálogo", catalogo), ("pedidos", pedidos), ("pagamentos", pagamentos)]:
    verificar(f"serviço de {nome} responde", cliente.get("/saude")["status"] == "ok")

print("2) Catálogo (CRUD)")
novo = catalogo.post("/produtos", {"nome": "Produto Teste", "preco": 100.0, "estoque": 10, "peso_kg": 1.0})
verificar("produto criado", novo["id"] is not None)
verificar("frete do produto físico = 10 + 2*peso = 12", novo["frete_unitario"] == 12.0)
digital = catalogo.post("/produtos", {"nome": "Curso Teste", "preco": 50.0, "tipo": "digital"})
verificar("produto digital tem frete 0", digital["frete_unitario"] == 0.0)
verificar("busca por nome encontra o produto", any(p["id"] == novo["id"] for p in catalogo.get("/produtos", {"busca": "teste"})))
atualizado = catalogo.put(f"/produtos/{novo['id']}", {"nome": "Produto Teste", "preco": 120.0, "estoque": 10, "peso_kg": 1.0})
verificar("preço atualizado", atualizado["preco"] == 120.0)
pid = novo["id"]

print("3) Compra com Pix (aprovada, 5% de desconto)")
p1 = pedidos.post("/pedidos", {"cliente": "Maria", "itens": [{"produto_id": pid, "quantidade": 2}], "metodo_pagamento": "pix"})
verificar("pedido ficou 'pago'", p1["status"] == "pago")
verificar("total = 2*120 + 2*12 = 264", p1["total"] == 264.0)
verificar("valor pago com desconto = 250.80", p1["total_pago"] == 250.80)
verificar("estoque baixou de 10 para 8", estoque(pid) == 8)

print("4) Cancelamento (estorno + devolução de estoque)")
c = pedidos.post(f"/pedidos/{p1['id']}/cancelar")
verificar("pedido ficou 'cancelado'", c["status"] == "cancelado")
verificar("estoque voltou para 10", estoque(pid) == 10)
verificar("pagamento ficou 'estornado'", pagamentos.get(f"/pagamentos/{p1['pagamento_id']}")["status"] == "estornado")
try:
    pedidos.post(f"/pedidos/{p1['id']}/cancelar")
    verificar("cancelar de novo é bloqueado", False)
except ErroServico as e:
    verificar("cancelar de novo é bloqueado (409)", e.status == 409)

print("5) Cartão recusado (estoque deve ser devolvido)")
p2 = pedidos.post("/pedidos", {"cliente": "João", "itens": [{"produto_id": pid, "quantidade": 3}],
                               "metodo_pagamento": "cartao", "parcelas": 3, "numero_cartao": "4111111111110000"})
verificar("pedido ficou 'pagamento_recusado'", p2["status"] == "pagamento_recusado")
verificar("estoque continua 10", estoque(pid) == 10)

print("6) Cartão aprovado parcelado")
p3 = pedidos.post("/pedidos", {"cliente": "Ana", "itens": [{"produto_id": pid, "quantidade": 1}],
                               "metodo_pagamento": "cartao", "parcelas": 4, "numero_cartao": "4111111111111111"})
verificar("pedido ficou 'pago'", p3["status"] == "pago")
verificar("mensagem cita 4x", "4x" in p3["mensagem_pagamento"])

print("7) Estoque insuficiente")
try:
    pedidos.post("/pedidos", {"cliente": "Zé", "itens": [{"produto_id": pid, "quantidade": 999}], "metodo_pagamento": "pix"})
    verificar("pedido com estoque insuficiente é recusado", False)
except ErroServico as e:
    verificar("pedido com estoque insuficiente é recusado (409)", e.status == 409)
verificar("estoque não foi alterado (9 após compra de 1)", estoque(pid) == 9)

print("8) Ciclo de vida do pedido")
a = pedidos.post(f"/pedidos/{p3['id']}/avancar")
b = pedidos.post(f"/pedidos/{p3['id']}/avancar")
verificar("pago -> enviado -> entregue", (a["status"], b["status"]) == ("enviado", "entregue"))
try:
    pedidos.post(f"/pedidos/{p3['id']}/cancelar")
    verificar("pedido entregue não pode ser cancelado", False)
except ErroServico as e:
    verificar("pedido entregue não pode ser cancelado (409)", e.status == 409)

print("9) Produto digital (sem controle de estoque)")
pd = pedidos.post("/pedidos", {"cliente": "Lu", "itens": [{"produto_id": digital["id"], "quantidade": 5}], "metodo_pagamento": "boleto"})
verificar("compra de digital aprovada, sem frete", pd["status"] == "pago" and pd["frete"] == 0.0)

print("10) API Gateway (entrada única)")
saude = gateway.get("/saude")
verificar("gateway enxerga os 3 serviços", all(v == "ok" for v in saude["servicos"].values()))
via_gw = gateway.get("/api/catalogo/produtos", {"busca": "teste"})
verificar("GET /api/catalogo/produtos encaminhado ao Catálogo", any(p["id"] == pid for p in via_gw))
pg = gateway.post("/api/pedidos/pedidos", {"cliente": "Via Gateway", "itens": [{"produto_id": pid, "quantidade": 1}], "metodo_pagamento": "pix"})
verificar("POST /api/pedidos/pedidos cria pedido pago", pg["status"] == "pago")
try:
    gateway.get("/api/inexistente/x")
    verificar("serviço desconhecido devolve 404", False)
except ErroServico as e:
    verificar("serviço desconhecido devolve 404", e.status == 404)
try:
    gateway.get(f"/api/catalogo/produtos/999999")
    verificar("erro do serviço chega ao cliente (404)", False)
except ErroServico as e:
    verificar("erro do serviço chega ao cliente (404)", e.status == 404)

# limpeza dos produtos criados pelo teste
catalogo.delete(f"/produtos/{pid}")
catalogo.delete(f"/produtos/{digital['id']}")

print()
print("TODOS OS TESTES PASSARAM" if falhas == 0 else f"{falhas} TESTE(S) FALHARAM")
raise SystemExit(1 if falhas else 0)
