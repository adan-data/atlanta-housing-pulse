"""
dashboard/app.py
Two-mode Streamlit dashboard.
  Community Overview  — for planners, nonprofits, advocates. No jargon.
  Technical Analysis  — for data reviewers and model auditors.
Auto-seeds demo DB on first run if housing_pulse.db is absent.
"""
import os, sys, sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
DB_PATH = os.path.join(ROOT, "housing_pulse.db")
COLORS  = {"Low":"#2ecc71","Moderate":"#f39c12","High":"#e74c3c","Critical":"#8e44ad"}

st.set_page_config(page_title="Atlanta Housing Pulse", page_icon=":building_construction:", layout="wide")

@st.cache_resource
def ensure_db():
    if not os.path.exists(DB_PATH):
        from demo_data import seed_demo_db
        seed_demo_db(DB_PATH)
    return True
ensure_db()

@st.cache_data(ttl=3600)
def load(table, query=None):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(query or f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def recommendation(row):
    if row["risk_tier"]=="Critical":
        return (f"Immediate action. Rent burden {row['rent_burden_pct']:.0%}, income ${row['median_income']:,.0f}. "
                "Emergency rental assistance recommended within 30 days.")
    if row["risk_tier"]=="High":
        return f"Escalating pressure. RTI={row['rent_to_income_ratio']:.2f}. Proactive tenant outreach recommended."
    if row["risk_tier"]=="Moderate": return "Monitoring advised — flag for quarterly review."
    return "Stable. Continue standard monitoring."

st.title("Atlanta Housing Pulse")
demo = not bool(os.getenv("CENSUS_API_KEY",""))
if demo:
    st.info("**Demo mode** — synthetic Atlanta data calibrated to 2022 ACS public summaries. "
            "Add Census + FRED API keys to load live data.", icon="ℹ️")
st.caption(f"U.S. Census ACS 5-Year · HUD FMR · FRED | {'Demo · ' if demo else ''}Updated {datetime.now().strftime('%B %Y')}")

df   = load("tracts_with_features")
view = st.radio("Select view", ["Community Overview","Technical Analysis"], horizontal=True)
st.divider()

if view == "Community Overview":
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Critical Tracts", int((df["risk_tier"]=="Critical").sum()))
    c2.metric("High Risk Tracts", int((df["risk_tier"]=="High").sum()))
    c3.metric("Avg Rent Burden", f"{df['rent_burden_pct'].mean():.1%}")
    c4.metric("Gentrification Flags", int(df.get("gentrification_pressure_flag", pd.Series(0)).sum()))


    st.subheader("Income vs. Rent by Tract")
    st.caption("Bubble = renter household count. Lower-right (high rent, low income) = highest-priority targets.")
    fig = px.scatter(df.dropna(subset=["median_income","median_rent"]),
        x="median_income", y="median_rent", size="total_renter_hh", color="risk_tier",
        color_discrete_map=COLORS, hover_data=["NAME","rent_burden_pct","displacement_risk_index"],
        labels={"median_income":"Median Income ($)","median_rent":"Median Rent ($)"}, height=460)
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Risk Distribution by County")
    county_tiers = df.groupby(["county_name","risk_tier"]).size().reset_index(name="tracts")
    fig2 = px.bar(county_tiers, x="county_name", y="tracts", color="risk_tier",
        color_discrete_map=COLORS, category_orders={"risk_tier":["Critical","High","Moderate","Low"]},
        labels={"county_name":"","tracts":"Census Tracts"}, height=360)
    fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 10 Highest-Risk Tracts")
    top10 = df.nlargest(10,"displacement_risk_index").copy()
    top10["Recommendation"] = top10.apply(recommendation, axis=1)
    st.dataframe(top10[["NAME","county_name","displacement_risk_index","risk_tier",
        "median_rent","median_income","rent_burden_pct","Recommendation"]],
        use_container_width=True, hide_index=True)

    try:
        fc = load("rent_forecast", "SELECT * FROM rent_forecast ORDER BY date")
        if not fc.empty:
            st.subheader("18-Month Rent Forecast")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=fc["date"],y=fc["forecast"],mode="lines+markers",
                name="Forecast",line=dict(color="#2980b9",width=2.5)))
            fig3.add_trace(go.Scatter(
                x=pd.concat([fc["date"],fc["date"][::-1]]),
                y=pd.concat([fc["upper_90"],fc["lower_90"][::-1]]),
                fill="toself",fillcolor="rgba(52,152,219,0.12)",
                line=dict(color="rgba(255,255,255,0)"),name="90% CI"))
            fig3.update_layout(xaxis_title="",yaxis_title="Forecasted Rent ($)",
                plot_bgcolor="white",paper_bgcolor="white",height=340)
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("3-month forecasts are actionable. 6+ months is directional only — CI widens substantially.")
    except Exception: pass

