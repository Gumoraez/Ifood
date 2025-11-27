# Projeto — Sistema de Entrega de Comida

## Escopo do Projeto
- Implementar autenticação (email/telefone com 2FA e Google com 2FA).
- Seleção de restaurante, montagem de carrinho, checkout, criação e acompanhamento de pedidos.
- Gestão de endereços com geolocalização, ViaCEP e favoritos.

## Sumário
- 1. Escopo do Projeto
- 2. Diagrama da Arquitetura
- 3. Requisitos/Funcionalidades e Regras
- 4. Campos e Validações
- 5. Modelo de Dados Físico
- 6. Script de Criação do Banco de Dados
- 7. Funcionalidades Implementadas (prints e explicações)

## Diagrama da Arquitetura
- Consulte `documentação/arquitetura.md`.

## Requisitos/Funcionalidades
- Autenticação com 2FA por email/telefone e Google.
- Troca de conta Google com seletor de contas e limpeza de estado.
- Catálogo de restaurantes e itens.
- Carrinho por usuário/restaurante.
- Checkout com endereço e pagamento.
- Criação e acompanhamento de pedidos.
- Favoritar restaurantes e itens.
- Endereços com geolocalização, fallback e ViaCEP.

### Regras da Funcionalidade
- Código de verificação expira em 10 minutos.
- Apenas caminhos relativos são aceitos em `next`.
- Carrinho é exclusivo do restaurante; troca limpa carrinho anterior.
- Endereço é obrigatório; dados de cartão são obrigatórios quando método for cartão.
- Preço do item do pedido é fixado no momento da compra.

### Campos Necessários
- Autenticação: `email` ou `phone` (um deles), `code`.
- Checkout: `address_id`, `payment_method`, `notes` (opcional), `card_*` (se cartão).
- Endereço: `nome`, `rua`, `numero`, `bairro`, `cidade`, `estado`, `cep`.

### Regras de Validação
- Email válido; telefone com DDI/DDD; CEP com 8 dígitos.
- `next` começa com `/` e não contém `//`.
- Cartão: `card_number` numérico, `card_expiry` no formato MM/AA, `card_cvv` 3-4 dígitos.

### Campos Obrigatórios
- Autenticação: `email` ou `phone` + `code`.
- Checkout: `address_id`, `payment_method`.
- Endereço: `nome`, `rua`, `numero`, `bairro`, `cidade`, `estado`, `cep`.

## Diagrama do Modelo de Dados Físico
- Consulte `documentação/data_model.md`.

## Script de Criação do Banco de Dados
- Consulte `documentação/create_database.sql`.

## Funcionalidades Implementadas (prints e explicações)
- Login com email/telefone (2FA): página `GET /login` e verificação `GET /verify-code/<id>`.
  - Código: geração/envio: app.py:1066–1081; verificação: app.py:1086–1114.
- Login com Google (2FA): `GET /login/google` e `GET /login/google/start`.
  - Código: app.py:1253–1291; troca de conta: app.py:1215–1229, 1296–1306.
- Registro de cliente: `GET/POST /register`.
  - Código: app.py:593–652; botão “outra conta Google” em templates/register.html:46.
- Lista de restaurantes e busca: `GET /`.
  - Código: app.py:577–591.
- Página de restaurante e cardápio: `GET /restaurant/<id>`.
  - Código: templates e consultas via `MenuItem` (app.py:396–410).
- Carrinho: adicionar/remover/limpar.
  - Código: app.py:412–449, 1561–1604.
- Checkout e criação de pedido: `GET/POST /checkout`.
  - Código: app.py:1607–1693.
- Acompanhamento de pedidos: `GET /orders` e detalhes.
  - Código: `Order` e `OrderItem` (app.py:494–539).
- Refazer pedido: `POST /orders/<id>/reorder`.
  - Código: app.py:1715–1739.
- Favoritos: restaurante e item de menu.
  - Código: app.py:541–570, 2485–2535.
- Endereços: CRUD, geolocalização e ViaCEP.
  - Código: `UserAddress` (app.py:463–493); reverse geocode (app.py:155–161); ViaCEP (app.py:168–193); UI (templates/address_form.html:192–231).

- Prints sugeridos:
  - Tela de Login, Verificação de Código, Seleção de Restaurante, Cardápio, Carrinho, Checkout, Pedidos, Favoritos, Endereços.
  - Capturar após navegar nas rotas acima.
