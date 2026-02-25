import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ALL
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dash import ctx

app = Dash(__name__)
server = app.server

@app.callback(
    Output("data-store", "data"),
    [
        Input("upload-data", "contents"),
        Input("manual-table", "data"),
        Input("add-row-btn", "n_clicks"),
        Input("clear-data-btn", "n_clicks")
    ],
    State("upload-data", "filename"),
    State("data-store", "data"),
)
def update_storage(contents, manual_data, add_row_clicks, clear_clicks, filename, stored_data):
    trigger = ctx.triggered_id

    # ---------------------------------------------------
    # CLEAR BUTTON
    # ---------------------------------------------------
    if trigger == "clear-data-btn":
        return []

    # ---------------------------------------------------
    # ADD ROW (just adds empty rows to the manual table, not stored yet)
    # You'll process manual_data below anyway
    # ---------------------------------------------------
    if trigger == "add-row-btn":
        return manual_data

    # ---------------------------------------------------
    # UPLOAD FILE
    # ---------------------------------------------------
    if trigger == "upload-data" and contents is not None:
        df = parse_uploaded_file(contents, filename)
        if df is not None:
            return df.to_dict("records")
        return stored_data

    # ---------------------------------------------------
    # MANUAL INPUT TABLE
    # ---------------------------------------------------
    if trigger == "manual-table":
        if manual_data is not None:
            df = pd.DataFrame(manual_data)
            df = df.dropna(how="all")  # drop fully empty rows
            return df.to_dict("records")

    # Default
    return stored_data

DATA_PATH = "data"
csv_path = os.path.join(DATA_PATH, "sales.csv")
excel_path = os.path.join(DATA_PATH, "sales.xlsx")

def load_initial_data():
    """Load initial data from existing files"""
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    elif os.path.exists(excel_path):
        return pd.read_excel(excel_path)
    else:
        # Return sample data if no file exists
        return pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'product': ['Product A', 'Product B', 'Product C'] * 3 + ['Product A'],
            'sales': [100, 150, 200, 120, 180, 220, 140, 190, 230, 160]
        })

df = load_initial_data()

# Modern color scheme
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'light': '#f3f4f6',
    'dark': '#1f2937',
    'white': '#ffffff'
}

