import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

CEDI = '\u20b5'  # ₵

app = Dash(
    __name__,
    meta_tags=[
        {'name': 'viewport', 'content': 'width=device-width, initial-scale=1'},
        {'name': 'mobile-web-app-capable', 'content': 'yes'},
        {'name': 'apple-mobile-web-app-capable', 'content': 'yes'},
    ],
)
server = app.server

COLORS = {
    'primary':   '#667eea',
    'secondary': '#764ba2',
    'success':   '#10b981',
    'warning':   '#f59e0b',
    'danger':    '#ef4444',
    'light':     '#f3f4f6',
    'dark':      '#1f2937',
    'white':     '#ffffff',
}

# Chart height used both in Python layout and CSS — single source of truth
CHART_H = 320

CSS = f"""
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 0; -webkit-text-size-adjust: 100%; overflow-x: hidden; }}

/* ── Header ── */
#app-header {{ padding: 28px 24px; text-align: center; }}
@media (max-width: 500px) {{
  #app-header {{ padding: 18px 14px; }}
  .hdr-title {{ font-size: 1.4em !important; }}
  .hdr-sub   {{ font-size: 0.85em !important; }}
}}

/* ── Main container ── */
#main-container {{ max-width: 1400px; margin: 0 auto; padding: 0 20px; }}
@media (max-width: 500px) {{ #main-container {{ padding: 0 12px; }} }}

/* ── Stats: 4-col → 2-col ── */
#stats-cards {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}}
@media (max-width: 860px) {{ #stats-cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }} }}

/* ── Charts: 2-col → 1-col ── */
#charts-row {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}}
@media (max-width: 760px) {{ #charts-row {{ grid-template-columns: 1fr; }} }}

/* Chart card: DO NOT clip — let it expand to fit the graph */
.chart-card {{
  background: white;
  border-radius: 14px;
  padding: 20px 20px 12px 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.07);
  min-width: 0;
}}

/* Graph wrapper: exact height, no overflow clipping */
.graph-wrap {{
  width: 100%;
  height: {CHART_H}px;
  position: relative;
}}

/* Plotly fills wrapper exactly */
.graph-wrap .js-plotly-plot,
.graph-wrap .plot-container,
.graph-wrap .svg-container {{
  width: 100% !important;
  height: 100% !important;
}}

/* ── Input card ── */
.input-card {{
  background: white;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.07);
  margin-bottom: 18px;
}}

/* ── Manual form: 4-col → 2-col → 1-col ── */
#manual-form-grid {{
  display: grid;
  grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) auto;
  gap: 14px;
  align-items: end;
  margin-bottom: 14px;
}}
#manual-form-grid > div {{ min-width: 0; }}
@media (max-width: 680px) {{ #manual-form-grid {{ grid-template-columns: minmax(0,1fr) minmax(0,1fr); }} }}
@media (max-width: 420px) {{ #manual-form-grid {{ grid-template-columns: 1fr; }} }}

/* Full-width buttons on mobile */
@media (max-width: 680px) {{
  #add-data-btn   {{ width: 100%; }}
  #clear-data-btn {{ width: 100%; margin-top: 6px; }}
}}

/* Tab buttons: stretch on tiny screens */
.tab-row {{ display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; }}
@media (max-width: 420px) {{
  .tab-row {{ gap: 8px; }}
  #tab-upload, #tab-manual {{ flex: 1; text-align: center; padding: 9px 6px !important; font-size: 0.85em !important; }}
}}

/* Stat cards */
.stat-card {{
  background: white;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  min-width: 0;
}}
@media (max-width: 500px) {{
  .stat-card {{ padding: 14px; }}
  .stat-val  {{ font-size: 1.35em !important; }}
  .stat-icon {{ font-size: 1.8em !important; }}
}}

/* DataTable: scroll on mobile */
.dash-spreadsheet-container {{ overflow-x: auto !important; -webkit-overflow-scrolling: touch; }}
.dash-cell div              {{ white-space: nowrap !important; }}

/* DatePicker width */
.DateInput, .DateInput_input, .SingleDatePickerInput {{ width: 100% !important; }}

/* Upload zone */
#upload-data {{ width: 100%; box-sizing: border-box; }}
@media (max-width: 500px) {{
  #upload-data {{ height: 110px !important; }}
  .upl-icon    {{ font-size: 2em !important; }}
  .upl-main    {{ font-size: 0.95em !important; }}
  .upl-sub     {{ font-size: 0.78em !important; }}
}}

/* Table header */
.tbl-hdr {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
@media (max-width: 420px) {{ .tbl-hdr {{ flex-direction: column; align-items: flex-start; }} }}
</style>
"""

