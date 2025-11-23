# Roteiro de Vídeo: Demonstração do CRUD e Fluxo de Pedidos

Este roteiro orienta a gravação em passos claros, mostrando funcionalidades e evidências no banco de dados.

1) Preparação
- Abrir o projeto no VS Code/Trae e um terminal.
- Com o venv ativo, iniciar servidor: `python app.py`.
- Abrir o navegador em: http://127.0.0.1:5000/.

2) Cadastro de Usuário (Cliente)
- Clique em "Cadastrar Usuário" no topo, preencha nome, email, senha, endereço, celular.
- Após cadastro, faça login e mostre o nome no navbar.
- Vá ao menu "Meus Dados" (se aplicável) e edite algum campo para demonstrar o update.

3) Cadastro de Restaurante (Conta de restaurante)
- No topo, clique em "Cadastrar Restaurante".
- Preencha nome completo, email, celular e senha.
- Após cadastro, você será direcionado automaticamente para criar o restaurante.
- Preencha os dados (nome, descrição, endereço, categoria, telefone, imagem) e salve.
- Mostre a listagem de restaurantes e o restaurante novo.

4) CRUD de Itens de Menu
- Entre em "Itens do Menu" do restaurante criado.
- Adicione um novo item (nome, descrição, preço, categoria, imagem).
- Edite o item e salve, depois exclua um item para demonstrar o delete.

5) Fluxo de Carrinho e Checkout
- Na página do restaurante, clique em "Adicionar ao carrinho" para alguns itens.
- Abra o Carrinho, ajuste quantidades e clique em "Finalizar Pedido".
- Mostre a página "Meus Pedidos" com o pedido criado, itens e total.

6) Login Social (Opcional)
- Acesse /login/google e /login/facebook (se credenciais estiverem configuradas).
- Mostre que a conta é criada sem senha e que o login funciona.

7) Evidências no Banco de Dados (SQLite)
- Abra um terminal separado e rode:
  - `python -c "import sqlite3, json; con=sqlite3.connect('ifood.db'); cur=con.cursor(); print(cur.execute('select count(*) from user').fetchone()); print(cur.execute('select count(*) from restaurant').fetchone()); print(cur.execute('select count(*) from menu_item').fetchone()); print(cur.execute('select count(*) from \"order\"').fetchone())"`
- Alternativamente, usar o cliente sqlite3 se instalado:
  - `sqlite3 ifood.db "SELECT id,name,email,is_restaurant,is_admin FROM user;"`
  - `sqlite3 ifood.db "SELECT id,name,owner_id FROM restaurant;"`
  - `sqlite3 ifood.db "SELECT id,name,price,restaurant_id FROM menu_item;"`
  - `sqlite3 ifood.db "SELECT id,user_id,restaurant_id,status,total,delivery_address,created_at FROM \"order\";"`
  - `sqlite3 ifood.db "SELECT id,order_id,menu_item_id,quantity,price FROM order_item;"`

8) Encerramento
- Mostrar que o logout funciona.
- Reforçar que todo CRUD básico (create/read/update/delete) de usuários, restaurantes e itens foi demonstrado.

Localização dos arquivos importantes
- Script SQL: create_database.sql
- Roteiro de vídeo: video_script.md
 - Template de checkout: templates/checkout.html