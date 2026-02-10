import streamlit as st
import requests
import pandas as pd
import re
import socket
from urllib.parse import urlparse

st.set_page_config(page_title="M3U Analyzer Pro", layout="wide")

st.title("📺 Analisador de Listas IPTV")

url_input = st.text_input("Cole seu link M3U:", placeholder="http://...")

def get_server_info(url):
    try:
        domain = urlparse(url).netloc.split(':')[0]
        ip_addr = socket.gethostbyname(domain)
        resp = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=5).json()
        return resp
    except:
        return None

if url_input:
    with st.spinner('Processando...'):
        try:
            # 1. Tentar pegar info do servidor
            server_data = get_server_info(url_input)
            
            # 2. Tentar baixar a lista com User-Agent de Smart TV
            headers = {'User-Agent': 'Mozilla/5.0 (SmartHub; SmartTV; Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url_input, headers=headers, timeout=15)
            
            if response.status_code != 200:
                st.error(f"❌ O servidor retornou erro {response.status_code}. Link possivelmente expirado.")
                st.stop()

            # 3. Extração manual para garantir que as colunas existam
            lines = response.text.splitlines()
            streams = []
            current_name = ""
            current_group = ""

            for line in lines:
                if line.startswith("#EXTINF:"):
                    # Pega o nome após a última vírgula
                    current_name = line.split(',')[-1].strip()
                    # Tenta pegar o grupo
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    current_group = group_match.group(1) if group_match else "Geral"
                
                elif line.strip().startswith("http"):
                    url_path = urlparse(line.strip()).path.lower()
                    # Define o formato pela extensão
                    if url_path.endswith('.ts'): fmt = "TS"
                    elif url_path.endswith('.m3u8'): fmt = "M3U8"
                    elif url_path.endswith('.mp4'): fmt = "MP4"
                    else: fmt = "Stream"
                    
                    streams.append({
                        "Nome": current_name,
                        "Grupo": current_group,
                        "Formato": fmt,
                        "URL": line.strip()
                    })

            # 4. Exibição Segura
            if not streams:
                st.warning("⚠️ O link foi acessado, mas não há canais dentro dele. Verifique seu login/senha.")
                if server_data:
                    st.write(f"**Servidor:** {server_data.get('isp')} | **País:** {server_data.get('country')}")
            else:
                df = pd.DataFrame(streams)
                
                # Métricas
                c1, c2, c3 = st.columns(3)
                if server_data:
                    c1.metric("País do Server", f"{server_data.get('countryCode')} 🌍")
                    c2.metric("Provedor", server_data.get('org', 'N/A'))
                c3.metric("Canais Encontrados", len(df))

                st.subheader("📋 Lista de Conteúdo")
                
                # Filtro que só aparece se houver dados
                if "Formato" in df.columns:
                    opcoes = st.multiselect("Filtrar Formatos:", df['Formato'].unique(), default=df['Formato'].unique())
                    df_filtrado = df[df['Formato'].isin(opcoes)]
                    st.dataframe(df_filtrado, use_container_width=True)
                else:
                    st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Ocorreu um problema técnico: {e}")
else:
    st.info("Insira um link acima para analisar.")
