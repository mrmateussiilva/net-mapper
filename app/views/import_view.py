# app/views/import_view.py
# Tela de importação da planilha Safe Notos para o banco de infraestrutura.
# Fluxo: Upload → Parse → Preview → Confirmar → Resultado

import io
import pandas as pd
import streamlit as st

from app.infra_import import parse_spreadsheet, execute_import


def render_import_view():
    """Página de importação em 3 fases: upload, preview e execução."""

    st.subheader("📥 Importar Planilha — Safe Notos")
    st.caption(
        "Importe os dados de cabeamento diretamente da planilha Safe Notos "
        "para popular racks, equipamentos, portas e conexões automaticamente."
    )

    # ── Fase 1: Upload ────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Selecione a planilha (.xlsx)",
        type=["xlsx"],
        key="import_xlsx_uploader",
        help="Deve conter as abas: Deck B - L717, Deck M - L521, Deck M - L519",
    )

    if not uploaded:
        st.info("📂 Faça upload da planilha para continuar.")
        _render_format_info()
        return

    # ── Fase 2: Parse + Preview ───────────────────────────────────────────────
    with st.spinner("Lendo e analisando a planilha..."):
        try:
            file_bytes = uploaded.read()
            parsed = parse_spreadsheet(file_bytes)
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            return

    # Avisos da leitura
    for w in parsed.get("warnings", []):
        st.warning(w)

    sheets = parsed.get("sheets_found", [])
    if not sheets:
        st.error("Nenhuma aba válida encontrada na planilha.")
        return

    # KPIs extraídos
    n_racks  = len(parsed["racks"])
    n_equip  = len(parsed["equipment"])
    n_conns  = len(parsed["connections"])
    # portas são criadas junto com conexões (pp_port + sw_port por conexão)
    n_ports  = n_conns * 2  # estimativa: 2 portas por conexão

    st.success(f"✅ Planilha lida com sucesso — **{len(sheets)}** aba(s) processada(s).")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🗄️ Racks", n_racks)
    k2.metric("📟 Equipamentos", n_equip)
    k3.metric("🔌 Portas (estimado)", f"~{n_ports}")
    k4.metric("🔗 Conexões", n_conns)

    # Contagem por sheet
    st.markdown("**Conexões válidas por aba:**")
    for sheet, count in parsed.get("row_counts", {}).items():
        st.markdown(f"- `{sheet}`: **{count}** conexões")

    st.divider()

    # Tabs de preview
    tab_racks, tab_equip, tab_conns = st.tabs(["🗄️ Racks", "📟 Equipamentos", "🔗 Conexões (amostra)"])

    with tab_racks:
        rack_rows = [{"Rack": name, "Localização": loc} for name, loc in sorted(parsed["racks"].items())]
        st.dataframe(pd.DataFrame(rack_rows), use_container_width=True, hide_index=True)

    with tab_equip:
        eq_rows = [
            {
                "Nome": e["name"],
                "Tipo inferido": e["type"],
                "Rack": e.get("rack_name") or "—",
                "Deck": e.get("location") or "—",
            }
            for e in sorted(parsed["equipment"].values(), key=lambda x: x["name"])
        ]
        eq_df = pd.DataFrame(eq_rows)

        # Breakdown por tipo
        type_counts = eq_df["Tipo inferido"].value_counts().to_dict()
        type_badges = "  ".join(f"**{k}**: {v}" for k, v in type_counts.items())
        st.caption(f"Tipos detectados — {type_badges}")

        search_eq = st.text_input("🔍 Filtrar por nome ou tipo", key="imp_eq_search")
        filtered_eq = eq_df[
            eq_df["Nome"].str.contains(search_eq, case=False, na=False) |
            eq_df["Tipo inferido"].str.contains(search_eq, case=False, na=False)
        ] if search_eq else eq_df
        st.dataframe(filtered_eq, use_container_width=True, hide_index=True, height=380)

    with tab_conns:
        sample = parsed["connections"][:200]
        conn_rows = [
            {
                "Patch Panel": c["pp_name"],
                "Porta PP":   c["pp_port"],
                "Switch":     c["sw_name"],
                "Porta SW":   c["sw_port"],
                "Wall Port":  c["wall_port"] or "—",
                "Status":     c["status"],
                "Deck":       c["deck"],
                "Notas":      c["notes"] or "—",
            }
            for c in sample
        ]
        conn_df = pd.DataFrame(conn_rows)

        def _color_status(val):
            m = {
                "active":  "background-color:#d1fae5;color:#065f46",
                "free":    "background-color:#f3f4f6;color:#6b7280",
                "unknown": "background-color:#fef3c7;color:#92400e",
            }
            return m.get(val, "")

        st.caption(f"Mostrando {len(sample)} de {n_conns} conexões")
        styled = conn_df.style.map(_color_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=400)

    st.divider()

    # ── Fase 3: Opções e Confirmação ──────────────────────────────────────────
    st.markdown("### ⚙️ Opções de importação")

    col_opt1, col_opt2 = st.columns(2)
    skip_existing = col_opt1.toggle(
        "Ignorar duplicatas (recomendado)",
        value=True,
        help="Se ativado, não sobrescreve racks/equipamentos já existentes no banco.",
    )
    col_opt2.markdown(
        """
        <div style="font-size:0.8rem;color:#6b7280;margin-top:0.5rem;">
        Equipamentos com o mesmo nome serão<br>pulados se esta opção estiver ativa.
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("### ✅ Confirmar importação")
    st.warning(
        f"Você está prestes a importar **{n_racks} racks**, "
        f"**{n_equip} equipamentos** e **{n_conns} conexões** no banco. "
        "Esta operação não pode ser desfeita automaticamente."
    )

    confirm = st.checkbox("Confirmo que quero executar a importação", key="import_confirm_check")

    col_btn, col_space = st.columns([1, 4])
    with col_btn:
        run_btn = st.button(
            "🚀 Executar importação",
            disabled=not confirm,
            type="primary",
            key="btn_run_import",
        )

    if run_btn and confirm:
        progress = st.progress(0, text="Iniciando importação...")

        try:
            progress.progress(10, text="Criando racks...")
            report = execute_import(parsed, skip_existing=skip_existing)
            progress.progress(100, text="Concluído!")
        except Exception as e:
            st.error(f"Erro durante a importação: {e}")
            return

        st.divider()
        st.markdown("## 📊 Resultado da importação")

        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("🗄️ Racks criados",    report["racks_created"],  f"-{report['racks_skipped']} skip")
        r2.metric("📟 Equip. criados",   report["equip_created"],  f"-{report['equip_skipped']} skip")
        r3.metric("🔌 Portas criadas",   report["ports_created"])
        r4.metric("🔗 Conexões criadas", report["conns_created"],  f"-{report['conns_skipped']} skip")
        r5.metric("⚠️ Erros",            len(report["errors"]))

        if report["errors"]:
            with st.expander(f"⚠️ {len(report['errors'])} erro(s) — clique para ver"):
                for err in report["errors"][:50]:
                    st.text(err)

        if report["conns_created"] > 0:
            st.success(
                f"✅ Importação concluída! "
                f"{report['equip_created']} equipamentos e {report['conns_created']} conexões inseridos."
            )
            st.info("Acesse **📋 Visão Geral** para ver os equipamentos importados.")
        else:
            st.warning("Nenhuma conexão foi criada. Verifique os erros ou se os dados já existem.")


def _render_format_info():
    """Mostra informações sobre o formato esperado da planilha."""
    with st.expander("ℹ️ Formato esperado da planilha"):
        st.markdown("""
**Abas esperadas:**
- `Deck B - L717`
- `Deck M - L521`
- `Deck M - L519`

**Colunas esperadas (linha 6 do Excel):**

| Coluna | Descrição |
|---|---|
| `Rack` | ID do rack de origem (patch panel) |
| `Optic Patch Painel` | Nome do patch panel |
| `Port` | Porta no patch panel |
| `Wall Port` | Tomada de parede (metadado) |
| `Rack2` | ID do rack de destino (switch) |
| `Switch` | Nome do switch |
| `Switch Port` | Porta no switch |
| `Active` | Status (Yes/No/XX/EMPTY...) |
| `Observation` | Notas |
        """)
