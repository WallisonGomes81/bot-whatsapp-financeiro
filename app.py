import os
import psycopg2
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import date

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
            categoria TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

    

def atualizar_banco():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        ALTER TABLE transacoes
        ADD COLUMN IF NOT EXISTS categoria TEXT
    """)

    conn.commit()
    cur.close()
    conn.close()




def salvar(telefone, tipo, valor, descricao, categoria):
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO transacoes (telefone, tipo, valor, descricao, categoria)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (telefone, tipo, valor, descricao, categoria)
    )

    conn.commit()
    cur.close()
    conn.close()


def calcular_saldo(telefone):
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        "SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE telefone=%s AND tipo='entrada'",
        (telefone,)
    )
    entradas = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE telefone=%s AND tipo='saida'",
        (telefone,)
    )
    saidas = cur.fetchone()[0]

    cur.close()
    conn.close()

    return entradas - saidas


def gastos_hoje(telefone):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(valor),0)
        FROM transacoes
        WHERE telefone=%s
        AND tipo='saida'
        AND DATE(data) = CURRENT_DATE
    """, (telefone,))

    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total


def relatorio_mes(telefone, mes, ano):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT tipo, COALESCE(SUM(valor),0)
        FROM transacoes
        WHERE telefone=%s
        AND EXTRACT(MONTH FROM data)=%s
        AND EXTRACT(YEAR FROM data)=%s
        GROUP BY tipo
    """, (telefone, mes, ano))

    dados = cur.fetchall()
    cur.close()
    conn.close()

    entradas = 0
    saidas = 0

    for tipo, valor in dados:
        if tipo == "entrada":
            entradas = valor
        elif tipo == "saida":
            saidas = valor

    return entradas, saidas


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    texto = request.form.get("Body", "").strip().lower()
    telefone = request.form.get("From", "")
    resp = MessagingResponse()

    try:
        # SALDO
        if texto == "saldo":
            saldo = calcular_saldo(telefone)
            resp.message(f"💰 Saldo atual: R$ {saldo:.2f}")
            return str(resp)

        # AJUDA
        if texto == "ajuda":
            resp.message(
                "📘 *Comandos disponíveis*\n\n"
                "+ valor desc → entrada\n"
                "- valor desc → saída\n"
                "saldo → saldo atual\n"
                "hoje → gastos de hoje\n"
                "mes → relatório mês atual\n"
                "mes mm/aaaa → relatório mês específico\n"
                "ajuda → ver comandos"
            )
            return str(resp)

        # GASTOS DO DIA
        if texto == "hoje":
            total = gastos_hoje(telefone)
            resp.message(f"📆 Gastos de hoje: R$ {total:.2f}")
            return str(resp)

        # RELATÓRIO MENSAL
        if texto.startswith("mes"):
            partes = texto.split()

            hoje = date.today()
            mes = hoje.month
            ano = hoje.year

            if len(partes) == 2:
                mes, ano = partes[1].split("/")
                mes = int(mes)
                ano = int(ano)

            entradas, saidas = relatorio_mes(telefone, mes, ano)
            saldo = entradas - saidas

            resp.message(
                f"📊 *Relatório {mes:02d}/{ano}*\n"
                f"➕ Entradas: R$ {entradas:.2f}\n"
                f"➖ Saídas: R$ {saidas:.2f}\n"
                f"💰 Saldo: R$ {saldo:.2f}"
            )
            return str(resp)

        # ENTRADA
        if texto.startswith("+"):
            conteudo = texto[1:].strip().split(" ", 1)
            valor = float(conteudo[0].replace(",", "."))
            descricao = conteudo[1] if len(conteudo) > 1 else "Entrada"
            salvar(telefone, "entrada", valor, descricao, "geral")
            resp.message(f"✅ Entrada registrada: R$ {valor:.2f}")
            return str(resp)

        # SAÍDA
        if texto.startswith("-"):
            conteudo = texto[1:].strip().split(" ", 1)
            valor = float(conteudo[0].replace(",", "."))
            descricao = conteudo[1] if len(conteudo) > 1 else "Saída"
            salvar(telefone, "saida", valor, descricao, descricao)
            resp.message(f"❌ Saída registrada: R$ {valor:.2f}")
            return str(resp)

        # COMANDO INVÁLIDO
        resp.message(
            "❓ Comando não reconhecido.\n"
            "Digite *ajuda* para ver os comandos disponíveis."
        )
        return str(resp)

    except Exception as e:
        resp.message("⚠️ Erro ao processar sua mensagem.")
        return str(resp)


criar_tabela()
atualizar_banco()

if __name__ == "__main__":
    app.run()

