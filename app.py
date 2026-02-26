import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import re
import io
import os
import pickle
import uuid
import shutil
import json
import sqlite3
from datetime import datetime

st.set_page_config(page_title="매니저 활동관리 시스템", layout="wide")

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

DATA_FILE = "app_data.pkl"
CONFIG_FILE = "app_config.pkl"
LOG_DB = "activity_log.db"

# ==========================================
# 0. 메리츠 스타일 커스텀 CSS
# ==========================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
.toss-header {
    background-color: rgb(128, 0, 0);
    padding: 32px 40px;
    border-radius: 20px;
    margin-bottom: 24px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.toss-title {
    color: #ffffff !important;
    font-size: 36px;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
}
.toss-subtitle {
    color: #ffcccc !important;
    font-size: 24px;
    font-weight: 700;
    margin-left: 10px;
}
.toss-desc {
    color: #f2f4f6 !important;
    font-size: 17px;
    margin: 12px 0 0 0;
    font-weight: 500;
}
.block-container {
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}
iframe { width: 100% !important; }
/* 파일 상태 카드 */
.file-card {
    background: #f8f9fa; border-radius: 12px; padding: 16px;
    border: 1px solid #e5e8eb; margin-bottom: 8px;
}
.file-card.loaded {
    background: #f0fdf4; border-color: #86efac;
}
/* 발송 배지 */
.badge-sent { display:inline-block; background:#22c55e; color:#fff; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:700; margin:1px; }
.badge-unsent { display:inline-block; background:#e5e7eb; color:#9ca3af; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; margin:1px; }
/* 모니터링 메트릭 */
.mon-card {
    background: #fff; border-radius: 14px; padding: 20px;
    border: 1px solid #e5e8eb; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.mon-card h3 { margin:0; font-size:14px; color:#6b7684; font-weight:600; }
.mon-card .num { font-size:32px; font-weight:800; color:#191f28; margin:8px 0 4px; }
.mon-card .sub { font-size:12px; color:#8b95a1; }

@media (max-width: 768px) {
    .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    .toss-header { padding: 18px 16px; border-radius: 14px; margin-bottom: 14px; }
    .toss-title { font-size: 22px !important; }
    .toss-subtitle { font-size: 14px !important; display: block; margin-left: 0; margin-top: 4px; }
    .toss-desc { font-size: 13px !important; margin-top: 6px; }
    iframe { min-height: 60vh !important; }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        width: 100% !important; padding: 10px !important; font-size: 15px !important;
    }
}
@media (max-width: 480px) {
    .block-container { padding-left: 0.25rem !important; padding-right: 0.25rem !important; }
    .toss-header { padding: 14px 12px; border-radius: 10px; }
    .toss-title { font-size: 19px !important; }
    .toss-subtitle { font-size: 12px !important; }
    .toss-desc { font-size: 12px !important; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 유틸리티 함수
# ==========================================
def clean_key(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan': return ""
    val_str = str(val).strip().replace(" ", "").upper()
    if val_str.endswith('.0'): val_str = val_str[:-2]
    return val_str

def decode_excel_text(val):
    if pd.isna(val): return val
    val_str = str(val)
    if '_x' not in val_str: return val_str
    def decode_match(match):
        try: return chr(int(match.group(1), 16))
        except: return match.group(0)
    return re.sub(r'_x([0-9a-fA-F]{4})_', decode_match, val_str)

@st.cache_data(show_spinner=False)
def load_file_data(file_bytes, file_name):
    if file_name.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8', errors='replace')
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(decode_excel_text)
    # 코드/번호 컬럼 float → str
    code_kw = ["코드", "번호", "ID", "id"]
    for col in df.columns:
        if any(kw in col for kw in code_kw):
            if df[col].dtype in ['float64', 'float32']:
                df[col] = df[col].apply(lambda x: str(int(x)) if pd.notna(x) else "")
            elif df[col].dtype in ['int64', 'int32']:
                df[col] = df[col].astype(str)
    return df

def fmt_num(val):
    """숫자 포맷팅: 0→빈칸, 세자리 콤마"""
    try:
        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == 'nan': return ""
        clean_val = str(val).replace(',', '')
        num = float(clean_val)
        if num == 0: return ""
        if num.is_integer(): return f"{int(num):,}"
        return f"{num:,.1f}"
    except:
        s = str(val).strip()
        if s in ["0", "0.0", "nan", "None"]: return ""
        return s

def safe_str(val):
    """NaN/None → 빈 문자열, 그 외 str 변환"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ('nan', 'none', 'nat'):
        return ""
    return s

def resolve_display_value(row, col_name, all_cols=None):
    """행에서 컬럼 값을 가져오되, NaN이면 빈 문자열. 접미사 붙은 버전도 시도."""
    if col_name and col_name in row.index:
        v = safe_str(row[col_name])
        if v: return v
    # 접미사 붙은 버전 시도
    if col_name:
        for suffix in ['_파일1', '_파일2', '_A', '_B']:
            alt = col_name + suffix
            if alt in row.index:
                v = safe_str(row[alt])
                if v: return v
    return ""

def resolve_customer_name(row, primary_col):
    """사용인 이름: 기본열 → 대체 후보 순회 → 고객번호"""
    v = resolve_display_value(row, primary_col)
    if v: return v
    # 대체 후보 열 (이름 관련)
    fallbacks = ['대리점설계사명', '현재대리점설계사조직명', '현재영업가족명', '현재대리점지사명']
    for fb in fallbacks:
        if fb == primary_col: continue
        for col in row.index:
            base = col.replace('_파일1','').replace('_파일2','')
            if base == fb:
                v = safe_str(row[col])
                if v: return v
    # 최후 수단: 고객번호
    for col in row.index:
        if '본인고객번호' in col:
            v = safe_str(row[col])
            if v: return v
    return "(이름없음)"

def resolve_customer_org(row, primary_col):
    """사용인 소속: 기본열 → 대체 후보 순회"""
    v = resolve_display_value(row, primary_col)
    if v: return v
    fallbacks = ['현재대리점설계사조직명', '현재영업가족명', '대리점지사명', '현재대리점지사명', '영업가족명']
    for fb in fallbacks:
        if fb == primary_col: continue
        for col in row.index:
            base = col.replace('_파일1','').replace('_파일2','')
            if base == fb:
                v = safe_str(row[col])
                if v: return v
    return ""

def resolve_customer_number(row):
    """본인고객번호를 찾아 반환"""
    for col in row.index:
        if '본인고객번호' in col:
            v = safe_str(row[col])
            if v: return v
    return ""

# ==========================================
# 2. 데이터 영구 저장/불러오기
# ==========================================

def sanitize_dataframe(df):
    """DataFrame에서 모든 NaN/None/'nan' 문자열을 정리"""
    if df is None or df.empty: return df
    for col in df.columns:
        if col.startswith('_'): continue
        # object(문자열) 컬럼: NaN → ""
        if df[col].dtype == object:
            df[col] = df[col].fillna("")
            # 'nan', 'None' 문자열도 제거
            df[col] = df[col].apply(lambda x: "" if str(x).strip().lower() in ('nan', 'none', 'nat') else x)
        elif df[col].dtype in ['float64', 'float32']:
            # 텍스트성 숫자열(코드/번호 등)은 문자열로 변환
            text_kw = ['명', '코드', '번호', 'ID', 'id', '구분', '구간', '여부', '상태', '직책', '대상', '선물', '조직']
            if any(kw in col for kw in text_kw):
                df[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(int(x)) if isinstance(x, float) and x == int(x) else str(x))
            else:
                df[col] = df[col].fillna(0)
        elif df[col].dtype in ['int64', 'int32']:
            pass  # int는 NaN 없음
        else:
            # 기타 타입: NaN → ""
            if df[col].isna().any():
                df[col] = df[col].fillna("")
    return df
def _reset_session_state():
    st.session_state['df_merged'] = pd.DataFrame()
    st.session_state['file_a_name'] = ""
    st.session_state['file_b_name'] = ""
    st.session_state['join_col_a'] = ""
    st.session_state['join_col_b'] = ""
    st.session_state['manager_col'] = ""
    st.session_state['manager_col2'] = ""
    st.session_state['manager_name_col'] = ""
    st.session_state['customer_name_col'] = ""
    st.session_state['customer_org_col'] = ""
    st.session_state['display_cols'] = []
    st.session_state['prize_json_data'] = {}

def load_data_and_config():
    cfg = None
    for fp in [CONFIG_FILE, CONFIG_FILE + ".bak"]:
        if not os.path.exists(fp): continue
        try:
            with open(fp, 'rb') as f:
                d = pickle.load(f)
            if isinstance(d, dict): cfg = d; break
        except: continue
    if cfg is None: cfg = {}
    
    for k in ['file_a_name', 'file_b_name', 'join_col_a', 'join_col_b',
              'manager_col', 'manager_col2', 'manager_name_col',
              'customer_name_col', 'customer_org_col']:
        st.session_state[k] = str(cfg.get(k, ""))
    st.session_state['display_cols'] = cfg.get('display_cols', []) if isinstance(cfg.get('display_cols'), list) else []
    st.session_state['prize_json_data'] = cfg.get('prize_json_data', {}) if isinstance(cfg.get('prize_json_data'), dict) else {}
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                data = pickle.load(f)
            df = data.get('df_merged', pd.DataFrame()) if isinstance(data, dict) else pd.DataFrame()
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = sanitize_dataframe(df)
            st.session_state['df_merged'] = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        except:
            st.session_state['df_merged'] = pd.DataFrame()

def save_config():
    cfg = {}
    for k in ['file_a_name', 'file_b_name', 'join_col_a', 'join_col_b',
              'manager_col', 'manager_col2', 'manager_name_col',
              'customer_name_col', 'customer_org_col', 'display_cols', 'prize_json_data']:
        cfg[k] = st.session_state.get(k, "")
    try:
        if os.path.exists(CONFIG_FILE):
            shutil.copy2(CONFIG_FILE, CONFIG_FILE + ".bak")
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, 'wb') as f: pickle.dump(cfg, f)
        shutil.move(tmp, CONFIG_FILE)
    except: pass

def save_data():
    try:
        data = {'df_merged': st.session_state.get('df_merged', pd.DataFrame())}
        tmp = DATA_FILE + ".tmp"
        with open(tmp, 'wb') as f: pickle.dump(data, f)
        shutil.move(tmp, DATA_FILE)
    except: pass

def has_data():
    df = st.session_state.get('df_merged', None)
    return isinstance(df, pd.DataFrame) and not df.empty

# ==========================================
# 3. 로그 DB (SQLite) — 메시지/로그인 추적
# ==========================================
def get_log_db():
    conn = sqlite3.connect(LOG_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_log_db():
    conn = get_log_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS message_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_code TEXT NOT NULL,
        manager_name TEXT,
        customer_number TEXT NOT NULL,
        customer_name TEXT,
        message_type INTEGER NOT NULL,
        sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        month_key TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_code TEXT NOT NULL,
        manager_name TEXT,
        login_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_mgr ON message_logs(manager_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_month ON message_logs(month_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_cust ON message_logs(customer_number)")
    conn.commit()
    conn.close()

def log_message(mgr_code, mgr_name, cust_num, cust_name, msg_type):
    month_key = datetime.now().strftime("%Y%m")
    conn = get_log_db()
    conn.execute("INSERT INTO message_logs (manager_code, manager_name, customer_number, customer_name, message_type, month_key) VALUES (?,?,?,?,?,?)",
                 (str(mgr_code), mgr_name, str(cust_num), cust_name, msg_type, month_key))
    conn.commit(); conn.close()

def get_customer_logs(mgr_code, cust_num):
    month_key = datetime.now().strftime("%Y%m")
    conn = get_log_db()
    rows = conn.execute("SELECT message_type, sent_date FROM message_logs WHERE manager_code=? AND customer_number=? AND month_key=? ORDER BY sent_date DESC",
                        (str(mgr_code), str(cust_num), month_key)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_manager_summary(mgr_code):
    month_key = datetime.now().strftime("%Y%m")
    conn = get_log_db()
    rows = conn.execute("SELECT message_type, COUNT(DISTINCT customer_number) as uniq, COUNT(*) as cnt FROM message_logs WHERE manager_code=? AND month_key=? GROUP BY message_type",
                        (str(mgr_code), month_key)).fetchall()
    conn.close()
    return {r['message_type']: {'customers': r['uniq'], 'count': r['cnt']} for r in rows}

def log_login(mgr_code, mgr_name=""):
    conn = get_log_db()
    conn.execute("INSERT INTO login_logs (manager_code, manager_name) VALUES (?,?)", (str(mgr_code), mgr_name))
    conn.commit(); conn.close()

def get_all_message_summary():
    month_key = datetime.now().strftime("%Y%m")
    conn = get_log_db()
    df = pd.read_sql("""SELECT manager_code as 매니저코드, manager_name as 매니저명,
        message_type as 메시지유형, COUNT(DISTINCT customer_number) as 발송인원, COUNT(*) as 발송횟수
        FROM message_logs WHERE month_key=? GROUP BY manager_code, manager_name, message_type ORDER BY manager_code""",
        conn, params=[month_key])
    conn.close()
    return df

def get_login_summary():
    month_key = datetime.now().strftime("%Y%m")
    conn = get_log_db()
    df = pd.read_sql(f"""SELECT manager_code as 매니저코드, manager_name as 매니저명,
        COUNT(*) as 로그인횟수, MAX(login_date) as 최근로그인
        FROM login_logs WHERE strftime('%Y%m', login_date) = ? GROUP BY manager_code ORDER BY 로그인횟수 DESC""",
        conn, params=[month_key])
    conn.close()
    return df

def cleanup_old_logs():
    month_key = datetime.now().strftime("%Y%m")
    conn = get_log_db()
    conn.execute("DELETE FROM message_logs WHERE month_key != ?", (month_key,))
    conn.commit(); conn.close()

# ==========================================
# 4. 카카오톡 공유 HTML 컴포넌트
# ==========================================
def render_kakao_btn(text, label="📋 카톡 보내기", btn_id="kakao", height=55):
    """모바일: Web Share API, PC: 클립보드 복사"""
    import base64 as _b64
    encoded = _b64.b64encode(text.encode('utf-8')).decode('ascii')
    html = f"""
    <style>
    .k-btn {{
        display:inline-flex; align-items:center; gap:8px;
        background:linear-gradient(135deg,#FEE500 0%,#F5D600 100%);
        color:#3C1E1E; border:none; padding:12px 24px; border-radius:12px;
        font-size:15px; font-weight:700; cursor:pointer; width:100%;
        justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,0.08);
        transition:all 0.15s; font-family:'Pretendard',sans-serif;
    }}
    .k-btn:active {{ transform:scale(0.97); }}
    .k-btn.done {{ background:linear-gradient(135deg,#22C55E,#16A34A); color:#fff; }}
    .k-status {{ font-size:12px; color:#666; margin-top:4px; text-align:center; }}
    </style>
    <button class="k-btn" id="{btn_id}" onclick="doShare_{btn_id}()">
        <svg viewBox="0 0 24 24" fill="#3C1E1E" width="20" height="20"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg>
        {label}
    </button>
    <div class="k-status" id="st_{btn_id}"></div>
    <script>
    function doShare_{btn_id}() {{
        var t = decodeURIComponent(escape(atob("{encoded}")));
        if(/Mobi|Android|iPhone/i.test(navigator.userAgent) && navigator.share) {{
            navigator.share({{text:t}}).then(function(){{showDone_{btn_id}();}}).catch(function(){{fallCopy_{btn_id}(t);}});
        }} else {{ fallCopy_{btn_id}(t); }}
    }}
    function fallCopy_{btn_id}(t) {{
        var ta=document.createElement('textarea'); ta.value=t;
        ta.style.cssText='position:fixed;left:-9999px;top:0;opacity:0;';
        document.body.appendChild(ta); ta.focus(); ta.select(); ta.setSelectionRange(0,999999);
        var ok=false; try{{ok=document.execCommand('copy');}}catch(e){{}}
        document.body.removeChild(ta);
        if(ok){{showDone_{btn_id}();}} else if(navigator.clipboard){{
            navigator.clipboard.writeText(t).then(function(){{showDone_{btn_id}();}}).catch(function(){{
                document.getElementById('st_{btn_id}').innerHTML='⚠️ 수동 복사: 텍스트를 길게 눌러 복사하세요';
            }});
        }}
    }}
    function showDone_{btn_id}() {{
        var b=document.getElementById('{btn_id}'); b.classList.add('done'); b.innerHTML='✅ 복사 완료!';
        document.getElementById('st_{btn_id}').innerHTML='<a href="kakaotalk://launch" style="color:#3B82F6;">카카오톡 열기</a>';
        setTimeout(function(){{ b.classList.remove('done'); b.innerHTML='<svg viewBox="0 0 24 24" fill="#3C1E1E" width="20" height="20"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg> {label}'; }}, 3000);
    }}
    </script>
    """
    components.html(html, height=height)

# ==========================================
# 5. 세션 초기화
# ==========================================
if 'df_merged' not in st.session_state:
    _reset_session_state()
    load_data_and_config()
init_log_db()
cleanup_old_logs()

# ==========================================
# 6. 사이드바 메뉴
# ==========================================
st.sidebar.title("📋 활동관리 시스템")
try:
    MANAGER_PASSWORD = os.environ.get("MANAGER_PASSWORD", "") or st.secrets.get("MANAGER_PASSWORD", "meritz1!")
except Exception:
    MANAGER_PASSWORD = os.environ.get("MANAGER_PASSWORD", "meritz1!")
try:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "") or st.secrets.get("ADMIN_PASSWORD", "wolf7998")
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "wolf7998")

menu = st.sidebar.radio("이동할 화면", ["📱 매니저 화면", "⚙️ 관리자 화면", "📊 활동 모니터링"])

# ==========================================
# 7. 관리자 화면
# ==========================================
if menu == "⚙️ 관리자 화면":
    st.title("⚙️ 관리자 설정 화면")
    
    if not st.session_state.get('admin_authenticated', False):
        with st.form("admin_login"):
            admin_pw = st.text_input("🔒 관리자 비밀번호", type="password")
            if st.form_submit_button("로그인"):
                if admin_pw == ADMIN_PASSWORD:
                    st.session_state['admin_authenticated'] = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 일치하지 않습니다.")
        st.stop()

    # ── 7-1. 파일 업로드 / 삭제 / 병합 ──
    st.header("1. 📂 데이터 파일 업로드 및 병합")
    
    if has_data():
        st.success(f"✅ 현재 **{len(st.session_state['df_merged']):,}행**의 병합 데이터가 운영 중입니다.")
    
    # 파일 A
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 📄 파일 A")
        if 'df_file_a' in st.session_state and st.session_state['df_file_a'] is not None:
            fa = st.session_state['df_file_a']
            st.markdown(f"""<div class='file-card loaded'>
                ✅ <b>{st.session_state.get('file_a_name','')}</b><br>
                <span style='color:#6b7684;font-size:13px;'>{len(fa):,}행 × {len(fa.columns)}열</span>
            </div>""", unsafe_allow_html=True)
            if st.button("🗑️ 파일 A 삭제", key="del_a"):
                del st.session_state['df_file_a']
                st.session_state['file_a_name'] = ""
                st.rerun()
        else:
            file_a = st.file_uploader("파일 A 업로드", type=['csv', 'xlsx'], key="upload_a")
            if file_a:
                with st.spinner("읽는 중..."):
                    df_a = load_file_data(file_a.getvalue(), file_a.name)
                    st.session_state['df_file_a'] = df_a
                    st.session_state['file_a_name'] = file_a.name
                    st.rerun()

    with col_b:
        st.markdown("#### 📄 파일 B")
        if 'df_file_b' in st.session_state and st.session_state['df_file_b'] is not None:
            fb = st.session_state['df_file_b']
            st.markdown(f"""<div class='file-card loaded'>
                ✅ <b>{st.session_state.get('file_b_name','')}</b><br>
                <span style='color:#6b7684;font-size:13px;'>{len(fb):,}행 × {len(fb.columns)}열</span>
            </div>""", unsafe_allow_html=True)
            if st.button("🗑️ 파일 B 삭제", key="del_b"):
                del st.session_state['df_file_b']
                st.session_state['file_b_name'] = ""
                st.rerun()
        else:
            file_b = st.file_uploader("파일 B 업로드", type=['csv', 'xlsx'], key="upload_b")
            if file_b:
                with st.spinner("읽는 중..."):
                    df_b = load_file_data(file_b.getvalue(), file_b.name)
                    st.session_state['df_file_b'] = df_b
                    st.session_state['file_b_name'] = file_b.name
                    st.rerun()

    # 조인 키 선택 및 병합
    fa_ok = 'df_file_a' in st.session_state and st.session_state.get('df_file_a') is not None
    fb_ok = 'df_file_b' in st.session_state and st.session_state.get('df_file_b') is not None
    
    if fa_ok and fb_ok:
        st.markdown("---")
        st.subheader("🔗 조인 키 선택 및 데이터 병합")
        
        cols_a = st.session_state['df_file_a'].columns.tolist()
        cols_b = st.session_state['df_file_b'].columns.tolist()
        
        prev_ja = st.session_state.get('join_col_a', '')
        prev_jb = st.session_state.get('join_col_b', '')
        idx_a = cols_a.index(prev_ja) if prev_ja in cols_a else (cols_a.index('본인고객번호') if '본인고객번호' in cols_a else 0)
        idx_b = cols_b.index(prev_jb) if prev_jb in cols_b else (cols_b.index('본인고객번호') if '본인고객번호' in cols_b else 0)
        
        c1, c2 = st.columns(2)
        with c1:
            join_a = st.selectbox("파일 A 조인 키", cols_a, index=idx_a, key="sel_join_a")
            sample_a = st.session_state['df_file_a'][join_a].head(3).tolist()
            st.caption(f"샘플: {', '.join(str(v) for v in sample_a)}")
        with c2:
            join_b = st.selectbox("파일 B 조인 키", cols_b, index=idx_b, key="sel_join_b")
            sample_b = st.session_state['df_file_b'][join_b].head(3).tolist()
            st.caption(f"샘플: {', '.join(str(v) for v in sample_b)}")
        
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        with c_btn1:
            if st.button("🔗 데이터 병합 (Outer Join)", type="primary", use_container_width=True):
                with st.spinner("병합 중..."):
                    df_a = st.session_state['df_file_a'].copy()
                    df_b = st.session_state['df_file_b'].copy()
                    df_a['_mk_a'] = df_a[join_a].apply(clean_key)
                    df_b['_mk_b'] = df_b[join_b].apply(clean_key)
                    
                    merged = pd.merge(df_a, df_b, left_on='_mk_a', right_on='_mk_b',
                                      how='outer', suffixes=('_파일1', '_파일2'))
                    
                    # suffix 동일 열 자동 통합
                    cols_1 = [c for c in merged.columns if c.endswith('_파일1')]
                    for c1_col in cols_1:
                        base = c1_col.replace('_파일1', '')
                        c2_col = base + '_파일2'
                        if c2_col in merged.columns:
                            merged[base] = merged[c1_col].combine_first(merged[c2_col])
                            merged.drop(columns=[c1_col, c2_col], inplace=True)
                    
                    merged['_search_key'] = merged['_mk_a'].combine_first(merged['_mk_b'])
                    
                    # ✅ NaN 정리
                    merged = sanitize_dataframe(merged)
                    
                    st.session_state['df_merged'] = merged.copy()
                    st.session_state['join_col_a'] = join_a
                    st.session_state['join_col_b'] = join_b
                    
                    save_data()
                    save_config()
                    st.success(f"✅ 병합 완료! {len(merged):,}행 × {len(merged.columns)}열")
                    st.rerun()
        
        with c_btn2:
            if has_data() and st.button("🗑️ 병합 데이터 삭제", use_container_width=True):
                st.session_state['df_merged'] = pd.DataFrame()
                save_data()
                st.rerun()
    
    elif fa_ok or fb_ok:
        st.info("💡 두 파일을 모두 업로드하면 병합할 수 있습니다.")
        single_df = st.session_state.get('df_file_a') if fa_ok else st.session_state.get('df_file_b')
        if single_df is not None:
            if st.button("📄 단일 파일만 사용"):
                single = sanitize_dataframe(single_df.copy())
                st.session_state['df_merged'] = single
                save_data(); save_config()
                st.rerun()
    
    # 병합 미리보기
    if has_data():
        df = st.session_state['df_merged']
        st.markdown("---")
        st.subheader(f"📋 병합 데이터 미리보기 ({len(df):,}행)")
        avail = [c for c in df.columns if not c.startswith('_')]
        mgr_cols = [c for c in avail if '매니저코드' in c or '지원매니저코드' in c]
        for mc in mgr_cols:
            st.caption(f"  `{mc}` 고유값: {df[mc].dropna().nunique()}개")
        preview = df[avail].head(30).fillna("")
        st.dataframe(preview, use_container_width=True, height=250)

    st.divider()
    
    # ── 7-2. 매니저/사용인 열 설정 ──
    if has_data():
        df = st.session_state['df_merged']
        avail = [c for c in df.columns if not c.startswith('_')]
        
        st.header("2. 매니저 로그인 & 사용인 표시 열 설정")
        st.caption("매니저 코드 열, 이름 열, 사용인 표시 열을 설정합니다.")
        
        c1, c2 = st.columns(2)
        with c1:
            prev_mc = st.session_state.get('manager_col', '')
            idx_mc = avail.index(prev_mc) if prev_mc in avail else (avail.index('매니저코드') if '매니저코드' in avail else 0)
            manager_col = st.selectbox("🔑 매니저 코드 열 (파일1)", avail, index=idx_mc, key="cfg_mgr")
        with c2:
            mc2_opts = ["(없음)"] + avail
            prev_mc2 = st.session_state.get('manager_col2', '')
            idx_mc2 = mc2_opts.index(prev_mc2) if prev_mc2 in mc2_opts else (mc2_opts.index('지원매니저코드') if '지원매니저코드' in mc2_opts else 0)
            manager_col2 = st.selectbox("🔑 보조 매니저 코드 열 (파일2)", mc2_opts, index=idx_mc2, key="cfg_mgr2")
        
        c3, c4 = st.columns(2)
        with c3:
            prev_mn = st.session_state.get('manager_name_col', '')
            idx_mn = avail.index(prev_mn) if prev_mn in avail else (avail.index('매니저명') if '매니저명' in avail else 0)
            manager_name_col = st.selectbox("👤 매니저 이름 열", avail, index=idx_mn, key="cfg_mgrn")
        with c4:
            prev_cn = st.session_state.get('customer_name_col', '')
            name_cand = [c for c in avail if '설계사' in c and '명' in c and '코드' not in c]
            default_cn = name_cand[0] if name_cand else avail[0]
            idx_cn = avail.index(prev_cn) if prev_cn in avail else (avail.index(default_cn) if default_cn in avail else 0)
            customer_name_col = st.selectbox("👤 사용인 이름 열", avail, index=idx_cn, key="cfg_custn")
        
        prev_co = st.session_state.get('customer_org_col', '')
        org_cand = [c for c in avail if '대리점' in c and '명' in c and '코드' not in c]
        default_co = org_cand[0] if org_cand else avail[0]
        idx_co = avail.index(prev_co) if prev_co in avail else (avail.index(default_co) if default_co in avail else 0)
        customer_org_col = st.selectbox("🏢 사용인 소속 열", avail, index=idx_co, key="cfg_custo")
        
        st.markdown("---")
        st.subheader("📋 사용인 카드에 표시할 항목 선택")
        st.caption("매니저가 사용인 클릭 시 볼 실적 항목을 선택하세요. 선택 순서대로 표시됩니다.")
        
        # 추천 항목
        rec_cols = ['인보험실적', '목표금액', '인정실적', '부족금액', '구간', '독려구분',
                    '현재월연속가동', '실적_1주차', '실적_2주차', '실적_3주차', '실적_4주차', '실적_5주차',
                    '실적계', '시상금계', '추가예정금계', '시상금계and추가예정금계',
                    '시상금총액_메클_메리츠plus', '메리츠plus_부족실적']
        prev_disp = st.session_state.get('display_cols', [])
        default_disp = prev_disp if prev_disp else [c for c in rec_cols if c in avail]
        
        display_cols = st.multiselect("표시 항목 (순서대로)", avail, default=[c for c in default_disp if c in avail], key="cfg_disp")
        
        if st.button("💾 설정 저장", key="save_all_cfg", type="primary"):
            st.session_state['manager_col'] = manager_col
            st.session_state['manager_col2'] = manager_col2 if manager_col2 != "(없음)" else ""
            st.session_state['manager_name_col'] = manager_name_col
            st.session_state['customer_name_col'] = customer_name_col
            st.session_state['customer_org_col'] = customer_org_col
            st.session_state['display_cols'] = display_cols
            save_config()
            st.success("✅ 설정이 저장되었습니다!")
            st.rerun()
        
        st.divider()
        
        # ── 7-3. 시상 JSON 업로드 ──
        st.header("3. 🏆 시상 JSON 업로드")
        st.caption("외부 앱에서 계산된 시상 JSON을 업로드하면 매니저 화면에서 시상 안내가 가능합니다.")
        
        prize_data = st.session_state.get('prize_json_data', {})
        if prize_data:
            cnt = len(prize_data) if isinstance(prize_data, (list, dict)) else 0
            st.success(f"✅ 시상 JSON 로드됨 ({cnt}건)")
            if st.button("🗑️ 시상 JSON 삭제"):
                st.session_state['prize_json_data'] = {}
                save_config()
                st.rerun()
        
        json_file = st.file_uploader("시상 JSON 파일", type=["json"], key="upload_json")
        if json_file:
            try:
                jdata = json.load(json_file)
                st.session_state['prize_json_data'] = jdata
                save_config()
                st.success("✅ 시상 JSON 업로드 완료!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("유효한 JSON 파일이 아닙니다.")
        
        st.divider()
        
        # ── 7-4. 시스템 초기화 ──
        with st.expander("⚠️ 시스템 초기화"):
            st.caption("모든 설정과 데이터가 삭제됩니다.")
            confirm = st.text_input("'reset' 입력 후 실행", key="reset_confirm")
            if st.button("🔄 초기화 실행", disabled=(confirm != "reset")):
                for fp in [CONFIG_FILE, DATA_FILE, LOG_DB]:
                    try:
                        if os.path.exists(fp): os.remove(fp)
                    except: pass
                _reset_session_state()
                st.rerun()


# ==========================================
# 8. 매니저 화면
# ==========================================
elif menu == "📱 매니저 화면":
    st.session_state['admin_authenticated'] = False
    
    if not has_data() or not st.session_state.get('manager_col'):
        st.title("📱 매니저 활동관리")
        st.warning("현재 데이터가 없거나 관리자 설정이 완료되지 않았습니다.")
        st.stop()
    
    df = st.session_state['df_merged'].copy()
    manager_col = st.session_state['manager_col']
    manager_col2 = st.session_state.get('manager_col2', '')
    manager_name_col = st.session_state.get('manager_name_col', manager_col)
    cust_name_col = st.session_state.get('customer_name_col', '')
    cust_org_col = st.session_state.get('customer_org_col', '')
    display_cols_cfg = st.session_state.get('display_cols', [])
    
    # ── 로그인 ──
    if not st.session_state.get('mgr_logged_in', False):
        st.title("📱 매니저 로그인")
        with st.form("mgr_login"):
            mgr_code_input = st.text_input("🔑 매니저 코드", placeholder="매니저코드를 입력하세요")
            mgr_pw_input = st.text_input("🔒 비밀번호", type="password")
            submit_login = st.form_submit_button("로그인", use_container_width=True)
            
            if submit_login:
                if mgr_pw_input != MANAGER_PASSWORD:
                    st.error("❌ 비밀번호가 올바르지 않습니다.")
                elif not mgr_code_input:
                    st.error("매니저코드를 입력하세요.")
                else:
                    code_clean = clean_key(mgr_code_input)
                    df['_sk1'] = df[manager_col].apply(clean_key)
                    mask = df['_sk1'] == code_clean
                    if manager_col2 and manager_col2 in df.columns:
                        df['_sk2'] = df[manager_col2].apply(clean_key)
                        mask = mask | (df['_sk2'] == code_clean)
                    
                    my_df = df[mask]
                    if my_df.empty:
                        st.error(f"❌ 매니저 코드 '{mgr_code_input}'에 매칭된 사용인이 없습니다.")
                    else:
                        mgr_name = "매니저"
                        if manager_name_col in my_df.columns:
                            names = my_df[manager_name_col].dropna()
                            names = names[names.astype(str).str.strip() != '']
                            if not names.empty:
                                n = safe_str(names.iloc[0])
                                if n: mgr_name = n
                        
                        st.session_state['mgr_logged_in'] = True
                        st.session_state['mgr_code'] = code_clean
                        st.session_state['mgr_name'] = mgr_name
                        st.session_state['selected_cust'] = None
                        log_login(code_clean, mgr_name)
                        st.rerun()
        st.stop()
    
    # ── 로그인 후 메인 ──
    mgr_code = st.session_state['mgr_code']
    mgr_name = st.session_state['mgr_name']
    
    # 사용인 필터
    df['_sk1'] = df[manager_col].apply(clean_key)
    mask = df['_sk1'] == mgr_code
    if manager_col2 and manager_col2 in df.columns:
        df['_sk2'] = df[manager_col2].apply(clean_key)
        mask = mask | (df['_sk2'] == mgr_code)
    my_df = df[mask].copy().reset_index(drop=True)
    
    # 헤더
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown(f"""<div class='toss-header'>
            <h1 class='toss-title'>{mgr_name} <span class='toss-subtitle'>매니저님</span></h1>
            <p class='toss-desc'>사용인 {len(my_df)}명 | {datetime.now().strftime('%Y년 %m월')} 기준</p>
        </div>""", unsafe_allow_html=True)
    with col_h2:
        st.write("")
        if st.button("🚪 로그아웃"):
            st.session_state['mgr_logged_in'] = False
            st.session_state['selected_cust'] = None
            st.rerun()
    
    # 발송 요약 메트릭
    summary = get_manager_summary(mgr_code)
    msg_labels = {1: "① 인사말", 2: "② 리플렛", 3: "③ 시상안내", 4: "④ 시상+실적"}
    mcols = st.columns(4)
    for i, (mt, label) in enumerate(msg_labels.items()):
        with mcols[i]:
            info = summary.get(mt, {'customers': 0, 'count': 0})
            st.metric(label, f"{info['customers']}명", f"{info['count']}회 발송")
    
    st.markdown("---")
    
    # ── 사용인 리스트 + 상세 ──
    col_list, col_detail = st.columns([2, 3])
    
    with col_list:
        st.subheader(f"👥 사용인 ({len(my_df)}명)")
        search = st.text_input("🔍 검색", placeholder="이름/소속 검색...", key="cust_search")
        
        filtered_df = my_df.copy()
        if search:
            search_mask = filtered_df.apply(lambda row: search.lower() in str(row.values).lower(), axis=1)
            filtered_df = filtered_df[search_mask]
        
        for idx, row in filtered_df.iterrows():
            c_name = resolve_customer_name(row, cust_name_col)
            c_org = resolve_customer_org(row, cust_org_col)
            c_num = resolve_customer_number(row)
            
            # 발송 뱃지
            logs = get_customer_logs(mgr_code, c_num) if c_num else []
            sent_types = set(l['message_type'] for l in logs)
            badges = ""
            for mt in [1, 2, 3, 4]:
                if mt in sent_types:
                    badges += f"<span class='badge-sent'>{mt}</span>"
                else:
                    badges += f"<span class='badge-unsent'>{mt}</span>"
            
            btn_label = f"{c_name} | {c_org}" if c_org else c_name
            
            # 뱃지 표시
            st.markdown(f"<div style='font-size:11px;margin-bottom:-8px;margin-top:4px;'>{badges}</div>", unsafe_allow_html=True)
            
            if st.button(btn_label, key=f"cust_{idx}", use_container_width=True):
                # NaN 안전 처리된 dict 저장
                clean_row = {k: (safe_str(v) if not isinstance(v, (int, float, np.integer, np.floating)) or pd.isna(v) else v) 
                             for k, v in row.to_dict().items()}
                st.session_state['selected_cust'] = {
                    'idx': idx, 'name': c_name, 'org': c_org, 'num': c_num,
                    'row': clean_row
                }
                st.rerun()
    
    with col_detail:
        sel = st.session_state.get('selected_cust', None)
        if sel is None:
            st.info("👈 왼쪽에서 사용인을 선택하세요.")
        else:
            cust_name = sel['name']
            cust_num = sel['num']
            cust_org = sel['org']
            cust_row = sel['row']
            
            st.subheader(f"📋 {cust_name}")
            org_text = f"소속: {cust_org} | " if cust_org else ""
            st.caption(f"{org_text}고객번호: {cust_num}")
            
            # 당월 발송 상태
            logs = get_customer_logs(mgr_code, cust_num)
            sent_types = set(l['message_type'] for l in logs)
            scols = st.columns(4)
            for i, (mt, label) in enumerate(msg_labels.items()):
                with scols[i]:
                    if mt in sent_types:
                        st.success(f"✅ {label}")
                    else:
                        st.warning(f"⬜ {label}")
            
            # 실적 데이터 표시
            with st.expander("📈 실적 상세", expanded=True):
                perf_items = []
                for col in display_cols_cfg:
                    # 직접 매칭 또는 접미사 매칭
                    val = None
                    actual_col = col
                    if col in cust_row:
                        val = cust_row[col]
                    else:
                        for suffix in ['_파일1', '_파일2']:
                            alt = col + suffix
                            if alt in cust_row:
                                val = cust_row[alt]
                                actual_col = alt
                                break
                    
                    if val is None:
                        continue
                    display_val = safe_str(val)
                    if not display_val or display_val in ('0', '0.0'):
                        continue
                    if isinstance(val, (int, float, np.integer, np.floating)) and not pd.isna(val):
                        display_val = fmt_num(val)
                    if display_val:
                        perf_items.append((col, display_val))  # 표시명은 원래 col 이름
                if perf_items:
                    perf_df = pd.DataFrame(perf_items, columns=['항목', '값'])
                    st.dataframe(perf_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("표시할 실적 데이터가 없습니다.")
            
            st.markdown("---")
            st.subheader("📤 메시지 발송")
            
            tab1, tab2, tab3, tab4 = st.tabs(["① 인사말", "② 리플렛", "③ 시상안내", "④ 시상+실적"])
            
            # ── ① 인사말 보내기 ──
            with tab1:
                greeting = st.text_area("인사말 입력", placeholder="안녕하세요! 이번 달도 화이팅입니다!", key=f"greet_{cust_num}", height=100)
                if greeting:
                    msg = f"안녕하세요, {cust_name}님!\n{mgr_name} 매니저입니다.\n\n{greeting}"
                    st.text_area("미리보기", msg, height=120, disabled=True, key=f"prev1_{cust_num}")
                    render_kakao_btn(msg, "📋 인사말 카톡 보내기", f"k1_{cust_num}")
                    if st.button("✅ 발송 완료 기록", key=f"log1_{cust_num}", type="primary"):
                        log_message(mgr_code, mgr_name, cust_num, cust_name, 1)
                        st.success("기록 완료!")
                        st.rerun()
            
            # ── ② 리플렛 보내기 ──
            with tab2:
                leaflet = st.file_uploader("리플렛 파일", type=["png", "jpg", "jpeg", "pdf"], key=f"leaf_{cust_num}")
                if leaflet:
                    st.success(f"📎 {leaflet.name} 첨부됨")
                    msg = f"📎 {mgr_name} 매니저가 {cust_name}님께 리플렛을 보냈습니다.\n\n첨부파일: {leaflet.name}\n\n카카오톡 공유 후 리플렛 파일을 직접 전송해주세요."
                    st.text_area("미리보기", msg, height=100, disabled=True, key=f"prev2_{cust_num}")
                    render_kakao_btn(msg, "📋 리플렛 안내 카톡 보내기", f"k2_{cust_num}")
                    if st.button("✅ 발송 완료 기록", key=f"log2_{cust_num}", type="primary"):
                        log_message(mgr_code, mgr_name, cust_num, cust_name, 2)
                        st.success("기록 완료!")
                        st.rerun()
            
            # ── ③ 시상 안내하기 ──
            with tab3:
                # 병합 데이터에서 시상 관련 열 추출
                prize_keys = ['시상금계', '추가예정금계', '시상금계and추가예정금계', '시상금총액_메클_메리츠plus',
                              '지급예정금1', '총지급예정금', '브릿지시상금', '연속가동시상금']
                prize_info = {}
                for k in cust_row:
                    base = k.replace('_파일1', '').replace('_파일2', '')
                    if base in prize_keys or any(pk in k for pk in prize_keys):
                        val = cust_row[k]
                        display_val = safe_str(val)
                        if not display_val or display_val in ('0', '0.0'):
                            continue
                        if isinstance(val, (int, float, np.integer, np.floating)) and not pd.isna(val):
                            display_val = fmt_num(val)
                        if display_val:
                            prize_info[k] = display_val
                
                # 외부 JSON 시상 데이터
                json_prize = st.session_state.get('prize_json_data', {})
                json_cust_prize = {}
                if json_prize:
                    if isinstance(json_prize, list):
                        for item in json_prize:
                            if str(item.get('본인고객번호', '')) == str(cust_num):
                                json_cust_prize = {k: v for k, v in item.items() if k != '본인고객번호'}
                                break
                    elif isinstance(json_prize, dict):
                        json_cust_prize = json_prize.get(str(cust_num), {})
                
                combined_prize = {**prize_info}
                for k, v in json_cust_prize.items():
                    display_val = safe_str(v)
                    if display_val and display_val not in ('0', '0.0'):
                        if isinstance(v, (int, float)):
                            display_val = fmt_num(v)
                        combined_prize[k] = display_val
                
                if combined_prize:
                    st.dataframe(pd.DataFrame([combined_prize]).fillna(""), use_container_width=True)
                    lines = [f"📊 {cust_name}님 시상 현황 안내", "─" * 20]
                    for k, v in combined_prize.items():
                        if v:  # 빈 값 스킵
                            lines.append(f"▪ {k}: {v}")
                    msg = "\n".join(lines)
                    st.text_area("미리보기", msg, height=180, disabled=True, key=f"prev3_{cust_num}")
                    render_kakao_btn(msg, "📋 시상안내 카톡 보내기", f"k3_{cust_num}")
                    if st.button("✅ 발송 완료 기록", key=f"log3_{cust_num}", type="primary"):
                        log_message(mgr_code, mgr_name, cust_num, cust_name, 3)
                        st.success("기록 완료!")
                        st.rerun()
                else:
                    st.warning("시상 데이터가 없습니다. 관리자에게 시상 JSON 업로드를 요청하세요.")
            
            # ── ④ 시상+실적 안내하기 ──
            with tab4:
                lines = [f"📊 {cust_name}님 실적 & 시상 현황", "─" * 20]
                
                # 실적 (perf_items already nan-filtered)
                if perf_items:
                    lines.append("\n📈 실적 현황")
                    for k, v in perf_items:
                        if v:  # 빈 값 스킵
                            lines.append(f"  ▪ {k}: {v}")
                
                # 시상 (combined_prize already nan-filtered)
                if combined_prize:
                    lines.append("\n🏆 시상 현황")
                    for k, v in combined_prize.items():
                        if v:  # 빈 값 스킵
                            lines.append(f"  ▪ {k}: {v}")
                
                if perf_items or combined_prize:
                    msg = "\n".join(lines)
                    st.text_area("미리보기", msg, height=250, disabled=True, key=f"prev4_{cust_num}")
                    render_kakao_btn(msg, "📋 시상+실적 카톡 보내기", f"k4_{cust_num}")
                    if st.button("✅ 발송 완료 기록", key=f"log4_{cust_num}", type="primary"):
                        log_message(mgr_code, mgr_name, cust_num, cust_name, 4)
                        st.success("기록 완료!")
                        st.rerun()
                else:
                    st.warning("실적 및 시상 데이터가 없습니다.")


# ==========================================
# 9. 활동 모니터링
# ==========================================
elif menu == "📊 활동 모니터링":
    st.title("📊 매니저 활동 모니터링")
    st.caption(f"기준월: {datetime.now().strftime('%Y년 %m월')} (매월 1일 자동 초기화)")
    
    if not st.session_state.get('admin_authenticated', False):
        with st.form("mon_login"):
            mon_pw = st.text_input("🔒 관리자 비밀번호", type="password")
            if st.form_submit_button("로그인"):
                if mon_pw == ADMIN_PASSWORD:
                    st.session_state['admin_authenticated'] = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 일치하지 않습니다.")
        st.stop()
    
    tab_login, tab_msg = st.tabs(["🔑 로그인 현황", "📤 메시지 발송 현황"])
    
    with tab_login:
        login_df = get_login_summary()
        if not login_df.empty:
            st.markdown(f"""<div class='mon-card'>
                <h3>당월 로그인 매니저</h3>
                <div class='num'>{len(login_df)}명</div>
            </div>""", unsafe_allow_html=True)
            st.write("")
            st.dataframe(login_df, use_container_width=True, hide_index=True)
        else:
            st.info("당월 로그인 기록이 없습니다.")
    
    with tab_msg:
        msg_df = get_all_message_summary()
        
        if not msg_df.empty:
            msg_labels = {1: "① 인사말", 2: "② 리플렛", 3: "③ 시상안내", 4: "④ 시상+실적"}
            
            # 유형별 총계
            st.subheader("유형별 총계")
            type_sum = msg_df.groupby("메시지유형").agg(총인원=("발송인원", "sum"), 총횟수=("발송횟수", "sum"), 매니저수=("매니저코드", "nunique")).reset_index()
            type_sum["메시지유형"] = type_sum["메시지유형"].map(lambda x: msg_labels.get(x, str(x)))
            
            tcols = st.columns(4)
            for i, (_, row) in enumerate(type_sum.iterrows()):
                if i < 4:
                    with tcols[i]:
                        st.metric(row["메시지유형"], f"{int(row['총인원'])}명", f"{int(row['총횟수'])}회 / {int(row['매니저수'])}매니저")
            
            st.markdown("---")
            
            # 매니저별 피벗
            st.subheader("매니저별 상세")
            msg_df['유형'] = msg_df['메시지유형'].map(lambda x: msg_labels.get(x, str(x)))
            
            pivot_cust = msg_df.pivot_table(index=["매니저코드", "매니저명"], columns="유형", values="발송인원", fill_value=0, aggfunc="sum").reset_index()
            pivot_cust.columns.name = None
            st.markdown("**발송 인원 (명)**")
            st.dataframe(pivot_cust, use_container_width=True, hide_index=True)
            
            pivot_cnt = msg_df.pivot_table(index=["매니저코드", "매니저명"], columns="유형", values="발송횟수", fill_value=0, aggfunc="sum").reset_index()
            pivot_cnt.columns.name = None
            st.markdown("**발송 횟수 (회)**")
            st.dataframe(pivot_cnt, use_container_width=True, hide_index=True)
            
            st.download_button("📥 CSV 다운로드",
                data=msg_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"message_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv")
        else:
            st.info("당월 메시지 발송 기록이 없습니다.")
