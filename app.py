from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3

app = Flask(__name__)
DB = "financeiro.db"

def salvar(tipo, valor, descricao):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transacoes (tipo, valor, descricao) VALUES (?, ?, ?)",
        (tipo, valor, descricao)
    )
    conn.commit()
    conn.close()

def calcular_saldo():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='entrada'")
    entradas = c.fetchone()[0] or 0

    c.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='saida'")
    saidas = c.fetchone()[0] or 0

    conn.close()
    return entradas - saidas

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body").lower().strip()
    resp = MessagingResponse()

    if msg.startswith("+"):
        partes = msg[1:].split(" ", 1)
        valor = float(partes[0])
        descricao = partes[1] if len(partes) > 1 else ""
        salvar("entrada", valor, descricao)
        resp.message(f"✅ Entrada registrada: R$ {valor}")

    elif msg.startswith("-"):
        partes = msg[1:].split(" ", 1)
        valor = float(partes[0])
        descricao = partes[1] if len(partes) > 1 else ""
        salvar("saida", valor, descricao)
        resp.message(f"❌ Saída registrada: R$ {valor}")

    elif msg == "saldo":
        saldo = calcular_saldo()
        resp.message(f"💰 Saldo atual: R$ {saldo:.2f}")

    else:
        resp.message(
            "📊 *Bot Financeiro*\n"
            "+ valor descrição → entrada\n"
            "- valor descrição → saída\n"
            "saldo → ver saldo"
        )

    return str(resp)

if __name__ == "__main__":
    app.run(port=5000)
