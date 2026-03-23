import base64
import io
import os
import json
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client, Client
import requests
# ── Supabase ───────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── App ────────────────────────────────────────────────────────────────────────
# ── OpenRouter ────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL   = "meta-llama/llama-3.1-8b-instruct:free"  # free model on OpenRouter

CEDI = '\u20b5'
SITE_URL = os.environ.get("SITE_URL", "sales-dashboard.app")

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[
        {'name': 'viewport', 'content': 'width=device-width, initial-scale=1'},
        {'name': 'mobile-web-app-capable', 'content': 'yes'},
        {'name': 'apple-mobile-web-app-capable', 'content': 'yes'},
    ],
)
server = app.server

# ── Design tokens ──────────────────────────────────────────────────────────────
COLORS = {
    'primary':   '#667eea', 'secondary': '#764ba2',
    'success':   '#10b981', 'warning':   '#f59e0b',
    'danger':    '#ef4444', 'light':     '#f3f4f6',
    'dark':      '#1f2937', 'white':     '#ffffff',
}
CHART_H = 320
BTN_BASE = {
    'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer',
    'fontSize': '0.95em', 'fontWeight': '600', 'touchAction': 'manipulation',
    'transition': 'opacity 0.15s',
}
INPUT_STYLE = {
    'width': '100%', 'padding': '10px 12px', 'boxSizing': 'border-box',
    'border': '2px solid var(--card-border, #e5e7eb)', 'borderRadius': '8px',
    'fontSize': '1em', 'outline': 'none',
    'backgroundColor': 'var(--card-bg, white)', 'color': 'var(--text, #1f2937)',
}
LABEL_STYLE = {
    'display': 'block', 'marginBottom': '6px', 'fontWeight': '600',
    'color': 'var(--text, #1f2937)', 'fontSize': '0.9em',
}
AUTH_INPUT = {}
AUTH_WRAP = {
    'display': 'flex', 'minHeight': '100dvh',
    'alignItems': 'center', 'justifyContent': 'center',
    'background': '#f4f6f8', 'fontFamily': 'Segoe UI',
    'padding': '20px', 'boxSizing': 'border-box',
}
AUTH_CARD = {
    'width': '100%', 'maxWidth': '380px', 'padding': '30px',
    'borderRadius': '10px', 'background': 'white',
    'boxShadow': '0 4px 10px rgba(0,0,0,0.1)',
    'boxSizing': 'border-box',
}

CSS = f"""
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 0; -webkit-text-size-adjust: 100%; overflow-x: hidden; }}
* {{ transition: background-color 0.2s, color 0.2s, border-color 0.2s; }}
#app-header {{ padding: 28px 24px; text-align: center; }}
@media (max-width: 500px) {{
  #app-header {{ padding: 18px 14px; }}
  .hdr-title {{ font-size: 1.4em !important; }}
  .hdr-sub   {{ font-size: 0.85em !important; }}
}}
#main-container {{ max-width: 1400px; margin: 0 auto; padding: 0 20px; }}
@media (max-width: 500px) {{ #main-container {{ padding: 0 12px; }} }}
#stats-cards {{
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px; margin-bottom: 18px;
}}
@media (max-width: 860px) {{ #stats-cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }} }}
#charts-row {{
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px; margin-bottom: 18px;
}}
#charts-row-bottom {{
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px; margin-bottom: 18px;
}}
@media (max-width: 760px) {{
  #charts-row {{ grid-template-columns: 1fr; }}
  #charts-row-bottom {{ grid-template-columns: 1fr; }}
}}
.chart-card {{
  background: var(--card-bg, white);
  border: 1px solid var(--card-border, #e5e7eb);
  border-radius: 14px; padding: 20px 20px 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.12); min-width: 0;
  transition: background 0.2s;
}}
.graph-wrap {{ width: 100%; height: {CHART_H}px; position: relative; }}
.graph-wrap .js-plotly-plot,
.graph-wrap .plot-container,
.graph-wrap .svg-container {{ width: 100% !important; height: 100% !important; }}
.input-card {{
  background: var(--card-bg, white);
  border: 1px solid var(--card-border, #e5e7eb);
  border-radius: 14px; padding: 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.12); margin-bottom: 18px;
  transition: background 0.2s;
}}
#manual-form-grid {{
  display: grid;
  grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) auto;
  gap: 14px; align-items: end; margin-bottom: 14px;
}}
#manual-form-grid > div {{ min-width: 0; }}
@media (max-width: 800px) {{ #manual-form-grid {{ grid-template-columns: minmax(0,1fr) minmax(0,1fr); }} }}
@media (max-width: 420px) {{ #manual-form-grid {{ grid-template-columns: 1fr; }} }}
@media (max-width: 680px) {{
  #add-data-btn   {{ width: 100%; }}
  #clear-data-btn {{ width: 100%; margin-top: 6px; }}
}}
.tab-row {{
  display: flex; gap: 10px; margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb; padding-bottom: 12px;
}}
.stat-card {{
  background: var(--card-bg, white);
  border: 1px solid var(--card-border, #e5e7eb);
  border-radius: 12px; padding: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12); min-width: 0;
  transition: background 0.2s;
}}
@media (max-width: 500px) {{
  .stat-card {{ padding: 14px; }}
  .stat-val  {{ font-size: 1.35em !important; }}
  .stat-icon {{ font-size: 1.8em !important; }}
}}
.dash-spreadsheet-container {{ overflow-x: auto !important; -webkit-overflow-scrolling: touch; }}
.dash-cell div              {{ white-space: nowrap !important; }}
.DateInput, .DateInput_input, .SingleDatePickerInput {{ width: 100% !important; }}
#upload-data {{ width: 100%; box-sizing: border-box; }}
.tbl-hdr {{
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 8px; margin-bottom: 12px;
}}

/* Filter bar */
#filter-bar {{
  background: var(--card-bg, white);
  border: 1px solid var(--card-border, #e5e7eb);
  border-radius: 14px; padding: 18px 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 18px;
  display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end;
}}
#filter-bar > div {{ flex: 1; min-width: 160px; }}
@media (max-width: 600px) {{ #filter-bar > div {{ min-width: 100%; }} }}

/* Target card */
#target-card {{
  background: var(--card-bg, white);
  border: 1px solid var(--card-border, #e5e7eb);
  border-radius: 14px; padding: 20px 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 18px;
}}

/* Progress bar */
.progress-outer {{
  height: 18px; border-radius: 9px;
  background: var(--card-border, #e5e7eb);
  overflow: hidden; margin: 10px 0 6px;
}}
.progress-inner {{
  height: 100%; border-radius: 9px;
  transition: width 0.6s ease;
}}

/* Trend badge */
.trend-up   {{ color: #10b981; font-size: 0.78em; font-weight: 700; margin-top: 3px; }}
.trend-down {{ color: #ef4444; font-size: 0.78em; font-weight: 700; margin-top: 3px; }}
.trend-flat {{ color: #9ca3af; font-size: 0.78em; font-weight: 700; margin-top: 3px; }}

/* ── Dashboard form inputs — fully themed ── */
#dashboard-wrapper input[type=text],
#dashboard-wrapper input[type=number] {{
  background: var(--input-bg, white) !important;
  color: var(--input-text, #1f2937) !important;
  border-color: var(--input-border, #e5e7eb) !important;
}}
#dashboard-wrapper .DateInput_input {{
  background: var(--input-bg, white) !important;
  color: var(--input-text, #1f2937) !important;
  border: none !important;
  font-size: 0.95em !important;
  padding: 8px 10px !important;
}}
#dashboard-wrapper .DateInput {{
  background: var(--input-bg, white) !important;
  width: 100% !important;
}}
#dashboard-wrapper .SingleDatePickerInput {{
  background: var(--input-bg, white) !important;
  border: 2px solid var(--input-border, #e5e7eb) !important;
  border-radius: 8px !important;
  width: 100% !important;
  display: flex !important;
}}
#dashboard-wrapper .DayPickerNavigation_button,
#dashboard-wrapper .DayPicker,
#dashboard-wrapper .CalendarMonth,
#dashboard-wrapper .CalendarMonth_caption,
#dashboard-wrapper .CalendarMonthGrid {{
  background: var(--card-bg, white) !important;
  color: var(--text, #1f2937) !important;
}}
#dashboard-wrapper .CalendarDay__default {{
  background: var(--card-bg, white) !important;
  color: var(--text, #1f2937) !important;
  border-color: var(--input-border, #e5e7eb) !important;
}}
#dashboard-wrapper .CalendarDay__selected {{
  background: #667eea !important;
  color: white !important;
}}
/* Upload drop zone */
#upload-data, #upload-data > div {{
  border-color: var(--input-border, #667eea) !important;
  background: var(--input-bg, #f9fafb) !important;
  color: var(--text, #1f2937) !important;
}}
/* Tab row border */
.tab-row {{
  border-bottom-color: var(--input-border, #e5e7eb) !important;
}}
/* DataTable filter row */
.dash-filter input {{
  background: var(--input-bg, white) !important;
  color: var(--input-text, #1f2937) !important;
  border: 1px solid var(--input-border, #e5e7eb) !important;
  border-radius: 4px !important;
  padding: 4px 8px !important;
}}
.dash-filter {{
  background: var(--input-bg, white) !important;
}}
/* Chart card text */
.chart-card h3, .chart-card p {{
  color: var(--text, #1f2937) !important;
}}

/* ── Kill iOS/Chrome autofill yellow background ── */
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {{
  -webkit-box-shadow: 0 0 0 40px white inset !important;
  -webkit-text-fill-color: #1f2937 !important;
  caret-color: #1f2937;
  transition: background-color 9999s ease-in-out 0s;
}}

/* ── Auth inputs ── */
input#login-email, input#login-password,
input#signup-email, input#signup-password {{
  display: block !important;
  width: 100% !important;
  padding: 16px 14px !important;
  margin: 0 0 16px 0 !important;
  border: 1.5px solid #d1d5db !important;
  border-radius: 8px !important;
  font-size: 16px !important;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
  color: #1f2937 !important;
  background: white !important;
  box-sizing: border-box !important;
  outline: none !important;
  -webkit-appearance: none;
  appearance: none;
  line-height: 1.5 !important;
  min-height: 52px !important;
}}
input#login-email:focus, input#login-password:focus,
input#signup-email:focus, input#signup-password:focus {{
  border-color: #667eea !important;
  box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
}}

/* ── Auth buttons ── */
#login-btn, #signup-btn {{
  display: block;
  width: 100% !important;
  padding: 16px !important;
  border: none !important;
  border-radius: 8px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  -webkit-appearance: none;
  appearance: none;
  min-height: 52px !important;
}}

/* Export modal overlay */
#export-modal {{
  display: none;
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 10000;
  align-items: center; justify-content: center;
}}
#export-modal.open {{ display: flex; }}
#export-modal-inner {{
  background: var(--card-bg, white);
  border-radius: 16px;
  padding: 28px 32px;
  width: 340px; max-width: 92vw;
  box-shadow: 0 8px 40px rgba(0,0,0,0.3);
  color: var(--text, #1f2937);
}}

/* ── Main section tabs ── */
.main-tabs {{
  display: flex; gap: 4px; margin: 12px 0 0;
}}
.main-tabs .tab-btn {{
  padding: 9px 22px; border: none; cursor: pointer;
  font-size: 0.88em; font-weight: 600; transition: all 0.18s;
  background: rgba(255,255,255,0.13); color: rgba(255,255,255,0.7);
  border-radius: 8px 8px 0 0;
}}
.main-tabs .tab-btn.active {{ background: white; color: #667eea; }}
.tab-panel {{ visibility: hidden; height: 0; overflow: hidden; }}
.tab-panel.active {{ visibility: visible; height: auto; overflow: visible; }}
/* Expense grids */
#exp-stats-cards {{
  display: grid; grid-template-columns: repeat(4, minmax(0,1fr));
  gap: 14px; margin-bottom: 18px;
}}
@media (max-width: 860px) {{ #exp-stats-cards {{ grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; }} }}
#exp-charts-row, #exp-charts-row-bottom {{
  display: grid; grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 16px; margin-bottom: 18px;
}}
@media (max-width: 760px) {{
  #exp-charts-row {{ grid-template-columns: 1fr; }}
  #exp-charts-row-bottom {{ grid-template-columns: 1fr; }}
}}
#exp-manual-form-grid {{
  display: grid;
  grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) auto;
  gap: 14px; align-items: end; margin-bottom: 14px;
}}
#exp-manual-form-grid > div {{ min-width: 0; }}
@media (max-width: 800px) {{ #exp-manual-form-grid {{ grid-template-columns: minmax(0,1fr) minmax(0,1fr); }} }}
@media (max-width: 420px) {{ #exp-manual-form-grid {{ grid-template-columns: 1fr; }} }}
#exp-filter-bar {{
  background: var(--card-bg,white); border: 1px solid var(--card-border,#e5e7eb);
  border-radius: 14px; padding: 18px 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 18px;
  display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end;
}}
#exp-filter-bar > div {{ flex: 1; min-width: 160px; }}
@media (max-width: 600px) {{ #exp-filter-bar > div {{ min-width: 100%; }} }}
/* ── AI Insights tab ── */
#ai-insights-panel {{
  max-width: 1400px; margin: 0 auto; padding: 20px 20px 40px;
}}
.ai-card {{
  background: var(--card-bg, white);
  border: 1px solid var(--card-border, #e5e7eb);
  border-radius: 14px; padding: 24px 28px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.10);
  margin-bottom: 18px;
}}
.ai-insights-text {{
  font-size: 0.97em; line-height: 1.8;
  color: var(--text, #1f2937);
  white-space: pre-wrap; word-break: break-word;
}}
.ai-section-header {{
  font-size: 1.15em; font-weight: 700;
  color: var(--text, #1f2937); margin: 0 0 10px;
}}
.ai-badge {{
  display: inline-block; padding: 3px 12px; border-radius: 20px;
  font-size: 0.78em; font-weight: 700; margin-right: 6px;
  vertical-align: middle;
}}
#exp-budget-card {{
  background: var(--card-bg,white); border: 1px solid var(--card-border,#e5e7eb);
  border-radius: 14px; padding: 20px 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 18px;
}}
</style>
"""

