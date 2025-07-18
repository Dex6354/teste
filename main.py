from fastapi import FastAPI, Query
import requests
import unicodedata
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import uvicorn

app = FastAPI()

# Configurações para Shibata
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3NTE5MjQ5MjgsInZlciI6MSwiY2xpZW50IjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTYxIn0.yDCjqkeJv7D3wJ0T_fu3AaKlX9s5PQYXD19cESWpH-j3F_Is-Zb-bDdUvduwoI_RkOeqbYCuxN0ppQQXb1ArVg"
ORG_ID = "161"
HEADERS_SHIBATA = {
    "Authorization": f"Bearer {TOKEN}",
    "organizationid": ORG_ID,
    "sessao-id": "4ea572793a132ad95d7e758a4eaf6b09",
    "domainkey": "loja.shibata.com.br",
    "User-Agent": "Mozilla/5.0"
}

# Funções utilitárias (mantidas do código original)
def remover_acentos(texto):
    if not texto:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def gerar_formas_variantes(termo):
    variantes = {termo}
    if termo.endswith("s"):
        variantes.add(termo[:-1])
    else:
        variantes.add(termo + "s")
    return list(variantes)

def calcular_precos_papel(descricao, preco_total):
    desc_minus = descricao.lower()
    match_leve = re.search(r'leve\s*(\d+)', desc_minus)
    if match_leve:
        q_rolos = int(match_leve.group(1))
    else:
        match_rolos = re.search(r'(\d+)\s*(rolos|unidades|uni|pacotes|pacote)', desc_minus)
        q_rolos = int(match_rolos.group(1)) if match_rolos else None
    match_metros = re.search(r'(\d+(?:[\.,]\d+)?)\s*m(?:etros)?', desc_minus)
    m_rolos = float(match_metros.group(1).replace(',', '.')) if match_metros else None
    if q_rolos and m_rolos:
        preco_por_metro = preco_total / (q_rolos * m_rolos)
        return preco_por_metro, f"R$ {preco_por_metro:.3f}".replace('.', ',') + "/m"
    return None, None

def calcular_preco_unidade(descricao, preco_total):
    desc_minus = remover_acentos(descricao)
    match_kg = re.search(r'(\d+(?:[\.,]\d+)?)\s*(kg|quilo)', desc_minus)
    if match_kg:
        peso = float(match_kg.group(1).replace(',', '.'))
        return preco_total / peso, f"R$ {preco_total / peso:.2f}".replace('.', ',') + "/kg"
    match_g = re.search(r'(\d+(?:[\.,]\d+)?)\s*(g|gramas?)', desc_minus)
    if match_g:
        peso = float(match_g.group(1).replace(',', '.')) / 1000
        return preco_total / peso, f"R$ {preco_total / peso:.2f}".replace('.', ',') + "/kg"
    match_l = re.search(r'(\d+(?:[\.,]\d+)?)\s*(l|litros?)', desc_minus)
    if match_l:
        litros = float(match_l.group(1).replace(',', '.'))
        return preco_total / litros, f"R$ {preco_total / litros:.2f}".replace('.', ',') + "/L"
    match_ml = re.search(r'(\d+(?:[\.,]\d+)?)\s*(ml|mililitros?)', desc_minus)
    if match_ml:
        litros = float(match_ml.group(1).replace(',', '.')) / 1000
        return preco_total / litros, f"R$ {preco_total / litros:.2f}".replace('.', ',') + "/L"
    return None, None

def calcular_preco_papel_toalha(descricao, preco_total):
    desc = descricao.lower()
    qtd_unidades = None
    match_unidades = re.search(r'(\d+)\s*(rolos|unidades|pacotes|pacote|kits?)', desc)
    if match_unidades:
        qtd_unidades = int(match_unidades.group(1))
    folhas_por_unidade = None
    match_folhas = re.search(r'(\d+)\s*(folhas|toalhas)\s*cada', desc)
    if not match_folhas:
        match_folhas = re.search(r'(\d+)\s*(folhas|toalhas)', desc)
    if match_folhas:
        folhas_por_unidade = int(match_folhas.group(1))
    match_leve_folhas = re.search(r'leve\s*(\d+)\s*pague\s*\d+\s*folhas', desc)
    if match_leve_folhas:
        folhas_leve = int(match_leve_folhas.group(1))
        preco_por_folha = preco_total / folhas_leve if folhas_leve else None
        return folhas_leve, preco_por_folha
    match_leve_pague = re.findall(r'(\d+)', desc)
    folhas_leve = None
    if 'leve' in desc and 'folhas' in desc and match_leve_pague:
        folhas_leve = max(int(n) for n in match_leve_pague)
    match_unidades_kit = re.search(r'unidades por kit[:\- ]+(\d+)', desc)
    match_folhas_rolo = re.search(r'quantidade de folhas por (?:rolo|unidade)[:\- ]+(\d+)', desc)
    if match_unidades_kit and match_folhas_rolo:
        total_folhas = int(match_unidades_kit.group(1)) * int(match_folhas_rolo.group(1))
        preco_por_folha = preco_total / total_folhas if total_folhas else None
        return total_folhas, preco_por_folha
    if qtd_unidades and folhas_por_unidade:
        total_folhas = qtd_unidades * folhas_por_unidade
        preco_por_folha = preco_total / total_folhas if total_folhas else None
        return total_folhas, preco_por_folha
    if folhas_por_unidade:
        preco_por_folha = preco_total / folhas_por_unidade
        return folhas_por_unidade, preco_por_folha
    if folhas_leve:
        preco_por_folha = preco_total / folhas_leve
        return folhas_leve, preco_por_folha
    return None, None

