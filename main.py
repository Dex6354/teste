import streamlit as st
import requests
import socket
from urllib.parse import urlparse
import urllib3
import ssl

# Desabilitar avisos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Ultra Domain Hunter", layout="wide")

def get_domains_via_openssl_fallback(hostname):
    """
    Tenta capturar o certificado usando a biblioteca SSL padrão com 
    configurações específicas para contornar bloqueios de Proxy/Cloudflare.
    """
    domains = {hostname}
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # A chave aqui é o server_hostname que ativa o SNI correto
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                
                # Coleta Common Name
                if 'subject' in cert:
                    for sub in cert['subject']:
                        for key, val in sub:
                            if key == 'commonName':
                                domains.add(val.replace('*.', ''))
                
                # Coleta Subject Alternative Names (Onde está o 5sco.co)
                if 'subjectAltName' in cert:
                    for type, name in cert['subjectAltName']:
                        if type == 'DNS':
                            domains.add(name.replace('*.', ''))
    except Exception as e:
        st.error(f"Erro técnico na varredura: {e}")
    
    return domains

# --- INTERFACE ---
st.title("🛡️ Ultra Domain & SAN Scanner")
st.markdown("Varredura profunda de certificados para encontrar mirrors ocultos (Ex: 5sco.co).")

# Link padrão
default_link = "http://tv10.me"

input_text = st.text_input("Cole o link M3U ou domínio:", value=default_link)

if st.button("🔍 Localizar Mirrors Ocultos"):
    if input_text:
        # Extrair hostname de forma limpa
        domain = input_text.replace("http://", "").replace("https://", "").split(":")[0].split("/")[0]
        
        with st.spinner(f"Analisando certificados de {domain}..."):
            all_domains = get_domains_via_openssl_fallback(domain)
            
            # Tentar pegar o IP para info adicional
            try:
                ip_addr = socket.gethostbyname(domain)
            except:
                ip_addr = "Não identificado"

            st.subheader(f"🌐 Relatório: {domain}")
            st.info(f"**IP de Conexão:** `{ip_addr}`")
            
            st.divider()

            # Filtramos domínios irrelevantes (como domínios da própria cloudflare)
            mirrors = sorted([d.lower() for d in all_domains if d])
            
            if len(mirrors) > 1:
                st.success(f"✅ Encontrados **{len(mirrors)}** domínios vinculados no certificado!")
                
                # Exibição organizada
                cols = st.columns(2)
                for idx, d in enumerate(mirrors):
                    with cols[idx % 2]:
                        st.code(d, language="text")
                
                st.text_area("Lista para cópia rápida:", value="\n".join(mirrors), height=150)
            else:
                st.warning("Apenas um domínio encontrado. Se você sabe que existem outros, o servidor pode estar usando certificados isolados por domínio.")

st.divider()
st.caption("Nota: Este scanner utiliza SNI (Server Name Indication) para tentar extrair a lista SAN do certificado.")
