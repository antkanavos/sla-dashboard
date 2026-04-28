import streamlit as st
import pandas as pd
import os
import json
import base64
import hashlib
import requests
import plotly.graph_objects as go
import plotly.express as px
from rapidfuzz import process, fuzz
from datetime import datetime, date
from collections import defaultdict

st.set_page_config(layout="wide", page_title="SLA Dashboard", page_icon="📦", initial_sidebar_state="expanded")

# ---------- CSS ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1a2235 !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #8fa3c0; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #8fa3c0 !important;
    font-size: 13px; font-weight: 500;
    padding: 8px 12px; border-radius: 8px;
    display: block; margin-bottom: 2px;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { color: white !important; background: rgba(255,255,255,0.06); }
[data-testid="stSidebarCollapseButton"] { display: flex !important; visibility: visible !important; }

/* When sidebar is collapsed — hide the gap entirely */
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 0 !important;
    width: 0 !important;
}
/* Collapsed control button — stays visible on the edge */
button[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    position: fixed !important;
    left: 0 !important;
    top: 50% !important;
    z-index: 999 !important;
    background: #1a2235 !important;
    border-radius: 0 8px 8px 0 !important;
    border: 1px solid #2a3550 !important;
    border-left: none !important;
    padding: 12px 6px !important;
}

