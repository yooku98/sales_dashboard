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
    'border': '2px solid #e5e7eb', 'borderRadius': '8px',
    'fontSize': '1em', 'outline': 'none',
}
LABEL_STYLE = {
    'display': 'block', 'marginBottom': '6px', 'fontWeight': '600',
    'color': COLORS['dark'], 'fontSize': '0.9em',
}
AUTH_INPUT = {
    'width': '100%', 'padding': '12px', 'marginBottom': '15px',
    'border': '1px solid #d1d5db', 'borderRadius': '5px',
    'fontSize': '1em', 'boxSizing': 'border-box',
}
AUTH_WRAP = {
    'display': 'flex', 'height': '100vh',
    'alignItems': 'center', 'justifyContent': 'center',
    'background': '#f4f6f8', 'fontFamily': 'Segoe UI',
}
AUTH_CARD = {
    'width': '350px', 'padding': '30px', 'borderRadius': '10px',
    'background': 'white', 'boxShadow': '0 4px 10px rgba(0,0,0,0.1)',
}

CSS = f"""
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 0; -webkit-text-size-adjust: 100%; overflow-x: hidden; }}
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
  background: white; border-radius: 14px; padding: 20px 20px 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.07); min-width: 0;
}}
.graph-wrap {{ width: 100%; height: {CHART_H}px; position: relative; }}
.graph-wrap .js-plotly-plot,
.graph-wrap .plot-container,
.graph-wrap .svg-container {{ width: 100% !important; height: 100% !important; }}
.input-card {{
  background: white; border-radius: 14px; padding: 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.07); margin-bottom: 18px;
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
  background: white; border-radius: 12px; padding: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07); min-width: 0;
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
</style>
"""

app.index_string = (
    '<!DOCTYPE html>\n<html>\n  <head>\n'
    '    {%metas%}\n    <title>Sales Dashboard</title>\n'
    '    {%favicon%}\n    {%css%}\n'
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

def empty_fig():
    fig = go.Figure()
    fig.add_annotation(
        text='No data — upload a file or enter records manually',
        showarrow=False, font=dict(size=13, color='#9ca3af'),
        xref='paper', yref='paper', x=0.5, y=0.5,
    )
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=CHART_H, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig

def stat_card(title, value, icon, color):
    return html.Div(className='stat-card', style={'borderLeft': f'4px solid {color}'}, children=[
        html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'},
                 children=[
                     html.Div([
                         html.Div(title, style={'color': '#6b7280', 'fontSize': '0.75em',
                                                'fontWeight': '500', 'textTransform': 'uppercase',
                                                'letterSpacing': '0.04em', 'marginBottom': '4px'}),
                         html.Div(value, className='stat-val',
                                  style={'color': COLORS['dark'], 'fontSize': '1.6em',
                                         'fontWeight': '700', 'lineHeight': '1.1', 'wordBreak': 'break-all'}),
                     ]),
                     html.Div(icon, className='stat-icon',
                              style={'fontSize': '2em', 'opacity': '0.2', 'flexShrink': '0'}),
                 ]),
    ])

