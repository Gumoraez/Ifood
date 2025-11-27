# Arquitetura do Sistema

```mermaid
flowchart LR
    subgraph Client [Cliente]
        B[Browser/SPA]
    end

    subgraph App [Flask App]
        A1[Auth & Sessão]
        A2[Pedidos & Carrinho]
        A3[Endereços & Geolocalização]
        A4[Integrações]
    end

    subgraph DB1 [SQLite Default]
        D1[user]
        D2[user_address]
        D3[oauth]
    end

    subgraph DB2 [SQLite Restaurants]
        R1[restaurant]
        R2[menu_item]
        R3[cart]
        R4[cart_item]
        R5[order]
        R6[order_item]
        R7[restaurant_favorite]
        R8[product_favorite]
        R9[restaurant_geo]
    end

    ext1[Google OAuth]
    ext2[Gmail SMTP]
    ext3[ViaCEP]
    ext4[Nominatim]

    B --> A1
    B --> A2
    B --> A3

    A1 --> D1
    A1 --> D3
    A1 --> ext1
    A1 --> ext2

    A2 --> R1
    A2 --> R2
    A2 --> R3
    A2 --> R4
    A2 --> R5
    A2 --> R6
    A2 --> R7
    A2 --> R8

    A3 --> D2
    A3 --> R9
    A3 --> ext3
    A3 --> ext4
```

- Hosts e SO: Windows (desenvolvimento local), Flask 2.3, SQLite.
- Componentes: Flask, Flask-Login, Flask-SQLAlchemy, Flask-Dance, Flask-Mail.
- Integrações: Google OAuth, Gmail SMTP, ViaCEP, Nominatim.
