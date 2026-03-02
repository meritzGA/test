import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import re, io, os, pickle, shutil, json, sqlite3, base64
from datetime import datetime, timedelta

st.set_page_config(page_title="매니저 활동관리", layout="wide", initial_sidebar_state="collapsed")
st.markdown('<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,interactive-widget=overlays-content">', unsafe_allow_html=True)
st.markdown("""<style>
/* 모바일 키보드로 인한 레이아웃 변경 방지 */
@supports (height: 100dvh) { html,body { height:100dvh; } }
</style>
<script>
(function(){
    // visualViewport resize 이벤트로 인한 Streamlit rerun 방지
    if(window.visualViewport){
        var initH=window.visualViewport.height;
        window.visualViewport.addEventListener('resize',function(e){e.stopPropagation();},true);
    }
})();
</script>""", unsafe_allow_html=True)

DATA_FILE="app_data.pkl"; CONFIG_FILE="app_config.pkl"; LOG_DB="activity_log.db"; BACKUP_DIR="log_backups"

# =============================================================
# 0. CSS — 세련된 디자인
# =============================================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
:root { --mr:128,0,0; --bg:#f7f8fa; --card:#fff; --border:#eaedf0; --text1:#191f28; --text2:#6b7684; --text3:#8b95a1; --green:#00c471; --red:rgb(var(--mr)); --radius:16px; }
html,body,[class*="css"]{ font-family:'Pretendard',-apple-system,BlinkMacSystemFont,system-ui,'Apple SD Gothic Neo','Noto Sans KR',sans-serif; }
.block-container { padding:.8rem 1rem !important; max-width:100% !important; background:var(--bg); }
section[data-testid="stSidebar"] { background:linear-gradient(180deg,rgb(128,0,0) 0%,rgb(80,0,0) 100%); }
section[data-testid="stSidebar"] * { color:#fff !important; }
section[data-testid="stSidebar"] label { color:rgba(255,255,255,0.85) !important; }
section[data-testid="stSidebar"] .stRadio label span { color:#fff !important; font-weight:600; }
/* 히어로 — 흰색 글씨 강제 */
.hero-card {
    background:linear-gradient(135deg,rgb(128,0,0) 0%,rgb(95,0,0) 50%,rgb(65,0,0) 100%);
    padding:24px 28px 20px; border-radius:var(--radius); margin-bottom:14px;
    position:relative; overflow:hidden; box-shadow:0 4px 20px rgba(128,0,0,0.15);
}
.hero-card::after { content:''; position:absolute; top:-50px; right:-50px; width:200px; height:200px; background:rgba(255,255,255,0.03); border-radius:50%; }
.hero-card h1, .hero-card p, .hero-card span { color:#ffffff !important; }
.hero-name { color:#ffffff !important; font-size:26px; font-weight:800; margin:0; letter-spacing:-0.5px; }
.hero-sub { color:#ffffff !important; font-size:14px; font-weight:400; margin:5px 0 0; opacity:0.85; }
/* 메트릭 */
.metric-row { display:flex; gap:8px; margin-bottom:12px; }
.metric-card { flex:1; min-width:70px; background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 8px; text-align:center; transition:all .15s; }
.metric-card .mc-label { font-size:10px; color:var(--text3); font-weight:600; letter-spacing:-0.3px; }
.metric-card .mc-val { font-size:20px; font-weight:800; color:var(--text1); line-height:1.2; }
.metric-card .mc-sub { font-size:10px; color:var(--text3); }
.metric-card.active { border-color:rgba(var(--mr),0.25); background:rgba(var(--mr),0.04); }
.metric-card.active .mc-val { color:var(--red); }
/* 일반 버튼 */
.stButton > button { border-radius:8px !important; font-weight:600 !important; border:1px solid var(--border) !important; text-align:center !important; justify-content:center !important; padding:3px 10px !important; font-size:12px !important; transition:all .1s !important; color:var(--text2) !important; }
.stButton > button:hover { background:rgba(var(--mr),0.06) !important; border-color:rgba(var(--mr),0.3) !important; color:rgb(var(--mr)) !important; }
/* Primary 버튼 */
.stButton > button[kind="primary"],[data-testid="stFormSubmitButton"]>button { background:rgb(var(--mr)) !important; color:#fff !important; border:none !important; padding:6px 10px !important; font-size:13px !important; }
/* 리스트 카드 */
.lc { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 14px 8px; margin-bottom:0; }
.lc-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.lc-info { flex:1; min-width:0; }
.lc-org { font-size:14px; color:var(--text2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; line-height:1.3; font-weight:600; }
.lc-name { font-size:20px; font-weight:900; color:var(--text1); line-height:1.25; letter-spacing:-0.5px; }
.lc-perfs { display:flex; gap:4px; flex-shrink:0; flex-wrap:wrap; justify-content:flex-end; }
.lc-pill { display:inline-flex; flex-direction:column; align-items:center; justify-content:center; min-width:50px; border-radius:10px; font-weight:800; padding:3px 8px; line-height:1.2; }
.lc-pill .pl-lbl { font-size:9px; font-weight:600; opacity:0.75; }
.lc-pill .pl-val { font-size:13px; font-weight:900; }
.lc-pill.r { background:rgba(var(--mr),0.1); color:rgb(var(--mr)); }
.lc-pill.g { background:#e8f5e9; color:#2e7d32; }
.lc-bottom { display:flex; gap:4px; margin-top:6px; }
.lc-dot { display:flex; align-items:center; gap:3px; font-size:11px; color:var(--text3); padding:2px 6px; border-radius:5px; background:#f7f8fa; font-weight:500; }
.lc-dot.done { background:#00a85e; color:#fff; font-weight:700; }
.lc-dot .dot { width:7px; height:7px; border-radius:50%; background:#d5d8db; flex-shrink:0; }
.lc-dot.done .dot { background:#fff; }
/* 사용인 정보 카드 */
.info-card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:12px 16px; margin-bottom:8px; }
.info-card .ic-name { font-size:22px; font-weight:800; color:var(--text1); }
.info-card .ic-meta { font-size:14px; color:var(--text2); margin-top:3px; }
.info-badges { display:flex; gap:5px; margin-top:8px; }
.info-badges .ib { padding:3px 10px; border-radius:6px; font-size:13px; font-weight:600; }
.info-badges .ib.done { background:#00a85e; color:#fff; }
.info-badges .ib.wait { background:#f2f4f6; color:#c4c9d0; }
/* 탭 버튼 */
div[data-testid="column"] .stButton button { border-radius:10px !important; font-weight:700 !important; font-size:13px !important; }
/* 선택된 카드 강조 */
.lc.active { border-color:rgb(var(--mr)); border-width:2px; background:rgba(var(--mr),0.02); }
/* 컴팩트 시상 라인 */
.prize-line { display:flex; align-items:center; gap:6px; padding:7px 10px; background:var(--card); border:1px solid var(--border); border-radius:10px; margin-bottom:4px; flex-wrap:wrap; }
.prize-line.achieved { border-left:3px solid var(--green); }
.prize-line.partial { border-left:3px solid #ff9500; }
.prize-line.none { border-left:3px solid #e5e8eb; }
.pl-name { font-size:13px; font-weight:700; color:var(--text1); min-width:90px; }
.pl-chip { font-size:12px; padding:2px 8px; border-radius:6px; font-weight:600; white-space:nowrap; }
.pl-chip.perf { background:#f0f1f3; color:var(--text1); }
.pl-chip.target { background:#fff3e0; color:#e65100; }
.pl-chip.short { background:#fce4ec; color:#c62828; }
.pl-chip.ok { background:#e8f5e9; color:#2e7d32; }
.pl-chip.prize { background:#fff8e1; color:#f57f17; }
/* 컴팩트 실적 */
.perf-inline { display:flex; flex-wrap:wrap; gap:4px; margin:4px 0; }
.perf-tag { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:3px 8px; font-size:12px; }
.perf-tag .pk { color:var(--text3); margin-right:3px; font-size:11px; }
.perf-tag .pv { font-weight:700; color:var(--text1); }
/* 카드뉴스 — 2색 단순 */
.card-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin:8px 0; }
.data-card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px 12px 12px; text-align:center; }
.data-card .dc-label { font-size:11px; color:var(--text3); font-weight:700; margin-bottom:4px; letter-spacing:-0.3px; }
.data-card .dc-value { font-size:26px; font-weight:900; color:var(--text1); line-height:1.1; letter-spacing:-1px; }
.data-card.accent { border-color:rgba(var(--mr),0.2); }
.data-card.accent .dc-value { color:rgb(var(--mr)); }
/* 모니터링 4칼럼 그리드 */
.stat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:12px 0; }
.stat-card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px 14px; transition:all .15s; position:relative; overflow:hidden; }
.stat-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; border-radius:14px 14px 0 0; }
.stat-card:hover { border-color:rgba(var(--mr),0.3); box-shadow:0 4px 12px rgba(0,0,0,0.08); transform:translateY(-1px); }
.stat-card .sc-name { font-size:13px; font-weight:700; color:var(--text1); margin-bottom:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.stat-card .sc-rate { font-size:32px; font-weight:900; line-height:1; margin-bottom:6px; letter-spacing:-1.5px; }
.stat-card .sc-detail { font-size:11px; color:var(--text3); font-weight:500; }
@media(max-width:768px) {
    .card-grid { grid-template-columns:repeat(2,1fr); gap:6px; }
    .data-card .dc-value { font-size:20px; }
    .stat-grid { grid-template-columns:repeat(2,1fr); gap:8px; }
    .stat-card .sc-rate { font-size:26px; }
}
@media(max-width:480px) {
    .data-card .dc-value { font-size:18px; }
    .stat-grid { grid-template-columns:repeat(2,1fr); }
    .stat-card .sc-rate { font-size:22px; }
}
/* 파일 카드 */
.file-card { background:var(--card); border-radius:12px; padding:14px; border:1px solid var(--border); margin-bottom:6px; }
.file-card.loaded { border-color:rgba(0,196,113,0.3); background:rgba(0,196,113,0.02); }
/* 모니터링 */
.mon-row { display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
.mon-card { flex:1; min-width:130px; background:var(--card); border:1px solid var(--border); border-radius:14px; padding:18px 14px; text-align:center; }
.mon-card .mc-label { font-size:12px; color:var(--text3); font-weight:600; }
.mon-card .mc-num { font-size:28px; font-weight:800; color:var(--text1); margin:4px 0 2px; }
.mon-card .mc-sub { font-size:11px; color:var(--text3); }
.mon-card.red .mc-num { color:var(--red); }
/* iframe */
iframe { width:100% !important; }
/* 반응형 */
@media (max-width:768px) {
    .block-container { padding:.4rem .5rem !important; }
    .hero-card { padding:16px 16px 14px; } .hero-name { font-size:20px !important; }
    .metric-card .mc-val { font-size:16px; } .metric-card { padding:8px 6px; }
    .pl-name { min-width:80px; font-size:11px; } .pl-chip { font-size:10px; }
}
@media (max-width:480px) {
    .hero-card { padding:14px 12px; border-radius:12px; } .hero-name { font-size:18px !important; }
    button[data-baseweb="tab"] { font-size:12px !important; }
}
</style>
""", unsafe_allow_html=True)

# =============================================================
# 1. 유틸
# =============================================================
def clean_key(val):
    if pd.isna(val) or str(val).strip().lower()=='nan': return ""
    s = str(val).strip().replace(" ","").upper()
    return s[:-2] if s.endswith('.0') else s

def decode_excel_text(val):
    if pd.isna(val): return val
    s = str(val)
    return re.sub(r'_x([0-9a-fA-F]{4})_', lambda m: chr(int(m.group(1),16)), s) if '_x' in s else s

@st.cache_data(show_spinner=False)
def load_file_data(fb, fn):
    df = pd.read_csv(io.BytesIO(fb),encoding='utf-8',errors='replace') if fn.endswith('.csv') else pd.read_excel(io.BytesIO(fb))
    for c in df.columns:
        if df[c].dtype==object: df[c]=df[c].apply(decode_excel_text)
        if any(k in c for k in ["코드","번호","ID","id"]):
            if df[c].dtype in ['float64','float32']: df[c]=df[c].apply(lambda x: str(int(x)) if pd.notna(x) else "")
            elif df[c].dtype in ['int64','int32']: df[c]=df[c].astype(str)
    return df

def safe_str(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return ""
    s=str(v).strip(); return "" if s.lower() in ('nan','none','nat') else s

def fmt_num(v):
    s=safe_str(v)
    if not s: return ""
    try:
        n=float(s.replace(',',''))
        if n==0: return ""
        return f"{int(n):,}" if n==int(n) else f"{n:,.1f}"
    except: return "" if s in ("0","0.0") else s

def natural_sort_key(s):
    """자연 정렬: GA3-1, GA3-2, ... GA3-10, GA3-11"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(s))]

def hq_sort_key(name):
    """본부 정렬: GA숫자 먼저(번호순), 그 다음 한글(가나다순)"""
    m = re.match(r'GA(\d+)', str(name))
    if m: return (0, int(m.group(1)), str(name))
    return (1, 0, str(name))

def sanitize_dataframe(df):
    if df is None or df.empty: return df
    for c in df.columns:
        if c.startswith('_'): continue
        if df[c].dtype==object: df[c]=df[c].fillna(""); df[c]=df[c].apply(lambda x: "" if str(x).strip().lower() in ('nan','none','nat') else x)
        elif df[c].dtype in ['float64','float32']:
            if any(k in c for k in ['명','코드','번호','ID','id','구분','여부','상태','조직']): df[c]=df[c].apply(lambda x: "" if pd.isna(x) else str(int(x)) if isinstance(x,float) and x==int(x) else str(x))
            else: df[c]=df[c].fillna(0)
        elif df[c].isna().any(): df[c]=df[c].fillna("")
    return df

def resolve_val(row,ca,cb):
    for c in [ca,cb]:
        if c and c in row:
            v=safe_str(row[c])
            if v: return v
        if c:
            for sfx in ['_파일1','_파일2']:
                if c+sfx in row:
                    v=safe_str(row[c+sfx])
                    if v: return v
    return ""

def get_row_num(row,cn):
    if not cn: return 0
    for c in [cn]+[cn+s for s in ['_파일1','_파일2']]:
        if c in row:
            v=safe_str(row[c])
            if v:
                try: return float(v.replace(',',''))
                except: pass
    return 0

# =============================================================
# 2. 저장
# =============================================================
def _reset():
    st.session_state['df_merged']=pd.DataFrame()
    for k in ['file_a_name','file_b_name','join_col_a','join_col_b','manager_col','manager_col2','manager_name_col',
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b','cust_branch_col_a','cust_branch_col_b']:
        st.session_state[k]=""
    st.session_state['display_cols']=[]; st.session_state['prize_config']=[]

def load_cfg():
    cfg=None
    for fp in [CONFIG_FILE,CONFIG_FILE+".bak"]:
        if not os.path.exists(fp): continue
        try:
            with open(fp,'rb') as f: d=pickle.load(f)
            if isinstance(d,dict): cfg=d; break
        except: continue
    if cfg is None: cfg={}
    for k in ['file_a_name','file_b_name','join_col_a','join_col_b','manager_col','manager_col2','manager_name_col',
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b','cust_branch_col_a','cust_branch_col_b']:
        st.session_state[k]=str(cfg.get(k,""))
    st.session_state['display_cols']=cfg.get('display_cols',[]) if isinstance(cfg.get('display_cols'),list) else []
    st.session_state['display_labels']=cfg.get('display_labels',{}) if isinstance(cfg.get('display_labels'),dict) else {}
    st.session_state['prize_config']=cfg.get('prize_config',[]) if isinstance(cfg.get('prize_config'),list) else []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,'rb') as f: data=pickle.load(f)
            df=data.get('df_merged',pd.DataFrame()) if isinstance(data,dict) else pd.DataFrame()
            if isinstance(df,pd.DataFrame) and not df.empty: df=sanitize_dataframe(df)
            st.session_state['df_merged']=df if isinstance(df,pd.DataFrame) else pd.DataFrame()
        except: st.session_state['df_merged']=pd.DataFrame()

def save_cfg():
    cfg={}
    for k in ['file_a_name','file_b_name','join_col_a','join_col_b','manager_col','manager_col2','manager_name_col',
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b','cust_branch_col_a','cust_branch_col_b','display_cols','display_labels','prize_config']:
        cfg[k]=st.session_state.get(k,"")
    try:
        if os.path.exists(CONFIG_FILE): shutil.copy2(CONFIG_FILE,CONFIG_FILE+".bak")
        tmp=CONFIG_FILE+".tmp"
        with open(tmp,'wb') as f: pickle.dump(cfg,f)
        shutil.move(tmp,CONFIG_FILE)
    except: pass

def save_data():
    try:
        tmp=DATA_FILE+".tmp"
        with open(tmp,'wb') as f: pickle.dump({'df_merged':st.session_state.get('df_merged',pd.DataFrame())},f)
        shutil.move(tmp,DATA_FILE)
    except: pass

def has_data():
    df=st.session_state.get('df_merged'); return isinstance(df,pd.DataFrame) and not df.empty

USER_PREFS_FILE = "user_prefs.pkl"
def load_user_prefs(mgr_code=''):
    if os.path.exists(USER_PREFS_FILE):
        try:
            with open(USER_PREFS_FILE,'rb') as f: ap=pickle.load(f)
            if isinstance(ap,dict) and mgr_code and mgr_code in ap and isinstance(ap[mgr_code],dict): return ap[mgr_code]
            if isinstance(ap,dict) and ('greeting' in ap or 'leaflet' in ap): return ap
            return {}
        except: pass
    return {}
def save_user_prefs(prefs, mgr_code=''):
    try:
        ap={}
        if os.path.exists(USER_PREFS_FILE):
            with open(USER_PREFS_FILE,'rb') as f: ap=pickle.load(f)
            if not isinstance(ap,dict): ap={}
            if 'greeting' in ap and mgr_code:
                old=dict(ap); ap={}; ap[mgr_code]=old
        if mgr_code: ap[mgr_code]=prefs
        with open(USER_PREFS_FILE,'wb') as f: pickle.dump(ap,f)
    except: pass

# =============================================================
# 3. SQLite
# =============================================================
def get_db():
    conn=sqlite3.connect(LOG_DB,check_same_thread=False); conn.row_factory=sqlite3.Row; return conn

def init_db():
    conn=get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS message_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,manager_code TEXT NOT NULL,manager_name TEXT,customer_number TEXT NOT NULL,customer_name TEXT,message_type INTEGER NOT NULL,sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,month_key TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS login_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,manager_code TEXT NOT NULL,manager_name TEXT,login_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    for s in ["CREATE INDEX IF NOT EXISTS idx_mm ON message_logs(manager_code)","CREATE INDEX IF NOT EXISTS idx_mk ON message_logs(month_key)"]: conn.execute(s)
    conn.commit(); conn.close()

def daily_backup():
    os.makedirs(BACKUP_DIR,exist_ok=True); today=datetime.now().strftime("%Y%m%d")
    bak=os.path.join(BACKUP_DIR,f"log_{today}.db")
    if not os.path.exists(bak) and os.path.exists(LOG_DB):
        try: shutil.copy2(LOG_DB,bak)
        except: pass
    try:
        cutoff=(datetime.now()-timedelta(days=30)).strftime("%Y%m%d")
        for f in os.listdir(BACKUP_DIR):
            if f.startswith("log_") and f.endswith(".db") and f.replace("log_","").replace(".db","")<cutoff:
                os.remove(os.path.join(BACKUP_DIR,f))
    except: pass

def log_msg(mc,mn,cn,cna,mt):
    mk=datetime.now().strftime("%Y%m"); conn=get_db()
    conn.execute("INSERT INTO message_logs (manager_code,manager_name,customer_number,customer_name,message_type,month_key) VALUES (?,?,?,?,?,?)",(str(mc),mn,str(cn),cna,mt,mk)); conn.commit(); conn.close()

def get_cust_logs(mc,cn):
    mk=datetime.now().strftime("%Y%m"); conn=get_db()
    rows=conn.execute("SELECT message_type,sent_date FROM message_logs WHERE manager_code=? AND customer_number=? AND month_key=?",(str(mc),str(cn),mk)).fetchall(); conn.close()
    return [dict(r) for r in rows]

def get_mgr_summary(mc):
    mk=datetime.now().strftime("%Y%m"); conn=get_db()
    rows=conn.execute("SELECT message_type,COUNT(DISTINCT customer_number) as u,COUNT(*) as c FROM message_logs WHERE manager_code=? AND month_key=? GROUP BY message_type",(str(mc),mk)).fetchall(); conn.close()
    return {r['message_type']:{'customers':r['u'],'count':r['c']} for r in rows}

def log_login(mc,mn=""): conn=get_db(); conn.execute("INSERT INTO login_logs (manager_code,manager_name) VALUES (?,?)",(str(mc),mn)); conn.commit(); conn.close()

def get_available_months():
    conn=get_db(); rows=conn.execute("SELECT DISTINCT month_key FROM message_logs ORDER BY month_key DESC").fetchall(); conn.close()
    return [r['month_key'] for r in rows] if rows else [datetime.now().strftime("%Y%m")]

def get_msg_summary_by_month(mk):
    conn=get_db(); df=pd.read_sql("SELECT manager_code as 매니저코드,manager_name as 매니저명,message_type as 메시지유형,COUNT(DISTINCT customer_number) as 발송인원,COUNT(*) as 발송횟수 FROM message_logs WHERE month_key=? GROUP BY manager_code,manager_name,message_type",conn,params=[mk]); conn.close(); return df

def get_login_summary_by_month(mk):
    conn=get_db(); df=pd.read_sql("SELECT manager_code as 매니저코드,manager_name as 매니저명,COUNT(*) as 로그인횟수,MAX(login_date) as 최근로그인 FROM login_logs WHERE strftime('%Y%m',login_date)=? GROUP BY manager_code ORDER BY 로그인횟수 DESC",conn,params=[mk]); conn.close(); return df

def reset_month_logs(mk):
    conn=get_db(); conn.execute("DELETE FROM message_logs WHERE month_key=?",(mk,)); conn.execute(f"DELETE FROM login_logs WHERE strftime('%Y%m',login_date)='{mk}'"); conn.commit(); conn.close()

# =============================================================
# 4. 카카오톡 공유
# =============================================================
def render_kakao(text,label="📋 카톡 보내기",bid="kk",height=50):
    enc=base64.b64encode(text.encode('utf-8')).decode('ascii')
    html=f"""<style>.kb{{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,#FEE500,#F5D600);color:#3C1E1E;border:none;padding:10px 20px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;width:100%;justify-content:center;font-family:'Pretendard',sans-serif;}}.kb:active{{transform:scale(0.97);}}.kb.ok{{background:linear-gradient(135deg,#00c471,#00a85e);color:#fff;}}.ks{{font-size:11px;color:#888;margin-top:3px;text-align:center;}}</style><button class="kb" id="{bid}" onclick="ds_{bid}()"><svg viewBox="0 0 24 24" fill="#3C1E1E" width="18" height="18"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg>{label}</button><div class="ks" id="s_{bid}"></div><script>function ds_{bid}(){{var t=decodeURIComponent(escape(atob("{enc}")));if(/Mobi|Android|iPhone/i.test(navigator.userAgent)&&navigator.share){{navigator.share({{text:t}}).then(()=>dn_{bid}()).catch(()=>fc_{bid}(t));}}else{{fc_{bid}(t);}}}}function fc_{bid}(t){{var a=document.createElement('textarea');a.value=t;a.style.cssText='position:fixed;left:-9999px';document.body.appendChild(a);a.select();a.setSelectionRange(0,999999);var ok=false;try{{ok=document.execCommand('copy');}}catch(e){{}}document.body.removeChild(a);if(ok)dn_{bid}();else if(navigator.clipboard)navigator.clipboard.writeText(t).then(()=>dn_{bid}());}}function dn_{bid}(){{var b=document.getElementById('{bid}');b.classList.add('ok');b.innerHTML='✅ 복사 완료!';document.getElementById('s_{bid}').innerHTML='카카오톡에서 붙여넣기(Ctrl+V) 하세요';setTimeout(()=>{{b.classList.remove('ok');b.innerHTML='<svg viewBox="0 0 24 24" fill="#3C1E1E" width="18" height="18"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg> {label}';}},3000);}}</script>"""
    components.html(html,height=height)

def render_img_share(img_bytes,filename,bid,height=55):
    """이미지를 클립보드에 복사 (PC카톡 Ctrl+V 가능) / 모바일은 Web Share"""
    b64=base64.b64encode(img_bytes).decode('ascii')
    ext=filename.split('.')[-1].lower(); mime=f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
    html=f"""<style>.kb{{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,#FEE500,#F5D600);color:#3C1E1E;border:none;padding:10px 20px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;width:100%;justify-content:center;font-family:'Pretendard',sans-serif;}}.kb:active{{transform:scale(0.97);}}.kb.ok{{background:linear-gradient(135deg,#00c471,#00a85e);color:#fff;}}.ks{{font-size:11px;color:#888;margin-top:3px;text-align:center;}}</style>
    <button class="kb" id="{bid}" onclick="shareI_{bid}()">📷 리플렛 이미지 전송</button><div class="ks" id="s_{bid}"></div>
    <script>
    async function shareI_{bid}(){{
        var b64="{b64}"; var bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
        var blob=new Blob([bytes],{{type:"{mime}"}}); var file=new File([blob],"{filename}",{{type:"{mime}"}});
        var btn=document.getElementById("{bid}");
        // 모바일: Web Share API 파일 직접 공유
        if(/Mobi|Android|iPhone/i.test(navigator.userAgent) && navigator.canShare && navigator.canShare({{files:[file]}})){{
            try{{ await navigator.share({{files:[file]}}); ok_{bid}("✅ 전송 완료!","카카오톡에서 확인하세요"); return; }}catch(e){{}}
        }}
        // PC: 클립보드에 이미지 복사 → 카톡에서 Ctrl+V
        try{{
            var item=new ClipboardItem({{[blob.type]:blob}});
            await navigator.clipboard.write([item]);
            ok_{bid}("✅ 이미지 복사 완료!","카카오톡 채팅방에서 Ctrl+V 하세요");
        }}catch(e){{
            // fallback: 다운로드
            var url=URL.createObjectURL(blob); var a=document.createElement('a'); a.href=url; a.download="{filename}";
            document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
            ok_{bid}("✅ 다운로드 완료!","카카오톡에 파일을 드래그하세요");
        }}
    }}
    function ok_{bid}(t,sub){{
        var btn=document.getElementById("{bid}"); btn.classList.add('ok'); btn.innerHTML=t;
        document.getElementById("s_{bid}").innerHTML=sub;
        setTimeout(()=>{{btn.classList.remove('ok');btn.innerHTML='📷 리플렛 이미지 전송';}},4000);
    }}
    </script>"""
    components.html(html,height=height)

# =============================================================
# 5. 시상 엔진
# =============================================================
def calc_prize(row,cfgs):
    results=[]
    for p in cfgs:
        perf=get_row_num(row,p.get('col_val',''))
        tiers=sorted(p.get('tiers',[]),key=lambda x:x[0],reverse=True)
        existing=get_row_num(row,p.get('col_prize','')) if p.get('col_prize') else 0
        at=ap=0; nt=sf=0
        for th,pr in tiers:
            if perf>=th: at=th; ap=pr; break
            else: nt=th; sf=th-perf
        if at:
            found=False
            for th,pr in tiers:
                if th>at: nt=th; sf=th-perf; found=True; break
            if not found: nt=0; sf=0
        results.append({**p,'perf':perf,'achieved_tier':at,'achieved_prize':ap,'next_tier':nt,'shortfall':sf,'existing_prize':existing,'sorted_tiers':tiers})
    return results

def prize_line_html(p):
    """한 줄 컴팩트 시상 표시"""
    st_='achieved' if p['achieved_tier'] else ('partial' if p['perf']>0 else 'none')
    h=f"<div class='prize-line {st_}'>"
    h+=f"<span class='pl-name'>{p.get('name','')}</span>"
    h+=f"<span class='pl-chip perf'>실적 {fmt_num(p['perf']) or '0'}</span>"
    if p['existing_prize']>0:
        h+=f"<span class='pl-chip ok'>시상 {fmt_num(p['existing_prize'])}원</span>"
    if p['achieved_tier']:
        h+=f"<span class='pl-chip ok'>달성 {fmt_num(p['achieved_tier'])}</span>"
    if p['next_tier']:
        h+=f"<span class='pl-chip target'>목표 {fmt_num(p['next_tier'])}</span>"
        h+=f"<span class='pl-chip short'>부족 {fmt_num(p['shortfall'])}</span>"
    elif p['achieved_tier']:
        h+=f"<span class='pl-chip ok'>🎉 최고구간</span>"
    h+="</div>"; return h

# =============================================================
# 6. init
# =============================================================
if 'df_merged' not in st.session_state: _reset(); load_cfg()
init_db(); daily_backup()

# =============================================================
# 7. 사이드바
# =============================================================
st.sidebar.markdown("<div style='padding:6px 0 12px;'><span style='font-size:18px;font-weight:800;'>📋 활동관리</span></div>",unsafe_allow_html=True)
try: MGR_PW=os.environ.get("MANAGER_PASSWORD","") or st.secrets.get("MANAGER_PASSWORD","meritz1!")
except: MGR_PW=os.environ.get("MANAGER_PASSWORD","meritz1!")
try: ADM_PW=os.environ.get("ADMIN_PASSWORD","") or st.secrets.get("ADMIN_PASSWORD","wolf7998")
except: ADM_PW=os.environ.get("ADMIN_PASSWORD","wolf7998")
menu=st.sidebar.radio("메뉴",["📱 매니저 화면","⚙️ 관리자 설정","📊 활동 모니터링"])

# =============================================================
# 8. 관리자
# =============================================================
if menu=="⚙️ 관리자 설정":
    st.markdown("<h2 style='font-weight:800;'>⚙️ 관리자 설정</h2>",unsafe_allow_html=True)
    if not st.session_state.get('admin_auth'):
        with st.form("adm"):
            pw=st.text_input("🔒 비밀번호",type="password")
            if st.form_submit_button("로그인",use_container_width=True):
                if pw==ADM_PW: st.session_state['admin_auth']=True; st.rerun()
                else: st.error("❌")
        st.stop()
    st.markdown("### 📂 데이터 파일")
    if has_data(): st.success(f"✅ **{len(st.session_state['df_merged']):,}행** 운영 중")
    ca,cb=st.columns(2)
    with ca:
        st.markdown("**파일 A**")
        if 'df_file_a' in st.session_state and st.session_state['df_file_a'] is not None:
            fa=st.session_state['df_file_a']; st.markdown(f"<div class='file-card loaded'>✅ <b>{st.session_state.get('file_a_name','')}</b><br><span style='color:#6b7684;font-size:12px;'>{len(fa):,}행 × {len(fa.columns)}열</span></div>",unsafe_allow_html=True)
            if st.button("🗑️",key="da"): del st.session_state['df_file_a']; st.session_state['file_a_name']=""; st.rerun()
        else:
            f=st.file_uploader("업로드",type=['csv','xlsx'],key="ua",label_visibility="collapsed")
            if f: st.session_state['df_file_a']=load_file_data(f.getvalue(),f.name); st.session_state['file_a_name']=f.name; st.rerun()
    with cb:
        st.markdown("**파일 B**")
        if 'df_file_b' in st.session_state and st.session_state['df_file_b'] is not None:
            fb=st.session_state['df_file_b']; st.markdown(f"<div class='file-card loaded'>✅ <b>{st.session_state.get('file_b_name','')}</b><br><span style='color:#6b7684;font-size:12px;'>{len(fb):,}행 × {len(fb.columns)}열</span></div>",unsafe_allow_html=True)
            if st.button("🗑️",key="db"): del st.session_state['df_file_b']; st.session_state['file_b_name']=""; st.rerun()
        else:
            f=st.file_uploader("업로드",type=['csv','xlsx'],key="ub",label_visibility="collapsed")
            if f: st.session_state['df_file_b']=load_file_data(f.getvalue(),f.name); st.session_state['file_b_name']=f.name; st.rerun()
    fa_ok='df_file_a' in st.session_state and st.session_state.get('df_file_a') is not None
    fb_ok='df_file_b' in st.session_state and st.session_state.get('df_file_b') is not None
    if fa_ok and fb_ok:
        st.markdown("---"); st.markdown("### 🔗 병합")
        ca2=st.session_state['df_file_a'].columns.tolist(); cb2=st.session_state['df_file_b'].columns.tolist()
        pja=st.session_state.get('join_col_a',''); pjb=st.session_state.get('join_col_b','')
        ia=ca2.index(pja) if pja in ca2 else (ca2.index('본인고객번호') if '본인고객번호' in ca2 else 0)
        ib=cb2.index(pjb) if pjb in cb2 else (cb2.index('본인고객번호') if '본인고객번호' in cb2 else 0)
        j1,j2=st.columns(2)
        with j1: ja=st.selectbox("파일A 조인키",ca2,index=ia,key="sja")
        with j2: jb=st.selectbox("파일B 조인키",cb2,index=ib,key="sjb")
        if st.button("🔗 병합",type="primary",use_container_width=True):
            with st.spinner("병합..."):
                da=st.session_state['df_file_a'].copy(); db=st.session_state['df_file_b'].copy()
                da['_mk_a']=da[ja].apply(clean_key); db['_mk_b']=db[jb].apply(clean_key)
                m=pd.merge(da,db,left_on='_mk_a',right_on='_mk_b',how='outer',suffixes=('_파일1','_파일2'))
                for c1 in [c for c in m.columns if c.endswith('_파일1')]:
                    base=c1.replace('_파일1',''); c2c=base+'_파일2'
                    if c2c in m.columns: m[base]=m[c1].combine_first(m[c2c]); m.drop(columns=[c1,c2c],inplace=True)
                m['_search_key']=m['_mk_a'].combine_first(m['_mk_b']); m=sanitize_dataframe(m)
                st.session_state['df_merged']=m; st.session_state['join_col_a']=ja; st.session_state['join_col_b']=jb
                save_data(); save_cfg(); st.success(f"✅ {len(m):,}행"); st.rerun()
    if has_data():
        df=st.session_state['df_merged']; av=[c for c in df.columns if not c.startswith('_')]
        with st.expander(f"📋 미리보기 ({len(df):,}행)",expanded=False): st.dataframe(df[av].head(30).fillna(""),use_container_width=True,height=200)
        st.markdown("---"); st.markdown("### 🏷️ 열 매핑")
        opts=["(없음)"]+av
        def si(k,cands,ol):
            p=st.session_state.get(k,'')
            if p in ol: return ol.index(p)
            for c in cands:
                if c in ol: return ol.index(c)
            return 0
        st.markdown("**🔑 매니저**")
        m1,m2=st.columns(2)
        with m1: mc1=st.selectbox("코드(A)",av,index=si('manager_col',['매니저코드'],av),key="cm1")
        with m2: mc2=st.selectbox("코드(B)",opts,index=si('manager_col2',['지원매니저코드'],opts),key="cm2")
        mn_col=st.selectbox("이름",av,index=si('manager_name_col',['매니저명','지원매니저명'],av),key="cmn")
        st.markdown("**👤 사용인**")
        n1,n2=st.columns(2)
        with n1: cna=st.selectbox("이름(A)",opts,index=si('cust_name_col_a',['현재대리점설계사조직명'],opts),key="cna")
        with n2: cnb=st.selectbox("이름(B)",opts,index=si('cust_name_col_b',['대리점설계사명'],opts),key="cnb")
        c1c,c2c=st.columns(2)
        with c1c: cca=st.selectbox("코드(A)",opts,index=si('cust_code_col_a',['현재대리점설계사조직코드'],opts),key="cca")
        with c2c: ccb=st.selectbox("코드(B)",opts,index=si('cust_code_col_b',['대리점설계사조직코드'],opts),key="ccb")
        b1c,b2c=st.columns(2)
        with b1c: cba=st.selectbox("지사(A)",opts,index=si('cust_branch_col_a',['현재대리점지사명'],opts),key="cba")
        with b2c: cbb=st.selectbox("지사(B)",opts,index=si('cust_branch_col_b',['대리점지사명'],opts),key="cbb")
        st.markdown("---"); st.markdown("### 📋 실적 표시")
        prev=st.session_state.get('display_cols',[]); dc=st.multiselect("항목",av,default=[c for c in prev if c in av],key="cdc")
        # 별도 명칭 부여
        prev_labels=st.session_state.get('display_labels',{})
        dc_labels={}
        if dc:
            st.markdown("**표시 명칭** (비워두면 원래 열 이름 사용)")
            for ci,col in enumerate(dc):
                default_lbl=prev_labels.get(col,'')
                lbl=st.text_input(f"'{col}' 표시명",value=default_lbl,placeholder=col,key=f"dlbl_{ci}")
                dc_labels[col]=lbl.strip() if lbl.strip() else col
        st.markdown("---"); st.markdown("### 🏆 시상 JSON")
        pc=st.session_state.get('prize_config',[])
        if pc: st.success(f"✅ {len(pc)}개 시책")
        if st.button("🗑️ 시책 삭제",key="dpc") and pc: st.session_state['prize_config']=[]; save_cfg(); st.rerun()
        jf=st.file_uploader("JSON",type=["json"],key="uj")
        if jf:
            try:
                jd=json.load(jf)
                if isinstance(jd,list): st.session_state['prize_config']=jd; save_cfg(); st.success(f"✅ {len(jd)}개"); st.rerun()
            except: st.error("JSON 오류")
        st.markdown("---")
        if st.button("💾 설정 저장",type="primary",use_container_width=True):
            st.session_state['manager_col']=mc1; st.session_state['manager_col2']=mc2 if mc2!="(없음)" else ""
            st.session_state['manager_name_col']=mn_col
            for k,v in [('cust_name_col_a',cna),('cust_name_col_b',cnb),('cust_code_col_a',cca),('cust_code_col_b',ccb),('cust_branch_col_a',cba),('cust_branch_col_b',cbb)]:
                st.session_state[k]=v if v!="(없음)" else ""
            st.session_state['display_cols']=dc; st.session_state['display_labels']=dc_labels; save_cfg(); st.success("✅"); st.rerun()

# =============================================================
# 9. 매니저
# =============================================================
elif menu=="📱 매니저 화면":
    st.session_state['admin_auth']=False
    if not has_data() or not st.session_state.get('manager_col'):
        st.markdown("<div class='hero-card'><h1 class='hero-name'>매니저 활동관리</h1><p class='hero-sub'>관리자 설정 미완료</p></div>",unsafe_allow_html=True); st.stop()
    df=st.session_state['df_merged'].copy()
    mc1=st.session_state['manager_col']; mc2=st.session_state.get('manager_col2','')
    mn_col=st.session_state.get('manager_name_col',mc1)
    _cna=st.session_state.get('cust_name_col_a',''); _cnb=st.session_state.get('cust_name_col_b','')
    _cca=st.session_state.get('cust_code_col_a',''); _ccb=st.session_state.get('cust_code_col_b','')
    _cba=st.session_state.get('cust_branch_col_a',''); _cbb=st.session_state.get('cust_branch_col_b','')
    dcfg=st.session_state.get('display_cols',[]); pcfg=st.session_state.get('prize_config',[]); dlbl=st.session_state.get('display_labels',{})

    # ── 매니저 로그인 ──
    def _exec_login(code,pw):
        if pw!=MGR_PW: return "❌ 비밀번호 오류"
        if not code: return "코드를 입력하세요"
        _df=st.session_state['df_merged'].copy()
        _mc1=st.session_state['manager_col']; _mc2=st.session_state.get('manager_col2','')
        _mn_col=st.session_state.get('manager_name_col',_mc1)
        cc=clean_key(code); _df['_s1']=_df[_mc1].apply(clean_key); mask=_df['_s1']==cc
        if _mc2 and _mc2 in _df.columns: _df['_s2']=_df[_mc2].apply(clean_key); mask=mask|(_df['_s2']==cc)
        found=_df[mask]
        if found.empty: return f"❌ '{code}' 없음"
        mn="매니저"
        if _mn_col in found.columns:
            ns=found[_mn_col].dropna(); ns=ns[ns.astype(str).str.strip()!='']
            if not ns.empty:
                n=safe_str(ns.iloc[0])
                if n: mn=n
        st.session_state['mgr_in']=True; st.session_state['mgr_code']=cc; st.session_state['mgr_name']=mn
        st.session_state['sel_cust']=None; log_login(cc,mn)
        return ""

    # 자동 로그인: 이전 rerun에서 저장된 입력값이 있으면 즉시 시도
    if not st.session_state.get('mgr_in'):
        ac=st.session_state.get('_mlc',''); ap=st.session_state.get('_mlp','')
        if ac and ap:
            err=_exec_login(ac,ap)
            if not err:
                st.session_state.pop('_mlp',None)
            else:
                st.session_state['_mle']=err

    if not st.session_state.get('mgr_in'):
        st.markdown("<div class='hero-card'><h1 class='hero-name'>매니저 로그인</h1><p class='hero-sub'>코드와 비밀번호를 입력하세요</p></div>",unsafe_allow_html=True)
        st.text_input("매니저 코드",placeholder="코드",key="_mlc")
        st.text_input("비밀번호",type="password",key="_mlp")
        if st.button("로그인",type="primary",use_container_width=True):
            ci=st.session_state.get('_mlc',''); pi=st.session_state.get('_mlp','')
            if ci and pi:
                err=_exec_login(ci,pi)
                if err: st.error(err)
                else: st.session_state.pop('_mlp',None); st.rerun()
        err=st.session_state.get('_mle','')
        if err: st.error(err); st.session_state.pop('_mle',None)
        st.stop()

    mgr_c=st.session_state['mgr_code']; mgr_n=st.session_state['mgr_name']
    df['_s1']=df[mc1].apply(clean_key); mask=df['_s1']==mgr_c
    if mc2 and mc2 in df.columns: df['_s2']=df[mc2].apply(clean_key); mask=mask|(df['_s2']==mgr_c)
    my=df[mask].copy().reset_index(drop=True)
    # 정렬: 지사→이름
    sc=[]
    for _,r in my.iterrows():
        sc.append((resolve_val(r,_cba,_cbb) or resolve_val(r,'현재대리점지사명','대리점지사명'), resolve_val(r,_cna,_cnb) or resolve_val(r,'현재대리점설계사조직명','대리점설계사명')))
    my['_sb']=[s[0] for s in sc]; my['_sn']=[s[1] for s in sc]; my=my.sort_values(['_sb','_sn']).reset_index(drop=True)

    # 히어로
    hc1,hc2=st.columns([5,1])
    with hc1: st.markdown(f"<div class='hero-card'><h1 class='hero-name'>{mgr_n} 매니저님</h1><p class='hero-sub'>사용인 {len(my)}명 · {datetime.now().strftime('%Y년 %m월')}</p></div>",unsafe_allow_html=True)
    with hc2: st.write(""); st.write("")
    if hc2.button("🚪"): st.session_state['mgr_in']=False; st.session_state['sel_cust']=None; st.rerun()
    # 메트릭
    smry=get_mgr_summary(mgr_c); ml={1:"①인사",2:"②인사+리플렛",3:"③실적 및 시상"}
    mh="<div class='metric-row'>"
    for mt,lb in ml.items():
        inf=smry.get(mt,{'customers':0,'count':0}); ac=" active" if inf['customers']>0 else ""
        mh+=f"<div class='metric-card{ac}'><div class='mc-label'>{lb}</div><div class='mc-val'>{inf['customers']}</div><div class='mc-sub'>{inf['count']}건</div></div>"
    mh+="</div>"; st.markdown(mh,unsafe_allow_html=True)

    # ── 카드 HTML 생성 함수 ──
    dot_labels={1:"인사",2:"인사+리플렛",3:"실적/시상"}
    def render_card_html(row,idx):
        co=resolve_val(row,_cba,_cbb) or resolve_val(row,'현재대리점지사명','대리점지사명')
        cn=resolve_val(row,_cna,_cnb) or resolve_val(row,'현재대리점설계사조직명','대리점설계사명') or safe_str(row.get('본인고객번호',''))
        cc_=resolve_val(row,_cca,_ccb) or resolve_val(row,'현재대리점설계사조직코드','대리점설계사조직코드')
        cnum=safe_str(row.get('본인고객번호','')) or safe_str(row.get('_search_key',''))
        logs=get_cust_logs(mgr_c,cnum) if cnum else []; stypes=set(l['message_type'] for l in logs)
        pills_h=""
        if dcfg:
            rd=row.to_dict()
            for ci,col in enumerate(dcfg):
                val=rd.get(col)
                if val is None:
                    for sfx in ['_파일1','_파일2']:
                        if col+sfx in rd: val=rd[col+sfx]; break
                dv=safe_str(val)
                if not dv or dv in ('0','0.0'): continue
                if isinstance(val,(int,float,np.integer,np.floating)) and not pd.isna(val): dv=fmt_num(val)
                if dv:
                    pcls='r' if ci%2==0 else 'g'; lbl=dlbl.get(col,col)
                    pills_h+=f"<span class='lc-pill {pcls}'><span class='pl-lbl'>{lbl}</span><span class='pl-val'>{dv}</span></span>"
        dots_h=""
        for mt_id,mt_lbl in dot_labels.items():
            dc='done' if mt_id in stypes else ''
            dots_h+=f"<span class='lc-dot {dc}'><span class='dot'></span>{mt_lbl}</span>"
        is_sel=st.session_state.get('sel_cust') and st.session_state['sel_cust'].get('idx')==idx
        act_cls=' active' if is_sel else ''
        org_h=f"<div class='lc-org'>{co}</div>" if co else ""
        card_h=f"<div class='lc{act_cls}'><div class='lc-top'><div class='lc-info'>{org_h}<div class='lc-name'>{cn}</div></div><div class='lc-perfs'>{pills_h}</div></div><div class='lc-bottom'>{dots_h}</div></div>"
        return co,cn,cc_,cnum,is_sel,card_h

    # ── 활동 패널 렌더링 함수 ──
    def render_detail(cn_s,cnum_s,co_s,cc_s,crow,kp=""):
        logs_s=get_cust_logs(mgr_c,cnum_s); stypes_s=set(l['message_type'] for l in logs_s)
        # 탭 선택
        tab_key=f"_tab_{kp}{cnum_s}"
        if tab_key not in st.session_state: st.session_state[tab_key]=1
        tab_n={1:"💬 인사말",2:"📎 인사+리플렛",3:"📊 실적·시상"}
        tc1,tc2,tc3=st.columns(3)
        for col_w,tid in [(tc1,1),(tc2,2),(tc3,3)]:
            with col_w:
                is_act=st.session_state[tab_key]==tid
                is_done=tid in stypes_s
                lbl=tab_n[tid]+(" ✅" if is_done else "")
                if st.button(lbl,key=f"tb_{kp}{cnum_s}_{tid}",use_container_width=True,type="primary" if is_act else "secondary"):
                    if not is_act: st.session_state[tab_key]=tid; st.rerun()
        cur_tab=st.session_state[tab_key]
        if cur_tab==1:
            prefs=load_user_prefs(mgr_c); saved_gr=prefs.get('greeting','')
            gr=st.text_area("인사말",value=saved_gr,placeholder="안녕하세요! 이번 달도 화이팅입니다!",key=f"g_{kp}{cnum_s}",height=60)
            if st.button("💬 저장 & 생성",key=f"gb_{kp}{cnum_s}",use_container_width=True):
                if gr: prefs['greeting']=gr; save_user_prefs(prefs,mgr_c); st.session_state[f'msg1_{kp}{cnum_s}']=f"안녕하세요, {cn_s}팀장님!\n{mgr_n} 매니저입니다.\n\n{gr}"
                else: st.warning("입력하세요")
            sm=st.session_state.get(f'msg1_{kp}{cnum_s}','')
            if not sm and saved_gr: sm=f"안녕하세요, {cn_s}팀장님!\n{mgr_n} 매니저입니다.\n\n{saved_gr}"; st.session_state[f'msg1_{kp}{cnum_s}']=sm
            if sm:
                st.text_area("미리보기",sm,height=80,disabled=True,key=f"p1_{kp}{cnum_s}")
                render_kakao(sm,"📋 카톡 보내기",f"k1_{kp}{cnum_s}",45)
                if st.button("✅ 발송 기록",key=f"l1_{kp}{cnum_s}",type="primary"): log_msg(mgr_c,mgr_n,cnum_s,cn_s,1); st.success("✅"); st.rerun()
        elif cur_tab==2:
            prefs=load_user_prefs(mgr_c); saved_gr=prefs.get('greeting','')
            st.markdown("<p style='font-size:13px;color:var(--text2);margin-bottom:4px;'>💡 인사말 카톡 → 리플렛 이미지 순서로 보내세요</p>",unsafe_allow_html=True)
            lf=st.file_uploader("리플렛 이미지 (한번 저장하면 유지)",type=["png","jpg","jpeg"],key=f"lf_{kp}{cnum_s}")
            if lf: prefs['leaflet']=lf.getvalue(); prefs['leaflet_name']=lf.name; save_user_prefs(prefs,mgr_c)
            lb=prefs.get('leaflet'); ln=prefs.get('leaflet_name','')
            st.markdown("<p style='font-size:14px;font-weight:700;margin:8px 0 4px;'>📝 STEP 1. 인사말 보내기</p>",unsafe_allow_html=True)
            sm2=''
            if saved_gr: sm2=f"안녕하세요, {cn_s}팀장님!\n{mgr_n} 매니저입니다.\n\n{saved_gr}"
            if sm2: st.text_area("인사말",sm2,height=60,disabled=True,key=f"p2t_{kp}{cnum_s}"); render_kakao(sm2,"📋 인사말 카톡",f"k2t_{kp}{cnum_s}",45)
            else: st.caption("①인사말 탭에서 인사말을 먼저 저장하세요")
            st.markdown("<p style='font-size:14px;font-weight:700;margin:8px 0 4px;'>🖼️ STEP 2. 리플렛 보내기</p>",unsafe_allow_html=True)
            if lb: st.image(lb,caption=ln,use_container_width=True); render_img_share(lb,ln,f"is_{kp}{cnum_s}",50)
            else: st.caption("📷 위에서 리플렛 이미지를 업로드하세요")
            if sm2 or lb:
                if st.button("✅ 발송 기록",key=f"l2_{kp}{cnum_s}",type="primary"): log_msg(mgr_c,mgr_n,cnum_s,cn_s,2); st.success("✅"); st.rerun()
        elif cur_tab==3:
            lines=["📋 메리츠 시상 현황 안내",f"📅 {datetime.now().strftime('%Y.%m.%d')} 기준",""]
            if dcfg:
                lines.append("━━ 실적 ━━")
                for col in dcfg:
                    val=crow.get(col)
                    if val is None:
                        for sfx in ['_파일1','_파일2']:
                            if col+sfx in crow: val=crow[col+sfx]; break
                    dv=safe_str(val)
                    if dv and dv not in ('0','0.0'):
                        if isinstance(val,(int,float)) and not pd.isna(val): dv=fmt_num(val)
                        if dv:
                            lbl_t=dlbl.get(col,col)
                            pfx="  🔴 " if '부족' in col or '부족' in lbl_t else ("  🎯 " if '목표' in col or '목표' in lbl_t else "  ")
                            lines.append(f"{pfx}{lbl_t}: {dv}")
                lines.append("")
            if pcfg:
                prs=calc_prize(crow,pcfg); weekly=[p for p in prs if p.get('category')=='weekly']; cumul=[p for p in prs if p.get('category')=='cumulative']
                if weekly:
                    lines.append("━━ 시책 ━━")
                    for pr in weekly:
                        s="✅" if pr['achieved_tier'] else "⬜"
                        lines.append(f"  {s} {pr['name']}: {fmt_num(pr['perf'])}")
                        if pr['shortfall']>0: lines.append(f"     🔴 목표 {fmt_num(pr['next_tier'])} 부족 {fmt_num(pr['shortfall'])}")
                    lines.append("")
                if cumul:
                    lines.append("━━ 누계 ━━")
                    for pr in cumul:
                        if pr['existing_prize']>0: lines.append(f"  {pr['name']}: {fmt_num(pr['existing_prize'])}원")
                    lines.append("")
                tp=sum(p['existing_prize'] for p in cumul if p['existing_prize']>0)
                if tp>0: lines.append(f"💰 시상금: {fmt_num(tp)}원"); lines.append("")
            lines+=["부족한 거 챙겨서 꼭 시상 많이 받으세요!","좋은 하루 되세요! 😊"]
            if len(lines)>5:
                msg="\n".join(lines)
                st.text_area("미리보기",msg,height=200,disabled=True,key=f"p3_{kp}{cnum_s}")
                render_kakao(msg,"📋 실적 및 시상 카톡",f"k3_{kp}{cnum_s}",45)
                if st.button("✅ 발송 기록",key=f"l3_{kp}{cnum_s}",type="primary"): log_msg(mgr_c,mgr_n,cnum_s,cn_s,3); st.success("✅"); st.rerun()
            else: st.info("실적/시상 데이터가 없습니다")

    # ── 뷰 모드 (수동 전환) ──
    if 'view_mode' not in st.session_state: st.session_state['view_mode']='desktop'

    vc1,vc2=st.columns([9,1])
    with vc2:
        cur_icon="📱" if st.session_state['view_mode']=='mobile' else "🖥️"
        if st.button(cur_icon,key="vm_toggle"):
            nxt='desktop' if st.session_state['view_mode']=='mobile' else 'mobile'
            st.session_state['view_mode']=nxt; st.session_state['sel_cust']=None; st.rerun()

    srch=st.text_input("🔍",placeholder="이름/소속 검색",key="cs",label_visibility="collapsed")
    fdf=my.copy()
    if srch: fdf=fdf[fdf.apply(lambda r: srch.lower() in str(r.values).lower(),axis=1)]

    if st.session_state['view_mode']=='mobile':
        # ═══ 모바일: 아코디언 ═══
        for idx,row in fdf.iterrows():
            co,cn,cc_,cnum,is_sel,card_h=render_card_html(row,idx)
            st.markdown(card_h,unsafe_allow_html=True)
            btn_label="▼ 접기" if is_sel else "Touch"
            if st.button(btn_label,key=f"c_{idx}",use_container_width=True):
                cr={k:(safe_str(v) if not isinstance(v,(int,float,np.integer,np.floating)) or pd.isna(v) else v) for k,v in row.to_dict().items()}
                if is_sel: st.session_state['sel_cust']=None
                else: st.session_state['sel_cust']={'idx':idx,'name':cn,'org':co,'code':cc_,'num':cnum,'row':cr}
                st.rerun()
            if is_sel:
                sel=st.session_state['sel_cust']
                render_detail(sel['name'],sel['num'],sel['org'],sel.get('code',''),sel['row'])
                st.markdown("<hr style='margin:8px 0;border-color:var(--border);'>",unsafe_allow_html=True)
    else:
        # ═══ 데스크탑: 2컬럼 ═══
        cl,cd=st.columns([2,3])
        with cl:
            list_c=st.container(height=600)
            with list_c:
                for idx,row in fdf.iterrows():
                    co,cn,cc_,cnum,is_sel,card_h=render_card_html(row,idx)
                    st.markdown(card_h,unsafe_allow_html=True)
                    if st.button("Touch",key=f"c_{idx}",use_container_width=True):
                        cr={k:(safe_str(v) if not isinstance(v,(int,float,np.integer,np.floating)) or pd.isna(v) else v) for k,v in row.to_dict().items()}
                        st.session_state['sel_cust']={'idx':idx,'name':cn,'org':co,'code':cc_,'num':cnum,'row':cr}; st.rerun()
        with cd:
            sel=st.session_state.get('sel_cust')
            if sel is None:
                st.markdown("<div style='text-align:center;padding:40px 20px;color:#8b95a1;font-size:14px;'>👈 사용인을 선택하세요</div>",unsafe_allow_html=True)
            else:
                det_c=st.container(height=600)
                with det_c:
                    cn_s=sel['name']; cnum_s=sel['num']; co_s=sel['org']; cc_s=sel.get('code','')
                    st.markdown(f"<div class='info-card'><div class='ic-name'>{cn_s}</div><div class='ic-meta'>{co_s}</div></div>",unsafe_allow_html=True)
                    render_detail(cn_s,cnum_s,co_s,cc_s,sel['row'],kp="d_")

# =============================================================
# 10. 모니터링 — 총괄→본부→지점 드릴다운
# =============================================================
elif menu=="📊 활동 모니터링":
    st.markdown("<h2 style='font-weight:800;'>📊 활동 모니터링</h2>",unsafe_allow_html=True)
    if not st.session_state.get('mon_auth'):
        with st.form("mon_pw"):
            pw=st.text_input("🔒 비밀번호",type="password")
            if st.form_submit_button("로그인",use_container_width=True):
                if pw==ADM_PW: st.session_state['mon_auth']=True; st.rerun()
                else: st.error("❌")
        st.stop()
    months=get_available_months(); cur_mk=datetime.now().strftime("%Y%m")
    if cur_mk not in months: months=[cur_mk]+months
    mlbl={m:f"{m[:4]}년 {m[4:]}월" for m in months}
    sel_mk=st.selectbox("📅 월 선택",months,format_func=lambda x:mlbl.get(x,x),key="ms")
    ldf=get_login_summary_by_month(sel_mk); mdf=get_msg_summary_by_month(sel_mk)
    tm=ldf['매니저코드'].nunique() if not ldf.empty else 0
    tc=int(mdf['발송횟수'].sum()) if not mdf.empty else 0
    tp=int(mdf['발송인원'].sum()) if not mdf.empty else 0
    st.markdown(f"<div class='mon-row'><div class='mon-card red'><div class='mc-label'>로그인</div><div class='mc-num'>{tm}</div><div class='mc-sub'>명</div></div><div class='mon-card'><div class='mc-label'>발송</div><div class='mc-num'>{tc}</div><div class='mc-sub'>건</div></div><div class='mon-card'><div class='mc-label'>대상</div><div class='mc-num'>{tp}</div><div class='mc-sub'>명</div></div></div>",unsafe_allow_html=True)

    if has_data():
        df_all=st.session_state['df_merged'].copy()
        mc1_=st.session_state.get('manager_col',''); mc2_=st.session_state.get('manager_col2','')
        mn_col_=st.session_state.get('manager_name_col','')
        HQ_COLS=('현재영업단조직명','지역단조직명'); BR_COLS=('현재지점조직명','지점조직명')

        # 매니저별 정보 수집
        mgr_info={}
        all_mc=[mc1_]+([mc2_] if mc2_ and mc2_ in df_all.columns else [])
        for mc_col in all_mc:
            if mc_col not in df_all.columns: continue
            df_all[f'_ck_{mc_col}']=df_all[mc_col].apply(clean_key)
            for k in df_all[f'_ck_{mc_col}'].unique():
                if not k or k in mgr_info: continue
                sub=df_all[df_all[f'_ck_{mc_col}']==k]
                r0=sub.iloc[0].to_dict()
                hq=resolve_val(r0,HQ_COLS[0],HQ_COLS[1]) or '(미지정)'
                br=resolve_val(r0,BR_COLS[0],BR_COLS[1]) or '(미지정)'
                nm=safe_str(r0.get(mn_col_,'')) if mn_col_ else k
                mgr_info[k]={'total':len(sub),'hq':hq,'branch':br,'name':nm or k}

        mgr_sent={}
        if not mdf.empty:
            for _,r in mdf.iterrows():
                k=clean_key(str(r['매니저코드']))
                if k not in mgr_sent: mgr_sent[k]=0
                mgr_sent[k]=max(mgr_sent[k],int(r['발송인원']))
                if k not in mgr_info: mgr_info[k]={'total':0,'hq':'(미지정)','branch':'(미지정)','name':r['매니저명'] or k}

        # 계층 집계
        hq_stats={}
        for k,info in mgr_info.items():
            hq=info['hq']; br=info['branch']; snt=mgr_sent.get(k,0); tot=info['total']
            if hq not in hq_stats: hq_stats[hq]={'total':0,'sent':0,'branches':{}}
            hq_stats[hq]['total']+=tot; hq_stats[hq]['sent']+=snt
            if br not in hq_stats[hq]['branches']: hq_stats[hq]['branches'][br]={'total':0,'sent':0,'mgrs':[]}
            hq_stats[hq]['branches'][br]['total']+=tot; hq_stats[hq]['branches'][br]['sent']+=snt
            rate=round(snt/tot*100) if tot>0 else 0
            hq_stats[hq]['branches'][br]['mgrs'].append({'code':k,'name':info['name'],'total':tot,'sent':snt,'rate':rate})

        def rc(rate): return '#00c471' if rate>=80 else ('#ff9500' if rate>=50 else 'rgb(128,0,0)')

        # 드릴다운 네비게이션
        view_options=["📊 총괄"]+[f"🏛️ {hq}" for hq in sorted(hq_stats.keys(), key=hq_sort_key)]
        sel_view=st.selectbox("보기",view_options,key="mv")

        if sel_view=="📊 총괄":
            # ── 총괄: 본부별 4칼럼 그리드 ──
            st.markdown("#### 🏛️ 본부별 활동률")
            sorted_hqs=sorted(hq_stats.items(),key=lambda x:hq_sort_key(x[0]))
            gh="<div class='stat-grid'>"
            for hq_name,hs in sorted_hqs:
                rate=round(hs['sent']/hs['total']*100) if hs['total']>0 else 0; c=rc(rate)
                n_br=len(hs['branches']); n_mgr=sum(len(b['mgrs']) for b in hs['branches'].values())
                gh+=f"""<div class='stat-card' style='border-top:3px solid {c};'>
                    <div class='sc-name'>{hq_name}</div>
                    <div class='sc-rate' style='color:{c};'>{rate}%</div>
                    <div style='background:#f0f1f3;border-radius:4px;height:8px;margin-bottom:6px;overflow:hidden;'>
                        <div style='height:100%;width:{min(rate,100)}%;background:{c};border-radius:4px;'></div></div>
                    <div class='sc-detail'>{hs['sent']}/{hs['total']}명</div>
                    <div class='sc-detail'>지점 {n_br}개 · 매니저 {n_mgr}명</div>
                </div>"""
            gh+="</div>"; st.markdown(gh,unsafe_allow_html=True)

            # 매니저 전체 리스트
            st.markdown("#### 👤 매니저별")
            ml_all=[]
            for hq_name,hs in sorted_hqs:
                for br_name,bs in sorted(hs['branches'].items(),key=lambda x:natural_sort_key(x[0])):
                    for m in bs['mgrs']: ml_all.append({**m,'hq':hq_name,'branch':br_name})
            ml_all.sort(key=lambda x:x['rate'],reverse=True)
            if ml_all:
                mdf2=pd.DataFrame(ml_all).rename(columns={'hq':'본부','branch':'지점','name':'매니저','total':'사용인','sent':'활동','rate':'%'})
                st.dataframe(mdf2[['본부','지점','매니저','사용인','활동','%']],use_container_width=True,hide_index=True)

        else:
            # ── 본부 선택: 지점별 4칼럼 그리드 ──
            sel_hq=sel_view.replace("🏛️ ","")
            hs=hq_stats.get(sel_hq,{'total':0,'sent':0,'branches':{}})
            hq_rate=round(hs['sent']/hs['total']*100) if hs['total']>0 else 0
            st.markdown(f"<div style='background:linear-gradient(135deg,rgb(128,0,0),rgb(80,0,0));padding:16px 20px;border-radius:14px;margin-bottom:12px;color:#fff;'>"
                f"<div style='font-size:20px;font-weight:800;'>{sel_hq}</div>"
                f"<div style='font-size:14px;opacity:0.85;margin-top:4px;'>활동률 {hq_rate}% · {hs['sent']}/{hs['total']}명</div></div>",unsafe_allow_html=True)

            st.markdown("#### 🏢 지점별 활동률")
            sorted_brs=sorted(hs['branches'].items(),key=lambda x:natural_sort_key(x[0]))
            gh="<div class='stat-grid'>"
            for br_name,bs in sorted_brs:
                rate=round(bs['sent']/bs['total']*100) if bs['total']>0 else 0; c=rc(rate)
                gh+=f"""<div class='stat-card' style='border-top:3px solid {c};'>
                    <div class='sc-name'>{br_name}</div>
                    <div class='sc-rate' style='color:{c};'>{rate}%</div>
                    <div style='background:#f0f1f3;border-radius:4px;height:8px;margin-bottom:6px;overflow:hidden;'>
                        <div style='height:100%;width:{min(rate,100)}%;background:{c};border-radius:4px;'></div></div>
                    <div class='sc-detail'>{bs['sent']}/{bs['total']}명 · 매니저 {len(bs['mgrs'])}명</div>
                </div>"""
            gh+="</div>"; st.markdown(gh,unsafe_allow_html=True)

            # 매니저 리스트
            st.markdown("#### 👤 매니저별")
            ml_hq=[]
            for br_name,bs in sorted_brs:
                for m in bs['mgrs']: ml_hq.append({**m,'branch':br_name})
            ml_hq.sort(key=lambda x:x['rate'],reverse=True)
            if ml_hq:
                mdf2=pd.DataFrame(ml_hq).rename(columns={'branch':'지점','name':'매니저','total':'사용인','sent':'활동','rate':'%'})
                st.dataframe(mdf2[['지점','매니저','사용인','활동','%']],use_container_width=True,hide_index=True)

    if not ldf.empty:
        with st.expander("🔐 로그인 상세"): st.dataframe(ldf,use_container_width=True,hide_index=True)
    if not mdf.empty:
        csv=mdf.to_csv(index=False).encode('utf-8-sig'); st.download_button("📥 CSV",csv,f"s_{sel_mk}.csv","text/csv")
    st.markdown("---")
    c1_,c2_=st.columns(2)
    with c1_:
        st.caption(f"{mlbl.get(sel_mk,'')} 기록 삭제")
        if st.button(f"🗑️ 초기화",type="primary"): reset_month_logs(sel_mk); st.success("✅"); st.rerun()
    with c2_:
        if os.path.exists(LOG_DB):
            with open(LOG_DB,'rb') as f: st.download_button("💾 DB 백업",f.read(),f"log_{datetime.now().strftime('%Y%m%d')}.db","application/octet-stream")
