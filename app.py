import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

app = Dash(__name__)
server = app.server

# ── Color scheme ──────────────────────────────────────────────────────────────

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

# ── Sample / seed data (used only if localStorage is empty on first visit) ────

def build_seed_data():
    """Return sample records as a list of dicts for dcc.Store seeding."""
    df = pd.DataFrame({
        'date':    pd.date_range('2024-01-01', periods=10, freq='D').strftime('%Y-%m-%d').tolist(),
        'product': ['Product A', 'Product B', 'Product C'] * 3 + ['Product A'],
        'sales':   [100, 150, 200, 120, 180, 220, 140, 190, 230, 160],
    })
    # Try to load from disk first
    for path, reader in [('data/sales.csv', pd.read_csv), ('data/sales.xlsx', pd.read_excel)]:
        if os.path.exists(path):
            try:
                disk_df = reader(path)
                disk_df.columns = disk_df.columns.str.strip().str.lower()
                for col in ['date', 'product', 'sales']:
                    if col not in disk_df.columns:
                        disk_df[col] = None
                disk_df = disk_df.dropna(how='all')
                disk_df['date'] = pd.to_datetime(disk_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
                return disk_df.to_dict('records')
            except Exception:
                pass
    return df.to_dict('records')


SEED_DATA = build_seed_data()

# ── Helpers ───────────────────────────────────────────────────────────────────

def records_to_df(records):
    """
    Safely convert stored JSON records to a clean DataFrame.
    - Ensures date is datetime, sales is float.
    - Drops rows where both product and sales are null.
    """
    if not records:
        return pd.DataFrame(columns=['date', 'product', 'sales'])

    df = pd.DataFrame(records)

    # Ensure required columns exist
    for col in ['date', 'product', 'sales']:
        if col not in df.columns:
            df[col] = None

    # Type coercion — JSON round-trips can turn numbers into strings
    df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
    df['date']  = pd.to_datetime(df['date'],  errors='coerce')

    # Drop rows with no useful data
    df = df.dropna(subset=['sales'])                          # must have a sales value
    df = df[df['product'].notna() & (df['product'].astype(str).str.strip() != '')]

    return df.reset_index(drop=True)


def parse_uploaded_file(contents, filename):
    """Parse a base64-encoded uploaded CSV or Excel file. Returns clean DataFrame or None."""
    if not contents or not filename:
        return None
    try:
        _content_type, content_string = contents.split(',', 1)
        decoded = base64.b64decode(content_string)

        if filename.lower().endswith('.csv'):
            raw = pd.read_csv(io.StringIO(decoded.decode('utf-8', errors='ignore')), skip_blank_lines=True)
        elif filename.lower().endswith(('.xlsx', '.xls')):
            raw = pd.read_excel(io.BytesIO(decoded))
        else:
            return None

        raw.columns = raw.columns.str.strip().str.lower()
        for col in ['date', 'product', 'sales']:
            if col not in raw.columns:
                raw[col] = None

        raw = raw.dropna(how='all')
        raw['sales'] = pd.to_numeric(raw['sales'], errors='coerce')
        raw['date']  = pd.to_datetime(raw['date'],  errors='coerce').dt.strftime('%Y-%m-%d')
        raw = raw.dropna(subset=['sales'])

        return raw
    except Exception as e:
        print(f'[parse_uploaded_file] error: {e}')
        return None


def df_to_store(df):
    """Convert DataFrame to JSON-serialisable records (dates as strings)."""
    out = df.copy()
    if 'date' in out.columns and pd.api.types.is_datetime64_any_dtype(out['date']):
        out['date'] = out['date'].dt.strftime('%Y-%m-%d')
    return out.to_dict('records')


def empty_figure(message='No data available<br>Upload a file or enter data manually'):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=14, color='#6b7280'),
                       xref='paper', yref='paper', x=0.5, y=0.5)
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                      height=320, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def create_stat_card(title, value, icon, color):
    return html.Div(
        style={
            'backgroundColor': COLORS['white'],
            'borderRadius': '12px',
            'padding': '20px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
            'borderLeft': f'4px solid {color}',
        },
        children=[html.Div(
            style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'},
            children=[
                html.Div([
                    html.Div(title, style={'color': '#6b7280', 'fontSize': '0.9em', 'marginBottom': '8px'}),
                    html.Div(value, style={'color': COLORS['dark'], 'fontSize': '1.8em', 'fontWeight': '700'}),
                ]),
                html.Div(icon, style={'fontSize': '2.5em', 'opacity': '0.3'}),
            ],
        )],
    )

