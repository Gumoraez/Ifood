import sqlite3
import json
import os
import argparse

# Resolve paths to root and instance DBs and pick the one the app is using
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT_DB = os.path.join(BASE_DIR, 'ifood.db')
INSTANCE_DB = os.path.join(BASE_DIR, 'instance', 'ifood.db')
DB_PATH = ROOT_DB if os.path.exists(ROOT_DB) else INSTANCE_DB


def escape_table(name: str) -> str:
    """Quote reserved table names like order."""
    return '"order"' if name and name.lower() == 'order' else name


def parse_set_pairs(set_str: str):
    """Parse key=value pairs separated by commas into (keys, values).
    Supports quoted strings (single or double), and tries to cast numbers.
    Example: "name='Novo Nome',is_admin=1,price=39.90"
    """
    keys, values = [] , []
    for part in set_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '=' not in part:
            raise ValueError(f"Par inválido '{part}'. Use formato chave=valor")
        k, v = part.split('=', 1)
        k = k.strip()
        v = v.strip()
        # strip quotes if present
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            v_clean = v[1:-1]
        else:
            # try cast numeric
            try:
                v_clean = float(v) if '.' in v else int(v)
            except ValueError:
                v_clean = v
        keys.append(k)
        values.append(v_clean)
    return keys, values


def main():
    parser = argparse.ArgumentParser(description="SQLite DB inspector and editor")
    parser.add_argument("--table", help="Table name (e.g., user, restaurant, menu_item, order)")
    parser.add_argument("--cols", default="*", help="Columns to select, comma-separated (default: *)")
    parser.add_argument("--where", default=None, help="Optional WHERE clause without the 'WHERE' keyword")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of rows returned (default: 5)")

    # Edit capabilities
    parser.add_argument("--update", help="Update rows: key=value pairs separated by commas. Ex.: name='Novo',is_admin=1")
    parser.add_argument("--delete", action="store_true", help="Delete rows that match WHERE or id")
    parser.add_argument("--id", type=int, help="Convenience: use WHERE id=?")
    parser.add_argument("--dry-run", action="store_true", help="Show SQL only; do not commit changes")

    args = parser.parse_args()

    print(f"Opening SQLite DB: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("ERROR: Database file not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 2000')
    cur = conn.cursor()

    # --- UPDATE mode ---
    if args.update:
        if not args.table:
            print("ERROR: --update requer --table")
            conn.close()
            return
        if not args.where and args.id is None:
            print("ERROR: --update requer --where ou --id para evitar atualização em massa.")
            conn.close()
            return
        t = escape_table(args.table)
        try:
            keys, values = parse_set_pairs(args.update)
            set_sql = ", ".join([f"{k}=?" for k in keys])
            if args.id is not None:
                sql = f"UPDATE {t} SET {set_sql} WHERE id=?"
                params = values + [args.id]
            else:
                sql = f"UPDATE {t} SET {set_sql} WHERE {args.where}"
                params = values
            print(f"\nUpdate SQL: {sql}\nParams: {params}")
            if args.dry_run:
                print("DRY RUN: nenhuma alteração foi aplicada.")
            else:
                cur.execute(sql, params)
                conn.commit()
                print(f"Linhas afetadas: {cur.rowcount}")
                # Mostrar resultado após update
                try:
                    if args.id is not None:
                        sel_sql = f"SELECT * FROM {t} WHERE id=?"
                        rows = cur.execute(sel_sql, (args.id,)).fetchall()
                    elif args.where:
                        sel_sql = f"SELECT * FROM {t} WHERE {args.where}"
                        rows = cur.execute(sel_sql).fetchall()
                    print("\nApós UPDATE (amostra):")
                    print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
                except Exception:
                    pass
        except Exception as e:
            print("ERROR ao executar UPDATE:", e)
        conn.close()
        return

    # --- DELETE mode ---
    if args.delete:
        if not args.table:
            print("ERROR: --delete requer --table")
            conn.close()
            return
        if not args.where and args.id is None:
            print("ERROR: --delete requer --where ou --id para evitar apagar tudo.")
            conn.close()
            return
        t = escape_table(args.table)
        try:
            if args.id is not None:
                sql = f"DELETE FROM {t} WHERE id=?"
                params = (args.id,)
            else:
                sql = f"DELETE FROM {t} WHERE {args.where}"
                params = ()
            print(f"\nDelete SQL: {sql}\nParams: {params}")
            if args.dry_run:
                print("DRY RUN: nenhuma alteração foi aplicada.")
            else:
                cur.execute(sql, params)
                conn.commit()
                print(f"Linhas apagadas: {cur.rowcount}")
        except Exception as e:
            print("ERROR ao executar DELETE:", e)
        conn.close()
        return

    # --- QUERY mode ---
    if args.table:
        t = escape_table(args.table)
        sql = f"SELECT {args.cols} FROM {t}"
        if args.where:
            sql += f" WHERE {args.where}"
        if args.limit and args.limit > 0:
            sql += f" LIMIT {args.limit}"
        try:
            rows = cur.execute(sql).fetchall()
            print(f"\nQuery: {sql}")
            print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
        except Exception as e:
            print("\nERROR ao executar SELECT:", e)
        conn.close()
        return

    # --- SUMMARY mode (default) ---
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("\nTables:", tables)

    def count(table_name):
        try:
            cur.execute(f"SELECT COUNT(*) AS c FROM {table_name}")
            return cur.fetchone()[0]
        except Exception as e:
            return f"error: {e}"

    for t in ["user", "restaurant", "menu_item", "order", "order_item"]:
        print(f"Count {t}:", count(t if t != "order" else '"order"'))

    def sample(sql, label):
        try:
            rows = cur.execute(sql).fetchall()
            print(f"\n{label} (up to 5):")
            print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"\n{label} ERROR:", e)

    sample("SELECT id, name, email, is_admin, is_restaurant, social_provider FROM user ORDER BY id DESC LIMIT 5", "Users")
    sample("SELECT id, name, owner_id FROM restaurant ORDER BY id DESC LIMIT 5", "Restaurants")
    sample("SELECT id, name, restaurant_id, price FROM menu_item ORDER BY id DESC LIMIT 5", "Menu Items")
    sample("SELECT id, user_id, restaurant_id, status FROM \"order\" ORDER BY id DESC LIMIT 5", "Orders")
    sample("SELECT id, order_id, menu_item_id, quantity, price FROM order_item ORDER BY id DESC LIMIT 5", "Order Items")

    conn.close()


if __name__ == "__main__":
    main()