import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

# ---------- PASSWORD ----------
PASSWORD = os.getenv("APP_PASSWORD", "1234")

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

# ---------- LOAD DATA ----------
data_url = "https://raw.githubusercontent.com/antkanavos/sla-dashboard/refs/heads/main/data.csv"
df = pd.read_csv(data_url)

master = pd.read_csv("master.csv")
holidays_df = pd.read_csv("holidays.csv")

# ---------- HOLIDAYS ----------
holidays = set(
    pd.to_datetime(holidays_df["date"], dayfirst=True).dt.date
)

# ---------- CLEAN KEYS ----------
df["KEY_CLEAN"] = df["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
master["KEY_CLEAN"] = master["KEY1"].str.extract(r"(\d+)")

df = df.merge(master, on="KEY_CLEAN", how="left")

# ---------- PARSE DATES ----------
df["Ημ/νία Δημιουργίας"] = pd.to_datetime(df["Ημ/νία Δημιουργίας"], dayfirst=True)
df["Ημ/νία Παράδοσης"] = pd.to_datetime(df["Ημ/νία Παράδοσης"], dayfirst=True, errors="coerce")

# ---------- SLA DAYS ----------
def sla_to_days(x):
    return {24: 1, 48: 2, 96: 4}.get(x, None)

df["sla_days"] = df["Χρόνος Παράδοσης"].apply(sla_to_days)

# ---------- WORKING DAYS ----------
def working_days(start, end):
    if pd.isna(end):
        return None

    days = pd.date_range(start, end)

    working = [
        d for d in days
        if d.weekday() != 6 and d.date() not in holidays
    ]

    return len(working) - 1

df["working_days"] = df.apply(
    lambda x: working_days(x["Ημ/νία Δημιουργίας"], x["Ημ/νία Παράδοσης"]),
    axis=1
)

# ---------- DELIVERED ----------
delivered = df[df["Ημ/νία Παράδοσης"].notna()].copy()

# ---------- SLA ----------
delivered["on_time"] = delivered["working_days"] <= delivered["sla_days"]

delivered["delay_days"] = delivered["working_days"] - delivered["sla_days"]
delivered["delay_days"] = delivered["delay_days"].clip(lower=0)

def delay_bucket(x):
    if x == 0:
        return "on_time"
    elif x == 1:
        return "delay_1"
    elif x == 2:
        return "delay_2"
    else:
        return "delay_3_plus"

delivered["delay_bucket"] = delivered["delay_days"].apply(delay_bucket)

# ---------- KPIs ----------
total = len(df)
delivered_count = len(delivered)
on_time_count = delivered["on_time"].sum()
sla_percent = (on_time_count / delivered_count * 100) if delivered_count else 0

# ---------- UI ----------
st.title("📦 SLA Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Σύνολο", total)
col2.metric("Παραδόθηκαν", delivered_count)
col3.metric("Εντός SLA", on_time_count)
col4.metric("SLA %", f"{sla_percent:.2f}%")

st.divider()

# ---------- SLA ANALYSIS ----------
st.subheader("Ανάλυση SLA")

sla_summary = delivered.groupby("Χρόνος Παράδοσης").agg(
    total=("Αριθμός", "count"),
    on_time=("on_time", "sum")
)

sla_summary["late"] = sla_summary["total"] - sla_summary["on_time"]

st.dataframe(sla_summary)

# ---------- DELAYS ----------
st.subheader("Καθυστερήσεις")

delay_summary = delivered.groupby(["delay_bucket", "Χρόνος Παράδοσης"]).size().unstack(fill_value=0)

st.dataframe(delay_summary)