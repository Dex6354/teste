import streamlit as st
import requests
import pandas as pd
import re
import socket
from urllib.parse import urlparse
import concurrent.futures

st.set_page_config(page_title="IPTV Analyzer Pro", page_icon="📡", layout="wide")

st.title("📡 Analisador de M3U & Status de Conexão")

url_input = st.text_input("Cole o link M3U aqui:", placeholder="http://...")

def get_server_info(url):
    try:
        domain = urlparse(url).netloc.split(':')[0]
        ip_addr = socket.gethostbyname(domain)
        # Usando ip-api (gratuita e rápida)
        response = requests.get(f"http://ip-api.com/json/{ip_addr}").json()
        return {
            "IP": ip_addr,
            "País": f"{response.get('country')} {response.get('countryCode')}",
            "Cidade": response.get('city'),
            "Provedor": response.get('isp'),
            "Status Servidor": response.get('status')
        }
    except:
        return None

def check_link_status(url):
    try:
        # Timeout curto para não travar; apenas verifica se o cabeçalho responde
        r = requests.head(url, timeout=3)
        return "✅ ON" if r.status_code == 200 else f"❌ {r.status_code}"
    except:
        return "offline"

if url_input:
    with st.spinner('Extraindo dados do servidor e processando lista...'):
        server_info = get_server_info(url_input)
        
        try:
            r = requests.get(url_input, timeout=15)
            lines = r.text.splitlines()
            
            streams = []
            current_item = {}
            for line in lines:
                if line.startswith("#EXTINF:"):
                    name_match = re.search(r',(.+)$', line)
                    current_item['Nome'] = name_match.group(1) if name_match else "Sem Nome"
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    current_item['Grupo'] = group_match.group(1) if group_match else "Geral"
                elif line.startswith("http"):
                    current_item['URL'] = line
                    ext = urlparse(line).path.split('.')[-1].lower()
                    current_item['Formato'] = ext if ext in ['ts', 'm3u8', 'mp4'] else 'stream'
                    streams.append(current_item)
                    current_item = {}

            df = pd.DataFrame(streams)

            # --- Painel de Informações ---
            if server_info:
                st.success(f"Servidor localizado em: {server_info['País']} ({server_info['Cidade']})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("País", server_info['País'])
                c2.metric("ISP", server_info['Provedor'])
                c3.metric("Total de Itens", len(df))
                c4.metric("Formato Nativo", df['Formato'].mode()[0] if not df.empty else "N/A")

            # --- Verificação de Status ---
            st.divider()
            st.subheader("🛠 Teste de Conectividade")
            num_test = st.number_input("Quantos links deseja testar (amostra)?", min_value=1, max_value=100, value=10)
            
            if st.button(f"Testar Primeiros {num_test} Links"):
                test_list = df.head(num_test).copy()
                with st.spinner('Testando links...'):
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        results = list(executor.map(check_link_status, test_list['URL']))
                    test_list['Status'] = results
                    st.table(test_list[['Nome', 'Status', 'Formato']])

            # --- Tabela Completa ---
            st.subheader("📋 Lista Completa")
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao ler M3U: {e}")
else:
    st.info("Insira um link para começar.")
