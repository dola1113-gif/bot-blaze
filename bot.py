import requests
import time
import threading
from collections import deque
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

TOKEN = "8652332209:AAFv6vSuGcNk-2nZ04eQbrx1qaXrxweljro"
CHAT_ID = "5233844811"

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
# VARIÁVEIS DO BOT PADRÕES
# =========================
tempo_inicio = time.time()

historico = deque(maxlen=20)
cache_250 = deque(maxlen=250)

entrada_ativa = False
is_sombra = False
gale = 0
max_gale = 5
alvo_atual = None
minutos_alvo = []

# Placar Oficial (> 50%)
wins = 0
loss = 0
win_seq = 0
loss_seq = 0
max_win_seq = 0
max_loss_seq = 0
gale_win = {i: 0 for i in range(6)}

# Placar Sombra (< 50%)
wins_sombra = 0
loss_sombra = 0
gale_win_sombra = {i: 0 for i in range(6)}

msg_gale_id = None
bot_ativo = True

def formatar_historico():
    return "".join([c for c, n, dt in historico])

def format_uptime():
    segundos = int(time.time() - tempo_inicio)
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos = segundos % 60
    return f"{horas:02d}h {minutos:02d}m {segundos:02d}s"

def placar():
    total = wins + loss
    return "0%" if total == 0 else f"{(wins / total) * 100:.1f}%"

def painel():
    dist = " | ".join([f"{'SG' if i == 0 else f'G{i}'}:{gale_win[i]}" for i in range(max_gale + 1)])
    dist_sombra = " | ".join([f"{'SG' if i == 0 else f'G{i}'}:{gale_win_sombra[i]}" for i in range(max_gale + 1)])

    total_250 = len(cache_250)
    if total_250 > 0:
        cores_250 = [c for c, n, dt in cache_250]
        pct_red = (cores_250.count("🔴") / total_250) * 100
        pct_black = (cores_250.count("⚫") / total_250) * 100
        pct_white = (cores_250.count("⚪") / total_250) * 100
        stats_250 = f"🔴 {pct_red:.1f}% | ⚫ {pct_black:.1f}% | ⚪ {pct_white:.1f}%"
    else:
        stats_250 = "Carregando..."

    return f"""
<b>🎲 BLAZE PADRÕES VIP 🎲</b>
⏱️ <b>Uptime:</b> {format_uptime()}

📊 <b>Placar Oficial (>50%):</b> {wins}x{loss} ({placar()})
📌 <b>Wins por Gale:</b> {dist}
🔥 Maior WIN Seq: {max_win_seq} | 💀 Maior LOSS Seq: {max_loss_seq}

👻 <b>Placar Abortados (Sombra):</b> {wins_sombra}x{loss_sombra}
📌 <b>Wins por Gale:</b> {dist_sombra}

📊 <b>Pagamento (Últimas {total_250}):</b>
{stats_250}

🎯 <b>Últimas 20:</b>
{formatar_historico()}
"""

def resetar():
    global entrada_ativa, is_sombra, gale, alvo_atual
    entrada_ativa = False
    is_sombra = False
    gale = 0
    alvo_atual = None
    enviar("🔄 Analisando novos padrões...")

def get_resultado(caixa):
    classe = caixa.get_attribute("class") or ""
    if "white" in classe:
        return "⚪", 0
    try:
        el = caixa.locator(".number")
        if el.count() == 0:
            return None, None
        numero = int(el.inner_text(timeout=1200).strip())
        if "red" in classe:
            return "🔴", numero
        elif "black" in classe:
            return "⚫", numero
        return None, None
    except:
        return None, None

