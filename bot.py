import requests
import time
import threading
from collections import deque
from playwright.sync_api import sync_playwright
from datetime import datetime
import os

# 🔐 Variáveis seguras (Railway)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def enviar(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
        )
        return r.json()["result"]["message_id"]
    except:
        return None

def deletar(msg_id):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/deleteMessage",
            data={"chat_id": CHAT_ID, "message_id": msg_id}
        )
    except:
        pass

# =========================
# CONFIG
# =========================
historico = deque(maxlen=20)
entrada_ativa = False
gale = 0
max_gale = 5
alvo_atual = None

def escutar_comandos():
    global entrada_ativa
    offset = 0
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=30&offset={offset}",
                timeout=35
            )
            dados = r.json()

            if dados.get("ok"):
                for msg in dados["result"]:
                    offset = msg["update_id"] + 1

                    if "message" in msg and "text" in msg["message"]:
                        texto = msg["message"]["text"]

                        if texto == "/status":
                            enviar("🤖 Bot rodando 24h no Railway!")

        except:
            pass

        time.sleep(1)

threading.Thread(target=escutar_comandos, daemon=True).start()

# =========================
# PLAYWRIGHT
# =========================
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("https://blaze.com/pt/games/double")
    page.wait_for_selector("#roulette-recent .sm-box")

    enviar("🚀 BOT ONLINE 24H!")

    while True:
        try:
            caixas = page.locator("#roulette-recent .sm-box")

            if caixas.count() < 1:
                time.sleep(1)
                continue

            numero = caixas.first.locator(".number").inner_text()
            cor_class = caixas.first.get_attribute("class")

            if "red" in cor_class:
                cor = "🔴"
            elif "black" in cor_class:
                cor = "⚫"
            else:
                cor = "⚪"

            resultado = f"{cor} {numero}"
            print("Resultado:", resultado)

        except Exception as e:
            print("Erro:", e)

        time.sleep(2)