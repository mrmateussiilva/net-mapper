import pandas as pd
import streamlit as st

from app.data import safe, ign

def patch_panel_html(pp_df: pd.DataFrame, pp_name: str, n_ports: int = 24) -> str:
    """Generates an HTML representation of a patch panel with LED status indicators."""
    port_status = {}
    port_info = {}
    
    for _, row in pp_df.iterrows():
        p = row.get("Port")
        if pd.notna(p):
            try:
                pi = int(p)
                port_status[pi] = safe(row.get("Active_norm", ""))
                sw = safe(row.get("Switch", ""))
                wp = safe(row.get("Wall Port", ""))
                sw_pt = safe(row.get("Switch Port", ""))
                
                info = f"Porta {pi}"
                if sw and not ign(sw): info += f" → {sw}"
                if sw_pt: info += f" :{sw_pt}"
                if wp and not ign(wp): info += f" | WP:{wp}"
                
                port_info[pi] = info
            except ValueError:
                pass # safely ignore ports that cannot be cast to int
                
    leds = ""
    for i in range(1, n_ports + 1):
        s = port_status.get(i, "")
        cls = "led-on" if s == "Active" else "led-off" if s == "Inactive/Empty" else "led-unk" if s == "Unknown" else "led-nd" if s == "Not Documented" else "led-off"
        leds += f'<div class="pp-led {cls}" title="{port_info.get(i, f"Porta {i}: —")}">{i}</div>'
        
    act = sum(1 for s in port_status.values() if s == "Active")
    tot = n_ports
    
    return f"""
<div style="border:1px solid rgba(0,0,0,0.1);border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
    <div>
      <strong style="font-size:0.95rem;">🔌 {pp_name}</strong>
      <span style="font-size:0.75rem;color:#6b7280;margin-left:8px;">{act}/{tot} portas ativas</span>
    </div>
    <div>
      <span class="badge b-green">{act} on</span>
      <span class="badge b-gray">{sum(1 for s in port_status.values() if s=="Inactive/Empty")} off</span>
      <span class="badge b-yellow">{sum(1 for s in port_status.values() if s=="Unknown")} unk</span>
    </div>
  </div>
  <div class="pp-grid">{leds}</div>
</div>"""


def rack_diagram_html(rack_df: pd.DataFrame, rack_name: str) -> str:
    """Generates an HTML representation of a physical rack with U-slots."""
    slots = ""
    sort_col = "Port" if "Port" in rack_df.columns else rack_df.columns[0]
    
    for i, (_, row) in enumerate(rack_df.sort_values(sort_col).iterrows(), 1):
        if i > 64: 
            break
        s = safe(row.get("Active_norm", ""))
        label = safe(row.get("Optic Patch Painel", "")) or safe(row.get("Switch", "")) or "—"
        sw = safe(row.get("Switch", ""))
        
        try:
            port = str(int(row["Port"])) if pd.notna(row.get("Port")) else "?"
        except ValueError:
            port = str(row["Port"]) if pd.notna(row.get("Port")) else "?"
            
        tip = f"{label} :{port}" + (f" → {sw}" if sw and not ign(sw) else "")
        cls = "rs-active" if s == "Active" else "rs-unknown" if s == "Unknown" else "rs-inactive"
        
        slots += f"""<div class="rack-slot" title="{tip}">
          <span class="rack-num">{i:02d}U</span>
          <div class="rack-bar {cls}">{label[:36]}</div>
        </div>"""
        
    act = (rack_df["Active_norm"] == "Active").sum()
    
    return f"""
<div style="border:1px solid rgba(0,0,0,0.1);border-radius:12px;padding:1rem;margin-top:0.5rem;">
  <div style="font-size:0.75rem;color:#6b7280;margin-bottom:0.6rem;font-weight:600;">
    RACK {rack_name} · {act}/{len(rack_df)} ativos
    &nbsp;<span class="badge b-green">● Active</span>
    <span class="badge b-gray">○ Empty</span>
    <span class="badge b-yellow">◌ Unknown</span>
  </div>
  {slots}
</div>"""


def style_status(df_in: pd.DataFrame, col: str = "Status"):
    """Styles a pandas dataframe to apply background colors based on port status."""
    def ca(v):
        m = {
            "Active": "background-color:#d1fae5;color:#065f46",
            "Inactive/Empty": "background-color:#f3f4f6;color:#6b7280",
            "Unknown": "background-color:#fef3c7;color:#92400e",
            "Not Documented": "background-color:#fee2e2;color:#991b1b"
        }
        return m.get(v, "")
        
    sty = df_in.style
    try:
        return sty.map(ca, subset=[col])
    except AttributeError:
        # Fallback for older pandas versions
        return sty.applymap(ca, subset=[col])


def init_wiki_state():
    """Initializes session state required for the Wiki navigation system."""
    if "wiki_type" not in st.session_state: 
        st.session_state.wiki_type = None
    if "wiki_name" not in st.session_state: 
        st.session_state.wiki_name = None

def go_wiki(wtype: str, wname: str):
    """Sets session state to navigate to a specific Wiki page and reruns."""
    st.session_state.wiki_type = wtype
    st.session_state.wiki_name = wname
    st.rerun()
