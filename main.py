import streamlit as st
import requests
import pandas as pd
import re
import socket
from urllib.parse import urlparse
import concurrent.futures

st.set_page_config(page_title="M3U Master Analyzer", page_icon="📡", layout="wide")

st.title("📡 M3U Stream & Server Analyzer")

url_input = st.text_input("Insira o link M3U:", placeholder="http://...")

def get_server_info(url):
    try:
        domain = urlparse(url).netloc.split(':')[0]
        ip_addr = socket.gethostbyname(domain)
        # API de Geolocalização rápida
        resp = requests.get(f"http://ip-api.com/json/{ip_addr}", timeout=5).json()
        return {
            "IP": ip_addr,
            "País": f"{resp.get('country')} {resp.get('countryCode')}",
            "Cidade": resp.get('city'),
            "Provedor": resp.get('isp')
        }
    except:
        return {"IP": "N/A", "País": "Não Identificado", "Cidade": "N/A", "Provedor": "N/A"}

if url_input:
    with st.spinner('Extraindo dados...'):
        try:
            # 1. Info do Servidor
            info = get_server_info(url_input)
            
            # 2. Requisição simulando um Player de IPTV (VLC)
            headers = {'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18'}
            response = requests.get(url_input, headers=headers, timeout=15)
            
            if response.status_code != 200:
                st.error(f"O servidor retornou erro {response.status_code}. O link pode estar offline ou bloqueado.")
                st.stop()

            # 3. Parsing manual do M3U
            lines = response.text.splitlines()
            data = []
            temp_entry = {}

            for line in lines:
                if line.startswith("#EXTINF:"):
                    # Extrai o nome do canal (após a última vírgula)
                    name = line.split(',')[-1] if ',' in line else "Sem Nome"
                    temp_entry['Nome'] = name.strip()
                    
                    # Extrai o grupo (categoria)
                    group = re.search(r'group-title="([^"]+)"', line)
                    temp_entry['Grupo'] = group.group(1) if group else "Geral"
                
                elif line.strip().startswith("http"):
                    temp_entry['URL'] = line.strip()
                    
                    # Identifica o formato pela extensão do arquivo
                    path = urlparse(line.strip()).path.lower()
                    if path.endswith('.ts'): fmt = 'TS'
                    elif path.endswith('.m3u8'): fmt = 'M3U8'
                    elif path.endswith('.mp4'): fmt = 'MP4'
                    else: fmt = 'Stream/HLS'
                    
                    temp_entry['Formato'] = fmt
                    data.append(temp_entry)
                    temp_entry = {}

            # 4. Verificação de Dados
            if not data:
                st.warning("Nenhum canal encontrado. O link pode estar vazio ou as credenciais expiraram.")
                st.json(info)
            else:
                df = pd.DataFrame(data)

                # Métricas principais
                c1, c2, c3 = st.columns(3)
                c1.metric("Localização", info['País'])
                c2.metric("Total de Canais", len(df))
                c3.metric("IP do Host", info['IP'])

                st.subheader("🌐 Detalhes Técnicos")
                st.write(f"**Provedor (ISP):** {info['Provedor']} | **Cidade:** {info['Cidade']}")

                st.subheader("📊 Lista de Canais")
                # Filtro seguro
                if 'Formato' in df.columns:
                    formatos = st.multiselect("Filtrar formatos:", df['Formato'].unique(), default=df['Formato'].unique())
                    df_final = df[df['Formato'].isin(formatos)]
                else:
                    df_final = df
                
                st.dataframe(df_final, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao processar: {str(e)}")
else:
    st.info("Aguardando link M3U para análise.")
