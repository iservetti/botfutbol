import os
import requests
from playwright.sync_api import sync_playwright
import re
import random
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN", "8746465129:AAEBGR8UfqUrkxp3g-w8gyqKAUqveTZnwF4")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8449279037")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def enviar_alerta(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=10)
    except Exception as e:
        print(f"⚠️ Error al enviar mensaje a Telegram: {e}")
    
    try:
        tiempo_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("historial_bugs.txt", "a", encoding="utf-8") as archivo:
            archivo.write(f"[{tiempo_actual}]\n{texto}\n{'-'*40}\n")
    except Exception as e:
        print(f"⚠️ Error al guardar en el historial local: {e}")

def es_futbol_ascenso_argentino(texto_upper):
    # Palabras clave para detectar todo el ascenso y el interior
    palabras_clave = [
        "PRIMERA NACIONAL", "B METROPOLITANA", "PRIMERA C", "PRIMERA D", 
        "TORNEO FEDERAL", "FEDERAL A", "FEDERAL B", "FEDERAL C", 
        "INTERIOR", "LIGA DEL INTERIOR", "TORNEO REGIONAL", 
        "COPA ARGENTINA", "LIGA PROFESIONAL", "RESERVA", "SUPERLIGA"
    ]
    return any(k in texto_upper for k in palabras_clave)

def identificar_deporte(texto):
    texto_upper = texto.upper()
    if es_futbol_ascenso_argentino(texto_upper):
        return "🇦🇷 Fútbol Argentino / Ascenso"
    elif any(k in texto_upper for k in ["VIRTUAL", "ESPORTS", "ESPORT", "CS:GO", "DOTA", "LEAGUE OF LEGENDS", "VALORANT", "E-FUTBOL", "E-BASKET"]):
        return "🎮 eSports / Virtuales"
    elif any(k in texto_upper for k in ["BASKET", "NBA", "EUROLIGA", "LNB", "BALONCESTO"]):
        return "🏀 Básquetbol"
    elif any(k in texto_upper for k in ["TENIS", "ATP", "WTA", "ITF", "CHALLENGER"]):
        return "🎾 Tenis"
    elif any(k in texto_upper for k in ["TENIS DE MESA", "ITTF", "SET", "PONG"]):
        return "🏓 Tenis de Mesa"
    else:
        return "⚽ Fútbol Internacional / General"

def procesar_bloques(pagina, nombre_casa):
    bloques = pagina.locator("div").all()
    partidos_procesados = set()
    bugs_encontrados = 0
    partidos_ascenso_avisados = set()
    
    for bloque in bloques:
        try:
            texto_crudo = bloque.inner_text().strip()
            if "\n" not in texto_crudo or len(texto_crudo) < 25: continue
            
            texto_limpio = " | ".join([linea.strip() for linea in texto_crudo.split('\n') if linea.strip()])
            
            if any(palabra in texto_limpio.upper() for palabra in ["MEJORADAS", "SUPER", "BOOST", "AUMENTADAS"]):
                continue
            
            if texto_limpio in partidos_procesados: continue
            partidos_procesados.add(texto_limpio)
            
            texto_upper = texto_limpio.upper()
            
            # 1. AVISO DE PARTIDO NUEVO: Si detecta cualquier evento del ascenso o interior argentino
            if es_futbol_ascenso_argentino(texto_upper):
                # Usamos una porción del texto como identificador único para no repetir el aviso del mismo partido
                id_partido = texto_limpio[:40]
                if id_partido not in partidos_ascenso_avisados:
                    partidos_ascenso_avisados.add(id_partido)
                    aviso_partido = f"📌 [{nombre_casa}] Nuevo partido de Ascenso/Interior detectado:\n📝 {texto_limpio[:80]}"
                    enviar_alerta(aviso_partido)

            deporte_detectado = identificar_deporte(texto_limpio)
            
            cuotas_str = re.findall(r"\b\d{1,3}\.\d{2}\b", texto_limpio)
            cuotas = [float(c) for c in cuotas_str if 1.10 <= float(c) <= 150.0]
            
            if len(cuotas) == 3:
                if not any(c > 2.0 for c in cuotas):
                    continue
                    
                margen = (1/cuotas[0]) + (1/cuotas[1]) + (1/cuotas[2])
                cuotas_usadas = cuotas[:3]
                
                if 0.50 < margen < 0.97: 
                    bugs_encontrados += 1
                    alerta = f"🚨 [{nombre_casa}] ¡BUG REAL (1X2) en {deporte_detectado}!\n📉 Margen: {margen:.3f}\n💰 Cuotas Altas: {cuotas_usadas}\n📝 {texto_limpio[:70]}"
                    enviar_alerta(alerta)

            elif len(cuotas) == 2:
                if not any(c > 2.0 for c in cuotas):
                    continue
                    
                margen = (1/cuotas[0]) + (1/cuotas[1])
                cuotas_usadas = cuotas[:2]
                
                if cuotas_usadas[0] > 2.0 and cuotas_usadas[1] > 2.0:
                    continue
                    
                if 0.50 < margen < 0.97:
                    bugs_encontrados += 1
                    alerta = f"🚨 [{nombre_casa}] ¡BUG REAL (2 OPCIONES) en {deporte_detectado}!\n📉 Margen: {margen:.3f}\n💰 Cuotas Altas: {cuotas_usadas}\n📝 {texto_limpio[:70]}"
                    enviar_alerta(alerta)
        
        except Exception:
            continue
            
    print(f"[{nombre_casa}] Ciclo terminado. Bloques analizados: {len(partidos_procesados)} | Bugs: {bugs_encontrados}")

def ejecutar_escaneo_unico():
    print("🎯 Iniciando escaneo completo (Ascenso + Cuotas Altas)...")
    agente_actual = random.choice(USER_AGENTS)
    
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
        )
        contexto = navegador.new_context(
            no_viewport=True,
            user_agent=agente_actual
        )
        contexto.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)
        pagina = contexto.new_page()

        # 1. BETANO
        try:
            print("Escaneando Betano...")
            pagina.goto("https://www.betano.bet.ar/", timeout=60000)
            pagina.wait_for_load_state("domcontentloaded")
            pagina.wait_for_timeout(5000)
            try:
                btn = pagina.get_by_role("button", name=re.compile("Aceptar|OK|Entendido", re.IGNORECASE)).first
                if btn.is_visible(timeout=2000): btn.click()
            except: pass
            try:
                pagina.keyboard.press("Escape")
                pagina.wait_for_timeout(500)
            except: pass
            procesar_bloques(pagina, "BETANO")
        except Exception as e:
            print(f"Error en Betano: {e}")

        # 2. IVIBET
        try:
            print("Escaneando Ivibet...")
            pagina.goto("https://ivibet.com/es", timeout=60000)
            pagina.wait_for_load_state("domcontentloaded")
            pagina.wait_for_timeout(6000)
            try:
                pagina.keyboard.press("Escape")
                pagina.wait_for_timeout(500)
            except: pass
            procesar_bloques(pagina, "IVIBET")
        except Exception as e:
            print(f"Error en Ivibet: {e}")

        finally:
            navegador.close()

if __name__ == "__main__":
    ejecutar_escaneo_unico()
