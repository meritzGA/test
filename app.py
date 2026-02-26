import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import re, io, os, pickle, shutil, json, sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="매니저 활동관리", layout="wide", initial_sidebar_state="collapsed")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">', unsafe_allow_html=True)

DATA_FILE = "app_data.pkl"
CONFIG_FILE = "app_config.pkl"
LOG_DB = "activity_log.db"
BACKUP_DIR = "log_backups"

# =============================================================
# 0. CSS
# =============================================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
:root {
    --mr: 128,0,0; --bg: #fafafa; --card: #ffffff;
    --border: #f0f0f0; --text1: #191f28; --text2: #6b7684; --text3: #8b95a1;
    --green: #00c471; --red: rgb(var(--mr));
    --red-light: rgba(var(--mr),0.06); --radius: 16px;
}
html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
}
.block-container { padding: 1rem 1.2rem !important; max-width: 100% !important; background: var(--bg); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, rgb(128,0,0) 0%, rgb(90,0,0) 100%); }
section[data-testid="stSidebar"] * { color: #fff !important; }
section[data-testid="stSidebar"] label { color: rgba(255,255,255,0.85) !important; }
/* 히어로 */
.hero-card {
    background: linear-gradient(135deg, rgb(128,0,0) 0%, rgb(100,0,0) 40%, rgb(70,0,0) 100%);
    padding: 28px 32px 24px; border-radius: var(--radius); margin-bottom: 20px;
    position: relative; overflow: hidden;
}
.hero-card::after { content:''; position:absolute; top:-40px; right:-40px; width:180px; height:180px; background:rgba(255,255,255,0.04); border-radius:50%; }
.hero-name { color: #fff; font-size: 28px; font-weight: 800; margin: 0; }
.hero-sub { color: #fff; font-size: 15px; font-weight: 500; margin: 6px 0 0; opacity: 0.9; }
/* 메트릭 */
.metric-row { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.metric-card { flex:1; min-width:80px; background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px 12px; text-align:center; }
.metric-card .mc-label { font-size:11px; color:var(--text3); font-weight:600; }
.metric-card .mc-val { font-size:22px; font-weight:800; color:var(--text1); }
.metric-card .mc-sub { font-size:11px; color:var(--text3); }
.metric-card.active { border-color:rgba(var(--mr),0.3); background:var(--red-light); }
.metric-card.active .mc-val { color:var(--red); }
/* 사용인 리스트 버튼 - 뱃지 내장 */
.cust-btn-wrap { position: relative; margin-bottom: 2px; }
.cust-badges { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); display: flex; gap: 3px; z-index: 1; pointer-events: none; }
.cb { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:5px; font-size:10px; font-weight:700; }
.cb.done { background:var(--green); color:#fff; }
.cb.wait { background:#eee; color:#ccc; }
/* 시상 카드 */
.prize-card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px; margin-bottom:8px; }
.prize-card.achieved { border-left:4px solid var(--green); }
.prize-card.partial { border-left:4px solid #ff9500; }
.prize-card.none { border-left:4px solid #e5e8eb; }
.pc-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.pc-name { font-size:14px; font-weight:700; }
.pc-type { font-size:10px; padding:2px 7px; border-radius:5px; font-weight:600; }
.pc-type.weekly { background:rgba(var(--mr),0.08); color:var(--red); }
.pc-type.cumul { background:#e8f5e9; color:#2e7d32; }
.pc-desc { font-size:11px; color:var(--text2); margin-bottom:8px; white-space:pre-line; }
.pc-progress { background:#f5f6f8; border-radius:8px; padding:8px 12px; }
.pc-row { display:flex; justify-content:space-between; padding:2px 0; font-size:13px; }
.pc-row .label { color:var(--text2); }
.pc-row .value { font-weight:700; }
.pc-row .value.green { color:var(--green); }
.pc-row .value.red { color:var(--red); }
.pc-row .value.orange { color:#ff9500; }
.prog-bar { height:5px; background:#eee; border-radius:3px; margin:6px 0 4px; overflow:hidden; }
.prog-fill { height:100%; border-radius:3px; }
.prog-fill.green { background:var(--green); }
.prog-fill.orange { background:#ff9500; }
.prog-fill.red { background:var(--red); }
.tier-table { width:100%; font-size:11px; margin-top:6px; border-collapse:collapse; }
.tier-table th { background:#f8f9fa; padding:4px 6px; text-align:center; font-weight:600; color:var(--text2); border-bottom:1px solid var(--border); }
.tier-table td { padding:4px 6px; text-align:center; border-bottom:1px solid var(--border); color:var(--text2); }
.tier-table tr.hit td { background:rgba(0,196,113,0.06); color:var(--green); font-weight:700; }
.tier-table tr.next td { background:rgba(255,149,0,0.06); color:#ff9500; font-weight:600; }
/* 컴팩트 실적 */
.perf-inline { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
.perf-tag { background:#f5f6f8; border-radius:8px; padding:4px 10px; font-size:12px; }
.perf-tag .pk { color:var(--text3); margin-right:4px; }
.perf-tag .pv { font-weight:700; color:var(--text1); }
/* 파일 카드 */
.file-card { background:var(--card); border-radius:14px; padding:18px; border:1px solid var(--border); margin-bottom:8px; }
.file-card.loaded { border-color:rgba(0,196,113,0.3); background:rgba(0,196,113,0.03); }
/* 모니터링 */
.mon-row { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
.mon-card { flex:1; min-width:140px; background:var(--card); border:1px solid var(--border); border-radius:14px; padding:20px 16px; text-align:center; }
.mon-card .mc-label { font-size:13px; color:var(--text3); font-weight:600; }
.mon-card .mc-num { font-size:32px; font-weight:800; color:var(--text1); margin:6px 0 2px; }
.mon-card .mc-sub { font-size:12px; color:var(--text3); }
.mon-card.red .mc-num { color:var(--red); }
/* 오버라이드 */
.stButton > button { border-radius:12px !important; font-weight:600 !important; border:1px solid var(--border) !important; }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button { background:rgb(var(--mr)) !important; color:#fff !important; border:none !important; }
iframe { width:100% !important; }
@media (max-width:768px) {
    .block-container { padding:0.5rem 0.6rem !important; }
    .hero-card { padding:20px 18px 16px; } .hero-name { font-size:22px; }
    .metric-card .mc-val { font-size:18px; }
}
@media (max-width:480px) {
    .block-container { padding:0.3rem !important; }
    .hero-card { padding:16px 14px; } .hero-name { font-size:20px; }
}
</style>
""", unsafe_allow_html=True)

# =============================================================
# 1. 유틸리티
# =============================================================
def clean_key(val):
    if pd.isna(val) or str(val).strip().lower()=='nan': return ""
    s = str(val).strip().replace(" ","").upper()
    if s.endswith('.0'): s = s[:-2]
    return s

def decode_excel_text(val):
    if pd.isna(val): return val
    s = str(val)
    if '_x' not in s: return s
    return re.sub(r'_x([0-9a-fA-F]{4})_', lambda m: chr(int(m.group(1),16)), s)

@st.cache_data(show_spinner=False)
def load_file_data(file_bytes, file_name):
    df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8', errors='replace') if file_name.endswith('.csv') else pd.read_excel(io.BytesIO(file_bytes))
    for col in df.columns:
        if df[col].dtype == object: df[col] = df[col].apply(decode_excel_text)
    for col in df.columns:
        if any(kw in col for kw in ["코드","번호","ID","id"]):
            if df[col].dtype in ['float64','float32']: df[col] = df[col].apply(lambda x: str(int(x)) if pd.notna(x) else "")
            elif df[col].dtype in ['int64','int32']: df[col] = df[col].astype(str)
    return df

def safe_str(val):
    if val is None or (isinstance(val, float) and pd.isna(val)): return ""
    s = str(val).strip()
    return "" if s.lower() in ('nan','none','nat') else s

def fmt_num(val):
    s = safe_str(val)
    if not s: return ""
    try:
        n = float(s.replace(',',''))
        if n == 0: return ""
        return f"{int(n):,}" if n == int(n) else f"{n:,.1f}"
    except: return "" if s in ("0","0.0") else s

def sanitize_dataframe(df):
    if df is None or df.empty: return df
    for col in df.columns:
        if col.startswith('_'): continue
        if df[col].dtype == object:
            df[col] = df[col].fillna("")
            df[col] = df[col].apply(lambda x: "" if str(x).strip().lower() in ('nan','none','nat') else x)
        elif df[col].dtype in ['float64','float32']:
            text_kw = ['명','코드','번호','ID','id','구분','구간','여부','상태','직책','대상','선물','조직']
            if any(kw in col for kw in text_kw):
                df[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(int(x)) if isinstance(x,float) and x==int(x) else str(x))
            else: df[col] = df[col].fillna(0)
        else:
            if df[col].isna().any(): df[col] = df[col].fillna("")
    return df

def resolve_val(row, col_a, col_b):
    for c in [col_a, col_b]:
        if c and c in row:
            v = safe_str(row[c])
            if v: return v
        if c:
            for sfx in ['_파일1','_파일2']:
                if c+sfx in row:
                    v = safe_str(row[c+sfx])
                    if v: return v
    return ""

def get_row_num(row, col_name):
    if not col_name: return 0
    for c in [col_name] + [col_name+s for s in ['_파일1','_파일2']]:
        if c in row:
            v = safe_str(row[c])
            if v:
                try: return float(v.replace(',',''))
                except: pass
    return 0

# =============================================================
# 2. 저장/불러오기
# =============================================================
def _reset():
    st.session_state['df_merged'] = pd.DataFrame()
    for k in ['file_a_name','file_b_name','join_col_a','join_col_b',
              'manager_col','manager_col2','manager_name_col',
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b',
              'cust_branch_col_a','cust_branch_col_b']:
        st.session_state[k] = ""
    st.session_state['display_cols'] = []
    st.session_state['prize_config'] = []

def load_cfg():
    cfg = None
    for fp in [CONFIG_FILE, CONFIG_FILE+".bak"]:
        if not os.path.exists(fp): continue
        try:
            with open(fp,'rb') as f: d = pickle.load(f)
            if isinstance(d, dict): cfg = d; break
        except: continue
    if cfg is None: cfg = {}
    for k in ['file_a_name','file_b_name','join_col_a','join_col_b',
              'manager_col','manager_col2','manager_name_col',
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b',
              'cust_branch_col_a','cust_branch_col_b']:
        st.session_state[k] = str(cfg.get(k, ""))
    st.session_state['display_cols'] = cfg.get('display_cols', []) if isinstance(cfg.get('display_cols'), list) else []
    st.session_state['prize_config'] = cfg.get('prize_config', []) if isinstance(cfg.get('prize_config'), list) else []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,'rb') as f: data = pickle.load(f)
            df = data.get('df_merged', pd.DataFrame()) if isinstance(data, dict) else pd.DataFrame()
            if isinstance(df, pd.DataFrame) and not df.empty: df = sanitize_dataframe(df)
            st.session_state['df_merged'] = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        except: st.session_state['df_merged'] = pd.DataFrame()

def save_cfg():
    cfg = {}
    for k in ['file_a_name','file_b_name','join_col_a','join_col_b',
              'manager_col','manager_col2','manager_name_col',
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b',
              'cust_branch_col_a','cust_branch_col_b','display_cols','prize_config']:
        cfg[k] = st.session_state.get(k, "")
    try:
        if os.path.exists(CONFIG_FILE): shutil.copy2(CONFIG_FILE, CONFIG_FILE+".bak")
        tmp = CONFIG_FILE+".tmp"
        with open(tmp,'wb') as f: pickle.dump(cfg, f)
        shutil.move(tmp, CONFIG_FILE)
    except: pass

def save_data():
    try:
        tmp = DATA_FILE+".tmp"
        with open(tmp,'wb') as f: pickle.dump({'df_merged': st.session_state.get('df_merged', pd.DataFrame())}, f)
        shutil.move(tmp, DATA_FILE)
    except: pass

def has_data():
    df = st.session_state.get('df_merged')
    return isinstance(df, pd.DataFrame) and not df.empty

# =============================================================
# 3. SQLite — 월별 보존 + 일일 백업
# =============================================================
def get_db():
    conn = sqlite3.connect(LOG_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row; return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS message_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, manager_code TEXT NOT NULL, manager_name TEXT,
        customer_number TEXT NOT NULL, customer_name TEXT, message_type INTEGER NOT NULL,
        sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, month_key TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, manager_code TEXT NOT NULL, manager_name TEXT,
        login_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    for s in ["CREATE INDEX IF NOT EXISTS idx_mm ON message_logs(manager_code)",
              "CREATE INDEX IF NOT EXISTS idx_mk ON message_logs(month_key)",
              "CREATE INDEX IF NOT EXISTS idx_mc ON message_logs(customer_number)"]:
        conn.execute(s)
    conn.commit(); conn.close()

def daily_backup():
    """매일 1회 DB 백업"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    bak_path = os.path.join(BACKUP_DIR, f"log_{today}.db")
    if not os.path.exists(bak_path) and os.path.exists(LOG_DB):
        try: shutil.copy2(LOG_DB, bak_path)
        except: pass
    # 7일 이상 된 백업 삭제 (최근 7일만 유지)
    try:
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        for f in os.listdir(BACKUP_DIR):
            if f.startswith("log_") and f.endswith(".db"):
                fdate = f.replace("log_","").replace(".db","")
                if fdate < cutoff:
                    os.remove(os.path.join(BACKUP_DIR, f))
    except: pass

def log_msg(mc, mn, cn, cna, mt):
    mk = datetime.now().strftime("%Y%m"); conn = get_db()
    conn.execute("INSERT INTO message_logs (manager_code,manager_name,customer_number,customer_name,message_type,month_key) VALUES (?,?,?,?,?,?)",
                 (str(mc),mn,str(cn),cna,mt,mk)); conn.commit(); conn.close()

def get_cust_logs(mc, cn):
    mk = datetime.now().strftime("%Y%m"); conn = get_db()
    rows = conn.execute("SELECT message_type, sent_date FROM message_logs WHERE manager_code=? AND customer_number=? AND month_key=?",
                        (str(mc),str(cn),mk)).fetchall(); conn.close()
    return [dict(r) for r in rows]

def get_mgr_summary(mc):
    mk = datetime.now().strftime("%Y%m"); conn = get_db()
    rows = conn.execute("SELECT message_type, COUNT(DISTINCT customer_number) as u, COUNT(*) as c FROM message_logs WHERE manager_code=? AND month_key=? GROUP BY message_type",
                        (str(mc),mk)).fetchall(); conn.close()
    return {r['message_type']: {'customers':r['u'],'count':r['c']} for r in rows}

def log_login(mc, mn=""):
    conn = get_db(); conn.execute("INSERT INTO login_logs (manager_code,manager_name) VALUES (?,?)", (str(mc),mn)); conn.commit(); conn.close()

def get_available_months():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT month_key FROM message_logs ORDER BY month_key DESC").fetchall()
    conn.close()
    return [r['month_key'] for r in rows] if rows else [datetime.now().strftime("%Y%m")]

def get_msg_summary_by_month(mk):
    conn = get_db()
    df = pd.read_sql("SELECT manager_code as 매니저코드, manager_name as 매니저명, message_type as 메시지유형, COUNT(DISTINCT customer_number) as 발송인원, COUNT(*) as 발송횟수 FROM message_logs WHERE month_key=? GROUP BY manager_code, manager_name, message_type", conn, params=[mk])
    conn.close(); return df

def get_login_summary_by_month(mk):
    conn = get_db()
    df = pd.read_sql("SELECT manager_code as 매니저코드, manager_name as 매니저명, COUNT(*) as 로그인횟수, MAX(login_date) as 최근로그인 FROM login_logs WHERE strftime('%Y%m', login_date)=? GROUP BY manager_code ORDER BY 로그인횟수 DESC", conn, params=[mk])
    conn.close(); return df

def reset_month_logs(mk):
    conn = get_db()
    conn.execute("DELETE FROM message_logs WHERE month_key=?", (mk,))
    conn.execute(f"DELETE FROM login_logs WHERE strftime('%Y%m', login_date)='{mk}'")
    conn.commit(); conn.close()

# =============================================================
# 4. 카카오톡 공유
# =============================================================
def render_kakao(text, label="📋 카톡 보내기", bid="kk", height=55):
    import base64
    enc = base64.b64encode(text.encode('utf-8')).decode('ascii')
    html = f"""<style>
    .kb{{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,#FEE500,#F5D600);
    color:#3C1E1E;border:none;padding:12px 24px;border-radius:12px;font-size:15px;font-weight:700;
    cursor:pointer;width:100%;justify-content:center;font-family:'Pretendard',sans-serif;}}
    .kb:active{{transform:scale(0.97);}}.kb.ok{{background:linear-gradient(135deg,#00c471,#00a85e);color:#fff;}}
    .ks{{font-size:12px;color:#888;margin-top:4px;text-align:center;}}</style>
    <button class="kb" id="{bid}" onclick="ds_{bid}()">
    <svg viewBox="0 0 24 24" fill="#3C1E1E" width="20" height="20"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg>
    {label}</button><div class="ks" id="s_{bid}"></div>
    <script>
    function ds_{bid}(){{var t=decodeURIComponent(escape(atob("{enc}")));
    if(/Mobi|Android|iPhone/i.test(navigator.userAgent)&&navigator.share){{navigator.share({{text:t}}).then(()=>dn_{bid}()).catch(()=>fc_{bid}(t));}}else{{fc_{bid}(t);}}}}
    function fc_{bid}(t){{var a=document.createElement('textarea');a.value=t;a.style.cssText='position:fixed;left:-9999px';
    document.body.appendChild(a);a.select();a.setSelectionRange(0,999999);var ok=false;try{{ok=document.execCommand('copy');}}catch(e){{}}
    document.body.removeChild(a);if(ok){{dn_{bid}();}}else if(navigator.clipboard){{navigator.clipboard.writeText(t).then(()=>dn_{bid}());}}}}
    function dn_{bid}(){{var b=document.getElementById('{bid}');b.classList.add('ok');b.innerHTML='✅ 복사 완료!';
    document.getElementById('s_{bid}').innerHTML='<a href="kakaotalk://launch" style="color:#3B82F6;">카카오톡 열기</a>';
    setTimeout(()=>{{b.classList.remove('ok');b.innerHTML='<svg viewBox="0 0 24 24" fill="#3C1E1E" width="20" height="20"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg> {label}';}},3000);}}
    </script>"""
    components.html(html, height=height)

# =============================================================
# 5. 시상 엔진
# =============================================================
def calc_prize(row, cfgs):
    results = []
    for p in cfgs:
        perf = get_row_num(row, p.get('col_val',''))
        tiers = sorted(p.get('tiers',[]), key=lambda x: x[0], reverse=True)
        existing = get_row_num(row, p.get('col_prize','')) if p.get('col_prize') else 0
        at = ap = 0; nt = np_ = sf = 0
        for th, pr in tiers:
            if perf >= th: at = th; ap = pr; break
            else: nt = th; np_ = pr; sf = th - perf
        if at:
            for th, pr in tiers:
                if th > at: nt = th; np_ = pr; sf = th - perf; break
            else: nt = 0; sf = 0
        mx = tiers[0][0] if tiers else 1
        pct = min(perf / mx * 100, 100) if mx > 0 else 0
        results.append({**p, 'perf': perf, 'achieved_tier': at, 'achieved_prize': ap,
            'next_tier': nt, 'shortfall': sf, 'progress': pct, 'existing_prize': existing, 'sorted_tiers': tiers})
    return results

def prize_card_html(p):
    st_ = "achieved" if p['achieved_tier'] else ("partial" if p['perf']>0 else "none")
    cat = "weekly" if p.get('category')=='weekly' else "cumul"
    cat_lbl = p.get('type','') or ("구간" if cat=='weekly' else "누계")
    pct = min(p['progress'],100)
    bar = "green" if p['achieved_tier'] else ("orange" if p['perf']>0 else "red")
    h = f"<div class='prize-card {st_}'><div class='pc-header'><span class='pc-name'>{p.get('name','')}</span><span class='pc-type {cat}'>{cat_lbl}</span></div>"
    if p.get('desc'): h += f"<div class='pc-desc'>{p['desc']}</div>"
    h += f"<div class='prog-bar'><div class='prog-fill {bar}' style='width:{pct}%'></div></div>"
    h += "<div class='pc-progress'>"
    h += f"<div class='pc-row'><span class='label'>실적</span><span class='value'>{fmt_num(p['perf'])}</span></div>"
    if p['achieved_tier']:
        h += f"<div class='pc-row'><span class='label'>달성</span><span class='value green'>{fmt_num(p['achieved_tier'])} ({fmt_num(p['achieved_prize'])}%)</span></div>"
    if p['existing_prize']>0:
        h += f"<div class='pc-row'><span class='label'>확정</span><span class='value green'>{fmt_num(p['existing_prize'])}원</span></div>"
    if p['next_tier']:
        h += f"<div class='pc-row'><span class='label'>다음</span><span class='value orange'>{fmt_num(p['next_tier'])}</span></div>"
        h += f"<div class='pc-row'><span class='label'>부족</span><span class='value red'>{fmt_num(p['shortfall'])}</span></div>"
    elif p['achieved_tier']:
        h += "<div class='pc-row'><span class='label'>🎉</span><span class='value green'>최고구간!</span></div>"
    h += "</div>"
    if p['sorted_tiers']:
        h += "<table class='tier-table'><tr><th>구간</th><th>시상률</th></tr>"
        for th, pr in p['sorted_tiers']:
            cls = "hit" if p['achieved_tier'] and th==p['achieved_tier'] else ("next" if p['next_tier'] and th==p['next_tier'] else "")
            h += f"<tr class='{cls}'><td>{fmt_num(th)}이상</td><td>{fmt_num(pr)}%</td></tr>"
        h += "</table>"
    h += "</div>"
    return h

# =============================================================
# 6. 초기화
# =============================================================
if 'df_merged' not in st.session_state:
    _reset(); load_cfg()
init_db(); daily_backup()

# =============================================================
# 7. 사이드바
# =============================================================
st.sidebar.markdown("<div style='padding:8px 0 16px;'><span style='font-size:20px;font-weight:800;'>📋 활동관리</span></div>", unsafe_allow_html=True)
try: MGR_PW = os.environ.get("MANAGER_PASSWORD","") or st.secrets.get("MANAGER_PASSWORD","meritz1!")
except: MGR_PW = os.environ.get("MANAGER_PASSWORD","meritz1!")
try: ADM_PW = os.environ.get("ADMIN_PASSWORD","") or st.secrets.get("ADMIN_PASSWORD","wolf7998")
except: ADM_PW = os.environ.get("ADMIN_PASSWORD","wolf7998")
menu = st.sidebar.radio("메뉴", ["📱 매니저 화면","⚙️ 관리자 설정","📊 활동 모니터링"])

# =============================================================
# 8. 관리자 (이전과 동일 — 생략 없이 포함)
# =============================================================
if menu == "⚙️ 관리자 설정":
    st.markdown("<h2 style='font-weight:800;'>⚙️ 관리자 설정</h2>", unsafe_allow_html=True)
    if not st.session_state.get('admin_auth'):
        with st.form("adm"):
            pw = st.text_input("🔒 비밀번호", type="password")
            if st.form_submit_button("로그인", use_container_width=True):
                if pw == ADM_PW: st.session_state['admin_auth'] = True; st.rerun()
                else: st.error("❌ 비밀번호 오류")
        st.stop()
    st.markdown("### 📂 데이터 파일")
    if has_data(): st.success(f"✅ **{len(st.session_state['df_merged']):,}행** 운영 중")
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**파일 A**")
        if 'df_file_a' in st.session_state and st.session_state['df_file_a'] is not None:
            fa = st.session_state['df_file_a']
            st.markdown(f"<div class='file-card loaded'>✅ <b>{st.session_state.get('file_a_name','')}</b><br><span style='color:#6b7684;font-size:13px;'>{len(fa):,}행 × {len(fa.columns)}열</span></div>", unsafe_allow_html=True)
            if st.button("🗑️ 삭제", key="da"): del st.session_state['df_file_a']; st.session_state['file_a_name']=""; st.rerun()
        else:
            f = st.file_uploader("업로드", type=['csv','xlsx'], key="ua", label_visibility="collapsed")
            if f: st.session_state['df_file_a'] = load_file_data(f.getvalue(), f.name); st.session_state['file_a_name'] = f.name; st.rerun()
    with cb:
        st.markdown("**파일 B**")
        if 'df_file_b' in st.session_state and st.session_state['df_file_b'] is not None:
            fb = st.session_state['df_file_b']
            st.markdown(f"<div class='file-card loaded'>✅ <b>{st.session_state.get('file_b_name','')}</b><br><span style='color:#6b7684;font-size:13px;'>{len(fb):,}행 × {len(fb.columns)}열</span></div>", unsafe_allow_html=True)
            if st.button("🗑️ 삭제", key="db"): del st.session_state['df_file_b']; st.session_state['file_b_name']=""; st.rerun()
        else:
            f = st.file_uploader("업로드", type=['csv','xlsx'], key="ub", label_visibility="collapsed")
            if f: st.session_state['df_file_b'] = load_file_data(f.getvalue(), f.name); st.session_state['file_b_name'] = f.name; st.rerun()
    fa_ok = 'df_file_a' in st.session_state and st.session_state.get('df_file_a') is not None
    fb_ok = 'df_file_b' in st.session_state and st.session_state.get('df_file_b') is not None
    if fa_ok and fb_ok:
        st.markdown("---"); st.markdown("### 🔗 조인 & 병합")
        ca2 = st.session_state['df_file_a'].columns.tolist(); cb2 = st.session_state['df_file_b'].columns.tolist()
        pja = st.session_state.get('join_col_a',''); pjb = st.session_state.get('join_col_b','')
        ia = ca2.index(pja) if pja in ca2 else (ca2.index('본인고객번호') if '본인고객번호' in ca2 else 0)
        ib = cb2.index(pjb) if pjb in cb2 else (cb2.index('본인고객번호') if '본인고객번호' in cb2 else 0)
        j1, j2 = st.columns(2)
        with j1: ja = st.selectbox("파일A 조인키", ca2, index=ia, key="sja")
        with j2: jb = st.selectbox("파일B 조인키", cb2, index=ib, key="sjb")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔗 병합", type="primary", use_container_width=True):
                with st.spinner("병합..."):
                    da = st.session_state['df_file_a'].copy(); db = st.session_state['df_file_b'].copy()
                    da['_mk_a'] = da[ja].apply(clean_key); db['_mk_b'] = db[jb].apply(clean_key)
                    m = pd.merge(da, db, left_on='_mk_a', right_on='_mk_b', how='outer', suffixes=('_파일1','_파일2'))
                    for c1 in [c for c in m.columns if c.endswith('_파일1')]:
                        base = c1.replace('_파일1',''); c2c = base+'_파일2'
                        if c2c in m.columns: m[base] = m[c1].combine_first(m[c2c]); m.drop(columns=[c1,c2c], inplace=True)
                    m['_search_key'] = m['_mk_a'].combine_first(m['_mk_b'])
                    m = sanitize_dataframe(m)
                    st.session_state['df_merged'] = m.copy()
                    st.session_state['join_col_a'] = ja; st.session_state['join_col_b'] = jb
                    save_data(); save_cfg(); st.success(f"✅ {len(m):,}행"); st.rerun()
        with b2:
            if has_data() and st.button("🗑️ 삭제", key="dm", use_container_width=True):
                st.session_state['df_merged'] = pd.DataFrame(); save_data(); st.rerun()
    elif fa_ok or fb_ok:
        sd = st.session_state.get('df_file_a') if fa_ok else st.session_state.get('df_file_b')
        if sd is not None and st.button("📄 단일 파일 사용"):
            st.session_state['df_merged'] = sanitize_dataframe(sd.copy()); save_data(); save_cfg(); st.rerun()
    if has_data():
        df = st.session_state['df_merged']
        with st.expander(f"📋 미리보기 ({len(df):,}행)", expanded=False):
            av = [c for c in df.columns if not c.startswith('_')]
            st.dataframe(df[av].head(30).fillna(""), use_container_width=True, height=250)
        st.markdown("---"); st.markdown("### 🏷️ 열 매핑")
        av = [c for c in df.columns if not c.startswith('_')]; opts = ["(없음)"] + av
        def si(k, cands, ol):
            p = st.session_state.get(k,'')
            if p in ol: return ol.index(p)
            for c in cands:
                if c in ol: return ol.index(c)
            return 0
        st.markdown("#### 🔑 매니저")
        m1, m2 = st.columns(2)
        with m1: mc1 = st.selectbox("매니저코드 (A)", av, index=si('manager_col',['매니저코드'],av), key="cm1")
        with m2: mc2 = st.selectbox("매니저코드 (B)", opts, index=si('manager_col2',['지원매니저코드'],opts), key="cm2")
        mn_col = st.selectbox("매니저 이름", av, index=si('manager_name_col',['매니저명','지원매니저명'],av), key="cmn")
        st.markdown("#### 👤 사용인 (파일별)")
        n1, n2 = st.columns(2)
        with n1: cna = st.selectbox("사용인명 (A)", opts, index=si('cust_name_col_a',['현재대리점설계사조직명'],opts), key="cna")
        with n2: cnb = st.selectbox("사용인명 (B)", opts, index=si('cust_name_col_b',['대리점설계사명'],opts), key="cnb")
        c1c, c2c = st.columns(2)
        with c1c: cca = st.selectbox("사용인코드 (A)", opts, index=si('cust_code_col_a',['현재대리점설계사조직코드'],opts), key="cca")
        with c2c: ccb = st.selectbox("사용인코드 (B)", opts, index=si('cust_code_col_b',['대리점설계사조직코드'],opts), key="ccb")
        b1c, b2c = st.columns(2)
        with b1c: cba = st.selectbox("지사명 (A)", opts, index=si('cust_branch_col_a',['현재대리점지사명'],opts), key="cba")
        with b2c: cbb = st.selectbox("지사명 (B)", opts, index=si('cust_branch_col_b',['대리점지사명'],opts), key="cbb")
        st.markdown("---"); st.markdown("### 📋 실적 표시 항목")
        rec = ['인보험실적','목표금액','인정실적','부족금액','이전월인정실적','구간','실적_1주차','실적_2주차','실적_3주차','실적계','시상금계','추가예정금계','시상금계and추가예정금계']
        prev = st.session_state.get('display_cols',[]); dd = prev if prev else [c for c in rec if c in av]
        dc = st.multiselect("표시 항목", av, default=[c for c in dd if c in av], key="cdc")
        st.markdown("---"); st.markdown("### 🏆 시상 시책 JSON")
        pc = st.session_state.get('prize_config',[])
        if pc:
            st.success(f"✅ {len(pc)}개 시책")
            if st.button("🗑️ 시책 삭제"): st.session_state['prize_config'] = []; save_cfg(); st.rerun()
        jf = st.file_uploader("시상 JSON", type=["json"], key="uj")
        if jf:
            try:
                jd = json.load(jf)
                if isinstance(jd, list): st.session_state['prize_config'] = jd; save_cfg(); st.success(f"✅ {len(jd)}개"); st.rerun()
            except: st.error("유효하지 않은 JSON")
        st.markdown("---")
        if st.button("💾 설정 저장", type="primary", use_container_width=True):
            st.session_state['manager_col'] = mc1
            st.session_state['manager_col2'] = mc2 if mc2!="(없음)" else ""
            st.session_state['manager_name_col'] = mn_col
            for k, v in [('cust_name_col_a',cna),('cust_name_col_b',cnb),('cust_code_col_a',cca),('cust_code_col_b',ccb),('cust_branch_col_a',cba),('cust_branch_col_b',cbb)]:
                st.session_state[k] = v if v!="(없음)" else ""
            st.session_state['display_cols'] = dc
            save_cfg(); st.success("✅ 저장!"); st.rerun()
        with st.expander("⚠️ 초기화"):
            cf = st.text_input("'reset' 입력", key="rcf")
            if st.button("🔄 초기화", disabled=(cf!="reset")):
                for fp in [CONFIG_FILE,DATA_FILE,LOG_DB]:
                    try:
                        if os.path.exists(fp): os.remove(fp)
                    except: pass
                _reset(); st.rerun()

# =============================================================
# 9. 매니저 화면
# =============================================================
elif menu == "📱 매니저 화면":
    st.session_state['admin_auth'] = False
    if not has_data() or not st.session_state.get('manager_col'):
        st.markdown("<div class='hero-card'><h1 class='hero-name'>매니저 활동관리</h1><p class='hero-sub'>관리자 설정 미완료</p></div>", unsafe_allow_html=True); st.stop()
    df = st.session_state['df_merged'].copy()
    mc1 = st.session_state['manager_col']; mc2 = st.session_state.get('manager_col2','')
    mn_col = st.session_state.get('manager_name_col', mc1)
    _cna = st.session_state.get('cust_name_col_a',''); _cnb = st.session_state.get('cust_name_col_b','')
    _cca = st.session_state.get('cust_code_col_a',''); _ccb = st.session_state.get('cust_code_col_b','')
    _cba = st.session_state.get('cust_branch_col_a',''); _cbb = st.session_state.get('cust_branch_col_b','')
    dcfg = st.session_state.get('display_cols',[]); pcfg = st.session_state.get('prize_config',[])

    if not st.session_state.get('mgr_in'):
        st.markdown("<div class='hero-card'><h1 class='hero-name'>매니저 로그인</h1><p class='hero-sub'>매니저 코드와 비밀번호를 입력하세요</p></div>", unsafe_allow_html=True)
        with st.form("ml"):
            ci = st.text_input("매니저 코드", placeholder="코드 입력")
            pi = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인", use_container_width=True):
                if pi != MGR_PW: st.error("❌ 비밀번호 오류")
                elif not ci: st.error("코드를 입력하세요")
                else:
                    cc = clean_key(ci)
                    df['_s1'] = df[mc1].apply(clean_key); mask = df['_s1']==cc
                    if mc2 and mc2 in df.columns: df['_s2'] = df[mc2].apply(clean_key); mask = mask|(df['_s2']==cc)
                    my = df[mask]
                    if my.empty: st.error(f"❌ '{ci}' 매칭 없음")
                    else:
                        mn = "매니저"
                        if mn_col in my.columns:
                            ns = my[mn_col].dropna(); ns = ns[ns.astype(str).str.strip()!='']
                            if not ns.empty:
                                n = safe_str(ns.iloc[0])
                                if n: mn = n
                        st.session_state.update({'mgr_in':True,'mgr_code':cc,'mgr_name':mn,'sel_cust':None})
                        log_login(cc, mn); st.rerun()
        st.stop()

    mgr_c = st.session_state['mgr_code']; mgr_n = st.session_state['mgr_name']
    df['_s1'] = df[mc1].apply(clean_key); mask = df['_s1']==mgr_c
    if mc2 and mc2 in df.columns: df['_s2'] = df[mc2].apply(clean_key); mask = mask|(df['_s2']==mgr_c)
    my = df[mask].copy().reset_index(drop=True)

    # ── 정렬: 지사명 → 이름 순 ──
    sort_cols = []
    for idx_r, row_r in my.iterrows():
        co_r = resolve_val(row_r, _cba, _cbb) or resolve_val(row_r, '현재대리점지사명','대리점지사명')
        cn_r = resolve_val(row_r, _cna, _cnb) or resolve_val(row_r, '현재대리점설계사조직명','대리점설계사명')
        sort_cols.append((co_r, cn_r))
    my['_sort_branch'] = [s[0] for s in sort_cols]
    my['_sort_name'] = [s[1] for s in sort_cols]
    my = my.sort_values(['_sort_branch','_sort_name']).reset_index(drop=True)

    h1, h2 = st.columns([5,1])
    with h1:
        st.markdown(f"<div class='hero-card'><h1 class='hero-name'>{mgr_n} 매니저님</h1><p class='hero-sub'>사용인 {len(my)}명 · {datetime.now().strftime('%Y년 %m월')}</p></div>", unsafe_allow_html=True)
    with h2:
        st.write("")
        if st.button("🚪 로그아웃"): st.session_state['mgr_in']=False; st.session_state['sel_cust']=None; st.rerun()

    smry = get_mgr_summary(mgr_c)
    ml = {1:"①인사말",2:"②리플렛",3:"③시상",4:"④시상+실적"}
    mh = "<div class='metric-row'>"
    for mt, lb in ml.items():
        inf = smry.get(mt,{'customers':0,'count':0})
        ac = " active" if inf['customers']>0 else ""
        mh += f"<div class='metric-card{ac}'><div class='mc-label'>{lb}</div><div class='mc-val'>{inf['customers']}명</div><div class='mc-sub'>{inf['count']}회</div></div>"
    mh += "</div>"; st.markdown(mh, unsafe_allow_html=True)

    cl, cd = st.columns([2,3])
    with cl:
        st.markdown(f"<p style='font-size:16px;font-weight:700;margin-bottom:8px;'>👥 사용인 ({len(my)}명)</p>", unsafe_allow_html=True)
        srch = st.text_input("🔍", placeholder="이름/소속 검색", key="cs", label_visibility="collapsed")
        fdf = my.copy()
        if srch: fdf = fdf[fdf.apply(lambda r: srch.lower() in str(r.values).lower(), axis=1)]
        for idx, row in fdf.iterrows():
            co = resolve_val(row, _cba, _cbb) or resolve_val(row, '현재대리점지사명','대리점지사명')
            cn = resolve_val(row, _cna, _cnb) or resolve_val(row, '현재대리점설계사조직명','대리점설계사명') or safe_str(row.get('본인고객번호',''))
            cc = resolve_val(row, _cca, _ccb) or resolve_val(row, '현재대리점설계사조직코드','대리점설계사조직코드')
            cnum = safe_str(row.get('본인고객번호','')) or safe_str(row.get('_search_key',''))
            logs = get_cust_logs(mgr_c, cnum) if cnum else []
            stypes = set(l['message_type'] for l in logs)
            # 뱃지를 버튼 라벨에 내장
            badges = "".join(f"{'✅' if mt in stypes else '⬜'}" for mt in [1,2,3,4])
            bl = f"{co} | {cn}" if co else cn
            bl_with_badge = f"{bl}  [{badges}]"
            if st.button(bl_with_badge, key=f"c_{idx}", use_container_width=True):
                cr = {k: (safe_str(v) if not isinstance(v,(int,float,np.integer,np.floating)) or pd.isna(v) else v) for k,v in row.to_dict().items()}
                st.session_state['sel_cust'] = {'idx':idx,'name':cn,'org':co,'code':cc,'num':cnum,'row':cr}; st.rerun()

    with cd:
        sel = st.session_state.get('sel_cust')
        if sel is None:
            st.markdown("<div style='text-align:center;padding:60px 20px;color:#8b95a1;'><p style='font-size:48px;margin-bottom:12px;'>👈</p><p>사용인을 선택하세요</p></div>", unsafe_allow_html=True)
        else:
            cn = sel['name']; cnum = sel['num']; co = sel['org']; cc = sel.get('code',''); crow = sel['row']
            hp = []
            if co: hp.append(co)
            if cc: hp.append(f"코드: {cc}")
            st.markdown(f"<div style='margin-bottom:8px;'><span style='font-size:20px;font-weight:800;'>{cn}</span><br><span style='font-size:13px;color:#6b7684;'>{' · '.join(hp)}</span></div>", unsafe_allow_html=True)

            logs = get_cust_logs(mgr_c, cnum); stypes = set(l['message_type'] for l in logs)
            sh = "<div style='display:flex;gap:6px;margin-bottom:12px;'>"
            for mt, lb in ml.items():
                if mt in stypes: sh += f"<span style='background:#00c471;color:#fff;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600;'>{lb} ✅</span>"
                else: sh += f"<span style='background:#f2f4f6;color:#bbb;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600;'>{lb}</span>"
            sh += "</div>"; st.markdown(sh, unsafe_allow_html=True)

            # 시상
            if pcfg:
                st.markdown("<p style='font-size:15px;font-weight:700;margin:4px 0;'>🏆 시상 현황</p>", unsafe_allow_html=True)
                prs = calc_prize(crow, pcfg)
                ph = "<div>"
                for pr in prs: ph += prize_card_html(pr)
                ph += "</div>"; st.markdown(ph, unsafe_allow_html=True)

            # ── 컴팩트 실적 (인라인 태그) ──
            if dcfg:
                perf_tags = []
                for col in dcfg:
                    val = crow.get(col)
                    if val is None:
                        for sfx in ['_파일1','_파일2']:
                            if col+sfx in crow: val = crow[col+sfx]; break
                    dv = safe_str(val)
                    if not dv or dv in ('0','0.0'): continue
                    if isinstance(val,(int,float,np.integer,np.floating)) and not pd.isna(val): dv = fmt_num(val)
                    if dv: perf_tags.append((col, dv))
                if perf_tags:
                    ph = "<div class='perf-inline'>"
                    for k, v in perf_tags:
                        ph += f"<span class='perf-tag'><span class='pk'>{k}</span><span class='pv'>{v}</span></span>"
                    ph += "</div>"
                    st.markdown(ph, unsafe_allow_html=True)

            # ── 메시지 발송 ──
            st.markdown("---")
            st.markdown("<p style='font-size:15px;font-weight:700;'>📤 메시지 발송</p>", unsafe_allow_html=True)
            t1, t2, t3, t4 = st.tabs(["①인사말","②리플렛","③시상","④시상+실적"])

            with t1:
                # 인사말 저장 버튼 방식
                gr_key = f"g_{cnum}"
                gr = st.text_area("인사말 입력", placeholder="안녕하세요! 이번 달도 화이팅입니다!", key=gr_key, height=80)
                if st.button("💬 메시지 생성", key=f"gb_{cnum}", use_container_width=True):
                    if gr:
                        st.session_state[f'msg1_{cnum}'] = f"안녕하세요, {cn}님!\n{mgr_n} 매니저입니다.\n\n{gr}"
                    else:
                        st.warning("인사말을 입력하세요.")
                saved_msg = st.session_state.get(f'msg1_{cnum}','')
                if saved_msg:
                    st.text_area("미리보기", saved_msg, height=100, disabled=True, key=f"p1_{cnum}")
                    render_kakao(saved_msg, "📋 인사말 카톡", f"k1_{cnum}")
                    if st.button("✅ 발송 기록", key=f"l1_{cnum}", type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,1); st.success("✅"); st.rerun()

            with t2:
                lf = st.file_uploader("리플렛", type=["png","jpg","jpeg","pdf"], key=f"lf_{cnum}")
                if lf:
                    msg = f"📎 {mgr_n} 매니저 → {cn}님 리플렛\n첨부: {lf.name}"
                    st.text_area("미리보기", msg, height=80, disabled=True, key=f"p2_{cnum}")
                    render_kakao(msg, "📋 리플렛 카톡", f"k2_{cnum}")
                    if st.button("✅ 발송 기록", key=f"l2_{cnum}", type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,2); st.success("✅"); st.rerun()

            with t3:
                if pcfg:
                    prs = calc_prize(crow, pcfg)
                    lines = ["📋 메리츠 시상 현황 안내", f"📅 {datetime.now().strftime('%Y.%m.%d')} 기준", "",
                             f"👤 {co+' ' if co else ''}{cn} 팀장님", ""]
                    weekly = [p for p in prs if p.get('category')=='weekly']
                    cumul = [p for p in prs if p.get('category')=='cumulative']
                    if weekly:
                        lines.append("━━ 시책 현황 ━━")
                        for pr in weekly:
                            lines.append(f"  {pr['name']}: {fmt_num(pr['perf'])}")
                            if pr['achieved_tier']: lines.append(f"  ✅ {fmt_num(pr['achieved_tier'])} 달성 ({fmt_num(pr['achieved_prize'])}%)")
                            if pr['next_tier']: lines.append(f"  🎯 다음 {fmt_num(pr['next_tier'])}까지"); lines.append(f"  🔴 부족: {fmt_num(pr['shortfall'])}")
                            lines.append("")
                    if cumul:
                        lines.append("━━ 누계 시상 ━━")
                        for pr in cumul:
                            if pr['existing_prize']>0: lines.append(f"  {pr['name']}: {fmt_num(pr['existing_prize'])}원")
                            elif pr['perf']>0: lines.append(f"  {pr['name']}: 실적 {fmt_num(pr['perf'])}")
                        lines.append("")
                    tp = sum(p['existing_prize'] for p in cumul if p['existing_prize']>0)
                    if tp>0: lines.append(f"💰 예상 시상금: {fmt_num(tp)}원"); lines.append("")
                    lines += ["부족한 거 챙겨서 꼭 시상 많이 받아 가셨으면 좋겠습니다!","좋은 하루 되세요! 😊"]
                    msg = "\n".join(lines)
                    st.text_area("미리보기", msg, height=220, disabled=True, key=f"p3_{cnum}")
                    render_kakao(msg, "📋 시상 카톡", f"k3_{cnum}")
                    if st.button("✅ 발송 기록", key=f"l3_{cnum}", type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,3); st.success("✅"); st.rerun()
                else: st.info("관리자에서 시상 JSON 업로드 필요")

            with t4:
                lines = ["📋 메리츠 시상 현황 안내", f"📅 {datetime.now().strftime('%Y.%m.%d')} 기준","",f"👤 {co+' ' if co else ''}{cn} 팀장님",""]
                if dcfg:
                    lines.append("━━ 실적 현황 ━━")
                    for col in dcfg:
                        val = crow.get(col)
                        if val is None:
                            for sfx in ['_파일1','_파일2']:
                                if col+sfx in crow: val = crow[col+sfx]; break
                        dv = safe_str(val)
                        if dv and dv not in ('0','0.0'):
                            if isinstance(val,(int,float)) and not pd.isna(val): dv = fmt_num(val)
                            if dv:
                                pfx = "  🔴 " if '부족' in col else ("  🎯 " if '목표' in col else "  ")
                                lines.append(f"{pfx}{col}: {dv}")
                    lines.append("")
                if pcfg:
                    prs = calc_prize(crow, pcfg)
                    weekly = [p for p in prs if p.get('category')=='weekly']
                    cumul = [p for p in prs if p.get('category')=='cumulative']
                    if weekly:
                        lines.append("━━ 시책 현황 ━━")
                        for pr in weekly:
                            s = "✅" if pr['achieved_tier'] else "⬜"
                            lines.append(f"  {s} {pr['name']}: {fmt_num(pr['perf'])}")
                            if pr['shortfall']>0: lines.append(f"     🔴 다음 {fmt_num(pr['next_tier'])}까지 {fmt_num(pr['shortfall'])}")
                        lines.append("")
                    if cumul:
                        lines.append("━━ 누계 시상 ━━")
                        for pr in cumul:
                            if pr['existing_prize']>0: lines.append(f"  {pr['name']}: {fmt_num(pr['existing_prize'])}원")
                        lines.append("")
                    tp = sum(p['existing_prize'] for p in cumul if p['existing_prize']>0)
                    if tp>0: lines.append(f"💰 예상 시상금: {fmt_num(tp)}원"); lines.append("")
                lines += ["부족한 거 챙겨서 꼭 시상 많이 받아 가셨으면 좋겠습니다!","좋은 하루 되세요! 😊"]
                if len(lines)>7:
                    msg = "\n".join(lines)
                    st.text_area("미리보기", msg, height=280, disabled=True, key=f"p4_{cnum}")
                    render_kakao(msg, "📋 시상+실적 카톡", f"k4_{cnum}")
                    if st.button("✅ 발송 기록", key=f"l4_{cnum}", type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,4); st.success("✅"); st.rerun()
                else: st.info("데이터 없음")

# =============================================================
# 10. 모니터링 — 월별 조회 + 통계 초기화 + 백업
# =============================================================
elif menu == "📊 활동 모니터링":
    st.markdown("<h2 style='font-weight:800;'>📊 활동 모니터링</h2>", unsafe_allow_html=True)

    # 월 선택
    months = get_available_months()
    cur_mk = datetime.now().strftime("%Y%m")
    if cur_mk not in months: months = [cur_mk] + months
    month_labels = {m: f"{m[:4]}년 {m[4:]}월" for m in months}
    sel_mk = st.selectbox("📅 조회 월 선택", months, format_func=lambda x: month_labels.get(x, x), key="mon_sel")

    ldf = get_login_summary_by_month(sel_mk)
    mdf = get_msg_summary_by_month(sel_mk)
    tm = ldf['매니저코드'].nunique() if not ldf.empty else 0
    tc = int(mdf['발송횟수'].sum()) if not mdf.empty else 0
    tp = int(mdf['발송인원'].sum()) if not mdf.empty else 0

    st.markdown(f"""<div class='mon-row'>
        <div class='mon-card red'><div class='mc-label'>로그인 매니저</div><div class='mc-num'>{tm}</div><div class='mc-sub'>명</div></div>
        <div class='mon-card'><div class='mc-label'>총 발송</div><div class='mc-num'>{tc}</div><div class='mc-sub'>건</div></div>
        <div class='mon-card'><div class='mc-label'>발송 대상</div><div class='mc-num'>{tp}</div><div class='mc-sub'>명</div></div>
    </div>""", unsafe_allow_html=True)

    if not ldf.empty:
        st.markdown("#### 🔐 로그인"); st.dataframe(ldf, use_container_width=True, hide_index=True)
    if not mdf.empty:
        st.markdown("#### 📤 발송")
        mlm = {1:"①인사말",2:"②리플렛",3:"③시상",4:"④시상+실적"}
        mdf['메시지유형'] = mdf['메시지유형'].map(mlm)
        pc = mdf.pivot_table(index=['매니저코드','매니저명'], columns='메시지유형', values='발송인원', fill_value=0).reset_index()
        st.markdown("**인원**"); st.dataframe(pc, use_container_width=True, hide_index=True)
        pk = mdf.pivot_table(index=['매니저코드','매니저명'], columns='메시지유형', values='발송횟수', fill_value=0).reset_index()
        st.markdown("**횟수**"); st.dataframe(pk, use_container_width=True, hide_index=True)
        csv = mdf.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV 다운로드", csv, f"summary_{sel_mk}.csv", "text/csv")

    # 통계 초기화 + 백업 다운로드
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🗑️ 통계 초기화")
        st.caption(f"선택한 월({month_labels.get(sel_mk,'')})의 발송/로그인 기록을 삭제합니다.")
        if st.button(f"🗑️ {month_labels.get(sel_mk,'')} 초기화", type="primary"):
            reset_month_logs(sel_mk)
            st.success(f"✅ {month_labels.get(sel_mk,'')} 통계가 초기화되었습니다.")
            st.rerun()
    with c2:
        st.markdown("#### 💾 백업 다운로드")
        st.caption("DB 파일을 다운로드하여 백업합니다. 매일 자동 백업도 진행됩니다.")
        if os.path.exists(LOG_DB):
            with open(LOG_DB, 'rb') as f:
                db_bytes = f.read()
            st.download_button("💾 DB 백업 다운로드", db_bytes, f"activity_log_{datetime.now().strftime('%Y%m%d')}.db", "application/octet-stream")
        # 자동 백업 파일 목록
        if os.path.exists(BACKUP_DIR):
            baks = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], reverse=True)
            if baks:
                st.caption(f"자동 백업: {len(baks)}개 (최근 30일)")
                for bk in baks[:5]:
                    bk_path = os.path.join(BACKUP_DIR, bk)
                    with open(bk_path, 'rb') as f:
                        st.download_button(f"📁 {bk}", f.read(), bk, "application/octet-stream", key=f"bk_{bk}")
