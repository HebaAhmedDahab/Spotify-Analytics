import json
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv
from dash import Dash, Input, Output, dcc, html
import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# 1. Load environment variables
# ============================================================

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")


# ============================================================
# 2. PostgreSQL connection
# ============================================================


def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


# ============================================================
# 3. Load data from PostgreSQL
# ============================================================


def load_data():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'recent_tracks'
                ORDER BY ordinal_position
                """
            )
            available_columns = [row[0] for row in cur.fetchall()]

    selected_columns = [
        col
        for col in [
            "track_id",
            "track",
            "artist",
            "album",
            "played_at",
            "played_date",
            "played_hour",
            "day_of_week",
            "duration_minutes",
            "duration_ms",
            "image_url",
        ]
        if col in available_columns
    ]

    if not selected_columns or "played_at" not in selected_columns:
        return pd.DataFrame()

    query = f"SELECT {', '.join(selected_columns)} FROM recent_tracks ORDER BY played_at;"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df

    df["played_at"] = pd.to_datetime(df["played_at"], utc=True)

    if "played_date" not in df.columns:
        df["played_date"] = df["played_at"].dt.strftime("%Y-%m-%d")
    if "played_hour" not in df.columns:
        df["played_hour"] = df["played_at"].dt.hour
    if "day_of_week" not in df.columns:
        df["day_of_week"] = df["played_at"].dt.day_name()
    if "duration_minutes" not in df.columns:
        if "duration_ms" in df.columns:
            df["duration_minutes"] = (df["duration_ms"] / 60000).round(2)
        else:
            durations = pd.to_numeric(df["track_id"].map(load_duration_map()), errors="coerce")
            df["duration_minutes"] = (durations / 60000).round(2).fillna(0.0)
    if "image_url" not in df.columns:
        df["image_url"] = df["track_id"].map(load_artwork_map())

    return df


# ============================================================
# 4. Theme colors
# ============================================================

BACKGROUND = "#121212"
CARD = "#181818"
CARD_HOVER = "#282828"
GREEN = "#1DB954"
BRIGHT_GREEN = "#1ED760"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#B3B3B3"
GRAY = "#535353"


# ============================================================
# 5. Dash app setup
# ============================================================

app = Dash(__name__, title="Spotify Listening Analytics")

APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "spotify_logo.svg"
SPOTIFY_LOGO_EXISTS = LOGO_PATH.exists()
RAW_DIR = APP_DIR.parent / "raw"


def load_artwork_map():
    artwork = {}
    for raw_file in RAW_DIR.glob("recent_tracks_*.json"):
        try:
            with raw_file.open() as file:
                for item in json.load(file).get("items", []):
                    track = item.get("track", {})
                    images = track.get("album", {}).get("images", [])
                    if track.get("id") and images:
                        artwork[track["id"]] = images[0].get("url")
        except (OSError, json.JSONDecodeError):
            continue
    return artwork


def load_duration_map():
    durations = {}
    for raw_file in RAW_DIR.glob("recent_tracks_*.json"):
        try:
            with raw_file.open() as file:
                for item in json.load(file).get("items", []):
                    track = item.get("track", {})
                    if track.get("id") and track.get("duration_ms") is not None:
                        durations[track["id"]] = track["duration_ms"]
        except (OSError, json.JSONDecodeError):
            continue
    return durations


# ============================================================
# 6. Reusable helpers
# ============================================================

CARD_STYLE = {
    "backgroundColor": CARD,
    "borderRadius": "12px",
    "padding": "14px 16px",
    "margin": "0 0 12px 0",
    "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.20)",
    "border": "1px solid rgba(255,255,255,0.03)",
}


def spotify_logo_component():
    if SPOTIFY_LOGO_EXISTS:
        return html.Img(
            src="/assets/spotify_logo.svg",
            style={
                "height": "200px",
                "width": "auto",
                "display": "block",
            },
        )
    return html.Div(
        "Spotify",
        style={
            "fontSize": "35px",
            "fontWeight": "700",
            "color": GREEN,
            "letterSpacing": "0.5px",
            "whiteSpace": "nowrap",
        },
    )


def empty_figure(title):
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "font": {"size": 35, "color": WHITE}},
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font={"color": LIGHT_GRAY},
        margin={"l": 30, "r": 10, "t": 30, "b": 20},
        showlegend=False,
    )
    return fig


def chart_layout(title):
    return {
        "title": {"text": title, "font": {"size": 18, "color": WHITE}},
        "paper_bgcolor": CARD,
        "plot_bgcolor": CARD,
        "font": {"color": LIGHT_GRAY},
        "margin": {"l": 30, "r": 15, "t": 30, "b": 30},
        "xaxis": {"gridcolor": CARD_HOVER, "linecolor": GRAY, "tickfont": {"size": 10}},
        "yaxis": {"gridcolor": CARD_HOVER, "linecolor": GRAY, "tickfont": {"size": 10}},
        "hoverlabel": {"bgcolor": CARD_HOVER, "font_color": WHITE},
        "showlegend": False,
    }


def kpi_card(title, value):
    return [
        html.P(
            title,
            style={
                "color": LIGHT_GRAY,
                "fontSize": "15px",
                "margin": "0 0 8px 0",
                "fontWeight": "600",
                "letterSpacing": "0.2px",
            },
        ),
        html.H2(
            value,
            style={
                "color": GREEN,
                "fontSize": "28px",
                "margin": "0",
                "fontWeight": "700",
                "lineHeight": "1.2",
            },
        ),
    ]


def build_most_played_card(df):
    if df.empty:
        return html.Div(
            "No data available",
            style={
                "padding": "12px 10px",
                "color": LIGHT_GRAY,
                "fontSize": "12px",
                "backgroundColor": CARD,
                "borderRadius": "10px",
            },
        )

    summary = (
        df.groupby(["track", "artist"], dropna=False, as_index=False)
        .agg(
            plays=("track", "size"),
            image_url=("image_url", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
        )
        .sort_values("plays", ascending=False)
        .reset_index(drop=True)
    )

    if summary.empty:
        return html.Div(
            "No data available",
            style={
                "padding": "12px 10px",
                "color": LIGHT_GRAY,
                "fontSize": "12px",
                "backgroundColor": CARD,
                "borderRadius": "10px",
            },
        )

    best = summary.iloc[0]
    image_url = best["image_url"] if pd.notna(best["image_url"]) and str(best["image_url"]).strip() else None

    album_cover = (
        html.Img(
            src=image_url,
            style={
                "width": "200px",
                "height": "200px",
                "borderRadius": "8px",
                "objectFit": "cover",
                "backgroundColor": CARD_HOVER,
                "flexShrink": 0,
            },
        )
        if image_url
        else html.Div(
            "ALBUM",
            style={
                "width": "300px",
                "height": "200px",
                "borderRadius": "8px",
                "backgroundColor": CARD_HOVER,
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "color": LIGHT_GRAY,
                "fontSize": "19px",
                "fontWeight": "700",
                "letterSpacing": "0.7px",
            },
        )
    )

    return html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "14px",
            "padding": "10px 12px",
            "backgroundColor": CARD,
            "borderRadius": "10px",
            "width": "460px",
            "minWidth": "460px",
            "border": "1px solid rgba(255,255,255,0.04)",
        },
        children=[
            album_cover,
            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "center",
                    "lineHeight": "1.2",
                },
                children=[
                    html.Div(
                        str(best["track"])[:32] + ("..." if len(str(best["track"])) > 32 else ""),
                        style={"color": WHITE, "fontSize": "12px", "fontWeight": "700"},
                    ),
                    html.Div(str(best["artist"]), style={"color": LIGHT_GRAY, "fontSize": "11px"}),
                    html.Div(
                        f"{int(best['plays'])} plays",
                        style={"color": GREEN, "fontSize": "11px", "fontWeight": "600", "marginTop": "2px"},
                    ),
                ],
            ),
        ],
    )


# ============================================================
# 7. Layout
# ============================================================

app.layout = html.Div(
    style={
        "backgroundColor": BACKGROUND,
        "minHeight": "100vh",
        "padding": "12px 18px 18px 18px",
        "fontFamily": "Arial, sans-serif",
        "color": WHITE,
        "maxWidth": "1500px",
        "margin": "0 auto",
    },
    children=[
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "padding": "8px 0 12px 0",
                "borderBottom": "1px solid rgba(255,255,255,0.08)",
                "marginBottom": "14px",
                "gap": "12px",
            },
            children=[
                html.Div(
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "flex-start",
                        "gap": "18px",
                        "minWidth": 0,
                    },
                    children=[
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "18px", "minWidth": 0},
                            children=[
                                spotify_logo_component(),
                                html.H1(
                                    "Spotify Listening Analytics",
                                    style={
                                        "margin": 0,
                                        "fontSize": "45px",
                                        "fontWeight": "700",
                                        "color": WHITE,
                                        "lineHeight": "1.2",
                                        "whiteSpace": "nowrap",
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            style={"display": "flex", "flexDirection": "column", "gap": "4px", "width": "360px"},
                            children=[
                                html.Label(
                                    "Listening Period",
                                    style={"color": LIGHT_GRAY, "fontSize": "15px", "fontWeight": "600", "textAlign": "left"},
                                ),
                                dcc.DatePickerRange(
                                    id="date-filter",
                                    className="listening-period-picker",
                                    display_format="DD MMM YYYY",
                                    start_date_placeholder_text="Start",
                                    end_date_placeholder_text="End",
                                    style={"width": "360px"},
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "display": "flex",
                        "alignItems": "flex-end",
                        "gap": "10px",
                        "justifyContent": "flex-end",
                        "flexWrap": "wrap",
                    },
                    children=[
                        html.Div(
                            id="most-played-song-card",
                            style={"width": "484px", "minWidth": "484px", "maxWidth": "484px"},
                        ),
                    ],
                ),
            ],
        ),
        dcc.Interval(id="data-refresh", interval=60 * 1000, n_intervals=0),
        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, minmax(150px, 1fr))",
                "gap": "10px",
                "marginBottom": "10px",
            },
            children=[
                html.Div(id="total-plays-card", style={**CARD_STYLE, "padding": "12px 16px"}),
                html.Div(id="artists-card", style={**CARD_STYLE, "padding": "12px 16px"}),
                html.Div(id="tracks-card", style={**CARD_STYLE, "padding": "12px 16px"}),
                html.Div(id="duration-card", style={**CARD_STYLE, "padding": "12px 16px"}),
            ],
        ),
        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "10px",
                "marginBottom": "10px",
            },
            children=[
                html.Div(
                    dcc.Graph(id="top-songs-chart", config={"displayModeBar": False}, style={"height": "280px"}),
                    style={**CARD_STYLE, "padding": "8px 10px 6px 10px"},
                ),
                html.Div(
                    dcc.Graph(id="top-artists-chart", config={"displayModeBar": False}, style={"height": "280px"}),
                    style={**CARD_STYLE, "padding": "8px 10px 6px 10px"},
                ),
            ],
        ),
        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "1.25fr 1fr",
                "gap": "10px",
                "marginBottom": "10px",
            },
            children=[
                html.Div(
                    dcc.Graph(id="listening-activity", config={"displayModeBar": False}, style={"height": "260px"}),
                    style={**CARD_STYLE, "padding": "8px 10px 6px 10px"},
                ),
                html.Div(
                    dcc.Graph(id="listening-hour", config={"displayModeBar": False}, style={"height": "260px"}),
                    style={**CARD_STYLE, "padding": "8px 10px 6px 10px"},
                ),
            ],
        ),
        html.Div(
            style={**CARD_STYLE, "padding": "12px 14px 10px 14px"},
            children=[
                html.H3(
                    "Top Tracks",
                    style={"color": WHITE, "margin": "0 auto 10px auto", "fontSize": "16px", "fontWeight": "700", "width": "92%", "textAlign": "left"},
                ),
                html.Div(id="top-tracks-table"),
            ],
        ),
        html.Div(
            "Spotify Listening Analytics • Powered by PostgreSQL & Dash",
            style={
                "textAlign": "center",
                "color": GRAY,
                "fontSize": "12px",
                "padding": "18px 8px 6px 8px",
            },
        ),
    ],
)


# ============================================================
# 8. Main Dashboard callback
# ============================================================

@app.callback(
    Output("total-plays-card", "children"),
    Output("artists-card", "children"),
    Output("tracks-card", "children"),
    Output("duration-card", "children"),
    Output("most-played-song-card", "children"),
    Output("top-songs-chart", "figure"),
    Output("top-artists-chart", "figure"),
    Output("listening-activity", "figure"),
    Output("listening-hour", "figure"),
    Output("top-tracks-table", "children"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("data-refresh", "n_intervals"),
)
def update_dashboard(start_date, end_date, _n_intervals):
    df = load_data()

    if df.empty:
        message = html.Div(
            "No listening data available.",
            style={"color": LIGHT_GRAY, "padding": "12px", "fontWeight": "600"},
        )
        empty_graph = empty_figure("Top Songs")
        return (
            message,
            message,
            message,
            message,
            message,
            empty_graph,
            empty_graph,
            empty_figure("Listening Activity"),
            empty_figure("Listening by Hour"),
            message,
        )

    if start_date:
        df = df[df["played_at"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["played_at"] < (pd.to_datetime(end_date) + pd.Timedelta(days=1))]

    if df.empty:
        message = html.Div("No data for this period.", style={"color": LIGHT_GRAY, "padding": "12px", "fontWeight": "600"})
        empty_graph = empty_figure("Top Songs")
        return (
            message,
            message,
            message,
            message,
            message,
            empty_graph,
            empty_graph,
            empty_figure("Listening Activity"),
            empty_figure("Listening by Hour"),
            message,
        )

    total_plays = len(df)
    unique_artists = df["artist"].nunique()
    unique_tracks = df["track_id"].nunique()
    average_duration = df["duration_minutes"].mean()

    total_plays_card = kpi_card("Total Plays", f"{total_plays:,}")
    artists_card = kpi_card("Unique Artists", f"{unique_artists:,}")
    tracks_card = kpi_card("Unique Tracks", f"{unique_tracks:,}")
    duration_card = kpi_card("Avg Duration", f"{average_duration:.1f} min")

    top_songs_data = (
        df.groupby("track", as_index=False)
        .agg(plays=("track", "size"))
        .sort_values("plays", ascending=False)
        .head(10)
        .sort_values("plays", ascending=True)
    )
    top_songs_data["display_track"] = top_songs_data["track"].map(
        lambda track: str(track) if len(str(track)) <= 24 else f"{str(track)[:21]}..."
    )

    top_songs_fig = px.bar(
        top_songs_data,
        x="plays",
        y="display_track",
        orientation="h",
        text="plays",
        custom_data=["track"],
        color_discrete_sequence=[GREEN],
    )
    top_songs_fig.update_traces(
        marker=dict(color=GREEN, line=dict(color=BRIGHT_GREEN, width=1)),
        textposition="outside",
        textfont={"color": WHITE, "size": 11},
        hovertemplate="%{customdata[0]}<br>Plays: %{x}<extra></extra>",
    )
    layout = chart_layout("Top 10 Songs")
    layout.update({
        "xaxis": {"title": {"text": "Plays", "font": {"size": 11, "color": LIGHT_GRAY}}, "gridcolor": CARD_HOVER, "linecolor": GRAY},
        "yaxis": {"title": {"text": "", "font": {"size": 11, "color": LIGHT_GRAY}}, "gridcolor": CARD_HOVER, "linecolor": GRAY, "tickfont": {"size": 9}},
        "margin": {"l": 82, "r": 25, "t": 24, "b": 20},
    })
    top_songs_fig.update_layout(layout)

    top_artists_data = (
        df.groupby("artist", as_index=False)
        .agg(plays=("artist", "size"))
        .sort_values("plays", ascending=False)
        .head(10)
        .sort_values("plays", ascending=True)
    )

    top_artists_fig = px.bar(
        top_artists_data,
        x="plays",
        y="artist",
        orientation="h",
        text="plays",
        color_discrete_sequence=[GREEN],
    )
    top_artists_fig.update_traces(
        marker=dict(color=GREEN, line=dict(color=BRIGHT_GREEN, width=1)),
        textposition="outside",
        textfont={"color": WHITE, "size": 11},
        hovertemplate="%{y}<br>Plays: %{x}<extra></extra>",
    )
    layout = chart_layout("Top 10 Artists")
    layout.update({
        "xaxis": {"title": {"text": "Plays", "font": {"size": 11, "color": LIGHT_GRAY}}, "gridcolor": CARD_HOVER, "linecolor": GRAY},
        "yaxis": {"title": {"text": "Artist", "font": {"size": 11, "color": LIGHT_GRAY}}, "gridcolor": CARD_HOVER, "linecolor": GRAY},
        "margin": {"l": 20, "r": 15, "t": 30, "b": 20},
    })
    top_artists_fig.update_layout(layout)

    activity = (
        df.groupby("played_date", as_index=False)
        .agg(plays=("played_date", "size"))
        .sort_values("played_date")
    )
    activity["played_date"] = pd.to_datetime(activity["played_date"])

    fig_activity = go.Figure()
    fig_activity.add_trace(
        go.Scatter(
            x=activity["played_date"],
            y=activity["plays"],
            mode="lines+markers",
            line={"color": GREEN, "width": 3},
            marker={"size": 7, "color": BRIGHT_GREEN},
            hovertemplate="%{x|%A, %B %d}<br>%{y} plays<extra></extra>",
        )
    )
    layout = chart_layout("Listening Activity")
    layout.update({
        "xaxis": {"title": {"text": "Date", "font": {"color": LIGHT_GRAY, "size": 11}}, "type": "date", "gridcolor": CARD_HOVER, "linecolor": GRAY},
        "yaxis": {"title": {"text": "Plays", "font": {"color": LIGHT_GRAY, "size": 11}}, "gridcolor": CARD_HOVER, "linecolor": GRAY},
        "margin": {"l": 35, "r": 10, "t": 30, "b": 35},
    })
    fig_activity.update_layout(layout)

    hourly = (
        df.groupby("played_hour", as_index=False)
        .agg(plays=("played_hour", "size"))
        .sort_values("played_hour")
    )

    fig_hour = px.bar(
        hourly,
        x="played_hour",
        y="plays",
        color_discrete_sequence=[GREEN],
    )
    fig_hour.update_traces(
        marker=dict(color=GREEN, line=dict(color=BRIGHT_GREEN, width=1)),
        hovertemplate="%{x}:00<br>%{y} plays<extra></extra>",
    )
    layout = chart_layout("Listening by Hour")
    layout.update({
        "xaxis": {
            "title": {"text": "Hour", "font": {"color": LIGHT_GRAY, "size": 11}},
            "tickmode": "array",
            "tickvals": list(range(0, 24, 2)),
            "ticktext": [f"{h}:00" for h in range(0, 24, 2)],
            "gridcolor": CARD_HOVER,
            "linecolor": GRAY,
        },
        "yaxis": {"title": {"text": "Plays", "font": {"color": LIGHT_GRAY, "size": 11}}, "gridcolor": CARD_HOVER, "linecolor": GRAY},
        "margin": {"l": 35, "r": 10, "t": 30, "b": 30},
    })
    fig_hour.update_layout(layout)

    top_tracks = (
        df.groupby(["track", "artist"], as_index=False)
        .agg(plays=("track", "size"))
        .sort_values("plays", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    table_rows = []
    for index, row in top_tracks.iterrows():
        table_rows.append(
            html.Tr(
                [
                    html.Td(
                        str(index + 1),
                        style={"padding": "6px 8px 6px 0", "color": LIGHT_GRAY, "fontWeight": "600", "width": "26px", "textAlign": "left"},
                    ),
                    html.Td(
                        row["track"],
                        style={"padding": "6px 10px", "color": WHITE, "fontWeight": "600", "textAlign": "left"},
                    ),
                    html.Td(
                        row["artist"],
                        style={"padding": "6px 10px", "color": LIGHT_GRAY, "textAlign": "left"},
                    ),
                    html.Td(
                        row["plays"],
                        style={"padding": "6px 10px", "color": GREEN, "fontWeight": "700", "textAlign": "left"},
                    ),
                ]
            )
        )

    table = html.Table(
        [
            html.Colgroup(
                [
                    html.Col(style={"width": "5%"}),
                    html.Col(style={"width": "40%"}),
                    html.Col(style={"width": "35%"}),
                    html.Col(style={"width": "20%"}),
                ]
            ),
            html.Thead(
                html.Tr(
                    [
                        html.Th("", style={"padding": "6px 8px 8px 0", "color": LIGHT_GRAY, "fontSize": "11px", "textAlign": "left"}),
                        html.Th("Track", style={"padding": "6px 10px", "color": LIGHT_GRAY, "fontSize": "11px", "textAlign": "left"}),
                        html.Th("Artist", style={"padding": "6px 10px", "color": LIGHT_GRAY, "fontSize": "11px", "textAlign": "left"}),
                        html.Th("Plays", style={"padding": "6px 10px", "color": LIGHT_GRAY, "fontSize": "11px", "textAlign": "left"}),
                    ]
                )
            ),
            html.Tbody(table_rows),
        ],
        style={"width": "92%", "margin": "0 auto", "borderCollapse": "collapse", "tableLayout": "fixed", "textAlign": "left"},
    )

    most_played_card = build_most_played_card(df)

    return (
        total_plays_card,
        artists_card,
        tracks_card,
        duration_card,
        most_played_card,
        top_songs_fig,
        top_artists_fig,
        fig_activity,
        fig_hour,
        table,
    )


# ============================================================
# 9. Run application
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
