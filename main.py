import streamlit as st
import socket
import ssl
from urllib.parse import urlparse
import urllib3

# Desabilitar avisos SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Domain Hunter Pro", layout="wide")

def get_domains_from_ssl(hostname):
    """Extrai domínios do certificado usando biblioteca nativa ssl"""
    domains = set()
    domains.add(hostname)
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                # Extrai o Common Name (CN) e Subject Alternative Names (SAN)
                if 'subject' in cert:
                    for sub in cert['subject']:
                        for key, value in sub:
                            if key == 'commonName':
                                domains.add(value.replace('*.', ''))
                
                if 'subjectAltName' in cert:
                    for type, name in cert['subjectAltName']:
                        if type == 'DNS':
                            domains.add(name.replace('*.', ''))
    except:
        pass
    return domains

# --- INTERFACE ---
st.title("🔍 Xtream Domain & Mirror Finder")
st.markdown("O sistema analisa o **Certificado SSL** do servidor para encontrar endereços alternativos (mirrors).")

# Link padrão preenchido conforme solicitado
default_link = "http://cuzcuz.shop:80/get.php?username=miguelima9&password=7635fx9999&type=m3u_plus"

input_text = st.text_input(
    "URL do Servidor / Link M3U:", 
    value=default_link,
    placeholder="Insira o link aqui..."
)

if st.button("🚀 Mapear Domínios"):
    if input_text:
        parsed_url = urlparse(input_text)
        hostname = parsed_url.hostname
        
        if not hostname:
            st.error("⚠️ URL inválida. Verifique o formato.")
        else:
            with st.spinner(f"Escaneando infraestrutura de {hostname}..."):
                # Busca de mirrors via SSL
                found_domains = get_domains_from_ssl(hostname)
                
                # Busca de IP e DNS Reverso
                try:
                    ip_addr = socket.gethostbyname(hostname)
                    reverse_dns = socket.getfqdn(ip_addr)
                except:
                    ip_addr, reverse_dns = "Não encontrado", "Não encontrado"

                # --- EXIBIÇÃO DOS RESULTADOS ---
                st.subheader("📊 Relatório de Infraestrutura")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("IP Atual", ip_addr)
                with c2:
                    st.metric("DNS Reverso", reverse_dns)

                st.divider()

                if len(found_domains) > 1:
                    st.success(f"🔥 Foram detectados **{len(found_domains)}** domínios vinculados!")
                    
                    # Exibe a lista formatada
                    lista_limpa = sorted(list(found_domains))
                    for d in lista_limpa:
                        tipo = "🌐 Principal" if d == hostname else "🔗 Mirror / Alternativo"
                        st.write(f"- `{d}` ({tipo})")
                    
                    st.text_area("Lista bruta para cópia:", value="\n".join(lista_limpa), height=150)
                else:
                    st.warning("Apenas o domínio principal foi detectado. Isso acontece se o servidor não usar SSL ou não tiver mirrors registrados no mesmo certificado.")

st.divider()
st.caption("Nota: Este scanner foca na camada de transporte (SSL/TLS) para identificar redirecionamentos e redundâncias.")
