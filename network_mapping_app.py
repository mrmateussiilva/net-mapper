import traceback
import streamlit as st
import pandas as pd

# Page config must be the first Streamlit command
st.set_page_config(
    page_title="Network Mapping · Safe Notos",
    layout="wide",
    page_icon="🔌",
    initial_sidebar_state="expanded",
)

# Application modules
from app.config import inject_custom_css
from app.data import load_and_process_data
from app.ui import init_wiki_state, init_infra_state

from app.infra_db import init_db
from app.views.dashboard import render_dashboard
from app.views.grafo3d import render_grafo3d
from app.views.deck_view import render_deck_view
from app.views.racks_panels_view import render_racks_view, render_patch_panels_view
from app.views.wiki_view import render_wiki
from app.views.errors_view import render_errors_view
from app.views.spotlight_view import render_spotlight_view
from app.views.infra_view import render_infra

# Initialize UI styling and states
inject_custom_css()
init_wiki_state()
init_infra_state()
init_db()  # Creates infra tables in cabling.db if they don't exist yet

SHEET_MAP = {
    "📋 Deck B · L717": "Deck B - L717",
    "📋 Deck M · L521": "Deck M - L521",
    "📋 Deck M · L519": "Deck M - L519",
}

# ── Upload ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔌 Safe Notos")
    uploaded_file = st.file_uploader("Planilha (.xlsx)", type=["xlsx"])
    st.divider()

    # Infra nav is always visible (no spreadsheet required)
    nav_always = st.radio("Modo", ["📊 Mapeamento de Rede", "🏭 Infraestrutura"],
                          label_visibility="collapsed", key="top_mode")

if nav_always == "🏭 Infraestrutura":
    render_infra()
    st.stop()

if uploaded_file is None:
    st.title("🔌 Network Mapping — Safe Notos")
    st.info("👈 Faça upload da planilha na sidebar para começar a análise.")
    st.stop()

# ── Carregamento Otimizado de Dados ───────────────────────────────────────────
try:
    with st.spinner("Processando e otimizando dados..."):
        file_bytes = uploaded_file.read()
        dfs, all_df = load_and_process_data(file_bytes)
except Exception as e:
    st.error(f"Erro ao carregar a planilha. Verifique se o formato é válido.\nErro detalhado: {e}")
    st.stop()

# ── Menu de Navegação ─────────────────────────────────────────────────────────
with st.sidebar:
    nav = st.radio("Navegar", [
        "🏠 Dashboard",
        "🌐 Grafo 3D",
        "📋 Deck B · L717",
        "📋 Deck M · L521",
        "📋 Deck M · L519",
        "🏗️ Racks Físicos",
        "🔌 Patch Panels",
        "📖 Wiki",
        "🚨 Erros",
        "🔍 Spotlight",
    ], label_visibility="collapsed")

# ── Roteador Principal ────────────────────────────────────────────────────────
try:
    if nav == "🏠 Dashboard":
        render_dashboard(dfs, all_df)

    elif nav == "🌐 Grafo 3D":
        render_grafo3d(all_df)

    elif nav in SHEET_MAP:
        sheet_name = SHEET_MAP[nav]
        if sheet_name in dfs:
            render_deck_view(sheet_name, dfs[sheet_name])
        else:
            st.error(f"Aba '{sheet_name}' não encontrada na planilha fornecida.")

    elif nav == "🏗️ Racks Físicos":
        render_racks_view(dfs)

    elif nav == "🔌 Patch Panels":
        render_patch_panels_view(dfs)

    elif nav == "📖 Wiki":
        render_wiki(all_df)

    elif nav == "🚨 Erros":
        render_errors_view(dfs)

    elif nav == "🔍 Spotlight":
        render_spotlight_view(all_df)

except Exception as e:
    st.error(f"Ocorreu um erro interno durante a renderização da página '{nav}'.")
    with st.expander("Ver detalhes técnicos"):
        st.code(traceback.format_exc(), language="python")
