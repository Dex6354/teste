 '')
                        imagem = p.get('imagem', '')
                        em_oferta = p.get('em_oferta', False)
                        oferta_info = p.get('oferta') or {}
                        preco_oferta = oferta_info.get('preco_oferta')
                        preco_antigo = oferta_info.get('preco_antigo')
                        imagem_url = f"https://produtos.vipcommerce.com.br/250x250/{imagem}"
                        preco_total = float(preco_oferta) if em_oferta and preco_oferta else preco
                        quantidade_dif = p.get('quantidade_unidade_diferente')
                        unidade_sigla = p.get('unidade_sigla')
                        preco_formatado = formatar_preco_unidade_personalizado(preco_total, quantidade_dif, unidade_sigla)

                        preco_info_extra = ""
                        descricao_modificada = descricao

                        # Cálculo extraído de preco_formatado: /0,15kg ou /250ml
                        match_preco_unitario = re.search(r"/\s*([\d.,]+)\s*(kg|g|l|ml)", preco_formatado.lower())
                        if match_preco_unitario:
                            quantidade_str = match_preco_unitario.group(1).replace(",", ".")
                            unidade = match_preco_unitario.group(2)

                            try:
                                quantidade = float(quantidade_str)
                                if unidade == "g":
                                    quantidade /= 1000
                                    unidade = "kg"
                                elif unidade == "ml":
                                    quantidade /= 1000
                                    unidade = "l"

                                if quantidade > 0:
                                    preco_unitario = preco_total / quantidade
                                    preco_info_extra += f"<div style='color:gray; font-size:0.75em;'>R$ {preco_unitario:.2f}/{unidade}</div>"
                            except:
                                pass

                        # Destaques para papel higiênico
                        if 'papel higienico' in remover_acentos(descricao):
                            descricao_modificada = re.sub(r'(folha simples)', r"<span style='color:red;'><b>\1</b></span>", descricao_modificada, flags=re.IGNORECASE)
                            descricao_modificada = re.sub(r'(folha dupla|folha tripla)', r"<span style='color:green;'><b>\1</b></span>", descricao_modificada, flags=re.IGNORECASE)

                        # Preço por folha (papel toalha)
                        total_folhas, preco_por_folha = calcular_preco_papel_toalha(descricao, preco_total)
                        if total_folhas and preco_por_folha:
                            descricao_modificada += f" <span style='color:gray;'>({total_folhas} folhas)</span>"
                            preco_info_extra += f"<div style='color:gray; font-size:0.75em;'>R$ {preco_por_folha:.3f}/folha</div>"
                        else:
                            _, preco_por_metro_str = calcular_precos_papel(descricao, preco_total)
                            _, preco_por_unidade_str = calcular_preco_unidade(descricao, preco_total)
                            if preco_por_metro_str:
                                preco_info_extra += f"<div style='color:gray; font-size:0.75em;'>{preco_por_metro_str}</div>"
                            # Evitar mostrar preço por unidade baseado na descrição se a unidade já está presente no preço_formatado
                            # Se já há unidade válida no preço formatado, evita duplicar info do título
                            match_preco_formatado = re.search(r"/\s*([\d.,]+)\s*(kg|g|l|ml|un|l|ml|folhas?|m)", preco_formatado.lower())
                            unidade_presente_no_preco = bool(match_preco_formatado)
                            if not unidade_presente_no_preco:

                                _, preco_por_unidade_str = calcular_preco_unidade(descricao, preco_total)
                                if preco_por_unidade_str:
                                    preco_info_extra += f"<div style='color:gray; font-size:0.75em;'>{preco_por_unidade_str}</div>"


                        # Preço por unidade (ovo)
                        if 'ovo' in remover_acentos(descricao).lower():
                            match_ovo = re.search(r'(\d+)\s*(unidades|un|ovos|c/|com)', descricao.lower())
                            if match_ovo:
                                qtd_ovos = int(match_ovo.group(1))
                                if qtd_ovos > 0:
                                    preco_por_ovo = preco_total / qtd_ovos
                                    preco_info_extra += f"<div style='color:gray; font-size:0.75em;'>R$ {preco_por_ovo:.2f}/unidade</div>"

                        if re.search(r'1\s*d[uú]zia', descricao.lower()):
                            preco_por_unidade_duzia = preco_total / 12
                            preco_info_extra += f"<div style='color:gray; font-size:0.75em;'>R$ {preco_por_unidade_duzia:.2f}/unidade (dúzia)</div>"

                        # Preço (com ou sem oferta)
                        if em_oferta and preco_oferta and preco_antigo:
                            preco_oferta_val = float(preco_oferta)
                            preco_antigo_val = float(preco_antigo)
                            desconto = round(100 * (preco_antigo_val - preco_oferta_val) / preco_antigo_val) if preco_antigo_val else 0
                            preco_antigo_str = f"R$ {preco_antigo_val:.2f}".replace('.', ',')
                            preco_html = f"""
                                <div><b>{preco_formatado}</b><br> <span style='color:red;font-weight: bold;'>({desconto}% OFF)</span></div>
                                <div><span style='color:gray; text-decoration: line-through;'>{preco_antigo_str}</span></div>
                            """
                        else:
                            preco_html = f"<div><b>{preco_formatado}</b></div>"

                        # Renderização final do produto
                        st.markdown(f"""
                            <div class='product-container'>
                                <div class='product-image'>
                                    <img src='{imagem_url}' width='80' style='display: block;'/>
                                    <img src='https://raw.githubusercontent.com/Dex6354/PrecoShibata/refs/heads/main/logo-shibata.png' width='80' 
                                        style='background-color: white; display: block; margin: 0 auto; border-radius: 4px; padding: 3px;'/>
                                </div>
                                <div class='product-info'>
                                    <div style='margin-bottom: 4px;'><b>{descricao_modificada}</b></div>
                                    <div style='font-size:0.85em;'>{preco_html}</div>
                                    <div style='font-size:0.85em;'>{preco_info_extra}</div>
                                </div>
                            </div>
                            <hr class='product-separator' />
                        """, unsafe_allow_html=True)


    # Exibição dos resultados na COLUNA 2 (Nagumo)
    with col2:
        st.markdown(f"""
            <h5 style="display: flex; align-items: center; justify-content: center;">
                <img src="https://institucional.nagumo.com.br/images/nagumo-2000.png" width="80" style="margin-right:8px; background-color: white; border-radius: 4px; padding: 2px;"/>
                Nagumo
            </h5>
        """, unsafe_allow_html=True)
        st.markdown(f"<small>🔎 {len(produtos_nagumo_ordenados)} produto(s) encontrado(s).</small>", unsafe_allow_html=True)
        if not produtos_nagumo_ordenados:
            st.warning("Nenhum produto encontrado.")
        for p in produtos_nagumo_ordenados:
            imagem = p['photosUrl'][0] if p.get('photosUrl') else ""
            preco_unitario = p['preco_unitario_str']
            preco = p['price']
            promocao = p.get("promotion") or {}
            cond = promocao.get("conditions") or []
            preco_desconto = None
            if promocao.get("isActive") and isinstance(cond, list) and len(cond) > 0:
                preco_desconto = cond[0].get("price")
            if preco_desconto and preco_desconto < preco:
                desconto_percentual = ((preco - preco_desconto) / preco) * 100
                preco_html = f"""
                    <span style='font-weight: bold; font-size: 1rem;'>R$ {preco_desconto:.2f}</span><br>
                    <span style='color: red; font-weight: bold;'> ({desconto_percentual:.0f}% OFF)</span><br>
                    <span style='text-decoration: line-through; color: gray;'>R$ {preco:.2f}</span>
                """
            else:
                preco_html = f"R$ {preco:.2f}"
            st.markdown(f"""
                <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0rem; flex-wrap: wrap;">
                    <div style="flex: 0 0 auto;">
                        <img src="{imagem}" width="80" style="border-radius:8px; display: block;"/>
                        <img src="https://institucional.nagumo.com.br/images/nagumo-2000.png" width="80" style="background-color: white; border-radius: 4px; padding: 3px; display: block;"/>
</div>
                    <div style="flex: 1; word-break: break-word; overflow-wrap: anywhere;">
                        <strong>{p['titulo_exibido']}</strong><br>
                        <strong>{preco_html}</strong><br>
                        <div style="margin-top: 4px; font-size: 0.9em; color: #666;">{preco_unitario}</div>
                        <div style="color: gray; font-size: 0.8em;">Estoque: {p['stock']}</div>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)
