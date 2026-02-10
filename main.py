import streamlit as st
import requests
import pandas as pd
import re
import socket
from urllib.parse import urlparse

st.set_page_config(page_title="M3U Analyzer", page_icon="📺", layout="wide")

st.title("📺 M3U Stream & Server Analyzer")

url_input = st.text_input("Link M3U:", placeholder="http://...")

def get_server_info(url):
    try:
        domain = urlparse(url).netloc.split(':')[0]
        ip_addr = socket.gethostbyname(domain)
        resp = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=5).json()
        return {
            "IP": ip_addr,
            "País": f"{resp.get('country')} {resp.get('countryCode')}",
            "Org": resp.get('isp')
        }
    except:
        return {"IP": "N/A", "País": "Desconhecido", "Org": "N/A"}

if url_input:
    with st.spinner('Lendo dados do servidor...'):
        try:
            # Info do Servidor
            info = get_server_info(url_input)
            
            # Request com User-Agent de IPTV para evitar bloqueio
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLC/3.0.18'}
            r = requests.get(url_input, headers=headers, timeout=15)
            
            if r.status_code != 200:
                st.error(f"O servidor recusou a conexão (Erro {r.status_code}). O link pode ter expirado.")
                st.stop()

            # Processamento da Lista
            lines = r.text.splitlines()
            streams = []
            current = {}

            for line in lines:
                if line.startswith("#EXTINF:"):
                    # Extrair nome e tentar achar bandeiras/países
                    name = line.split(',')[-1].strip()
                    current['Nome'] = name
                    
                    # Tenta detectar país pelo nome (ex: UA, BR, PT)
                    country_match = re.search(r'\[(\w{2})\]|\s(\w{2})\s|🇺🇦|🇧🇷', name)
                    current['País Detectado'] = country_match.group(0) if country_match else "Geral"
                
                elif line.strip().startswith("http"):
                    link = line.strip()
                    current['URL'] = link
                    # Identificar formato pela extensão
                    ext = urlparse(link).path.split('.')[-1].lower()
                    current['Formato'] = ext if ext in ['ts', 'm3u8', 'mp4', 'mkv'] else 'stream'
                    streams.append(current)
                    current = {}

            # Exibição dos Dados
            if not streams:
                st.warning("⚠️ O link foi lido, mas a lista de canais está VAZIA. Verifique o usuário e senha.")
                st.json(info)
            else:
                df = pd.DataFrame(streams)
                
                # Interface
                col1, col2, col3 = st.columns(3)
                col1.metric("Servidor (IP)", info['IP'])
                col2.metric("País do Host", info['País'])
                col3.metric("Canais Encontrados", len(df))

                st.subheader("📊 Resultados da Análise")
                
                # Filtro Seguro: Só executa se a coluna existir
                if 'Formato' in df.columns:
                    fmts = st.multiselect("Filtrar por Formato:", df['Formato'].unique(), default=df['Formato'].unique())
                    df = df[df['Formato'].isin(fmts)]

                st.dataframe(df, use_container_width=True)
                
                # Resumo de Formatos
                st.write("**Contagem por Formato:**")
                st.write(df['Formato'].value_counts())

        except Exception as e:
            st.error(f"Erro inesperado: {e}")
else:
    st.info("Insira o link acima para analisar.")