# ── Layout ────────────────────────────────────────────────────────────────────

INPUT_STYLE = {
    'width': '100%', 'padding': '10px',
    'border': '2px solid #e5e7eb', 'borderRadius': '8px',
    'fontSize': '1em', 'boxSizing': 'border-box', 'outline': 'none',
}
LABEL_STYLE = {'display': 'block', 'marginBottom': '5px', 'fontWeight': '600', 'color': COLORS['dark']}

app.layout = html.Div(
    style={'backgroundColor': COLORS['light'], 'minHeight': '100vh', 'margin': '0',
           'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"},
    children=[

        # ── Persistent browser store ───────────────────────────────────────────
        # storage_type='local' → survives page refresh (localStorage).
        # `data=SEED_DATA` is only used when localStorage has NO existing value
        # for this store's key (i.e. first-ever visit). Subsequent loads use
        # whatever the browser has saved, so user data is never blown away.
        dcc.Store(id='stored-data', storage_type='local', data=SEED_DATA),

        # ── Header ─────────────────────────────────────────────────────────────
        html.Div(
            style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                'padding': '30px 40px', 'color': COLORS['white'],
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)', 'marginBottom': '30px',
            },
            children=[
                html.H1('📊 Sales Analytics Dashboard',
                        style={'margin': '0', 'fontSize': '2.5em', 'fontWeight': '700', 'textAlign': 'center'}),
                html.P('Upload files or enter data manually — your data is saved in this browser',
                       style={'margin': '10px 0 0 0', 'fontSize': '1.1em', 'textAlign': 'center', 'opacity': '0.9'}),
            ],
        ),

        # ── Main container ──────────────────────────────────────────────────────
        html.Div(style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '0 20px'}, children=[

            # ── Input card ────────────────────────────────────────────────────
            html.Div(
                style={'backgroundColor': COLORS['white'], 'borderRadius': '15px',
                       'padding': '30px', 'marginBottom': '30px',
                       'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'},
                children=[

                    # Tab buttons
                    html.Div(
                        style={'display': 'flex', 'gap': '10px', 'marginBottom': '25px',
                               'borderBottom': '2px solid #e5e7eb', 'paddingBottom': '10px'},
                        children=[
                            html.Button('📤 Upload File', id='tab-upload', n_clicks=1,
                                        style={'padding': '12px 25px', 'border': 'none',
                                               'borderRadius': '8px', 'cursor': 'pointer',
                                               'fontSize': '1em', 'fontWeight': '600',
                                               'backgroundColor': COLORS['primary'], 'color': 'white'}),
                            html.Button('✏️ Enter Manually', id='tab-manual', n_clicks=0,
                                        style={'padding': '12px 25px',
                                               'border': f'2px solid {COLORS["primary"]}',
                                               'borderRadius': '8px', 'cursor': 'pointer',
                                               'fontSize': '1em', 'fontWeight': '600',
                                               'backgroundColor': 'white', 'color': COLORS['primary']}),
                        ],
                    ),

                    # Upload section
                    html.Div(id='upload-section', children=[
                        html.H3('📤 Upload Your Data',
                                style={'color': COLORS['dark'], 'marginBottom': '20px', 'fontSize': '1.5em'}),
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.Div('📁', style={'fontSize': '3em', 'marginBottom': '10px'}),
                                html.Div('Drag and Drop or Click to Select',
                                         style={'fontSize': '1.2em', 'fontWeight': '600'}),
                                html.Div('Supports CSV and Excel (.xlsx) files',
                                         style={'fontSize': '0.9em', 'color': '#6b7280', 'marginTop': '5px'}),
                            ]),
                            style={
                                'width': '100%', 'height': '150px', 'boxSizing': 'border-box',
                                'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
                                'borderColor': COLORS['primary'], 'textAlign': 'center',
                                'backgroundColor': '#f9fafb', 'cursor': 'pointer',
                                'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                            },
                            multiple=False,
                        ),
                    ]),

                    # Manual entry section
                    html.Div(id='manual-section', style={'display': 'none'}, children=[
                        html.H3('✏️ Enter Sales Data',
                                style={'color': COLORS['dark'], 'marginBottom': '20px', 'fontSize': '1.5em'}),
                        html.Div(
                            style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr 1fr auto',
                                   'gap': '15px', 'alignItems': 'end', 'marginBottom': '20px'},
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
                                              placeholder='Enter product name', style=INPUT_STYLE),
                                ]),
                                html.Div([
                                    html.Label('Sales ($)', style=LABEL_STYLE),
                                    dcc.Input(id='input-sales', type='number', min=0,
                                              placeholder='Enter amount', style=INPUT_STYLE),
                                ]),
                                html.Button('➕ Add', id='add-data-btn', n_clicks=0,
                                            style={'padding': '10px 25px', 'backgroundColor': COLORS['success'],
                                                   'color': 'white', 'border': 'none', 'borderRadius': '8px',
                                                   'cursor': 'pointer', 'fontSize': '1em', 'fontWeight': '600'}),
                            ],
                        ),
                        html.Button('🗑️ Clear All Data', id='clear-data-btn', n_clicks=0,
                                    style={'padding': '10px 20px', 'backgroundColor': COLORS['danger'],
                                           'color': 'white', 'border': 'none', 'borderRadius': '8px',
                                           'cursor': 'pointer', 'fontSize': '0.9em', 'fontWeight': '600'}),
                    ]),

                    # Status message
                    html.Div(id='status-message',
                             style={'marginTop': '15px', 'padding': '12px', 'borderRadius': '8px',
                                    'textAlign': 'center', 'fontSize': '0.95em', 'display': 'none'}),
                ],
            ),

            # ── Stats cards ───────────────────────────────────────────────────
            html.Div(id='stats-cards',
                     style={'display': 'grid',
                            'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))',
                            'gap': '20px', 'marginBottom': '30px'}),

            # ── Charts row ────────────────────────────────────────────────────
            html.Div(
                style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(480px, 1fr))',
                       'gap': '20px', 'marginBottom': '30px'},
                children=[
                    html.Div(
                        style={'backgroundColor': COLORS['white'], 'borderRadius': '15px',
                               'padding': '25px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'},
                        children=[
                            html.H3('📈 Sales Trend',
                                    style={'color': COLORS['dark'], 'marginBottom': '5px', 'fontSize': '1.3em'}),
                            html.P('Daily totals across all products',
                                   style={'color': '#9ca3af', 'fontSize': '0.85em', 'marginBottom': '15px', 'marginTop': '2px'}),
                            dcc.Graph(id='sales-line-chart', config={'displayModeBar': False}),
                        ],
                    ),
                    html.Div(
                        style={'backgroundColor': COLORS['white'], 'borderRadius': '15px',
                               'padding': '25px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'},
                        children=[
                            html.H3('🏆 Top Products',
                                    style={'color': COLORS['dark'], 'marginBottom': '5px', 'fontSize': '1.3em'}),
                            html.P('Total sales by product (top 10)',
                                   style={'color': '#9ca3af', 'fontSize': '0.85em', 'marginBottom': '15px', 'marginTop': '2px'}),
                            dcc.Graph(id='product-bar-chart', config={'displayModeBar': False}),
                        ],
                    ),
                ],
            ),

            # ── Data table ────────────────────────────────────────────────────
            html.Div(id='data-table-container',
                     style={'backgroundColor': COLORS['white'], 'borderRadius': '15px',
                            'padding': '25px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                            'marginBottom': '30px'}),

            # ── Footer ────────────────────────────────────────────────────────
            html.Div(
                style={'textAlign': 'center', 'padding': '20px', 'color': '#6b7280', 'fontSize': '0.9em'},
                children=[html.Ul(
                    html.Li(html.A('William Thompson', href='https://yooku98.github.io/web')),
                    style={'listStyle': 'none', 'padding': 0, 'margin': 0},
                )],
            ),
        ]),
    ],
)

