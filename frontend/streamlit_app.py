import streamlit as st
import requests
import os
from dotenv import load_dotenv
from urllib.parse import quote


load_dotenv()
API = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="PoseidonGov", page_icon="🔱", layout="wide")  # ← FIRST

if st.sidebar.button("Clear cache"):
    st.cache_data.clear()
    st.rerun()

st.title("🔱 PoseidonGov")
st.subheader("AI Deal Intelligence — Aviation & GovCon Private Equity")

@st.cache_data(ttl=300)
def get_companies():
    try:
        r = requests.get(f"{API}/companies", timeout=10)
        if r.status_code == 200:
            return sorted(list(r.json().keys()))
        return []
    except requests.exceptions.RequestException:
        st.error(

   
          "The system was unable to establish a connection to the primary database.",
          title="Connection Timeout",
           icon="🚨"
            )
        return []

def fetch_risk(name: str) -> dict | None:
    """Fetch risk data for one company. Shows an error and returns None on failure."""
    try:
        r = requests.get(f"{API}/companies/{quote(name, safe='')}/risk", timeout=15)
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach the API: {e}")
        return None
    if r.status_code == 404:
        st.error(f"Company not found: {name}")
        return None
    if r.status_code != 200:
        st.error(f"API error {r.status_code}: {r.text[:300]}")
        return None
    return r.json()

companies = get_companies()

def risk_card(label, value, risk_label):
    color = {
        "HIGH RISK": "#FF4B4B",
        "HIGH":      "#FF4B4B",
        "MODERATE":  "#FFA500",
        "MEDIUM":    "#FFA500",
        "HEALTHY":   "#00C853",
        "LOW":       "#00C853",
    }.get(risk_label, "#888888")
    st.markdown(f"""
        <div style="padding:20px; border-radius:10px;
                    border: 2px solid {color}; text-align:center; margin-bottom:10px">
            <p style="color:#888; margin:0; font-size:13px">{label}</p>
            <h2 style="color:white; margin:5px 0">{value}</h2>
            <span style="background:{color}; padding:4px 14px;
                         border-radius:20px; color:white; font-weight:bold;
                         font-size:13px">{risk_label}</span>
        </div>
    """, unsafe_allow_html=True)

company = st.selectbox("Select company:", companies)

if st.button("Analyze", type="primary", disabled=not company):
    with st.spinner("Running risk analysis..."):
        data = fetch_risk(company)
    if data is None:
        st.session_state.pop("risk_data", None)
        st.session_state.pop("analyzed_company", None)
    else:
        st.session_state["risk_data"] = data
        st.session_state["analyzed_company"] = company
    st.session_state.pop("memo", None)   # never show a memo from an older analysis


if "risk_data" in st.session_state:
    data = st.session_state["risk_data"]
    company = st.session_state["analyzed_company"]
    company_path = quote(company, safe="")  # names can contain "/", "#", "&"

    col1, col2 = st.columns(2)
    with col1:
        risk_card("HHI Concentration Risk", f"{data['hhi']:.4f}", data["hhi_label"])
    with col2:
        risk_card("Recompete Risk", f"{data['recompete_risk']:.4f}", data["recompete_label"])

    if data.get("recompete_method") == "xgboost":
        st.caption(
            f"Recompete risk: XGBoost estimate over {data['recompete_contracts_scored']} "
            "contracts ending within 24 months (a relative ranking, not a probability)."
        )
    else:
        st.caption("Recompete risk: rule-based estimate (too little data for the model).")

    st.divider()

    st.subheader("Revenue by Agency")
    breakdown = data["agency_breakdown"]
    if breakdown:
        agencies = [(b["agency"] or "Unknown")[:35] for b in breakdown]
        pcts = [float(b["pct"]) for b in breakdown]
        st.bar_chart(dict(zip(agencies, pcts)))

    st.divider()

    st.subheader("Fleet Analysis")
    with st.spinner("Loading fleet data..."):
        fleet_r = requests.get(f"{API}/companies/{company_path}/fleet", timeout=15)
    if fleet_r.status_code == 200:
        fleet = fleet_r.json()
        st.metric("Registered Aircraft", fleet["fleet_size"])
        if fleet["aircraft"]:
            st.dataframe(fleet["aircraft"][:20])
    else:
        st.info("No fleet data found for this company.")

    st.divider()

    st.subheader("AI Diligence Memo")
    if st.button("Generate Memo", type="secondary"):
        with st.spinner("Generating memo via AWS Bedrock... (15-20 seconds)"):
            try:
                memo_r = requests.get(
                    f"{API}/companies/{company_path}/memo",
                    timeout=60
                )
                if memo_r.status_code == 200:
                    st.session_state["memo"] = memo_r.json()
                else:
                    st.error(f"API error {memo_r.status_code}: {memo_r.text[:300]}")
                    st.session_state.pop("memo", None)
            except requests.exceptions.Timeout:
                st.error("Request timed out. Try again.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    if "memo" in st.session_state:
        memo = st.session_state["memo"]
        st.markdown("#### Executive Summary")
        st.write(memo.get("executive_summary", "—"))
        st.markdown("#### Key Risks")
        st.markdown(memo.get("key_risks", "—"))
        st.markdown("#### Recommendation")
        rec = memo.get("recommendation", "—")
        color = "red" if "PASS" in rec.upper() else "green"
        st.markdown(f":{color}[**{rec}**]")

st.divider()
st.caption("Data sources: USASpending.gov · SAM.gov · FAA Aircraft Registry | Built by Mobin Ezzati")

