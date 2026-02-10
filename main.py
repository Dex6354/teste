import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse
from datetime import datetime
import socket
import urllib3

# Desabilitar avisos SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream Formats & Geo", layout="wide")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLC/3.0.18"
}

def get_geo_info(base_url):
    """Obtém o país e a bandeira do servidor"""
    try:
        domain = urlparse(base_url).hostname
        ip_addr = socket.gethostbyname(domain)
        resp = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=5).json()
        country = resp.get('country', 'Unknown')
        code = resp.get('countryCode', '')
        # Mapeamento simples de bandeira para alguns países
        flags = {"UA": "🇺🇦", "BR": "🇧🇷", "US": "🇺🇸", "FR": "🇫🇷", "DE": "🇩🇪"}
        flag = flags.get(code, "🌐")
        return f"{flag} {country} ({code})"
    except:
        return "🌐 Desconhecido"

def get_supported_formats(api_url):
    """Analisa os formatos e extensões suportados pelo painel"""
    formats = set()
    try:
        # 1. Verifica no Index da API (Geralmente contém as extensões permitidas)
        resp = requests.get(api_url, headers=HEADERS, verify=False, timeout=10).json()
        u_info = resp.get("user_info", {})
        
        # O campo 'url_suffix' indica o formato padrão (ex: .ts ou .m3u8)
        suffix = u_info.get("url_suffix")
        if suffix:
            formats.add(suffix.replace('.', ''))

        # 2. Amostragem de streams para ver formatos reais
        streams_resp = requests.get(f"{api_url}&action=get_live_streams", headers=HEADERS, verify=False, timeout=10).json()
        if isinstance(streams_resp, list) and len(streams_resp) > 0:
            for item in streams_resp[:10]: # Checa os 10 primeiros para diversidade
                ext = item.get('container_extension')
                if ext: formats.add(ext)
        
        # 3. Adiciona RTMP se o servidor for antigo/compatível (comum em Xtream)
        # Se aceita TS e M3U8, geralmente suporta ambos via parâmetro &output=
        if "ts" in formats or "m3u8" in formats:
            formats.add("ts")
            formats.add("m3u8")
            
    except:
        pass
    
    # Retorna como string formatada [m3u8, ts, rtmp]
    return f"[{', '.join(sorted(list(formats)))}]" if formats else "[ts]"

def parse_input(text):
    """Extrai credenciais de blocos de texto ou URLs"""
    pattern = r"(https?://[^\s\"']+(?:get\.php|player_api\.php)\?username=([a-zA-Z0-9._-]+)&password=([a-zA-Z0-9._-]+))"
    return re.findall(pattern, text)

# --- INTERFACE ---
st.title("🛡️ Xtream Intelligence Analyzer")
st.markdown("Extração de **País 🌍** e **Formatos Suportados 🎥**")

with st.container(border=True):
    input_text = st.text_area("Cole aqui os links ou o dump do painel:", height=150)
    btn_analisar = st.button("🚀 Iniciar Varredura")

if btn_analisar and input_text:
    found_urls = parse_input(input_text)
    
    if not found_urls:
        st.error("Nenhuma credencial Xtream encontrada.")
    else:
        for full_url, user, pwd in found_urls:
            base = re.search(r"(https?://[^/]+)", full_url).group(1)
            api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
            
            with st.spinner(f"Analisando {base}..."):
                geo = get_geo_info(base)
                formats = get_supported_formats(api_url)
                
                # Chamada para pegar contagens
                try:
                    main_data = requests.get(api_url, headers=HEADERS, verify=False, timeout=10).json()
                    u_info = main_data.get("user_info", {})
                    status = "✅ Ativo" if u_info.get("auth") == 1 else "❌ Inativo"
                    exp = datetime.fromtimestamp(int(u_info['exp_date'])).strftime('%d/%m/%Y') if u_info.get('exp_date', '').isdigit() and int(u_info['exp_date']) > 0 else "Ilimitado"
                except:
                    status, exp = "⚠️ Erro", "N/A"

                # --- EXIBIÇÃO ESTILIZADA ---
                with st.expander(f"📋 Resultado para: {urlparse(base).hostname}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**𝐂𝐨𝐮𝐧𝐭𝐫𝐲:** ➩ {geo}")
                        st.write(f"**𝐅𝐨𝐫𝐦𝐚𝐭𝐬:** ➩ `{formats}`")
                    with c2:
                        st.write(f"**Status:** {status}")
                        st.write(f"**Validade:** {exp}")
                    with c3:
                        st.write(f"👤 **User:** `{user}`")
                        st.write(f"🔑 **Pass:** `{pwd}`")

st.divider()
st.caption("Nota: A detecção de formatos [rtmp] é baseada na compatibilidade padrão de servidores Xtream UI.")