# ── Callbacks ─────────────────────────────────────────────────────────────────

# ── 1. Tab switching ──────────────────────────────────────────────────────────

@app.callback(
    [Output('upload-section', 'style'),
     Output('manual-section', 'style'),
     Output('tab-upload', 'style'),
     Output('tab-manual', 'style')],
    [Input('tab-upload', 'n_clicks'),
     Input('tab-manual', 'n_clicks')],
)
def switch_tabs(_upload_clicks, _manual_clicks):
    """Show the tab whose button was clicked most recently."""
    show_upload = ctx.triggered_id != 'tab-manual'  # defaults to upload on load

    active = {'padding': '12px 25px', 'border': 'none', 'borderRadius': '8px',
               'cursor': 'pointer', 'fontSize': '1em', 'fontWeight': '600',
               'backgroundColor': COLORS['primary'], 'color': 'white', 'transition': 'all 0.3s'}
    inactive = {'padding': '12px 25px', 'border': f'2px solid {COLORS["primary"]}',
                'borderRadius': '8px', 'cursor': 'pointer', 'fontSize': '1em', 'fontWeight': '600',
                'backgroundColor': 'white', 'color': COLORS['primary'], 'transition': 'all 0.3s'}

    if show_upload:
        return {'display': 'block'}, {'display': 'none'}, active, inactive
    return {'display': 'none'}, {'display': 'block'}, inactive, active


