import streamlit as st

PASSWORD = "0026549"  # βάλε ό,τι θες

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        password = st.text_input("Βάλε password", type="password")
        if password == PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.stop()

check_password()

import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("📦 SLA Dashboard")

# Load master
@st.cache_data
def load_master():
    df = pd.read_csv("master.csv")
    df["KEY_CLEAN"] = df["KEY1"].str.extract(r"(\d+)")
    return df[["KEY_CLEAN", "Χρόνος Παράδοσης", "Regional Unity"]]

master = load_master()

uploaded_file = st.file_uploader("Upload Operational CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    df["KEY_CLEAN"] = df["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
    
    df = df.merge(master, on="KEY_CLEAN", how="left")

    total = len(df)
    delivered = len(df[df["Κατάσταση"] == "ΠΑΡΑΔΟΘΗΚΕ"])
    not_delivered = total - delivered

    col1, col2, col3 = st.columns(3)
    col1.metric("Σύνολο", total)
    col2.metric("Παραδόθηκαν", delivered)
    col3.metric("Μη Παραδοθείσες", not_delivered)

    st.subheader("SLA Performance")

    sla_summary = df.groupby("Χρόνος Παράδοσης").agg(
        total=("Αριθμός", "count"),
        delivered=("Κατάσταση", lambda x: (x == "ΠΑΡΑΔΟΘΗΚΕ").sum())
    ).reset_index()

    sla_summary["%"] = (sla_summary["delivered"] / sla_summary["total"] * 100).round(2)

    st.dataframe(sla_summary)

    st.bar_chart(sla_summary.set_index("Χρόνος Παράδοσης")["%"])

    st.subheader("Ανάλυση ανά Νομό")

    region = df.groupby("Regional Unity").agg(
        total=("Αριθμός", "count"),
        delivered=("Κατάσταση", lambda x: (x == "ΠΑΡΑΔΟΘΗΚΕ").sum())
    ).reset_index()

    region["%"] = (region["delivered"] / region["total"] * 100).round(2)

    st.dataframe(region)