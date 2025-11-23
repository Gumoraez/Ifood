import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'instance' / 'delivery.db'
SCHEMA_PATH = BASE_DIR / 'documentação' / 'create_database.sql'

# Garantir que a pasta instance exista
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

print('Inicializando banco em:', DB_PATH)

# Ler apenas a parte de schema do arquivo SQL (antes de "-- Dados de exemplo")
sql_text = SCHEMA_PATH.read_text(encoding='utf-8')

split_marker = '-- Dados de exemplo'
if split_marker in sql_text:
    schema_sql = sql_text.split(split_marker)[0]
else:
    schema_sql = sql_text  # fallback: usar todo o arquivo se não encontrar marcador

con = sqlite3.connect(str(DB_PATH))
con.execute('PRAGMA foreign_keys = ON')
cur = con.cursor()

# Criar tabelas
cur.executescript(schema_sql)
con.commit()

# Mostrar tabelas criadas
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tabelas criadas/encontradas:', tables)

con.close()
print('Schema aplicado com sucesso.')