def escutar_comandos():
    global bot_ativo
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=30&offset={offset}"
            r = requests.get(url, timeout=35)
            dados = r.json()
            if dados.get("ok"):
                for msg in dados["result"]:
                    offset = msg["update_id"] + 1
                    if "message" in msg and "text" in msg["message"]:
                        texto = msg["message"]["text"]
                        chat_id = msg["message"]["chat"]["id"]
                        
                        if str(chat_id) == CHAT_ID:
                            if texto == "/pausar":
                                bot_ativo = False
                                resetar()
                                enviar("⏸ <b>Bot Pausado.</b>\nAguardando comando /iniciar.")
                            elif texto == "/iniciar":
                                bot_ativo = True
                                resetar()
                                enviar("▶️ <b>Bot Iniciado.</b>\nCaçando padrões!")
                            elif texto == "/status":
                                enviar(f"ℹ️ <b>Status:</b> {'🟢 Ligado' if bot_ativo else '🔴 Pausado'}\n\n{painel()}")
        except:
            pass
        time.sleep(1)

threading.Thread(target=escutar_comandos, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    page = context.new_page()

    # Usando wait_until='commit' para carregar mais rápido e timeout de 90s
    page.goto("https://blaze.com/pt/games/double", wait_until="commit", timeout=90000)
    page.wait_for_selector("#roulette-recent .sm-box", timeout=90000)

    def carregar_historico_api():
        try:
            print("⏳ Carregando histórico inicial via API...")
            r = requests.get("https://blaze.com/api/roulette_games/recent", timeout=10)
            if r.status_code == 200:
                dados = r.json()
                # A API retorna do mais novo para o mais antigo
                for jogo in reversed(dados):
                    cor_code = jogo["color"]
                    num = jogo["roll"]
                    # Converter cor (0=⚪, 1=🔴, 2=⚫)
                    c = "⚪" if cor_code == 0 else "🔴" if cor_code == 1 else "⚫"
                    # Criar datetime a partir da string (ex: 2024-04-26T13:40:00.000Z)
                    dt_str = jogo["created_at"].replace("Z", "+00:00")
                    dt = datetime.fromisoformat(dt_str).astimezone() # Ajusta para o fuso local
                    
                    cache_250.append((c, num, dt))
                    historico.append((c, num, dt))
                print(f"✅ Cache inicializado com {len(cache_250)} pedras do histórico.")
            else:
                print("⚠️ Não foi possível carregar o histórico da API. O cache será preenchido conforme as rodadas saírem.")
        except Exception as e:
            print(f"❌ Erro ao carregar API: {e}")

    carregar_historico_api()

    print("✅ BOT DE PADRÕES INICIADO")
    enviar("🚀 BOT DE PADRÕES INICIADO!")

    estado_anterior = ""
    tempo_ultima_mudanca = time.time()
    ultimo_estado_estavel = None

    while True:
        try:
            caixas = page.locator("#roulette-recent .sm-box")
            if caixas.count() < 4:
                time.sleep(0.3)
                continue

            estado_list = []
            valido = True
            for i in range(4):
                c, n = get_resultado(caixas.nth(i))
                if c is None:
                    valido = False
                    break
                estado_list.append(f"{c}{n}")

            if not valido:
                time.sleep(0.3)
                continue

            estado_atual = "-".join(estado_list)

            if estado_atual != estado_anterior:
                estado_anterior = estado_atual
                tempo_ultima_mudanca = time.time()
                time.sleep(0.2)
                continue

            # Aguarda estabilidade do DOM para evitar falsas rodadas
            if time.time() - tempo_ultima_mudanca < 1.0:
                time.sleep(0.2)
                continue

            if ultimo_estado_estavel is not None:
                if estado_atual == ultimo_estado_estavel:
                    time.sleep(0.2)
                    continue

            ultimo_estado_estavel = estado_atual
            
            cor, numero = get_resultado(caixas.first)
            resultado = f"{cor} {numero}"

            agora = datetime.now()
            historico.append((cor, numero, agora))
            cache_250.append((cor, numero, agora))
            print(f"🎯 Rodada: {resultado} | Histórico: {len(cache_250)} pedras")

            if not bot_ativo:
                print("⏸️ Bot pausado, aguardando /iniciar")
                continue

            # LÓGICA DE ENTRADA E GALE
            if entrada_ativa:
                # Verificando Win ou Loss
                if cor == alvo_atual:
                    if not is_sombra:
                        wins += 1
                        gale_win[max(0, gale)] += 1
                        win_seq += 1
                        loss_seq = 0
                        if win_seq > max_win_seq: max_win_seq = win_seq
                        
                        nome_gale = "SG" if gale == 0 else f"G{gale}"
                        enviar(f"✅ WIN no {nome_gale} ({alvo_atual})\n{painel()}")
                    else:
                        wins_sombra += 1
                        gale_win_sombra[max(0, gale)] += 1
                        nome_gale = "SG" if gale == 0 else f"G{gale}"
                        enviar(f"👻✅ WIN SOMBRA no {nome_gale} ({alvo_atual})\n{painel()}")

                    resetar()

                else:
                    gale += 1
                    if msg_gale_id:
                        deletar(msg_gale_id)

                    if gale > max_gale:
                        if not is_sombra:
                            loss += 1
                            loss_seq += 1
                            win_seq = 0
                            if loss_seq > max_loss_seq: max_loss_seq = loss_seq
                            enviar(f"❌ LOSS\n{painel()}")
                        else:
                            loss_sombra += 1
                            enviar(f"👻❌ LOSS SOMBRA\n{painel()}")
                            
                        resetar()
                    else:
                        if not is_sombra:
                            msg_gale_id = enviar(f"⚠️ Entrando no G{gale} para {alvo_atual}")
                        else:
                            msg_gale_id = enviar(f"👻 Acompanhando Sombra G{gale} para {alvo_atual}")
                
                continue  # Não analisa novos padrões enquanto está na entrada

            # ANÁLISE DE ESTRATÉGIA: PADRÃO DE BRANCO (MINUTOS)
            agora_loop = datetime.now()
            
            # Verifica se é hora de iniciar uma entrada pendente
            min_agora = agora_loop.minute
            if min_agora in minutos_alvo and not entrada_ativa:
                entrada_ativa = True
                alvo_atual = "⚪"
                minutos_alvo.remove(min_agora)
                enviar(f"🎯 <b>ENTRADA INICIADA</b>\nMinuto Alvo: {min_agora}\nEntrar: {alvo_atual}\nAté G5!")

            # Verifica se apareceu um novo branco para gerar novos gatilhos
            if cor == "⚪":
                min_atual = agora.minute
                
                # Minutos de confirmação no histórico
                check_1 = [(min_atual - i) % 60 for i in [4, 5, 6]]
                check_2 = [(min_atual - i) % 60 for i in [9, 10, 11]]
                
                confirmado = False
                min_confirmacao = None
                
                # Procura no cache por brancos nos minutos de check
                # Ignora a pedra atual (última do cache)
                lista_cache = list(cache_250)[:-1]
                for c_hist, n_hist, dt_hist in reversed(lista_cache):
                    if c_hist == "⚪":
                        if dt_hist.minute in check_1 or dt_hist.minute in check_2:
                            confirmado = True
                            min_confirmacao = dt_hist.minute
                            break
                
                if confirmado:
                    t1 = (min_atual + 4) % 60
                    t2 = (min_atual + 9) % 60
                    
                    if t1 not in minutos_alvo: minutos_alvo.append(t1)
                    if t2 not in minutos_alvo: minutos_alvo.append(t2)
                    
                    msg = f"⚪ <b>BRANCO CONFIRMADO!</b>\n"
                    msg += f"Visto em: {min_atual}min\n"
                    msg += f"Confirmação no histórico: {min_confirmacao}min\n\n"
                    msg += f"🚀 <b>Próximas Entradas:</b>\n"
                    msg += f"• Minuto {t1} (+4)\n"
                    msg += f"• Minuto {t2} (+9)\n"
                    msg += f"Alvo: ⚪ (Até G5)"
                    enviar(msg)
                    print(f"✅ Padrão confirmado! Alvos: {t1}, {t2}")
                else:
                    print(f"⚪ Branco em {min_atual}min, mas sem confirmação em {check_1} ou {check_2}")
            
            elif not entrada_ativa:
                print(f"🔎 Analisando... Alvos pendentes: {minutos_alvo}")




        except Exception as e:
            print("Erro:", e)

        time.sleep(0.3)