.kpi-card { background: white; border-radius: 16px; padding: 22px 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #f0f2f5; }
.kpi-label { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #8fa3c0; margin-bottom: 6px; }
.kpi-value { font-size: 36px; font-weight: 800; color: #1a2235; line-height: 1.1; }
.kpi-sub { font-size: 12px; color: #8fa3c0; margin-top: 5px; font-weight: 500; }
.kpi-purple { color: #7c3aed !important; }

.section-header { font-size: 13px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: #1a2235; }
.section-sub { font-size: 12px; color: #8fa3c0; font-weight: 500; margin-bottom: 14px; }

.chart-card { background: white; border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); border: 1px solid #f0f2f5; }
.chart-label { font-size: 12px; font-weight: 700; color: #8fa3c0; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 2px; }
.legend-row { display: flex; align-items: center; gap: 7px; font-size: 12px; color: #444; margin-bottom: 4px; font-weight: 500; }
.legend-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.total-lbl { font-size: 11px; color: #8fa3c0; font-weight: 500; margin-top: 8px; }
.total-val { font-size: 14px; font-weight: 700; color: #1a2235; }

.month-card { background: white; border-radius: 14px; padding: 20px 22px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); border: 1px solid #f0f2f5; }
.month-title { font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #8fa3c0; margin-bottom: 12px; }
.bar-lbl { font-size: 12px; color: #444; font-weight: 500; margin-bottom: 3px; }
.bar-wrap { background: #f0f2f5; border-radius: 6px; height: 9px; margin-bottom: 11px; overflow: hidden; }

.hist-card { background: white; border-radius: 14px; padding: 14px 18px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); border: 1px solid #f0f2f5; margin-bottom: 10px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 700; }
.badge-green { background: #dcfce7; color: #16a34a; }
.badge-orange { background: #ffedd5; color: #c2410c; }
.badge-red { background: #fee2e2; color: #b91c1c; }

.divider { border: none; border-top: 1px solid #e8ecf4; margin: 16px 0; }
.snap-ok   { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 10px 14px; font-size: 12px; color: #166534; font-weight: 600; margin-bottom: 12px; }
.snap-warn { background: #fefce8; border: 1px solid #fde68a; border-radius: 10px; padding: 10px 14px; font-size: 12px; color: #92400e; font-weight: 600; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

# ---------- PASSWORD ----------
PASSWORD = st.secrets.get("APP_PASSWORD", os.getenv("APP_PASSWORD", "1234"))

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if not st.session_state.password_correct:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("### 🔐 SLA Dashboard")
            pw = st.text_input("Κωδικός", type="password")
            if pw == PASSWORD:
                st.session_state.password_correct = True
                st.rerun()
            elif pw:
                st.error("Λάθος κωδικός")
        st.stop()

check_password()

# ---------- GITHUB HELPERS ----------
GH        = st.secrets.get("github", {})
GH_TOKEN  = GH.get("token", "")
GH_REPO   = GH.get("repo", "")
GH_BRANCH = GH.get("branch", "main")
GH_HDR    = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def gh_get(path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}?ref={GH_BRANCH}"
    r = requests.get(url, headers=GH_HDR, timeout=10)
    if r.status_code == 200:
        d = r.json()
        return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]
    return None, None

def gh_put(path, content_str, message, sha=None):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_str.encode()).decode(),
        "branch": GH_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=GH_HDR, json=payload, timeout=15)
    return r.status_code in (200, 201)

@st.cache_data(ttl=60)
def load_index():
    c, _ = gh_get("history/index.json")
    return json.loads(c) if c else []

def load_detail(date_str):
    c, _ = gh_get(f"history/{date_str}.json")
    return json.loads(c) if c else None

# ---------- HELPERS ----------
@st.cache_data(ttl=3600)
def load_sla_master():
    return pd.read_csv(f"{GH_RAW}/master.csv")

@st.cache_data(ttl=3600)
def load_holidays():
    hol_df = pd.read_csv(f"{GH_RAW}/holidays.csv")
    return set(pd.to_datetime(hol_df["date"], dayfirst=True).dt.date)

def clean_addr(x):
    if pd.isna(x) or str(x).strip() in ("","nan"): return None
    x = str(x).upper().replace("-"," ").replace(",","").replace(".","")
    for a,b in [("ΟΔΟΣ",""),("ΑΓΙΟΥ","ΑΓ"),("ΑΓΙΑΣ","ΑΓ"),("ΚΑΙ","&")]:
        x = x.replace(a,b)
    return " ".join(x.strip().split())

def clean_pc(x):
    if pd.isna(x): return None
    x = "".join(filter(str.isdigit, str(x).replace(".0","").replace(" ","").replace("-","")))
    return x[:5] if len(x) >= 5 else x

def do_sla_matching(df, master):
    master = master.copy()
    master["KEY_CLEAN"]  = master["KEY1"].str.extract(r"(\d+)")
    master["ADDR_CLEAN"] = master["Full Address"].apply(clean_addr)
    master["POSTCODE"]   = master["Account : Site : Site PostCode"].apply(clean_pc)

    df = df.reset_index(drop=True).copy()
    df["SLA_matched"] = None
    df["RU_matched"]  = None

    # Step 1: KEY + POSTCODE exact
    m1 = master.sort_values("Χρόνος Παράδοσης").drop_duplicates(["KEY_CLEAN","POSTCODE"], keep="first")
    merged = df[["KEY_CLEAN","POSTCODE"]].merge(
        m1[["KEY_CLEAN","POSTCODE","Χρόνος Παράδοσης","Regional Unity"]], on=["KEY_CLEAN","POSTCODE"], how="left"
    )
    s1 = merged["Χρόνος Παράδοσης"].notna().values
    df.loc[s1, "SLA_matched"] = merged.loc[s1, "Χρόνος Παράδοσης"].values
    df.loc[s1, "RU_matched"]  = merged.loc[s1, "Regional Unity"].values

    # Step 2: fuzzy for multi-SLA keys (within same KEY)
    multi_keys = set(master.groupby("KEY_CLEAN")["Χρόνος Παράδοσης"].nunique()[lambda x: x>1].index)
    um2 = df.index[df["SLA_matched"].isna() & df["KEY_CLEAN"].isin(multi_keys)]
    if len(um2):
        def fmatch(row):
            sub = master[master["KEY_CLEAN"]==row["KEY_CLEAN"]]
            if sub.empty: return None, None
            m = process.extractOne(row["ADDR_CLEAN"], sub["ADDR_CLEAN"].tolist(), scorer=fuzz.token_sort_ratio)
            if m and m[1]>=75:
                hit = sub.iloc[m[2]]
                return hit["Χρόνος Παράδοσης"], hit.get("Regional Unity")
            return None, None
        res = [fmatch(df.loc[i]) for i in um2]
        df.loc[um2, "SLA_matched"] = [r[0] for r in res]
        df.loc[um2, "RU_matched"]  = [r[1] for r in res]

    # Step 3: KEY only (single-SLA keys)
    single_keys = master.groupby("KEY_CLEAN").filter(lambda x: x["Χρόνος Παράδοσης"].nunique()==1)
    key_sla = single_keys.drop_duplicates("KEY_CLEAN")[["KEY_CLEAN","Χρόνος Παράδοσης","Regional Unity"]]
    um3 = df.index[df["SLA_matched"].isna()]
    if len(um3):
        m3 = df.loc[um3,["KEY_CLEAN"]].merge(key_sla, on="KEY_CLEAN", how="left")
        m3.index = um3
        s3 = m3["Χρόνος Παράδοσης"].notna()
        df.loc[um3[s3], "SLA_matched"] = m3.loc[s3,"Χρόνος Παράδοσης"].values
        df.loc[um3[s3], "RU_matched"]  = m3.loc[s3,"Regional Unity"].values

    # Step 4: POSTCODE dominant
    pcm = master.groupby("POSTCODE")["Χρόνος Παράδοσης"].agg(lambda x: x.mode()[0]).reset_index()
    um4 = df.index[df["SLA_matched"].isna()]
    if len(um4):
        m4 = df.loc[um4,["POSTCODE"]].merge(pcm, on="POSTCODE", how="left")
        m4.index = um4
        s4 = m4["Χρόνος Παράδοσης"].notna()
        df.loc[um4[s4], "SLA_matched"] = m4.loc[s4,"Χρόνος Παράδοσης"].values

    # Step 5: PC3 prefix
    master["PC3"] = master["POSTCODE"].str[:3]
    df["PC3"]     = df["POSTCODE"].str[:3]
    pc3m = master.groupby("PC3")["Χρόνος Παράδοσης"].agg(lambda x: x.mode()[0]).reset_index()
    um5 = df.index[df["SLA_matched"].isna()]
    if len(um5):
        m5 = df.loc[um5,["PC3"]].merge(pc3m, on="PC3", how="left")
        m5.index = um5
        s5 = m5["Χρόνος Παράδοσης"].notna()
        df.loc[um5[s5], "SLA_matched"] = m5.loc[s5,"Χρόνος Παράδοσης"].values
    df.drop(columns=["PC3"], inplace=True, errors="ignore")

    df["Χρόνος Παράδοσης"] = pd.to_numeric(df["SLA_matched"], errors="coerce")
    df["Regional Unity"]   = df["RU_matched"]
    df.drop(columns=["SLA_matched","RU_matched"], inplace=True)
    return df

# ---------- MASTER TABLE ----------
MASTER_TABLE_PATH = "history/master_table.csv"  # kept for reference only

# ---------- GOOGLE SHEETS ----------
def get_gsheet():
    import gspread
    from google.oauth2.service_account import Credentials
    gs = st.secrets.get("gsheets", {})
    creds_dict = {
        "type":                        gs.get("type", "service_account"),
        "project_id":                  gs.get("project_id"),
        "private_key_id":              gs.get("private_key_id"),
        "private_key":                 gs.get("private_key"),
        "client_email":                gs.get("client_email"),
        "client_id":                   gs.get("client_id"),
        "token_uri":                   gs.get("token_uri", "https://oauth2.googleapis.com/token"),
        "auth_uri":                    "https://accounts.google.com/o/oauth2/auth",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "universe_domain":             "googleapis.com",
    }
    creds  = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    return client.open_by_key(gs.get("spreadsheet_id","")).sheet1

@st.cache_data(ttl=30)
def load_master_table():
    try:
        ws   = get_gsheet()
        data = ws.get_all_records(default_blank="")
        if not data:
            return pd.DataFrame(), None
        df = pd.DataFrame(data, dtype=str)
        # Replace "nan" strings with empty
        df = df.replace({"nan":"", "NaT":"", "None":""})
        return df, None
    except Exception as e:
        return pd.DataFrame(), None

def save_master_table(df_master, sha=None):
    load_master_table.clear()
    load_and_process.clear()
    try:
        ws      = get_gsheet()
        headers = df_master.columns.tolist()
        rows    = df_master.fillna("").astype(str).values.tolist()
        ws.clear()
        ws.update([headers] + rows)
        return True
    except Exception as e:
        st.error(f"Google Sheets save error: {e}")
        return False

def normalize_date(d):
    """Normalize date string to dd/mm/yyyy for consistent comparison."""
    if not d or str(d).strip() in ("","nan","NaT","None"):
        return ""
    try:
        return pd.to_datetime(str(d), dayfirst=True, errors="coerce").strftime("%d/%m/%Y")
    except:
        return str(d).strip()

def update_master_table(df_new):
    """
    Merge df_new into master_table.
    - Νέα εγγραφή → προσθήκη (χωρίς SLA/Working_Days ακόμα)
    - Υπάρχει + delivered → skip
    - Υπάρχει + pending + τώρα delivered → overwrite Ημ_Παράδοσης, καθαρισμός Working_Days
    - Υπάρχει + pending + ακόμα pending → skip
    """
    existing, sha = load_master_table()
    df_new = df_new.copy()
    # Φιλτράρισμα εγγραφών χωρίς KEY
    df_new["_key_clean"] = df_new["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
    df_new = df_new[df_new["_key_clean"].notna()].drop(columns=["_key_clean"])
    df_new = df_new.reset_index(drop=True)
    df_new["Αριθμός"] = df_new["Αριθμός"].astype(str)
    df_new["Ημ/νία Παράδοσης_str"] = df_new["Ημ/νία Παράδοσης"].astype(str).replace("NaT","")

    new_cols = ["Αριθμός","Ημ_Δημιουργίας","Ημ_Παράδοσης","Key","Διεύθυνση","ΤΚ",
                "Κωδ_Καταστήματος","Κατάστημα","SLA","Regional_Unity","Working_Days"]

    if existing.empty:
        rows = []
        for _, row in df_new.iterrows():
            rows.append({
                "Αριθμός":          str(row["Αριθμός"]),
                "Ημ_Δημιουργίας":   normalize_date(str(row["Ημ/νία Δημιουργίας"])),
                "Ημ_Παράδοσης":     normalize_date(str(row["Ημ/νία Παράδοσης_str"]).strip()),
                "Key":              str(row["Κλειδί Πελάτη 3"]),
                "Διεύθυνση":        str(row["Δ/νση Παράδοσης"]),
                "ΤΚ":               str(row["Τ.Κ Παράδοσης"]),
                "Κωδ_Καταστήματος": str(row.get("Κωδ. Καταστήματος Παράδοσης", "")),
                "Κατάστημα":        str(row.get("Κατάστημα Παραλαβής", "")),
                "SLA":              "",
                "Regional_Unity":   "",
                "Working_Days":     "",
            })
        result = pd.DataFrame(rows, columns=new_cols)
        return result, len(result), 0, True, sha

    existing["Αριθμός"] = existing["Αριθμός"].astype(str)
    # Ensure new columns exist
    for col in ["SLA","Regional_Unity","Working_Days"]:
        if col not in existing.columns:
            existing[col] = ""

    existing_idx = existing.set_index("Αριθμός")
    n_new = 0; n_updated = 0
    rows_to_add = []

    for _, row in df_new.iterrows():
        ar      = str(row["Αριθμός"])
        new_del = normalize_date(str(row["Ημ/νία Παράδοσης_str"]).strip())

        if ar not in existing_idx.index:
            rows_to_add.append({
                "Αριθμός":          ar,
                "Ημ_Δημιουργίας":   normalize_date(str(row["Ημ/νία Δημιουργίας"])),
                "Ημ_Παράδοσης":     new_del,
                "Key":              str(row["Κλειδί Πελάτη 3"]),
                "Διεύθυνση":        str(row["Δ/νση Παράδοσης"]),
                "ΤΚ":               str(row["Τ.Κ Παράδοσης"]),
                "Κωδ_Καταστήματος": str(row.get("Κωδ. Καταστήματος Παράδοσης", "")),
                "Κατάστημα":        str(row.get("Κατάστημα Παραλαβής", "")),
                "SLA":              "",
                "Regional_Unity":   "",
                "Working_Days":     "",
            })
            n_new += 1
        else:
            existing_del = normalize_date(str(existing_idx.loc[ar, "Ημ_Παράδοσης"]).strip())
            if existing_del:
                pass  # already delivered → skip
            elif new_del:
                # pending → delivered
                existing.loc[existing["Αριθμός"]==ar, "Ημ_Παράδοσης"] = new_del
                existing.loc[existing["Αριθμός"]==ar, "Working_Days"]  = ""
                n_updated += 1

    if rows_to_add:
        existing = pd.concat([existing, pd.DataFrame(rows_to_add, columns=new_cols)], ignore_index=True)

    changed = (n_new > 0) or (n_updated > 0)
    return existing, n_new, n_updated, changed, sha

def save_snapshot(snap, force_new_id=False):
    """Save snapshot — uses data_hash as unique ID so each data change = new snapshot."""
    snap_id   = snap["snapshot_id"]  # hash-based unique ID
    path      = f"history/{snap_id}.json"
    c_str     = json.dumps(snap, ensure_ascii=False, indent=2)
    _, old_sha = gh_get(path)
    ok1 = gh_put(path, c_str, f"snapshot: {snap['date']} ({snap_id})", old_sha)

    index = load_index()
    load_index.clear()
    # Never remove — every upload with changes gets its own entry
    index.append({
        "snapshot_id": snap_id,
        "date":        snap["date"],
        "uploaded_at": snap["created_at"],
        "total":       snap["total"],
        "delivered":   snap["delivered"],
        "on_time":     snap["on_time"],
        "sla_pct":     snap["sla_pct"],
        "missing_sla": snap["missing_sla"],
        "n_new":       snap.get("n_new", 0),
        "n_updated":   snap.get("n_updated", 0),
    })
    index.sort(key=lambda x: x.get("uploaded_at", x.get("date", "")))
    _, idx_sha = gh_get("history/index.json")
    ok2 = gh_put("history/index.json",
                 json.dumps(index, ensure_ascii=False, indent=2),
                 f"index: {snap['date']}", idx_sha)
    return ok1 and ok2

# ---------- DATA LOADING ----------
GH_RAW = f"https://raw.githubusercontent.com/{GH_REPO}/refs/heads/{GH_BRANCH}"

# Module-level singleton
_DF_FULL = None
_DF_HASH = None

@st.cache_resource
@st.cache_resource
def load_and_process():
    from io import StringIO
    import numpy as np

    master_sla = load_sla_master()
    holidays   = load_holidays()

    # Load master_table from Google Sheets
    mt, _ = load_master_table()
    mt_sha = None

    if mt is not None and len(mt) > 0:
        st.session_state["_mt_cols"] = mt.columns.tolist()

    if mt is None or len(mt) == 0 or "Ημ_Δημιουργίας" not in (mt.columns.tolist() if mt is not None else []):
        df_raw = pd.read_csv(f"{GH_RAW}/data.csv")
        df_raw["KEY_CLEAN"] = df_raw["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
        df_raw = df_raw[df_raw["KEY_CLEAN"].notna()].reset_index(drop=True)
        if "Κωδ. Καταστήματος Παράδοσης" in df_raw.columns:
            df_raw["Κατάστημα"] = (
                df_raw["Κωδ. Καταστήματος Παράδοσης"].astype(str).str.strip() + " " +
                df_raw["Κατάστημα Παραλαβής"].astype(str).str.strip()
            ).str.strip().replace({"nan nan":"—","nan":"—"})
        else:
            df_raw["Κατάστημα"] = "—"
        df_raw["ADDR_CLEAN"] = df_raw["Δ/νση Παράδοσης"].apply(clean_addr)
        df_raw["POSTCODE"]   = df_raw["Τ.Κ Παράδοσης"].apply(clean_pc)
        df_raw = do_sla_matching(df_raw, master_sla)
        df_raw["Ημ/νία Δημιουργίας"] = pd.to_datetime(df_raw["Ημ/νία Δημιουργίας"], dayfirst=True, errors="coerce")
        df_raw["Ημ/νία Παράδοσης"]   = pd.to_datetime(df_raw["Ημ/νία Παράδοσης"],   dayfirst=True, errors="coerce")
        df_raw["sla_days"] = df_raw["Χρόνος Παράδοσης"].map({24:1, 48:2, 96:4})
        def wdays(start, end):
            if pd.isna(end) or pd.isna(start): return None
            days = pd.date_range(start, end)
            return len([d for d in days if d.weekday()!=6 and d.date() not in holidays]) - 1
        df_raw["working_days"] = df_raw.apply(lambda x: wdays(x["Ημ/νία Δημιουργίας"], x["Ημ/νία Παράδοσης"]), axis=1)
        return df_raw

    # ── Normal path: master_table has data ──
    mt_sha = mt_sha  # keep sha for saving later
    for col in ["SLA","Regional_Unity","Working_Days"]:
        if col not in mt.columns:
            mt[col] = ""

    # Rename to working column names
    col_map = {
        "Ημ_Δημιουργίας": "Ημ/νία Δημιουργίας",
        "Ημ_Παράδοσης":   "Ημ/νία Παράδοσης",
        "Key":            "Κλειδί Πελάτη 3",
        "Διεύθυνση":      "Δ/νση Παράδοσης",
        "ΤΚ":             "Τ.Κ Παράδοσης",
        "Κωδ_Καταστήματος": "Κωδ. Καταστήματος Παράδοσης",
        "Κατάστημα":      "Κατάστημα Παραλαβής",
    }
    df = mt.rename(columns=col_map)

    # KEY_CLEAN
    df["KEY_CLEAN"] = df["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
    df = df[df["KEY_CLEAN"].notna()].reset_index(drop=True)

    # Κατάστημα combined
    if "Κωδ. Καταστήματος Παράδοσης" in df.columns:
        df["Κατάστημα"] = (
            df["Κωδ. Καταστήματος Παράδοσης"].astype(str).str.strip() + " " +
            df["Κατάστημα Παραλαβής"].astype(str).str.strip()
        ).str.strip().replace({"nan nan":"—","nan":"—"})
    else:
        df["Κατάστημα"] = "—"

    df["ADDR_CLEAN"] = df["Δ/νση Παράδοσης"].apply(clean_addr)
    df["POSTCODE"]   = df["Τ.Κ Παράδοσης"].apply(clean_pc)

    # ── SLA matching only for rows without SLA ──
    needs_sla = df["SLA"].isna() | (df["SLA"].astype(str).str.strip().isin(["","nan"]))
    needs_sla_count = needs_sla.sum()

    if needs_sla_count > 0:
        df_to_match = df[needs_sla].copy().reset_index(drop=True)
        df_to_match["orig_idx"] = df[needs_sla].index.tolist()
        matched = do_sla_matching(df_to_match, master_sla)
        for i, orig_i in enumerate(df_to_match["orig_idx"]):
            df.at[orig_i, "SLA"]           = str(matched.at[i, "Χρόνος Παράδοσης"]) if pd.notna(matched.at[i, "Χρόνος Παράδοσης"]) else ""
            df.at[orig_i, "Regional_Unity"] = str(matched.at[i, "Regional Unity"])   if pd.notna(matched.at[i, "Regional Unity"])   else ""

    # ── Parse dates ──
    df["Ημ/νία Δημιουργίας"] = pd.to_datetime(df["Ημ/νία Δημιουργίας"], dayfirst=True, errors="coerce")
    df["Ημ/νία Παράδοσης"]   = pd.to_datetime(df["Ημ/νία Παράδοσης"],   errors="coerce")
    df["Χρόνος Παράδοσης"]   = pd.to_numeric(df["SLA"], errors="coerce")
    df["Regional Unity"]      = df["Regional_Unity"].replace({"nan":"", "":None})
    df["sla_days"] = df["Χρόνος Παράδοσης"].map({24:1, 48:2, 96:4})

    # ── Working days — vectorized, only for delivered rows without cached value ──
    delivered_mask = df["Ημ/νία Παράδοσης"].notna()
    needs_wd = delivered_mask & (df["Working_Days"].isna() | df["Working_Days"].astype(str).str.strip().isin(["","nan"]))

    if needs_wd.sum() > 0:
        import numpy as np

        sub = df[needs_wd][["Ημ/νία Δημιουργίας","Ημ/νία Παράδοσης"]].copy()
        holiday_dates = set(holidays)

        results = []
        for s, e in zip(sub["Ημ/νία Δημιουργίας"], sub["Ημ/νία Παράδοσης"]):
            if pd.isna(s) or pd.isna(e):
                results.append("")
                continue
            days = pd.date_range(s, e)
            wd = len([d for d in days if d.weekday() != 6 and d.date() not in holiday_dates]) - 1
            results.append(str(max(0, wd)))

        df.loc[needs_wd, "Working_Days"] = results

    df["working_days"] = pd.to_numeric(df["Working_Days"], errors="coerce")
    return df

with st.spinner("Φόρτωση δεδομένων..."):
    df_full = load_and_process()

if "_mt_cols" in st.session_state:
    st.write("DEBUG Sheet columns:", st.session_state["_mt_cols"])

# ---------- METRICS ----------
def metrics(df):
    d = df[(df["Ημ/νία Παράδοσης"].notna()) & (df["sla_days"].notna())].copy()
    if not len(d): return d, {}
    d["on_time"]    = d["working_days"] <= d["sla_days"]
    d["delay_days"] = (d["working_days"] - d["sla_days"]).clip(lower=0)
    ot = int(d["on_time"].sum())
    return d, {
        "total":       len(df),
        "delivered":   int(df["Ημ/νία Παράδοσης"].notna().sum()),
        "on_time":     ot,
        "sla_pct":     round(ot/len(d)*100,2) if len(d) else 0,
        "missing_sla": int(df["sla_days"].isna().sum()),
    }

def build_snapshot(df, m, del_df, n_new=0, n_updated=0):
    data_hash = hashlib.md5(df["Αριθμός"].astype(str).sort_values().str.cat().encode()).hexdigest()[:12]
    snap_date = df["Ημ/νία Δημιουργίας"].max().strftime("%Y-%m-%d")
    sla_bd = {}
    for h,d,lbl in [(24,1,"24h"),(48,2,"48h"),(96,4,"96h")]:
        g  = del_df[del_df["sla_days"]==d]
        ot = int(g["on_time"].sum()) if len(g) else 0
        sla_bd[lbl] = {"total":len(g),"on_time":ot,"pct":round(ot/len(g)*100,2) if len(g) else 0}
    missed = del_df[~del_df["on_time"]]
    top_missed = (missed.groupby("KEY_CLEAN").size().sort_values(ascending=False).head(20)
                  .reset_index().rename(columns={0:"misses"}).to_dict(orient="records"))
    regional = {}
    if "Regional Unity" in del_df.columns:
        for reg, grp in del_df.groupby("Regional Unity"):
            if pd.isna(reg): continue
            ot_r = int(grp["on_time"].sum())
            regional[str(reg)] = {"total":len(grp),"on_time":ot_r,"pct":round(ot_r/len(grp)*100,2)}
    return {
        "snapshot_id": data_hash,
        "date":        snap_date,
        **m,
        "n_new":       n_new,
        "n_updated":   n_updated,
        "sla_breakdown": sla_bd,
        "delay_counts": {"1d":int((del_df["delay_days"]==1).sum()),
                         "2d":int((del_df["delay_days"]==2).sum()),
                         "3d+":int((del_df["delay_days"]>=3).sum())},
        "top_missed_customers": top_missed,
        "regional": regional,
        "created_at": datetime.now().isoformat(),
    }

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("""
    <div style='padding:20px 16px 8px;display:flex;align-items:center;gap:10px;'>
        <span style='font-size:20px;'>📦</span>
        <span style='font-size:14px;font-weight:800;color:white !important;'>SLA Dashboard</span>
    </div>
    <hr style='border-color:#2a3550;margin:6px 0 14px;'>
    """, unsafe_allow_html=True)

    page = st.radio("Πλοήγηση", [
        "🏠  Επισκόπηση",
        "🗺️  Ανάλυση Νομού",
        "🏪  Ανάλυση Καταστήματος",
    ], label_visibility="collapsed")

    st.markdown(f"""
    <div style='position:fixed;bottom:20px;width:178px;'>
        <div style='font-size:10px;color:#3a5070;font-weight:600;'>Τελευταία ενημέρωση</div>
        <div style='font-size:11px;color:#5a7090;'>{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>""", unsafe_allow_html=True)

# ---------- FILTERS ----------
min_d = df_full["Ημ/νία Δημιουργίας"].min().date()
max_d = df_full["Ημ/νία Δημιουργίας"].max().date()
date_from   = min_d
date_to     = max_d
shop_filter = "Όλα"

if "Επισκόπηση" in page:
    shops = ["Όλα"] + sorted(df_full["Κατάστημα"].dropna().unique().tolist())
    fc1,fc2,fc3,fc4 = st.columns([2,2,3,3])
    with fc1: date_from   = st.date_input("Από", value=min_d, min_value=min_d, max_value=max_d, key="ep_df")
    with fc2: date_to     = st.date_input("Έως", value=max_d, min_value=min_d, max_value=max_d, key="ep_dt")
    with fc3: shop_filter = st.selectbox("Κατάστημα", shops, key="ep_shop")
    with fc4: st.markdown(f"<div style='text-align:right;font-size:11px;color:#8fa3c0;padding-top:28px;'>Φίλτρο βάσει <b>ημ. δημιουργίας</b> &nbsp;·&nbsp; {datetime.now().strftime('%d/%m/%Y %H:%M')} 🔄</div>", unsafe_allow_html=True)

df = df_full[
    (df_full["Ημ/νία Δημιουργίας"].dt.date >= date_from) &
    (df_full["Ημ/νία Δημιουργίας"].dt.date <= date_to)
].copy()
if shop_filter != "Όλα":
    df = df[df["Κατάστημα"] == shop_filter].copy()
delivered, m = metrics(df)

# ══════════════════════════════════════════════
# PAGE: ΕΠΙΣΚΟΠΗΣΗ
# ══════════════════════════════════════════════
if "Επισκόπηση" in page:

    # KPIs
    k1,k2,k3,k4,k5 = st.columns(5)
    kpi_data = [
        (k1,"📦","ΣΥΝΟΛΟ ΑΠΟΣΤΟΛΩΝ", f"{m['total']:,}", "100%", ""),
        (k2,"✅","ΠΑΡΑΔΟΘΗΚΑΝ", f"{m['delivered']:,}", f"{m['delivered']/m['total']*100:.2f}% του συνόλου" if m['total'] else "—", ""),
        (k3,"🎯","ΕΝΤΟΣ SLA", f"{m['on_time']:,}", f"{m['on_time']/m['delivered']*100:.2f}% παραδοθέντων" if m['delivered'] else "—", ""),
        (k4,"📈","SLA % (ΕΝΤΟΣ)", f"{m['sla_pct']:.2f}%", f"{m['on_time']:,} / {m['delivered']:,}", "kpi-purple"),
        (k5,"⚠️","MISSING SLA", f"{m['missing_sla']:,}", "χωρίς αντιστοίχιση", ""),
    ]
    for col,icon,lbl,val,sub,cls in kpi_data:
        with col:
            st.markdown(f"""<div class="kpi-card">
                <div style="font-size:26px;margin-bottom:8px;">{icon}</div>
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value {cls}">{val}</div>
                <div class="kpi-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Donut helper — renders as full-width SVG inside a white card, no plotly widget
    def donut_html(pct, c_in, c_out, label):
        """Pure SVG donut — fixed geometry so nothing gets clipped"""
        r = 38; cx = cy = 50; stroke = 12
        circumference = 2 * 3.14159 * r
        filled = circumference * pct / 100
        gap    = circumference - filled
        return f"""
        <div style="text-align:center;padding:6px 0 2px;">
            <div style="font-size:10px;font-weight:700;color:#8fa3c0;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;line-height:1.3;">{label}</div>
            <svg viewBox="0 0 100 100" width="100" height="100" style="display:block;margin:0 auto;">
                <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c_out}" stroke-width="{stroke}"/>
                <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c_in}" stroke-width="{stroke}"
                    stroke-dasharray="{filled:.2f} {gap:.2f}"
                    stroke-linecap="round"
                    transform="rotate(-90 {cx} {cy})"/>
                <text x="{cx}" y="{cy-4}" text-anchor="middle" dominant-baseline="central"
                    font-family="Plus Jakarta Sans,sans-serif" font-size="15" font-weight="800" fill="#1a2235">{pct:.1f}%</text>
                <text x="{cx}" y="{cy+13}" text-anchor="middle"
                    font-family="Plus Jakarta Sans,sans-serif" font-size="7" font-weight="600" fill="#8fa3c0">εντός SLA</text>
            </svg>
        </div>"""

    def donut_svg(pct, c_in, c_out, size=200):
        r = 72; cx = cy = 90; stroke = 18
        circ = 2 * 3.14159 * r
        filled = circ * pct / 100
        gap = circ - filled
        return f"""<svg viewBox="0 0 180 180" width="{size}" height="{size}" style="flex-shrink:0;">
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c_out}" stroke-width="{stroke}"/>
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c_in}" stroke-width="{stroke}"
                stroke-dasharray="{filled:.2f} {gap:.2f}" stroke-linecap="round"
                transform="rotate(-90 {cx} {cy})"/>
            <text x="{cx}" y="{cy-8}" text-anchor="middle" dominant-baseline="central"
                font-family="Plus Jakarta Sans,sans-serif" font-size="26" font-weight="800" fill="#1a2235">{pct:.1f}%</text>
            <text x="{cx}" y="{cy+18}" text-anchor="middle"
                font-family="Plus Jakarta Sans,sans-serif" font-size="11" font-weight="600" fill="#8fa3c0">εντός SLA</text>
        </svg>"""

    def seg_svg(d24, d48, d96, size=200):
        total = d24 + d48 + d96
        r = 72; cx = cy = 90; sw = 18
        circ = 2 * 3.14159265 * r
        if total == 0:
            return f"""<svg viewBox="0 0 180 180" width="{size}" height="{size}" style="flex-shrink:0;">
                <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#f0f2f5" stroke-width="{sw}"/>
                <text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central"
                    font-family="Plus Jakarta Sans,sans-serif" font-size="26" font-weight="800" fill="#1a2235">0</text>
            </svg>"""
        gap = circ * 0.016
        def seg(count, color, offset):
            length = (count/total)*circ - gap
            if length <= 0: return ""
            return f"""<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}"
                stroke-dasharray="{length:.3f} {circ-length:.3f}" stroke-linecap="butt"
                transform="rotate({offset-90} {cx} {cy})"/>"""
        a24=(d24/total)*360; a48=(d48/total)*360
        return f"""<svg viewBox="0 0 180 180" width="{size}" height="{size}" style="flex-shrink:0;">
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#f0f2f5" stroke-width="{sw}"/>
            {seg(d24,"#22c55e",0)}{seg(d48,"#f97316",a24)}{seg(d96,"#ef4444",a24+a48)}
            <text x="{cx}" y="{cy-8}" text-anchor="middle" dominant-baseline="central"
                font-family="Plus Jakarta Sans,sans-serif" font-size="26" font-weight="800" fill="#1a2235">{total:,}</text>
            <text x="{cx}" y="{cy+18}" text-anchor="middle"
                font-family="Plus Jakarta Sans,sans-serif" font-size="11" font-weight="600" fill="#8fa3c0">αποστολές</text>
        </svg>"""

    def card_sla(g, lbl):
        if not len(g):
            return f'<div style="background:white;border-radius:14px;padding:20px;box-shadow:0 1px 8px rgba(0,0,0,0.07);border:1px solid #f0f2f5;min-height:200px;"><div style="font-size:11px;font-weight:700;color:#8fa3c0;text-transform:uppercase;">{lbl}</div><div style="color:#ccc;font-size:12px;margin-top:8px;">Δεν υπάρχουν</div></div>'
        ot  = int(g["on_time"].sum()); lat = len(g)-ot; pct = ot/len(g)*100
        return f"""<div style="background:white;border-radius:14px;padding:16px 20px;box-shadow:0 1px 8px rgba(0,0,0,0.07);border:1px solid #f0f2f5;display:flex;align-items:center;gap:20px;">
            {donut_svg(pct,"#22c55e","#fee2e2")}
            <div style="flex:1;min-width:0;">
                <div style="font-size:11px;font-weight:700;color:#8fa3c0;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:14px;">{lbl}</div>
                <div style="font-size:13px;color:#444;font-weight:500;margin-bottom:6px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e;margin-right:7px;"></span>Εντός &nbsp;<b style="color:#1a2235;font-size:15px;">{ot:,}</b> <span style="color:#8fa3c0">({pct:.2f}%)</span></div>
                <div style="font-size:13px;color:#444;font-weight:500;margin-bottom:14px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;margin-right:7px;"></span>Εκτός &nbsp;<b style="color:#1a2235;font-size:15px;">{lat:,}</b> <span style="color:#8fa3c0">({100-pct:.2f}%)</span></div>
                <div style="font-size:11px;color:#8fa3c0;font-weight:500;">Σύνολο παραδοθέντων</div>
                <div style="font-size:18px;font-weight:800;color:#1a2235;">{len(g):,}</div>
            </div>
        </div>"""

    def card_delay(dd, lbl, td):
        n   = len(dd)
        d24 = len(dd[dd["sla_days"]==1]); d48 = len(dd[dd["sla_days"]==2]); d96 = len(dd[dd["sla_days"]==4])
        p24 = round(d24/n*100,1) if n else 0; p48 = round(d48/n*100,1) if n else 0; p96 = round(d96/n*100,1) if n else 0
        pct_tot = round(n/td*100,1) if td else 0
        return f"""<div style="background:white;border-radius:14px;padding:16px 20px;box-shadow:0 1px 8px rgba(0,0,0,0.07);border:1px solid #f0f2f5;display:flex;align-items:center;gap:20px;">
            {seg_svg(d24,d48,d96)}
            <div style="flex:1;min-width:0;">
                <div style="font-size:11px;font-weight:700;color:#8fa3c0;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:14px;">{lbl} καθυστέρηση</div>
                <div style="font-size:13px;color:#444;font-weight:500;margin-bottom:6px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e;margin-right:7px;"></span>24h &nbsp;<b style="color:#1a2235;font-size:15px;">{d24:,}</b> <span style="color:#8fa3c0">({p24}%)</span></div>
                <div style="font-size:13px;color:#444;font-weight:500;margin-bottom:6px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f97316;margin-right:7px;"></span>48h &nbsp;<b style="color:#1a2235;font-size:15px;">{d48:,}</b> <span style="color:#8fa3c0">({p48}%)</span></div>
                <div style="font-size:13px;color:#444;font-weight:500;margin-bottom:14px;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;margin-right:7px;"></span>96h &nbsp;<b style="color:#1a2235;font-size:15px;">{d96:,}</b> <span style="color:#8fa3c0">({p96}%)</span></div>
                <div style="font-size:11px;color:#8fa3c0;font-weight:500;">% επί παραδοθέντων</div>
                <div style="font-size:18px;font-weight:800;color:#1a2235;">{pct_tot}%</div>
            </div>
        </div>"""

    td = len(delivered)

    # Row 1: SLA by type
    st.markdown('<div class="section-header">ΑΝΑΛΥΣΗ ΑΝΑ ΖΩΝΗ ΠΑΡΑΔΟΣΗΣ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">(ΟΛΟ ΤΟ ΔΙΑΣΤΗΜΑ)</div>', unsafe_allow_html=True)
    r1c1, r1c2, r1c3 = st.columns(3)
    for col, sd, lbl in [(r1c1,1,"24h (1 εργάσιμη)"),(r1c2,2,"48h (2 εργάσιμες)"),(r1c3,4,"96h (4 εργάσιμες)")]:
        with col:
            st.markdown(card_sla(delivered[delivered["sla_days"]==sd], lbl), unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Row 2: Delays
    st.markdown('<div class="section-header">ΚΑΘΥΣΤΕΡΗΣΗ ΠΑΡΑΔΟΣΕΩΝ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">(ΟΛΟ ΤΟ ΔΙΑΣΤΗΜΑ)</div>', unsafe_allow_html=True)
    r2c1, r2c2, r2c3 = st.columns(3)
    for col, days, use_gte, lbl in [(r2c1,1,False,"1 ημέρα"),(r2c2,2,False,"2 ημέρες"),(r2c3,3,True,"3+ ημέρες")]:
        with col:
            dd = delivered[delivered["delay_days"]>=days] if use_gte else delivered[delivered["delay_days"]==days]
            st.markdown(card_delay(dd, lbl, td), unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:10px;color:#8fa3c0;text-align:right;margin-top:4px;'>Σύνολο παραδοθέντων: {td:,}</div>", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Monthly
    st.markdown('<div class="section-header">ΜΗΝΙΑΙΑ ΕΠΙΔΟΣΗ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">(ΤΕΛΕΥΤΑΙΟΙ 3 ΗΜΕΡΟΛΟΓΙΑΚΟΙ ΜΗΝΕΣ)</div>', unsafe_allow_html=True)

    latest = df_full["Ημ/νία Δημιουργίας"].max()
    MGR    = {1:"ΙΑΝΟΥΑΡΙΟΣ",2:"ΦΕΒΡΟΥΑΡΙΟΣ",3:"ΜΑΡΤΙΟΣ",4:"ΑΠΡΙΛΙΟΣ",5:"ΜΑΙΟΣ",6:"ΙΟΥΝΙΟΣ",
              7:"ΙΟΥΛΙΟΣ",8:"ΑΥΓΟΥΣΤΟΣ",9:"ΣΕΠΤΕΜΒΡΙΟΣ",10:"ΟΚΤΩΒΡΙΟΣ",11:"ΝΟΕΜΒΡΙΟΣ",12:"ΔΕΚΕΜΒΡΙΟΣ"}
    months_show = []
    for i in range(2,-1,-1):
        mo = (latest.month-i-1)%12+1; yr = latest.year-((latest.month-i-1)//12)
        months_show.append((yr,mo))

    mc1,mc2,mc3 = st.columns(3)
    for col,(y,mo) in zip([mc1,mc2,mc3], months_show):
        with col:
            mask = (df_full["Ημ/νία Δημιουργίας"].dt.year==y)&(df_full["Ημ/νία Δημιουργίας"].dt.month==mo)
            mdel, mm = metrics(df_full[mask])
            is_partial = (y==latest.year and mo==latest.month)
            title = f"{MGR[mo]} {y}" + (f" (έως {latest.strftime('%d/%m')})" if is_partial else "")
            if not mm:
                st.markdown(f'<div class="month-card"><div class="month-title">{title}</div><div style="color:#ccc;font-size:11px;">Δεν υπάρχουν δεδομένα</div></div>', unsafe_allow_html=True)
                continue
            def grp_p(sd): g=mdel[mdel["sla_days"]==sd]; return g["on_time"].sum()/len(g)*100 if len(g) else 0
            def bar(lbl,pct): c="#22c55e" if pct>=85 else "#f97316" if pct>=70 else "#ef4444"; return f'<div class="bar-lbl">{lbl}<span style="float:right;font-weight:700;color:{c};">{pct:.2f}%</span></div><div class="bar-wrap"><div style="width:{min(pct,100)}%;height:100%;background:{c};border-radius:6px;"></div></div>'
            p24=grp_p(1); p48=grp_p(2); p96=grp_p(4)
            st.markdown(f"""<div class="month-card">
                <div class="month-title">{title}</div>
                <div style="margin-bottom:14px;">
                    <div style="font-size:11px;color:#8fa3c0;font-weight:600;">SLA % (ΕΝΤΟΣ)</div>
                    <div style="font-size:28px;font-weight:800;color:#1a2235;">{mm['sla_pct']:.2f}%</div>
                    <div style="font-size:12px;color:#8fa3c0;">{mm['on_time']:,} / {mm['delivered']:,}</div>
                </div>
                {bar("24h (1 εργάσιμη)",p24)}{bar("48h (2 εργάσιμες)",p48)}{bar("96h (4 εργάσιμες)",p96)}
            </div>""", unsafe_allow_html=True)

    # ---------- MASTER TABLE + SNAPSHOT ----------
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if GH_TOKEN and GH_REPO:
        with st.spinner("🔄 Έλεγχος αλλαγών..."):
            try:
                df_new_data = pd.read_csv(f"{GH_RAW}/data.csv")
                df_new_data["Ημ/νία Παράδοσης"] = pd.to_datetime(df_new_data["Ημ/νία Παράδοσης"], dayfirst=True, errors="coerce")
            except:
                df_new_data = None

            if df_new_data is not None:
                df_processed, n_new, n_updated, changed, mt_sha = update_master_table(df_new_data)

                if changed:
                    ok_mt = save_master_table(df_processed, mt_sha)
                    d_all, m_all = metrics(df_full)
                    snap = build_snapshot(df_full, m_all, d_all, n_new=n_new, n_updated=n_updated)
                    index = load_index()
                    existing_ids = [s.get("snapshot_id","") for s in index]
                    if snap["snapshot_id"] not in existing_ids:
                        ok_snap = save_snapshot(snap)
                        msg = f"✅ Νέο snapshot: <b>{n_new}</b> νέες αποστολές, <b>{n_updated}</b> pending → delivered"
                        st.markdown(f'<div class="snap-ok">{msg}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="snap-ok">✅ Τα δεδομένα είναι ήδη ενημερωμένα</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="snap-ok">✅ Καμία αλλαγή — δεν χρειάζεται νέο snapshot</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="snap-warn">⚠️ GitHub token δεν έχει οριστεί — ιστορικό απενεργοποιημένο</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: ΙΣΤΟΡΙΚΟ
# ══════════════════════════════════════════════
elif "Ιστορικό" in page:
    st.markdown('<div class="section-header">ΙΣΤΟΡΙΚΟ ΑΠΟΔΟΣΗΣ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Αυτόματο snapshot κάθε φορά που ανεβαίνει νέο data.csv</div>', unsafe_allow_html=True)

    snapshots = load_index()
    if not snapshots:
        st.info("Δεν υπάρχουν snapshots ακόμα. Πήγαινε στην Επισκόπηση για να δημιουργηθεί το πρώτο.")
        st.stop()

    # Trend
    sdf = pd.DataFrame(snapshots).sort_values("date")
    sdf["date_dt"] = pd.to_datetime(sdf["date"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sdf["date_dt"], y=sdf["sla_pct"],
        mode="lines+markers", name="SLA %",
        line=dict(color="#7c3aed", width=2.5),
        marker=dict(size=7, color="#7c3aed"),
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>SLA: %{y:.2f}%<extra></extra>"
    ))
    fig.add_hrect(y0=90, y1=105, fillcolor="#dcfce7", opacity=0.3, line_width=0)
    fig.add_hrect(y0=75, y1=90, fillcolor="#fef9c3", opacity=0.3, line_width=0)
    fig.update_layout(
        height=260, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=20,b=20,l=40,r=20),
        yaxis=dict(range=[0,105], ticksuffix="%", gridcolor="#f0f2f5"),
        xaxis=dict(gridcolor="#f0f2f5"),
        font=dict(family="Plus Jakarta Sans"), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Comparison
    if len(snapshots) >= 2:
        st.markdown("#### 🔍 Σύγκριση δύο uploads")
        def snap_label(s):
            upl = s.get("uploaded_at","")[:16].replace("T"," ")
            return f"{s['date']}  ({upl})"
        snap_labels = [snap_label(s) for s in reversed(snapshots)]
        snap_ids    = [s.get("snapshot_id", s["date"]) for s in reversed(snapshots)]
        cc1,cc2 = st.columns(2)
        with cc1: i1 = st.selectbox("Upload Α", range(len(snap_labels)), format_func=lambda i: snap_labels[i], key="s1")
        with cc2: i2 = st.selectbox("Upload Β", range(len(snap_labels)), format_func=lambda i: snap_labels[i], index=min(1,len(snap_labels)-1), key="s2")

        if i1 != i2:
            d1 = load_detail(snap_ids[i1]); d2 = load_detail(snap_ids[i2])
            if d1 and d2:
                r1,r2,r3,r4 = st.columns(4)
                def delta(v1, v2, hib=True):
                    diff = v2-v1
                    if diff==0: return "—"
                    arrow = "▲" if diff>0 else "▼"
                    color = "#16a34a" if (diff>0)==hib else "#b91c1c"
                    return f'<span style="color:{color};font-weight:700;font-size:12px;">{arrow} {abs(diff):.2f}</span>'
                for col,lbl,k,hib in [(r1,"SLA %","sla_pct",True),(r2,"Σύνολο","total",True),(r3,"Εντός SLA","on_time",True),(r4,"Missing","missing_sla",False)]:
                    with col:
                        st.markdown(f"""<div class="kpi-card">
                            <div class="kpi-label">{lbl}</div>
                            <div style="font-size:15px;font-weight:700;color:#1a2235;">{d1[k]} → {d2[k]}</div>
                            {delta(float(d1[k]), float(d2[k]), hib)}
                        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # All snapshots
    st.markdown("#### 📋 Όλα τα Uploads")
    for snap in reversed(snapshots):
        pct    = snap["sla_pct"]
        bc     = "badge-green" if pct>=90 else "badge-orange" if pct>=75 else "badge-red"
        bl     = "✅ Καλό" if pct>=90 else "⚠️ Μέτριο" if pct>=75 else "❌ Κακό"
        sc     = "#16a34a" if pct>=90 else "#92400e" if pct>=75 else "#b91c1c"
        n_new  = snap.get("n_new", "—")
        n_upd  = snap.get("n_updated", "—")
        upl_at = snap.get("uploaded_at","")[:16].replace("T"," ")
        st.markdown(f"""<div class="hist-card" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:13px;font-weight:700;color:#1a2235;">
                    {snap['date']}
                    <span style="font-size:11px;color:#8fa3c0;font-weight:400;margin-left:8px;">upload: {upl_at}</span>
                </div>
                <div style="font-size:11px;color:#8fa3c0;margin-top:3px;">
                    {snap['total']:,} αποστολές &nbsp;·&nbsp; {snap['delivered']:,} παραδόθηκαν &nbsp;·&nbsp;
                    <span style="color:#16a34a;font-weight:600;">+{n_new} νέες</span> &nbsp;·&nbsp;
                    <span style="color:#7c3aed;font-weight:600;">{n_upd} ενημερώσεις pending→delivered</span>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:22px;font-weight:800;color:{sc};">{pct:.2f}%</div>
                <span class="badge {bc}">{bl}</span>
            </div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: ΑΝΑΛΥΣΗ ΝΟΜΟΥ
# ══════════════════════════════════════════════
elif "Νομού" in page:
    st.markdown('<div class="section-header">ΑΝΑΛΥΣΗ ΑΝΑ ΝΟΜΟ / ΠΕΡΙΟΧΗ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Σύγκριση δύο περιόδων βάσει ημερομηνίας δημιουργίας</div>', unsafe_allow_html=True)

    # ---- Period selectors ----
    all_min = df_full["Ημ/νία Δημιουργίας"].min().date()
    all_max = df_full["Ημ/νία Δημιουργίας"].max().date()

    pa1, pa2, pb1, pb2, _ = st.columns([2,2,2,2,1])
    with pa1: p1_from = st.date_input("Περίοδος Α — Από", value=all_min, min_value=all_min, max_value=all_max, key="p1f")
    with pa2: p1_to   = st.date_input("Περίοδος Α — Έως", value=all_max, min_value=all_min, max_value=all_max, key="p1t")
    with pb1: p2_from = st.date_input("Περίοδος Β — Από", value=all_min, min_value=all_min, max_value=all_max, key="p2f")
    with pb2: p2_to   = st.date_input("Περίοδος Β — Έως", value=all_max, min_value=all_min, max_value=all_max, key="p2t")

    def reg_stats(df_src, d_from, d_to):
        mask = (df_src["Ημ/νία Δημιουργίας"].dt.date >= d_from) & (df_src["Ημ/νία Δημιουργίας"].dt.date <= d_to)
        sub  = df_src[mask]
        del_sub, _ = metrics(sub)
        if not len(del_sub) or "Regional Unity" not in del_sub.columns:
            return pd.DataFrame()
        r = (del_sub.groupby("Regional Unity")
             .agg(total=("on_time","count"), on_time=("on_time","sum"))
             .reset_index())
        r["sla_pct"] = (r["on_time"] / r["total"] * 100).round(2)
        return r.rename(columns={"Regional Unity":"Περιοχή"})

    r1 = reg_stats(df_full, p1_from, p1_to)
    r2 = reg_stats(df_full, p2_from, p2_to)

    if r1.empty or r2.empty:
        st.info("Δεν υπάρχουν δεδομένα Regional Unity για μία από τις περιόδους.")
        st.stop()

    # ---- Merge ----
    merged = r1[["Περιοχή","sla_pct","total"]].merge(
        r2[["Περιοχή","sla_pct","total"]], on="Περιοχή", how="outer", suffixes=("_A","_B")
    ).fillna(0).sort_values("sla_pct_A", ascending=True)
    merged["diff"]  = (merged["sla_pct_B"] - merged["sla_pct_A"]).round(2)
    merged["arrow"] = merged["diff"].apply(lambda d: "▲" if d > 0.5 else ("▼" if d < -0.5 else "→"))
    merged["arrow_color"] = merged["diff"].apply(lambda d: "#16a34a" if d > 0.5 else ("#ef4444" if d < -0.5 else "#8fa3c0"))
    merged["diff_label"] = merged.apply(
        lambda r: f"{r['arrow']} {abs(r['diff']):.1f}%", axis=1
    )

    # ══ SCATTER ══
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("#### 🔵 Scatter — Περίοδος Α vs Β")
    st.markdown('<div class="section-sub">Hover για λεπτομέρειες · Πάνω από τη διαγώνιο = βελτίωση στην Β · Κάτω = επιδείνωση</div>', unsafe_allow_html=True)

    fig_sc = go.Figure()
    fig_sc.add_shape(type="line", x0=50, y0=50, x1=100, y1=100,
                     line=dict(color="#e2e8f0", width=1.5, dash="dot"))

    colors = merged["diff"].apply(lambda d: "#22c55e" if d > 0.5 else ("#ef4444" if d < -0.5 else "#94a3b8")).tolist()

    fig_sc.add_trace(go.Scatter(
        x=merged["sla_pct_A"], y=merged["sla_pct_B"],
        mode="markers",
        marker=dict(
            size=12,
            color=colors, opacity=0.85,
            line=dict(color="white", width=1.5)
        ),
        text=merged["Περιοχή"],
        customdata=merged[["diff_label","total_A","total_B"]].values,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Περίοδος Α: %{x:.1f}%<br>"
            "Περίοδος Β: %{y:.1f}%<br>"
            "Μεταβολή: %{customdata[0]}<br>"
            "Αποστολές Α: %{customdata[1]:.0f} · Β: %{customdata[2]:.0f}"
            "<extra></extra>"
        ),
    ))

    fig_sc.update_layout(
        height=420,
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=10, b=40, l=50, r=20),
        font=dict(family="Plus Jakarta Sans"),
        xaxis=dict(title="SLA % — Περίοδος Α", range=[50,102], ticksuffix="%",
                   gridcolor="#f0f2f5", showgrid=True),
        yaxis=dict(title="SLA % — Περίοδος Β", range=[50,102], ticksuffix="%",
                   gridcolor="#f0f2f5", showgrid=True),
        showlegend=False,
    )
    fig_sc.add_annotation(x=100, y=54, text="📉 Επιδείνωση", showarrow=False,
                          font=dict(size=10, color="#ef4444"), xanchor="right")
    fig_sc.add_annotation(x=52, y=100, text="📈 Βελτίωση", showarrow=False,
                          font=dict(size=10, color="#22c55e"), xanchor="left")
    st.plotly_chart(fig_sc, use_container_width=True)

    # ══ BULLET BARS ══
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    sort_col1, sort_col2 = st.columns([3,1])
    with sort_col1:
        st.markdown("#### 📊 Σύγκριση ανά Νομό")
    with sort_col2:
        sort_dir = st.radio("Ταξινόμηση", ["▲", "▼"], horizontal=True, key="sort_dir", label_visibility="collapsed")

    ascending = sort_dir == "▼"
    merged_sorted = merged.sort_values("diff", ascending=ascending)
    regions = merged_sorted["Περιοχή"].tolist()

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=regions, x=merged_sorted["sla_pct_A"],
        orientation="h", name="Περίοδος Α",
        marker_color="#7c3aed", opacity=0.45,
        width=0.35, offset=-0.35,
        hovertemplate="<b>%{y}</b><br>Περίοδος Α: %{x:.1f}%<extra></extra>",
    ))
    fig_bar.add_trace(go.Bar(
        y=regions, x=merged_sorted["sla_pct_B"],
        orientation="h", name="Περίοδος Β",
        marker_color="#0ea5e9", opacity=0.85,
        width=0.35, offset=0,
        hovertemplate="<b>%{y}</b><br>Περίοδος Β: %{x:.1f}%<extra></extra>",
    ))

    for _, row in merged_sorted.iterrows():
        fig_bar.add_annotation(
            y=row["Περιοχή"],
            x=max(row["sla_pct_A"], row["sla_pct_B"]) + 1,
            text=f"<b>{row['diff_label']}</b>",
            showarrow=False,
            font=dict(size=10, color=row["arrow_color"], family="Plus Jakarta Sans"),
            xanchor="left",
        )

    fig_bar.update_layout(
        height=max(400, len(regions)*36),
        barmode="overlay",
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=10, b=20, l=20, r=90),
        font=dict(family="Plus Jakarta Sans"),
        xaxis=dict(range=[50,112], ticksuffix="%", gridcolor="#f0f2f5"),
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", y=1.03, x=0,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        bargap=0.3,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ══ TABLE ══
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    tbl = merged_sorted[["Περιοχή","sla_pct_A","total_A","sla_pct_B","total_B","diff","diff_label"]].copy()
    tbl.columns = ["Περιοχή","SLA% Α","Αποστολές Α","SLA% Β","Αποστολές Β","Μεταβολή",""]
    tbl["Αποστολές Α"] = tbl["Αποστολές Α"].astype(int)
    tbl["Αποστολές Β"] = tbl["Αποστολές Β"].astype(int)
    st.dataframe(tbl, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
# PAGE: ΑΝΑΛΥΣΗ ΚΑΤΑΣΤΗΜΑΤΟΣ
# ══════════════════════════════════════════════
elif "Καταστήματος" in page:
    st.markdown('<div class="section-header">ΑΝΑΛΥΣΗ ΑΝΑ ΚΑΤΑΣΤΗΜΑ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Βάσει φίλτρου ημερομηνιών</div>', unsafe_allow_html=True)

    # Period selectors only (no global filters here)
    all_min = df_full["Ημ/νία Δημιουργίας"].min().date()
    all_max = df_full["Ημ/νία Δημιουργίας"].max().date()

    sp1, sp2, sp3, sp4, _ = st.columns([2,2,2,2,1])
    with sp1: s_p1_from = st.date_input("Περίοδος Α — Από", value=all_min, min_value=all_min, max_value=all_max, key="sp1f")
    with sp2: s_p1_to   = st.date_input("Περίοδος Α — Έως", value=all_max, min_value=all_min, max_value=all_max, key="sp1t")
    with sp3: s_p2_from = st.date_input("Περίοδος Β — Από", value=all_min, min_value=all_min, max_value=all_max, key="sp2f")
    with sp4: s_p2_to   = st.date_input("Περίοδος Β — Έως", value=all_max, min_value=all_min, max_value=all_max, key="sp2t")

    def shop_stats(d_from, d_to):
        mask = (df_full["Ημ/νία Δημιουργίας"].dt.date >= d_from) & (df_full["Ημ/νία Δημιουργίας"].dt.date <= d_to)
        sub  = df_full[mask]
        d, _ = metrics(sub)
        if not len(d) or "Κατάστημα" not in d.columns: return pd.DataFrame()
        r = d.groupby("Κατάστημα").agg(total=("on_time","count"), on_time=("on_time","sum")).reset_index()
        r["sla_pct"] = (r["on_time"] / r["total"] * 100).round(2)
        r["late"]    = r["total"] - r["on_time"]
        return r

    grp_A = shop_stats(s_p1_from, s_p1_to)
    grp_B = shop_stats(s_p2_from, s_p2_to)

    if grp_A.empty:
        st.info("Δεν υπάρχουν δεδομένα καταστήματος για την περίοδο Α.")
        st.stop()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    period_a_lbl = f"{s_p1_from.strftime('%d/%m/%Y')} – {s_p1_to.strftime('%d/%m/%Y')}"

    # ── TOP 10 / BOTTOM 10 cards ──
    def shop_cards(grp, ascending):
        top = grp.sort_values("sla_pct", ascending=ascending).head(10)
        cols = st.columns(5)
        for i, (_, row) in enumerate(top.iterrows()):
            pct = row["sla_pct"]
            badge_col = "#22c55e" if pct>=90 else "#f97316" if pct>=75 else "#ef4444"
            with cols[i % 5]:
                st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:14px;box-shadow:0 1px 6px rgba(0,0,0,0.07);
                    border:1px solid #f0f2f5;margin-bottom:10px;border-top:3px solid {badge_col};">
                    <div style="font-size:10px;color:#8fa3c0;font-weight:600;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                        title="{row['Κατάστημα']}">{row['Κατάστημα']}</div>
                    <div style="font-size:22px;font-weight:800;color:{badge_col};">{pct:.1f}%</div>
                    <div style="font-size:11px;color:#8fa3c0;">{row['total']:,} αποστολές</div>
                </div>""", unsafe_allow_html=True)

    st.markdown(f'#### 🏆 Top 10 — Καλύτερη επίδοση <span style="font-size:12px;color:#8fa3c0;font-weight:400;">Περίοδος Α: {period_a_lbl}</span>', unsafe_allow_html=True)
    shop_cards(grp_A, False)

    st.markdown(f'#### ⚠️ Bottom 10 — Χαμηλότερη επίδοση <span style="font-size:12px;color:#8fa3c0;font-weight:400;">Περίοδος Α: {period_a_lbl}</span>', unsafe_allow_html=True)
    shop_cards(grp_A, True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Dual-period bar chart (like Νομού) ──
    st.markdown("#### 📊 Σύγκριση Περιόδων ανά Κατάστημα")

    if not grp_B.empty:
        merged_s = grp_A[["Κατάστημα","sla_pct","total"]].merge(
            grp_B[["Κατάστημα","sla_pct","total"]], on="Κατάστημα", how="outer", suffixes=("_A","_B")
        ).fillna(0)
        merged_s["diff"]  = (merged_s["sla_pct_B"] - merged_s["sla_pct_A"]).round(2)
        merged_s["arrow"] = merged_s["diff"].apply(lambda d: "▲" if d>0.5 else ("▼" if d<-0.5 else "→"))
        merged_s["arrow_color"] = merged_s["diff"].apply(lambda d: "#16a34a" if d>0.5 else ("#ef4444" if d<-0.5 else "#8fa3c0"))
        merged_s["diff_label"]  = merged_s.apply(lambda r: f"{r['arrow']} {abs(r['diff']):.1f}%", axis=1)

        sc1, sc2 = st.columns([3,1])
        with sc2:
            s_sort = st.radio("Ταξινόμηση", ["▲","▼"], horizontal=True, key="s_sort", label_visibility="collapsed")
        merged_s = merged_s.sort_values("diff", ascending=(s_sort=="▼"))
        shops_s  = merged_s["Κατάστημα"].tolist()

        fig_s = go.Figure()
        fig_s.add_trace(go.Bar(
            y=shops_s, x=merged_s["sla_pct_A"], orientation="h", name="Περίοδος Α",
            marker_color="#7c3aed", opacity=0.45, width=0.35, offset=-0.35,
            hovertemplate="<b>%{y}</b><br>Α: %{x:.1f}%<extra></extra>",
        ))
        fig_s.add_trace(go.Bar(
            y=shops_s, x=merged_s["sla_pct_B"], orientation="h", name="Περίοδος Β",
            marker_color="#0ea5e9", opacity=0.85, width=0.35, offset=0,
            hovertemplate="<b>%{y}</b><br>Β: %{x:.1f}%<extra></extra>",
        ))
        for _, row in merged_s.iterrows():
            fig_s.add_annotation(
                y=row["Κατάστημα"], x=max(row["sla_pct_A"],row["sla_pct_B"])+1,
                text=f"<b>{row['diff_label']}</b>", showarrow=False,
                font=dict(size=9, color=row["arrow_color"], family="Plus Jakarta Sans"),
                xanchor="left",
            )
        fig_s.update_layout(
            height=max(500, len(shops_s)*28),
            barmode="overlay", paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(t=10,b=20,l=20,r=80),
            font=dict(family="Plus Jakarta Sans"),
            xaxis=dict(range=[50,115], ticksuffix="%", gridcolor="#f0f2f5"),
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", y=1.02, bgcolor="rgba(0,0,0,0)"),
            bargap=0.3,
        )
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("Ορίστε Περίοδο Β για σύγκριση.")

    # ── Table ──
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    tbl_s = grp_A.sort_values("sla_pct")[["Κατάστημα","sla_pct","total","on_time","late"]].copy()
    tbl_s.columns = ["Κατάστημα","SLA%","Σύνολο","Εντός SLA","Εκτός SLA"]
    st.dataframe(tbl_s, use_container_width=True, hide_index=True)

