"""
reports/monthly_brief_template.py

Generates a one-page monthly PDF brief from the current database state.
Intended to be run on the first Monday of each month after a fresh
data pull, producing a stakeholder-ready summary without opening the
interactive dashboard.

Usage: python reports/monthly_brief_template.py
Output: reports/monthly_brief_YYYY_MM.pdf
"""
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF


DB_PATH = "housing_pulse.db"


def load_summary():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM tracts_with_features", conn)
    fc = pd.DataFrame()
    try:
        fc = pd.read_sql("SELECT * FROM rent_forecast ORDER BY date LIMIT 3", conn)
    except Exception:
        pass
    conn.close()
    return df, fc


class MonthlyBriefPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 12, "Atlanta Housing Pulse — Monthly Brief", ln=True, align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, datetime.now().strftime("%B %Y"), ln=True, align="C")
        self.ln(4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, title, ln=True)
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def key_metric(self, label: str, value: str):
        self.set_font("Helvetica", "B", 10)
        self.cell(70, 7, label, border=0)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 7, value, ln=True)


def generate_brief(output_path: str = None):
    df, fc = load_summary()
    if output_path is None:
        output_path = f"reports/monthly_brief_{datetime.now().strftime('%Y_%m')}.pdf"

    tier_counts = df["risk_tier"].value_counts().reindex(["Critical","High","Moderate","Low"], fill_value=0)
    gentrif = int(df["gentrification_pressure_flag"].sum())
    avg_burden = df["rent_burden_pct"].mean()

    pdf = MonthlyBriefPDF()
    pdf.add_page()

    pdf.section_title("Headline Metrics")
    pdf.key_metric("Critical-risk tracts:", str(tier_counts["Critical"]))
    pdf.key_metric("High-risk tracts:", str(tier_counts["High"]))
    pdf.key_metric("Average rent burden:", f"{avg_burden:.1%}")
    pdf.key_metric("Gentrification flags:", str(gentrif))
    pdf.key_metric("Total tracts analyzed:", str(len(df)))
    pdf.ln(4)

    pdf.section_title("Risk Tier Distribution")
    for tier, count in tier_counts.items():
        pct = count / len(df) * 100
        bar = "█" * int(pct / 2)
        pdf.body_text(f"  {tier:<12} {count:>4} ({pct:.1f}%)  {bar}")

    pdf.section_title("Top 5 Highest-Risk Tracts")
    top5 = df.nlargest(5, "displacement_risk_index")[["NAME","county_name","displacement_risk_index","risk_tier"]]
    for _, row in top5.iterrows():
        pdf.body_text(f"  {row['NAME']}  |  DRI: {row['displacement_risk_index']:.3f}  |  {row['risk_tier']}")

    if not fc.empty:
        pdf.section_title("3-Month Rent Forecast")
        row = fc.iloc[2]
        pdf.body_text(
            f"  Point estimate: ${row['forecast']:,.0f}  "
            f"(90% range: ${row['lower_90']:,.0f} – ${row['upper_90']:,.0f})"
        )
        pdf.body_text("  Treat 6+ month forecasts as directional only.")

    pdf.section_title("Notes")
    pdf.body_text(
        "DRI reflects 2022 ACS 5-Year data. Rent forecast is model-generated. "
        "This brief is auto-generated — contact the analysis team for tract-level detail."
    )

    pdf.output(output_path)
    print(f"Brief generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_brief()
