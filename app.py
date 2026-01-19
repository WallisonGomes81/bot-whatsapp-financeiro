import os
import psycopg2
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


def conectar():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def criar_tabela():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY,
            telefone TEXT,
            tipo TEXT NOT NULL,
            valor NUMERIC NOT NULL,
            descricao TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def salvar(telefone, tipo, valor, descricao):
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO transacoes (telefone, tipo, valor, descricao) VALUES (%s, %s, %s, %s)",
        (telefone, tipo, valor, descricao)
    )

    conn.commit()
    cur.close()
    conn.close()


def calcular_saldo(telefone):
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        "SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE telefone=%s AND tipo='entrada'",
        (telefone,)
    )
    entradas = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE telefone=%s AND tipo='saida'",
        (telefone,)
    )
    saidas = cur.fetchone()[0]

    cur.close()
    conn.close()

    return entradas - saidas


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    texto = request.form.get("Body", "").strip()
    telefone = request.form.get("From", "")
    resp = MessagingResponse()

    try:
        if texto.lower() == "saldo":
            saldo = calcular_saldo(telefone)
            resp.message(f"💰 Saldo atual: R$ {saldo:.2f}")
            return str(resp)

        if texto.startswith("+"):
            conteudo = texto[1:].strip()
            partes = conteudo.split(" ", 1)

            valor = float(partes[0].replace(",", "."))
            descricao = partes[1] if len(partes) > 1 else "Entrada"

            salvar(telefone, "entrada", valor, descricao)
            resp.message(f"✅ Entrada registrada: R$ {valor:.2f}")
            return str(resp)

        if texto.startswith("-"):
            conteudo = texto[1:].strip()
            partes = conteudo.split(" ", 1)

            valor = float(partes[0].replace(",", "."))
            descricao = partes[1] if len(partes) > 1 else "Saída"

            salvar(telefone, "saida", valor, descricao)
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
        resp.message("⚠️ Erro ao processar mensagem.")
        return str(resp)


# 🔥 cria tabela automaticamente
criar_tabela()

if __name__ == "__main__":
    app.run()