def formatar_preco_unidade_personalizado(preco_total, quantidade, unidade):
    if not unidade:
        return None
    unidade = unidade.lower()
    if quantidade and quantidade != 1:
        return f"R$ {preco_total:.2f}".replace('.', ',') + f"/{str(quantidade).replace('.', ',')}{unidade.lower()}"
    else:
        return f"R$ {preco_total:.2f}".replace('.', ',') + f"/{unidade.lower()}"

# Funções para busca (mantidas do código original)
def buscar_pagina_shibata(termo, pagina):
    url = f"https://services.vipcommerce.com.br/api-admin/v1/org/{ORG_ID}/filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/{termo}?page={pagina}"
    try:
        response = requests.get(url, headers=HEADERS_SHIBATA, timeout=10)
        if response.status_code == 200:
            data = response.json().get('data', {}).get('produtos', [])
            return [produto for produto in data if produto.get("disponivel", True)]
        else:
            return []
    except requests.exceptions.RequestException:
        return []
    except Exception:
        return []

def contem_papel_toalha(texto):
    texto = remover_acentos(texto.lower())
    return "papel" in texto and "toalha" in texto

def extrair_info_papel_toalha(nome, descricao):
    texto_nome = remover_acentos(nome.lower())
    texto_desc = remover_acentos(descricao.lower())
    match = re.search(r'(\d+)\s*(un|unidades?|rolos?)\s*(\d+)\s*(folhas|toalhas)', texto_nome)
    if match:
        rolos = int(match.group(1))
        folhas_por_rolo = int(match.group(3))
        total_folhas = rolos * folhas_por_rolo
        return rolos, folhas_por_rolo, total_folhas, f"{rolos} {match.group(2)}, {folhas_por_rolo} {match.group(4)}"
    match = re.search(r'(\d+)\s*(folhas|toalhas)', texto_nome)
    if match:
        total_folhas = int(match.group(1))
        return None, None, total_folhas, f"{total_folhas} {match.group(2)}"
    texto_completo = f"{texto_nome} {texto_desc}"
    match = re.search(r'(\d+)\s*(un|unidades?|rolos?)\s*.*?(\d+)\s*(folhas|toalhas)', texto_completo)
    if match:
        rolos = int(match.group(1))
        folhas_por_rolo = int(match.group(3))
        total_folhas = rolos * folhas_por_rolo
        return rolos, folhas_por_rolo, total_folhas, f"{rolos} {match.group(2)}, {folhas_por_rolo} {match.group(4)}"
    match = re.search(r'(\d+)\s*(folhas|toalhas)', texto_completo)
    if match:
        total_folhas = int(match.group(1))
        return None, None, total_folhas, f"{total_folhas} {match.group(2)}"
    m_un = re.search(r"(\d+)\s*(un|unidades?)", texto_completo)
    if m_un:
        total = int(m_un.group(1))
        return None, None, total, f"{total} unidades"
    return None, None, None, None