# Layout
app.layout = html.Div(
    style={
        'backgroundColor': COLORS['light'],
        'minHeight': '100vh',
        'padding': '0',
        'margin': '0',
        'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
    },
    children=[
        # Hidden div to store data
        dcc.Store(id='stored-data', data=df.to_dict('records')),
        
        # Header
        html.Div(
            style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                'padding': '30px 40px',
                'color': COLORS['white'],
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                'marginBottom': '30px'
            },
            children=[
                html.H1(
                    "📊 Sales Analytics Dashboard",
                    style={
                        'margin': '0',
                        'fontSize': '2.5em',
                        'fontWeight': '700',
                        'textAlign': 'center'
                    }
                ),
                html.P(
                    "Upload files or enter data manually to visualize insights instantly",
                    style={
                        'margin': '10px 0 0 0',
                        'fontSize': '1.1em',
                        'textAlign': 'center',
                        'opacity': '0.9'
                    }
                )
            ]
        ),

        # Main Content Container
        html.Div(
            style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '0 20px'},
            children=[
                # Input Methods Tabs
                html.Div(
                    style={
                        'backgroundColor': COLORS['white'],
                        'borderRadius': '15px',
                        'padding': '30px',
                        'marginBottom': '30px',
                        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
                    },
                    children=[
                        # Tab Buttons
                        html.Div(
                            style={
                                'display': 'flex',
                                'gap': '10px',
                                'marginBottom': '25px',
                                'borderBottom': '2px solid #e5e7eb',
                                'paddingBottom': '10px'
                            },
                            children=[
                                html.Button(
                                    "📤 Upload File",
                                    id="tab-upload",
                                    n_clicks=0,
                                    style={
                                        'padding': '12px 25px',
                                        'border': 'none',
                                        'borderRadius': '8px',
                                        'cursor': 'pointer',
                                        'fontSize': '1em',
                                        'fontWeight': '600',
                                        'backgroundColor': COLORS['primary'],
                                        'color': 'white',
                                        'transition': 'all 0.3s'
                                    }
                                ),
                                html.Button(
                                    "✏️ Enter Manually",
                                    id="tab-manual",
                                    n_clicks=0,
                                    style={
                                        'padding': '12px 25px',
                                        'border': f'2px solid {COLORS["primary"]}',
                                        'borderRadius': '8px',
                                        'cursor': 'pointer',
                                        'fontSize': '1em',
                                        'fontWeight': '600',
                                        'backgroundColor': 'white',
                                        'color': COLORS['primary'],
                                        'transition': 'all 0.3s'
                                    }
                                )
                            ]
                        ),
                        
                        # Upload Section
                        html.Div(
                            id="upload-section",
                            children=[
                                html.H3(
                                    "📤 Upload Your Data",
                                    style={
                                        'color': COLORS['dark'],
                                        'marginBottom': '20px',
                                        'fontSize': '1.5em'
                                    }
                                ),
                                dcc.Upload(
                                    id="upload-data",
                                    children=html.Div([
                                        html.Div(
                                            "📁",
                                            style={'fontSize': '3em', 'marginBottom': '10px'}
                                        ),
                                        html.Div(
                                            "Drag and Drop or Click to Select",
                                            style={'fontSize': '1.2em', 'fontWeight': '600'}
                                        ),
                                        html.Div(
                                            "Supports CSV and Excel (.xlsx) files",
                                            style={
                                                'fontSize': '0.9em',
                                                'color': '#6b7280',
                                                'marginTop': '5px'
                                            }
                                        )
                                    ]),
                                    style={
                                        'width': '100%',
                                        'height': '150px',
                                        'lineHeight': 'normal',
                                        'borderWidth': '2px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '10px',
                                        'borderColor': COLORS['primary'],
                                        'textAlign': 'center',
                                        'backgroundColor': '#f9fafb',
                                        'cursor': 'pointer',
                                        'display': 'flex',
                                        'alignItems': 'center',
                                        'justifyContent': 'center',
                                        'transition': 'all 0.3s ease'
                                    },
                                    multiple=False
                                ),
                            ]
                        ),
                        
                        # Manual Entry Section
                        html.Div(
                            id="manual-section",
                            style={'display': 'none'},
                            children=[
                                html.H3(
                                    "✏️ Enter Sales Data",
                                    style={
                                        'color': COLORS['dark'],
                                        'marginBottom': '20px',
                                        'fontSize': '1.5em'
                                    }
                                ),
                                
                                # Input Form
                                html.Div(
                                    style={
                                        'display': 'grid',
                                        'gridTemplateColumns': '1fr 1fr 1fr auto',
                                        'gap': '15px',
                                        'alignItems': 'end',
                                        'marginBottom': '20px'
                                    },
                                    children=[
                                        html.Div([
                                            html.Label(
                                                "Date",
                                                style={
                                                    'display': 'block',
                                                    'marginBottom': '5px',
                                                    'fontWeight': '600',
                                                    'color': COLORS['dark']
                                                }
                                            ),
                                            dcc.DatePickerSingle(
                                                id='input-date',
                                                date=datetime.today().strftime('%Y-%m-%d'),
                                                display_format='YYYY-MM-DD',
                                                style={'width': '100%'}
                                            )
                                        ]),
                                        html.Div([
                                            html.Label(
                                                "Product",
                                                style={
                                                    'display': 'block',
                                                    'marginBottom': '5px',
                                                    'fontWeight': '600',
                                                    'color': COLORS['dark']
                                                }
                                            ),
                                            dcc.Input(
                                                id='input-product',
                                                type='text',
                                                placeholder='Enter product name',
                                                style={
                                                    'width': '100%',
                                                    'padding': '10px',
                                                    'border': '2px solid #e5e7eb',
                                                    'borderRadius': '8px',
                                                    'fontSize': '1em'
                                                }
                                            )
                                        ]),
                                        html.Div([
                                            html.Label(
                                                "Sales ($)",
                                                style={
                                                    'display': 'block',
                                                    'marginBottom': '5px',
                                                    'fontWeight': '600',
                                                    'color': COLORS['dark']
                                                }
                                            ),
                                            dcc.Input(
                                                id='input-sales',
                                                type='number',
                                                placeholder='Enter amount',
                                                style={
                                                    'width': '100%',
                                                    'padding': '10px',
                                                    'border': '2px solid #e5e7eb',
                                                    'borderRadius': '8px',
                                                    'fontSize': '1em'
                                                }
                                            )
                                        ]),
                                        html.Button(
                                            "➕ Add",
                                            id='add-data-btn',
                                            n_clicks=0,
                                            style={
                                                'padding': '10px 25px',
                                                'backgroundColor': COLORS['success'],
                                                'color': 'white',
                                                'border': 'none',
                                                'borderRadius': '8px',
                                                'cursor': 'pointer',
                                                'fontSize': '1em',
                                                'fontWeight': '600',
                                                'transition': 'all 0.3s'
                                            }
                                        )
                                    ]
                                ),
                                
                                # Clear Data Button
                                html.Button(
                                    "🗑️ Clear All Data",
                                    id='clear-data-btn',
                                    n_clicks=0,
                                    style={
                                        'padding': '10px 20px',
                                        'backgroundColor': COLORS['danger'],
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '8px',
                                        'cursor': 'pointer',
                                        'fontSize': '0.9em',
                                        'fontWeight': '600',
                                        'marginTop': '10px'
                                    }
                                )
                            ]
                        ),
                        
                        # Status Message
                        html.Div(
                            id="status-message",
                            style={
                                'marginTop': '15px',
                                'padding': '12px',
                                'borderRadius': '8px',
                                'textAlign': 'center',
                                'fontSize': '0.95em',
                                'display': 'none'
                            }
                        )
                    ]
                ),

                # Stats Cards Row
                html.Div(
                    id="stats-cards",
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(250px, 1fr))',
                        'gap': '20px',
                        'marginBottom': '30px'
                    }
                ),

                # Charts Row
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(500px, 1fr))',
                        'gap': '20px',
                        'marginBottom': '30px'
                    },
                    children=[
                        # Sales Line Chart Card
                        html.Div(
                            style={
                                'backgroundColor': COLORS['white'],
                                'borderRadius': '15px',
                                'padding': '25px',
                                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
                            },
                            children=[
                                html.H3(
                                    "📈 Sales Trend",
                                    style={
                                        'color': COLORS['dark'],
                                        'marginBottom': '20px',
                                        'fontSize': '1.3em'
                                    }
                                ),
                                dcc.Graph(id="sales-line-chart", config={'displayModeBar': False})
                            ]
                        ),

                        # Product Bar Chart Card
                        html.Div(
                            style={
                                'backgroundColor': COLORS['white'],
                                'borderRadius': '15px',
                                'padding': '25px',
                                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
                            },
                            children=[
                                html.H3(
                                    "🏆 Top Products",
                                    style={
                                        'color': COLORS['dark'],
                                        'marginBottom': '20px',
                                        'fontSize': '1.3em'
                                    }
                                ),
                                dcc.Graph(id="product-bar-chart", config={'displayModeBar': False})
                            ]
                        )
                    ]
                ),
                
                # Data Table Section
                html.Div(
                    id="data-table-container",
                    style={
                        'backgroundColor': COLORS['white'],
                        'borderRadius': '15px',
                        'padding': '25px',
                        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
                        'marginBottom': '30px'
                    }
                ),

                # Footer
                html.Div(
                    style={
                        'textAlign': 'center',
                        'padding': '20px',
                        'color': '#6b7280',
                        'fontSize': '0.9em'
                    },
                    children=[
                        html.Li(html.A("William Thompson", href="https://yooku98.github.io/web"))
                    ]
                )
            ]
        )
    ]
)

