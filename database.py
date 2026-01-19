import sqlite3

DB_NAME = "financeiro.db"

def conectar():
    return sqlite3.connect(DB_NAME)

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            valor REAL,
            descricao TEXT
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    criar_tabelas()
