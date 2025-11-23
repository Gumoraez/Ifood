# Mobile — CRUD de Restaurantes (Expo React Native)

Este app mobile demonstra o CRUD de restaurantes integrado ao backend Flask via endpoints JSON.

Pré-requisitos:
- Node.js LTS instalado.
- Expo CLI (opcional) ou usar `npx expo`.

Como executar:
- `cd mobile`
- `npm init -y`
- `npm install react react-native expo expo-status-bar`
- `npm install --save-dev @babel/core`
- Crie `App.js` (já incluído neste repositório).
- Inicie o backend Flask em `http://127.0.0.1:5000`.
- `npx expo start` e abra no emulador ou Expo Go.

Configuração de API:
- O app assume `API_BASE = http://127.0.0.1:5000`.
- Endpoints usados:
  - `GET /api/restaurants`
  - `POST /api/restaurants`
  - `PUT /api/restaurants/<id>`
  - `DELETE /api/restaurants/<id>`

Observações:
- Em dispositivos físicos, substitua `127.0.0.1` pelo IP da máquina hospedeira.
- Em produção, adicionar autenticação e validação mais rígida.