# Tab switching callbacks
@app.callback(
    [Output('upload-section', 'style'),
     Output('manual-section', 'style'),
     Output('tab-upload', 'style'),
     Output('tab-manual', 'style')],
    [Input('tab-upload', 'n_clicks'),
     Input('tab-manual', 'n_clicks')]
)
def switch_tabs(upload_clicks, manual_clicks):
    """Switch between upload and manual entry tabs"""
    # Determine which tab was clicked last
    if upload_clicks > manual_clicks:
        return (
            {'display': 'block'},  # Show upload
            {'display': 'none'},   # Hide manual
            {
                'padding': '12px 25px',
                'border': 'none',
                'borderRadius': '8px',
                'cursor': 'pointer',
                'fontSize': '1em',
                'fontWeight': '600',
                'backgroundColor': COLORS['primary'],
                'color': 'white'
            },
            {
                'padding': '12px 25px',
                'border': f'2px solid {COLORS["primary"]}',
                'borderRadius': '8px',
                'cursor': 'pointer',
                'fontSize': '1em',
                'fontWeight': '600',
                'backgroundColor': 'white',
                'color': COLORS['primary']
            }
        )
    else:
        return (
            {'display': 'none'},   # Hide upload
            {'display': 'block'},  # Show manual
            {
                'padding': '12px 25px',
                'border': f'2px solid {COLORS["primary"]}',
                'borderRadius': '8px',
                'cursor': 'pointer',
                'fontSize': '1em',
                'fontWeight': '600',
                'backgroundColor': 'white',
                'color': COLORS['primary']
            },
            {
                'padding': '12px 25px',
                'border': 'none',
                'borderRadius': '8px',
                'cursor': 'pointer',
                'fontSize': '1em',
                'fontWeight': '600',
                'backgroundColor': COLORS['primary'],
                'color': 'white'
            }
        )