def calcular_preco_unitario_nagumo(preco_valor, descricao, nome, unidade_api=None):
    preco_unitario = "Sem unidade"
    texto_completo = f"{nome} {descricao}".lower()
    if contem_papel_toalha(texto_completo):
        rolos, folhas_por_rolo, total_folhas, texto_exibicao = extrair_info_papel_toalha(nome, descricao)
        if total_folhas and total_folhas > 0:
            preco_por_item = preco_valor / total_folhas
            return f"R$ {preco_por_item:.3f}/folha"
        return "Preço por folha: n/d"
    if "papel higi" in texto_completo:
        match_rolos = re.search(r"leve\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"\blv?\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"\blv?(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"\bl\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"c/\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"(\d+)\s*rolos?", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"(\d+)\s*(un|unidades?)", texto_completo)
        match_metros = re.search(r"(\d+[.,]?\d*)\s*(m|metros?|mt)", texto_completo)
        if match_rolos and match_metros:
            try:
                rolos = int(match_rolos.group(1))
                metros = float(match_metros.group(1).replace(',', '.'))
                if rolos > 0 and metros > 0:
                    preco_por_metro = preco_valor / rolos / metros
                    return f"R$ {preco_por_metro:.3f}/m"
            except:
                pass
    fontes = [descricao.lower(), nome.lower()]
    for fonte in fontes:
        match_g = re.search(r"(\d+[.,]?\d*)\s*(g|gramas?)", fonte)
        if match_g:
            gramas = float(match_g.group(1).replace(',', '.'))
            if gramas > 0:
                return f"R$ {preco_valor / (gramas / 1000):.2f}/kg"
        match_kg = re.search(r"(\d+[.,]?\d*)\s*(kg|quilo)", fonte)
        if match_kg:
            kg = float(match_kg.group(1).replace(',', '.'))
            if kg > 0:
                return f"R$ {preco_valor / kg:.2f}/kg"
        match_ml = re.search(r"(\d+[.,]?\d*)\s*(ml|mililitros?)", fonte)
        if match_ml:
            ml = float(match_ml.group(1).replace(',', '.'))
            if ml > 0:
                return f"R$ {preco_valor / (ml / 1000):.2f}/L"
        match_l = re.search(r"(\d+[.,]?\d*)\s*(l|litros?)", fonte)
        if match_l:
            litros = float(match_l.group(1).replace(',', '.'))
            if litros > 0:
                return f"R$ {preco_valor / litros:.2f}/L"
        match_un = re.search(r"(\d+[.,]?\d*)\s*(un|unidades?)", fonte)
        if match_un:
            unidades = float(match_un.group(1).replace(',', '.'))
            if unidades > 0:
                return f"R$ {preco_valor / unidades:.2f}/un"
    if unidade_api:
        unidade_api = unidade_api.lower()
        if unidade_api == 'kg':
            return f"R$ {preco_valor:.2f}/kg"
        elif unidade_api == 'g':
            return f"R$ {preco_valor * 1000:.2f}/kg"
        elif unidade_api == 'l':
            return f"R$ {preco_valor:.2f}/L"
        elif unidade_api == 'ml':
            return f"R$ {preco_valor * 1000:.2f}/L"
        elif unidade_api == 'un':
            return f"R$ {preco_valor:.2f}/un"
    return preco_unitario

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    if match:
        return float(match.group(1).replace(',', '.'))
    return float('inf')

def buscar_nagumo(term="banana"):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.nagumo.com",
        "Referer": "https://www.nagumo.com/",
        "User-Agent": "Mozilla/5.0",
        "apollographql-client-name": "Ecommerce SSR",
        "apollographql-client-version": "0.11.0"
    }
    payload = {
        "operationName": "SearchProducts",
        "variables": {
            "searchProductsInput": {
                "clientId": "NAGUMO",
                "storeReference": "22",
                "currentPage": 1,
                "minScore": 1,
                "pageSize": 100,
                "search": [{"query": term}],
                "filters": {},
                "googleAnalyticsSessionId": ""
            }
        },
        "query": """
        query SearchProducts($searchProductsInput: SearchProductsInput!) {
          searchProducts(searchProductsInput: $searchProductsInput) {
            products {
              name
              price
              photosUrl
              sku
              stock
              description
              unit
              promotion {
                isActive
                type
                conditions {
                  price
                  priceBeforeTaxes
                }
              }
            }
          }
        }
        """
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        return data.get("data", {}).get("searchProducts", {}).get("products", [])
    except requests.exceptions.RequestException:
        return []
    except Exception:
        return []

# Endpoint principal da API
@app.get("/buscar")
async def buscar_produtos(termo: str = Query("banana", min_length=1)):
    termo = termo.strip().lower()
    termos_expandidos = gerar_formas_variantes(remover_acentos(termo))
    
    # Busca Shibata
    produtos_shibata = []
    max_workers = 8
    max_paginas = 15
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(buscar_pagina_shibata, t, pagina)
                   for t in termos_expandidos
                   for pagina in range(1, max_paginas + 1)]
        for future in as_completed(futures):
            produtos_shibata.extend(future.result())

    ids_vistos = set()
    produtos_shibata = [p for p in produtos_shibata if p.get('id') not in ids_vistos and not ids_vistos.add(p.get('id'))]

    termo_sem_acento = remover_acentos(termo)
    palavras_termo = termo_sem_acento.split()
    produtos_shibata_filtrados = [
        p for p in produtos_shibata
        if all(
            palavra in remover_acentos(
                f"{p.get('descricao', '')} {p.get('nome', '')}"
            ) for palavra in palavras_termo
        )
    ]

    produtos_shibata_processados = []
    for p in produtos_shibata_filtrados:
        if not p.get("disponivel", True):
            continue
        preco = float(p.get('preco') or 0)
        em_oferta = p.get('em_oferta', False)
        oferta_info = p.get('oferta') or {}
        preco_oferta = oferta_info.get('preco_oferta')
        preco_total = float(preco_oferta) if em_oferta and preco_oferta else preco
        descricao = p.get('descricao', '')
        quantidade_dif = p.get('quantidade_unidade_diferente')
        unidade_sigla = p.get('unidade_sigla')
        if unidade_sigla and unidade_sigla.lower() == "grande":
            unidade_sigla = None
        preco_formatado = formatar_preco_unidade_personalizado(preco_total, quantidade_dif, unidade_sigla)
        descricao_limpa = descricao.lower().replace('grande', '').strip()
        preco_unidade_val, _ = calcular_preco_unidade(descricao_limpa, preco_total)

        match = re.search(r"/\s*([\d.,]+)\s*(kg|g|l|ml)", preco_formatado.lower()) if preco_formatado else None
        if match:
            try:
                quantidade = float(match.group(1).replace(",", "."))
                unidade = match.group(2).lower()
                if unidade == "g":
                    quantidade /= 1000
                    unidade = "kg"
                elif unidade == "ml":
                    quantidade /= 1000
                    unidade = "l"
                if quantidade > 0:
                    preco_unidade_val = preco_total / quantidade
            except:
                pass

        preco_por_metro_val, preco_por_metro_str = calcular_precos_papel(descricao, preco_total)

        if not preco_unidade_val or preco_unidade_val == float('inf'):
            match_unidade = re.search(r"/\s*([a-zA-Z]+)", preco_formatado.lower()) if preco_formatado else None
            unidade_fallback = match_unidade.group(1) if match_unidade else "un"
            preco_unidade_val = preco_total

        total_folhas, preco_por_folha = calcular_preco_papel_toalha(descricao, preco_total)
        preco_por_folha_val = preco_por_folha if preco_por_folha else float('inf')

        imagem_url = f"https://produtos.vipcommerce.com.br/250x250/{p.get('imagem', '')}"
        preco_antigo = oferta_info.get('preco_antigo')
        desconto = round(100 * (float(preco_antigo) - preco_total) / float(preco_antigo)) if em_oferta and preco_antigo else None

        preco_info_extra = []
        if match and quantidade > 0:
            preco_info_extra.append(f"R$ {preco_unidade_val:.2f}/{unidade}")
        if total_folhas and preco_por_folha:
            preco_info_extra.append(f"R$ {preco_por_folha:.3f}/folha")
        if preco_por_metro_str:
            preco_info_extra.append(preco_por_metro_str)
        if 'ovo' in remover_acentos(descricao).lower():
            match_ovo = re.search(r'(\d+)\s*(unidades|un|ovos|c/|com)', descricao.lower())
            if match_ovo:
                qtd_ovos = int(match_ovo.group(1))
                if qtd_ovos > 0:
                    preco_por_ovo = preco_total / qtd_ovos
                    preco_info_extra.append(f"R$ {preco_por_ovo:.2f}/unidade")
            if re.search(r'1\s*d[uú]zia', descricao.lower()):
                preco_por_unidade_duzia = preco_total / 12
                preco_info_extra.append(f"R$ {preco_por_unidade_duzia:.2f}/unidade (dúzia)")

        descricao_modificada = descricao
        if 'papel higienico' in remover_acentos(descricao):
            descricao_modificada = re.sub(r'(folha simples)', r"\1", descricao_modificada, flags=re.IGNORECASE)
            descricao_modificada = re.sub(r'(folha dupla|folha tripla)', r"\1", descricao_modificada, flags=re.IGNORECASE)

        produtos_shibata_processados.append({
            "descricao": descricao_modificada,
            "preco": f"R$ {preco_total:.2f}",
            "preco_formatado": preco_formatado,
            "preco_info_extra": preco_info_extra,
            "imagem": imagem_url,
            "em_oferta": em_oferta,
            "desconto": f"{desconto}% OFF" if desconto else None,
            "preco_antigo": f"R$ {float(preco_antigo):.2f}" if preco_antigo else None,
            "preco_unidade_val": preco_unidade_val,
            "preco_por_metro_val": preco_por_metro_val if preco_por_metro_val else float('inf'),
            "preco_por_folha_val": preco_por_folha_val,
            "total_folhas": total_folhas
        })

    if 'papel toalha' in termo_sem_acento:
        produtos_shibata_ordenados = sorted(produtos_shibata_processados, key=lambda x: x['preco_por_folha_val'])
    elif 'papel higienico' in termo_sem_acento:
        produtos_shibata_ordenados = sorted(produtos_shibata_processados, key=lambda x: x['preco_por_metro_val'])
    else:
        def preco_mais_preciso(produto):
            descricao = produto.get('descricao', '').lower()
            preco_total = float(produto.get('preco').replace('R$ ', ''))
            if 'ovo' in remover_acentos(descricao):
                match_duzia = re.search(r'1\s*d[uú]zia', descricao)
                if match_duzia:
                    return preco_total / 12
                match = re.search(r'(\d+)\s*(unidades|un|ovos|c\/|com)', descricao)
                if match:
                    qtd = int(match.group(1))
                    if qtd > 0:
                        return preco_total / qtd
            valores = [produto.get('preco_unidade_val', float('inf'))]
            return min(valores)
        produtos_shibata_ordenados = sorted(produtos_shibata_processados, key=preco_mais_preciso)

    # Busca Nagumo
    produtos_nagumo = []
    for termo_expandido in termos_expandidos:
        produtos_nagumo.extend(buscar_nagumo(termo_expandido))
    for palavra in palavras_termo:
        produtos_nagumo.extend(buscar_nagumo(palavra))
    produtos_nagumo_unicos = {p['sku']: p for p in produtos_nagumo}.values()

    produtos_nagumo_filtrados = []
    for produto in produtos_nagumo_unicos:
        texto = f"{produto['name']} {produto.get('description', '')}"
        texto_normalizado = remover_acentos(texto)
        if all(p in texto_normalizado for p in palavras_termo):
            produtos_nagumo_filtrados.append(produto)

    produtos_nagumo_processados = []
    for p in produtos_nagumo_filtrados:
        preco_normal = p.get("price", 0)
        promocao = p.get("promotion") or {}
        cond = promocao.get("conditions") or []
        preco_desconto = None
        if promocao.get("isActive") and isinstance(cond, list) and len(cond) > 0:
            preco_desconto = cond[0].get("price")
        preco_exibir = preco_desconto if preco_desconto else preco_normal

        preco_unitario = calcular_preco_unitario_nagumo(preco_exibir, p['description'], p['name'], p.get("unit"))
        preco_unitario_valor = extrair_valor_unitario(preco_unitario)
        titulo = p['name']
        texto_completo = p['name'] + " " + p['description']
        if contem_papel_toalha(texto_completo):
            rolos, folhas_por_rolo, total_folhas, texto_exibicao = extrair_info_papel_toalha(p['name'], p['description'])
            if texto_exibicao:
                titulo += f" ({texto_exibicao})"
        if "papel higi" in remover_acentos(titulo.lower()):
            titulo_lower = remover_acentos(titulo.lower())
            if "folha simples" in titulo_lower:
                titulo = re.sub(r"(folha simples)", r"\1", titulo, flags=re.IGNORECASE)
            if "folha dupla" in titulo_lower or "folha tripla" in titulo_lower:
                titulo = re.sub(r"(folha dupla|folha tripla)", r"\1", titulo, flags=re.IGNORECASE)

        desconto_percentual = ((preco_normal - preco_desconto) / preco_normal * 100) if preco_desconto and preco_desconto < preco_normal else None
        produtos_nagumo_processados.append({
            "titulo": titulo,
            "preco": f"R$ {preco_exibir:.2f}",
            "preco_unitario": preco_unitario,
            "imagem": p['photosUrl'][0] if p.get('photosUrl') else "",
            "estoque": p['stock'],
            "em_promocao": bool(preco_desconto and preco_desconto < preco_normal),
            "desconto": f"{desconto_percentual:.0f}% OFF" if desconto_percentual else None,
            "preco_antigo": f"R$ {preco_normal:.2f}" if desconto_percentual else None,
            "preco_unitario_valor": preco_unitario_valor
        })

    produtos_nagumo_ordenados = sorted(produtos_nagumo_processados, key=lambda x: x['preco_unitario_valor'])

    return {
        "shibata": {
            "total": len(produtos_shibata_ordenados),
            "produtos": produtos_shibata_ordenados
        },
        "nagumo": {
            "total": len(produtos_nagumo_ordenados),
            "produtos": produtos_nagumo_ordenados
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