app.index_string = (
    '<!DOCTYPE html>\n<html>\n  <head>\n'
    '    {%metas%}\n    <title>Sales Analytics</title>\n'
    '    {%favicon%}\n    {%css%}\n'
    + CSS +
    '  </head>\n  <body>\n    {%app_entry%}\n'
    '    <footer>{%config%}{%scripts%}{%renderer%}</footer>\n'
    '  </body>\n</html>'
)

# ── Data helpers ───────────────────────────────────────────────────────────────

def clean_col_names(df):
    """Remove \\r\\n and spaces from column names; prevents _X000D_ phantom columns."""
    df.columns = df.columns.str.replace(r'[\r\n]', '', regex=True).str.strip().str.lower()
    return df


def build_seed_data():
    fallback = pd.DataFrame({
        'date':    pd.date_range('2024-01-01', periods=10, freq='D').strftime('%Y-%m-%d').tolist(),
        'product': ['Product A', 'Product B', 'Product C'] * 3 + ['Product A'],
        'sales':   [100, 150, 200, 120, 180, 220, 140, 190, 230, 160],
    })
    for path, reader in [('data/sales.csv', pd.read_csv), ('data/sales.xlsx', pd.read_excel)]:
        if os.path.exists(path):
            try:
                d = reader(path)
                d = clean_col_names(d)
                for col in ['date', 'product', 'sales']:
                    if col not in d.columns:
                        d[col] = None
                d = d[['date', 'product', 'sales']].dropna(how='all')
                d['sales'] = pd.to_numeric(d['sales'], errors='coerce')
                d['date']  = pd.to_datetime(d['date'], errors='coerce').dt.strftime('%Y-%m-%d')
                return d.dropna(subset=['sales']).to_dict('records')
            except Exception:
                pass
    return fallback.to_dict('records')


SEED_DATA = build_seed_data()


def records_to_df(records):
    """JSON records → clean DataFrame with exactly [date, product, sales]."""
    if not records:
        return pd.DataFrame(columns=['date', 'product', 'sales'])
    df = pd.DataFrame(records)
    df = clean_col_names(df)
    for col in ['date', 'product', 'sales']:
        if col not in df.columns:
            df[col] = None
    df = df[['date', 'product', 'sales']].copy()
    df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
    df['date']  = pd.to_datetime(df['date'],  errors='coerce')
    df = df.dropna(subset=['sales'])
    df = df[df['product'].notna() & (df['product'].astype(str).str.strip() != '')]
    return df.reset_index(drop=True)


def parse_uploaded_file(contents, filename):
    if not contents or not filename:
        return None
    try:
        _ct, b64 = contents.split(',', 1)
        decoded  = base64.b64decode(b64)
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

# ── Shared inline styles ───────────────────────────────────────────────────────

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
LABEL_STYLE = {'display': 'block', 'marginBottom': '6px', 'fontWeight': '600',
               'color': COLORS['dark'], 'fontSize': '0.9em'}


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
                                         'fontWeight': '700', 'lineHeight': '1.1',
                                         'wordBreak': 'break-all'}),
                     ]),
                     html.Div(icon, className='stat-icon',
                              style={'fontSize': '2em', 'opacity': '0.2', 'flexShrink': '0'}),
                 ]),
    ])

# ── Layout ────────────────────────────────────────────────────────────────────