# Add/Clear data callbacks
@app.callback(
    [Output('stored-data', 'data'),
     Output('status-message', 'children'),
     Output('status-message', 'style'),
     Output('input-product', 'value'),
     Output('input-sales', 'value')],
    [Input('add-data-btn', 'n_clicks'),
     Input('clear-data-btn', 'n_clicks'),
     Input('upload-data', 'contents')],
    [State('input-date', 'date'),
     State('input-product', 'value'),
     State('input-sales', 'value'),
     State('stored-data', 'data'),
     State('upload-data', 'filename')]
)
def manage_data(add_clicks, clear_clicks, upload_contents, date, product, sales, current_data, filename):
    """Add new data or clear all data"""
    from dash.exceptions import PreventUpdate
    from dash import callback_context
    
    if not callback_context.triggered:
        raise PreventUpdate
    
    trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    
    # Load current data
    data_df = pd.DataFrame(current_data) if current_data else pd.DataFrame()
    
    # Handle file upload
    if trigger_id == 'upload-data' and upload_contents and filename:
        uploaded_df = parse_uploaded_file(upload_contents, filename)
        if uploaded_df is not None and not uploaded_df.empty:
            return (
                uploaded_df.to_dict('records'),
                f"✅ Successfully loaded: {filename} ({len(uploaded_df)} rows)",
                {
                    'marginTop': '15px',
                    'padding': '12px',
                    'borderRadius': '8px',
                    'textAlign': 'center',
                    'fontSize': '0.95em',
                    'backgroundColor': '#d1fae5',
                    'color': '#065f46',
                    'border': f'1px solid {COLORS["success"]}',
                    'display': 'block'
                },
                '', None
            )
    
    # Handle add data
    if trigger_id == 'add-data-btn' and add_clicks > 0:
        if not date or not product or sales is None:
            return (
                current_data,
                "❌ Please fill in all fields",
                {
                    'marginTop': '15px',
                    'padding': '12px',
                    'borderRadius': '8px',
                    'textAlign': 'center',
                    'fontSize': '0.95em',
                    'backgroundColor': '#fee2e2',
                    'color': '#991b1b',
                    'border': f'1px solid {COLORS["danger"]}',
                    'display': 'block'
                },
                product, sales
            )
        
        # Add new row
        new_row = pd.DataFrame({
            'date': [pd.to_datetime(date)],
            'product': [product],
            'sales': [float(sales)]
        })
        
        data_df = pd.concat([data_df, new_row], ignore_index=True)
        
        return (
            data_df.to_dict('records'),
            f"✅ Added: {product} - ${sales} on {date}",
            {
                'marginTop': '15px',
                'padding': '12px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'fontSize': '0.95em',
                'backgroundColor': '#d1fae5',
                'color': '#065f46',
                'border': f'1px solid {COLORS["success"]}',
                'display': 'block'
            },
            '', None  # Clear inputs
        )
    
    # Handle clear data
    if trigger_id == 'clear-data-btn' and clear_clicks > 0:
        return (
            [],
            "✅ All data cleared",
            {
                'marginTop': '15px',
                'padding': '12px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'fontSize': '0.95em',
                'backgroundColor': '#d1fae5',
                'color': '#065f46',
                'border': f'1px solid {COLORS["success"]}',
                'display': 'block'
            },
            '', None
        )
    
    raise PreventUpdate

def parse_uploaded_file(contents, filename):
    """Parse uploaded CSV or Excel file safely."""
    if not contents:
        return None

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        # Load file depending on extension
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8', errors='ignore')),
                skip_blank_lines=True
            )

        elif filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(decoded))

        else:
            return None

        # Clean columns
        df.columns = df.columns.str.strip().str.lower()

        # Force required columns to exist
        required = ['date', 'product', 'sales']
        for col in required:
            if col not in df.columns:
                df[col] = None  # Create empty col

        # Drop completely blank rows
        df = df.dropna(how='all')

        # Fix date column
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

        return df

    except Exception as e:
        print("File parse error:", e)
        return None

def create_stat_card(title, value, icon, color):
    """Create a statistics card"""
    return html.Div(
        style={
            'backgroundColor': COLORS['white'],
            'borderRadius': '12px',
            'padding': '20px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
            'borderLeft': f'4px solid {color}'
        },
        children=[
            html.Div(
                style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'},
                children=[
                    html.Div([
                        html.Div(
                            title,
                            style={
                                'color': '#6b7280',
                                'fontSize': '0.9em',
                                'marginBottom': '8px'
                            }
                        ),
                        html.Div(
                            value,
                            style={
                                'color': COLORS['dark'],
                                'fontSize': '1.8em',
                                'fontWeight': '700'
                            }
                        )
                    ]),
                    html.Div(
                        icon,
                        style={
                            'fontSize': '2.5em',
                            'opacity': '0.3'
                        }
                    )
                ]
            )
        ]
    )

