## Visão Geral do que Falta
- Entrega em GDrive: subir os documentos (itens 1–4) e gerar link.
- Repositório GitHub: publicar o código e fornecer o link.
- Vídeo com áudio: gravar explicação e demonstração completa dos CRUDs (item 6) e demais fluxos.
- Login social (item 7): implementar Google/Facebook com biblioteca compatível (Authlib), já que Flask-Dance conflita com Flask/Werkzeug atuais.
- Verificação de 6 dígitos (item 8): tornar canais reais (Email/SMS/WhatsApp) além do modo desenvolvimento.
- Pagamento (item 14): adicionar validação de pagamento (sandbox) antes de gravar o pedido.
- Módulos/casos especiais: confirmar “Entregador”, “Carreira” e “iFood Card” (apenas se exigidos nesta fase), pois não estão ativos.

## Ajustes Técnicos Propostos
- Email (Gmail): finalizar com “senha de app” ou usar Mailtrap para testes. Adicionar teste automático via /debug.
- SMS/WhatsApp: integrar Twilio (SID/Auth Token/From/Sandbox). Ativar botões de reenvio com canal real.
- Login Google/Facebook: usar Authlib (OAuth2) e rotas /login/google, /login/facebook com callback, criando usuário verificado.
- Pagamento: integrar Stripe/Mercado Pago (modo sandbox) no checkout; validar transação (status pago) e só então persistir o pedido.
- Segurança: ler segredos via .env e nunca versionar credenciais; checagem de variáveis em /debug.
- Testes: criar rotas/fixtures de diagnóstico para validar email/SMS/pagamento e registros de logs.

## CRUDs e Filtros (Validação de Entrega)
- Contas (item 6): garantir inclusão/alteração/exclusão/consulta com exibição do banco na gravação.
- Endereços (item 9): já implementado; incluir no vídeo todas operações.
- Restaurantes (item 10) e Refeições/Lanches (item 11): já implementado; validar no vídeo.
- Filtros (itens 12 e 13): restaurantes/produtos por favoritos, proximidade, categoria; demonstrar.
- Cesta/Checkout/Pagamento (item 14): demonstrar inserção/remoção/quantidade; fechar pedido com endereço/pagamento/entrega; validar pagamento.
- NF (item 15): usar /orders/<id>/invoice com pedido entregue.

## Mobile (item 16)
- Confirmar pasta mobile (React Native) com CRUD de restaurantes: apontar API `/api/restaurants`.
- Ajustar baseURL e garantir criação/edição/exclusão via app; demonstrar emulador.

## Documentação e Entregáveis
- Atualizar documentos: funcionalidades/regras (1), arquitetura (2), modelo de dados físico (3), script SQL (4), documento do projeto detalhado (5).
- Subir os documentos no GDrive (item 1–4) e compartilhar link.
- Publicar código no GitHub (item 5–16) e gravar vídeo com áudio explicando o código e executando os CRUDs, mostrando o banco em cada operação.

## Plano de Execução
1) Configuração de canais (Email, SMS/WhatsApp) e testes.
2) Implementação de OAuth com Authlib e callbacks.
3) Integração de pagamento sandbox e validação no checkout.
4) Revisão dos CRUDs e filtros, ajustes finos e logs de auditoria.
5) Ajustes no Mobile (baseURL, CRUD, teste em emulador).
6) Atualização de documentação e publicação (GDrive + GitHub).
7) Gravação do vídeo com a demonstração completa.

## Confirmação
- Confirmo que quer que eu avance nestes itens. Caso tenha preferência (Mailer: Gmail vs Mailtrap; Pagamento: Stripe vs Mercado Pago; Canal: SMS vs WhatsApp), me diga e eu sigo com as integrações escolhidas.