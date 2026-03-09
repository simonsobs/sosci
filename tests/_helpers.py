import sqlite3


def print_db(db_path: str) -> None:
    
    con = sqlite3.connect(db_path)
    for table, in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        print(f"\n--- {table} ---")
        rows = con.execute(f"SELECT * FROM {table}").fetchall()
        for row in rows:
            print(row)
    con.close()