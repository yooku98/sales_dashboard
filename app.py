import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client

# ── Supabase ───────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── App ────────────────────────────────────────────────────────────────────────
CEDI = '\u20b5'

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
AUTH_INPUT = {}  # Styled via CSS input#id selectors
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
@media (max-width: 760px) {{ #charts-row {{ grid-template-columns: 1fr; }} }}
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
  grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) auto;
  gap: 14px; align-items: end; margin-bottom: 14px;
}}
#manual-form-grid > div {{ min-width: 0; }}
@media (max-width: 680px) {{ #manual-form-grid {{ grid-template-columns: minmax(0,1fr) minmax(0,1fr); }} }}
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

/* ── Auth inputs — target the actual <input> Dash renders inside the wrapper ── */
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

app.index_string = (
    '<!DOCTYPE html>\n<html>\n  <head>\n'
    '    {%metas%}\n    <title>Sales Dashboard</title>\n'
    '    {%favicon%}\n    {%css%}\n'
    + PWA_TAGS
    + CSS +
    '  </head>\n  <body>\n    {%app_entry%}\n'
    '    <footer>{%config%}{%scripts%}{%renderer%}</footer>\n'
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
            }).execute()
        except Exception as e:
            print(f"[insert_rows] {e}")

def delete_user_data(user_id: str):
    try:
        supabase.table("sales_records").delete().eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[delete_user_data] {e}")

# ── Data helpers ───────────────────────────────────────────────────────────────
def clean_col_names(df):
    df.columns = df.columns.str.replace(r'[\r\n]', '', regex=True).str.strip().str.lower()
    return df

def records_to_df(records):
    if not records:
        return pd.DataFrame(columns=['date', 'product', 'sales'])
    df = pd.DataFrame(records)
    df = clean_col_names(df)
    for col in ['date', 'product', 'sales']:
        if col not in df.columns:
            df[col] = None
    df = df[['date', 'product', 'sales']].copy()
    df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
    df['date']  = pd.to_datetime(df['date'], errors='coerce')
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
        for col in ['date', 'product', 'sales']:
            if col not in raw.columns:
                raw[col] = None
        raw = raw[['date', 'product', 'sales']].copy()
        raw = raw.dropna(how='all')
        raw['sales'] = pd.to_numeric(raw['sales'], errors='coerce')
        raw['date']  = pd.to_datetime(raw['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        return raw.dropna(subset=['sales'])
    except Exception as e:
        print(f'[parse_uploaded_file] {e}')
        return None

def fmt_cedi(v):
    return f'{CEDI}{v:,.0f}'

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

def stat_card(title, value, icon, color, th=None):
    if th is None:
        th = THEME['light']
    return html.Div(className='stat-card', style={
        'borderLeft': f'4px solid {color}',
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
            # Polls every 60s to detect session expiry and redirect to login
            dcc.Interval(id='session-check', interval=60_000, n_intervals=0),

            html.Div(id='app-header', style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                'color': 'white', 'boxShadow': '0 4px 14px rgba(102,126,234,0.3)',
                'marginBottom': '18px', 'padding': '20px 24px',
            }, children=[
                html.Div(style={
                    'display': 'flex', 'justifyContent': 'space-between',
                    'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '10px',
                }, children=[
                    html.H1('\U0001f4ca Sales Analytics Dashboard', className='hdr-title',
                            style={'margin': '0', 'fontSize': '1.9em', 'fontWeight': '700'}),
                    html.Div(style={'display':'flex','gap':'8px','alignItems':'center'}, children=[
                        html.Button(id='theme-toggle-btn', n_clicks=0,
                                    style={
                                        'background': 'rgba(255,255,255,0.15)',
                                        'color': 'white', 'border': '1.5px solid rgba(255,255,255,0.5)',
                                        'borderRadius': '20px', 'padding': '7px 14px',
                                        'fontSize': '0.85em', 'fontWeight': '600', 'cursor': 'pointer',
                                        'whiteSpace': 'nowrap', 'flexShrink': '0',
                                    }),
                        html.Button('\U0001f6aa Sign Out', id='signout-btn', n_clicks=0,
                                    style={
                                        'background': 'rgba(255,255,255,0.2)',
                                        'color': 'white', 'border': '1.5px solid rgba(255,255,255,0.6)',
                                        'borderRadius': '20px', 'padding': '7px 16px',
                                        'fontSize': '0.85em', 'fontWeight': '600', 'cursor': 'pointer',
                                        'whiteSpace': 'nowrap', 'flexShrink': '0',
                                    }),
                    ]),
                ]),
                html.Div(style={'marginTop': '8px'}, children=[
                    html.Span(id='user-greeting',
                              style={'fontSize': '0.95em', 'opacity': '0.95', 'fontWeight': '500'}),
                    html.P(f'Track sales in Ghana Cedis ({CEDI}) \u2014 data saved to Supabase',
                           className='hdr-sub',
                           style={'margin': '3px 0 0', 'fontSize': '0.85em', 'opacity': '0.75'}),
                ]),
            ]),
            html.Div(id='signout-toast', style={'display': 'none'}),

            html.Div(id='dashboard-wrapper', children=[
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
                                style={'color': 'var(--text, #1f2937)', 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                        dcc.Upload(id='upload-data', multiple=False,
                                   style={
                                       'height': '130px', 'borderWidth': '2px', 'borderStyle': 'dashed',
                                       'borderRadius': '10px', 'borderColor': COLORS['primary'],
                                       'cursor': 'pointer',
                                       'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                                       'textAlign': 'center',
                                   },
                                   children=html.Div([
                                       html.Div('\U0001f4c1', style={'fontSize': '2.2em', 'marginBottom': '6px'}),
                                       html.Div('Drag and Drop or Tap to Select',
                                                style={'fontSize': '1em', 'fontWeight': '600'}),
                                       html.Div('CSV or Excel (.xlsx)',
                                                style={'fontSize': '0.82em', 'color': '#6b7280', 'marginTop': '3px'}),
                                   ])),
                    ]),
                    html.Div(id='manual-section', style={'display': 'none'}, children=[
                        html.H3('\u270f\ufe0f Enter Sales Data',
                                style={'color': 'var(--text, #1f2937)', 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                        html.Div(id='manual-form-grid', children=[
                            html.Div([
                                html.Label('Date', style=LABEL_STYLE),
                                dcc.DatePickerSingle(id='input-date',
                                                     date=datetime.today().strftime('%Y-%m-%d'),
                                                     display_format='YYYY-MM-DD',
                                                     style={'width': '100%'}),
                            ]),
                            html.Div([
                                html.Label('Product', style=LABEL_STYLE),
                                dcc.Input(id='input-product', type='text',
                                          placeholder='Product name', style=INPUT_STYLE),
                            ]),
                            html.Div([
                                html.Label(f'Sales ({CEDI})', style=LABEL_STYLE),
                                dcc.Input(id='input-sales', type='number', min=0,
                                          placeholder='0.00', style=INPUT_STYLE),
                            ]),
                            html.Div([
                                html.Label('\u00a0', style={**LABEL_STYLE, 'visibility': 'hidden'}),
                                html.Button('\u2795 Add', id='add-data-btn', n_clicks=0,
                                            style={**BTN_BASE, 'width': '100%', 'padding': '10px 18px',
                                                   'backgroundColor': COLORS['success'], 'color': 'white'}),
                            ]),
                        ]),
                        html.Button('\U0001f5d1\ufe0f Clear All Data', id='clear-data-btn', n_clicks=0,
                                    style={**BTN_BASE, 'padding': '9px 18px', 'marginTop': '10px',
                                           'backgroundColor': COLORS['danger'], 'color': 'white'}),
                    ]),
                    html.Div(id='status-message',
                             style={'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                                    'textAlign': 'center', 'fontSize': '0.9em', 'display': 'none'}),
                ]),

                html.Div(id='stats-cards'),

                html.Div(id='charts-row', children=[
                    html.Div(className='chart-card', children=[
                        html.H3('\U0001f4c8 Sales Trend',
                                style={'color': 'var(--text, #1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                        html.P('Daily totals \u2014 all products',
                               style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                        html.Div(className='graph-wrap', children=[
                            dcc.Graph(id='sales-line-chart', style={'height': '100%'},
                                      config={'displayModeBar': False, 'responsive': True}),
                        ]),
                    ]),
                    html.Div(className='chart-card', children=[
                        html.H3('\U0001f3c6 Top Products',
                                style={'color': 'var(--text, #1f2937)', 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                        html.P(f'Total {CEDI} by product (top 10)',
                               style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                        html.Div(className='graph-wrap', children=[
                            dcc.Graph(id='product-bar-chart', style={'height': '100%'},
                                      config={'displayModeBar': False, 'responsive': True}),
                        ]),
                    ]),
                ]),

                html.Div(id='data-table-container', style={'marginBottom': '24px'}),

            ]),  # end dashboard-wrapper
                html.Div(style={'textAlign': 'center', 'padding': '10px 0 24px',
                                'color': '#9ca3af', 'fontSize': '0.82em'},
                         children=[html.Ul(
                             html.Li(html.A('William Thompson', href='https://yooku98.github.io/web',
                                            style={'color': COLORS['primary']})),
                             style={'listStyle': 'none', 'padding': 0, 'margin': 0},
                         )]),
            ]),
        ],
    )

# ── Root layout ────────────────────────────────────────────────────────────────
# session-store and url live here permanently so they are always in the DOM.
# page-content is swapped by the router callback.
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
            # Not logged in — bounce back to login
            return dcc.Location(id='auth-redirect', href='/login', refresh=True)
        return dashboard_layout()

    # /login or anything else
    return login_layout()

# ── Login callback ─────────────────────────────────────────────────────────────
# Writes the session and updates the URL pathname in one atomic step.
# Because url has refresh=False, Dash re-renders page-content via render_page
# without a full page reload — session-store is already written so the
# auth check in render_page passes immediately.
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
    # Clear error message whenever user edits either field
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

# ── Signup callback ────────────────────────────────────────────────────────────
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

# ── Greeting callback ─────────────────────────────────────────────────────────
@app.callback(
    Output('user-greeting', 'children'),
    Input('session-store',  'data'),
)
def update_greeting(session):
    if not session or not session.get('user_id'):
        return ''
    email = session.get('email', '')
    # Derive first name: take the part before @ then before any dot/underscore
    if email:
        local = email.split('@')[0]
        import re
        # Split on common separators first
        parts = re.split(r'[._\-]+', local)
        if len(parts) > 1:
            firstname = parts[0].capitalize()
        else:
            # No separator — treat whole local as name, just capitalise it
            # e.g. willvoks → Willvoks, johndoe → Johndoe
            firstname = local.capitalize()
        return f'👋 Hello, {firstname}!'
    return '👋 Hello!'

# ── Sign-out callback ──────────────────────────────────────────────────────────
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
    # Derive first name for goodbye message
    email = (session or {}).get('email', '')
    if email:
        local = email.split('@')[0]
        import re
        parts = re.split(r'[._\-]+', local)
        if len(parts) > 1:
            firstname = parts[0].capitalize()
        else:
            firstname = local.capitalize()
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

# ── Session expiry check ──────────────────────────────────────────────────────
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('session-check',  'n_intervals'),
    State('session-store',  'data'),
    State('url',            'pathname'),
    prevent_initial_call=True,
)
def check_session(n, session, pathname):
    # Only check when on the dashboard
    if pathname != '/dashboard':
        raise PreventUpdate
    if not session or not session.get('token'):
        return '/login'
    # Verify token is still valid with Supabase
    try:
        supabase.auth.get_user(session['token'])
        raise PreventUpdate
    except Exception:
        return '/login'

# ── Theme toggle callback ─────────────────────────────────────────────────────
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

# ── Sync toggle button label on page load ──────────────────────────────────────
@app.callback(
    Output('theme-toggle-btn', 'children', allow_duplicate=True),
    Input('theme-store',       'data'),
    prevent_initial_call='initial_duplicate',
)
def sync_toggle_label(theme):
    t = theme or 'dark'
    return THEME[t]['toggle_label']

# ── Apply theme to page background and cards ───────────────────────────────────
@app.callback(
    Output('app-root', 'style'),
    Input('theme-store', 'data'),
)
def apply_theme_to_root(theme):
    t = theme or 'dark'
    return {'backgroundColor': THEME[t]['page_bg'], 'minHeight': '100vh'}

# ── Dashboard: tab switcher ────────────────────────────────────────────────────
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

# ── Dashboard: data management ────────────────────────────────────────────────
@app.callback(
    Output('stored-data',    'data'),
    Output('status-message', 'children'),
    Output('status-message', 'style'),
    Output('input-product',  'value'),
    Output('input-sales',    'value'),
    Input('add-data-btn',    'n_clicks'),
    Input('clear-data-btn',  'n_clicks'),
    Input('upload-data',     'contents'),
    State('input-date',      'date'),
    State('input-product',   'value'),
    State('input-sales',     'value'),
    State('upload-data',     'filename'),
    State('session-store',   'data'),
    prevent_initial_call=True,
)
def manage_data(add_clicks, clear_clicks, upload_contents,
                date, product, sales, filename, session):
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
            return refreshed, msg, sty, no_update, no_update
        sty, msg = err(f'\u274c Could not parse "{filename}". Use CSV/Excel with date, product, sales columns.')
        return no_update, msg, sty, no_update, no_update

    if trigger == 'add-data-btn':
        if not date or not product or not str(product).strip() or sales is None:
            sty, msg = err('\u274c Fill in all fields (Date, Product, Sales).')
            return no_update, msg, sty, product, sales
        v = float(sales)
        if v < 0:
            sty, msg = err('\u274c Sales cannot be negative.')
            return no_update, msg, sty, product, sales
        new_row = pd.DataFrame({
            'date':    [pd.to_datetime(date).strftime('%Y-%m-%d')],
            'product': [str(product).strip()],
            'sales':   [v],
        })
        insert_rows(user_id, new_row)
        refreshed = load_user_data(user_id)
        sty, msg = ok(f'\u2705 Added {str(product).strip()} \u2014 {fmt_cedi(v)} on {date}')
        return refreshed, msg, sty, '', None

    if trigger == 'clear-data-btn':
        delete_user_data(user_id)
        sty, msg = ok('\u2705 All data cleared from Supabase.')
        return [], msg, sty, '', None

    raise PreventUpdate

# ── Dashboard: charts + table ─────────────────────────────────────────────────
@app.callback(
    Output('sales-line-chart',     'figure'),
    Output('product-bar-chart',    'figure'),
    Output('stats-cards',          'children'),
    Output('data-table-container', 'children'),
    Output('dashboard-wrapper',    'style'),
    Input('stored-data',           'data'),
    Input('session-store',         'data'),
    Input('theme-store',           'data'),
)
def update_dashboard(stored_data, session, theme):
    t = theme or 'dark'
    th = THEME[t]
    user_id = (session or {}).get('user_id')
    records = load_user_data(user_id) if user_id else (stored_data or [])
    data = records_to_df(records)

    if data.empty:
        stats = [html.Div('\U0001f4ed No data yet \u2014 upload a file or enter records manually.',
                          style={'color': th['sub_text'], 'padding': '18px', 'textAlign': 'center',
                                 'gridColumn': '1 / -1', 'background': th['card_bg'],
                                 'borderRadius': '12px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'})]
    else:
        s = data['sales'].dropna()
        stats = [
            stat_card('Total Sales',  fmt_cedi(s.sum()),             '\U0001f4b0', COLORS['success'],  th),
            stat_card('Average Sale', fmt_cedi(s.mean()),             '\U0001f4ca', COLORS['primary'],  th),
            stat_card('Products',     str(data['product'].nunique()), '\U0001f3f7\ufe0f', COLORS['warning'],  th),
            stat_card('Records',      str(len(data)),                 '\U0001f4dd', COLORS['secondary'], th),
        ]

    if data.empty:
        line_fig = empty_fig(t)
    else:
        clean = data.dropna(subset=['date', 'sales']).copy()
        clean['_d'] = clean['date'].dt.normalize()
        daily = (clean.groupby('_d', as_index=False)['sales']
                      .sum().rename(columns={'_d': 'date'}).sort_values('date'))
        line_fig = empty_fig(t) if daily.empty else _line_chart(daily, t)

    bar_fig = empty_fig(t) if data.empty else _bar_chart(data, t)

    if data.empty:
        tbl = html.Div('\U0001f4ed No data to display.',
                       style={'color': '#6b7280', 'textAlign': 'center', 'padding': '20px'})
    else:
        disp = data.sort_values('date', ascending=False).copy()
        disp['date']  = disp['date'].dt.strftime('%Y-%m-%d')
        disp['sales'] = disp['sales'].round(2)
        col_map = {'date': 'Date', 'product': 'Product', 'sales': f'Sales ({CEDI})'}
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
                columns=[{'name': col_map.get(c, c.title()), 'id': c} for c in disp.columns],
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
                    {'if': {'row_index': 'odd'},
                     'backgroundColor': th['plot_bg']},
                    {'if': {'column_id': 'sales'}, 'textAlign': 'right', 'fontWeight': '600'},
                ],
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
    return line_fig, bar_fig, stats, tbl, wrapper_style


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


if __name__ == '__main__':
    app.run(debug=True)