# ── 2. Data management → stored-data ─────────────────────────────────────────

@app.callback(
    [Output('stored-data',     'data'),
     Output('status-message',  'children'),
     Output('status-message',  'style'),
     Output('input-product',   'value'),
     Output('input-sales',     'value')],
    [Input('add-data-btn',  'n_clicks'),
     Input('clear-data-btn','n_clicks'),
     Input('upload-data',   'contents')],
    [State('input-date',    'date'),
     State('input-product', 'value'),
     State('input-sales',   'value'),
     State('stored-data',   'data'),
     State('upload-data',   'filename')],
    prevent_initial_call=True,   # never fires on page load — preserves localStorage
)
def manage_data(add_clicks, clear_clicks, upload_contents,
                date, product, sales, current_data, filename):
    """
    Single source of truth for all data mutations.
    prevent_initial_call=True ensures this never fires on app startup,
    which would otherwise overwrite the user's persisted localStorage data.
    """

    trigger = ctx.triggered_id

    def ok_style():
        return {'marginTop': '15px', 'padding': '12px', 'borderRadius': '8px',
                'textAlign': 'center', 'fontSize': '0.95em', 'display': 'block',
                'backgroundColor': '#d1fae5', 'color': '#065f46',
                'border': f'1px solid {COLORS["success"]}'}

    def err_style():
        return {'marginTop': '15px', 'padding': '12px', 'borderRadius': '8px',
                'textAlign': 'center', 'fontSize': '0.95em', 'display': 'block',
                'backgroundColor': '#fee2e2', 'color': '#991b1b',
                'border': f'1px solid {COLORS["danger"]}'}

    # ── Upload ──
    if trigger == 'upload-data':
        if not upload_contents or not filename:
            raise PreventUpdate
        uploaded = parse_uploaded_file(upload_contents, filename)
        if uploaded is not None and not uploaded.empty:
            return (
                uploaded.to_dict('records'),
                f'✅ Loaded {filename} — {len(uploaded)} rows',
                ok_style(), no_update, no_update,
            )
        return (
            current_data,
            f'❌ Could not parse "{filename}". Use a CSV or Excel file with date, product, sales columns.',
            err_style(), no_update, no_update,
        )

    # ── Add row ──
    if trigger == 'add-data-btn':
        if not date or not product or str(product).strip() == '' or sales is None:
            return (current_data, '❌ Please fill in all fields (Date, Product, Sales).',
                    err_style(), product, sales)

        sales_val = float(sales)
        if sales_val < 0:
            return (current_data, '❌ Sales value cannot be negative.',
                    err_style(), product, sales)

        existing = records_to_df(current_data)
        # Normalise existing dates back to strings so concat doesn't create mixed types
        if not existing.empty and pd.api.types.is_datetime64_any_dtype(existing['date']):
            existing = existing.copy()
            existing['date'] = existing['date'].dt.strftime('%Y-%m-%d')
        new_row = pd.DataFrame({
            'date':    [pd.to_datetime(date).strftime('%Y-%m-%d')],
            'product': [str(product).strip()],
            'sales':   [sales_val],
        })
        combined = pd.concat([existing, new_row], ignore_index=True)
        return (
            combined.to_dict('records'),
            f'✅ Added: {product.strip()} — ${sales_val:,.2f} on {date}',
            ok_style(), '', None,
        )

    # ── Clear ──
    if trigger == 'clear-data-btn':
        return [], '✅ All data cleared.', ok_style(), '', None

    raise PreventUpdate


