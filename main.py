import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import unicodedata
import urllib3
import socket

# Desabilitar avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Testar Xtream API Pro", layout="centered")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FUNÇÕES ADICIONADAS PARA PAÍS E FORMATO ---

def get_geo_info(base_url):
    """Retorna o país do servidor baseado no IP do domínio"""
    try:
        domain = urlparse(base_url).hostname
        ip_addr = socket.gethostbyname(domain)
        resp = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=5).json()
        country = resp.get('country', 'Desconhecido')
        country_code = resp.get('countryCode', '')
        return f"{country} {country_code}".strip()
    except:
        return "Desconhecido"

def get_stream_format(api_url):
    """Verifica o formato predominante na lista de canais"""
    try:
        # Pega apenas os 5 primeiros canais para ser rápido
        resp = requests.get(f"{api_url}&action=get_live_streams", headers=HEADERS, verify=False, timeout=10).json()
        if isinstance(resp, list) and len(resp) > 0:
            # Tenta identificar a extensão ou container
            ext = resp[0].get('container_extension', 'ts')
            return str(ext).upper()
    except:
        pass
    return "TS/M3U8"

# --- FIM DAS FUNÇÕES ADICIONADAS ---

def clear_input():
    st.session_state.m3u_input_value = ""
    st.session_state.search_name = ""

def normalize_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

def parse_urls(message):
    m3u_pattern = r"(https?://[^\s\"']+(?:get\.php|player_api\.php)\?username=([a-zA-Z0-9._-]+)&password=([a-zA-Z0-9._-]+))"
    found = re.findall(m3u_pattern, message)
    parsed_urls = []
    unique_ids = set()

    for item in found:
        full_url, user, pwd = item
        base_match = re.search(r"(https?://[^/]+(?::\d+)?)", full_url)
        if base_match:
            base_full = base_match.group(1)
            parsed_url = urlparse(base_full)
            base_display = f"{parsed_url.scheme}://{parsed_url.hostname}"
            
            identifier = (base_full, user, pwd)
            if identifier not in unique_ids:
                unique_ids.add(identifier)
                parsed_urls.append({
                    "base": base_full, 
                    "display_base": base_display, 
                    "username": user, 
                    "password": pwd
                })
    return parsed_urls

def get_xtream_info(url_data, search_name=None):
    base, user, pwd = url_data["base"], url_data["username"], url_data["password"]
    u_enc, p_enc = quote(user), quote(pwd)
    api_url = f"{base}/player_api.php?username={u_enc}&password={p_enc}"
    
    res = {
        "is_json": False, "exp_date": "Falha no login",
        "active_cons": "0", "max_connections": "0", "has_adult_content": False,
        "live_count": 0, "vod_count": 0, "series_count": 0,
        "country": "Buscando...", "format": "Buscando...",
        "search_matches": {"Canais": [], "Filmes": [], "Séries": {}}
    }

    try:
        # Busca País e Formato em paralelo com a auth
        res["country"] = get_geo_info(base)
        res["format"] = get_stream_format(api_url)

        main_resp = requests.get(api_url, headers=HEADERS, verify=False, timeout=12)
        data_json = main_resp.json()

        if "user_info" in data_json:
            res["is_json"] = True
            u_info = data_json.get("user_info", {})
            exp = u_info.get("exp_date")
            
            if exp and str(exp).isdigit():
                if int(exp) == 0: res["exp_date"] = "Ilimitado"
                else: res["exp_date"] = datetime.fromtimestamp(int(exp)).strftime('%d/%m/%Y')
            
            res["active_cons"] = u_info.get("active_cons", "0")
            res["max_connections"] = u_info.get("max_connections", "0")

            # Contagem simplificada para performance
            res["live_count"] = data_json.get("categories", {}).get("live", 0) # Alguns servidores enviam no index
            
            # Se não enviou no index, fazemos as chamadas de contagem
            actions = {"live": "get_live_streams", "vod": "get_vod_streams", "series": "get_series"}
            for key, act in actions.items():
                r = requests.get(f"{api_url}&action={act}", headers=HEADERS, verify=False, timeout=10).json()
                if isinstance(r, list):
                    res[f"{key}_count"] = len(r)

    except: pass
    return url_data, res

# Interface Streamlit
st.title("🔌 Xtream API Analyzer + Geo")

with st.form("xtream_form"):
    m3u_message = st.text_area("Cole os links ou texto aqui:", height=150)
    submit = st.form_submit_button("🚀 Analisar Agora")

if submit and m3u_message:
    parsed = parse_urls(m3u_message)
    if not parsed:
        st.error("Nenhum link válido encontrado.")
    else:
        for url in parsed:
            orig, info = get_xtream_info(url)
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"### {info['country']} 🌍")
                    st.write(f"**URL:** `{orig['display_base']}`")
                    st.write(f"👤 **User:** `{orig['username']}`")
                    st.write(f"📅 **Expira:** `{info['exp_date']}`")
                    st.write(f"📦 **Formato:** `{info['format']}`")
                with col2:
                    st.write(f"📺 **Canais:** `{info['live_count']}`")
                    st.write(f"🎬 **Filmes:** `{info['vod_count']}`")
                    st.write(f"🍿 **Séries:** `{info['series_count']}`")
                    st.write(f"👥 **Conexões:** `{info['active_cons']}/{info['max_connections']}`")
