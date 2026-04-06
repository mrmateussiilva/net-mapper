# app/config.py

import streamlit as st

# ── Constants ─────────────────────────────────────────────────────────────────
SHEETS = ['Deck B - L717', 'Deck M - L521', 'Deck M - L519']
IGNORE = {'XXX', 'XX', 'X', 'EMPTY', 'NAN', '?', '', 'NONE'}
CMAP = {
    'Active':         '#10b981',
    'Inactive/Empty': '#6b7280',
    'Unknown':        '#f59e0b',
    'Not Documented': '#ef4444',
}
TEMPLATE = 'plotly_white'

# ── Minimal CSS: only component-level, no background overrides ────────────────
CSS_CONTENT = """
<style>
.badge {
    display:inline-block; padding:2px 10px; border-radius:999px;
    font-size:0.72rem; font-weight:600; margin:2px;
}
.b-green  { background:#d1fae5; color:#065f46; }
.b-blue   { background:#dbeafe; color:#1e40af; }
.b-yellow { background:#fef3c7; color:#92400e; }
.b-red    { background:#fee2e2; color:#991b1b; }
.b-purple { background:#ede9fe; color:#5b21b6; }
.b-gray   { background:#f3f4f6; color:#374151; }

.wiki-card {
    border:1px solid rgba(0,0,0,0.1); border-radius:12px;
    padding:1rem 1.2rem; margin-bottom:0.5rem;
    transition:box-shadow 0.2s;
}
.wiki-card:hover { box-shadow:0 4px 16px rgba(0,0,0,0.08); }

.stat-row {
    display:flex; gap:8px; flex-wrap:wrap; margin:0.5rem 0;
}
.stat-pill {
    background:rgba(0,0,0,0.04); border-radius:8px;
    padding:6px 14px; font-size:0.8rem;
    display:flex; flex-direction:column; align-items:center;
}
.stat-pill strong { font-size:1.2rem; font-weight:700; line-height:1.2; }

.pp-grid { display:flex; flex-wrap:wrap; gap:5px; margin:0.8rem 0; }
.pp-led {
    width:32px; height:32px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:0.6rem; font-weight:700; cursor:default;
    border:1.5px solid transparent; transition:transform 0.1s;
}
.pp-led:hover { transform:scale(1.25); }
.led-on  { background:#d1fae5; border-color:#059669; color:#065f46; }
.led-off { background:#f3f4f6; border-color:#d1d5db; color:#9ca3af; }
.led-unk { background:#fef3c7; border-color:#d97706; color:#92400e; }
.led-nd  { background:#fee2e2; border-color:#ef4444; color:#991b1b; }

.rack-slot {
    display:flex; align-items:center; gap:8px;
    padding:3px 6px; border-radius:4px; margin-bottom:2px;
    font-size:0.72rem;
}
.rack-num { color:#9ca3af; min-width:28px; text-align:right; font-size:0.65rem; }
.rack-bar {
    flex:1; height:24px; border-radius:4px;
    display:flex; align-items:center; padding:0 10px;
    font-size:0.68rem; font-weight:600; white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis;
}
.rs-active   { background:#d1fae5; color:#065f46; border:1px solid #6ee7b7; }
.rs-inactive { background:#f3f4f6; color:#9ca3af; border:1px solid #e5e7eb; }
.rs-unknown  { background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }

.breadcrumb { font-size:0.78rem; color:#6b7280; margin-bottom:1rem; }
.breadcrumb span { color:#111827; font-weight:600; }

.section-header {
    display:flex; align-items:center; gap:10px;
    border-bottom:2px solid #e5e7eb; padding-bottom:6px; margin:1.5rem 0 1rem;
}
.section-header h3 { margin:0; font-size:1rem; }
</style>
"""

def inject_custom_css():
    """Injects custom CSS templates into Streamlit app."""
    st.markdown(CSS_CONTENT, unsafe_allow_html=True)
