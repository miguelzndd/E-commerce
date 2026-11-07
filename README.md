# MiniLoja — E-commerce com Microsserviços e Componentes de Software

Sistema de e-commerce em Python. Cada parte do negócio é um **microsserviço**
independente (API REST com FastAPI, banco SQLite próprio). Um **API Gateway** é a
entrada única e também entrega a interface web, que você abre no navegador em
`http://127.0.0.1:8000`. Tudo roda local; não precisa de Tkinter, internet nem servidor externo.

## Como rodar

### Opção 1: direto no Python (sem Docker)

```bash
pip install -r requirements.txt
python iniciar_servicos.py       # sobe gateway + 3 microsserviços
```

Depois abra **http://127.0.0.1:8000** no navegador. Para encerrar, Ctrl+C no terminal.

Teste automático de ponta a ponta (com os serviços no ar, em outro terminal):

```bash
python testar_fluxo.py
```

Rode sempre de dentro da pasta `ecommerce/`.

### Opção 2: Docker Compose

```bash
docker compose up --build        # sobe gateway + 3 serviços
# abra http://127.0.0.1:8000
docker compose down              # para tudo
```

> O `docker-compose.yml` foi validado com `docker compose config`, mas o build das imagens
> ainda precisa ser testado em uma máquina com Docker em execução.

Documentação interativa de cada API: `http://127.0.0.1:PORTA/docs`.

## Arquitetura

```
              ┌────────────────────┐
              │ Navegador (web/)   │
              └─────────┬──────────┘
                        │ HTTP
                        ▼
              ┌────────────────────┐
              │    API Gateway     │  porta 8000
              │ /  e /api/<serv>/..│  (entrega a página e encaminha a API)
              └───┬────────┬───────┘
        ┌─────────┘        └─────────┐
        ▼                            ▼
┌────────────────┐  HTTP  ┌────────────────┐  HTTP  ┌────────────────┐
│    Catálogo    │◄───────┤    Pedidos     ├───────►│   Pagamentos   │
│   porta 8001   │        │   porta 8002   │        │   porta 8003   │
│  catalogo.db   │        │   pedidos.db   │        │ pagamentos.db  │
└────────────────┘        └────────────────┘        └────────────────┘
```

| Serviço     | Porta | Responsabilidade                                              |
|-------------|-------|---------------------------------------------------------------|
| API Gateway | 8000  | Entrega a interface web; encaminha `/api/<servico>/...`       |
| Catálogo    | 8001  | Produtos, preço, estoque, frete                               |
| Pedidos     | 8002  | Criar/consultar/avançar/cancelar pedidos (orquestra)          |
| Pagamentos  | 8003  | Cobrar (cartão, Pix, boleto) e estornar                       |

**Princípios de microsserviços aplicados**
- Cada serviço tem **seu próprio banco**; nenhum lê o banco do outro.
- A comunicação é **só por HTTP/JSON**.
- Cada serviço roda em **processo e porta próprios**.
- Pedidos fala **direto** com Catálogo e Pagamentos; só a interface passa pelo gateway.

**Componentes de software reutilizáveis** (pasta `comum/`)
- `BancoSQLite`: acesso ao banco, usado pelos três serviços.
- `ClienteServico`: cliente HTTP com tratamento de erros, usado pelo serviço de Pedidos.

Em cada serviço o código é dividido em `dominio.py` (regras e classes),
`repositorio.py` (persistência) e `app.py` (API). Pagamentos não tem `repositorio.py`.

## Interface web

Uma única página (`web/index.html`, HTML + CSS + JavaScript puro) com quatro telas: Loja,
Carrinho, Pedidos e Gerenciar produtos. Ela só chama o gateway (`/api/...`).

## Fluxo de criação de um pedido

1. Para cada item: busca o produto no **Catálogo** e **reserva** o estoque.
2. Calcula total (itens + frete) e chama o serviço de **Pagamentos**.
3. Pagamento aprovado → pedido `pago`.
4. Pagamento recusado ou serviço fora do ar → **devolve o estoque** e o pedido fica
   `pagamento_recusado` / `falhou`.
5. Cancelar um pedido `pago` → **estorna** o pagamento e devolve o estoque.

Ciclo de vida: `pago → enviado → entregue` (cancelamento só enquanto `pago`).

## Regras de negócio

- Frete de produto físico: R$ 10 + R$ 2 por kg, por unidade. Produto digital: sem frete e sem controle de estoque.
- Pix: 5% de desconto. Cartão: 1x a 12x; recusado se o número terminar em `0000`, tiver menos de 12 dígitos ou o valor passar de R$ 5.000 (simulação). Boleto: aprovado.
- Os pagamentos são **simulados** (nenhuma operadora real).

## Orientação a objetos (nas classes de domínio)

| Conceito       | Onde                                                                                      |
|----------------|-------------------------------------------------------------------------------------------|
| Herança        | `ProdutoFisico`/`ProdutoDigital` herdam de `Produto`; `PagamentoCartao`/`Pix`/`Boleto` herdam de `Pagamento` |
| Polimorfismo   | `frete_unitario()` e `controla_estoque()` mudam por tipo de produto; `processar()` muda por forma de pagamento |
| Abstração      | `Pagamento` é classe abstrata (`ABC`) com `processar()` abstrato                           |
| Encapsulamento | `Produto` guarda preço e estoque em atributos privados; `Pedido` só muda de status por `avancar()`/`cancelar()` |

## Estrutura de pastas

```
ecommerce/
├── comum/            # componentes reutilizáveis (banco, cliente HTTP)
├── gateway/          # app.py (API Gateway + entrega da interface)
├── web/index.html    # interface web
├── catalogo/         # dominio.py, repositorio.py, app.py
├── pedidos/          # dominio.py, repositorio.py, app.py
├── pagamentos/       # dominio.py, app.py
├── dados/            # bancos .db (criados ao rodar)
├── Dockerfile, docker-compose.yml
├── iniciar_servicos.py
├── testar_fluxo.py   # 30 verificações automáticas da API
└── requirements.txt
```
