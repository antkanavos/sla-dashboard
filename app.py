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

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #1a2235 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #8fa3c0;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #8fa3c0 !important;
    font-size: 13px;
    font-weight: 500;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    color: white !important;
}
/* Sidebar collapse button - always visible */
[data-testid="stSidebarCollapseButton"],
button[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: #2a3550 !important;
    border-radius: 50% !important;
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

# ---------- MASTER TABLE ----------
MASTER_TABLE_PATH = "history/master_table.csv"

@st.cache_data(ttl=60)
def load_master_table():
    """Load the persistent master table from GitHub."""
    c, sha = gh_get(MASTER_TABLE_PATH)
    if c:
        from io import StringIO
        return pd.read_csv(StringIO(c), dtype=str), sha
    return pd.DataFrame(), None

def update_master_table(df_new):
    """
    Merge df_new into master_table with the logic:
    - Αριθμός ΔΕΝ υπάρχει       → νέα εγγραφή
    - Υπάρχει + έχει παράδοση  → skip
    - Υπάρχει + δεν έχει παράδ. + τώρα έχει → overwrite
    - Υπάρχει + δεν έχει παράδ. + ακόμα δεν έχει → skip
    Returns (updated_df, n_new, n_updated, changed)
    """
    existing, sha = load_master_table()

    # Normalize incoming data to str for consistent comparison
    df_new = df_new.copy()
    df_new["Αριθμός"] = df_new["Αριθμός"].astype(str)
    df_new["Ημ/νία Παράδοσης_str"] = df_new["Ημ/νία Παράδοσης"].astype(str).replace("NaT","")

    if existing.empty:
        # First time — save everything
        result = df_new[["Αριθμός","Ημ/νία Δημιουργίας","Ημ/νία Παράδοσης_str",
                          "Κλειδί Πελάτη 3","Δ/νση Παράδοσης","Τ.Κ Παράδοσης"]].copy()
        result.columns = ["Αριθμός","Ημ_Δημιουργίας","Ημ_Παράδοσης","Key","Διεύθυνση","ΤΚ"]
        return result, len(result), 0, True, sha

    existing["Αριθμός"] = existing["Αριθμός"].astype(str)
    existing_idx = existing.set_index("Αριθμός")

    n_new = 0
    n_updated = 0
    rows_to_add = []

    for _, row in df_new.iterrows():
        ar = str(row["Αριθμός"])
        new_del = row["Ημ/νία Παράδοσης_str"].strip()

        if ar not in existing_idx.index:
            # Νέα εγγραφή
            rows_to_add.append({
                "Αριθμός": ar,
                "Ημ_Δημιουργίας": str(row["Ημ/νία Δημιουργίας"]),
                "Ημ_Παράδοσης": new_del,
                "Key": str(row["Κλειδί Πελάτη 3"]),
                "Διεύθυνση": str(row["Δ/νση Παράδοσης"]),
                "ΤΚ": str(row["Τ.Κ Παράδοσης"]),
            })
            n_new += 1
        else:
            existing_del = str(existing_idx.loc[ar, "Ημ_Παράδοσης"]).strip()
            if existing_del and existing_del not in ("nan","","NaT"):
                # Ήδη delivered → skip
                pass
            elif new_del and new_del not in ("nan","","NaT"):
                # Pending → τώρα delivered → overwrite
                existing.loc[existing["Αριθμός"]==ar, "Ημ_Παράδοσης"] = new_del
                n_updated += 1

    if rows_to_add:
        existing = pd.concat([existing, pd.DataFrame(rows_to_add)], ignore_index=True)

    changed = (n_new > 0) or (n_updated > 0)
    return existing, n_new, n_updated, changed, sha

def save_master_table(df_master, sha):
    """Save master table CSV to GitHub."""
    load_master_table.clear()
    csv_str = df_master.to_csv(index=False)
    _, current_sha = gh_get(MASTER_TABLE_PATH)
    effective_sha = current_sha or sha
    return gh_put(MASTER_TABLE_PATH, csv_str, "master_table update", effective_sha)

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

@st.cache_data(ttl=300)
def load_and_process():
    df         = pd.read_csv(f"{GH_RAW}/data.csv")
    master     = pd.read_csv(f"{GH_RAW}/master.csv")
    hol_df     = pd.read_csv(f"{GH_RAW}/holidays.csv")
    holidays   = set(pd.to_datetime(hol_df["date"], dayfirst=True).dt.date)

    def clean_addr(x):
        if pd.isna(x): return None
        x = str(x).upper().replace("-"," ").replace(",","").replace(".","")
        for a,b in [("ΟΔΟΣ",""),("ΑΓΙΟΥ","ΑΓ"),("ΑΓΙΑΣ","ΑΓ"),("ΚΑΙ","&")]:
            x = x.replace(a,b)
        return " ".join(x.strip().split())

    def clean_pc(x):
        if pd.isna(x): return None
        x = "".join(filter(str.isdigit, str(x).replace(".0","").replace(" ","").replace("-","")))
        return x[:5] if len(x) >= 5 else x

    df["KEY_CLEAN"]     = df["Κλειδί Πελάτη 3"].str.extract(r"(\d+)")
    df = df[df["KEY_CLEAN"].notna()].copy()
    master["KEY_CLEAN"] = master["KEY1"].str.extract(r"(\d+)")
    df["ADDR_CLEAN"]    = df["Δ/νση Παράδοσης"].apply(clean_addr)
    master["ADDR_CLEAN"]= master["Full Address"].apply(clean_addr)
    df["POSTCODE"]      = df["Τ.Κ Παράδοσης"].apply(clean_pc)
    master["POSTCODE"]  = master["Account : Site : Site PostCode"].apply(clean_pc)

    master = master.sort_values("Χρόνος Παράδοσης").drop_duplicates(["KEY_CLEAN","POSTCODE"], keep="first")

    # Step 1
    df = df.merge(master[["KEY_CLEAN","POSTCODE","Χρόνος Παράδοσης","Regional Unity"]], on=["KEY_CLEAN","POSTCODE"], how="left")
    # Step 2
    fb = df[df["Χρόνος Παράδοσης"].isna()].copy().drop(columns=["Χρόνος Παράδοσης"])
    fb = fb.merge(master[["KEY_CLEAN","Χρόνος Παράδοσης"]].drop_duplicates("KEY_CLEAN"), on="KEY_CLEAN", how="left")
    df.loc[fb.index,"Χρόνος Παράδοσης"] = df.loc[fb.index,"Χρόνος Παράδοσης"].combine_first(fb["Χρόνος Παράδοσης"])
    # Step 3 fuzzy
    um = df[df["Χρόνος Παράδοσης"].isna()].copy()
    def fmatch(row):
        sub = master[master["KEY_CLEAN"]==row["KEY_CLEAN"]]
        if sub.empty: return None
        m = process.extractOne(row["ADDR_CLEAN"], sub["ADDR_CLEAN"].tolist(), scorer=fuzz.token_sort_ratio)
        return sub.iloc[m[2]]["Χρόνος Παράδοσης"] if m and m[1]>=75 else None
    fz = pd.to_numeric(um.apply(fmatch, axis=1), errors="coerce")
    df.loc[um.index,"Χρόνος Παράδοσης"] = df.loc[um.index,"Χρόνος Παράδοσης"].combine_first(fz)
    # Step 4 postcode
    pcm = master.groupby("POSTCODE")["Χρόνος Παράδοσης"].agg(lambda x: x.mode()[0]).reset_index().rename(columns={"Χρόνος Παράδοσης":"SLA_pc"})
    still = df["Χρόνος Παράδοσης"].isna()
    df = df.merge(pcm, on="POSTCODE", how="left")
    df.loc[still,"Χρόνος Παράδοσης"] = df.loc[still,"Χρόνος Παράδοσης"].combine_first(df.loc[still,"SLA_pc"])
    df.drop(columns=["SLA_pc"], inplace=True)
    # Step 5 pc3
    master["PC3"] = master["POSTCODE"].str[:3]
    df["PC3"]     = df["POSTCODE"].str[:3]
    pc3m = master.groupby("PC3")["Χρόνος Παράδοσης"].agg(lambda x: x.mode()[0]).reset_index().rename(columns={"Χρόνος Παράδοσης":"SLA_pc3"})
    still = df["Χρόνος Παράδοσης"].isna()
    df = df.merge(pc3m, on="PC3", how="left")
    df.loc[still,"Χρόνος Παράδοσης"] = df.loc[still,"Χρόνος Παράδοσης"].combine_first(df.loc[still,"SLA_pc3"])
    df.drop(columns=["SLA_pc3","PC3"], inplace=True)

    df["Ημ/νία Δημιουργίας"] = pd.to_datetime(df["Ημ/νία Δημιουργίας"], dayfirst=True)
    df["Ημ/νία Παράδοσης"]   = pd.to_datetime(df["Ημ/νία Παράδοσης"],   dayfirst=True, errors="coerce")
    df["sla_days"] = df["Χρόνος Παράδοσης"].map({24:1, 48:2, 96:4})

    def wdays(start, end):
        if pd.isna(end): return None
        days = pd.date_range(start, end)
        return len([d for d in days if d.weekday()!=6 and d.date() not in holidays]) - 1

    df["working_days"] = df.apply(lambda x: wdays(x["Ημ/νία Δημιουργίας"], x["Ημ/νία Παράδοσης"]), axis=1)
    return df

with st.spinner("Φόρτωση δεδομένων..."):
    df_full = load_and_process()

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
    ], label_visibility="collapsed")

    st.markdown(f"""
    <div style='position:fixed;bottom:20px;width:178px;'>
        <div style='font-size:10px;color:#3a5070;font-weight:600;'>Τελευταία ενημέρωση</div>
        <div style='font-size:11px;color:#5a7090;'>{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>""", unsafe_allow_html=True)