@app.callback(
    [Output("sales-line-chart", "figure"),
     Output("product-bar-chart", "figure"),
     Output("stats-cards", "children"),
     Output("data-table-container", "children")],
    [Input("stored-data", "data")]
)
def update_dashboard(stored_data):
    """Update all dashboard components based on stored data"""
    
    # Convert stored data to DataFrame
    if stored_data:
        data = pd.DataFrame(stored_data)
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
    else:
        data = pd.DataFrame()
    
    # Create statistics cards
    stats_cards = []
    if not data.empty and 'sales' in data.columns:
        total_sales = data['sales'].sum()
        avg_sales = data['sales'].mean()
        total_products = data['product'].nunique() if 'product' in data.columns else 0
        total_records = len(data)
        
        stats_cards = [
            create_stat_card("Total Sales", f"${total_sales:,.0f}", "💰", COLORS['success']),
            create_stat_card("Average Sale", f"${avg_sales:,.0f}", "📊", COLORS['primary']),
            create_stat_card("Products", str(total_products), "🏷️", COLORS['warning']),
            create_stat_card("Records", str(total_records), "📝", COLORS['secondary'])
        ]
    
    # Create line chart
    if not data.empty and 'date' in data.columns and 'sales' in data.columns:
        data_sorted = data.sort_values('date')
        line_fig = px.line(
            data_sorted,
            x='date',
            y='sales',
            title='',
            labels={'date': 'Date', 'sales': 'Sales ($)'}
        )
        line_fig.update_traces(
            line_color=COLORS['primary'],
            line_width=3,
            fill='tozeroy',
            fillcolor=f'rgba(102, 126, 234, 0.1)'
        )
        line_fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=0, r=0, t=0, b=0),
            height=300,
            hovermode='x unified'
        )
    else:
        line_fig = go.Figure()
        line_fig.add_annotation(
            text="No data available<br>Upload a file or enter data manually",
            showarrow=False,
            font=dict(size=14, color='#6b7280')
        )
        line_fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )

    # Create bar chart
    if not data.empty and 'product' in data.columns and 'sales' in data.columns:

        # Clean rows where product or sales is empty
        data = data.dropna(subset=['product', 'sales'])

        if data.empty:
            bar_fig = go.Figure()
            bar_fig.add_annotation(
                text="No valid product or sales data found",
                showarrow=False,
                font=dict(size=14, color='#6b7280')
            )
        else:
            # Compute product totals
            product_sales = (
                data.groupby('product', dropna=True)['sales']
                .sum()
                .reset_index()
            )

            # Remove blank product names
            product_sales = product_sales[product_sales['product'].astype(str).str.strip() != ""]

            # Sort top 10
            product_sales = product_sales.sort_values('sales', ascending=False).head(10)

            bar_fig = px.bar(
                product_sales,
                x='product',
                y='sales',
                title='',
                labels={'product': 'Product', 'sales': 'Total Sales ($)'}
            )
            bar_fig.update_traces(
                marker_color=COLORS['secondary'],
                marker_line_color=COLORS['primary'],
                marker_line_width=1
            )
            bar_fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=0, r=0, t=0, b=0),
                height=300,
                xaxis={'categoryorder': 'total descending'}
            )

    else:
        bar_fig = go.Figure()
        bar_fig.add_annotation(
            text="No data available<br>Upload a file or enter data manually",
            showarrow=False,
            font=dict(size=14, color='#6b7280')
        )
        bar_fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )

    # Create data table
    data_table = None
    if not data.empty:
        display_data = data.sort_values('date', ascending=False) if 'date' in data.columns else data
        data_table = html.Div([
            html.H3(
                f"📋 All Sales Data ({len(data)} records)",
                style={'color': COLORS['dark'], 'marginBottom': '15px'}
            ),
            dash_table.DataTable(
                data=display_data.to_dict('records'),
                columns=[{'name': col.title(), 'id': col} for col in display_data.columns],
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px',
                    'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
                },
                style_header={
                    'backgroundColor': COLORS['primary'],
                    'color': 'white',
                    'fontWeight': '600',
                    'border': 'none'
                },
                style_data={
                    'border': '1px solid #e5e7eb'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9fafb'
                    }
                ]
            )
        ])

    return line_fig, bar_fig, stats_cards, data_table


if __name__ == "__main__":
    app.run_server(debug=True)