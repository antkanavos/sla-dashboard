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

st.set_page_config(layout="wide", page_title="SLA Dashboard", page_icon="📦")

# ---------- CSS ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { background: #1a2235; min-width: 210px !important; max-width: 210px !important; }
section[data-testid="stSidebar"] * { color: #8fa3c0 !important; }

.kpi-card { background: white; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); border: 1px solid #f0f2f5; }
.kpi-label { font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #8fa3c0; margin-bottom: 4px; }
.kpi-value { font-size: 30px; font-weight: 800; color: #1a2235; line-height: 1.1; }
.kpi-sub { font-size: 11px; color: #8fa3c0; margin-top: 3px; font-weight: 500; }
.kpi-purple { color: #7c3aed !important; }

.section-header { font-size: 12px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: #1a2235; }
.section-sub { font-size: 11px; color: #8fa3c0; font-weight: 500; margin-bottom: 12px; }

.chart-card { background: white; border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); border: 1px solid #f0f2f5; }
.chart-label { font-size: 11px; font-weight: 700; color: #8fa3c0; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 2px; }
.legend-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #444; margin-bottom: 3px; font-weight: 500; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.total-lbl { font-size: 10px; color: #8fa3c0; font-weight: 500; margin-top: 6px; }
.total-val { font-size: 12px; font-weight: 700; color: #1a2235; }

.month-card { background: white; border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 8px rgba(0,0,0,0.07); border: 1px solid #f0f2f5; }
.month-title { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #8fa3c0; margin-bottom: 10px; }
.bar-lbl { font-size: 11px; color: #444; font-weight: 500; margin-bottom: 2px; }
.bar-wrap { background: #f0f2f5; border-radius: 6px; height: 7px; margin-bottom: 9px; overflow: hidden; }

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

def save_snapshot(snap):
    date_str  = snap["date"]
    path      = f"history/{date_str}.json"
    c_str     = json.dumps(snap, ensure_ascii=False, indent=2)
    _, old_sha = gh_get(path)
    ok1 = gh_put(path, c_str, f"snapshot: {date_str}", old_sha)

    index = load_index()
    load_index.clear()
    index = [s for s in index if s["date"] != date_str]
    index.append({"date": date_str, "total": snap["total"], "delivered": snap["delivered"],
                  "on_time": snap["on_time"], "sla_pct": snap["sla_pct"], "missing_sla": snap["missing_sla"]})
    index.sort(key=lambda x: x["date"])
    _, idx_sha = gh_get("history/index.json")
    ok2 = gh_put("history/index.json", json.dumps(index, ensure_ascii=False, indent=2),
                 f"index: {date_str}", idx_sha)
    return ok1 and ok2

def load_detail(date_str):
    c, _ = gh_get(f"history/{date_str}.json")
    return json.loads(c) if c else None

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

def build_snapshot(df, m, del_df):
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
        "date": snap_date,
        "data_hash": hashlib.md5(df["Αριθμός"].astype(str).sort_values().str.cat().encode()).hexdigest()[:8],
        **m,
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

    page = st.radio("", [
        "🏠  Επισκόπηση",
        "📈  Ιστορικό",
        "🔁  Recurring Misses",
        "🗺️  Ανάλυση Νομού",
        "⚙️  Ρυθμίσεις",
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
with fc1: date_from = st.date_input("Από", value=min_d, min_value=min_d, max_value=max_d, key="df")
with fc2: date_to   = st.date_input("Έως", value=max_d, min_value=min_d, max_value=max_d, key="dt")
with fc3: st.markdown(f"<div style='text-align:right;font-size:11px;color:#8fa3c0;padding-top:10px;'>Τελευταία ενημέρωση: {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;🔄</div>", unsafe_allow_html=True)

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
                <div style="font-size:20px;margin-bottom:6px;">{icon}</div>
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value {cls}">{val}</div>
                <div class="kpi-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Donut helper
    def donut(pct, c_in, c_out, size=148):
        fig = go.Figure(go.Pie(
            values=[pct, 100-pct], hole=0.68,
            marker_colors=[c_in, c_out],
            textinfo="none", hoverinfo="none", direction="clockwise", sort=False,
        ))
        fig.update_layout(
            margin=dict(t=0,b=0,l=0,r=0), showlegend=False,
            height=size, width=size,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text=f"<b>{pct:.1f}%</b>", x=0.5, y=0.5,
                font_size=15, showarrow=False,
                font=dict(family="Plus Jakarta Sans", color="#1a2235"))]
        )
        return fig

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
                    st.markdown(f'<div class="chart-label">{lbl}</div><div style="color:#ccc;font-size:11px;margin-top:8px;">Δεν υπάρχουν</div>', unsafe_allow_html=True)
                    continue
                ot  = int(g["on_time"].sum()); lat = len(g)-ot; pct = ot/len(g)*100
                st.markdown(f'<div class="chart-label">{lbl}</div>', unsafe_allow_html=True)
                st.plotly_chart(donut(pct,"#22c55e","#fee2e2"), use_container_width=False)
                st.markdown(f"""
                <div class="legend-row"><span class="legend-dot" style="background:#22c55e"></span>Εντός &nbsp;<b>{ot:,}</b> ({pct:.2f}%)</div>
                <div class="legend-row"><span class="legend-dot" style="background:#ef4444"></span>Εκτός &nbsp;<b>{lat:,}</b> ({100-pct:.2f}%)</div>
                <div class="total-lbl">Σύνολο</div><div class="total-val">{len(g):,}</div>
                """, unsafe_allow_html=True)

    # Right: Delays
    with col_r:
        st.markdown('<div class="section-header">ΚΑΘΥΣΤΕΡΗΣΗ ΠΑΡΑΔΟΣΕΩΝ</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">(ΟΛΟ ΤΟ ΔΙΑΣΤΗΜΑ)</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        td = len(delivered)
        for col, days, lbl, color in [
            (c1, "==1","1 ημέρα","#f97316"),
            (c2, "==2","2 ημέρες","#f59e0b"),
            (c3, ">=3","3+ ημέρες","#ef4444"),
        ]:
            with col:
                dd  = delivered[eval(f"delivered['delay_days']{days}")]
                n   = len(dd)
                pct = n/td*100 if td else 0
                d24 = len(dd[dd["sla_days"]==1]); d48 = len(dd[dd["sla_days"]==2]); d96 = len(dd[dd["sla_days"]==4])
                p24 = round(d24/n*100,2) if n else 0; p48 = round(d48/n*100,2) if n else 0; p96 = round(d96/n*100,2) if n else 0
                st.markdown(f'<div class="chart-label">{lbl} καθυστέρηση</div>', unsafe_allow_html=True)
                st.plotly_chart(donut(pct, color, "#f0f2f5"), use_container_width=False)
                st.markdown(f"""
                <div class="legend-row"><span class="legend-dot" style="background:#22c55e"></span>24h &nbsp;<b>{d24}</b> ({p24:.1f}%)</div>
                <div class="legend-row"><span class="legend-dot" style="background:{color}"></span>48h &nbsp;<b>{d48}</b> ({p48:.1f}%)</div>
                <div class="legend-row"><span class="legend-dot" style="background:#ef4444"></span>96h &nbsp;<b>{d96}</b> ({p96:.1f}%)</div>
                <div class="total-lbl">Σύνολο με {lbl}</div><div class="total-val">{n:,}</div>
                """, unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:10px;color:#8fa3c0;text-align:right;margin-top:4px;'>Επί συνόλου παραδοθέντων ({td:,})</div>", unsafe_allow_html=True)

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
                    <div style="font-size:10px;color:#8fa3c0;font-weight:600;">SLA % (ΕΝΤΟΣ)</div>
                    <div style="font-size:24px;font-weight:800;color:#1a2235;">{mm['sla_pct']:.2f}%</div>
                    <div style="font-size:10px;color:#8fa3c0;">{mm['on_time']:,} / {mm['delivered']:,}</div>
                </div>
                {bar("24h (1 εργάσιμη)",p24)}{bar("48h (2 εργάσιμες)",p48)}{bar("96h (4 εργάσιμες)",p96)}
            </div>""", unsafe_allow_html=True)

    # Auto-snapshot
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if GH_TOKEN and GH_REPO:
        snap_date = df_full["Ημ/νία Δημιουργίας"].max().strftime("%Y-%m-%d")
        index     = load_index()
        if snap_date not in [s["date"] for s in index]:
            with st.spinner("💾 Αποθήκευση snapshot..."):
                d_all, m_all = metrics(df_full)
                snap = build_snapshot(df_full, m_all, d_all)
                ok = save_snapshot(snap)
            if ok:
                st.markdown(f'<div class="snap-ok">✅ Νέο snapshot αποθηκεύτηκε: {snap_date}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="snap-warn">⚠️ Αποτυχία snapshot — έλεγξε το GitHub token</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="snap-ok">✅ Snapshot {snap_date} υπάρχει ήδη</div>', unsafe_allow_html=True)

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
    dates = [s["date"] for s in reversed(snapshots)]
    if len(dates) >= 2:
        st.markdown("#### 🔍 Σύγκριση δύο ημερομηνιών")
        cc1,cc2 = st.columns(2)
        with cc1: sel1 = st.selectbox("Ημερομηνία Α", dates, key="s1")
        with cc2: sel2 = st.selectbox("Ημερομηνία Β", dates, index=1, key="s2")

        if sel1 != sel2:
            d1 = load_detail(sel1); d2 = load_detail(sel2)
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
    st.markdown("#### 📋 Όλα τα Snapshots")
    for snap in reversed(snapshots):
        pct = snap["sla_pct"]
        bc  = "badge-green" if pct>=90 else "badge-orange" if pct>=75 else "badge-red"
        bl  = "✅ Καλό" if pct>=90 else "⚠️ Μέτριο" if pct>=75 else "❌ Κακό"
        sc  = "#16a34a" if pct>=90 else "#92400e" if pct>=75 else "#b91c1c"
        st.markdown(f"""<div class="hist-card" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:13px;font-weight:700;color:#1a2235;">{snap['date']}</div>
                <div style="font-size:11px;color:#8fa3c0;">{snap['total']:,} αποστολές &nbsp;·&nbsp; {snap['delivered']:,} παραδόθηκαν &nbsp;·&nbsp; Missing SLA: {snap['missing_sla']:,}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:22px;font-weight:800;color:{sc};">{pct:.2f}%</div>
                <span class="badge {bc}">{bl}</span>
            </div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: RECURRING MISSES
# ══════════════════════════════════════════════
elif "Recurring" in page:
    st.markdown('<div class="section-header">RECURRING MISSES</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Πελάτες με επαναλαμβανόμενες καθυστερήσεις σε όλο το ιστορικό</div>', unsafe_allow_html=True)

    snapshots = load_index()
    if len(snapshots) < 2:
        st.info("Χρειάζονται τουλάχιστον 2 snapshots. Κάνε push νέο data.csv και άνοιξε ξανά την Επισκόπηση.")
        st.stop()

    miss_counter = defaultdict(int)
    for snap in snapshots:
        det = load_detail(snap["date"])
        if det and "top_missed_customers" in det:
            for row in det["top_missed_customers"]:
                miss_counter[row["KEY_CLEAN"]] += row["misses"]

    miss_df = pd.DataFrame([
        {"Κωδικός Πελάτη": k, "Συνολικές Καθυστερήσεις": v}
        for k,v in sorted(miss_counter.items(), key=lambda x: -x[1])
    ]).head(30)

    fig = px.bar(miss_df, x="Κωδικός Πελάτη", y="Συνολικές Καθυστερήσεις",
                 color="Συνολικές Καθυστερήσεις",
                 color_continuous_scale=["#fde68a","#f97316","#ef4444"],
                 title="Top 30 πελάτες με τις περισσότερες καθυστερήσεις")
    fig.update_layout(height=380, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(t=40,b=60,l=40,r=10),
                      font=dict(family="Plus Jakarta Sans"), coloraxis_showscale=False,
                      xaxis=dict(tickangle=45))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(miss_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
# PAGE: ΑΝΑΛΥΣΗ ΝΟΜΟΥ
# ══════════════════════════════════════════════
elif "Νομού" in page:
    st.markdown('<div class="section-header">ΑΝΑΛΥΣΗ ΑΝΑ ΝΟΜΟ / ΠΕΡΙΟΧΗ</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Βάσει Regional Unity (φίλτρο ημερομηνιών ισχύει)</div>', unsafe_allow_html=True)

    if "Regional Unity" not in delivered.columns or delivered["Regional Unity"].isna().all():
        st.info("Δεν υπάρχουν δεδομένα Regional Unity στο τρέχον φίλτρο.")
        st.stop()

    reg = (delivered.groupby("Regional Unity")
           .agg(Σύνολο=("on_time","count"), Εντός_SLA=("on_time","sum"))
           .reset_index().rename(columns={"Regional Unity":"Περιοχή"}))
    reg["SLA %"] = (reg["Εντός_SLA"]/reg["Σύνολο"]*100).round(2)
    reg = reg.sort_values("SLA %", ascending=True)

    fig = px.bar(reg, x="SLA %", y="Περιοχή", orientation="h",
                 color="SLA %", color_continuous_scale=["#ef4444","#f97316","#22c55e"],
                 range_color=[50,100], text=reg["SLA %"].apply(lambda x: f"{x:.1f}%"))
    fig.update_traces(textposition="outside")
    fig.update_layout(height=max(400,len(reg)*26), paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(t=10,b=20,l=20,r=70),
                      font=dict(family="Plus Jakarta Sans"), coloraxis_showscale=False,
                      xaxis=dict(range=[0,112], ticksuffix="%"))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(reg.sort_values("SLA %")[["Περιοχή","Σύνολο","Εντός_SLA","SLA %"]],
                 use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
# PAGE: ΡΥΘΜΙΣΕΙΣ
# ══════════════════════════════════════════════
elif "Ρυθμίσεις" in page:
    st.markdown('<div class="section-header">ΡΥΘΜΙΣΕΙΣ</div>', unsafe_allow_html=True)

    st.markdown("#### 🔗 GitHub Σύνδεση")
    if GH_TOKEN and GH_REPO:
        st.success(f"✅ Συνδεδεμένο: `{GH_REPO}` — branch: `{GH_BRANCH}`")
    else:
        st.error("❌ Δεν έχουν οριστεί GitHub credentials στα Secrets")

    st.markdown("#### 💾 Snapshots")
    snapshots = load_index()
    st.info(f"Υπάρχουν **{len(snapshots)}** snapshots αποθηκευμένα στο GitHub (`history/`)")

    if st.button("🔄 Αναγκαστικό snapshot τώρα"):
        with st.spinner("Αποθήκευση..."):
            d_all, m_all = metrics(df_full)
            snap = build_snapshot(df_full, m_all, d_all)
            ok = save_snapshot(snap)
        st.success(f"✅ Snapshot {snap['date']} αποθηκεύτηκε!") if ok else st.error("❌ Αποτυχία")

    if st.button("🗑️ Εκκαθάριση cache δεδομένων"):
        load_and_process.clear()
        load_index.clear()
        st.success("Cache εκκαθαρίστηκε — ανανέωσε τη σελίδα")

    st.markdown("#### 📊 Πληροφορίες δεδομένων")
    st.code(f"""
Data URL  : {GH_RAW}/data.csv
Rows      : {len(df_full):,}
Ημ. range : {df_full['Ημ/νία Δημιουργίας'].min().strftime('%d/%m/%Y')} – {df_full['Ημ/νία Δημιουργίας'].max().strftime('%d/%m/%Y')}
Missing   : {int(df_full['sla_days'].isna().sum()):,}
Snapshots : {len(snapshots)}
    """)
