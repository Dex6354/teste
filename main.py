import streamlit as st
import requests
import pandas as pd
import re
import socket
from urllib.parse import urlparse
import concurrent.futures

st.set_page_config(page_title="M3U Analyzer Pro", page_icon="📺", layout="wide")

st.title("📺 M3U Stream & Server Analyzer")

# Input do link
url_input = st.text_input("Link M3U:", placeholder="http://...")

def get_server_info(url):
    try:
        domain = urlparse(url).netloc.split(':')[0]
        ip_addr = socket.gethostbyname(domain)
        # Usando ip-api (sem necessidade de API key para este volume)
        resp = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=5).json()
        return {
            "IP": ip_addr,
            "Country": f"{resp.get('country')} {resp.get('countryCode')}",
            "City": resp.get('city'),
            "Org": resp.get('isp')
        }
    except:
        return {"IP": "N/A", "Country": "Desconhecido", "City": "N/A", "Org": "N/A"}

def check_link_status(url):
    try:
        # Simula um player para o teste de status
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLC/3.0.18'}
        r = requests.head(url, headers=headers, timeout=3)
        return "✅ ON" if r.status_code < 400 else f"❌ {r.status_code}"
    except:
        return "⚠️ OFF"

if url_input:
    with st.spinner('Analisando link e servidor...'):
        try:
            # Info do Servidor
            server_info = get_server_info(url_input)
            
            # Headers para evitar bloqueio
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = requests.get(url_input, headers=headers, timeout=15)
            
            if r.status_code != 200:
                st.error(f"O servidor recusou a conexão. Status Code: {r.status_code}")
                st.stop()

            lines = r.text.splitlines()
            streams = []
            current_item = {}
            
            for line in lines:
                if line.startswith("#EXTINF:"):
                    name_match = re.search(r',(.+)$', line)
                    current_item['Nome'] = name_match.group(1).strip() if name_match else "Sem Nome"
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    current_item['Grupo'] = group_match.group(1) if group_match else "Geral"
                elif line.strip().startswith("http"):
                    current_item['URL'] = line.strip()
                    # Detectar formato pela URL
                    path = urlparse(line).path.lower()
                    if path.endswith('.ts'): current_item['Formato'] = 'TS'
                    elif path.endswith('.m3u8'): current_item['Formato'] = 'M3U8'
                    elif path.endswith('.mp4'): current_item['Formato'] = 'MP4'
                    elif path.endswith('.mkv'): current_item['Formato'] = 'MKV'
                    else: current_item['Formato'] = 'Stream'
                    
                    streams.append(current_item)
                    current_item = {}

            if not streams:
                st.warning("O link foi lido, mas nenhum canal/vídeo foi encontrado. Verifique se o usuário/senha estão ativos.")
                st.subheader("🌐 Detalhes do Servidor")
                st.json(server_info)
            else:
                df = pd.DataFrame(streams)

                # --- EXIBIÇÃO ---
                col1, col2, col3 = st.columns(3)
                col1.metric("País do Servidor", server_info['Country'])
                col2.metric("IP do Host", server_info['IP'])
                col3.metric("Total de Canais", len(df))

                st.subheader("🌐 Detalhes do Servidor")
                st.json(server_info)

                st.subheader("📊 Lista de Conteúdo")
                
                formato_filtro = st.multiselect("Filtrar por Formato:", df['Formato'].unique(), default=df['Formato'].unique())
                df_filtrado = df[df['Formato'].isin(formato_filtro)]
                
                st.dataframe(df_filtrado, use_container_width=True)

                # Teste de Status
                st.divider()
                if st.button("Testar Status (Primeiros 10)"):
                    test_list = df_filtrado.head(10).copy()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        results = list(executor.map(check_link_status, test_list['URL']))
                    test_list['Status'] = results
                    st.table(test_list[['Nome', 'Status', 'Formato']])

        except Exception as e:
            st.error(f"Erro crítico: {e}")
else:
    st.info("Insira um link para começar.")
