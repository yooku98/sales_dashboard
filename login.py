import dash
from dash import html, dcc, Input, Output, State
from supabase_client import supabase

dash.register_page(__name__, path="/login")

layout = html.Div(
    style={
        "display": "flex",
        "height": "100vh",
        "alignItems": "center",
        "justifyContent": "center",
        "background": "#f4f6f8",
        "fontFamily": "Segoe UI",
    },
    children=[
        dcc.Location(id="login-redirect"),

        html.Div(
            style={
                "width": "350px",
                "padding": "30px",
                "borderRadius": "10px",
                "background": "white",
                "boxShadow": "0 4px 10px rgba(0,0,0,0.1)",
            },
            children=[
                html.H2("Login", style={"textAlign": "center", "marginBottom": "30px"}),

                dcc.Input(
                    id="login-email",
                    type="email",
                    placeholder="Email address",
                    style={"width": "100%", "padding": "12px", "marginBottom": "15px"},
                ),

                dcc.Input(
                    id="login-password",
                    type="password",
                    placeholder="Password",
                    style={"width": "100%", "padding": "12px", "marginBottom": "15px"},
                ),

                html.Button(
                    "Sign In",
                    id="login-btn",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "padding": "12px",
                        "background": "#2563eb",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "5px",
                        "cursor": "pointer",
                    },
                ),

                html.Div(id="login-error", style={"color": "red", "marginTop": "10px"}),

                html.Div(
                    [
                        html.Span("Don't have an account? "),
                        dcc.Link("Create one", href="/signup"),
                    ],
                    style={"marginTop": "20px", "textAlign": "center"},
                ),

                # Session store — token and user_id stored here, never in URL
                dcc.Store(id="session-store", storage_type="session"),
            ],
        ),
    ],
)


@dash.callback(
    Output("login-error", "children"),
    Output("login-redirect", "href"),
    Output("session-store", "data"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def login_user(n_clicks, email, password):
    if not email or not password:
        return "Please fill in all fields.", None, None

    try:
        res = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        session_data = {
            "token": res.session.access_token,
            "user_id": res.user.id,
        }

        return "", "/dashboard", session_data

    except Exception as e:
        print(f"[login_user] {e}")
        return "Invalid email or password.", None, None