# YookuInc Analytics — Sales & Expense Dashboard

A Plotly Dash web app for small businesses to track sales and expenses, see trends at a glance, and get AI-written business insights. Users sign in, upload or enter their data, and their records are stored per account in Supabase.

**Live demo:** https://sales-dashboard-i0tz.onrender.com/ (free Render instance — the first load can take up to a minute while it wakes up)

## Features

- **Accounts:** email/password sign-up and login (Supabase Auth)
- **Sales:** upload CSV/Excel or enter records manually; edit records. Views: sales trend, month-over-month, top products, revenue share, sales heatmap, monthly sales target
- **Expenses:** the same upload/entry/edit flow, with expense trend, top vendors, expense share, heatmap and monthly budget
- **AI insights:** executive summary, strengths and opportunities, risks, recommendations and outlook, generated through OpenRouter
- **Export:** download the dashboard as PNG or PDF (client-side, html2canvas + jsPDF)
- Light/dark theme and an installable PWA (manifest + service worker)

## Stack

Python · Dash · Plotly · pandas · Supabase (auth + Postgres) · OpenRouter · gunicorn

## Structure

```
app.py               The whole app: layouts, callbacks, chart builders, Supabase and OpenRouter helpers
assets/              Manifest, icons and service worker (Dash serves this folder automatically)
data/sales.xlsx      Sample sales file to try the upload flow
pages/, supabase_client.py
                     Earlier login/signup pages; not loaded by app.py (it doesn't enable Dash pages)
Procfile             gunicorn entry point for Render
requirements.txt
```

## Configuration

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `OPENROUTER_API_KEY` | Key for the AI insights tab |

The app reads and writes two Supabase tables: `sales_records` (`date, product, sales, category`) and `expense_records` (`date, vendor, amount, category`), scoped to the signed-in user.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SUPABASE_URL=... SUPABASE_KEY=... OPENROUTER_API_KEY=...
python app.py
```

## Deployment

Deployed on Render as a Python web service. The start command comes from the `Procfile` (`gunicorn app:server`), and the environment variables above are set in the Render dashboard.