# ---------- DATE FILTER ----------
min_d = df_full["Ημ/νία Δημιουργίας"].min().date()
max_d = df_full["Ημ/νία Δημιουργίας"].max().date()

fc1,fc2,fc3 = st.columns([2,2,4])
with fc1: date_from = st.date_input("Από", value=min_d, min_value=min_d, max_value=max_d, key="df", help="Ημερομηνία δημιουργίας αποστολής")
with fc2: date_to   = st.date_input("Έως", value=max_d, min_value=min_d, max_value=max_d, key="dt", help="Ημερομηνία δημιουργίας αποστολής")
with fc3: st.markdown(f"<div style='text-align:right;font-size:11px;color:#8fa3c0;padding-top:10px;'>Φίλτρο βάσει <b>ημ. δημιουργίας</b> &nbsp;·&nbsp; Τελευταία ενημέρωση: {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;🔄</div>", unsafe_allow_html=True)

df = df_full[
    (df_full["Ημ/νία Δημιουργίας"].dt.date >= date_from) &
    (df_full["Ημ/νία Δημιουργίας"].dt.date <= date_to)
].copy()
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

    col_l, col_r = st.columns(2)

    # Left: SLA by type
    with col_l:
        st.markdown('<div class="section-header">ΑΝΑΛΥΣΗ ΑΝΑ ΧΡΟΝΟ ΠΑΡΑΔΟΣΗΣ</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">(ΟΛΟ ΤΟ ΔΙΑΣΤΗΜΑ)</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        for col, sd, lbl in [(c1,1,"24h (1 εργάσιμη)"),(c2,2,"48h (2 εργάσιμες)"),(c3,4,"96h (4 εργάσιμες)")]:
            with col:
                g = delivered[delivered["sla_days"]==sd]
                if not len(g):
                    st.markdown(f'<div style="padding:12px;background:white;border-radius:12px;border:1px solid #f0f2f5;"><div class="chart-label">{lbl}</div><div style="color:#ccc;font-size:11px;margin-top:8px;">Δεν υπάρχουν</div></div>', unsafe_allow_html=True)
                    continue
                ot  = int(g["on_time"].sum()); lat = len(g)-ot; pct = ot/len(g)*100
                st.markdown(f"""
                <div style="background:white;border-radius:14px;padding:14px 12px 16px;box-shadow:0 1px 8px rgba(0,0,0,0.07);border:1px solid #f0f2f5;">
                    {donut_html(pct, "#22c55e", "#fee2e2", lbl)}
                    <div style="margin-top:10px;padding:0 4px;">
                        <div class="legend-row"><span class="legend-dot" style="background:#22c55e"></span>Εντός &nbsp;<b>{ot:,}</b> ({pct:.2f}%)</div>
                        <div class="legend-row"><span class="legend-dot" style="background:#ef4444"></span>Εκτός &nbsp;<b>{lat:,}</b> ({100-pct:.2f}%)</div>
                        <div class="total-lbl" style="margin-top:8px;">Σύνολο παραδοθέντων</div>
                        <div class="total-val">{len(g):,}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

    # Right: Delays - 3-segment donut (24h/48h/96h breakdown within each delay bucket
    with col_r:
        st.markdown('<div class="section-header">ΚΑΘΥΣΤΕΡΗΣΗ ΠΑΡΑΔΟΣΕΩΝ</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">(ΟΛΟ ΤΟ ΔΙΑΣΤΗΜΑ)</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        td = len(delivered)
        delay_configs = [
            (c1, 1,  False, "1 ημέρα",   ),
            (c2, 2,  False, "2 ημέρες",  ),
            (c3, 3,  True,  "3+ ημέρες", ),
        ]

        def three_segment_donut(d24, d48, d96, label):
            total = d24 + d48 + d96
            r = 38; cx = cy = 50; sw = 12
            circ = 2 * 3.14159265 * r
            if total == 0:
                return f"""<div style="text-align:center;padding:6px 0 2px;">
                    <div style="font-size:10px;font-weight:700;color:#8fa3c0;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;line-height:1.3;">{label} καθυστέρηση</div>
                    <svg viewBox="0 0 100 100" width="100" height="100" style="display:block;margin:0 auto;">
                        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#f0f2f5" stroke-width="{sw}"/>
                        <text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central"
                            font-family="Plus Jakarta Sans,sans-serif" font-size="15" font-weight="800" fill="#1a2235">0</text>
                    </svg></div>"""
            gap = circ * 0.018
            def seg(count, color, offset):
                length = (count / total) * circ - gap
                if length <= 0: return ""
                return f"""<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}"
                    stroke-dasharray="{length:.3f} {circ-length:.3f}"
                    stroke-linecap="butt"
                    transform="rotate({offset-90} {cx} {cy})"/>"""
            a24 = (d24/total)*360; a48 = (d48/total)*360
            return f"""<div style="text-align:center;padding:6px 0 2px;">
                <div style="font-size:10px;font-weight:700;color:#8fa3c0;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;line-height:1.3;">{label} καθυστέρηση</div>
                <svg viewBox="0 0 100 100" width="100" height="100" style="display:block;margin:0 auto;">
                    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#f0f2f5" stroke-width="{sw}"/>
                    {seg(d24,"#22c55e",0)}{seg(d48,"#f97316",a24)}{seg(d96,"#ef4444",a24+a48)}
                    <text x="{cx}" y="{cy-4}" text-anchor="middle" dominant-baseline="central"
                        font-family="Plus Jakarta Sans,sans-serif" font-size="15" font-weight="800" fill="#1a2235">{total:,}</text>
                    <text x="{cx}" y="{cy+13}" text-anchor="middle"
                        font-family="Plus Jakarta Sans,sans-serif" font-size="7" font-weight="600" fill="#8fa3c0">αποστολές</text>
                </svg>
            </div>"""

        for col, days, use_gte, lbl in delay_configs:
            with col:
                dd  = delivered[delivered["delay_days"] >= days] if use_gte else delivered[delivered["delay_days"] == days]
                n   = len(dd)
                d24 = len(dd[dd["sla_days"]==1])
                d48 = len(dd[dd["sla_days"]==2])
                d96 = len(dd[dd["sla_days"]==4])
                p24 = round(d24/n*100,1) if n else 0
                p48 = round(d48/n*100,1) if n else 0
                p96 = round(d96/n*100,1) if n else 0
                pct_of_total = round(n/td*100,1) if td else 0
                st.markdown(f"""
                <div style="background:white;border-radius:14px;padding:14px 12px 16px;box-shadow:0 1px 8px rgba(0,0,0,0.07);border:1px solid #f0f2f5;">
                    {three_segment_donut(d24, d48, d96, lbl)}
                    <div style="margin-top:10px;padding:0 4px;">
                        <div class="legend-row"><span class="legend-dot" style="background:#22c55e"></span>24h &nbsp;<b>{d24:,}</b> ({p24}%)</div>
                        <div class="legend-row"><span class="legend-dot" style="background:#f97316"></span>48h &nbsp;<b>{d48:,}</b> ({p48}%)</div>
                        <div class="legend-row"><span class="legend-dot" style="background:#ef4444"></span>96h &nbsp;<b>{d96:,}</b> ({p96}%)</div>
                        <div class="total-lbl" style="margin-top:8px;">% επί παραδοθέντων</div>
                        <div class="total-val">{pct_of_total}%</div>
                    </div>
                </div>""", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:10px;color:#8fa3c0;text-align:right;margin-top:6px;'>Σύνολο παραδοθέντων: {td:,}</div>", unsafe_allow_html=True)

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
            # Step 1: update master table
            df_processed, n_new, n_updated, changed, mt_sha = update_master_table(df_full)

            if changed:
                # Save updated master table
                ok_mt = save_master_table(df_processed, mt_sha)
                # Step 2: compute current hash AFTER update
                d_all, m_all = metrics(df_full)
                snap = build_snapshot(df_full, m_all, d_all, n_new=n_new, n_updated=n_updated)
                # Check if this exact hash already in index (idempotent)
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
    st.markdown('<div class="section-sub">Hover για λεπτομέρειες · Πάνω από τη διαγώνιο = βελτίωση στην Β · Κάτω = χειροτέρεμα</div>', unsafe_allow_html=True)

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
    fig_sc.add_annotation(x=100, y=54, text="📉 Χειροτέρεμα", showarrow=False,
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
        sort_dir = st.radio("Ταξινόμηση", ["▲", "▼"], horizontal=True, key="sort_dir")

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
    tbl = merged_sorted[["Περιοχή","sla_pct_A","total_A","sla_pct_B","total_B","diff","arrow"]].copy()
    tbl.columns = ["Περιοχή","SLA% Α","Αποστολές Α","SLA% Β","Αποστολές Β","Μεταβολή %",""]
    tbl["Αποστολές Α"] = tbl["Αποστολές Α"].astype(int)
    tbl["Αποστολές Β"] = tbl["Αποστολές Β"].astype(int)
    tbl = tbl.sort_values("Διαφορά (pp)", ascending=True)
    st.dataframe(tbl, use_container_width=True, hide_index=True)
