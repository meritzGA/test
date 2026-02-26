import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import re, io, os, pickle, shutil, json, sqlite3, base64
from datetime import datetime, timedelta

st.set_page_config(page_title="매니저 활동관리", layout="wide", initial_sidebar_state="collapsed")
st.markdown('<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">', unsafe_allow_html=True)

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
/* 리스트 버튼 — 왼쪽 정렬 */
.stButton > button { border-radius:10px !important; font-weight:500 !important; border:1px solid var(--border) !important; text-align:left !important; justify-content:flex-start !important; padding:6px 12px !important; font-size:13px !important; transition:all .1s !important; }
.stButton > button:hover { background:#f0f1f3 !important; border-color:#d5d8db !important; }
.stButton > button[kind="primary"],[data-testid="stFormSubmitButton"]>button { background:rgb(var(--mr)) !important; color:#fff !important; border:none !important; text-align:center !important; justify-content:center !important; }
/* 사용인 정보 카드 */
.info-card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 14px; margin-bottom:6px; }
.info-card .ic-name { font-size:20px; font-weight:800; color:var(--text1); }
.info-card .ic-meta { font-size:13px; color:var(--text2); margin-top:2px; }
.info-badges { display:flex; gap:4px; margin-top:6px; }
.info-badges .ib { padding:2px 8px; border-radius:5px; font-size:11px; font-weight:600; }
.info-badges .ib.done { background:#e8f8ef; color:#00a85e; }
.info-badges .ib.wait { background:#f2f4f6; color:#c4c9d0; }
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
/* 활동률 바 */
.act-bar-wrap { background:#f0f1f3; border-radius:6px; height:20px; position:relative; overflow:hidden; }
.act-bar-fill { height:100%; border-radius:6px; background:linear-gradient(90deg,rgb(128,0,0),rgb(180,40,40)); transition:width .3s; }
.act-bar-text { position:absolute; top:0; left:0; right:0; text-align:center; font-size:11px; font-weight:700; color:#fff; line-height:20px; }
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
              'cust_name_col_a','cust_name_col_b','cust_code_col_a','cust_code_col_b','cust_branch_col_a','cust_branch_col_b','display_cols','prize_config']:
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
def load_user_prefs():
    if os.path.exists(USER_PREFS_FILE):
        try:
            with open(USER_PREFS_FILE,'rb') as f: return pickle.load(f)
        except: pass
    return {}
def save_user_prefs(prefs):
    try:
        with open(USER_PREFS_FILE,'wb') as f: pickle.dump(prefs,f)
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
            st.session_state['display_cols']=dc; save_cfg(); st.success("✅"); st.rerun()

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
    dcfg=st.session_state.get('display_cols',[]); pcfg=st.session_state.get('prize_config',[])

    if not st.session_state.get('mgr_in'):
        st.markdown("<div class='hero-card'><h1 class='hero-name'>매니저 로그인</h1><p class='hero-sub'>코드와 비밀번호를 입력하세요</p></div>",unsafe_allow_html=True)
        with st.form("ml"):
            ci=st.text_input("매니저 코드",placeholder="코드"); pi=st.text_input("비밀번호",type="password")
            if st.form_submit_button("로그인",use_container_width=True):
                if pi!=MGR_PW: st.error("❌ 비밀번호 오류")
                elif not ci: st.error("코드를 입력하세요")
                else:
                    cc=clean_key(ci); df['_s1']=df[mc1].apply(clean_key); mask=df['_s1']==cc
                    if mc2 and mc2 in df.columns: df['_s2']=df[mc2].apply(clean_key); mask=mask|(df['_s2']==cc)
                    my=df[mask]
                    if my.empty: st.error(f"❌ '{ci}' 없음")
                    else:
                        mn="매니저"
                        if mn_col in my.columns:
                            ns=my[mn_col].dropna(); ns=ns[ns.astype(str).str.strip()!='']
                            if not ns.empty:
                                n=safe_str(ns.iloc[0])
                                if n: mn=n
                        st.session_state.update({'mgr_in':True,'mgr_code':cc,'mgr_name':mn,'sel_cust':None}); log_login(cc,mn); st.rerun()
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
    smry=get_mgr_summary(mgr_c); ml={1:"①인사",2:"②리플렛",3:"③시상",4:"④종합"}
    mh="<div class='metric-row'>"
    for mt,lb in ml.items():
        inf=smry.get(mt,{'customers':0,'count':0}); ac=" active" if inf['customers']>0 else ""
        mh+=f"<div class='metric-card{ac}'><div class='mc-label'>{lb}</div><div class='mc-val'>{inf['customers']}</div><div class='mc-sub'>{inf['count']}건</div></div>"
    mh+="</div>"; st.markdown(mh,unsafe_allow_html=True)

    cl,cd=st.columns([2,3])
    with cl:
        srch=st.text_input("🔍",placeholder="이름/소속 검색",key="cs",label_visibility="collapsed")
        fdf=my.copy()
        if srch: fdf=fdf[fdf.apply(lambda r: srch.lower() in str(r.values).lower(),axis=1)]
        list_c=st.container(height=520)
        with list_c:
            for idx,row in fdf.iterrows():
                co=resolve_val(row,_cba,_cbb) or resolve_val(row,'현재대리점지사명','대리점지사명')
                cn=resolve_val(row,_cna,_cnb) or resolve_val(row,'현재대리점설계사조직명','대리점설계사명') or safe_str(row.get('본인고객번호',''))
                cc_=resolve_val(row,_cca,_ccb) or resolve_val(row,'현재대리점설계사조직코드','대리점설계사조직코드')
                cnum=safe_str(row.get('본인고객번호','')) or safe_str(row.get('_search_key',''))
                logs=get_cust_logs(mgr_c,cnum) if cnum else []; stypes=set(l['message_type'] for l in logs)
                bg=" ".join('🟢' if mt in stypes else '⚪' for mt in [1,2,3,4])
                bl=f"{co} | {cn}" if co else cn
                if st.button(f"{bl}  {bg}",key=f"c_{idx}",use_container_width=True):
                    cr={k:(safe_str(v) if not isinstance(v,(int,float,np.integer,np.floating)) or pd.isna(v) else v) for k,v in row.to_dict().items()}
                    st.session_state['sel_cust']={'idx':idx,'name':cn,'org':co,'code':cc_,'num':cnum,'row':cr}; st.rerun()

    with cd:
        sel=st.session_state.get('sel_cust')
        if sel is None:
            st.markdown("<div style='text-align:center;padding:40px 20px;color:#8b95a1;font-size:14px;'>👈 사용인을 선택하세요</div>",unsafe_allow_html=True)
        else:
            cn=sel['name']; cnum=sel['num']; co=sel['org']; cc_=sel.get('code',''); crow=sel['row']
            det_c=st.container(height=580)
            with det_c:
                # 정보카드 (컴팩트)
                logs=get_cust_logs(mgr_c,cnum); stypes=set(l['message_type'] for l in logs)
                ih=f"<div class='info-card'><div class='ic-name'>{cn}</div>"
                meta_parts=[]
                if co: meta_parts.append(co)
                if cc_: meta_parts.append(cc_)
                if meta_parts: ih+=f"<div class='ic-meta'>{' · '.join(meta_parts)}</div>"
                ih+="<div class='info-badges'>"
                for mt,lb in ml.items():
                    ih+=f"<span class='ib {'done' if mt in stypes else 'wait'}'>{lb}{'✓' if mt in stypes else ''}</span>"
                ih+="</div></div>"; st.markdown(ih,unsafe_allow_html=True)

                # 실적 + 시상 밀착 배치
                has_perf=False
                if dcfg:
                    pt=[]
                    for col in dcfg:
                        val=crow.get(col)
                        if val is None:
                            for sfx in ['_파일1','_파일2']:
                                if col+sfx in crow: val=crow[col+sfx]; break
                        dv=safe_str(val)
                        if not dv or dv in ('0','0.0'): continue
                        if isinstance(val,(int,float,np.integer,np.floating)) and not pd.isna(val): dv=fmt_num(val)
                        if dv: pt.append((col,dv))
                    if pt:
                        has_perf=True
                        ph="<div class='perf-inline'>"
                        for k,v in pt: ph+=f"<span class='perf-tag'><span class='pk'>{k}</span><span class='pv'>{v}</span></span>"
                        ph+="</div>"; st.markdown(ph,unsafe_allow_html=True)

                if pcfg:
                    prs=calc_prize(crow,pcfg)
                    ph="<div style='margin:2px 0;'>"
                    for pr in prs: ph+=prize_line_html(pr)
                    ph+="</div>"; st.markdown(ph,unsafe_allow_html=True)

                # 메시지
                st.markdown("<p style='font-size:14px;font-weight:700;margin:6px 0 2px;color:var(--text2);'>📤 메시지</p>",unsafe_allow_html=True)
                t1,t2,t3,t4=st.tabs(["①인사","②리플렛","③시상","④종합"])

                with t1:
                    # 인사말 — 파일 영구 저장
                    prefs=load_user_prefs(); saved_gr=prefs.get('greeting','')
                    gr=st.text_area("인사말",value=saved_gr,placeholder="안녕하세요! 이번 달도 화이팅입니다!",key=f"g_{cnum}",height=60)
                    if st.button("💬 저장 & 생성",key=f"gb_{cnum}",use_container_width=True):
                        if gr:
                            prefs['greeting']=gr; save_user_prefs(prefs)
                            st.session_state[f'msg1_{cnum}']=f"안녕하세요, {cn}님!\n{mgr_n} 매니저입니다.\n\n{gr}"
                        else: st.warning("입력하세요")
                    sm=st.session_state.get(f'msg1_{cnum}','')
                    if not sm and saved_gr:
                        sm=f"안녕하세요, {cn}님!\n{mgr_n} 매니저입니다.\n\n{saved_gr}"
                        st.session_state[f'msg1_{cnum}']=sm
                    if sm:
                        st.text_area("미리보기",sm,height=80,disabled=True,key=f"p1_{cnum}")
                        render_kakao(sm,"📋 카톡",f"k1_{cnum}",45)
                        if st.button("✅ 기록",key=f"l1_{cnum}",type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,1); st.success("✅"); st.rerun()

                with t2:
                    # 리플렛 — 파일 영구 저장
                    prefs=load_user_prefs()
                    lf=st.file_uploader("이미지 (한번 저장하면 유지)",type=["png","jpg","jpeg"],key=f"lf_{cnum}")
                    if lf:
                        prefs['leaflet']=lf.getvalue(); prefs['leaflet_name']=lf.name; save_user_prefs(prefs)
                    lb=prefs.get('leaflet'); ln=prefs.get('leaflet_name','')
                    if lb:
                        st.image(lb,caption=ln,use_container_width=True)
                        render_img_share(lb,ln,f"is_{cnum}",50)
                        if st.button("✅ 기록",key=f"l2_{cnum}",type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,2); st.success("✅"); st.rerun()
                    else:
                        st.caption("리플렛 이미지를 업로드하세요")

                with t3:
                    if pcfg:
                        prs=calc_prize(crow,pcfg)
                        lines=["📋 메리츠 시상 현황 안내",f"📅 {datetime.now().strftime('%Y.%m.%d')} 기준","",f"👤 {co+' ' if co else ''}{cn} 팀장님",""]
                        weekly=[p for p in prs if p.get('category')=='weekly']; cumul=[p for p in prs if p.get('category')=='cumulative']
                        if weekly:
                            lines.append("━━ 시책 현황 ━━")
                            for pr in weekly:
                                lines.append(f"  {pr['name']}: {fmt_num(pr['perf'])}")
                                if pr['achieved_tier']: lines.append(f"  ✅ {fmt_num(pr['achieved_tier'])} 달성")
                                if pr['next_tier']: lines.append(f"  🎯 목표 {fmt_num(pr['next_tier'])}"); lines.append(f"  🔴 부족 {fmt_num(pr['shortfall'])}")
                                lines.append("")
                        if cumul:
                            lines.append("━━ 누계 시상 ━━")
                            for pr in cumul:
                                if pr['existing_prize']>0: lines.append(f"  {pr['name']}: {fmt_num(pr['existing_prize'])}원")
                                elif pr['perf']>0: lines.append(f"  {pr['name']}: 실적 {fmt_num(pr['perf'])}")
                            lines.append("")
                        tp=sum(p['existing_prize'] for p in cumul if p['existing_prize']>0)
                        if tp>0: lines.append(f"💰 시상금: {fmt_num(tp)}원"); lines.append("")
                        lines+=["부족한 거 챙겨서 꼭 시상 많이 받으세요!","좋은 하루 되세요! 😊"]
                        msg="\n".join(lines)
                        st.text_area("미리보기",msg,height=180,disabled=True,key=f"p3_{cnum}")
                        render_kakao(msg,"📋 시상 카톡",f"k3_{cnum}",45)
                        if st.button("✅ 기록",key=f"l3_{cnum}",type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,3); st.success("✅"); st.rerun()
                    else: st.info("시상 JSON 필요")

                with t4:
                    # 종합카톡 — 소속/코드/성명 제거 (이미 특정인에게 보내므로)
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
                                    pfx="  🔴 " if '부족' in col else ("  🎯 " if '목표' in col else "  ")
                                    lines.append(f"{pfx}{col}: {dv}")
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
                        st.text_area("미리보기",msg,height=180,disabled=True,key=f"p4_{cnum}")
                        render_kakao(msg,"📋 종합 카톡",f"k4_{cnum}",45)
                        if st.button("✅ 기록",key=f"l4_{cnum}",type="primary"): log_msg(mgr_c,mgr_n,cnum,cn,4); st.success("✅"); st.rerun()

# =============================================================
# 10. 모니터링 — 본부/지점/매니저별 활동률
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

    # 본부/지점/매니저별 활동률 계산
    if has_data() and not mdf.empty:
        df_all=st.session_state['df_merged'].copy()
        mc1_=st.session_state.get('manager_col',''); mc2_=st.session_state.get('manager_col2','')
        mn_col_=st.session_state.get('manager_name_col','')

        # 본부/지점 열 (파일A/B 자동 resolve)
        HQ_COLS = ('현재영업단조직명','지역단조직명')   # 본부
        BR_COLS = ('현재지점조직명','지점조직명')       # 지점

        # 매니저별 정보 수집
        mgr_info = {}  # code -> {total, hq, branch, name}
        all_mgr_cols = [mc1_] + ([mc2_] if mc2_ and mc2_ in df_all.columns else [])
        for mc_col in all_mgr_cols:
            if mc_col not in df_all.columns: continue
            df_all[f'_ck_{mc_col}'] = df_all[mc_col].apply(clean_key)
            for k in df_all[f'_ck_{mc_col}'].unique():
                if not k or k in mgr_info: continue
                sub = df_all[df_all[f'_ck_{mc_col}']==k]
                row0 = sub.iloc[0].to_dict()
                hq = resolve_val(row0, HQ_COLS[0], HQ_COLS[1]) or '(미지정)'
                br = resolve_val(row0, BR_COLS[0], BR_COLS[1]) or '(미지정)'
                nm = safe_str(row0.get(mn_col_,'')) if mn_col_ else k
                mgr_info[k] = {'total':len(sub), 'hq':hq, 'branch':br, 'name':nm or k}

        # 매니저별 발송 인원
        mgr_sent = {}
        for _,r in mdf.iterrows():
            k = clean_key(str(r['매니저코드']))
            if k not in mgr_sent: mgr_sent[k] = 0
            mgr_sent[k] = max(mgr_sent[k], int(r['발송인원']))
            if k not in mgr_info:
                mgr_info[k] = {'total':0,'hq':'(미지정)','branch':'(미지정)','name':r['매니저명'] or k}

        # 본부별 집계
        hq_stats = {}  # hq -> {total, sent, branches: {br -> {total, sent, mgrs:[]}}}
        for k,info in mgr_info.items():
            hq = info['hq']; br = info['branch']
            snt = mgr_sent.get(k, 0); tot = info['total']
            if hq not in hq_stats: hq_stats[hq] = {'total':0,'sent':0,'branches':{}}
            hq_stats[hq]['total'] += tot; hq_stats[hq]['sent'] += snt
            if br not in hq_stats[hq]['branches']: hq_stats[hq]['branches'][br] = {'total':0,'sent':0,'mgrs':[]}
            hq_stats[hq]['branches'][br]['total'] += tot
            hq_stats[hq]['branches'][br]['sent'] += snt
            rate = round(snt/tot*100) if tot>0 else 0
            hq_stats[hq]['branches'][br]['mgrs'].append({'code':k,'name':info['name'],'total':tot,'sent':snt,'rate':rate})

        def bar_color(rate): return '#00c471' if rate>=80 else ('#ff9500' if rate>=50 else 'rgb(128,0,0)')

        # ── 본부별 활동률 ──
        st.markdown("#### 🏛️ 본부별 활동률")
        sorted_hqs = sorted(hq_stats.items(), key=lambda x: x[1]['sent']/max(x[1]['total'],1), reverse=True)
        for hq_name, hs in sorted_hqs:
            rate = round(hs['sent']/hs['total']*100) if hs['total']>0 else 0
            bc = bar_color(rate)
            st.markdown(f"""<div style='background:#fff;border:1px solid #eaedf0;border-radius:12px;padding:12px 16px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.04);'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;'>
                    <span style='font-size:15px;font-weight:800;color:#191f28;'>🏛️ {hq_name}</span>
                    <span style='font-size:16px;font-weight:800;color:{bc};'>{rate}%</span>
                </div>
                <div class='act-bar-wrap'><div class='act-bar-fill' style='width:{min(rate,100)}%;background:{bc};'></div>
                <div class='act-bar-text' style='color:{"#fff" if rate>15 else "#333"};'>{hs['sent']}/{hs['total']}명</div></div>
                <div style='font-size:11px;color:#8b95a1;margin-top:3px;'>지점 {len(hs["branches"])}개 · 매니저 {sum(len(b["mgrs"]) for b in hs["branches"].values())}명</div>
            </div>""", unsafe_allow_html=True)

        # ── 지점별 활동률 ──
        st.markdown("#### 🏢 지점별 활동률")
        all_branches = []
        for hq_name, hs in sorted_hqs:
            for br_name, bs in hs['branches'].items():
                all_branches.append((hq_name, br_name, bs))
        all_branches.sort(key=lambda x: x[2]['sent']/max(x[2]['total'],1), reverse=True)
        for hq_name, br_name, bs in all_branches:
            rate = round(bs['sent']/bs['total']*100) if bs['total']>0 else 0
            bc = bar_color(rate)
            st.markdown(f"""<div style='background:#fff;border:1px solid #eaedf0;border-radius:10px;padding:10px 14px;margin-bottom:5px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
                    <div><span style='font-size:13px;font-weight:700;'>{br_name}</span><span style='font-size:10px;color:#8b95a1;margin-left:6px;'>{hq_name}</span></div>
                    <span style='font-size:13px;font-weight:800;color:{bc};'>{rate}%</span>
                </div>
                <div class='act-bar-wrap'><div class='act-bar-fill' style='width:{min(rate,100)}%;background:{bc};'></div>
                <div class='act-bar-text' style='color:{"#fff" if rate>15 else "#333"};'>{bs['sent']}/{bs['total']}명</div></div>
            </div>""", unsafe_allow_html=True)

        # ── 매니저별 상세 리스트 ──
        st.markdown("#### 👤 매니저별 활동 현황")
        mgr_list = []
        for hq_name, hs in sorted_hqs:
            for br_name, bs in hs['branches'].items():
                for m in bs['mgrs']:
                    mgr_list.append({**m, 'hq':hq_name, 'branch':br_name})
        mgr_list.sort(key=lambda x: x['rate'], reverse=True)
        mgr_df = pd.DataFrame(mgr_list)
        if not mgr_df.empty:
            mgr_df = mgr_df.rename(columns={'hq':'본부','branch':'지점','name':'매니저','total':'사용인수','sent':'활동인원','rate':'활동률%'})
            mgr_df = mgr_df[['본부','지점','매니저','사용인수','활동인원','활동률%']]
            st.dataframe(mgr_df, use_container_width=True, hide_index=True)
    elif not mdf.empty:
        st.markdown("#### 📤 발송"); mlm={1:"①인사",2:"②리플렛",3:"③시상",4:"④종합"}; mdf['메시지유형']=mdf['메시지유형'].map(mlm)
        pc=mdf.pivot_table(index=['매니저코드','매니저명'],columns='메시지유형',values='발송인원',fill_value=0).reset_index()
        st.dataframe(pc,use_container_width=True,hide_index=True)

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
