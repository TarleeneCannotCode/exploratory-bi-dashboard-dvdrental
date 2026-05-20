"""
=============================================================================
DVD Rental Analysis Dashboard
Exploratory Business Intelligence Dashboard using PostgreSQL DVD Rental Dataset
=============================================================================
Author  : [Lintar]
Course  : Data Visualization
Dataset : PostgreSQL dvdrental
=============================================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import warnings

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DVD Rental · Geographic Performance",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0d0f14; color: #e8e8e8; }

    section[data-testid="stSidebar"] {
        background: #13161e !important;
        border-right: 1px solid #1f2333;
    }
    section[data-testid="stSidebar"] * { color: #c9cdd8 !important; }

    div[data-testid="metric-container"] {
        background: #181b26;
        border: 1px solid #252a3a;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    div[data-testid="metric-container"] label {
        color: #7c8299 !important;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #f0c040 !important;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.2rem;
    }
    .section-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.6rem;
        color: #f0c040;
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #1f2333;
        margin: 0.4rem 0 1.2rem 0;
    }
    .insight-box {
        background: #181b26;
        border-left: 3px solid #f0c040;
        border-radius: 0 8px 8px 0;
        padding: 12px 18px;
        margin: 10px 0 20px 0;
        font-size: 0.85rem;
        color: #b0b5c8;
        line-height: 1.65;
    }
    .insight-box strong { color: #f0c040; }
    .header-banner {
        background: linear-gradient(135deg, #0d0f14 0%, #1a1e2e 50%, #0d0f14 100%);
        border: 1px solid #252a3a;
        border-radius: 16px;
        padding: 32px 40px;
        margin-bottom: 32px;
        text-align: center;
    }
    .header-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 3rem;
        color: #f0c040;
        letter-spacing: 0.06em;
        line-height: 1;
        margin: 0;
    }
    .header-sub {
        color: #7c8299;
        font-size: 0.9rem;
        margin-top: 8px;
        letter-spacing: 0.04em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# PLOTLY CONSTANTS
# RULE: Colors must be 6-digit hex (#rrggbb) or rgba().
# Plotly does not support 8-digit hex (#rrggbbaa) — use rgba() for transparency.
# ─────────────────────────────────────────────
PLOTLY_TEMPLATE = "plotly_dark"
PLOT_BG = "#181b26"
PAPER_BG = "#181b26"
ACCENT = "#f0c040"
GRID_COLOR = "#252a3a"
TREND_COLOR = "rgba(255,255,255,0.13)"
MARKER_BORDER = "rgba(255,255,255,0.13)"


def style_fig(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family="Inter", color="#c9cdd8"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# ─────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="🔌 Connecting to database…")
def get_engine():
    try:
        db = st.secrets["postgres"]
    except KeyError:
        st.error(
            "❌ **`[postgres]` not found in secrets.toml.**\n\n"
            "Create the file `.streamlit/secrets.toml` with:\n"
            "```toml\n[postgres]\nhost=\"localhost\"\nport=5432\n"
            "database=\"dvdrental\"\nusername=\"postgres\"\npassword=\"xxx\"\n```"
        )
        st.stop()
    except Exception as e:
        st.error(f"❌ **Secrets error:** {e}")
        st.stop()

    missing = [
        f
        for f in ["host", "port", "database", "username", "password"]
        if f not in db
    ]
    if missing:
        st.error(f"❌ **Missing field(s) in secrets.toml:** `{missing}`")
        st.stop()

    try:
        url = (
            f"postgresql+psycopg2://{db['username']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['database']}"
        )
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ **Failed to connect to PostgreSQL:** `{e}`")
        st.stop()


# ─────────────────────────────────────────────
# QUERY HELPERS
# ─────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_countries() -> list:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT DISTINCT country FROM country ORDER BY country;")
        )
        return [row[0] for row in result]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_date_range() -> tuple:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT MIN(rental_date)::date, MAX(rental_date)::date FROM rental;"
            )
        ).fetchone()
        return row[0], row[1]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_geo_data(countries: tuple, date_start: str, date_end: str) -> pd.DataFrame:
    engine = get_engine()
    country_clause = ""
    params: dict = {"date_start": date_start, "date_end": date_end}
    if countries:
        country_clause = "AND co.country IN :countries"
        params["countries"] = countries

    query = text(
        f"""
        SELECT
            co.country,
            COUNT(DISTINCT cu.customer_id)   AS total_customers,
            COALESCE(SUM(p.amount), 0)       AS total_revenue
        FROM country co
        JOIN city     ci ON ci.country_id = co.country_id
        JOIN address  a  ON a.city_id     = ci.city_id
        JOIN customer cu ON cu.address_id = a.address_id
        LEFT JOIN rental  r ON r.customer_id = cu.customer_id
            AND r.rental_date::date BETWEEN :date_start AND :date_end
        LEFT JOIN payment p ON p.rental_id  = r.rental_id
        WHERE 1=1 {country_clause}
        GROUP BY co.country
        ORDER BY total_revenue DESC;
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)

    df["avg_revenue_per_customer"] = df.apply(
        lambda row: row["total_revenue"] / row["total_customers"]
        if row["total_customers"] > 0
        else 0,
        axis=1,
    )
    return df


