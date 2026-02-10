import streamlit as st
import requests
import pandas as pd
import re
import socket
from urllib.parse import urlparse

st.set_page_config(page_title="M3U Analyzer Pro", page_icon="📺", layout="wide")

st.title("📺 M3U Stream & Server Analyzer")
st.markdown("Insira seu link M3U abaixo para analisar formatos e localização do servidor.")

# Input do link
url_input = st.text_input("Link M3U:", placeholder="http://exemplo.com/get.php?username=...")

def get_server_info(url):
    try:
        domain = urlparse(url).netloc.split(':')[0]
        ip_addr = socket.gethostbyname(domain)
        response = requests.get(f"https://ipapi.co/{ip_addr}/json/").json()
        return {
            "IP": ip_addr,
            "Country": f"{response.get('country_name')} {response.get('country_code')}",
            "City": response.get('city'),
            "Org": response.get('org')
        }
    except:
        return {"IP": "N/A", "Country": "Desconhecido", "City": "N/A", "Org": "N/A"}

if url_input:
    with st.spinner('Analisando link e servidor...'):
        try:
            # 1. Obter info do Servidor
            server_info = get_server_info(url_input)
            
            # 2. Baixar e Processar M3U
            r = requests.get(url_input, timeout=10)
            lines = r.text.splitlines()
            
            streams = []
            current_item = {}
            
            for line in lines:
                if line.startswith("#EXTINF:"):
                    # Extrair nome do canal
                    name_match = re.search(r',(.+)$', line)
                    current_item['Name'] = name_match.group(1) if name_match else "Unknown"
                    
                    # Extrair Grupo/Categoria
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    current_item['Group'] = group_match.group(1) if group_match else "N/A"
                    
                elif line.startswith("http"):
                    current_item['URL'] = line
                    # Identificar Formato
                    ext = urlparse(line).path.split('.')[-1].lower()
                    current_item['Format'] = ext if ext in ['ts', 'm3u8', 'mp4', 'mkv'] else 'Outro/Stream'
                    streams.append(current_item)
                    current_item = {}

            df = pd.DataFrame(streams)

            # --- EXIBIÇÃO ---
            col1, col2, col3 = st.columns(3)
            col1.metric("País do Servidor", server_info['Country'])
            col2.metric("IP do Host", server_info['IP'])
            col3.metric("Total de Canais", len(df))

            st.subheader("🌐 Detalhes do Servidor")
            st.json(server_info)

            st.subheader("📊 Lista de Conteúdo")
            
            # Filtros rápidos
            formato_filtro = st.multiselect("Filtrar por Formato:", df['Format'].unique(), default=df['Format'].unique())
            df_filtrado = df[df['Format'].isin(formato_filtro)]
            
            st.dataframe(df_filtrado, use_container_width=True)

            # Gráfico de Formatos
            st.subheader("📈 Distribuição de Formatos")
            st.bar_chart(df['Format'].value_counts())

        except Exception as e:
            st.error(f"Erro ao processar: {e}")
else:
    st.info("Aguardando link para iniciar a análise.")
