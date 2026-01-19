from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os

app = Flask(__name__)

DB = "financeiro.db"


def conectar():
    return sqlite3.connect(DB)


def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            descricao TEXT
        )
    """)

    conn.commit()
    conn.close()


def salvar(tipo, valor, descricao):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        "INSERT INTO transacoes (tipo, valor, descricao) VALUES (?, ?, ?)",
        (tipo, valor, descricao)
    )
    conn.commit()
    conn.close()


def calcular_saldo():
    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='entrada'")
    entradas = c.fetchone()[0] or 0

    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='saida'")
    saidas = c.fetchone()[0] or 0

    conn.close()
    return entradas - saidas


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    texto = request.form.get("Body", "").strip()
    resp = MessagingResponse()

    try:
        if texto.lower() == "saldo":
            saldo = calcular_saldo()
            resp.message(f"💰 Saldo atual: R$ {saldo:.2f}")
            return str(resp)

        if texto.startswith("+"):
            conteudo = texto[1:].strip()
            partes = conteudo.split(" ", 1)

            valor = float(partes[0].replace(",", "."))
            descricao = partes[1] if len(partes) > 1 else "Entrada"

            salvar("entrada", valor, descricao)
            resp.message(f"✅ Entrada registrada: R$ {valor:.2f}")
            return str(resp)

        if texto.startswith("-"):
            conteudo = texto[1:].strip()
            partes = conteudo.split(" ", 1)

            valor = float(partes[0].replace(",", "."))
            descricao = partes[1] if len(partes) > 1 else "Saída"

            salvar("saida", valor, descricao)
            resp.message(f"❌ Saída registrada: R$ {valor:.2f}")
            return str(resp)

        resp.message(
            "📊 *Bot Financeiro*\n"
            "+ valor descrição → entrada\n"
            "- valor descrição → saída\n"
            "saldo → ver saldo"
        )
        return str(resp)

    except Exception:
        resp.message(
            "⚠️ Erro ao processar mensagem.\n"
            "Use:\n"
            "+ 100 salário\n"
            "- 25 almoço"
        )
        return str(resp)


# 🔥 CRIA AS TABELAS AUTOMATICAMENTE
criar_tabelas()


if __name__ == "__main__":
    app.run()