@st.cache_data(ttl=300, show_spinner=False)
def fetch_genre_data(
    countries: tuple, date_start: str, date_end: str
) -> pd.DataFrame:
    engine = get_engine()
    country_clause = ""
    params: dict = {"date_start": date_start, "date_end": date_end}
    if countries:
        country_clause = "AND co.country IN :countries"
        params["countries"] = countries

    query = text(
        f"""
        SELECT
            ca.name            AS genre,
            co.country,
            COUNT(r.rental_id) AS rental_count
        FROM rental r
        JOIN inventory    i  ON i.inventory_id = r.inventory_id
        JOIN film         f  ON f.film_id       = i.film_id
        JOIN film_category fc ON fc.film_id     = f.film_id
        JOIN category     ca ON ca.category_id = fc.category_id
        JOIN customer     cu ON cu.customer_id = r.customer_id
        JOIN address      a  ON a.address_id   = cu.address_id
        JOIN city         ci ON ci.city_id     = a.city_id
        JOIN country      co ON co.country_id  = ci.country_id
        WHERE r.rental_date::date BETWEEN :date_start AND :date_end
          {country_clause}
        GROUP BY ca.name, co.country
        ORDER BY rental_count DESC;
        """
    )

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_rental_duration(countries: tuple, date_start: str, date_end: str) -> pd.DataFrame:
    engine = get_engine()
    country_clause = ""
    params: dict = {"date_start": date_start, "date_end": date_end}
    if countries:
        country_clause = "AND co.country IN :countries"
        params["countries"] = countries

    query = text(
        f"""
        SELECT
            EXTRACT(EPOCH FROM (r.return_date - r.rental_date)) / 86400.0 AS duration_days
        FROM rental r
        JOIN customer cu ON cu.customer_id = r.customer_id
        JOIN address  a  ON a.address_id   = cu.address_id
        JOIN city     ci ON ci.city_id     = a.city_id
        JOIN country  co ON co.country_id  = ci.country_id
        WHERE r.return_date IS NOT NULL
          AND r.rental_date::date BETWEEN :date_start AND :date_end
          {country_clause};
        """
    )

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 DVD Rental")
    st.markdown("### Filters")
    st.markdown("---")

    all_countries = fetch_all_countries()
    selected_countries = st.multiselect(
        "🌍 Country",
        options=all_countries,
        default=[],
        placeholder="All countries…",
    )

    min_date, max_date = fetch_date_range()
    date_range = st.date_input(
        "📅 Rental Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#4a5068'>Data: PostgreSQL dvdrental<br>"
        "Dashboard: Exploratory Business Intelligence Dashboard using PostgreSQL DVD Rental Dataset</small>",
        unsafe_allow_html=True,
    )

