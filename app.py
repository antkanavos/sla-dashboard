import streamlit as st
import pandas as pd
import os
import plotly.express as px

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

# ---------- CLEAN FUNCTIONS ----------
def clean_address(x):
    if pd.isna(x):
        return None

    x = str(x).upper()
    x = x.replace("-", " ")
    x = x.replace(",", "")
    x = x.replace(".", "")
    x = x.strip()
    x = " ".join(x.split())

    return x

# ---------- KEYS ----------
df["KEY_CLEAN"] = df["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
master["KEY_CLEAN"] = master["KEY1"].str.extract(r"(\d+)")

# ---------- REMOVE ROWS WITHOUT KEY ----------
df = df[df["KEY_CLEAN"].notna()].copy()

# ---------- CLEAN ADDRESSES ----------
df["ADDR_CLEAN"] = df["Δ/νση Παράδοσης"].apply(clean_address)
master["ADDR_CLEAN"] = master["Full Address"].apply(clean_address)

# ---------- 🔥 DEDUP MASTER ----------
master = master.drop_duplicates(subset=["KEY_CLEAN", "ADDR_CLEAN"])

# ---------- MERGE ----------
df = df.merge(
    master,
    on=["KEY_CLEAN", "ADDR_CLEAN"],
    how="left"
)

# ---------- DATES ----------
df["Ημ/νία Δημιουργίας"] = pd.to_datetime(df["Ημ/νία Δημιουργίας"], dayfirst=True)
df["Ημ/νία Παράδοσης"] = pd.to_datetime(df["Ημ/νία Παράδοσης"], dayfirst=True, errors="coerce")

# ---------- SLA ----------
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
delivered = df[
    (df["Ημ/νία Παράδοσης"].notna()) &
    (df["sla_days"].notna())
].copy()

# ---------- SLA LOGIC ----------
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
delivered_count = len(df[df["Ημ/νία Παράδοσης"].notna()])  # πραγματικά παραδομένες
on_time_count = delivered["on_time"].sum()

sla_percent = (on_time_count / len(delivered) * 100) if len(delivered) else 0
missing_sla = df["sla_days"].isna().sum()

# ---------- UI ----------
st.title("📦 SLA Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Σύνολο", total)
col2.metric("Παραδόθηκαν", delivered_count)
col3.metric("Εντός SLA", on_time_count)
col4.metric("SLA %", f"{sla_percent:.2f}%")
col5.metric("Missing SLA", missing_sla)

st.divider()

# ---------- SLA DONUTS ----------
st.subheader("Ανάλυση SLA")

sla_summary = delivered.groupby("Χρόνος Παράδοσης").agg(
    total=("Αριθμός", "count"),
    on_time=("on_time", "sum")
)

sla_summary["late"] = sla_summary["total"] - sla_summary["on_time"]

cols = st.columns(3)

for i, sla in enumerate([24, 48, 96]):
    if sla in sla_summary.index:
        row = sla_summary.loc[sla]

        fig = px.pie(
            values=[row["on_time"], row["late"]],
            names=["Εντός SLA", "Εκτός SLA"],
            hole=0.6,
            color=["Εντός SLA", "Εκτός SLA"],
            color_discrete_map={
                "Εντός SLA": "green",
                "Εκτός SLA": "red"
            }
        )

        fig.update_layout(title=f"{sla}h SLA")

        cols[i].plotly_chart(fig, use_container_width=True)

# ---------- DELAY DONUTS ----------
st.subheader("Καθυστερήσεις")

delay_summary = delivered.groupby(["delay_bucket", "Χρόνος Παράδοσης"]).size().unstack(fill_value=0)

delay_cols = st.columns(3)

mapping = {
    "delay_1": "1 ημέρα",
    "delay_2": "2 ημέρες",
    "delay_3_plus": "3+ ημέρες"
}

color_map = {
    24: "#1f77b4",
    48: "#ff7f0e",
    96: "#d62728"
}

for i, bucket in enumerate(["delay_1", "delay_2", "delay_3_plus"]):
    if bucket in delay_summary.index:
        row = delay_summary.loc[bucket]

        fig = px.pie(
            values=row.values,
            names=row.index,
            hole=0.6,
            color=row.index,
            color_discrete_map=color_map
        )

        fig.update_layout(title=mapping[bucket])

        delay_cols[i].plotly_chart(fig, use_container_width=True)