import streamlit as st
import requests

API = "http://100.51.21.135:8000"

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
    except:
        return []


companies = get_companies()

# companies = [
#     "CONCUR TECHNOLOGIES, INC.",
#     "CW GOVERNMENT TRAVEL INC",
#     "FEDERAL EXPRESS CORPORATION",
#     "UNITED AIRLINES, INC.",
#     "ADVANCED AIR AMBULANCE, CORP.",
# ]

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
st.session_state["company"] = company

if st.button("Analyze", type="primary"):
    with st.spinner("Running risk analysis..."):
        r = requests.get(f"{API}/companies/{company}/risk", timeout=15)
    if r.status_code != 200:
        st.error(f"Company not found: {company}")
        st.session_state.pop("risk_data", None)
    else:
        st.session_state["risk_data"] = r.json()

if "risk_data" in st.session_state:
    data = st.session_state["risk_data"]
    company = st.session_state["company"]

    col1, col2 = st.columns(2)
    with col1:
        risk_card("HHI Concentration Risk", f"{data['hhi']:.4f}", data["hhi_label"])
    with col2:
        risk_card("Recompete Risk", f"{data['recompete_risk']:.4f}", data["recompete_label"])

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
        fleet_r = requests.get(f"{API}/companies/{company}/fleet", timeout=15)
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
                    f"{API}/companies/{company}/memo",
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