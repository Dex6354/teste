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
    Extrai exaustivamente todos os domínios do certificado SSL (SAN)
    """
    domains = set()
    if not hostname:
        return domains
        
    domains.add(hostname)
    
    # Tentamos conectar na porta 443 (padrão SSL)
    port = 443
    
    try:
        # Cria um contexto SSL que não valida o certificado (para aceitar mirrors expirados/autoassinados)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                
                # 1. Busca no Subject (Common Name)
                for sub in cert.get('subject', ()):
                    for key, value in sub:
                        if key == 'commonName':
                            domains.add(value.replace('*.', ''))
                
                # 2. Busca no Subject Alternative Name (SAN) - Onde ficam os mirrors
                if 'subjectAltName' in cert:
                    for type, name in cert['subjectAltName']:
                        if type == 'DNS':
                            domains.add(name.replace('*.', ''))
                            
    except Exception as e:
        st.error(f"Erro ao ler certificado de {hostname}: {e}")
        
    return domains

# --- INTERFACE ---
st.title("🔍 Xtream Domain & Mirror Finder (Deep Scan)")
st.markdown("Busca profunda por domínios alternativos via registros de certificados SSL.")

# Link padrão atualizado
default_link = "http://tv10.me"

input_text = st.text_input(
    "URL do Servidor / Link M3U:", 
    value=default_link,
    placeholder="Insira o link aqui..."
)

if st.button("🚀 Mapear Domínios"):
    if input_text:
        # Limpeza da URL para pegar apenas o domínio
        if not input_text.startswith(('http://', 'https://')):
            url_to_parse = 'http://' + input_text
        else:
            url_to_parse = input_text
            
        parsed_url = urlparse(url_to_parse)
        hostname = parsed_url.hostname
        
        if not hostname:
            st.error("⚠️ URL inválida.")
        else:
            with st.spinner(f"Fazendo varredura profunda no certificado de {hostname}..."):
                # Busca de mirrors via SSL (Deep Scan)
                found_domains = get_all_domains_from_cert(hostname)
                
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

                # Filtrar domínios vazios ou inválidos
                lista_limpa = sorted([d for d in found_domains if d])

                if len(lista_limpa) > 0:
                    st.success(f"🔥 Foram detectados **{len(lista_limpa)}** domínios no certificado!")
                    
                    for d in lista_limpa:
                        status = "🌐 Principal" if d == hostname else "🔗 Mirror / Alternativo"
                        st.write(f"- `{d}` ({status})")
                    
                    st.text_area("Lista bruta para cópia:", value="\n".join(lista_limpa), height=150)
                else:
                    st.warning("Nenhum domínio extraído. O servidor pode estar usando uma porta SSL não padrão ou não possuir SAN.")

st.divider()
st.caption("Nota: Se um domínio como '5sco.co' está no certificado de 'tv10.me', este script irá listá-lo.")