app.layout = html.Div(
    style={'backgroundColor': COLORS['light'], 'minHeight': '100vh',
           'margin': '0', 'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"},
    children=[

        dcc.Store(id='stored-data', storage_type='local', data=SEED_DATA),

        # Header
        html.Div(id='app-header', style={
            'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
            'color': 'white', 'boxShadow': '0 4px 14px rgba(102,126,234,0.3)',
            'marginBottom': '18px',
        }, children=[
            html.H1('\U0001f4ca Sales Analytics Dashboard', className='hdr-title',
                    style={'margin': '0', 'fontSize': '1.9em', 'fontWeight': '700'}),
            html.P(f'Track sales in Ghana Cedis ({CEDI}) \u2014 data saved in this browser',
                   className='hdr-sub',
                   style={'margin': '6px 0 0', 'fontSize': '0.95em', 'opacity': '0.88'}),
        ]),

        html.Div(id='main-container', children=[

            # ── Input card ────────────────────────────────────────────────────
            html.Div(className='input-card', children=[

                # Tabs
                html.Div(className='tab-row', children=[
                    html.Button('\U0001f4e4 Upload File', id='tab-upload', n_clicks=1,
                                style={**BTN_BASE, 'padding': '10px 20px',
                                       'backgroundColor': COLORS['primary'], 'color': 'white'}),
                    html.Button('\u270f\ufe0f Enter Manually', id='tab-manual', n_clicks=0,
                                style={**BTN_BASE, 'padding': '10px 20px',
                                       'border': f'2px solid {COLORS["primary"]}',
                                       'backgroundColor': 'white', 'color': COLORS['primary']}),
                ]),

                # Upload panel
                html.Div(id='upload-section', children=[
                    html.H3('\U0001f4e4 Upload Your Data',
                            style={'color': COLORS['dark'], 'fontSize': '1.2em', 'margin': '0 0 14px'}),
                    dcc.Upload(id='upload-data', multiple=False,
                               style={
                                   'height': '130px', 'borderWidth': '2px', 'borderStyle': 'dashed',
                                   'borderRadius': '10px', 'borderColor': COLORS['primary'],
                                   'backgroundColor': '#f9fafb', 'cursor': 'pointer',
                                   'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                                   'textAlign': 'center', 'WebkitTapHighlightColor': 'transparent',
                               },
                               children=html.Div([
                                   html.Div('\U0001f4c1', className='upl-icon',
                                            style={'fontSize': '2.2em', 'marginBottom': '6px'}),
                                   html.Div('Drag and Drop or Tap to Select', className='upl-main',
                                            style={'fontSize': '1em', 'fontWeight': '600'}),
                                   html.Div('CSV or Excel (.xlsx)', className='upl-sub',
                                            style={'fontSize': '0.82em', 'color': '#6b7280', 'marginTop': '3px'}),
                               ])),
                ]),

                # Manual panel
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

            # ── Stats ─────────────────────────────────────────────────────────
            html.Div(id='stats-cards'),

            # ── Charts ────────────────────────────────────────────────────────
            html.Div(id='charts-row', children=[

                html.Div(className='chart-card', children=[
                    html.H3('\U0001f4c8 Sales Trend',
                            style={'color': COLORS['dark'], 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                    html.P('Daily totals \u2014 all products',
                           style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                    # Wrapper div with explicit height — Plotly sizes itself to fill this
                    html.Div(className='graph-wrap', children=[
                        dcc.Graph(id='sales-line-chart',
                                  style={'height': '100%'},
                                  config={'displayModeBar': False, 'responsive': True}),
                    ]),
                ]),

                html.Div(className='chart-card', children=[
                    html.H3('\U0001f3c6 Top Products',
                            style={'color': COLORS['dark'], 'margin': '0 0 2px', 'fontSize': '1.1em'}),
                    html.P(f'Total {CEDI} by product (top 10)',
                           style={'color': '#9ca3af', 'fontSize': '0.78em', 'margin': '0 0 12px'}),
                    html.Div(className='graph-wrap', children=[
                        dcc.Graph(id='product-bar-chart',
                                  style={'height': '100%'},
                                  config={'displayModeBar': False, 'responsive': True}),
                    ]),
                ]),
            ]),

            # ── Data table ────────────────────────────────────────────────────
            html.Div(id='data-table-container',
                     style={'background': 'white', 'borderRadius': '14px', 'padding': '22px',
                            'boxShadow': '0 2px 10px rgba(0,0,0,0.07)', 'marginBottom': '24px'}),

            # Footer
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

# ── Callbacks ──────────────────────────────────────────────────────────────────

@app.callback(
    [Output('upload-section', 'style'),
     Output('manual-section', 'style'),
     Output('tab-upload', 'style'),
     Output('tab-manual', 'style')],
    [Input('tab-upload', 'n_clicks'), Input('tab-manual', 'n_clicks')],
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


@app.callback(
    [Output('stored-data',    'data'),
     Output('status-message', 'children'),
     Output('status-message', 'style'),
     Output('input-product',  'value'),
     Output('input-sales',    'value')],
    [Input('add-data-btn',   'n_clicks'),
     Input('clear-data-btn', 'n_clicks'),
     Input('upload-data',    'contents')],
    [State('input-date',    'date'),
     State('input-product', 'value'),
     State('input-sales',   'value'),
     State('stored-data',   'data'),
     State('upload-data',   'filename')],
    prevent_initial_call=True,
)
def manage_data(add_clicks, clear_clicks, upload_contents,
                date, product, sales, current_data, filename):

    trigger = ctx.triggered_id

    def ok(msg):
        return {'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
                'backgroundColor': '#d1fae5', 'color': '#065f46',
                'border': f'1px solid {COLORS["success"]}'}, msg

    def err(msg):
        return {'marginTop': '12px', 'padding': '10px 14px', 'borderRadius': '8px',
                'textAlign': 'center', 'fontSize': '0.9em', 'display': 'block',
                'backgroundColor': '#fee2e2', 'color': '#991b1b',
                'border': f'1px solid {COLORS["danger"]}'}, msg

    if trigger == 'upload-data':
        if not upload_contents or not filename:
            raise PreventUpdate
        uploaded = parse_uploaded_file(upload_contents, filename)
        if uploaded is not None and not uploaded.empty:
            sty, msg = ok(f'\u2705 Loaded {filename} \u2014 {len(uploaded)} rows')
            return uploaded.to_dict('records'), msg, sty, no_update, no_update
        sty, msg = err(f'\u274c Could not parse "{filename}". Use CSV/Excel with date, product, sales columns.')
        return current_data, msg, sty, no_update, no_update

    if trigger == 'add-data-btn':
        if not date or not product or not str(product).strip() or sales is None:
            sty, msg = err(f'\u274c Fill in all fields (Date, Product, Sales).')
            return current_data, msg, sty, product, sales
        v = float(sales)
        if v < 0:
            sty, msg = err('\u274c Sales cannot be negative.')
            return current_data, msg, sty, product, sales
        existing = records_to_df(current_data)
        if not existing.empty and pd.api.types.is_datetime64_any_dtype(existing['date']):
            existing = existing.copy()
            existing['date'] = existing['date'].dt.strftime('%Y-%m-%d')
        new_row = pd.DataFrame({
            'date':    [pd.to_datetime(date).strftime('%Y-%m-%d')],
            'product': [str(product).strip()],
            'sales':   [v],
        })
        combined = pd.concat([existing, new_row], ignore_index=True)
        sty, msg = ok(f'\u2705 Added {product.strip()} \u2014 {fmt_cedi(v)} on {date}')
        return combined.to_dict('records'), msg, sty, '', None

    if trigger == 'clear-data-btn':
        sty, msg = ok('\u2705 All data cleared.')
        return [], msg, sty, '', None

    raise PreventUpdate


@app.callback(
    [Output('sales-line-chart',     'figure'),
     Output('product-bar-chart',    'figure'),
     Output('stats-cards',          'children'),
     Output('data-table-container', 'children')],
    Input('stored-data', 'data'),
)
def update_dashboard(stored_data):
    data = records_to_df(stored_data)

    # ── Stats ──
    if data.empty:
        stats = [html.Div('📭 No data yet — upload a file or enter records manually.',
                          style={'color': '#6b7280', 'padding': '18px', 'textAlign': 'center',
                                 'gridColumn': '1 / -1', 'background': 'white',
                                 'borderRadius': '12px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.07)'})]
    else:
        s = data['sales'].dropna()
        stats = [
            stat_card('Total Sales',  fmt_cedi(s.sum()),           '\U0001f4b0', COLORS['success']),
            stat_card('Average Sale', fmt_cedi(s.mean()),           '\U0001f4ca', COLORS['primary']),
            stat_card('Products',     str(data['product'].nunique()),'\U0001f3f7\ufe0f', COLORS['warning']),
            stat_card('Records',      str(len(data)),                '\U0001f4dd', COLORS['secondary']),
        ]

    # ── Line chart ──
    if data.empty:
        line_fig = empty_fig()
    else:
        clean = data.dropna(subset=['date', 'sales']).copy()
        clean['_d'] = clean['date'].dt.normalize()  # snap to midnight → no time artifacts
        daily = (clean.groupby('_d', as_index=False)['sales']
                      .sum()
                      .rename(columns={'_d': 'date'})
                      .sort_values('date'))
        if daily.empty:
            line_fig = empty_fig()
        else:
            line_fig = px.line(daily, x='date', y='sales',
                               labels={'date': '', 'sales': ''})
            line_fig.update_traces(
                line_color=COLORS['primary'], line_width=2.5,
                mode='lines+markers',
                marker=dict(size=5, color=COLORS['primary'], line=dict(width=2, color='white')),
                fill='tozeroy', fillcolor='rgba(102,126,234,0.1)',
                hovertemplate=f'%{{x|%b %d}}<br><b>{CEDI}%{{y:,.0f}}</b><extra></extra>',
            )
            line_fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                height=CHART_H,
                margin=dict(l=60, r=12, t=8, b=40),
                hovermode='x unified',
                xaxis=dict(
                    showgrid=False, showline=True, linecolor='#e5e7eb',
                    tickformat='%b %d', tickfont=dict(size=10), fixedrange=True,
                    title=None,
                ),
                yaxis=dict(
                    showgrid=True, gridcolor='#f0f0f0', zeroline=False,
                    tickprefix=CEDI, tickfont=dict(size=10), fixedrange=True,
                    title=None,
                ),
            )

    # ── Bar chart ──
    if data.empty:
        bar_fig = empty_fig()
    else:
        ps = (data.dropna(subset=['product', 'sales'])
                  .groupby('product', as_index=False)['sales']
                  .sum()
                  .sort_values('sales', ascending=False)
                  .head(10))
        if ps.empty:
            bar_fig = empty_fig()
        else:
            bar_fig = px.bar(ps, x='product', y='sales',
                             labels={'product': '', 'sales': ''},
                             color='sales',
                             color_continuous_scale=[[0, COLORS['primary']], [1, COLORS['secondary']]])
            bar_fig.update_traces(
                hovertemplate=f'%{{x}}<br><b>{CEDI}%{{y:,.0f}}</b><extra></extra>',
            )
            bar_fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                height=CHART_H,
                margin=dict(l=60, r=12, t=8, b=56),
                coloraxis_showscale=False,
                xaxis=dict(
                    showgrid=False, showline=True, linecolor='#e5e7eb',
                    categoryorder='total descending',
                    tickfont=dict(size=10), fixedrange=True,
                    tickangle=-30, title=None,
                ),
                yaxis=dict(
                    showgrid=True, gridcolor='#f0f0f0', zeroline=False,
                    tickprefix=CEDI, tickfont=dict(size=10), fixedrange=True,
                    title=None,
                ),
            )

    # ── Table ──
    if data.empty:
        tbl = html.Div('📭 No data to display.',
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
                id='data-table',
                data=disp.to_dict('records'),
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


if __name__ == '__main__':
    app.run_server(debug=True)