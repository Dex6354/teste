import streamlit as st
import socket
import ssl
from urllib.parse import urlparse
import urllib3

# Desabilitar avisos SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Domain Hunter Pro", layout="wide")

def get_all_domains_from_cert(hostname):
    """
    Tenta extrair domínios do certificado com tolerância a erros e timeout longo.
    """
    domains = set()
    if not hostname:
        return domains
        
    domains.add(hostname)
    
    # Contexto SSL ultra-permissivo
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # Forçar protocolos mais antigos se necessário
    context.set_ciphers('DEFAULT@SECLEVEL=1')

    # Tenta na porta 443 e também na 8443 (comum em painéis)
    for port in [443, 8443]:
        try:
            # Aumentamos o timeout para 15 segundos
            sock = socket.create_connection((hostname, port), timeout=15)
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                
                # Extração do Common Name
                for sub in cert.get('subject', ()):
                    for key, value in sub:
                        if key == 'commonName':
                            domains.add(value.replace('*.', ''))
                
                # Extração do SAN (Subject Alternative Names)
                if 'subjectAltName' in cert:
                    for type, name in cert['subjectAltName']:
                        if type == 'DNS':
                            domains.add(name.replace('*.', ''))
            break # Se conseguiu em uma porta, para de tentar outras
        except Exception:
            continue
            
    return domains

# --- INTERFACE ---
st.title("🔍 Deep Domain Scanner")
st.markdown("Busca avançada de mirrors via Certificado Digital (SAN/SSL).")

# Link padrão solicitado
default_link = "http://tv10.me"

input_text = st.text_input(
    "URL do Servidor / Link M3U:", 
    value=default_link,
    placeholder="Ex: http://servidor.com:80"
)

if st.button("🚀 Iniciar Varredura"):
    if input_text:
        # Extração limpa do hostname
        raw_url = input_text.strip()
        if not raw_url.startswith(('http://', 'https://')):
            raw_url = 'http://' + raw_url
        
        hostname = urlparse(raw_url).hostname
        
        if not hostname:
            st.error("⚠️ Hostname inválido.")
        else:
            with st.spinner(f"Tentando ler certificados de {hostname}... Isso pode levar 15s."):
                
                found_domains = get_all_domains_from_cert(hostname)
                
                try:
                    ip_addr = socket.gethostbyname(hostname)
                    reverse_dns = socket.getfqdn(ip_addr)
                except:
                    ip_addr, reverse_dns = "N/A", "N/A"

                # --- EXIBIÇÃO ---
                st.subheader(f"🌐 Resultados para {hostname}")
                
                c1, c2 = st.columns(2)
                c1.metric("IP do Servidor", ip_addr)
                c2.metric("DNS Reverso", reverse_dns)

                st.divider()

                # Limpeza final dos domínios encontrados
                lista_limpa = sorted([d.lower() for d in found_domains if d])

                if len(lista_limpa) > 1:
                    st.success(f"✅ Encontrados **{len(lista_limpa)}** domínios no certificado!")
                    for d in lista_limpa:
                        if d == hostname.lower():
                            st.write(f"🔹 **{d}** (Domínio Alvo)")
                        else:
                            st.write(f"🔗 `{d}` (Mirror Encontrado)")
                    
                    st.text_area("Copiável:", value="\n".join(lista_limpa), height=100)
                elif len(lista_limpa) == 1:
                    st.warning("Apenas o domínio original foi encontrado. O servidor pode estar usando um certificado único (sem mirrors) ou estar bloqueando a varredura.")
                else:
                    st.error("Não foi possível ler o certificado SSL (Conexão Recusada ou Timeout).")

st.info("💡 **Dica:** Servidores de IPTV costumam bloquear IPs de data centers (como os do Streamlit Cloud). Se o erro de Timeout persistir, tente rodar o código localmente em sua máquina.")
