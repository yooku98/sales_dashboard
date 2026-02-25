import base64
import io
import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

app = Dash(__name__)
server = app.server

DATA_PATH = "data"
csv_path = os.path.join(DATA_PATH, "sales.csv")
excel_path = os.path.join(DATA_PATH, "sales.xlsx")

def load_initial_data():
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    elif os.path.exists(excel_path):
        return pd.read_excel(excel_path)
    else:
        return pd.DataFrame()

df = load_initial_data()

app.layout = html.Div(
    style={"padding": "20px", "fontFamily": "Arial"},
    children=[
        html.H1("Sales Dashboard", style={"textAlign": "center"}),

        html.Div([
            html.H3("Upload CSV or Excel File"),
            dcc.Upload(
                id="upload-data",
                children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
                style={
                    "width": "100%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "margin": "10px 0",
                },
                multiple=False
            ),
        ]),

        html.Hr(),

        dcc.Graph(id="sales-line-chart"),
        dcc.Graph(id="product-bar-chart")
    ]
)

def parse_uploaded_file(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if filename.endswith(".csv"):
            return pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif filename.endswith(".xlsx"):
            return pd.read_excel(io.BytesIO(decoded))
        else:
            return None
    except:
        return None


@app.callback(
    [Output("sales-line-chart", "figure"),
     Output("product-bar-chart", "figure")],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")]
)
def update_output(contents, filename):
    data = df  # default

    if contents and filename:
        uploaded_df = parse_uploaded_file(contents, filename)
        if uploaded_df is not None:
            data = uploaded_df

    if "date" in data.columns and "sales" in data.columns:
        line_fig = px.line(data, x="date", y="sales", title="Sales Over Time")
    else:
        line_fig = px.scatter(title="Missing columns: date, sales")

    if "product" in data.columns and "sales" in data.columns:
        bar_fig = px.bar(data, x="product", y="sales", title="Top Products")
    else:
        bar_fig = px.scatter(title="Missing columns: product, sales")

    return line_fig, bar_fig


if __name__ == "__main__":
    app.run_server(debug=True)
