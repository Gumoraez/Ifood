## Objetivo

* Implementar e validar os itens 6–16: CRUDs Web, login com código 6 dígitos (email/SMS/WhatsApp), login social, filtros de restaurantes/produtos, cesta/checkout/pagamento, emissão de NF e CRUD Mobile, com documentação, GitHub e vídeo.

## Pré-requisitos e Integrações

* Email: usar Gmail com “senha de app” OU Mailtrap (sandbox) para garantir entrega de código.

* SMS/WhatsApp: integrar Twilio (Account SID, Auth Token, número From ou WhatsApp sandbox).

* Login Social: usar Authlib (OAuth2) para Google/Facebook, evitando conflitos de versões.

* Pagamento: integrar sandbox (Stripe ou Mercado Pago) para validar no checkout antes de gravar o pedido.

* Variáveis: manter segredos no `.env` e validar via rotas de diagnóstico.

## Item 6: CRUD Web de Contas

* Páginas: lista (`/users`), detalhe (`/users/<id>`), criar/editar (`/users/edit/<id>`), excluir (`/users/delete/<id>`).

* Validações: campos obrigatórios (nome, email/telefone), unicidade, normalização.

* Demonstração: inclusão, alteração, deleção e consulta, exibindo o banco (tabela `user`).

## Item 7: Inserção de nova conta via Facebook/Gmail

* Implementar OAuth2 com Authlib:

  * Rotas `/login/google` e `/login/facebook` com callback.

  * Ao autorizar, criar a conta (com `id_social`, `provedor_social`) e marcar `verificado=True`.

  * Registrar apenas dados essenciais (nome, email) e aplicar restrições de módulo conforme exigido.

## Item 8: Login com código 6 dígitos (email/SMS/WhatsApp)

* Fluxo: gerar código (6 dígitos), expiração em 10 minutos, reenvio por canal escolhido.

* Email: enviar via Flask-Mail (Gmail/Mailtrap). SMS/WhatsApp: enviar via Twilio.

* UI: página `verify_code` com exibição do código em modo desenvolvimento e botões de reenvio.

* Segurança: limites de reenvio, mensagens claras de erro.

## Item 9: CRUD Web de Endereços

* Páginas: lista (`/addresses`), criar (`/addresses/new`), editar (`/addresses/<id>/edit`), excluir (`/addresses/<id>/delete`), definir padrão.

* Validações: obrigatórios (rua, número, bairro, cidade, estado, CEP), gerenciamento de “padrão”.

* Demonstração completa no vídeo, mostrando persistência em `user_address`.

## Item 10: CRUD Web de Restaurantes

* Páginas: listar, criar, editar, excluir, com verificação de propriedade (`owner_id`).

* Campos: nome, categoria, endereço, taxa/tempo de entrega, avaliação.

* Demonstração completa com reflexo no banco `restaurant`.

## Item 11: CRUD Web de Refeições/Lanches

* Páginas: listar itens do menu, criar, editar, excluir.

* Validações: preço numérico, disponibilidade, vínculo com restaurante.

* Demonstração refletindo em `menu_item`.

## Item 12: Consulta de Restaurantes com Filtros

* Filtros: favoritos, próximos a mim (geocodificação em BR), por tipo de comida; ordenação.

* Implementar chips/filtros na UI e demonstrar resultados consistentes.

## Item 13: Consulta de Produtos com Filtros

* Filtros: favoritos, próximos a mim, categoria, preço, disponibilidade; ordenação.

* Exibir restaurante relacionado e distância quando aplicável.

## Item 14: Cesta, Checkout e Pagamento

* Cesta: inserir/retirar/alterar quantidade, consolidar por restaurante.

* Checkout: selecionar endereço, forma de pagamento, calcular frete, total.

* Pagamento: validar via sandbox (Stripe/Mercado Pago); somente gravar pedido se aprovado.

* Persistência: criar `order` e `order_item`, limpar carrinho ao final.

## Item 15: Emissão de NF

* Rota `/orders/<id>/invoice`: exibir dados do pedido entregue e informações da empresa (sem marca/“iFood”).

* Garantir acesso apenas por dono do pedido/dono do restaurante/admin.

## Item 16: Mobile – CRUD de Restaurantes

* App React Native consumindo `/api/restaurants` (listar, criar, atualizar, excluir).

* Ajustar `API_BASE` conforme ambiente, demonstrar em emulador.

* Persistência validada contra o mesmo banco.

## Documentação e Entregas

* Atualizar documentos (itens 1–4) e publicar no GDrive com link público.

* Publicar código completo no GitHub e fornecer o link.

* Gravar vídeo com áudio explicando o código e demonstrando cada CRUD, mostrando o banco em cada operação.

## Validação e Diagnóstico

* Rotas de debug para email, SMS/WhatsApp, pagamento e banco.

* Logs e mensagens de sucesso/erro visíveis na UI.

## Próximos Passos

* Confirmar preferências: Email (Gmail vs Mailtrap), Pagamento (Stripe vs Mercado Pago), Canal (SMS vs WhatsApp).

* Em seguida, implementar integrações escolhidas, validar fluxos e preparar os entregáveis (links GDrive/GitHub e vídeo).