# ── 3. Dashboard rendering ────────────────────────────────────────────────────

@app.callback(
    [Output('sales-line-chart',     'figure'),
     Output('product-bar-chart',    'figure'),
     Output('stats-cards',          'children'),
     Output('data-table-container', 'children')],
    Input('stored-data', 'data'),
)
def update_dashboard(stored_data):
    """
    Re-renders all visuals whenever stored-data changes.
    This fires on page load too (reading existing localStorage), so charts are
    always in sync with persisted data immediately on arrival.
    """

    data = records_to_df(stored_data)   # clean, type-safe DataFrame

    # ── Stats ──────────────────────────────────────────────────────────────────
    if data.empty:
        stats_cards = [html.Div(
            '📭 No data yet — upload a file or enter records manually.',
            style={'color': '#6b7280', 'padding': '20px', 'textAlign': 'center',
                   'gridColumn': '1 / -1'},
        )]
    else:
        valid_sales = data['sales'].dropna()
        stats_cards = [
            create_stat_card('Total Sales',   f"${valid_sales.sum():,.0f}",   '💰', COLORS['success']),
            create_stat_card('Average Sale',  f"${valid_sales.mean():,.0f}",  '📊', COLORS['primary']),
            create_stat_card('Products',      str(data['product'].nunique()),  '🏷️', COLORS['warning']),
            create_stat_card('Records',       str(len(data)),                  '📝', COLORS['secondary']),
        ]

    # ── Line chart — aggregate by date so one point per day ───────────────────
    if data.empty or 'date' not in data.columns:
        line_fig = empty_figure()
    else:
        daily = (
            data.dropna(subset=['date', 'sales'])
                .groupby('date', as_index=False)['sales']
                .sum()
                .sort_values('date')
        )
        if daily.empty:
            line_fig = empty_figure('No dated sales data to display')
        else:
            line_fig = px.line(
                daily, x='date', y='sales',
                labels={'date': 'Date', 'sales': 'Total Sales ($)'},
            )
            line_fig.update_traces(
                line_color=COLORS['primary'], line_width=3,
                mode='lines+markers',
                marker=dict(size=6, color=COLORS['primary'], line=dict(width=2, color='white')),
                fill='tozeroy', fillcolor='rgba(102,126,234,0.1)',
                hovertemplate='%{x}<br><b>$%{y:,.0f}</b><extra></extra>',
            )
            line_fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                height=320, margin=dict(l=10, r=10, t=10, b=10),
                hovermode='x unified',
                xaxis=dict(showgrid=False, showline=True, linecolor='#e5e7eb',
                           tickfont=dict(size=11)),
                yaxis=dict(showgrid=True, gridcolor='#f3f4f6', showline=False,
                           tickprefix='$', tickfont=dict(size=11)),
            )

    # ── Bar chart — aggregate by product ──────────────────────────────────────
    if data.empty or 'product' not in data.columns:
        bar_fig = empty_figure()
    else:
        product_sales = (
            data.dropna(subset=['product', 'sales'])
                .groupby('product', as_index=False)['sales']
                .sum()
                .sort_values('sales', ascending=False)
                .head(10)
        )
        if product_sales.empty:
            bar_fig = empty_figure('No valid product / sales data')
        else:
            bar_fig = px.bar(
                product_sales, x='product', y='sales',
                labels={'product': 'Product', 'sales': 'Total Sales ($)'},
                color='sales',
                color_continuous_scale=[[0, COLORS['primary']], [1, COLORS['secondary']]],
            )
            bar_fig.update_traces(
                hovertemplate='%{x}<br><b>$%{y:,.0f}</b><extra></extra>',
            )
            bar_fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                height=320, margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                xaxis=dict(showgrid=False, showline=True, linecolor='#e5e7eb',
                           categoryorder='total descending', tickfont=dict(size=11)),
                yaxis=dict(showgrid=True, gridcolor='#f3f4f6', showline=False,
                           tickprefix='$', tickfont=dict(size=11)),
            )

    # ── Data table ────────────────────────────────────────────────────────────
    if data.empty:
        data_table_content = html.Div(
            '📭 No data to display.',
            style={'color': '#6b7280', 'textAlign': 'center', 'padding': '20px'},
        )
    else:
        # Build display copy with formatted date strings
        display = data.sort_values('date', ascending=False).copy()
        display['date']  = display['date'].dt.strftime('%Y-%m-%d')
        display['sales'] = display['sales'].round(2)

        data_table_content = html.Div([
            html.Div(
                style={'display': 'flex', 'justifyContent': 'space-between',
                       'alignItems': 'center', 'marginBottom': '15px'},
                children=[
                    html.H3(f'📋 All Sales Data',
                            style={'color': COLORS['dark'], 'margin': '0', 'fontSize': '1.3em'}),
                    html.Span(f'{len(data)} records',
                              style={'backgroundColor': COLORS['primary'], 'color': 'white',
                                     'padding': '4px 12px', 'borderRadius': '20px', 'fontSize': '0.85em'}),
                ],
            ),
            dash_table.DataTable(
                id='data-table',
                data=display.to_dict('records'),
                columns=[{'name': col.title(), 'id': col} for col in display.columns],
                page_size=10,
                sort_action='native',       # allow column sorting
                filter_action='native',     # allow column filtering
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left', 'padding': '12px',
                    'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                    'fontSize': '0.95em',
                },
                style_header={
                    'backgroundColor': COLORS['primary'], 'color': 'white',
                    'fontWeight': '600', 'border': 'none',
                },
                style_data={'border': '1px solid #e5e7eb'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9fafb'},
                    {'if': {'column_id': 'sales'}, 'textAlign': 'right', 'fontWeight': '600'},
                ],
            ),
        ])

    return line_fig, bar_fig, stats_cards, data_table_content


if __name__ == '__main__':
    app.run_server(debug=True)