# Resolve date range
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    d_start, d_end = date_range
else:
    d_start = d_end = date_range[0] if date_range else min_date

# Convert list → tuple for SQL IN clause
country_tuple = tuple(selected_countries) if selected_countries else ()

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
with st.spinner("Loading data…"):
    geo_df = fetch_geo_data(country_tuple, str(d_start), str(d_end))
    genre_df = fetch_genre_data(country_tuple, str(d_start), str(d_end))
    dur_df = fetch_rental_duration(country_tuple, str(d_start), str(d_end))

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(
    """
    <div class="header-banner">
        <p class="header-title">Exploratory BI Dashboard (Sample DVD Rental Dataset)</p>
        <p class="header-sub">Exploring customer and rental patterns within a synthetic PostgreSQL dataset</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">📊 Key Performance Indicators</p>', unsafe_allow_html=True)
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

total_customers = int(geo_df["total_customers"].sum())
total_revenue = float(geo_df["total_revenue"].sum())
avg_rev_user = total_revenue / total_customers if total_customers > 0 else 0
genre_summary = genre_df.groupby("genre")["rental_count"].sum()
top_genre = genre_summary.idxmax() if not genre_summary.empty else "N/A"

k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Total Customers", f"{total_customers:,}")
k2.metric("💰 Total Revenue", f"${total_revenue:,.2f}")
k3.metric("💵 Avg Revenue / User", f"${avg_rev_user:,.2f}")
k4.metric("🎭 Most Popular Genre", top_genre)

st.markdown(
    """
    <div class="insight-box">
    💡 <strong>Insight for Stakeholders:</strong>
    The KPIs summarize outcomes within a <em>sample</em> relational dataset. Total revenue and customer counts can be used together to describe how activity is distributed, and the "Avg Revenue / User" metric provides a simple view of average monetization per customer in the selected date range.
    <strong>Most Popular Genre</strong> indicates which genre categories generate the highest number of rentals in this dataset slice, which can inform how the dashboard might be structured for inventory-related questions in a controlled study.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# ─────────────────────────────────────────────
# CHOROPLETH MAP
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">🗺️ Global Customer Distribution</p>', unsafe_allow_html=True)
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

if geo_df.empty:
    st.warning("No geographic data available for the selected filters.")
else:
    fig_map = px.choropleth(
        geo_df,
        locations="country",
        locationmode="country names",
        color="total_customers",
        hover_name="country",
        hover_data={
            "total_customers": True,
            "total_revenue": ":.2f",
            "avg_revenue_per_customer": ":.2f",
        },
        color_continuous_scale=[
            [0.0, "#1a1e2e"],
            [0.25, "#2a3a5e"],
            [0.5, "#1e6091"],
            [0.75, "#c98a00"],
            [1.0, "#f0c040"],
        ],
        title="Customers per Country",
    )
    fig_map.update_layout(
        paper_bgcolor=PAPER_BG,
        geo=dict(
            bgcolor=PLOT_BG,
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#252a3a",
            showland=True,
            landcolor="#1a1e2e",
            showocean=True,
            oceancolor="#0d0f14",
            showlakes=True,
            lakecolor="#0d0f14",
        ),
        coloraxis_colorbar=dict(
            title=dict(text="Customers", font=dict(color="#c9cdd8")),
            tickfont=dict(color="#c9cdd8"),
        ),
        font=dict(family="Inter", color="#c9cdd8"),
        margin=dict(l=0, r=0, t=50, b=0),
        height=480,
    )
    st.plotly_chart(fig_map, use_container_width=True)

st.markdown(
    """
    <div class="insight-box">
    💡 <strong>Insight for Stakeholders:</strong>
    This choropleth summarizes how customer activity (distinct customers) is distributed across countries for the selected filters. Higher values indicate countries that contribute more rental activity <em>within this synthetic dataset</em>. The map supports exploratory comparison, but it does not justify claims about real-world market potential or expansion opportunities.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# ─────────────────────────────────────────────
# ROW 2 — Treemap & Scatter Plot
# ─────────────────────────────────────────────
col_left, col_right = st.columns(2, gap="large")

# ── TREEMAP ──────────────────────────────────
with col_left:
    st.markdown('<p class="section-title">🎭 Movie Genre Popularity</p>', unsafe_allow_html=True)
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if genre_df.empty:
        st.warning("No genre data available.")
    else:
        genre_agg = genre_df.groupby("genre", as_index=False)["rental_count"].sum()
        genre_agg = genre_agg.sort_values("rental_count", ascending=False)

        fig_tree = px.treemap(
            genre_agg,
            path=["genre"],
            values="rental_count",
            color="rental_count",
            color_continuous_scale=[
                [0.0, "#1a1e2e"],
                [0.5, "#1e6091"],
                [1.0, "#f0c040"],
            ],
            title="Rentals by Genre",
        )
        fig_tree = style_fig(fig_tree)
        fig_tree.update_traces(
            textfont=dict(family="Inter", size=13),
            hovertemplate="<b>%{label}</b><br>Rentals: %{value:,}<extra></extra>",
        )
        fig_tree.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown(
        """
        <div class="insight-box">
        💡 <strong>Insight for Stakeholders:</strong>
        <strong>Which genre is the most represented?</strong> In this treemap, larger areas correspond to higher rental counts by genre category for the selected period.
        Because the dataset is sample-based, the result is best framed as evidence of <em>what this synthetic catalog tends to generate</em>, rather than a directive for real inventory decisions.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── SCATTER PLOT ─────────────────────────────
with col_right:
    st.markdown('<p class="section-title">📈 Market Efficiency by Country</p>', unsafe_allow_html=True)
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if geo_df.empty or len(geo_df) < 2:
        st.warning("Not enough data to render the scatter plot.")
    else:
        fig_scatter = px.scatter(
            geo_df,
            x="total_customers",
            y="total_revenue",
            size="avg_revenue_per_customer",
            color="avg_revenue_per_customer",
            hover_name="country",
            text="country",
            color_continuous_scale=[
                [0.0, "#1e6091"],
                [0.5, "#c98a00"],
                [1.0, "#f0c040"],
            ],
            labels={
                "total_customers": "Total Customers",
                "total_revenue": "Total Revenue ($)",
                "avg_revenue_per_customer": "Avg Rev/User ($)",
            },
            title="Total Customers vs. Total Revenue",
        )

        # Trend line
        x_sorted = geo_df["total_customers"].sort_values()
        ratio = geo_df["total_revenue"].mean() / geo_df["total_customers"].mean()
        y_sorted = ratio * x_sorted

        fig_scatter.add_trace(
            go.Scatter(
                x=x_sorted,
                y=y_sorted,
                mode="lines",
                name="Trend (avg)",
                line=dict(color=TREND_COLOR, dash="dot", width=1.5),
            )
        )

        fig_scatter = style_fig(fig_scatter)
        fig_scatter.update_traces(
            selector=dict(mode="markers+text"),
            textposition="top center",
            textfont=dict(size=9, color="#9aa0b8"),
            marker=dict(
                line=dict(
                    width=1,
                    color=MARKER_BORDER,
                )
            ),
        )
        fig_scatter.update_layout(
            height=420,
            xaxis=dict(gridcolor=GRID_COLOR, zeroline=False),
            yaxis=dict(gridcolor=GRID_COLOR, zeroline=False),
            coloraxis_colorbar=dict(
                title=dict(text="Avg Rev/User", font=dict(color="#c9cdd8")),
                tickfont=dict(color="#c9cdd8"),
            ),
            showlegend=False,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown(
        """
        <div class="insight-box">
        💡 <strong>Insight for Stakeholders:</strong>
        This scatter plot compares customer counts (x-axis) to total revenue (y-axis) at the country level, with marker size and color reflecting "Avg Rev / User". Points above the trend line have higher revenue than the dataset-wide average relationship suggests, while points below indicate lower revenue relative to customer volume.
        This is an exploratory pattern in sample data; it does not establish causal links to profitability strategies such as loyalty programs.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ─────────────────────────────────────────────
# BONUS — Revenue Ranking by Country
# ─────────────────────────────────────────────
with st.expander("📋 View Table: Revenue Ranking (Top 10 by Country)"):
    top10 = geo_df.nlargest(10, "total_revenue").copy()
    top10["total_revenue"] = top10["total_revenue"].map("${:,.2f}".format)
    top10["avg_revenue_per_customer"] = top10[
        "avg_revenue_per_customer"
    ].map("${:,.2f}".format)
    top10 = top10.rename(
        columns={
            "country": "Country",
            "total_customers": "Total Customers",
            "total_revenue": "Total Revenue",
            "avg_revenue_per_customer": "Avg Rev / Customer",
        }
    )
    top10 = top10.reset_index(drop=True)
    top10.index = top10.index + 1  # display ranking starting from 1
    st.dataframe(top10, use_container_width=True)

st.markdown(
    """
    <div class="insight-box">
    💡 <strong>Insight for Stakeholders:</strong>
    The ranking table lists the countries with the highest <em>total revenue</em> in the selected date range and filter set. Use it as an exploratory summary of where revenue is concentrated in this synthetic dataset. For interpretation, it is helpful to consider both <strong>volume</strong> (total customers) and <strong>monetization</strong> (avg revenue per customer), since high revenue can result from either more customers, higher spending per customer, or both.
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# DATASET LIMITATIONS 
# ─────────────────────────────────────────────
st.markdown(
    """
    <div class="insight-box">
    <strong>Dataset Limitation (for defensible interpretation)</strong>
    <ul style="margin:0.4rem 0 0 1.1rem; padding:0;">
        <li>The PostgreSQL <em>DVD Rental</em> dataset is synthetic and represents a small, fictional operating context. Country values reflect the dataset’s sample geography rather than real coverage.</li>
        <li>Metrics are computed over rentals and payments within the selected date range and (optionally) selected countries. Results therefore describe patterns in this dataset slice, not outcomes of a real business.</li>
        <li>Relationships observed in charts (e.g., customer volume vs. revenue) are exploratory correlations. They do not prove causal drivers such as pricing, marketing, or loyalty programs.</li>
    </ul>
    </div>

    <div style="height:10px;"></div>

    <div class="insight-box">
    <strong>More Valid Analytical Framing (suggestions)</strong>
    <ul style="margin:0.4rem 0 0 1.1rem; padding:0;">
        <li>Use phrasing such as <em>“within this sample dataset”</em> and <em>“for the selected filters”</em>.</li>
        <li>Frame results as support for <em>hypothesis generation</em> (e.g., which genres dominate rental counts; where revenue is concentrated) rather than operational recommendations.</li>
        <li>When discussing ranking or comparisons, explicitly separate <strong>volume</strong> (e.g., customer counts) from <strong>monetization</strong> (e.g., revenue per customer).</li>
        <li>Include a note on data coverage (which countries/date ranges are included) to avoid overstating representativeness.</li>
    </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="text-align:center;color:#3a3f55;font-size:0.78rem;margin-top:20px;padding:20px 0;">
        DVD Rental Analysis · Exploratory BI Dashboard using PostgreSQL DVD Rental Dataset<br>
        Built with Streamlit + Plotly · Data: PostgreSQL dvdrental (sample dataset)
    </div>
    """,
    unsafe_allow_html=True,
)

