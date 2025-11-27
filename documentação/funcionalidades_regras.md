# Funcionalidades e Regras de Negócio

## Autenticação
- Login por email/telefone com código de 6 dígitos (2FA).
- Login social com Google, sempre exigindo verificação por código.
- Troca de conta Google forçada via `force=1` e `prompt=consent select_account`.
- Sessão e tokens OAuth limpos ao trocar de conta.
- Logout limpa sessão e tokens.

### Regras
- Código de verificação expira em 10 minutos.
- Exibir código na tela em desenvolvimento quando envio falhar.
- `next` seguro (apenas caminhos relativos) é preservado após login.
- Usuários sem senha podem entrar apenas via código.
- Auto-criação de usuário ao solicitar código por email/telefone.

### Rotas-chave
- `POST /enviar_codigo`: gera e envia código; cria usuário se necessário.
- `POST /verificar_codigo`: valida código e conclui login.
- `GET /verify-code/<user_id>`: página para digitar código.
- `GET /login/google` e `GET /login/google/start`: fluxo Google.
- `GET /login/google/choose`: força seletor de contas e limpeza de estado.

### Referências de código
- Geração/envio ao voltar do Google: app.py:1260–1291
- Verificação do código: app.py:1086–1114
- Auto-criação de usuário no login: app.py:1048–1056
- Forçar troca de conta Google: app.py:1215–1229, 1296–1306

## Solicitação de Pedidos
- Descoberta de restaurantes por busca e categoria.
- Visualização de cardápio e itens com preço e disponibilidade.
- Carrinho por usuário e restaurante, com itens e quantidades.
- Checkout com seleção de endereço e método de pagamento.
- Criação de pedido com itens, subtotal, taxa de entrega e total.
- Acompanhamento de status do pedido: pending → confirmed → preparing → ready → delivering → delivered/cancelled.
- Refazer pedido (reorder) repovoa carrinho com itens antigos.
- Favoritar restaurantes e itens de menu.

### Regras
- Carrinho pertence a um único restaurante; ao refazer pedido de outro restaurante, carrinho anterior é limpo.
- Endereço padrão sugerido no checkout; endereço é obrigatório.
- Método de pagamento obrigatório; cartões exigem nome, número, validade e CVV.
- Status do pedido atualizado por backoffice/loja.
- Itens do pedido guardam o preço no momento da compra.

### Rotas-chave
- `GET /`: lista e busca restaurantes.
- `GET /restaurant/<id>`: página do restaurante.
- `POST /add_to_cart`, `POST /remove_from_cart`, `POST /clear_cart`.
- `GET/POST /checkout`: finalização e criação do pedido.
- `GET /orders`: lista pedidos do usuário.
- `POST /orders/<id>/reorder`: refaz pedido.
- `POST /restaurants/<id>/favorite`, `POST /restaurants/<id>/unfavorite`.

### Referências de código
- Carrinho e itens: app.py:412–449
- Checkout e criação de pedido: app.py:1607–1693
- Refazer pedido: app.py:1715–1739
- Favoritos: app.py:541–570, 2485–2535

## Endereço e Geolocalização
- Uso de geolocalização do navegador (HTTPS/localhost) para sugerir endereço.
- Reverse geocode com fallback de cidade/estado.
- ViaCEP para preencher endereço a partir do CEP.

### Regras
- Em conexões não seguras, geolocalização é bloqueada; instrução exibida ao usuário.
- Quando reverse geocode falhar, preencher cidade/estado e solicitar rua/número/bairro/CEP.
- CEP deve ter 8 dígitos; ViaCEP formata e retorna complementos.

### Rotas-chave
- `GET /api/reverse-geocode`: retorna endereço obtido, ou fallback.
- `GET /api/viacep?cep=NNNNNNNN`: preenche campos a partir do CEP.

### Referências de código
- Fallback reverse geocode: app.py:155–161
- ViaCEP endpoint: app.py:168–193
- UI de endereço: templates/address_form.html:192–231
