import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ── Ghana Cedi symbol ─────────────────────────────────────────────────────────

CEDI = ‘\u20b5’   # ₵

app = Dash(
**name**,
meta_tags=[
# Tells mobile browsers to use device width and prevent auto-zoom
{‘name’: ‘viewport’, ‘content’: ‘width=device-width, initial-scale=1, maximum-scale=1’},
{‘name’: ‘mobile-web-app-capable’,       ‘content’: ‘yes’},
{‘name’: ‘apple-mobile-web-app-capable’, ‘content’: ‘yes’},
],
)
server = app.server

# ── Color scheme ──────────────────────────────────────────────────────────────

COLORS = {
‘primary’:   ‘#667eea’,
‘secondary’: ‘#764ba2’,
‘success’:   ‘#10b981’,
‘warning’:   ‘#f59e0b’,
‘danger’:    ‘#ef4444’,
‘light’:     ‘#f3f4f6’,
‘dark’:      ‘#1f2937’,
‘white’:     ‘#ffffff’,
}

# ── Responsive CSS ─────────────────────────────────────────────────────────────

# Dash inline styles don’t support media queries, so we inject CSS via

# app.index_string to handle all mobile breakpoints in one place.

MOBILE_CSS = “””

<style>
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; padding: 0; -webkit-text-size-adjust: 100%; overflow-x: hidden; }

  /* Header text */
  @media (max-width: 600px) {
    .dash-h1  { font-size: 1.45em !important; }
    .dash-sub { font-size: 0.88em !important; }
  }

  /* Stats grid — 4 cols desktop → 2 cols tablet/mobile */
  #stats-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 20px;
  }
  @media (max-width: 860px)  { #stats-cards { grid-template-columns: repeat(2, 1fr); gap: 12px; } }
  @media (max-width: 400px)  { #stats-cards { gap: 10px; } }

  /* Charts — side by side on desktop, stacked on mobile */
  #charts-row {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 20px;
  }
  @media (max-width: 780px) { #charts-row { grid-template-columns: 1fr; } }

  /* Manual entry form — 4-col desktop, 2-col tablet, 1-col mobile */
  #manual-form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr auto;
    gap: 14px;
    align-items: end;
    margin-bottom: 14px;
  }
  @media (max-width: 680px) { #manual-form-grid { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 420px) { #manual-form-grid { grid-template-columns: 1fr;     } }

  /* Full-width action buttons on small screens */
  @media (max-width: 680px) {
    #add-data-btn   { width: 100%; }
    #clear-data-btn { width: 100%; margin-top: 4px; }
  }

  /* Tab buttons fill row on very small screens */
  @media (max-width: 420px) {
    #tab-upload, #tab-manual {
      flex: 1; text-align: center;
      padding: 9px 6px !important;
      font-size: 0.85em !important;
    }
  }

  /* Stat card internal scaling */
  @media (max-width: 600px) {
    .stat-value { font-size: 1.4em !important; }
    .stat-icon  { font-size: 1.9em !important; }
    .dash-card  { padding: 14px !important; }
  }

  /* Main container horizontal padding */
  #main-container { max-width: 1400px; margin: 0 auto; padding: 0 20px; }
  @media (max-width: 480px) { #main-container { padding: 0 12px; } }

  /* Header padding */
  #app-header { padding: 24px 20px; }
  @media (max-width: 480px) { #app-header { padding: 16px 14px; } }

  /* Upload zone — shorter on mobile */
  @media (max-width: 560px) {
    #upload-data               { height: 110px !important; }
    .upload-icon               { font-size: 2em !important; }
    .upload-main               { font-size: 0.95em !important; }
    .upload-sub                { font-size: 0.78em !important; }
  }

  /* DataTable: always scroll, never wrap */
  .dash-spreadsheet-container { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
  .dash-cell div              { white-space: nowrap !important; }

  /* DatePicker width fix */
  .DateInput, .DateInput_input, .SingleDatePickerInput { width: 100% !important; }

  /* Table header row wraps on very small screens */
  @media (max-width: 440px) {
    #table-header-row { flex-direction: column; align-items: flex-start !important; gap: 6px; }
  }
</style>

“””

app.index_string = (
‘<!DOCTYPE html>\n<html>\n  <head>\n’
’    {%metas%}\n    <title>Sales Analytics</title>\n’
’    {%favicon%}\n    {%css%}\n’
+ MOBILE_CSS +
’  </head>\n  <body>\n    {%app_entry%}\n’
’    <footer>{%config%}{%scripts%}{%renderer%}</footer>\n’
’  </body>\n</html>’
)

# ── Sample / seed data (first-ever visit only) ─────────────────────────────────

def build_seed_data():
df = pd.DataFrame({
‘date’:    pd.date_range(‘2024-01-01’, periods=10, freq=‘D’).strftime(’%Y-%m-%d’).tolist(),
‘product’: [‘Product A’, ‘Product B’, ‘Product C’] * 3 + [‘Product A’],
‘sales’:   [100, 150, 200, 120, 180, 220, 140, 190, 230, 160],
})
for path, reader in [(‘data/sales.csv’, pd.read_csv), (‘data/sales.xlsx’, pd.read_excel)]:
if os.path.exists(path):
try:
d = reader(path)
d.columns = d.columns.str.strip().str.lower()
for col in [‘date’, ‘product’, ‘sales’]:
if col not in d.columns:
d[col] = None
d = d.dropna(how=‘all’)
d[‘sales’] = pd.to_numeric(d[‘sales’], errors=‘coerce’)
d[‘date’]  = pd.to_datetime(d[‘date’], errors=‘coerce’).dt.strftime(’%Y-%m-%d’)
return d.dropna(subset=[‘sales’]).to_dict(‘records’)
except Exception:
pass
return df.to_dict(‘records’)

SEED_DATA = build_seed_data()

# ── Data helpers ───────────────────────────────────────────────────────────────

def records_to_df(records):
“”“Convert stored JSON records to a clean, type-safe DataFrame.”””
if not records:
return pd.DataFrame(columns=[‘date’, ‘product’, ‘sales’])
df = pd.DataFrame(records)
for col in [‘date’, ‘product’, ‘sales’]:
if col not in df.columns:
df[col] = None
df[‘sales’] = pd.to_numeric(df[‘sales’], errors=‘coerce’)
df[‘date’]  = pd.to_datetime(df[‘date’],  errors=‘coerce’)
df = df.dropna(subset=[‘sales’])
df = df[df[‘product’].notna() & (df[‘product’].astype(str).str.strip() != ‘’)]
return df.reset_index(drop=True)

def parse_uploaded_file(contents, filename):
“”“Parse base64-encoded CSV or Excel upload. Returns DataFrame or None.”””
if not contents or not filename:
return None
try:
_ct, b64 = contents.split(’,’, 1)
decoded  = base64.b64decode(b64)
if filename.lower().endswith(’.csv’):
raw = pd.read_csv(io.StringIO(decoded.decode(‘utf-8’, errors=‘ignore’)), skip_blank_lines=True)
elif filename.lower().endswith((’.xlsx’, ‘.xls’)):
raw = pd.read_excel(io.BytesIO(decoded))
else:
return None
raw.columns = raw.columns.str.strip().str.lower()
for col in [‘date’, ‘product’, ‘sales’]:
if col not in raw.columns:
raw[col] = None
raw = raw.dropna(how=‘all’)
raw[‘sales’] = pd.to_numeric(raw[‘sales’], errors=‘coerce’)
raw[‘date’]  = pd.to_datetime(raw[‘date’], errors=‘coerce’).dt.strftime(’%Y-%m-%d’)
return raw.dropna(subset=[‘sales’])
except Exception as e:
print(f’[parse_uploaded_file] {e}’)
return None

def fmt_cedi(value):
“”“Format a number as Ghana Cedis: ₵1,234.”””
return f’{CEDI}{value:,.0f}’

def empty_figure(msg=‘No data available<br>Upload a file or enter data manually’):
fig = go.Figure()
fig.add_annotation(text=msg, showarrow=False, font=dict(size=13, color=’#6b7280’),
xref=‘paper’, yref=‘paper’, x=0.5, y=0.5)
fig.update_layout(plot_bgcolor=‘white’, paper_bgcolor=‘white’,
autosize=True, height=260,
margin=dict(l=10, r=10, t=10, b=10),
xaxis=dict(visible=False), yaxis=dict(visible=False))
return fig

# ── Shared style constants ─────────────────────────────────────────────────────

INPUT_STYLE = {
‘width’: ‘100%’, ‘padding’: ‘10px 12px’,
‘border’: ‘2px solid #e5e7eb’, ‘borderRadius’: ‘8px’,
‘fontSize’: ‘1em’, ‘boxSizing’: ‘border-box’, ‘outline’: ‘none’,
‘transition’: ‘border-color 0.2s’,
}
LABEL_STYLE = {
‘display’: ‘block’, ‘marginBottom’: ‘6px’,
‘fontWeight’: ‘600’, ‘color’: COLORS[‘dark’], ‘fontSize’: ‘0.9em’,
}
CARD_STYLE = {
‘backgroundColor’: COLORS[‘white’], ‘borderRadius’: ‘14px’,
‘padding’: ‘22px’, ‘boxShadow’: ‘0 2px 10px rgba(0,0,0,0.07)’,
}

def create_stat_card(title, value, icon, color):
return html.Div(
className=‘dash-card’,
style={
‘backgroundColor’: COLORS[‘white’], ‘borderRadius’: ‘12px’,
‘padding’: ‘18px’, ‘boxShadow’: ‘0 2px 8px rgba(0,0,0,0.07)’,
‘borderLeft’: f’4px solid {color}’,
},
children=[html.Div(
style={‘display’: ‘flex’, ‘justifyContent’: ‘space-between’, ‘alignItems’: ‘center’},
children=[
html.Div([
html.Div(title,
style={‘color’: ‘#6b7280’, ‘fontSize’: ‘0.78em’, ‘marginBottom’: ‘5px’,
‘fontWeight’: ‘500’, ‘textTransform’: ‘uppercase’,
‘letterSpacing’: ‘0.04em’}),
html.Div(value,
className=‘stat-value’,
style={‘color’: COLORS[‘dark’], ‘fontSize’: ‘1.55em’,
‘fontWeight’: ‘700’, ‘lineHeight’: ‘1.15’,
‘wordBreak’: ‘break-all’}),
]),
html.Div(icon, className=‘stat-icon’,
style={‘fontSize’: ‘2.1em’, ‘opacity’: ‘0.22’, ‘flexShrink’: ‘0’}),
],
)],
)

# ── Layout ─────────────────────────────────────────────────────────────────────

app.layout = html.Div(
style={
‘backgroundColor’: COLORS[‘light’],
‘minHeight’: ‘100vh’,
‘margin’: ‘0’,
‘overflowX’: ‘hidden’,
‘fontFamily’: “‘Segoe UI’, Tahoma, Geneva, Verdana, sans-serif”,
},
children=[

```
    # ── Persistent store — survives page refresh via localStorage ────────
    # data=SEED_DATA only used on first-ever visit (empty localStorage).
    dcc.Store(id='stored-data', storage_type='local', data=SEED_DATA),

    # ── Header ──────────────────────────────────────────────────────────
    html.Div(
        id='app-header',
        style={
            'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
            'color': COLORS['white'],
            'boxShadow': '0 4px 14px rgba(102,126,234,0.35)',
            'marginBottom': '20px',
            'textAlign': 'center',
        },
        children=[
            html.H1(
                f'\U0001f4ca Sales Analytics Dashboard',
                className='dash-h1',
                style={'margin': '0', 'fontSize': '2em', 'fontWeight': '700'},
            ),
            html.P(
                f'Track your sales in Ghana Cedis ({CEDI}) \u2014 data saved in this browser',
                className='dash-sub',
                style={'margin': '8px 0 0 0', 'fontSize': '0.98em', 'opacity': '0.88'},
            ),
        ],
    ),

    # ── Main container ──────────────────────────────────────────────────
    html.Div(
        id='main-container',
        children=[

            # ── Input card ──────────────────────────────────────────────
            html.Div(
                className='dash-card',
                style={**CARD_STYLE, 'marginBottom': '20px'},
                children=[

                    # Tab row
                    html.Div(
                        style={'display': 'flex', 'gap': '10px', 'marginBottom': '20px',
                               'borderBottom': '2px solid #e5e7eb', 'paddingBottom': '12px'},
                        children=[
                            html.Button('📤 Upload File', id='tab-upload', n_clicks=1,
                                        style={'padding': '10px 20px', 'border': 'none',
                                               'borderRadius': '8px', 'cursor': 'pointer',
                                               'fontSize': '0.95em', 'fontWeight': '600',
                                               'backgroundColor': COLORS['primary'], 'color': 'white',
                                               'transition': 'all 0.2s', 'touchAction': 'manipulation'}),
                            html.Button('\u270f\ufe0f Enter Manually', id='tab-manual', n_clicks=0,
                                        style={'padding': '10px 20px',
                                               'border': f'2px solid {COLORS["primary"]}',
                                               'borderRadius': '8px', 'cursor': 'pointer',
                                               'fontSize': '0.95em', 'fontWeight': '600',
                                               'backgroundColor': 'white', 'color': COLORS['primary'],
                                               'transition': 'all 0.2s', 'touchAction': 'manipulation'}),
                        ],
                    ),

                    # Upload section
                    html.Div(id='upload-section', children=[
                        html.H3('\U0001f4e4 Upload Your Data',
                                style={'color': COLORS['dark'], 'fontSize': '1.25em',
                                       'margin': '0 0 14px 0'}),
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.Div('\U0001f4c1', className='upload-icon',
                                         style={'fontSize': '2.4em', 'marginBottom': '6px'}),
                                html.Div('Drag and Drop or Tap to Select', className='upload-main',
                                         style={'fontSize': '1.05em', 'fontWeight': '600'}),
                                html.Div('Supports CSV and Excel (.xlsx)', className='upload-sub',
                                         style={'fontSize': '0.83em', 'color': '#6b7280', 'marginTop': '3px'}),
                            ]),
                            style={
                                'width': '100%', 'height': '130px', 'boxSizing': 'border-box',
                                'borderWidth': '2px', 'borderStyle': 'dashed',
                                'borderRadius': '10px', 'borderColor': COLORS['primary'],
                                'textAlign': 'center', 'backgroundColor': '#f9fafb',
                                'cursor': 'pointer', 'display': 'flex',
                                'alignItems': 'center', 'justifyContent': 'center',
                                'transition': 'all 0.2s',
                                'WebkitTapHighlightColor': 'transparent',
                            },
                            multiple=False,
                        ),
                    ]),

                    # Manual entry section
                    html.Div(id='manual-section', style={'display': 'none'}, children=[
                        html.H3('\u270f\ufe0f Enter Sales Data',
                                style={'color': COLORS['dark'], 'fontSize': '1.25em',
                                       'margin': '0 0 14px 0'}),

                        html.Div(
                            id='manual-form-grid',
                            children=[
                                html.Div([
                                    html.Label('Date', style=LABEL_STYLE),
                                    dcc.DatePickerSingle(
                                        id='input-date',
                                        date=datetime.today().strftime('%Y-%m-%d'),
                                        display_format='YYYY-MM-DD',
                                        style={'width': '100%'},
                                    ),
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
                                    # Invisible label keeps button aligned to inputs on desktop
                                    html.Label('\u00a0', style={**LABEL_STYLE, 'visibility': 'hidden'}),
                                    html.Button(
                                        '\u2795 Add', id='add-data-btn', n_clicks=0,
                                        style={
                                            'width': '100%', 'padding': '10px 18px',
                                            'backgroundColor': COLORS['success'],
                                            'color': 'white', 'border': 'none',
                                            'borderRadius': '8px', 'cursor': 'pointer',
                                            'fontSize': '1em', 'fontWeight': '600',
                                            'touchAction': 'manipulation',
                                        },
                                    ),
                                ]),
                            ],
                        ),

                        html.Button(
                            '\U0001f5d1\ufe0f Clear All Data', id='clear-data-btn', n_clicks=0,
                            style={
                                'padding': '9px 18px', 'marginTop': '12px',
                                'backgroundColor': COLORS['danger'],
                                'color': 'white', 'border': 'none',
                                'borderRadius': '8px', 'cursor': 'pointer',
                                'fontSize': '0.9em', 'fontWeight': '600',
                                'touchAction': 'manipulation',
                            },
                        ),
                    ]),

                    # Status feedback message
                    html.Div(id='status-message',
                             style={'marginTop': '12px', 'padding': '10px 14px',
                                    'borderRadius': '8px', 'textAlign': 'center',
                                    'fontSize': '0.9em', 'display': 'none'}),
                ],
            ),

            # ── Stats (grid layout from CSS) ────────────────────────────
            html.Div(id='stats-cards'),

            # ── Charts (grid layout from CSS) ───────────────────────────
            html.Div(
                id='charts-row',
                children=[
                    html.Div(
                        className='dash-card',
                        style=CARD_STYLE,
                        children=[
                            html.H3('\U0001f4c8 Sales Trend',
                                    style={'color': COLORS['dark'], 'margin': '0 0 2px 0',
                                           'fontSize': '1.1em'}),
                            html.P('Daily totals \u2014 all products',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em',
                                          'margin': '0 0 10px 0'}),
                            dcc.Graph(id='sales-line-chart',
                                      config={'displayModeBar': False, 'responsive': True}),
                        ],
                    ),
                    html.Div(
                        className='dash-card',
                        style=CARD_STYLE,
                        children=[
                            html.H3('\U0001f3c6 Top Products',
                                    style={'color': COLORS['dark'], 'margin': '0 0 2px 0',
                                           'fontSize': '1.1em'}),
                            html.P(f'Total {CEDI} sales by product (top 10)',
                                   style={'color': '#9ca3af', 'fontSize': '0.78em',
                                          'margin': '0 0 10px 0'}),
                            dcc.Graph(id='product-bar-chart',
                                      config={'displayModeBar': False, 'responsive': True}),
                        ],
                    ),
                ],
            ),

            html.Div(style={'height': '20px'}),

            # ── Data table ──────────────────────────────────────────────
            html.Div(
                id='data-table-container',
                className='dash-card',
                style={**CARD_STYLE, 'marginBottom': '24px'},
            ),

            # ── Footer ──────────────────────────────────────────────────
            html.Div(
                style={'textAlign': 'center', 'padding': '12px 0 24px',
                       'color': '#9ca3af', 'fontSize': '0.83em'},
                children=[html.Ul(
                    html.Li(html.A('William Thompson', href='https://yooku98.github.io/web',
                                   style={'color': COLORS['primary']})),
                    style={'listStyle': 'none', 'padding': 0, 'margin': 0},
                )],
            ),
        ],
    ),
],
```

)

# ── Callbacks ──────────────────────────────────────────────────────────────────

# 1. Tab switching

@app.callback(
[Output(‘upload-section’, ‘style’),
Output(‘manual-section’, ‘style’),
Output(‘tab-upload’, ‘style’),
Output(‘tab-manual’, ‘style’)],
[Input(‘tab-upload’, ‘n_clicks’),
Input(‘tab-manual’, ‘n_clicks’)],
)
def switch_tabs(_u, _m):
show_upload = ctx.triggered_id != ‘tab-manual’
base = {‘padding’: ‘10px 20px’, ‘borderRadius’: ‘8px’, ‘cursor’: ‘pointer’,
‘fontSize’: ‘0.95em’, ‘fontWeight’: ‘600’,
‘transition’: ‘all 0.2s’, ‘touchAction’: ‘manipulation’}
active   = {**base, ‘border’: ‘none’,
‘backgroundColor’: COLORS[‘primary’], ‘color’: ‘white’}
inactive = {**base, ‘border’: f’2px solid {COLORS[“primary”]}’,
‘backgroundColor’: ‘white’, ‘color’: COLORS[‘primary’]}
if show_upload:
return {‘display’: ‘block’}, {‘display’: ‘none’}, active, inactive
return {‘display’: ‘none’}, {‘display’: ‘block’}, inactive, active

# 2. Data management

@app.callback(
[Output(‘stored-data’,    ‘data’),
Output(‘status-message’, ‘children’),
Output(‘status-message’, ‘style’),
Output(‘input-product’,  ‘value’),
Output(‘input-sales’,    ‘value’)],
[Input(‘add-data-btn’,   ‘n_clicks’),
Input(‘clear-data-btn’, ‘n_clicks’),
Input(‘upload-data’,    ‘contents’)],
[State(‘input-date’,    ‘date’),
State(‘input-product’, ‘value’),
State(‘input-sales’,   ‘value’),
State(‘stored-data’,   ‘data’),
State(‘upload-data’,   ‘filename’)],
prevent_initial_call=True,  # never fires on load → localStorage is preserved
)
def manage_data(add_clicks, clear_clicks, upload_contents,
date, product, sales, current_data, filename):

```
trigger = ctx.triggered_id

def ok_style():
    return {'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
            'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
            'backgroundColor': '#d1fae5', 'color': '#065f46',
            'border': f'1px solid {COLORS["success"]}'}

def err_style():
    return {'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
            'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
            'backgroundColor': '#fee2e2', 'color': '#991b1b',
            'border': f'1px solid {COLORS["danger"]}'}

# Upload
if trigger == 'upload-data':
    if not upload_contents or not filename:
        raise PreventUpdate
    uploaded = parse_uploaded_file(upload_contents, filename)
    if uploaded is not None and not uploaded.empty:
        return (uploaded.to_dict('records'),
                f'\u2705 Loaded {filename} \u2014 {len(uploaded)} rows',
                ok_style(), no_update, no_update)
    return (current_data,
            f'\u274c Could not parse "{filename}". Use CSV or Excel with date, product, sales columns.',
            err_style(), no_update, no_update)

# Add row
if trigger == 'add-data-btn':
    if not date or not product or str(product).strip() == '' or sales is None:
        return (current_data,
                f'\u274c Please fill in Date, Product and Sales ({CEDI}).',
                err_style(), product, sales)
    sales_val = float(sales)
    if sales_val < 0:
        return (current_data, '\u274c Sales value cannot be negative.',
                err_style(), product, sales)

    existing = records_to_df(current_data)
    if not existing.empty and pd.api.types.is_datetime64_any_dtype(existing['date']):
        existing = existing.copy()
        existing['date'] = existing['date'].dt.strftime('%Y-%m-%d')
    new_row = pd.DataFrame({
        'date':    [pd.to_datetime(date).strftime('%Y-%m-%d')],
        'product': [str(product).strip()],
        'sales':   [sales_val],
    })
    combined = pd.concat([existing, new_row], ignore_index=True)
    return (combined.to_dict('records'),
            f'\u2705 Added: {product.strip()} \u2014 {fmt_cedi(sales_val)} on {date}',
            ok_style(), '', None)

# Clear
if trigger == 'clear-data-btn':
    return [], '\u2705 All data cleared.', ok_style(), '', None

raise PreventUpdate
```

# 3. Dashboard rendering

@app.callback(
[Output(‘sales-line-chart’,     ‘figure’),
Output(‘product-bar-chart’,    ‘figure’),
Output(‘stats-cards’,          ‘children’),
Output(‘data-table-container’, ‘children’)],
Input(‘stored-data’, ‘data’),
)
def update_dashboard(stored_data):
“”“Fires on page load (reads localStorage) and on every data change.”””

```
data = records_to_df(stored_data)

# Stats
if data.empty:
    stats_cards = [html.Div(
        '\U0001f4ed No data yet \u2014 upload a file or enter records manually.',
        style={'color': '#6b7280', 'padding': '18px', 'textAlign': 'center',
               'gridColumn': '1 / -1', 'backgroundColor': COLORS['white'],
               'borderRadius': '12px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'},
    )]
else:
    s = data['sales'].dropna()
    stats_cards = [
        create_stat_card('Total Sales',  fmt_cedi(s.sum()),          '\U0001f4b0', COLORS['success']),
        create_stat_card('Average Sale', fmt_cedi(s.mean()),          '\U0001f4ca', COLORS['primary']),
        create_stat_card('Products',     str(data['product'].nunique()), '\U0001f3f7\ufe0f', COLORS['warning']),
        create_stat_card('Records',      str(len(data)),                  '\U0001f4dd', COLORS['secondary']),
    ]

# Line chart — one aggregated point per day
if data.empty:
    line_fig = empty_figure()
else:
    daily = (data.dropna(subset=['date', 'sales'])
                 .groupby('date', as_index=False)['sales']
                 .sum()
                 .sort_values('date'))
    if daily.empty:
        line_fig = empty_figure('No dated sales data to display')
    else:
        line_fig = px.line(daily, x='date', y='sales',
                           labels={'date': 'Date', 'sales': f'Sales ({CEDI})'})
        line_fig.update_traces(
            line_color=COLORS['primary'], line_width=2.5,
            mode='lines+markers',
            marker=dict(size=5, color=COLORS['primary'], line=dict(width=2, color='white')),
            fill='tozeroy', fillcolor='rgba(102,126,234,0.1)',
            hovertemplate=f'%{{x}}<br><b>{CEDI}%{{y:,.0f}}</b><extra></extra>',
        )
        line_fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            autosize=True, height=260,
            margin=dict(l=8, r=8, t=6, b=6),
            hovermode='x unified',
            xaxis=dict(showgrid=False, showline=True, linecolor='#e5e7eb',
                       tickfont=dict(size=10), fixedrange=True),
            yaxis=dict(showgrid=True, gridcolor='#f3f4f6', showline=False,
                       tickprefix=CEDI, tickfont=dict(size=10), fixedrange=True),
        )

# Bar chart — totals per product
if data.empty:
    bar_fig = empty_figure()
else:
    ps = (data.dropna(subset=['product', 'sales'])
              .groupby('product', as_index=False)['sales']
              .sum()
              .sort_values('sales', ascending=False)
              .head(10))
    if ps.empty:
        bar_fig = empty_figure('No valid product / sales data')
    else:
        bar_fig = px.bar(ps, x='product', y='sales',
                         labels={'product': 'Product', 'sales': f'Sales ({CEDI})'},
                         color='sales',
                         color_continuous_scale=[[0, COLORS['primary']], [1, COLORS['secondary']]])
        bar_fig.update_traces(
            hovertemplate=f'%{{x}}<br><b>{CEDI}%{{y:,.0f}}</b><extra></extra>',
        )
        bar_fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            autosize=True, height=260,
            margin=dict(l=8, r=8, t=6, b=6),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, showline=True, linecolor='#e5e7eb',
                       categoryorder='total descending',
                       tickfont=dict(size=10), fixedrange=True,
                       tickangle=-30),   # angled labels prevent overlap on small screens
            yaxis=dict(showgrid=True, gridcolor='#f3f4f6', showline=False,
                       tickprefix=CEDI, tickfont=dict(size=10), fixedrange=True),
        )

# Data table
if data.empty:
    table_content = html.Div(
        '\U0001f4ed No data to display.',
        style={'color': '#6b7280', 'textAlign': 'center', 'padding': '20px'},
    )
else:
    display = data.sort_values('date', ascending=False).copy()
    display['date']  = display['date'].dt.strftime('%Y-%m-%d')
    display['sales'] = display['sales'].round(2)

    col_labels = {'date': 'Date', 'product': 'Product', 'sales': f'Sales ({CEDI})'}
    columns = [{'name': col_labels.get(c, c.title()), 'id': c} for c in display.columns]

    table_content = html.Div([
        html.Div(
            id='table-header-row',
            style={'display': 'flex', 'justifyContent': 'space-between',
                   'alignItems': 'center', 'marginBottom': '12px',
                   'flexWrap': 'wrap', 'gap': '8px'},
            children=[
                html.H3('\U0001f4cb All Sales Data',
                        style={'color': COLORS['dark'], 'margin': '0', 'fontSize': '1.1em'}),
                html.Span(f'{len(data)} records',
                          style={'backgroundColor': COLORS['primary'], 'color': 'white',
                                 'padding': '3px 12px', 'borderRadius': '20px',
                                 'fontSize': '0.8em', 'fontWeight': '600'}),
            ],
        ),
        dash_table.DataTable(
            id='data-table',
            data=display.to_dict('records'),
            columns=columns,
            page_size=10,
            sort_action='native',
            filter_action='native',
            style_table={'overflowX': 'auto', 'minWidth': '100%',
                         'WebkitOverflowScrolling': 'touch'},
            style_cell={
                'textAlign': 'left', 'padding': '9px 12px',
                'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                'fontSize': '0.88em',
                'whiteSpace': 'nowrap',
                'minWidth': '80px',
            },
            style_header={
                'backgroundColor': COLORS['primary'], 'color': 'white',
                'fontWeight': '600', 'border': 'none', 'fontSize': '0.85em',
            },
            style_data={'border': '1px solid #e5e7eb'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9fafb'},
                {'if': {'column_id': 'sales'},
                 'textAlign': 'right', 'fontWeight': '600',
                 'fontFeatureSettings': '"tnum"'},
            ],
        ),
    ])

return line_fig, bar_fig, stats_cards, table_content
```

if **name** == ‘**main**’:
app.run_server(debug=True)