PWA_TAGS = (
    '<link rel="manifest" href="/assets/manifest.json">\n'
    '<meta name="theme-color" content="#667eea">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
    '<meta name="apple-mobile-web-app-title" content="Sales Dashboard">\n'
    '<link rel="apple-touch-icon" href="/assets/icons/icon-192.png">\n'
    '<script>if("serviceWorker" in navigator)'
    '{navigator.serviceWorker.register("/assets/service_worker.js")}'
    '</script>\n'
)

# html2canvas + jsPDF for client-side export
EXPORT_SCRIPT = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script>
window.exportDashboard = function(format) {
    var target = document.getElementById('dashboard-wrapper');
    if (!target) return;
    html2canvas(target, {
        scale: 2,
        useCORS: true,
        backgroundColor: null,
        logging: false,
    }).then(function(canvas) {
        var watermark = window._siteUrl || 'sales-dashboard.app';
        var ctx2 = canvas.getContext('2d');
        ctx2.save();
        ctx2.globalAlpha = 0.18;
        ctx2.fillStyle = '#667eea';
        ctx2.font = 'bold ' + Math.round(canvas.width / 28) + 'px Segoe UI, Arial, sans-serif';
        ctx2.textAlign = 'center';
        ctx2.textBaseline = 'middle';
        var angle = -Math.PI / 8;
        var step = 240;
        for (var y = -step; y < canvas.height + step; y += step) {
            for (var x = -step; x < canvas.width + step; x += step) {
                ctx2.save();
                ctx2.translate(x, y);
                ctx2.rotate(angle);
                ctx2.fillText(watermark, 0, 0);
                ctx2.restore();
            }
        }
        ctx2.restore();

        if (format === 'png') {
            var link = document.createElement('a');
            link.download = 'sales-dashboard.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        } else {
            var imgData = canvas.toDataURL('image/jpeg', 0.92);
            var { jsPDF } = window.jspdf;
            var orientation = canvas.width > canvas.height ? 'l' : 'p';
            var pdf = new jsPDF(orientation, 'px', [canvas.width / 2, canvas.height / 2]);
            pdf.addImage(imgData, 'JPEG', 0, 0, canvas.width / 2, canvas.height / 2);
            pdf.save('sales-dashboard.pdf');
        }

        // close modal
        var modal = document.getElementById('export-modal');
        if (modal) modal.classList.remove('open');
    });
};

