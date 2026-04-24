import streamlit as st
import pandas as pd
import os
import plotly.express as px
from rapidfuzz import process, fuzz

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

# ---------- DATA ----------
data_url = "https://raw.githubusercontent.com/antkanavos/sla-dashboard/refs/heads/main/data.csv"
df = pd.read_csv(data_url)

master = pd.read_csv("master.csv")
holidays_df = pd.read_csv("holidays.csv")

# ---------- HOLIDAYS ----------
holidays = set(
    pd.to_datetime(holidays_df["date"], dayfirst=True).dt.date
)

# ---------- CLEAN ----------
def clean_address(x):
    if pd.isna(x):
        return None
    x = str(x).upper()
    x = x.replace("-", " ")
    x = x.replace(",", "")
    x = x.replace(".", "")
    x = x.replace("ΟΔΟΣ", "")
    x = x.replace("ΑΓΙΟΥ", "ΑΓ")
    x = x.replace("ΑΓΙΑΣ", "ΑΓ")
    x = x.replace("ΚΑΙ", "&")
    x = x.strip()
    x = " ".join(x.split())
    return x

def clean_postcode(x):
    if pd.isna(x):
        return None
    x = str(x)
    x = x.replace(".0", "")
    x = x.replace(" ", "")
    x = x.replace("-", "")
    x = "".join(filter(str.isdigit, x))
    if len(x) >= 5:
        x = x[:5]
    return x

# ---------- KEYS ----------
df["KEY_CLEAN"] = df["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
df = df[df["KEY_CLEAN"].notna()].copy()
df_original = df.copy()

master["KEY_CLEAN"] = master["KEY1"].str.extract(r"(\d+)")

# ---------- ADDRESS ----------
df["ADDR_CLEAN"] = df["Δ/νση Παράδοσης"].apply(clean_address)
master["ADDR_CLEAN"] = master["Full Address"].apply(clean_address)

# ---------- POSTCODE ----------
df["POSTCODE"] = df["Τ.Κ Παράδοσης"].apply(clean_postcode)
master["POSTCODE"] = master["Account : Site : Site PostCode"].apply(clean_postcode)

# ---------- MASTER CLEAN ----------
master = master.sort_values("Χρόνος Παράδοσης")
master = master.drop_duplicates(subset=["KEY_CLEAN", "POSTCODE"], keep="first")

# ---------- MERGE (KEY + POSTCODE) ----------
df = df.merge(
    master,
    on=["KEY_CLEAN", "POSTCODE"],
    how="left"
)

# ---------- 🔥 FALLBACK KEY ONLY ----------
fallback = df[df["Χρόνος Παράδοσης"].isna()].copy()

fallback = fallback.drop(columns=["Χρόνος Παράδοσης"])

fallback = fallback.merge(
    master[["KEY_CLEAN", "Χρόνος Παράδοσης"]],
    on="KEY_CLEAN",
    how="left"
)

df.loc[fallback.index, "Χρόνος Παράδοσης"] = \
df.loc[fallback.index, "Χρόνος Παράδοσης"].combine_first(
    fallback["Χρόνος Παράδοσης"]
)

# ---------- FUZZY ----------
df["ADDR_CLEAN"] = df["Δ/νση Παράδοσης"].apply(clean_address)

unmatched = df[df["Χρόνος Παράδοσης"].isna()].copy()

def fuzzy_match(row):
    subset = master[master["KEY_CLEAN"] == row["KEY_CLEAN"]]

    if subset.empty:
        return None

    choices = subset["ADDR_CLEAN"].tolist()

    match = process.extractOne(
        row["ADDR_CLEAN"],
        choices,
        scorer=fuzz.token_sort_ratio
    )

    if match is None:
        return None

    _, score, idx = match

    if score >= 75:
        return subset.iloc[idx]["Χρόνος Παράδοσης"]

    return None

fuzzy_results = unmatched.apply(fuzzy_match, axis=1)
fuzzy_results = pd.to_numeric(fuzzy_results, errors="coerce")

df.loc[unmatched.index, "Χρόνος Παράδοσης"] = \
df.loc[unmatched.index, "Χρόνος Παράδοσης"].combine_first(fuzzy_results)

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

# ---------- KPIs ----------
total = len(df_original)

delivered_count = len(
    df_original[df_original["Ημ/νία Παράδοσης"].notna()]
)

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

st.write("Fuzzy matches:", fuzzy_results.notna().sum())
st.write("Delivered rows:", len(delivered))