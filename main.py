import streamlit as st
import re
import socket
import ssl
import OpenSSL
from urllib.parse import urlparse
import urllib3

# Configurações básicas
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="DNS & SSL Domain Hunter", layout="wide")

def get_domains_from_ssl(hostname, port=443):
    """Extrai todos os domínios listados no certificado SSL (SAN)"""
    domains = set()
    try:
        # Adiciona o próprio hostname original
        domains.add(hostname)
        
        # Conexão SSL para obter o certificado
        cert = ssl.get_server_certificate((hostname, port))
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        
        # Varre as extensões do certificado em busca de Subject Alternative Names
        for i in range(x509.get_extension_count()):
            ext = x509.get_extension(i)
            if ext.get_short_name() == b'subjectAltName':
                # Limpa a string para pegar apenas os nomes de domínio
                alt_names = str(ext).split(", ")
                for name in alt_names:
                    if "DNS:" in name:
                        domains.add(name.replace("DNS:", "").strip())
    except Exception as e:
        pass # Silencioso se não houver SSL ou falhar
    return domains

def get_reverse_dns(hostname):
    """Tenta encontrar o IP e verificar se há outros registros vinculados"""
    try:
        ip_addr = socket.gethostbyname(hostname)
        return ip_addr, socket.getfqdn(ip_addr)
    except:
        return None, None

# --- INTERFACE ---
st.title("🔍 Domain & SSL Mirror Hunter")
st.markdown("Insira o link M3U para descobrir todos os domínios alternativos vinculados ao servidor via **Certificado SSL** e **DNS**.")

input_text = st.text_input("Cole o link M3U ou URL do servidor aqui:", 
                          placeholder="http://exemplo.com:80/get.php?username=...")

if st.button("🔎 Buscar Domínios Alternativos"):
    if input_text:
        # Extração do Host e Porta
        parsed_url = urlparse(input_text)
        hostname = parsed_url.hostname
        port = parsed_url.port if parsed_url.port else (443 if parsed_url.scheme == "https" else 80)
        
        if not hostname:
            st.error("URL Inválida.")
        else:
            with st.spinner(f"Fazendo varredura profunda em {hostname}..."):
                # 1. Busca via SSL (A forma mais certeira de achar mirrors)
                # Tentamos na 443 mesmo que o link seja porta 80, pois o certificado fica lá
                ssl_domains = get_domains_from_ssl(hostname)
                
                # 2. Busca via IP/DNS
                ip, fqdn = get_reverse_dns(hostname)
                
                # --- EXIBIÇÃO ---
                st.subheader(f"🌐 Resultados para: {hostname}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**IP do Servidor:** `{ip}`")
                with col2:
                    st.info(f"**Hostname Reverso:** `{fqdn}`")

                st.divider()
                
                if ssl_domains:
                    st.success(f"Foram encontrados **{len(ssl_domains)}** domínios vinculados no SSL:")
                    
                    # Criar uma lista limpa para o usuário copiar
                    domain_list = sorted(list(ssl_domains))
                    
                    # Exibição em tabela para facilitar a leitura
                    for d in domain_list:
                        status = "🟢 Principal" if d == hostname else "🔗 Mirror / Alternativo"
                        st.code(f"{d} ({status})")
                        
                    # Opção de download ou cópia rápida
                    st.text_area("Lista para Copiar:", value="\n".join(domain_list), height=150)
                else:
                    st.warning("Nenhum domínio alternativo encontrado via SSL. O servidor pode não usar HTTPS ou não possuir nomes alternativos no certificado.")

st.caption("Nota: A verificação SSL tenta conectar preferencialmente na porta 443 para ler o certificado X.509.")