window.openExportModal = function() {
    var modal = document.getElementById('export-modal');
    if (modal) modal.classList.add('open');
};
window.closeExportModal = function() {
    var modal = document.getElementById('export-modal');
    if (modal) modal.classList.remove('open');
};
</script>
"""

app.index_string = (
    '<!DOCTYPE html>\n<html>\n  <head>\n'
    '    {%metas%}\n    <title>Sales Dashboard</title>\n'
    '    {%favicon%}\n    {%css%}\n'
    + PWA_TAGS
    + CSS +
    '  </head>\n  <body>\n    {%app_entry%}\n'
    '    <footer>{%config%}{%scripts%}{%renderer%}</footer>\n'
    + EXPORT_SCRIPT +
    '  </body>\n</html>'
)

# ── Supabase helpers ───────────────────────────────────────────────────────────
def load_user_data(user_id: str) -> list:
    try:
        res = supabase.table("sales_records").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception as e:
        print(f"[load_user_data] {e}")
        return []

def insert_rows(user_id: str, df: pd.DataFrame):
    for _, row in df.iterrows():
        try:
            supabase.table("sales_records").insert({
                "user_id": user_id, "date": row["date"],
                "product": row["product"], "sales": row["sales"],
                "category": row.get("category", ""),
            }).execute()
        except Exception as e:
            print(f"[insert_rows] {e}")

def delete_user_data(user_id: str):
    try:
        supabase.table("sales_records").delete().eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[delete_user_data] {e}")

# ── Expense Supabase helpers ────────────────────────────────────────────────────────────────────────────
def load_expense_data(user_id: str) -> list:
    try:
        res = supabase.table("expense_records").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception as e:
        print(f"[load_expense_data] {e}")
        return []

def insert_expense_rows(user_id: str, df: pd.DataFrame):
    for _, row in df.iterrows():
        try:
            supabase.table("expense_records").insert({
                "user_id": user_id, "date": row["date"],
                "vendor": row["vendor"], "amount": row["amount"],
                "category": row.get("category", ""),
            }).execute()
        except Exception as e:
            print(f"[insert_expense_rows] {e}")

def delete_expense_data(user_id: str):
    try:
        supabase.table("expense_records").delete().eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[delete_expense_data] {e}")

def expense_records_to_df(records):
    if not records:
        return pd.DataFrame(columns=["date","vendor","amount","category"])
    df = pd.DataFrame(records)
    df = clean_col_names(df)
    for col in ["date","vendor","amount","category"]:
        if col not in df.columns: df[col] = None
    df = df[["date","vendor","amount","category"]].copy()
    df["amount"]   = pd.to_numeric(df["amount"], errors="coerce")
    df["date"]     = pd.to_datetime(df["date"], errors="coerce")
    df["category"] = df["category"].fillna("").astype(str)
    df = df.dropna(subset=["amount"])
    df = df[df["vendor"].notna() & (df["vendor"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)

def parse_expense_file(contents, filename):
    if not contents or not filename: return None
    try:
        _ct, b64 = contents.split(",", 1)
        decoded = base64.b64decode(b64)
        if filename.lower().endswith(".csv"):
            raw = pd.read_csv(io.StringIO(decoded.decode("utf-8", errors="ignore")), skip_blank_lines=True)
        elif filename.lower().endswith((".xlsx",".xls")):
            raw = pd.read_excel(io.BytesIO(decoded))
        else: return None
        raw = clean_col_names(raw)
        for col in ["date","vendor","amount","category"]:
            if col not in raw.columns: raw[col] = ""
        raw = raw[["date","vendor","amount","category"]].copy()
        raw = raw.dropna(how="all")
        raw["amount"] = pd.to_numeric(raw["amount"], errors="coerce")
        raw["date"]   = pd.to_datetime(raw["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return raw.dropna(subset=["amount"])
    except Exception as e:
        print(f"[parse_expense_file] {e}")
        return None


# ── Data helpers ───────────────────────────────────────────────────────────────
def clean_col_names(df):
    df.columns = df.columns.str.replace(r'[\r\n]', '', regex=True).str.strip().str.lower()
    return df

def records_to_df(records):
    if not records:
        return pd.DataFrame(columns=['date', 'product', 'sales', 'category'])
    df = pd.DataFrame(records)
    df = clean_col_names(df)
    for col in ['date', 'product', 'sales', 'category']:
        if col not in df.columns:
            df[col] = None
    df = df[['date', 'product', 'sales', 'category']].copy()
    df['sales']    = pd.to_numeric(df['sales'], errors='coerce')
    df['date']     = pd.to_datetime(df['date'], errors='coerce')
    df['category'] = df['category'].fillna('').astype(str)
    df = df.dropna(subset=['sales'])
    df = df[df['product'].notna() & (df['product'].astype(str).str.strip() != '')]
    return df.reset_index(drop=True)

def parse_uploaded_file(contents, filename):
    if not contents or not filename:
        return None
    try:
        _ct, b64 = contents.split(',', 1)
        decoded = base64.b64decode(b64)
        if filename.lower().endswith('.csv'):
            raw = pd.read_csv(io.StringIO(decoded.decode('utf-8', errors='ignore')), skip_blank_lines=True)
        elif filename.lower().endswith(('.xlsx', '.xls')):
            raw = pd.read_excel(io.BytesIO(decoded))
        else:
            return None
        raw = clean_col_names(raw)
        for col in ['date', 'product', 'sales', 'category']:
            if col not in raw.columns:
                raw[col] = ''
        raw = raw[['date', 'product', 'sales', 'category']].copy()
        raw = raw.dropna(how='all')
        raw['sales'] = pd.to_numeric(raw['sales'], errors='coerce')
        raw['date']  = pd.to_datetime(raw['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        return raw.dropna(subset=['sales'])
    except Exception as e:
        print(f'[parse_uploaded_file] {e}')
        return None

def fmt_cedi(v):
    return f'{CEDI}{v:,.0f}'

def trend_badge(current, previous):
    if previous is None or previous == 0:
        return html.Div('— No prior period', className='trend-flat')
    pct = (current - previous) / previous * 100
    if pct > 0:
        return html.Div(f'▲ {pct:.1f}% vs prev period', className='trend-up')
    elif pct < 0:
        return html.Div(f'▼ {abs(pct):.1f}% vs prev period', className='trend-down')
    return html.Div('→ No change vs prev period', className='trend-flat')

# ── Theme palettes ────────────────────────────────────────────────────────────
THEME = {
    'dark': {
        'bg':        '#0f172a',
        'plot_bg':   '#0f172a',
        'paper_bg':  '#0f172a',
        'grid':      'rgba(255,255,255,0.08)',
        'grid_dash': 'dash',
        'line':      '#667eea',
        'fill':      'rgba(102,126,234,0.18)',
        'tick':      '#94a3b8',
        'axis_line': 'rgba(255,255,255,0.1)',
        'anno':      '#64748b',
        'card_bg':   '#1e293b',
        'card_border':'#334155',
        'text':      '#f1f5f9',
        'sub_text':  '#94a3b8',
        'stat_text': '#f1f5f9',
        'stat_sub':  '#94a3b8',
        'page_bg':   '#0f172a',
        'input_bg':  '#1e293b',
        'input_border': '#475569',
        'input_text':'#f1f5f9',
        'toggle_label': '☀️ Light',
    },
    'light': {
        'bg':        'white',
        'plot_bg':   'white',
        'paper_bg':  'white',
        'grid':      '#e5e7eb',
        'grid_dash': 'solid',
        'line':      '#667eea',
        'fill':      'rgba(102,126,234,0.08)',
        'tick':      '#6b7280',
        'axis_line': '#e5e7eb',
        'anno':      '#9ca3af',
        'card_bg':   'white',
        'card_border':'#e5e7eb',
        'text':      '#1f2937',
        'sub_text':  '#6b7280',
        'stat_text': '#1f2937',
        'stat_sub':  '#6b7280',
        'page_bg':   '#f3f4f6',
        'input_bg':  'white',
        'input_border': '#d1d5db',
        'input_text':'#1f2937',
        'toggle_label': '🌙 Dark',
    },
}

def empty_fig(t='light'):
    th = THEME[t]
    fig = go.Figure()
    fig.add_annotation(
        text='No data — upload a file or enter records manually',
        showarrow=False, font=dict(size=13, color=th['anno']),
        xref='paper', yref='paper', x=0.5, y=0.5,
    )
    fig.update_layout(
        plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'],
        height=CHART_H, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig

def stat_card(title, value, icon, color, th=None, trend_el=None):
    if th is None:
        th = THEME['light']
    return html.Div(className='stat-card', style={
        'backgroundColor': th['card_bg'],
        'border': f'1px solid {th["card_border"]}',
        'borderLeft': f'4px solid {color}',
    }, children=[
        html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'},
                 children=[
                     html.Div([
                         html.Div(title, style={'color': th['stat_sub'], 'fontSize': '0.75em',
                                                'fontWeight': '500', 'textTransform': 'uppercase',
                                                'letterSpacing': '0.04em', 'marginBottom': '4px'}),
                         html.Div(value, className='stat-val',
                                  style={'color': th['stat_text'], 'fontSize': '1.6em',
                                         'fontWeight': '700', 'lineHeight': '1.1', 'wordBreak': 'break-all'}),
                         trend_el if trend_el else html.Div(),
                     ]),
                     html.Div(icon, className='stat-icon',
                              style={'fontSize': '2em', 'opacity': '0.25', 'flexShrink': '0'}),
                 ]),
    ])

# ── Page layouts ───────────────────────────────────────────────────────────────
def login_layout():
    return html.Div(style=AUTH_WRAP, children=[
        html.Div(style=AUTH_CARD, children=[
            html.H2("Login", style={"textAlign": "center", "marginBottom": "30px"}),
            dcc.Input(id="login-email", type="email", placeholder="Email address",
                      debounce=False, autoComplete="email", style=AUTH_INPUT),
            dcc.Input(id="login-password", type="password", placeholder="Password",
                      debounce=False, autoComplete="current-password", style=AUTH_INPUT),
            html.Button("Sign In", id="login-btn", n_clicks=0,
                        style={**BTN_BASE, "width": "100%", "padding": "14px",
                               "backgroundColor": "#2563eb", "color": "white",
                               "fontSize": "1em", "marginTop": "4px"}),
            html.Div(id="login-msg", style={"color": "red", "marginTop": "10px", "textAlign": "center"}),
            html.Div([
                html.Span("Don't have an account? "),
                dcc.Link("Create one", href="/signup"),
            ], style={"marginTop": "20px", "textAlign": "center"}),
        ]),
    ])

def signup_layout():
    return html.Div(style=AUTH_WRAP, children=[
        html.Div(style=AUTH_CARD, children=[
            html.H2("Create Account", style={"textAlign": "center", "marginBottom": "30px"}),
            dcc.Input(id="signup-email", type="email", placeholder="Email address",
                      debounce=False, autoComplete="email", style=AUTH_INPUT),
            dcc.Input(id="signup-password", type="password", placeholder="Password (min 6 chars)",
                      debounce=False, autoComplete="new-password", style=AUTH_INPUT),
            html.Button("Sign Up", id="signup-btn", n_clicks=0,
                        style={**BTN_BASE, "width": "100%", "padding": "12px",
                               "backgroundColor": "#16a34a", "color": "white"}),
            html.Div(id="signup-msg", style={"marginTop": "10px", "textAlign": "center"}),
            html.Div([
                html.Span("Already have an account? "),
                dcc.Link("Login", href="/login"),
            ], style={"marginTop": "20px", "textAlign": "center"}),
        ]),
    ])

def dashboard_layout():
    return html.Div(
        style={'minHeight': '100vh', 'margin': '0',
               'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"},
        children=[
            dcc.Store(id='stored-data', storage_type='session', data=[]),
            dcc.Store(id='exp-refresh', storage_type='memory', data=0),
            dcc.Interval(id='session-check', interval=60_000, n_intervals=0),
            html.Script(f'window._siteUrl = "{SITE_URL}";'),

            # ── Header ────────────────────────────────────────────────────────
            html.Div(id='app-header', style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                'color': 'white', 'boxShadow': '0 4px 14px rgba(102,126,234,0.3)',
                'marginBottom': '0', 'padding': '20px 24px',
            }, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between',
                                'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '10px'}, children=[
                    html.H1('\U0001f4ca Sales & Expense Dashboard', className='hdr-title',
                            style={'margin': '0', 'fontSize': '1.9em', 'fontWeight': '700'}),
                    html.Div(style={'display': 'flex', 'gap': '8px', 'alignItems': 'center'}, children=[
                        html.Button('\U0001f4e5 Export', id='export-btn', n_clicks=0,
                                    style={'background': 'rgba(255,255,255,0.15)', 'color': 'white',
                                           'border': '1.5px solid rgba(255,255,255,0.5)', 'borderRadius': '20px',
                                           'padding': '7px 14px', 'fontSize': '0.85em', 'fontWeight': '600',
                                           'cursor': 'pointer', 'whiteSpace': 'nowrap', 'flexShrink': '0'}),
                        html.Button(id='theme-toggle-btn', n_clicks=0,
                                    style={'background': 'rgba(255,255,255,0.15)', 'color': 'white',
                                           'border': '1.5px solid rgba(255,255,255,0.5)', 'borderRadius': '20px',
                                           'padding': '7px 14px', 'fontSize': '0.85em', 'fontWeight': '600',
                                           'cursor': 'pointer', 'whiteSpace': 'nowrap', 'flexShrink': '0'}),
                        html.Button('\U0001f6aa Sign Out', id='signout-btn', n_clicks=0,
                                    style={'background': 'rgba(255,255,255,0.2)', 'color': 'white',
                                           'border': '1.5px solid rgba(255,255,255,0.6)', 'borderRadius': '20px',
                                           'padding': '7px 16px', 'fontSize': '0.85em', 'fontWeight': '600',
                                           'cursor': 'pointer', 'whiteSpace': 'nowrap', 'flexShrink': '0'}),
                    ]),
                ]),
                html.Div(style={'marginTop': '8px'}, children=[
                    html.Span(id='user-greeting',
                              style={'fontSize': '0.95em', 'opacity': '0.95', 'fontWeight': '500'}),
                    html.P(f'Track sales & expenses in Ghana Cedis ({CEDI}) \u2014 data saved to Supabase',
                           className='hdr-sub',
                           style={'margin': '3px 0 0', 'fontSize': '0.85em', 'opacity': '0.75'}),
                ]),
                html.Div(className='main-tabs', children=[
                    html.Button('\U0001f4ca Sales', id='btn-sales', n_clicks=0,
                                className='tab-btn active'),
                    html.Button('\U0001f4b8 Expenses', id='btn-expenses', n_clicks=0,
                                className='tab-btn'),
                    html.Button('\U0001f916 AI Insights', id='btn-ai', n_clicks=0,
                                className='tab-btn'),
                ]),
            ]),
            html.Div(id='signout-toast', style={'display': 'none'}),

            # ── Export Modal ──────────────────────────────────────────────────
            html.Div(id='export-modal', children=[
                html.Div(id='export-modal-inner', children=[
                    html.H3('Export Dashboard', style={'margin': '0 0 18px', 'fontSize': '1.15em'}),
                    html.P(f'Watermark: {SITE_URL}',
                           style={'fontSize': '0.82em', 'color': '#9ca3af', 'margin': '0 0 20px'}),
                    html.Div(style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'}, children=[
                        html.Button('\U0001f5bc\ufe0f Export as PNG', id='export-png-btn', n_clicks=0,
                                    style={**BTN_BASE, 'padding': '11px 20px',
                                           'backgroundColor': COLORS['primary'], 'color': 'white', 'flex': '1'}),
                        html.Button('\U0001f4c4 Export as PDF', id='export-pdf-btn', n_clicks=0,
                                    style={**BTN_BASE, 'padding': '11px 20px',
                                           'backgroundColor': COLORS['secondary'], 'color': 'white', 'flex': '1'}),
                    ]),
                    html.Button('\u2715 Cancel', id='export-cancel-btn', n_clicks=0,
                                style={**BTN_BASE, 'width': '100%', 'marginTop': '12px',
                                       'padding': '9px', 'backgroundColor': '#e5e7eb', 'color': '#374151'}),
                ]),
            ]),

            # ── Main wrapper ──────────────────────────────────────────────────
            html.Div(id='dashboard-wrapper', children=[

                # ════════════════════════════════════════════════════════
                # SALES TAB
                # ════════════════════════════════════════════════════════
                html.Div(id='panel-sales', className='tab-panel active', children=[
                html.Div(id='main-container', children=[

                    html.Div(className='input-card', children=[
                        html.Div(className='tab-row', children=[
                            html.Button('\U0001f4e4 Upload File', id='tab-upload', n_clicks=1,
                                        style={**BTN_BASE, 'padding': '10px 20px',
                                               'backgroundColor': COLORS['primary'], 'color': 'white'}),
                            html.Button('\u270f\ufe0f Enter Manually', id='tab-manual', n_clicks=0,
                                        style={**BTN_BASE, 'padding': '10px 20px',
                                               'border': f'2px solid {COLORS["primary"]}',
                                               'backgroundColor': 'white', 'color': COLORS['primary']}),
                        ]),
                        html.Div(id='upload-section', children=[
                            html.H3('\U0001f4e4 Upload Your Data',
                                    style={'color': 'var(--text,#1f2937)', 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                            dcc.Upload(id='upload-data', multiple=False,
                                       style={'height': '130px', 'borderWidth': '2px', 'borderStyle': 'dashed',
                                              'borderRadius': '10px', 'borderColor': COLORS['primary'],
                                              'cursor': 'pointer', 'display': 'flex', 'alignItems': 'center',
                                              'justifyContent': 'center', 'textAlign': 'center'},
                                       children=html.Div([
                                           html.Div('\U0001f4c1', style={'fontSize': '2.2em', 'marginBottom': '6px'}),
                                           html.Div('Drag and Drop or Tap to Select',
                                                    style={'fontSize': '1em', 'fontWeight': '600'}),
                                           html.Div('CSV or Excel (.xlsx) \u2014 columns: date, product, sales, category (optional)',
                                                    style={'fontSize': '0.82em', 'color': '#6b7280', 'marginTop': '3px'}),
                                       ])),
                        ]),
                        html.Div(id='manual-section', style={'display': 'none'}, children=[
                            html.H3('\u270f\ufe0f Enter Sales Data',
                                    style={'color': 'var(--text,#1f2937)', 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                            html.Div(id='manual-form-grid', children=[
                                html.Div([html.Label('Date', style=LABEL_STYLE),
                                          dcc.DatePickerSingle(id='input-date',
                                                               date=datetime.today().strftime('%Y-%m-%d'),
                                                               display_format='YYYY-MM-DD',
                                                               style={'width': '100%'})]),
                                html.Div([html.Label('Product', style=LABEL_STYLE),
                                          dcc.Input(id='input-product', type='text',
                                                    placeholder='Product name', style=INPUT_STYLE)]),
                                html.Div([html.Label(f'Sales ({CEDI})', style=LABEL_STYLE),
                                          dcc.Input(id='input-sales', type='number', min=0,
                                                    placeholder='0.00', style=INPUT_STYLE)]),
                                html.Div([html.Label('Category (optional)', style=LABEL_STYLE),
                                          dcc.Input(id='input-category', type='text',
                                                    placeholder='e.g. Electronics', style=INPUT_STYLE)]),
                                html.Div([html.Label('\u00a0', style={**LABEL_STYLE, 'visibility': 'hidden'}),
                                          html.Button('\u2795 Add', id='add-data-btn', n_clicks=0,
                                                      style={**BTN_BASE, 'width': '100%', 'padding': '10px 18px',
                                                             'backgroundColor': COLORS['success'], 'color': 'white'})]),
                            ]),
                            html.Button('\U0001f5d1\ufe0f Clear All Data', id='clear-data-btn', n_clicks=0,
                                        style={**BTN_BASE, 'padding': '9px 18px', 'marginTop': '10px',
                                               'backgroundColor': COLORS['danger'], 'color': 'white'}),
                        ]),
                        html.Div(id='status-message',
                                 style={'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                                        'textAlign': 'center', 'fontSize': '0.9em', 'display': 'none'}),
                    ]),

                    html.Div(id='filter-bar', children=[
                        html.Div([html.Label('\U0001f4c5 Date Range', style={**LABEL_STYLE, 'marginBottom': '6px'}),
                                  dcc.DatePickerRange(id='filter-date-range', display_format='YYYY-MM-DD',
                                                     style={'width': '100%'})]),
                        html.Div([html.Label('\U0001f3f7\ufe0f Product(s)', style={**LABEL_STYLE, 'marginBottom': '6px'}),
                                  dcc.Dropdown(id='filter-products', multi=True,
                                               placeholder='All products\u2026', style={'fontSize': '0.93em'})]),
                        html.Div([html.Label('\U0001f4c2 Category', style={**LABEL_STYLE, 'marginBottom': '6px'}),
                                  dcc.Dropdown(id='filter-categories', multi=True,
                                               placeholder='All categories\u2026', style={'fontSize': '0.93em'})]),
                        html.Div([html.Label('\u00a0', style={**LABEL_STYLE, 'marginBottom': '6px', 'visibility': 'hidden'}),
                                  html.Button('\u21ba Reset Filters', id='reset-filters-btn', n_clicks=0,
                                              style={**BTN_BASE, 'width': '100%', 'padding': '10px 16px',
                                                     'backgroundColor': '#e5e7eb', 'color': '#374151'})],
                                 style={'maxWidth': '140px'}),
                    ]),

                    html.Div(id='target-card', children=[
                        html.Div(style={'display': 'flex', 'justifyContent': 'space-between',
                                        'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '12px'}, children=[
                            html.Div([
                                html.H3('\U0001f3af Monthly Sales Target',
                                        style={'margin': '0 0 4px', 'fontSize': '1.05em',
                                               'color': 'var(--text,#1f2937)'}),
                                html.Div(id='target-progress-text',
                                         style={'fontSize': '0.85em', 'color': 'var(--sub-text,#6b7280)'}),
                            ]),
                            html.Div(style={'display': 'flex', 'gap': '10px', 'alignItems': 'center'}, children=[
                                html.Label(f'Target ({CEDI})',
                                           style={**LABEL_STYLE, 'margin': '0', 'whiteSpace': 'nowrap'}),
                                dcc.Input(id='target-input', type='number', min=0,
                                          placeholder='e.g. 50000',
                                          style={**INPUT_STYLE, 'width': '160px', 'margin': '0'}),
                            ]),
                        ]),
                        html.Div(className='progress-outer', children=[
                            html.Div(id='target-progress-bar', className='progress-inner',
                                     style={'width': '0%', 'backgroundColor': COLORS['success']}),
                        ]),
                    ]),

                    html.Div(id='stats-cards'),

                    html.Div(id='charts-row', children=[
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f4c8 Sales Trend',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Daily totals \u2014 all products',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='sales-line-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f3c6 Top Products',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P(f'Total {CEDI} by product (top 10)',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='product-bar-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                    ]),

                    html.Div(id='charts-row-bottom', children=[
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f967 Revenue Share',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Product share of total revenue',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='donut-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f4ca Month-over-Month',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Current vs previous month per product (top 8)',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='mom-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                    ]),

                    html.Div(style={'marginBottom': '18px'}, children=[
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f321\ufe0f Sales Heatmap',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Sales by day-of-week and week number',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='heatmap-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                    ]),

                    html.Div(id='data-table-container', style={'marginBottom': '24px'}),

                    html.Div(style={'textAlign': 'center', 'padding': '10px 0 24px',
                                    'color': '#9ca3af', 'fontSize': '0.82em'},
                             children=[html.Ul(
                                 html.Li(html.A('Designed by William Thompson',
                                                href='https://yooku98.github.io/Portfolio-Website/index.html',
                                                style={'color': COLORS['primary']})),
                                 style={'listStyle': 'none', 'padding': 0, 'margin': 0},
                             )]),
                ]),
                ]),  # end panel-sales

                # ════════════════════════════════════════════════════════
                # EXPENSES TAB
                # ════════════════════════════════════════════════════════
                html.Div(id='panel-expenses', className='tab-panel', children=[
                html.Div(style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '0 20px'}, children=[

                    html.Div(className='input-card', children=[
                        html.Div(className='tab-row', children=[
                            html.Button('\U0001f4e4 Upload File', id='exp-tab-upload', n_clicks=1,
                                        style={**BTN_BASE, 'padding': '10px 20px',
                                               'backgroundColor': COLORS['danger'], 'color': 'white'}),
                            html.Button('\u270f\ufe0f Enter Manually', id='exp-tab-manual', n_clicks=0,
                                        style={**BTN_BASE, 'padding': '10px 20px',
                                               'border': f'2px solid {COLORS["danger"]}',
                                               'backgroundColor': 'white', 'color': COLORS['danger']}),
                        ]),
                        html.Div(id='exp-upload-section', children=[
                            html.H3('\U0001f4e4 Upload Expense Data',
                                    style={'color': 'var(--text,#1f2937)', 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                            dcc.Upload(id='exp-upload-data', multiple=False,
                                       style={'height': '130px', 'borderWidth': '2px', 'borderStyle': 'dashed',
                                              'borderRadius': '10px', 'borderColor': COLORS['danger'],
                                              'cursor': 'pointer', 'display': 'flex', 'alignItems': 'center',
                                              'justifyContent': 'center', 'textAlign': 'center'},
                                       children=html.Div([
                                           html.Div('\U0001f4c1', style={'fontSize': '2.2em', 'marginBottom': '6px'}),
                                           html.Div('Drag and Drop or Tap to Select',
                                                    style={'fontSize': '1em', 'fontWeight': '600'}),
                                           html.Div('CSV or Excel \u2014 columns: date, vendor, amount, category (optional)',
                                                    style={'fontSize': '0.82em', 'color': '#6b7280', 'marginTop': '3px'}),
                                       ])),
                        ]),
                        html.Div(id='exp-manual-section', style={'display': 'none'}, children=[
                            html.H3('\u270f\ufe0f Enter Expense',
                                    style={'color': 'var(--text,#1f2937)', 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                            html.Div(id='exp-manual-form-grid', children=[
                                html.Div([html.Label('Date', style=LABEL_STYLE),
                                          dcc.DatePickerSingle(id='exp-input-date',
                                                               date=datetime.today().strftime('%Y-%m-%d'),
                                                               display_format='YYYY-MM-DD',
                                                               style={'width': '100%'})]),
                                html.Div([html.Label('Vendor / Description', style=LABEL_STYLE),
                                          dcc.Input(id='exp-input-vendor', type='text',
                                                    placeholder='e.g. Electricity bill', style=INPUT_STYLE)]),
                                html.Div([html.Label(f'Amount ({CEDI})', style=LABEL_STYLE),
                                          dcc.Input(id='exp-input-amount', type='number', min=0,
                                                    placeholder='0.00', style=INPUT_STYLE)]),
                                html.Div([html.Label('Category (optional)', style=LABEL_STYLE),
                                          dcc.Input(id='exp-input-category', type='text',
                                                    placeholder='e.g. Utilities', style=INPUT_STYLE)]),
                                html.Div([html.Label('\u00a0', style={**LABEL_STYLE, 'visibility': 'hidden'}),
                                          html.Button('\u2795 Add', id='exp-add-btn', n_clicks=0,
                                                      style={**BTN_BASE, 'width': '100%', 'padding': '10px 18px',
                                                             'backgroundColor': COLORS['danger'], 'color': 'white'})]),
                            ]),
                            html.Button('\U0001f5d1\ufe0f Clear All Expenses', id='exp-clear-btn', n_clicks=0,
                                        style={**BTN_BASE, 'padding': '9px 18px', 'marginTop': '10px',
                                               'backgroundColor': '#6b7280', 'color': 'white'}),
                        ]),
                        html.Div(id='exp-status-message',
                                 style={'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                                        'textAlign': 'center', 'fontSize': '0.9em', 'display': 'none'}),
                    ]),

                    html.Div(id='exp-filter-bar', children=[
                        html.Div([html.Label('\U0001f4c5 Date Range', style={**LABEL_STYLE, 'marginBottom': '6px'}),
                                  dcc.DatePickerRange(id='exp-filter-date-range', display_format='YYYY-MM-DD',
                                                     style={'width': '100%'})]),
                        html.Div([html.Label('\U0001f3f7\ufe0f Vendor(s)', style={**LABEL_STYLE, 'marginBottom': '6px'}),
                                  dcc.Dropdown(id='exp-filter-vendors', multi=True,
                                               placeholder='All vendors\u2026', style={'fontSize': '0.93em'})]),
                        html.Div([html.Label('\U0001f4c2 Category', style={**LABEL_STYLE, 'marginBottom': '6px'}),
                                  dcc.Dropdown(id='exp-filter-categories', multi=True,
                                               placeholder='All categories\u2026', style={'fontSize': '0.93em'})]),
                        html.Div([html.Label('\u00a0', style={**LABEL_STYLE, 'marginBottom': '6px', 'visibility': 'hidden'}),
                                  html.Button('\u21ba Reset', id='exp-reset-filters-btn', n_clicks=0,
                                              style={**BTN_BASE, 'width': '100%', 'padding': '10px 16px',
                                                     'backgroundColor': '#e5e7eb', 'color': '#374151'})],
                                 style={'maxWidth': '140px'}),
                    ]),

                    html.Div(id='exp-budget-card', children=[
                        html.Div(style={'display': 'flex', 'justifyContent': 'space-between',
                                        'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '12px'}, children=[
                            html.Div([
                                html.H3('\U0001f3af Monthly Expense Budget',
                                        style={'margin': '0 0 4px', 'fontSize': '1.05em',
                                               'color': 'var(--text,#1f2937)'}),
                                html.Div(id='exp-budget-progress-text',
                                         style={'fontSize': '0.85em', 'color': 'var(--sub-text,#6b7280)'}),
                            ]),
                            html.Div(style={'display': 'flex', 'gap': '10px', 'alignItems': 'center'}, children=[
                                html.Label(f'Budget ({CEDI})',
                                           style={**LABEL_STYLE, 'margin': '0', 'whiteSpace': 'nowrap'}),
                                dcc.Input(id='exp-budget-input', type='number', min=0,
                                          placeholder='e.g. 20000',
                                          style={**INPUT_STYLE, 'width': '160px', 'margin': '0'}),
                            ]),
                        ]),
                        html.Div(className='progress-outer', children=[
                            html.Div(id='exp-budget-progress-bar', className='progress-inner',
                                     style={'width': '0%', 'backgroundColor': COLORS['danger']}),
                        ]),
                    ]),

                    html.Div(id='exp-stats-cards'),

                    html.Div(id='exp-charts-row', children=[
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f4c9 Expense Trend',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Daily totals \u2014 all vendors',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='exp-line-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True, 'autosizable': True}),
                            ]),
                        ]),
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f3c6 Top Vendors',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P(f'Total {CEDI} by vendor (top 10)',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='exp-bar-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                    ]),

                    html.Div(id='exp-charts-row-bottom', children=[
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f967 Expense Share',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Vendor share of total expenses',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='exp-donut-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f4ca Month-over-Month',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Current vs previous month per vendor (top 8)',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='exp-mom-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                    ]),

                    html.Div(style={'marginBottom': '18px'}, children=[
                        html.Div(className='chart-card', children=[
                            html.H3('\U0001f321\ufe0f Expense Heatmap',
                                    style={'color': 'var(--text,#1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                            html.P('Expenses by day-of-week and week number',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                            html.Div(className='graph-wrap', children=[
                                dcc.Graph(id='exp-heatmap-chart', style={'height': '100%'},
                                          config={'displayModeBar': False, 'responsive': True}),
                            ]),
                        ]),
                    ]),

                    html.Div(id='exp-table-container', style={'marginBottom': '24px'}),

                ]),
                ]),  # end panel-expenses

                # ════════════════════════════════════════════════════════
                # AI INSIGHTS TAB
                # ════════════════════════════════════════════════════════
                html.Div(id='panel-ai', className='tab-panel', children=[
                html.Div(id='ai-insights-panel', children=[

                    # Header card
                    html.Div(className='ai-card', style={'borderTop': '4px solid #667eea'}, children=[
                        html.Div(style={'display':'flex','justifyContent':'space-between',
                                        'alignItems':'center','flexWrap':'wrap','gap':'12px'}, children=[
                            html.Div([
                                html.H2('\U0001f916 AI Business Insights',
                                        style={'margin':'0 0 4px','fontSize':'1.25em',
                                               'color':'var(--text,#1f2937)'}),
                                html.P('Claude analyses your sales and expense data and generates actionable insights.',
                                       style={'margin':'0','fontSize':'0.85em',
                                              'color':'var(--sub-text,#6b7280)'}),
                            ]),
                            html.Button('\u27f3 Generate Insights', id='ai-generate-btn', n_clicks=0,
                                        style={**BTN_BASE, 'padding':'10px 22px',
                                               'backgroundColor':'#667eea','color':'white',
                                               'fontSize':'0.9em'}),
                        ]),
                        html.Div(id='ai-error-msg', style={'display':'none'}),
                    ]),

                    # Loading indicator
                    html.Div(id='ai-loading', style={'display':'none','textAlign':'center',
                                                      'padding':'40px 20px'}, children=[
                        html.Div('\U0001f4ad Analysing your data\u2026',
                                 style={'fontSize':'1.1em','color':'var(--sub-text,#6b7280)',
                                        'marginBottom':'12px','fontWeight':'600'}),
                        html.Div(style={'display':'flex','justifyContent':'center','gap':'6px'}, children=[
                            html.Div(style={'width':'10px','height':'10px','borderRadius':'50%',
                                           'backgroundColor':'#667eea',
                                           'animation':'pulse 1.2s ease-in-out infinite'}),
                            html.Div(style={'width':'10px','height':'10px','borderRadius':'50%',
                                           'backgroundColor':'#764ba2',
                                           'animation':'pulse 1.2s ease-in-out 0.4s infinite'}),
                            html.Div(style={'width':'10px','height':'10px','borderRadius':'50%',
                                           'backgroundColor':'#667eea',
                                           'animation':'pulse 1.2s ease-in-out 0.8s infinite'}),
                        ]),
                    ]),

                    # Results area
                    html.Div(id='ai-results', style={'display':'none'}, children=[

                        # Summary card
                        html.Div(className='ai-card', children=[
                            html.H3('\U0001f4ca Executive Summary', className='ai-section-header'),
                            html.Div(id='ai-summary', className='ai-insights-text'),
                        ]),

                        # Two-col: strengths + risks
                        html.Div(style={'display':'grid',
                                        'gridTemplateColumns':'repeat(auto-fit,minmax(300px,1fr))',
                                        'gap':'16px','marginBottom':'18px'}, children=[
                            html.Div(className='ai-card',
                                     style={'borderLeft':'4px solid #10b981'}, children=[
                                html.H3('\u2705 Strengths & Opportunities', className='ai-section-header'),
                                html.Div(id='ai-strengths', className='ai-insights-text'),
                            ]),
                            html.Div(className='ai-card',
                                     style={'borderLeft':'4px solid #ef4444'}, children=[
                                html.H3('\u26a0\ufe0f Risks & Watch Points', className='ai-section-header'),
                                html.Div(id='ai-risks', className='ai-insights-text'),
                            ]),
                        ]),

                        # Recommendations card
                        html.Div(className='ai-card',
                                 style={'borderLeft':'4px solid #f59e0b'}, children=[
                            html.H3('\U0001f3af Actionable Recommendations', className='ai-section-header'),
                            html.Div(id='ai-recommendations', className='ai-insights-text'),
                        ]),

                        # Forecast card
                        html.Div(className='ai-card',
                                 style={'borderLeft':'4px solid #764ba2'}, children=[
                            html.H3('\U0001f52e Outlook & Forecast', className='ai-section-header'),
                            html.Div(id='ai-forecast', className='ai-insights-text'),
                        ]),

                        html.P(id='ai-generated-at',
                               style={'textAlign':'right','fontSize':'0.75em',
                                      'color':'var(--sub-text,#9ca3af)','marginTop':'8px'}),
                    ]),

                    # Empty state
                    html.Div(id='ai-empty', style={'textAlign':'center','padding':'60px 20px'}, children=[
                        html.Div('\U0001f4ca', style={'fontSize':'3em','marginBottom':'12px'}),
                        html.P('Upload or enter your sales data, then click Generate Insights.',
                               style={'color':'var(--sub-text,#6b7280)','fontSize':'1em'}),
                    ]),

                ]),
                ]),  # end panel-ai

            ]),  # end dashboard-wrapper
        ],
    )


# ── Root layout ────────────────────────────────────────────────────────────────
app.layout = html.Div(id='app-root', children=[
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='session-store', storage_type='session'),
    dcc.Store(id='theme-store', storage_type='local', data='dark'),
    html.Div(id='page-content'),
])

# ── Router ─────────────────────────────────────────────────────────────────────
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    State('session-store', 'data'),
)
def render_page(pathname, session):
    authenticated = bool(session and session.get('user_id'))
    if pathname == '/signup':
        return signup_layout()
    if pathname == '/dashboard':
        if not authenticated:
            return dcc.Location(id='auth-redirect', href='/login', refresh=True)
        return dashboard_layout()
    return login_layout()

# ── Login ──────────────────────────────────────────────────────────────────────
@app.callback(
    Output('login-msg',     'children'),
    Output('session-store', 'data'),
    Output('url',           'pathname'),
    Input('login-btn',      'n_clicks'),
    Input('login-email',    'value'),
    Input('login-password', 'value'),
    State('login-email',    'value'),
    State('login-password', 'value'),
    prevent_initial_call=True,
)
def login_user(btn_clicks, _email_input, _password_input, email, password):
    if ctx.triggered_id in ('login-email', 'login-password'):
        return "", no_update, no_update
    if not email or not password:
        return "Please fill in all fields.", no_update, no_update
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session_data = {"token": res.session.access_token, "user_id": res.user.id, "email": res.user.email}
        return "", session_data, "/dashboard"
    except Exception as e:
        print(f"[login_user] {e}")
        return "Invalid email or password.", no_update, no_update

# ── Signup ─────────────────────────────────────────────────────────────────────
@app.callback(
    Output('signup-msg',   'children'),
    Output('signup-msg',   'style'),
    Input('signup-btn',    'n_clicks'),
    State('signup-email',  'value'),
    State('signup-password', 'value'),
    prevent_initial_call=True,
)
def signup_user(n_clicks, email, password):
    err = {"color": "red",   "marginTop": "10px", "textAlign": "center"}
    ok  = {"color": "green", "marginTop": "10px", "textAlign": "center"}
    if not email or not password:
        return "Please fill in all fields.", err
    if len(password) < 6:
        return "Password must be at least 6 characters.", err
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        return "Account created! Check your email to verify.", ok
    except Exception as e:
        print(f"[signup_user] {e}")
        return "Signup failed. Email may already be in use.", err

# ── Greeting ───────────────────────────────────────────────────────────────────
@app.callback(
    Output('user-greeting', 'children'),
    Input('session-store',  'data'),
)
def update_greeting(session):
    if not session or not session.get('user_id'):
        return ''
    email = session.get('email', '')
    if email:
        import re
        local = email.split('@')[0]
        parts = re.split(r'[._\-]+', local)
        firstname = parts[0].capitalize() if len(parts) > 1 else local.capitalize()
        return f'👋 Hello, {firstname}!'
    return '👋 Hello!'

# ── Sign-out ───────────────────────────────────────────────────────────────────
@app.callback(
    Output('session-store',   'data',     allow_duplicate=True),
    Output('url',             'pathname', allow_duplicate=True),
    Output('signout-toast',   'children'),
    Output('signout-toast',   'style'),
    Input('signout-btn',      'n_clicks'),
    State('session-store',    'data'),
    prevent_initial_call=True,
)
def sign_out(n_clicks, session):
    if not n_clicks:
        raise PreventUpdate
    import re
    email = (session or {}).get('email', '')
    if email:
        local = email.split('@')[0]
        parts = re.split(r'[._\-]+', local)
        firstname = parts[0].capitalize() if len(parts) > 1 else local.capitalize()
        goodbye = f'👋 Goodbye, {firstname}! You have been signed out.'
    else:
        goodbye = '👋 You have been signed out.'
    try:
        supabase.auth.sign_out()
    except Exception as e:
        print(f'[sign_out] {e}')
    toast_style = {
        'display': 'block', 'position': 'fixed', 'bottom': '30px', 'left': '50%',
        'transform': 'translateX(-50%)', 'backgroundColor': COLORS['dark'],
        'color': 'white', 'padding': '14px 24px', 'borderRadius': '30px',
        'fontSize': '0.95em', 'fontWeight': '500', 'zIndex': '9999',
        'boxShadow': '0 4px 20px rgba(0,0,0,0.3)', 'whiteSpace': 'nowrap',
    }
    return None, '/login', goodbye, toast_style

# ── Session check ──────────────────────────────────────────────────────────────
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('session-check',  'n_intervals'),
    State('session-store',  'data'),
    State('url',            'pathname'),
    prevent_initial_call=True,
)
def check_session(n, session, pathname):
    if pathname != '/dashboard':
        raise PreventUpdate
    if not session or not session.get('token'):
        return '/login'
    try:
        supabase.auth.get_user(session['token'])
        raise PreventUpdate
    except Exception:
        return '/login'

# ── Theme toggle ───────────────────────────────────────────────────────────────
@app.callback(
    Output('theme-store',       'data'),
    Output('theme-toggle-btn',  'children'),
    Input('theme-toggle-btn',   'n_clicks'),
    State('theme-store',        'data'),
    prevent_initial_call=True,
)
def toggle_theme(n, current):
    new_theme = 'light' if current == 'dark' else 'dark'
    return new_theme, THEME[new_theme]['toggle_label']

@app.callback(
    Output('theme-toggle-btn', 'children', allow_duplicate=True),
    Input('theme-store',       'data'),
    prevent_initial_call='initial_duplicate',
)
def sync_toggle_label(theme):
    return THEME[theme or 'dark']['toggle_label']

@app.callback(
    Output('app-root', 'style'),
    Input('theme-store', 'data'),
)
def apply_theme_to_root(theme):
    t = theme or 'dark'
    return {'backgroundColor': THEME[t]['page_bg'], 'minHeight': '100vh'}

# ── Tab switcher ───────────────────────────────────────────────────────────────
@app.callback(
    Output('upload-section', 'style'),
    Output('manual-section', 'style'),
    Output('tab-upload',     'style'),
    Output('tab-manual',     'style'),
    Input('tab-upload',      'n_clicks'),
    Input('tab-manual',      'n_clicks'),
)
def switch_tabs(_u, _m):
    upload_active = ctx.triggered_id != 'tab-manual'
    active   = {**BTN_BASE, 'padding': '10px 20px',
                'backgroundColor': COLORS['primary'], 'color': 'white'}
    inactive = {**BTN_BASE, 'padding': '10px 20px',
                'border': f'2px solid {COLORS["primary"]}',
                'backgroundColor': 'transparent', 'color': COLORS['primary']}
    if upload_active:
        return {'display': 'block'}, {'display': 'none'}, active, inactive
    return {'display': 'none'}, {'display': 'block'}, inactive, active

# ── Export modal (open/close via clientside) ───────────────────────────────────
app.clientside_callback(
    "function(n) { if(n) window.openExportModal(); return window.dash_clientside.no_update; }",
    Output('export-btn', 'n_clicks'),
    Input('export-btn', 'n_clicks'),
    prevent_initial_call=True,
)
app.clientside_callback(
    "function(n) { if(n) window.closeExportModal(); return window.dash_clientside.no_update; }",
    Output('export-cancel-btn', 'n_clicks'),
    Input('export-cancel-btn', 'n_clicks'),
    prevent_initial_call=True,
)
app.clientside_callback(
    "function(n) { if(n) { window.exportDashboard('png'); } return window.dash_clientside.no_update; }",
    Output('export-png-btn', 'n_clicks'),
    Input('export-png-btn', 'n_clicks'),
    prevent_initial_call=True,
)
app.clientside_callback(
    "function(n) { if(n) { window.exportDashboard('pdf'); } return window.dash_clientside.no_update; }",
    Output('export-pdf-btn', 'n_clicks'),
    Input('export-pdf-btn', 'n_clicks'),
    prevent_initial_call=True,
)

# ── Data management ────────────────────────────────────────────────────────────
@app.callback(
    Output('stored-data',    'data'),
    Output('status-message', 'children'),
    Output('status-message', 'style'),
    Output('input-product',  'value'),
    Output('input-sales',    'value'),
    Output('input-category', 'value'),
    Input('add-data-btn',    'n_clicks'),
    Input('clear-data-btn',  'n_clicks'),
    Input('upload-data',     'contents'),
    State('input-date',      'date'),
    State('input-product',   'value'),
    State('input-sales',     'value'),
    State('input-category',  'value'),
    State('upload-data',     'filename'),
    State('session-store',   'data'),
    prevent_initial_call=True,
)
def manage_data(add_clicks, clear_clicks, upload_contents,
                date, product, sales, category, filename, session):
    user_id = (session or {}).get('user_id')
    trigger = ctx.triggered_id

    if not user_id:
        raise PreventUpdate

    def ok(msg):
        return ({'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                 'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
                 'backgroundColor': '#d1fae5', 'color': '#065f46',
                 'border': f'1px solid {COLORS["success"]}'}, msg)

    def err(msg):
        return ({'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                 'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
                 'backgroundColor': '#fee2e2', 'color': '#991b1b',
                 'border': f'1px solid {COLORS["danger"]}'}, msg)

    if trigger == 'upload-data':
        if not upload_contents or not filename:
            raise PreventUpdate
        uploaded = parse_uploaded_file(upload_contents, filename)
        if uploaded is not None and not uploaded.empty:
            insert_rows(user_id, uploaded)
            refreshed = load_user_data(user_id)
            sty, msg = ok(f'\u2705 Loaded {filename} \u2014 {len(uploaded)} rows saved to Supabase')
            return refreshed, msg, sty, no_update, no_update, no_update
        sty, msg = err(f'\u274c Could not parse "{filename}". Use CSV/Excel with date, product, sales columns.')
        return no_update, msg, sty, no_update, no_update, no_update

    if trigger == 'add-data-btn':
        if not date or not product or not str(product).strip() or sales is None:
            sty, msg = err('\u274c Fill in all fields (Date, Product, Sales).')
            return no_update, msg, sty, product, sales, category
        v = float(sales)
        if v < 0:
            sty, msg = err('\u274c Sales cannot be negative.')
            return no_update, msg, sty, product, sales, category
        new_row = pd.DataFrame({
            'date':     [pd.to_datetime(date).strftime('%Y-%m-%d')],
            'product':  [str(product).strip()],
            'sales':    [v],
            'category': [str(category).strip() if category else ''],
        })
        insert_rows(user_id, new_row)
        refreshed = load_user_data(user_id)
        sty, msg = ok(f'\u2705 Added {str(product).strip()} \u2014 {fmt_cedi(v)} on {date}')
        return refreshed, msg, sty, '', None, ''

    if trigger == 'clear-data-btn':
        delete_user_data(user_id)
        sty, msg = ok('\u2705 All data cleared from Supabase.')
        return [], msg, sty, '', None, ''

    raise PreventUpdate

# ── Filter bar population ──────────────────────────────────────────────────────
@app.callback(
    Output('filter-products',   'options'),
    Output('filter-categories', 'options'),
    Output('filter-date-range', 'min_date_allowed'),
    Output('filter-date-range', 'max_date_allowed'),
    Output('filter-date-range', 'start_date'),
    Output('filter-date-range', 'end_date'),
    Input('stored-data',  'data'),
    Input('session-store','data'),
    Input('reset-filters-btn', 'n_clicks'),
)
def populate_filters(stored_data, session, _reset):
    user_id = (session or {}).get('user_id')
    records = load_user_data(user_id) if user_id else (stored_data or [])
    data = records_to_df(records)

    if data.empty:
        return [], [], None, None, None, None

    products   = sorted(data['product'].dropna().unique().tolist())
    categories = sorted([c for c in data['category'].unique() if c])
    min_d = data['date'].min().strftime('%Y-%m-%d')
    max_d = data['date'].max().strftime('%Y-%m-%d')
    return (
        [{'label': p, 'value': p} for p in products],
        [{'label': c, 'value': c} for c in categories],
        min_d, max_d, min_d, max_d,
    )

# ── Main dashboard update ──────────────────────────────────────────────────────
@app.callback(
    Output('sales-line-chart',     'figure'),
    Output('product-bar-chart',    'figure'),
    Output('donut-chart',          'figure'),
    Output('mom-chart',            'figure'),
    Output('heatmap-chart',        'figure'),
    Output('stats-cards',          'children'),
    Output('data-table-container', 'children'),
    Output('dashboard-wrapper',    'style'),
    Output('target-progress-bar',  'style'),
    Output('target-progress-text', 'children'),
    Input('stored-data',           'data'),
    Input('session-store',         'data'),
    Input('theme-store',           'data'),
    Input('filter-date-range',     'start_date'),
    Input('filter-date-range',     'end_date'),
    Input('filter-products',       'value'),
    Input('filter-categories',     'value'),
    Input('target-input',          'value'),
)
def update_dashboard(stored_data, session, theme,
                     start_date, end_date, sel_products, sel_categories,
                     target_val):
    t = theme or 'dark'
    th = THEME[t]
    user_id = (session or {}).get('user_id')
    records = load_user_data(user_id) if user_id else (stored_data or [])
    full_data = records_to_df(records)

    # ── Apply filters ─────────────────────────────────────────────────────────
    data = full_data.copy()
    if not data.empty:
        if start_date:
            data = data[data['date'] >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data['date'] <= pd.to_datetime(end_date)]
        if sel_products:
            data = data[data['product'].isin(sel_products)]
        if sel_categories:
            data = data[data['category'].isin(sel_categories)]

    # ── Trend: compare current vs previous equal-length period ────────────────
    def prev_period_total(df, col='sales'):
        if df.empty or df['date'].dropna().empty:
            return None, None
        mn, mx = df['date'].min(), df['date'].max()
        span = (mx - mn).days or 1
        prev_end   = mn - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span)
        prev = full_data[(full_data['date'] >= prev_start) & (full_data['date'] <= prev_end)]
        return df[col].sum(), prev[col].sum() if not prev.empty else None

    cur_total, prev_total = prev_period_total(data)

    # ── Stat cards ────────────────────────────────────────────────────────────
    if data.empty:
        stats = [html.Div('\U0001f4ed No data yet — upload a file or enter records manually.',
                          style={'color': th['sub_text'], 'padding': '18px', 'textAlign': 'center',
                                 'gridColumn': '1 / -1', 'background': th['card_bg'],
                                 'borderRadius': '12px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'})]
    else:
        s = data['sales'].dropna()

        # per-product count trend (products in current vs prev period)
        prev_recs = full_data.copy()
        if not data.empty and not data['date'].dropna().empty:
            mn, mx = data['date'].min(), data['date'].max()
            span = (mx - mn).days or 1
            prev_end   = mn - timedelta(days=1)
            prev_start = prev_end - timedelta(days=span)
            prev_recs = full_data[(full_data['date'] >= prev_start) & (full_data['date'] <= prev_end)]

        stats = [
            stat_card('Total Sales',  fmt_cedi(s.sum()),             '\U0001f4b0', COLORS['success'],  th,
                      trend_badge(s.sum(), prev_total)),
            stat_card('Average Sale', fmt_cedi(s.mean()),             '\U0001f4ca', COLORS['primary'],  th,
                      trend_badge(s.mean(), prev_recs['sales'].mean() if not prev_recs.empty else None)),
            stat_card('Products',     str(data['product'].nunique()), '\U0001f3f7\ufe0f', COLORS['warning'],  th,
                      trend_badge(data['product'].nunique(),
                                  prev_recs['product'].nunique() if not prev_recs.empty else None)),
            stat_card('Records',      str(len(data)),                 '\U0001f4dd', COLORS['secondary'], th,
                      trend_badge(len(data), len(prev_recs) if not prev_recs.empty else None)),
        ]

    # ── Target progress ───────────────────────────────────────────────────────
    target = float(target_val) if target_val else 0
    actual = data['sales'].sum() if not data.empty else 0
    if target > 0:
        pct = min(actual / target * 100, 100)
        bar_color = COLORS['success'] if pct >= 100 else (COLORS['warning'] if pct >= 60 else COLORS['danger'])
        prog_text = f'{fmt_cedi(actual)} of {fmt_cedi(target)} ({pct:.1f}%)'
    else:
        pct = 0
        bar_color = COLORS['primary']
        prog_text = 'Set a target above to track your progress'

    progress_bar_style = {
        'width': f'{pct:.1f}%',
        'backgroundColor': bar_color,
        'height': '100%',
        'borderRadius': '9px',
        'transition': 'width 0.6s ease',
    }

    # ── Line chart ────────────────────────────────────────────────────────────
    if data.empty:
        line_fig = empty_fig(t)
    else:
        clean = data.dropna(subset=['date', 'sales']).copy()
        clean['_d'] = clean['date'].dt.normalize()
        daily = (clean.groupby('_d', as_index=False)['sales']
                      .sum().rename(columns={'_d': 'date'}).sort_values('date'))
        line_fig = empty_fig(t) if daily.empty else _line_chart(daily, t)

    # ── Bar chart ─────────────────────────────────────────────────────────────
    bar_fig = empty_fig(t) if data.empty else _bar_chart(data, t)

    # ── Donut chart ───────────────────────────────────────────────────────────
    donut_fig = empty_fig(t) if data.empty else _donut_chart(data, t)

    # ── Month-over-month ──────────────────────────────────────────────────────
    mom_fig = empty_fig(t) if data.empty else _mom_chart(data, t)

    # ── Heatmap ───────────────────────────────────────────────────────────────
    heat_fig = empty_fig(t) if data.empty else _heatmap_chart(data, t)

    # ── Table ─────────────────────────────────────────────────────────────────
    if data.empty:
        tbl = html.Div('\U0001f4ed No data to display.',
                       style={'color': '#6b7280', 'textAlign': 'center', 'padding': '20px'})
    else:
        disp = data.sort_values('date', ascending=False).copy()
        disp['date']  = disp['date'].dt.strftime('%Y-%m-%d')
        disp['sales'] = disp['sales'].round(2)
        col_map = {'date': 'Date', 'product': 'Product', 'sales': f'Sales ({CEDI})', 'category': 'Category'}
        tbl = html.Div(style={'backgroundColor': th['card_bg'], 'borderRadius': '14px',
                              'padding': '22px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.07)',
                              'border': f'1px solid {th["card_border"]}'}, children=[
            html.Div(className='tbl-hdr', children=[
                html.H3('\U0001f4cb All Sales Data',
                        style={'color': th['text'], 'margin': '0', 'fontSize': '1.1em'}),
                html.Span(f'{len(data)} records',
                          style={'backgroundColor': COLORS['primary'], 'color': 'white',
                                 'padding': '3px 12px', 'borderRadius': '20px',
                                 'fontSize': '0.8em', 'fontWeight': '600'}),
            ]),
            dash_table.DataTable(
                id='data-table', data=disp.to_dict('records'),
                columns=[{'name': col_map.get(c, c.title()), 'id': c, 'editable': True}
                         for c in disp.columns],
                editable=True,
                page_size=10, sort_action='native', filter_action='native',
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'padding': '9px 12px', 'whiteSpace': 'nowrap',
                            'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                            'fontSize': '0.88em', 'minWidth': '80px'},
                style_header={'backgroundColor': COLORS['primary'], 'color': 'white',
                              'fontWeight': '600', 'border': 'none', 'fontSize': '0.85em'},
                style_data={'backgroundColor': th['card_bg'], 'color': th['text'],
                            'border': f'1px solid {th["card_border"]}'},
                style_filter={
                    'backgroundColor': th['input_bg'],
                    'color': th['input_text'],
                    'border': f'1px solid {th["input_border"]}',
                    'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                    'fontSize': '0.85em',
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': th['plot_bg']},
                    {'if': {'column_id': 'sales'}, 'textAlign': 'right', 'fontWeight': '600'},
                ],
                tooltip_delay=0,
                tooltip_duration=None,
            ),
        ])

    wrapper_style = {
        'backgroundColor': th['page_bg'],
        'minHeight': '100vh',
        '--card-bg':     th['card_bg'],
        '--card-border': th['card_border'],
        '--text':        th['text'],
        '--sub-text':    th['sub_text'],
        '--page-bg':     th['page_bg'],
        '--input-bg':    th['input_bg'],
        '--input-text':  th['input_text'],
        '--input-border':th['input_border'],
    }
    return (line_fig, bar_fig, donut_fig, mom_fig, heat_fig,
            stats, tbl, wrapper_style, progress_bar_style, prog_text)


# ── Chart builders ─────────────────────────────────────────────────────────────
def _line_chart(daily, t='light'):
    th = THEME[t]
    fig = px.line(daily, x='date', y='sales', labels={'date': '', 'sales': ''})
    fig.update_traces(
        line=dict(color=th['line'], width=2.5, shape='spline'),
        mode='lines+markers',
        marker=dict(size=7, color=th['plot_bg'],
                    line=dict(width=2.5, color=th['line'])),
        fill='tozeroy', fillcolor=th['fill'],
        hovertemplate=f'%{{x|%b %d}}<br>{CEDI}%{{y:,.0f}}<extra></extra>',
    )
    fig.update_layout(
        plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
        margin=dict(l=60, r=16, t=12, b=44), hovermode='x unified',
        hoverlabel=dict(bgcolor=th['card_bg'], font_color=th['text'],
                        bordercolor=th['grid']),
        xaxis=dict(
            showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
            showline=False, zeroline=False,
            tickformat='%b %d', tickfont=dict(size=10, color=th['tick']),
            fixedrange=True, title=None,
        ),
        yaxis=dict(
            showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
            zeroline=False, showline=False,
            tickprefix=CEDI, tickfont=dict(size=10, color=th['tick']),
            fixedrange=True, title=None,
        ),
    )
    return fig


def _bar_chart(data, t='light'):
    th = THEME[t]
    ps = (data.dropna(subset=['product', 'sales'])
              .groupby('product', as_index=False)['sales']
              .sum().sort_values('sales', ascending=False).head(10))
    if ps.empty:
        return empty_fig(t)
    fig = px.bar(ps, x='product', y='sales', labels={'product': '', 'sales': ''},
                 color='sales',
                 color_continuous_scale=[[0, COLORS['primary']], [1, COLORS['secondary']]])
    fig.update_traces(
        hovertemplate=f'%{{x}}<br>{CEDI}%{{y:,.0f}}<extra></extra>',
        marker_line_width=0,
    )
    fig.update_layout(
        plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
        margin=dict(l=60, r=16, t=12, b=56), coloraxis_showscale=False,
        hoverlabel=dict(bgcolor=th['card_bg'], font_color=th['text'],
                        bordercolor=th['grid']),
        xaxis=dict(
            showgrid=False, showline=False, zeroline=False,
            categoryorder='total descending',
            tickfont=dict(size=10, color=th['tick']),
            fixedrange=True, tickangle=-30, title=None,
        ),
        yaxis=dict(
            showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
            zeroline=False, showline=False,
            tickprefix=CEDI, tickfont=dict(size=10, color=th['tick']),
            fixedrange=True, title=None,
        ),
    )
    return fig


def _donut_chart(data, t='light'):
    th = THEME[t]
    ps = (data.dropna(subset=['product', 'sales'])
              .groupby('product', as_index=False)['sales']
              .sum().sort_values('sales', ascending=False).head(10))
    if ps.empty:
        return empty_fig(t)
    fig = go.Figure(go.Pie(
        labels=ps['product'], values=ps['sales'],
        hole=0.52,
        textinfo='percent',
        hovertemplate=f'%{{label}}<br>{CEDI}%{{value:,.0f}}<br>%{{percent}}<extra></extra>',
        marker=dict(
            colors=['#667eea','#10b981','#f59e0b','#ef4444','#06b6d4','#f97316','#8b5cf6','#ec4899','#14b8a6','#84cc16'][:len(ps)],
            line=dict(color=th['card_bg'], width=2),
        ),
        textfont=dict(size=11, color=th['text']),
    ))
    fig.update_layout(
        paper_bgcolor=th['paper_bg'],
        height=CHART_H,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(font=dict(color=th['text'], size=10),
                    bgcolor='rgba(0,0,0,0)', orientation='v',
                    yanchor='middle', y=0.5, xanchor='left', x=1.02),
        showlegend=True,
        hoverlabel=dict(bgcolor=th['card_bg'], font_color=th['text']),
        annotations=[dict(
            text=f'<b>{fmt_cedi(ps["sales"].sum())}</b>',
            x=0.5, y=0.5, font=dict(size=13, color=th['text']),
            showarrow=False, xanchor='center',
        )],
    )
    return fig


def _mom_chart(data, t='light'):
    th = THEME[t]
    if data.empty or data['date'].dropna().empty:
        return empty_fig(t)
    now = data['date'].max()
    cur_start  = now.replace(day=1)
    prev_end   = cur_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)

    cur  = data[data['date'] >= cur_start].groupby('product')['sales'].sum()
    prev = data[(data['date'] >= prev_start) & (data['date'] <= prev_end)].groupby('product')['sales'].sum()

    products = list(set(cur.index.tolist()) | set(prev.index.tolist()))
    if not products:
        return empty_fig(t)

    df_mom = pd.DataFrame({
        'product': products,
        'This Month': [cur.get(p, 0) for p in products],
        'Last Month': [prev.get(p, 0) for p in products],
    })
    df_mom['_total'] = df_mom['This Month'] + df_mom['Last Month']
    df_mom = df_mom.nlargest(8, '_total').sort_values('This Month', ascending=False)

    fig = go.Figure()
    fig.add_bar(name='Last Month', x=df_mom['product'], y=df_mom['Last Month'],
                marker_color='rgba(102,126,234,0.45)',
                hovertemplate=f'Last Month<br>%{{x}}<br>{CEDI}%{{y:,.0f}}<extra></extra>')
    fig.add_bar(name='This Month', x=df_mom['product'], y=df_mom['This Month'],
                marker_color=COLORS['primary'],
                hovertemplate=f'This Month<br>%{{x}}<br>{CEDI}%{{y:,.0f}}<extra></extra>')
    fig.update_layout(
        barmode='group',
        plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
        margin=dict(l=60, r=16, t=12, b=56),
        legend=dict(font=dict(color=th['text'], size=10), bgcolor='rgba(0,0,0,0)',
                    orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hoverlabel=dict(bgcolor=th['card_bg'], font_color=th['text']),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color=th['tick']),
                   tickangle=-25, title=None, fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
                   zeroline=False, tickprefix=CEDI, tickfont=dict(size=10, color=th['tick']),
                   fixedrange=True, title=None),
    )
    return fig


def _heatmap_chart(data, t='light'):
    th = THEME[t]
    if data.empty or data['date'].dropna().empty:
        return empty_fig(t)
    df = data.dropna(subset=['date', 'sales']).copy()
    df['dow']  = df['date'].dt.dayofweek          # 0=Mon
    df['week'] = df['date'].dt.isocalendar().week.astype(int)

    pivot = df.groupby(['week', 'dow'])['sales'].sum().reset_index()
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    weeks = sorted(pivot['week'].unique())
    z = []
    for dow_i in range(7):
        row = []
        for w in weeks:
            val = pivot[(pivot['week'] == w) & (pivot['dow'] == dow_i)]['sales']
            row.append(float(val.values[0]) if not val.empty else 0)
        z.append(row)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f'W{w}' for w in weeks],
        y=dow_names,
        colorscale=[[0, th['plot_bg']], [0.001, 'rgba(102,126,234,0.15)'],
                    [0.5, COLORS['primary']], [1, COLORS['secondary']]],
        hovertemplate='Week %{x} · %{y}<br>' + f'{CEDI}' + '%{z:,.0f}<extra></extra>',
        showscale=True,
        colorbar=dict(tickfont=dict(color=th['tick']), thickness=12, len=0.8),
    ))
    fig.update_layout(
        plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
        margin=dict(l=50, r=60, t=12, b=44),
        xaxis=dict(tickfont=dict(size=9, color=th['tick']), title=None, fixedrange=True),
        yaxis=dict(tickfont=dict(size=10, color=th['tick']), title=None, fixedrange=True),
        hoverlabel=dict(bgcolor=th['card_bg'], font_color=th['text']),
    )
    return fig


# ── Main tab switcher moved to bottom (3-tab version) ──────────────────────────

# ── Expense upload/manual tab switcher ────────────────────────────────────────
@app.callback(
    Output('exp-upload-section', 'style'),
    Output('exp-manual-section', 'style'),
    Output('exp-tab-upload',     'style'),
    Output('exp-tab-manual',     'style'),
    Input('exp-tab-upload',      'n_clicks'),
    Input('exp-tab-manual',      'n_clicks'),
)
def switch_exp_tabs(_u, _m):
    upload_active = ctx.triggered_id != 'exp-tab-manual'
    active   = {**BTN_BASE, 'padding': '10px 20px',
                'backgroundColor': COLORS['danger'], 'color': 'white'}
    inactive = {**BTN_BASE, 'padding': '10px 20px',
                'border': f'2px solid {COLORS["danger"]}',
                'backgroundColor': 'transparent', 'color': COLORS['danger']}
    if upload_active:
        return {'display': 'block'}, {'display': 'none'}, active, inactive
    return {'display': 'none'}, {'display': 'block'}, inactive, active


# ── Expense data management ────────────────────────────────────────────────────
@app.callback(
    Output('exp-status-message', 'children'),
    Output('exp-status-message', 'style'),
    Output('exp-input-vendor',   'value'),
    Output('exp-input-amount',   'value'),
    Output('exp-input-category', 'value'),
    Output('exp-refresh',        'data'),
    Input('exp-add-btn',         'n_clicks'),
    Input('exp-clear-btn',       'n_clicks'),
    Input('exp-upload-data',     'contents'),
    State('exp-input-date',      'date'),
    State('exp-input-vendor',    'value'),
    State('exp-input-amount',    'value'),
    State('exp-input-category',  'value'),
    State('exp-upload-data',     'filename'),
    State('session-store',       'data'),
    State('exp-refresh',         'data'),
    prevent_initial_call=True,
)
def manage_expense_data(add_clicks, clear_clicks, upload_contents,
                        date, vendor, amount, category, filename, session, refresh_count):
    user_id = (session or {}).get('user_id')
    trigger = ctx.triggered_id
    if not user_id:
        raise PreventUpdate

    def ok(msg):
        return ({'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                 'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
                 'backgroundColor': '#d1fae5', 'color': '#065f46',
                 'border': f'1px solid {COLORS["success"]}'}, msg)

    def err(msg):
        return ({'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                 'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
                 'backgroundColor': '#fee2e2', 'color': '#991b1b',
                 'border': f'1px solid {COLORS["danger"]}'}, msg)

    rc = (refresh_count or 0) + 1

    if trigger == 'exp-upload-data':
        if not upload_contents or not filename:
            raise PreventUpdate
        uploaded = parse_expense_file(upload_contents, filename)
        if uploaded is not None and not uploaded.empty:
            insert_expense_rows(user_id, uploaded)
            sty, msg = ok(f'\u2705 Loaded {filename} \u2014 {len(uploaded)} expense rows saved')
            return msg, sty, no_update, no_update, no_update, rc
        sty, msg = err(f'\u274c Could not parse "{filename}". Use CSV/Excel with date, vendor, amount columns.')
        return msg, sty, no_update, no_update, no_update, rc

    if trigger == 'exp-add-btn':
        if not date or not vendor or not str(vendor).strip() or amount is None:
            sty, msg = err('\u274c Fill in all fields (Date, Vendor, Amount).')
            return msg, sty, vendor, amount, category, rc
        v = float(amount)
        if v < 0:
            sty, msg = err('\u274c Amount cannot be negative.')
            return msg, sty, vendor, amount, category, rc
        new_row = pd.DataFrame({
            'date':     [pd.to_datetime(date).strftime('%Y-%m-%d')],
            'vendor':   [str(vendor).strip()],
            'amount':   [v],
            'category': [str(category).strip() if category else ''],
        })
        insert_expense_rows(user_id, new_row)
        sty, msg = ok(f'\u2705 Added {str(vendor).strip()} \u2014 {fmt_cedi(v)} on {date}')
        return msg, sty, '', None, '', rc

    if trigger == 'exp-clear-btn':
        delete_expense_data(user_id)
        sty, msg = ok('\u2705 All expense data cleared.')
        return msg, sty, '', None, '', rc

    raise PreventUpdate


# ── Expense filter population ──────────────────────────────────────────────────
@app.callback(
    Output('exp-filter-vendors',    'options'),
    Output('exp-filter-categories', 'options'),
    Output('exp-filter-date-range', 'min_date_allowed'),
    Output('exp-filter-date-range', 'max_date_allowed'),
    Output('exp-filter-date-range', 'start_date'),
    Output('exp-filter-date-range', 'end_date'),
    Input('session-store',          'data'),
    Input('exp-reset-filters-btn',  'n_clicks'),
    Input('exp-refresh',            'data'),
)
def populate_expense_filters(session, _reset, _refresh):
    user_id = (session or {}).get('user_id')
    if not user_id:
        return [], [], None, None, None, None
    records = load_expense_data(user_id)
    data    = expense_records_to_df(records)
    if data.empty:
        return [], [], None, None, None, None
    vendors    = sorted(data['vendor'].dropna().unique().tolist())
    categories = sorted([c for c in data['category'].unique() if c])
    min_d = data['date'].min().strftime('%Y-%m-%d')
    max_d = data['date'].max().strftime('%Y-%m-%d')
    return (
        [{'label': v, 'value': v} for v in vendors],
        [{'label': c, 'value': c} for c in categories],
        min_d, max_d, min_d, max_d,
    )


# ── Expense dashboard update ───────────────────────────────────────────────────
@app.callback(
    Output('exp-line-chart',           'figure'),
    Output('exp-bar-chart',            'figure'),
    Output('exp-donut-chart',          'figure'),
    Output('exp-mom-chart',            'figure'),
    Output('exp-heatmap-chart',        'figure'),
    Output('exp-stats-cards',          'children'),
    Output('exp-table-container',      'children'),
    Output('exp-budget-progress-bar',  'style'),
    Output('exp-budget-progress-text', 'children'),
    Input('session-store',             'data'),
    Input('theme-store',               'data'),
    Input('exp-filter-date-range',     'start_date'),
    Input('exp-filter-date-range',     'end_date'),
    Input('exp-filter-vendors',        'value'),
    Input('exp-filter-categories',     'value'),
    Input('exp-budget-input',          'value'),
    Input('exp-refresh',               'data'),
    Input('btn-expenses',              'n_clicks'),
)
def update_expense_dashboard(session, theme, start_date, end_date,
                              sel_vendors, sel_categories, budget_val, _refresh, _tab):
    t  = theme or 'dark'
    th = THEME[t]
    user_id = (session or {}).get('user_id')
    no_prog = {'width': '0%', 'backgroundColor': COLORS['danger'],
               'height': '100%', 'borderRadius': '9px'}

    if not user_id:
        ef = empty_fig(t)
        return ef, ef, ef, ef, ef, [], html.Div(), no_prog, 'Log in to view expenses'

    records   = load_expense_data(user_id)
    full_data = expense_records_to_df(records)
    data      = full_data.copy()

    if not data.empty:
        if start_date:
            data = data[data['date'] >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data['date'] <= pd.to_datetime(end_date)]
        if sel_vendors:
            data = data[data['vendor'].isin(sel_vendors)]
        if sel_categories:
            data = data[data['category'].isin(sel_categories)]

    # Prev period trend
    prev_tot = None
    if not data.empty and not data['date'].dropna().empty:
        mn, mx   = data['date'].min(), data['date'].max()
        span     = (mx - mn).days or 1
        pe       = mn - timedelta(days=1)
        ps       = pe - timedelta(days=span)
        prev_df  = full_data[(full_data['date'] >= ps) & (full_data['date'] <= pe)]
        prev_tot = prev_df['amount'].sum() if not prev_df.empty else None
    else:
        prev_df = pd.DataFrame()

    # Stat cards
    if data.empty:
        stats = [html.Div('\U0001f4ed No expense data yet \u2014 upload a file or enter manually.',
                          style={'color': th['sub_text'], 'padding': '18px', 'textAlign': 'center',
                                 'gridColumn': '1 / -1', 'background': th['card_bg'],
                                 'borderRadius': '12px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'})]
    else:
        s = data['amount'].dropna()
        stats = [
            stat_card('Total Expenses',  fmt_cedi(s.sum()),             '\U0001f4b8', COLORS['danger'],   th,
                      trend_badge(s.sum(), prev_tot)),
            stat_card('Average Expense', fmt_cedi(s.mean()),            '\U0001f4ca', COLORS['warning'],  th,
                      trend_badge(s.mean(), prev_df['amount'].mean() if not prev_df.empty else None)),
            stat_card('Vendors',         str(data['vendor'].nunique()), '\U0001f3eb', COLORS['primary'],  th,
                      trend_badge(data['vendor'].nunique(),
                                  prev_df['vendor'].nunique() if not prev_df.empty else None)),
            stat_card('Records',         str(len(data)),                '\U0001f4dd', COLORS['secondary'],th,
                      trend_badge(len(data), len(prev_df) if not prev_df.empty else None)),
        ]

    # Budget progress
    budget = float(budget_val) if budget_val else 0
    actual = data['amount'].sum() if not data.empty else 0
    if budget > 0:
        pct       = min(actual / budget * 100, 100)
        bar_color = COLORS['danger'] if pct >= 90 else (COLORS['warning'] if pct >= 60 else COLORS['success'])
        prog_text = f'{fmt_cedi(actual)} of {fmt_cedi(budget)} ({pct:.1f}%)'
    else:
        pct, bar_color, prog_text = 0, COLORS['danger'], 'Set a budget above to track your spending'

    prog_style = {'width': f'{pct:.1f}%', 'backgroundColor': bar_color,
                  'height': '100%', 'borderRadius': '9px', 'transition': 'width 0.6s ease'}

    EXP_C = ['#ef4444','#f97316','#f59e0b','#10b981','#06b6d4',
              '#8b5cf6','#ec4899','#667eea','#14b8a6','#84cc16']

    if data.empty:
        line_fig = bar_fig = donut_fig = mom_fig = heat_fig = empty_fig(t)
    else:
        # Line
        clean = data.dropna(subset=['date','amount']).copy()
        clean['_d'] = clean['date'].dt.normalize()
        daily = (clean.groupby('_d', as_index=False)['amount']
                      .sum().rename(columns={'_d':'date','amount':'sales'}).sort_values('date'))
        if daily.empty:
            line_fig = empty_fig(t)
        else:
            line_fig = px.line(daily, x='date', y='sales', labels={'date':'','sales':''})
            line_fig.update_traces(
                line=dict(color=COLORS['danger'], width=2.5, shape='spline'),
                mode='lines+markers',
                marker=dict(size=7, color=th['plot_bg'], line=dict(width=2.5, color=COLORS['danger'])),
                fill='tozeroy', fillcolor='rgba(239,68,68,0.10)',
                hovertemplate=f'%{{x|%b %d}}<br>{CEDI}%{{y:,.0f}}<extra></extra>',
            )
            line_fig.update_layout(
                plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
                margin=dict(l=60,r=16,t=12,b=44), hovermode='x unified',
                xaxis=dict(showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
                           showline=False, zeroline=False, tickformat='%b %d',
                           tickfont=dict(size=10, color=th['tick']), fixedrange=True, title=None),
                yaxis=dict(showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
                           zeroline=False, showline=False, tickprefix=CEDI,
                           tickfont=dict(size=10, color=th['tick']), fixedrange=True, title=None),
            )

        # Bar
        ps = (data.dropna(subset=['vendor','amount'])
                  .groupby('vendor', as_index=False)['amount']
                  .sum().sort_values('amount', ascending=False).head(10))
        if ps.empty:
            bar_fig = empty_fig(t)
        else:
            bar_fig = px.bar(ps, x='vendor', y='amount', labels={'vendor':'','amount':''})
            bar_fig.update_traces(
                marker_color=[EXP_C[i % len(EXP_C)] for i in range(len(ps))],
                hovertemplate=f'%{{x}}<br>{CEDI}%{{y:,.0f}}<extra></extra>',
                marker_line_width=0,
            )
            bar_fig.update_layout(
                plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
                margin=dict(l=60,r=16,t=12,b=56),
                xaxis=dict(showgrid=False, showline=False, zeroline=False,
                           categoryorder='total descending',
                           tickfont=dict(size=10, color=th['tick']),
                           fixedrange=True, tickangle=-30, title=None),
                yaxis=dict(showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
                           zeroline=False, showline=False, tickprefix=CEDI,
                           tickfont=dict(size=10, color=th['tick']), fixedrange=True, title=None),
            )

        # Donut
        if ps.empty:
            donut_fig = empty_fig(t)
        else:
            donut_fig = go.Figure(go.Pie(
                labels=ps['vendor'], values=ps['amount'], hole=0.52, textinfo='percent',
                hovertemplate=f'%{{label}}<br>{CEDI}%{{value:,.0f}}<br>%{{percent}}<extra></extra>',
                marker=dict(colors=EXP_C[:len(ps)], line=dict(color=th['card_bg'], width=2)),
                textfont=dict(size=11, color=th['text']),
            ))
            donut_fig.update_layout(
                paper_bgcolor=th['paper_bg'], height=CHART_H, margin=dict(l=10,r=10,t=10,b=10),
                legend=dict(font=dict(color=th['text'], size=10), bgcolor='rgba(0,0,0,0)',
                            orientation='v', yanchor='middle', y=0.5, xanchor='left', x=1.02),
                showlegend=True,
                annotations=[dict(text=f'<b>{fmt_cedi(ps["amount"].sum())}</b>',
                                  x=0.5, y=0.5, font=dict(size=13, color=th['text']),
                                  showarrow=False, xanchor='center')],
            )

        # MoM
        now        = data['date'].max()
        cur_start  = now.replace(day=1)
        prev_end   = cur_start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        cur_m  = data[data['date'] >= cur_start].groupby('vendor')['amount'].sum()
        prev_m = data[(data['date'] >= prev_start) & (data['date'] <= prev_end)].groupby('vendor')['amount'].sum()
        vendors = list(set(cur_m.index.tolist()) | set(prev_m.index.tolist()))
        if not vendors:
            mom_fig = empty_fig(t)
        else:
            df_mom = pd.DataFrame({
                'vendor': vendors,
                'This Month': [cur_m.get(v,0) for v in vendors],
                'Last Month': [prev_m.get(v,0) for v in vendors],
            })
            df_mom['_t'] = df_mom['This Month'] + df_mom['Last Month']
            df_mom = df_mom.nlargest(8,'_t').sort_values('This Month', ascending=False)
            mom_fig = go.Figure()
            mom_fig.add_bar(name='Last Month', x=df_mom['vendor'], y=df_mom['Last Month'],
                            marker_color='#94a3b8',
                            hovertemplate=f'Last Month<br>%{{x}}<br>{CEDI}%{{y:,.0f}}<extra></extra>')
            mom_fig.add_bar(name='This Month', x=df_mom['vendor'], y=df_mom['This Month'],
                            marker_color=COLORS['danger'],
                            hovertemplate=f'This Month<br>%{{x}}<br>{CEDI}%{{y:,.0f}}<extra></extra>')
            mom_fig.update_layout(
                barmode='group', plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
                margin=dict(l=60,r=16,t=12,b=56),
                legend=dict(font=dict(color=th['text'], size=10), bgcolor='rgba(0,0,0,0)',
                            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                xaxis=dict(showgrid=False, tickfont=dict(size=10, color=th['tick']),
                           tickangle=-25, title=None, fixedrange=True),
                yaxis=dict(showgrid=True, gridcolor=th['grid'], griddash=th['grid_dash'],
                           zeroline=False, tickprefix=CEDI,
                           tickfont=dict(size=10, color=th['tick']), fixedrange=True, title=None),
            )

        # Heatmap
        df_h = data.dropna(subset=['date','amount']).copy()
        df_h['dow']  = df_h['date'].dt.dayofweek
        df_h['week'] = df_h['date'].dt.isocalendar().week.astype(int)
        pivot = df_h.groupby(['week','dow'])['amount'].sum().reset_index()
        dow_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        weeks = sorted(pivot['week'].unique())
        z = [[float(pivot[(pivot['week']==w)&(pivot['dow']==d)]['amount'].values[0])
              if not pivot[(pivot['week']==w)&(pivot['dow']==d)].empty else 0
              for w in weeks] for d in range(7)]
        heat_fig = go.Figure(go.Heatmap(
            z=z, x=[f'W{w}' for w in weeks], y=dow_names,
            colorscale=[[0,th['plot_bg']],[0.001,'rgba(239,68,68,0.15)'],[0.5,'#ef4444'],[1,'#7f1d1d']],
            hovertemplate='Week %{x} \u00b7 %{y}<br>' + f'{CEDI}' + '%{z:,.0f}<extra></extra>',
            showscale=True, colorbar=dict(tickfont=dict(color=th['tick']), thickness=12, len=0.8),
        ))
        heat_fig.update_layout(
            plot_bgcolor=th['plot_bg'], paper_bgcolor=th['paper_bg'], height=CHART_H,
            margin=dict(l=50,r=60,t=12,b=44),
            xaxis=dict(tickfont=dict(size=9, color=th['tick']), title=None, fixedrange=True),
            yaxis=dict(tickfont=dict(size=10, color=th['tick']), title=None, fixedrange=True),
        )

    # Table
    if data.empty:
        tbl = html.Div('\U0001f4ed No expense data to display.',
                       style={'color': '#6b7280', 'textAlign': 'center', 'padding': '20px'})
    else:
        disp = data.sort_values('date', ascending=False).copy()
        disp['date']   = disp['date'].dt.strftime('%Y-%m-%d')
        disp['amount'] = disp['amount'].round(2)
        col_map = {'date':'Date','vendor':'Vendor','amount':f'Amount ({CEDI})','category':'Category'}
        tbl = html.Div(style={'backgroundColor': th['card_bg'], 'borderRadius': '14px',
                              'padding': '22px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.07)',
                              'border': f'1px solid {th["card_border"]}'}, children=[
            html.Div(className='tbl-hdr', children=[
                html.H3('\U0001f4cb All Expense Records',
                        style={'color': th['text'], 'margin': '0', 'fontSize': '1.1em'}),
                html.Span(f'{len(data)} records',
                          style={'backgroundColor': COLORS['danger'], 'color': 'white',
                                 'padding': '3px 12px', 'borderRadius': '20px',
                                 'fontSize': '0.8em', 'fontWeight': '600'}),
            ]),
            dash_table.DataTable(
                id='exp-data-table', data=disp.to_dict('records'),
                columns=[{'name': col_map.get(c, c.title()), 'id': c, 'editable': True}
                         for c in disp.columns],
                editable=True, page_size=10, sort_action='native', filter_action='native',
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'padding': '9px 12px', 'whiteSpace': 'nowrap',
                            'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                            'fontSize': '0.88em', 'minWidth': '80px'},
                style_header={'backgroundColor': COLORS['danger'], 'color': 'white',
                              'fontWeight': '600', 'border': 'none', 'fontSize': '0.85em'},
                style_data={'backgroundColor': th['card_bg'], 'color': th['text'],
                            'border': f'1px solid {th["card_border"]}'},
                style_filter={'backgroundColor': th['input_bg'], 'color': th['input_text'],
                              'border': f'1px solid {th["input_border"]}',
                              'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                              'fontSize': '0.85em'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': th['plot_bg']},
                    {'if': {'column_id': 'amount'}, 'textAlign': 'right', 'fontWeight': '600'},
                ],
                tooltip_delay=0, tooltip_duration=None,
            ),
        ])

    return line_fig, bar_fig, donut_fig, mom_fig, heat_fig, stats, tbl, prog_style, prog_text


# ── Main tab switcher (updated for 3 tabs) ────────────────────────────────────
@app.callback(
    Output('panel-sales',    'className', allow_duplicate=True),
    Output('panel-expenses', 'className', allow_duplicate=True),
    Output('panel-ai',       'className'),
    Output('btn-sales',      'className', allow_duplicate=True),
    Output('btn-expenses',   'className', allow_duplicate=True),
    Output('btn-ai',         'className'),
    Input('btn-sales',       'n_clicks'),
    Input('btn-expenses',    'n_clicks'),
    Input('btn-ai',          'n_clicks'),
    prevent_initial_call=True,
)
def switch_all_tabs(_s, _e, _a):
    tid = ctx.triggered_id
    if tid == 'btn-expenses':
        return ('tab-panel', 'tab-panel active', 'tab-panel',
                'tab-btn', 'tab-btn active', 'tab-btn')
    if tid == 'btn-ai':
        return ('tab-panel', 'tab-panel', 'tab-panel active',
                'tab-btn', 'tab-btn', 'tab-btn active')
    return ('tab-panel active', 'tab-panel', 'tab-panel',
            'tab-btn active', 'tab-btn', 'tab-btn')


# ── AI Insights generator ─────────────────────────────────────────────────────
def _build_data_summary(user_id):
    """Build a compact data summary string to send to Claude."""
    sales_records   = load_user_data(user_id)
    expense_records = load_expense_data(user_id)
    sales_df   = records_to_df(sales_records)
    expense_df = expense_records_to_df(expense_records)

    summary = {}

    if not sales_df.empty:
        s = sales_df.copy()
        s['month'] = s['date'].dt.to_period('M').astype(str)
        monthly = s.groupby('month')['sales'].sum().tail(6).to_dict()
        top_products = (s.groupby('product')['sales'].sum()
                         .sort_values(ascending=False).head(5).to_dict())
        by_category = (s.groupby('category')['sales'].sum()
                        .sort_values(ascending=False).to_dict()) if s['category'].any() else {}
        summary['sales'] = {
            'total':        round(float(s['sales'].sum()), 2),
            'average':      round(float(s['sales'].mean()), 2),
            'records':      len(s),
            'date_range':   f"{s['date'].min().date()} to {s['date'].max().date()}",
            'monthly':      {k: round(v, 2) for k, v in monthly.items()},
            'top_products': {k: round(v, 2) for k, v in top_products.items()},
            'by_category':  {k: round(v, 2) for k, v in by_category.items()},
        }

    if not expense_df.empty:
        e = expense_df.copy()
        e['month'] = e['date'].dt.to_period('M').astype(str)
        monthly_exp = e.groupby('month')['amount'].sum().tail(6).to_dict()
        top_vendors = (e.groupby('vendor')['amount'].sum()
                        .sort_values(ascending=False).head(5).to_dict())
        by_cat_exp  = (e.groupby('category')['amount'].sum()
                        .sort_values(ascending=False).to_dict()) if e['category'].any() else {}
        summary['expenses'] = {
            'total':       round(float(e['amount'].sum()), 2),
            'average':     round(float(e['amount'].mean()), 2),
            'records':     len(e),
            'date_range':  f"{e['date'].min().date()} to {e['date'].max().date()}",
            'monthly':     {k: round(v, 2) for k, v in monthly_exp.items()},
            'top_vendors': {k: round(v, 2) for k, v in top_vendors.items()},
            'by_category': {k: round(v, 2) for k, v in by_cat_exp.items()},
        }

    if 'sales' in summary and 'expenses' in summary:
        total_s = summary['sales']['total']
        total_e = summary['expenses']['total']
        summary['profit'] = {
            'gross_profit':  round(total_s - total_e, 2),
            'profit_margin': round((total_s - total_e) / total_s * 100, 1) if total_s else 0,
        }

    return summary


@app.callback(
    Output('ai-summary',         'children'),
    Output('ai-strengths',       'children'),
    Output('ai-risks',           'children'),
    Output('ai-recommendations', 'children'),
    Output('ai-forecast',        'children'),
    Output('ai-generated-at',    'children'),
    Output('ai-results',         'style'),
    Output('ai-loading',         'style'),
    Output('ai-empty',           'style'),
    Output('ai-error-msg',       'children'),
    Output('ai-error-msg',       'style'),
    Input('ai-generate-btn',     'n_clicks'),
    State('session-store',       'data'),
    prevent_initial_call=True,
)
def generate_ai_insights(n_clicks, session):
    if not n_clicks:
        raise PreventUpdate

    user_id = (session or {}).get('user_id')
    if not user_id:
        raise PreventUpdate

    hidden   = {'display': 'none'}
    err_show = {'display': 'block', 'marginTop': '12px', 'padding': '10px 14px',
                'borderRadius': '8px', 'backgroundColor': '#fee2e2',
                'color': '#991b1b', 'fontSize': '0.9em',
                'border': '1px solid #ef4444'}

    try:
        data_summary = _build_data_summary(user_id)
    except Exception as e:
        print(f"[ai] data build error: {e}")
        return ('', '', '', '', '', '',
                hidden, hidden, {'display':'block'},
                f'Could not load your data: {e}', err_show)

    if not data_summary:
        return ('', '', '', '', '', '',
                hidden, hidden, {'display':'block'},
                'No data found. Upload or enter sales records first.', err_show)

    prompt = f"""You are a business analyst. Analyse this Ghana-based business data (GHS amounts) and give brief insights.

