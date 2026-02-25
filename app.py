import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.express as px
import plotly.graph_objects as go

app = Dash(__name__)
server = app.server

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
                    "Upload your sales data and visualize insights instantly",
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
                # Upload Section
                html.Div(
                    style={
                        'backgroundColor': COLORS['white'],
                        'borderRadius': '15px',
                        'padding': '30px',
                        'marginBottom': '30px',
                        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
                    },
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
                        
                        # Upload Status
                        html.Div(
                            id="upload-status",
                            style={
                                'marginTop': '15px',
                                'padding': '10px',
                                'borderRadius': '8px',
                                'textAlign': 'center',
                                'fontSize': '0.95em'
                            }
                        ),

                        # Data Preview
                        html.Div(
                            id="data-preview-container",
                            style={'marginTop': '20px'}
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

                # Footer
                html.Div(
                    style={
                        'textAlign': 'center',
                        'padding': '20px',
                        'color': '#6b7280',
                        'fontSize': '0.9em'
                    },
                    children=[
                        "Built with ❤️ using Plotly Dash"
                    ]
                )
            ]
        )
    ]
)

def parse_uploaded_file(contents, filename):
    """Parse uploaded CSV or Excel file"""
    if not contents:
        return None
    
    try:
        # Split the content string
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        if filename.endswith('.csv'):
            # Parse CSV
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # Parse Excel
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None
        
        # Clean column names (remove whitespace)
        df.columns = df.columns.str.strip().str.lower()
        
        # Try to parse date column if it exists
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    
    except Exception as e:
        print(f"Error parsing file: {e}")
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
     Output("upload-status", "children"),
     Output("upload-status", "style"),
     Output("stats-cards", "children"),
     Output("data-preview-container", "children")],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")]
)
def update_dashboard(contents, filename):
    """Update all dashboard components"""
    data = df.copy()  # Start with default data
    status_msg = ""
    status_style = {'display': 'none'}
    
    # Handle file upload
    if contents and filename:
        uploaded_df = parse_uploaded_file(contents, filename)
        
        if uploaded_df is not None and not uploaded_df.empty:
            data = uploaded_df
            status_msg = f"✅ Successfully loaded: {filename} ({len(data)} rows, {len(data.columns)} columns)"
            status_style = {
                'marginTop': '15px',
                'padding': '12px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'fontSize': '0.95em',
                'backgroundColor': '#d1fae5',
                'color': '#065f46',
                'border': f'1px solid {COLORS["success"]}'
            }
        else:
            status_msg = "❌ Error: Could not parse file. Please ensure it's a valid CSV or Excel file."
            status_style = {
                'marginTop': '15px',
                'padding': '12px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'fontSize': '0.95em',
                'backgroundColor': '#fee2e2',
                'color': '#991b1b',
                'border': f'1px solid {COLORS["danger"]}'
            }
    
    # Create statistics cards
    stats_cards = []
    if not data.empty:
        total_sales = data['sales'].sum() if 'sales' in data.columns else 0
        avg_sales = data['sales'].mean() if 'sales' in data.columns else 0
        total_products = data['product'].nunique() if 'product' in data.columns else 0
        total_records = len(data)
        
        stats_cards = [
            create_stat_card("Total Sales", f"${total_sales:,.0f}", "💰", COLORS['success']),
            create_stat_card("Average Sale", f"${avg_sales:,.0f}", "📊", COLORS['primary']),
            create_stat_card("Products", str(total_products), "🏷️", COLORS['warning']),
            create_stat_card("Records", str(total_records), "📝", COLORS['secondary'])
        ]
    
    # Create line chart
    if 'date' in data.columns and 'sales' in data.columns:
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
            text="Missing 'date' or 'sales' column<br>Please upload data with these columns",
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
    if 'product' in data.columns and 'sales' in data.columns:
        product_sales = data.groupby('product')['sales'].sum().reset_index()
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
            text="Missing 'product' or 'sales' column<br>Please upload data with these columns",
            showarrow=False,
            font=dict(size=14, color='#6b7280')
        )
        bar_fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )
    
    # Create data preview table
    data_preview = None
    if not data.empty and contents:
        preview_data = data.head(5)
        data_preview = html.Div([
            html.H4(
                "📋 Data Preview (First 5 rows)",
                style={'color': COLORS['dark'], 'marginBottom': '15px'}
            ),
            dash_table.DataTable(
                data=preview_data.to_dict('records'),
                columns=[{'name': col, 'id': col} for col in preview_data.columns],
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
    
    return line_fig, bar_fig, status_msg, status_style, stats_cards, data_preview


if __name__ == "__main__":
    app.run_server(debug=True)