import dash
from dash import html, dcc, Input, Output, State
from supabase_client import supabase

dash.register_page(__name__, path="/signup")

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
        dcc.Location(id="signup-redirect"),

        html.Div(
            style={
                "width": "350px",
                "padding": "30px",
                "borderRadius": "10px",
                "background": "white",
                "boxShadow": "0 4px 10px rgba(0,0,0,0.1)",
            },
            children=[
                html.H2("Create Account", style={"textAlign": "center", "marginBottom": "30px"}),

                dcc.Input(
                    id="signup-email",
                    type="email",
                    placeholder="Email address",
                    style={"width": "100%", "padding": "12px", "marginBottom": "15px"},
                ),

                dcc.Input(
                    id="signup-password",
                    type="password",
                    placeholder="Password (min 6 chars)",
                    style={"width": "100%", "padding": "12px", "marginBottom": "15px"},
                ),

                html.Button(
                    "Sign Up",
                    id="signup-btn",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "padding": "12px",
                        "background": "#16a34a",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "5px",
                        "cursor": "pointer",
                    },
                ),

                html.Div(id="signup-message", style={"marginTop": "10px"}),

                html.Div(
                    [
                        html.Span("Already have an account? "),
                        dcc.Link("Login", href="/login"),
                    ],
                    style={"marginTop": "20px", "textAlign": "center"},
                ),
            ],
        ),
    ],
)


@dash.callback(
    Output("signup-message", "children"),
    Output("signup-message", "style"),
    Output("signup-redirect", "href"),
    Input("signup-btn", "n_clicks"),
    State("signup-email", "value"),
    State("signup-password", "value"),
    prevent_initial_call=True,
)
def signup_user(n_clicks, email, password):
    if not email or not password:
        return "Please fill in all fields.", {"color": "red", "marginTop": "10px"}, None

    if len(password) < 6:
        return "Password must be at least 6 characters.", {"color": "red", "marginTop": "10px"}, None

    try:
        supabase.auth.sign_up({"email": email, "password": password})
        return (
            "Account created! Check your email to verify.",
            {"color": "green", "marginTop": "10px"},
            None,
        )

    except Exception as e:
        print(f"[signup_user] {e}")
        return "Signup failed. Email may already be in use.", {"color": "red", "marginTop": "10px"}, None