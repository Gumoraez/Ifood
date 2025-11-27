# Roteiro de Vídeo: Itens 6–16 (o que mostrar e o que não precisa)

Preparação
- Iniciar servidor: `python app.py` e abrir `http://127.0.0.1:5000/`.
- Se desejar envios reais, configurar `MAIL_*`/`SMTP_*` para email e `TWILIO_*` para SMS/WhatsApp.
- Opcional: popular dados com `POST /debug/seed-demo` ou `POST /debug/seed-many`.

6) CRUD de contas com 2FA
- Mostrar: cadastro sem senha e envio de código em `register` (app.py:593); login com 2FA em `login` (app.py:1041) e verificação em `verify_code` (app.py:1116); editar perfil (`edit_user` app.py:2412) e excluir (`delete_user` app.py:2435).
- Não precisa: exibir logs internos de SMTP/Twilio; mostrar credenciais reais.

7) Conta via Gmail/Facebook (com 2FA)
- Mostrar: login Google `login/google/start` (app.py:1225) e Facebook `login/facebook/start` (app.py:1353), criação/associação de conta e envio do código; finalizar em `verify_code`.
- Não precisa: telas do console Google Cloud/Facebook; scopes avançados; troca de conta fora do app.

8) Login com código de 6 dígitos (email/SMS/WhatsApp)
- Mostrar: fluxo com email e telefone; reenvio de código `resend_code` (app.py:1159). Sem Twilio configurado, mostrar o fallback com código em tela.
- Não precisa: comprovar entrega real do SMS/WhatsApp; integração de produção.

9) CRUD de Locais (endereços)
- Mostrar: listar `addresses` (app.py:2274), criar (app.py:2280), editar (app.py:2318), excluir (app.py:2353), definir padrão (app.py:2374); consulta CEP `api_viacep` (app.py:164) e geocodificação reversa `api_reverse_geocode` (app.py:153).
- Não precisa: consumir serviços externos além dos endpoints já integrados.

10) CRUD de Restaurantes
- Mostrar: criar (app.py:2009), editar (modal) (app.py:2048), excluir (app.py:2093); listagem com filtros e favoritos `list_restaurants` (app.py:1862).
- Não precisa: upload real de imagem/logo; manipulação manual de coordenadas no banco.

11) CRUD de Refeições/Lanches
- Mostrar: listar `menu` (app.py:2179), criar (app.py:2186), editar com preço aceitando vírgula (app.py:2235–2244), excluir (app.py:2257).
- Não precisa: upload de imagens; catálogo extenso.

12) Consulta de restaurantes com filtros
- Mostrar: busca por nome/categoria, chips, ordenação, proximidade usando localização do usuário (`api_set_user_location` app.py:192), favoritos (app.py:2489/2517).
- Não precisa: ajustes finos de raio além do padrão; casos sem resultados.

13) Consulta de produtos com filtros
- Mostrar: busca, categoria, disponível, ordenação; favoritos (app.py:2797/2813); proximidade por raio (app.py:2629 e composição 2760–2794).
- Não precisa: demonstração de carrinho com itens de vários restaurantes (o carrinho é por restaurante).

14) Cesta e Checkout (pagamento e gravação)
- Mostrar: adicionar/alterar/remover no carrinho (app.py:1495/1558/1591), checkout (app.py:1625), seleção de endereço e forma de pagamento, validação sandbox `validate_payment` (app.py:267); persistência em `Order`/`OrderItem` (app.py:494/526).
- Não precisa: captura de cartão real; integração com gateway de produção.

15) Emissão de NF (visual)
- Mostrar: tela da NF `order_invoice` (app.py:1822) com `templates/invoice.html` (itens, subtotal, taxa, total, pagamento, dados do cliente/restaurante) e botão de imprimir.
- Não precisa: emissão fiscal oficial/SEFAZ; apenas comprovar a visualização completa.

16) Mobile – CRUD de restaurantes
- Mostrar: `mobile/App.js` consumindo `GET/POST/PUT/DELETE /api/restaurants` (app.py:2114–2174); criar, atualizar, excluir, listar.
- Não precisa: autenticação no mobile; persistência offline; UI avançada.

Evidências no banco
- `GET /debug/db-info` (app.py:2829) para paths e contagens.
- Alternativas: `scripts/db_inspect.py` ou comandos sqlite3 para verificar `user`, `restaurant`, `menu_item`, `order`, `order_item`.

Encerramento
- Logout e revisão rápida das telas principais.
- Reforço: foi demonstrado cadastro/login com 2FA, CRUDs completos (contas, endereços, restaurantes, itens), filtros e favoritos, carrinho/checkout, NF e mobile CRUD.