DATA:
{json.dumps(data_summary, indent=2)}

Reply ONLY with this JSON — no markdown, no extra text, keep each value under 100 words:
{{"summary":"1-2 sentences on business health","strengths":"2-3 bullet points using •","risks":"2-3 bullet points using •","recommendations":"3 numbered recommendations","forecast":"1-2 sentences on outlook"}}"""

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  SITE_URL,
                "X-Title":       "Sales Dashboard",
            },
            json={
                "model":      OPENROUTER_MODEL,
                "max_tokens": 1024,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        insights = json.loads(raw)

        generated_at = f"Generated at {datetime.now().strftime('%d %b %Y, %H:%M')} · Powered by AI"

        return (
            insights.get('summary', ''),
            insights.get('strengths', ''),
            insights.get('risks', ''),
            insights.get('recommendations', ''),
            insights.get('forecast', ''),
            generated_at,
            {'display': 'block'},   # ai-results
            hidden,                  # ai-loading
            hidden,                  # ai-empty
            '',                      # ai-error-msg children
            hidden,                  # ai-error-msg style
        )

    except json.JSONDecodeError as e:
        print(f"[ai] JSON parse error: {e}\nRaw: {raw[:300]}")
        return ('', '', '', '', '', '',
                hidden, hidden, {'display':'block'},
                'AI returned an unexpected format. Please try again.', err_show)
    except Exception as e:
        print(f"[ai] API error: {e}")
        return ('', '', '', '', '', '',
                hidden, hidden, {'display':'block'},
                f'AI error: {str(e)}', err_show)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port, debug=False)