# ── Page layouts ───────────────────────────────────────────────────────────────
def login_layout():
    return html.Div(style=AUTH_WRAP, children=[
        html.Div(style=AUTH_CARD, children=[
            html.H2("Login", style={"textAlign": "center", "marginBottom": "30px"}),
            dcc.Input(id="login-email", type="email", placeholder="Email address",
                      debounce=False, style=AUTH_INPUT),
            dcc.Input(id="login-password", type="password", placeholder="Password",
                      debounce=False, style=AUTH_INPUT),
            html.Button("Sign In", id="login-btn", n_clicks=0,
                        style={**BTN_BASE, "width": "100%", "padding": "12px",
                               "backgroundColor": "#2563eb", "color": "white"}),
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
                      debounce=False, style=AUTH_INPUT),
            dcc.Input(id="signup-password", type="password", placeholder="Password (min 6 chars)",
                      debounce=False, style=AUTH_INPUT),
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
        style={'backgroundColor': COLORS['light'], 'minHeight': '100vh', 'margin': '0',
               'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"},
        children=[
            dcc.Store(id='stored-data', storage_type='session', data=[]),

            html.Div(id='app-header', style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                'color': 'white', 'boxShadow': '0 4px 14px rgba(102,126,234,0.3)',
                'marginBottom': '18px',
            }, children=[
                html.H1('\U0001f4ca Sales Analytics Dashboard', className='hdr-title',
                        style={'margin': '0', 'fontSize': '1.9em', 'fontWeight': '700'}),
                html.P(f'Track sales in Ghana Cedis ({CEDI}) \u2014 data saved to Supabase',
                       className='hdr-sub',
                       style={'margin': '6px 0 0', 'fontSize': '0.95em', 'opacity': '0.88'}),
            ]),

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
                                style={'color': COLORS['dark'], 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                        dcc.Upload(id='upload-data', multiple=False,
                                   style={
                                       'height': '130px', 'borderWidth': '2px', 'borderStyle': 'dashed',
                                       'borderRadius': '10px', 'borderColor': COLORS['primary'],
                                       'backgroundColor': '#f9fafb', 'cursor': 'pointer',
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
                                style={'color': COLORS['dark'], 'fontSize': '1.2em', 'margin': '0 0 14px'}),
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
                                style={'color': COLORS['dark'], 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                        html.P('Daily totals \u2014 all products',
                               style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                        html.Div(className='graph-wrap', children=[
                            dcc.Graph(id='sales-line-chart', style={'height': '100%'},
                                      config={'displayModeBar': False, 'responsive': True}),
                        ]),
                    ]),
                    html.Div(className='chart-card', children=[
                        html.H3('\U0001f3c6 Top Products',
                                style={'color': COLORS['dark'], 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                        html.P(f'Total {CEDI} by product (top 10)',
                               style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                        html.Div(className='graph-wrap', children=[
                            dcc.Graph(id='product-bar-chart', style={'height': '100%'},
                                      config={'displayModeBar': False, 'responsive': True}),
                        ]),
                    ]),
                ]),

                html.Div(id='data-table-container',
                         style={'background': 'white', 'borderRadius': '14px', 'padding': '22px',
                                'boxShadow': '0 2px 10px rgba(0,0,0,0.07)', 'marginBottom': '24px'}),

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
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='session-store', storage_type='session'),
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
    State('login-email',    'value'),
    State('login-password', 'value'),
    prevent_initial_call=True,
)
def login_user(n_clicks, email, password):
    if not email or not password:
        return "Please fill in all fields.", no_update, no_update
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session_data = {"token": res.session.access_token, "user_id": res.user.id}
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
                'backgroundColor': 'white', 'color': COLORS['primary']}
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
    Input('stored-data',           'data'),
    State('session-store',         'data'),
)
def update_dashboard(stored_data, session):
    user_id = (session or {}).get('user_id')
    records = load_user_data(user_id) if user_id else (stored_data or [])
    data = records_to_df(records)

    if data.empty:
        stats = [html.Div('\U0001f4ed No data yet \u2014 upload a file or enter records manually.',
                          style={'color': '#6b7280', 'padding': '18px', 'textAlign': 'center',
                                 'gridColumn': '1 / -1', 'background': 'white',
                                 'borderRadius': '12px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'})]
    else:
        s = data['sales'].dropna()
        stats = [
            stat_card('Total Sales',  fmt_cedi(s.sum()),             '\U0001f4b0', COLORS['success']),
            stat_card('Average Sale', fmt_cedi(s.mean()),             '\U0001f4ca', COLORS['primary']),
            stat_card('Products',     str(data['product'].nunique()), '\U0001f3f7\ufe0f', COLORS['warning']),
            stat_card('Records',      str(len(data)),                 '\U0001f4dd', COLORS['secondary']),
        ]

    if data.empty:
        line_fig = empty_fig()
    else:
        clean = data.dropna(subset=['date', 'sales']).copy()
        clean['_d'] = clean['date'].dt.normalize()
        daily = (clean.groupby('_d', as_index=False)['sales']
                      .sum().rename(columns={'_d': 'date'}).sort_values('date'))
        line_fig = empty_fig() if daily.empty else _line_chart(daily)

    bar_fig = empty_fig() if data.empty else _bar_chart(data)

    if data.empty:
        tbl = html.Div('\U0001f4ed No data to display.',
                       style={'color': '#6b7280', 'textAlign': 'center', 'padding': '20px'})
    else:
        disp = data.sort_values('date', ascending=False).copy()
        disp['date']  = disp['date'].dt.strftime('%Y-%m-%d')
        disp['sales'] = disp['sales'].round(2)
        col_map = {'date': 'Date', 'product': 'Product', 'sales': f'Sales ({CEDI})'}
        tbl = html.Div([
            html.Div(className='tbl-hdr', children=[
                html.H3('\U0001f4cb All Sales Data',
                        style={'color': COLORS['dark'], 'margin': '0', 'fontSize': '1.1em'}),
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
                style_data={'border': '1px solid #e5e7eb'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9fafb'},
                    {'if': {'column_id': 'sales'}, 'textAlign': 'right', 'fontWeight': '600'},
                ],
            ),
        ])

    return line_fig, bar_fig, stats, tbl


def _line_chart(daily):
    fig = px.line(daily, x='date', y='sales', labels={'date': '', 'sales': ''})
    fig.update_traces(
        line_color=COLORS['primary'], line_width=2.5, mode='lines+markers',
        marker=dict(size=5, color=COLORS['primary'], line=dict(width=2, color='white')),
        fill='tozeroy', fillcolor='rgba(102,126,234,0.1)',
        hovertemplate=f'%{{x|%b %d}}<br>{CEDI}%{{y:,.0f}}',
    )
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white', height=CHART_H,
        margin=dict(l=60, r=12, t=8, b=40), hovermode='x unified',
        xaxis=dict(showgrid=False, showline=True, linecolor='#e5e7eb',
                   tickformat='%b %d', tickfont=dict(size=10), fixedrange=True, title=None),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', zeroline=False,
                   tickprefix=CEDI, tickfont=dict(size=10), fixedrange=True, title=None),
    )
    return fig


def _bar_chart(data):
    ps = (data.dropna(subset=['product', 'sales'])
              .groupby('product', as_index=False)['sales']
              .sum().sort_values('sales', ascending=False).head(10))
    if ps.empty:
        return empty_fig()
    fig = px.bar(ps, x='product', y='sales', labels={'product': '', 'sales': ''},
                 color='sales',
                 color_continuous_scale=[[0, COLORS['primary']], [1, COLORS['secondary']]])
    fig.update_traces(hovertemplate=f'%{{x}}<br>{CEDI}%{{y:,.0f}}')
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white', height=CHART_H,
        margin=dict(l=60, r=12, t=8, b=56), coloraxis_showscale=False,
        xaxis=dict(showgrid=False, showline=True, linecolor='#e5e7eb',
                   categoryorder='total descending', tickfont=dict(size=10),
                   fixedrange=True, tickangle=-30, title=None),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', zeroline=False,
                   tickprefix=CEDI, tickfont=dict(size=10), fixedrange=True, title=None),
    )
    return fig


if __name__ == '__main__':
    app.run(debug=True)