else:
    c1,c2 = st.columns(2)
    with c1:
        fig_h = px.histogram(df.dropna(subset=["displacement_risk_index"]),
            x="displacement_risk_index",nbins=40,color="risk_tier",color_discrete_map=COLORS,
            title="DRI Distribution",labels={"displacement_risk_index":"DRI Score"})
        fig_h.update_layout(plot_bgcolor="white",paper_bgcolor="white")
        st.plotly_chart(fig_h, use_container_width=True)
    with c2:
        corr_cols = ["rent_burden_pct","rent_to_income_ratio","vacancy_rate","median_income","median_rent","displacement_risk_index"]
        fig_c = px.imshow(df[corr_cols].corr(),text_auto=".2f",color_continuous_scale="RdBu_r",zmin=-1,zmax=1,title="Feature Correlations")
        st.plotly_chart(fig_c, use_container_width=True)

    st.subheader("DRI Methodology")
    st.dataframe(pd.DataFrame({
        "Component":["Rent Burden (≥50%)","Rent-to-Income Ratio","Low Vacancy (1–rate)","Low Income (inverted)"],
        "Weight":[0.35,0.25,0.20,0.20],
        "Rationale":["Realized distress — households at the breaking point",
                     "Forward affordability — captures rising pressure early",
                     "Tight market = fewer alternatives when pressure hits",
                     "Lower income = shorter runway to absorb increases"],
    }), use_container_width=True, hide_index=True)

    st.subheader("PSI Drift Monitor")
    try:
        drift = load("drift_log","SELECT * FROM drift_log ORDER BY checked_at DESC LIMIT 50")
        if not drift.empty:
            if drift["status"].eq("RETRAIN").any(): st.error("Significant drift. Retraining recommended.")
            elif drift["status"].eq("MONITOR").any(): st.warning("Moderate drift detected. Manual review advised.")
            else: st.success("All features within stable range.")
            fig_d = px.bar(drift.sort_values("psi_score",ascending=False),
                x="feature",y="psi_score",color="status",height=320,
                color_discrete_map={"STABLE":"#2ecc71","MONITOR":"#f39c12","RETRAIN":"#e74c3c"},
                labels={"psi_score":"PSI Score","feature":""})
            fig_d.add_hline(y=0.10,line_dash="dash",line_color="orange",annotation_text="Monitor (0.10)")
            fig_d.add_hline(y=0.25,line_dash="dash",line_color="red",annotation_text="Retrain (0.25)")
            fig_d.update_layout(plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig_d, use_container_width=True)
    except Exception: st.info("Run monitor.py to populate drift log.")

    st.subheader("County Summary")
    # Line 148: Safe county summary (handles ANY column names)
    df_safe = df.copy()
    df_safe['geoid'] = df_safe.get('geoid', df_safe.get('geo_id', 0)).astype(str)
    df_safe['gentrif_pressure_flag'] = df_safe.get('gentrif_pressure_flag', 0).fillna(0)
    df_safe['displacement_risk_index'] = df_safe.get('displacement_risk_index', 0).fillna(0)
    df_safe['median_rent'] = df_safe.get('median_rent', 0).fillna(0)

    # FIPS → COUNTY NAMES (extracts chars 2-4 from full GEOID "13121000100")
    def get_county(geoid):
        g = str(geoid)
        fips = g[2:5] if len(g) >= 5 else g
        return {
            '063': 'Clayton', '067': 'Cobb', '089': 'DeKalb',
            '121': 'Fulton',  '135': 'Gwinnett'
        }.get(fips, f'FIPS_{fips}')

    df_safe['countyname'] = df_safe['geoid'].apply(get_county)

    cs = df_safe.groupby('countyname').agg(
        Tracts=('geoid', 'count'),
        Avg_DRI=('displacement_risk_index', 'mean'),
        Med_Rent=('median_rent', 'mean'),
        Gentrif=('gentrif_pressure_flag', 'sum')
    ).round(3).reset_index()

    st.dataframe(cs, use_container_width=True)
