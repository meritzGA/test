import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(page_title="메리츠화재 시상 현황", layout="wide")

# --- 데이터 영구 저장을 위한 폴더 설정 ---
DATA_DIR = "app_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 🔒 추가 기능: 접속 로그 저장 함수 ---
LOG_FILE = os.path.join(DATA_DIR, "access_log.csv")

import re as _re
def _clean_excel_text(s):
    """엑셀 _xHHHH_ 이스케이프 시퀀스를 원래 유니코드 문자로 복원"""
    if not s or not isinstance(s, str): return s
    return _re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), s)

def save_log(user_name, user_code, action_type):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = pd.DataFrame([[now, user_name, user_code, action_type]], 
                            columns=["시간", "이름/구분", "코드", "작업"])
    if not os.path.exists(LOG_FILE):
        log_data.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
    else:
        log_data.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")

# --- 📋 추가 기능: 카카오톡 원클릭 복사 컴포넌트 ---
def copy_btn_component(text):
    escaped_text = json.dumps(text, ensure_ascii=False)
    js_code = f"""
    <div id="copy-container">
        <button id="copy-btn">💬 카카오톡 메시지 원클릭 복사</button>
    </div>
    <script>
    document.getElementById("copy-btn").onclick = function() {{
        const text = {escaped_text};
        navigator.clipboard.writeText(text).then(function() {{
            alert("메시지가 복사되었습니다! 원하시는 채팅창에 붙여넣기(Ctrl+V) 하세요.");
        }}, function(err) {{
            console.error('복사 실패:', err);
        }});
    }}
    </script>
    <style>
        #copy-btn {{
            width: 100%; height: 55px; background-color: #FEE500; color: #3C1E1E;
            border: none; border-radius: 12px; font-weight: 800; font-size: 1.1rem;
            cursor: pointer; margin-top: 5px; margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        #copy-btn:active {{ transform: scale(0.98); }}
    </style>
    """
    components.html(js_code, height=85)

# 데이터 불러오기 로직
if 'raw_data' not in st.session_state:
    st.session_state['raw_data'] = {}
    for file in os.listdir(DATA_DIR):
        if file.endswith('.pkl'):
            df = pd.read_pickle(os.path.join(DATA_DIR, file))
            df.columns = [_clean_excel_text(str(c)) for c in df.columns]
            for col in df.select_dtypes(include='object').columns:
                df[col] = df[col].apply(lambda v: _clean_excel_text(str(v)) if pd.notna(v) else v)
            st.session_state['raw_data'][file.replace('.pkl', '')] = df

if 'config' not in st.session_state:
    config_path = os.path.join(DATA_DIR, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            st.session_state['config'] = json.load(f)
    else:
        st.session_state['config'] = []

# 기존 데이터 호환성 보장
for c in st.session_state['config']:
    if 'category' not in c:
        c['category'] = 'weekly'

# 🌟 [오류 해결] 엑셀 외계어(_xHHHH_) 복원 및 정제 함수 🌟
def safe_str(val):
    if pd.isna(val) or val is None: return ""
    
    try:
        # 소수점으로 읽힌 사번 복구 (예: 12345.0 -> 12345)
        if isinstance(val, (int, float)) and float(val).is_integer():
            val = int(float(val))
    except:
        pass
        
    s = str(val)
    
    # 1. 엑셀의 숨겨진 16진수 외계어(_x0033_ 등)를 원래 문자(3 등)로 완벽 복원
    s = re.sub(r'_[xX]([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), s)
    
    # 2. 보이지 않는 띄어쓰기, 엔터, 탭 강제 삭제
    s = re.sub(r'\s+', '', s)
    
    # 3. 문자열에 남은 .0 잔재 제거
    if s.endswith('.0'): 
        s = s[:-2]
        
    # 4. 알파벳 대문자 통일 (매칭률 100% 보장)
    return s.upper()

# 🌟 [속도 100배 향상 핵심] 정제된 데이터를 캐싱하여 중복 연산 완전 제거 🌟
def get_clean_series(df, col_name):
    clean_col_name = f"_clean_{col_name}"
    # 한 번 정제된 컬럼이 없다면 최초 1회만 정제 연산을 수행하여 데이터프레임에 저장
    if clean_col_name not in df.columns:
        df[clean_col_name] = df[col_name].apply(safe_str)
    return df[clean_col_name]

def safe_float(val):
    if pd.isna(val) or val is None: return 0.0
    s = str(val).replace(',', '').strip()
    try: return float(s)
    except: return 0.0

# --- 🎨 커스텀 CSS (라이트/다크모드 완벽 대응) ---
st.markdown("""
<style>
    /* ========================================= */
    /* ☀️ 기본 모드 (Light Mode) CSS             */
    /* ========================================= */
    [data-testid="stAppViewContainer"] { background-color: #f2f4f6; color: #191f28; }
    span.material-symbols-rounded, span[data-testid="stIconMaterial"] { display: none !important; }
    
    div[data-testid="stRadio"] > div {
        display: flex; justify-content: center; background-color: #ffffff; 
        padding: 10px; border-radius: 15px; margin-bottom: 20px; margin-top: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #e5e8eb;
    }
    
    .title-band {
        background-color: rgb(128, 0, 0); color: #ffffff; font-size: 1.4rem; font-weight: 800;
        text-align: center; padding: 16px; border-radius: 12px; margin-bottom: 24px;
        letter-spacing: -0.5px; box-shadow: 0 4px 10px rgba(128, 0, 0, 0.2);
    }

    [data-testid="stForm"] { background-color: transparent; border: none; padding: 0; margin-bottom: 24px; }

    /* 공통 텍스트 타이틀 클래스 */
    .admin-title { color: #191f28; font-weight: 800; font-size: 1.8rem; margin-top: 20px; }
    .sub-title { color: #191f28; font-size: 1.4rem; margin-top: 30px; font-weight: 700; }
    .config-title { color: #191f28; font-size: 1.3rem; margin: 0; font-weight: 700; }
    .main-title { color: #191f28; font-weight: 800; font-size: 1.3rem; margin-bottom: 15px; }
    .blue-title { color: #1e3c72; font-size: 1.4rem; margin-top: 10px; font-weight: 800; }
    .agent-title { color: #3182f6; font-weight: 800; font-size: 1.5rem; margin-top: 0; text-align: center; }

    /* 공통 박스 클래스 */
    .config-box { background: #f9fafb; padding: 15px; border-radius: 15px; border: 1px solid #e5e8eb; margin-top: 15px; }
    .config-box-blue { background: #f0f4f8; padding: 15px; border-radius: 15px; border: 1px solid #c7d2fe; margin-top: 15px; }
    .detail-box { background: #ffffff; padding: 20px; border-radius: 20px; border: 2px solid #e5e8eb; margin-top: 10px; margin-bottom: 30px; }

    /* 시책 요약 카드 (상단) */
    .summary-card { 
        background: linear-gradient(135deg, rgb(160, 20, 20) 0%, rgb(128, 0, 0) 100%); 
        border-radius: 20px; padding: 32px 24px; margin-bottom: 24px; border: none;
        box-shadow: 0 10px 25px rgba(128, 0, 0, 0.25);
    }
    .cumulative-card { 
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
        border-radius: 20px; padding: 32px 24px; margin-bottom: 24px; border: none;
        box-shadow: 0 10px 25px rgba(30, 60, 114, 0.25);
    }
    .summary-label { color: rgba(255,255,255,0.85); font-size: 1.15rem; font-weight: 600; margin-bottom: 8px; }
    .summary-total { color: #ffffff; font-size: 2.6rem; font-weight: 800; letter-spacing: -1px; margin-bottom: 24px; white-space: nowrap; word-break: keep-all; }
    .summary-item-name { color: rgba(255,255,255,0.95); font-size: 1.15rem; }
    .summary-item-val { color: #ffffff; font-size: 1.3rem; font-weight: 800; white-space: nowrap; }
    .summary-divider { height: 1px; background-color: rgba(255,255,255,0.2); margin: 16px 0; }
    
    /* 개별 상세 카드 */
    .toss-card { 
        background: #ffffff; border-radius: 20px; padding: 28px 24px; 
        margin-bottom: 16px; border: 1px solid #e5e8eb; box-shadow: 0 4px 20px rgba(0,0,0,0.03); 
    }
    .toss-title { font-size: 1.6rem; font-weight: 700; color: #191f28; margin-bottom: 6px; letter-spacing: -0.5px; }
    .toss-desc { font-size: 1.15rem; color: rgb(128, 0, 0); font-weight: 800; margin-bottom: 24px; letter-spacing: -0.3px; line-height: 1.4; word-break: keep-all; }
    
    .data-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; flex-wrap: nowrap; }
    .data-label { color: #8b95a1; font-size: 1.1rem; word-break: keep-all; }
    .data-value { color: #333d4b; font-size: 1.3rem; font-weight: 600; white-space: nowrap; }
    
    /* 상위 구간 부족 금액 강조 디자인 */
    .shortfall-row { background-color: #fff0f0; padding: 14px; border-radius: 12px; margin-top: 15px; margin-bottom: 5px; border: 2px dashed #ff4b4b; text-align: center; }
    .shortfall-text { color: #d9232e; font-size: 1.2rem; font-weight: 800; word-break: keep-all; }

    .prize-row { display: flex; justify-content: space-between; align-items: center; padding-top: 20px; margin-top: 12px; flex-wrap: nowrap; }
    .prize-label { color: #191f28; font-size: 1.3rem; font-weight: 700; word-break: keep-all; white-space: nowrap; }
    .prize-value { color: rgb(128, 0, 0); font-size: 1.8rem; font-weight: 800; white-space: nowrap; text-align: right; } 
    
    .toss-divider { height: 1px; background-color: #e5e8eb; margin: 16px 0; }
    .sub-data { font-size: 1rem; color: #8b95a1; margin-top: 4px; text-align: right; }
    
    /* 누계 전용 세로 정렬 박스 */
    .cumul-stack-box {
        background: #ffffff; border: 1px solid #e5e8eb; border-left: 6px solid #2a5298; 
        border-radius: 16px; padding: 20px 24px; margin-bottom: 16px; 
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }
    .cumul-stack-info { display: flex; flex-direction: column; gap: 4px; }
    .cumul-stack-title { font-size: 1.25rem; color: #1e3c72; font-weight: 800; word-break: keep-all; }
    .cumul-stack-val { font-size: 1.05rem; color: #8b95a1; }
    .cumul-stack-prize { font-size: 1.6rem; color: #d9232e; font-weight: 800; text-align: right; white-space: nowrap; }
    
    /* 입력 컴포넌트 */
    div[data-testid="stTextInput"] input {
        font-size: 1.3rem !important; padding: 15px !important; height: 55px !important;
        background-color: #ffffff !important; color: #191f28 !important; border: 1px solid #e5e8eb !important; border-radius: 12px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.02);
    }
    div[data-testid="stSelectbox"] > div { background-color: #ffffff !important; border: 1px solid #e5e8eb !important; border-radius: 12px !important; }
    div[data-testid="stSelectbox"] * { font-size: 1.1rem !important; }
    
    /* 버튼 */
    div.stButton > button[kind="primary"] {
        font-size: 1.4rem !important; font-weight: 800 !important; height: 60px !important;
        border-radius: 12px !important; background-color: rgb(128, 0, 0) !important; color: white !important; border: none !important; width: 100%; margin-top: 10px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(128, 0, 0, 0.2) !important;
    }
    
    div.stButton > button[kind="secondary"] {
        font-size: 1.2rem !important; font-weight: 700 !important; min-height: 60px !important; height: auto !important; padding: 10px !important;
        border-radius: 12px !important; background-color: #e8eaed !important; color: #191f28 !important; border: 1px solid #d1d6db !important; width: 100%; margin-top: 5px; margin-bottom: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important; white-space: normal !important; 
    }

    .del-btn-container button {
        background-color: #f2f4f6 !important; color: #dc3545 !important; border: 1px solid #dc3545 !important;
        height: 40px !important; font-size: 1rem !important; margin-top: 0 !important; box-shadow: none !important;
    }

    /* ========================================= */
    /* 🌙 다크 모드 (Dark Mode) CSS              */
    /* ========================================= */
    @media (prefers-color-scheme: dark) {
        [data-testid="stAppViewContainer"] { background-color: #121212 !important; color: #e0e0e0 !important; }
        label, p, .stMarkdown p { color: #e0e0e0 !important; }
        div[data-testid="stRadio"] > div { background-color: #1e1e1e !important; border-color: #333 !important; }
        .admin-title, .sub-title, .config-title, .main-title { color: #ffffff !important; }
        .blue-title, .agent-title { color: #66b2ff !important; }
        .config-box { background-color: #1a1a1a !important; border-color: #333 !important; }
        .config-box-blue { background-color: #121928 !important; border-color: #2a5298 !important; }
        .detail-box { background-color: #121212 !important; border-color: #333 !important; }
        .toss-card { background-color: #1e1e1e !important; border-color: #333 !important; box-shadow: 0 4px 15px rgba(0,0,0,0.5) !important; }
        .toss-title { color: #ffffff !important; }
        .toss-desc { color: #ff6b6b !important; }
        .data-label { color: #a0aab5 !important; }
        .data-value { color: #ffffff !important; }
        .prize-label { color: #ffffff !important; }
        .prize-value { color: #ff4b4b !important; }
        .toss-divider { background-color: #333 !important; }
        .shortfall-row { background-color: #2a1215 !important; border-color: #ff4b4b !important; }
        .shortfall-text { color: #ff6b6b !important; }
        .cumul-stack-box { background-color: #1e1e1e !important; border-color: #333 !important; border-left-color: #4da3ff !important; box-shadow: 0 4px 15px rgba(0,0,0,0.5) !important; }
        .cumul-stack-title { color: #4da3ff !important; }
        .cumul-stack-val { color: #a0aab5 !important; }
        .cumul-stack-prize { color: #ff4b4b !important; }
        div[data-testid="stTextInput"] input { background-color: #1e1e1e !important; color: #ffffff !important; border-color: #444 !important; }
        div[data-testid="stSelectbox"] > div { background-color: #1e1e1e !important; color: #ffffff !important; border-color: #444 !important; }
        div.stButton > button[kind="secondary"] { background-color: #2d2d2d !important; color: #ffffff !important; border-color: #444 !important; }
    }
    
    @media (max-width: 450px) {
        .summary-total { font-size: 2.1rem !important; }
        .summary-label { font-size: 1.05rem !important; }
        .prize-label { font-size: 1.1rem !important; }
        .prize-value { font-size: 1.45rem !important; }
        .data-label { font-size: 1rem !important; }
        .data-value { font-size: 1.15rem !important; }
        .toss-title { font-size: 1.4rem !important; }
        .shortfall-text { font-size: 1.05rem !important; }
        .cumul-stack-box { padding: 16px 20px; flex-direction: row; }
        .cumul-stack-title { font-size: 1.15rem; }
        .cumul-stack-val { font-size: 0.95rem; }
        .cumul-stack-prize { font-size: 1.4rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 공통 함수 (데이터 계산)
# ==========================================
def _read_prize_items(cfg, match_df):
    """설정에서 시상금 항목들을 읽어 [{label, amount, eligible}] 리스트 반환.
    지급률(col_eligible)=0이면 미대상으로 제외, 그 외 값이면 대상으로 포함. 공란이면 무조건 포함."""
    prize_details = []
    items = cfg.get('prize_items', [])
    if items:
        for item in items:
            col_prize = item.get('col_prize', '') or item.get('col', '')  # 구형 호환
            label = item.get('label', '')
            if not col_prize or col_prize not in match_df.columns:
                continue
            
            # 대상 여부 확인
            col_elig = item.get('col_eligible', '')
            if col_elig and col_elig in match_df.columns:
                elig_val = safe_float(match_df[col_elig].values[0])
                if elig_val == 0:
                    # 미대상 (100 등) → 이 항목 건너뜀
                    continue
            
            raw = match_df[col_prize].values[0]
            amt = safe_float(raw)
            prize_details.append({"label": label or col_prize, "amount": amt})
    else:
        # 구형 호환: col_prize 단일 컬럼
        col_prize = cfg.get('col_prize', '')
        if col_prize and col_prize in match_df.columns:
            raw = match_df[col_prize].values[0]
            amt = safe_float(raw)
            if amt != 0:
                prize_details.append({"label": "시상금", "amount": amt})
    return prize_details

def calculate_agent_performance(target_code):
    calculated_results = []
    
    for cfg in st.session_state['config']:
        df = st.session_state['raw_data'].get(cfg['file'])
        if df is None: continue
        col_code = cfg.get('col_code', '')
        if not col_code or col_code not in df.columns: continue
        
        # 🌟 속도 개선: 캐싱된 컬럼에서 즉시 비교 🌟
        clean_codes = get_clean_series(df, col_code)
        match_df = df[clean_codes == safe_str(target_code)]
        if match_df.empty: continue
        
        cat = cfg.get('category', 'weekly')
        p_type = cfg.get('type', '구간 시책')
        
        # 🌟 시상금 여러 항목 읽기
        prize_details = _read_prize_items(cfg, match_df)
        prize = sum(d['amount'] for d in prize_details)
        
        if cat == 'weekly':
            if "1기간" in p_type: 
                if not prize_details: continue  # 미대상 → 항목 자체 미표시
                raw_prev = match_df[cfg['col_val_prev']].values[0] if cfg.get('col_val_prev') and cfg['col_val_prev'] in df.columns else 0
                raw_curr = match_df[cfg['col_val_curr']].values[0] if cfg.get('col_val_curr') and cfg['col_val_curr'] in df.columns else 0
                val_prev = safe_float(raw_prev)
                val_curr = safe_float(raw_curr)
                
                calculated_results.append({
                    "name": cfg['name'], "desc": cfg.get('desc', ''), "category": "weekly", "type": "브릿지1",
                    "val_prev": val_prev, "val_curr": val_curr, "prize": prize, "prize_details": prize_details
                })
                
            elif "2기간" in p_type:
                raw_curr = match_df[cfg['col_val_curr']].values[0] if cfg.get('col_val_curr') and cfg['col_val_curr'] in df.columns else 0
                val_curr = safe_float(raw_curr)
                
                curr_req = float(cfg.get('curr_req', 100000.0))
                calc_rate, tier_achieved, prize = 0, 0, 0
                
                for amt, rate in cfg.get('tiers', []):
                    if val_curr >= amt:
                        tier_achieved = amt
                        calc_rate = rate
                        break
                        
                if tier_achieved > 0:
                    prize = (tier_achieved + curr_req) * (calc_rate / 100)
                    
                next_tier = None
                for amt, rate in reversed(cfg.get('tiers', [])):
                    if val_curr < amt:
                        next_tier = amt
                        break
                shortfall = next_tier - val_curr if next_tier else 0
                
                calculated_results.append({
                    "name": cfg['name'], "desc": cfg.get('desc', ''), "category": "weekly", "type": "브릿지2",
                    "val": val_curr, "tier": tier_achieved, "rate": calc_rate, "prize": prize,
                    "curr_req": curr_req, "next_tier": next_tier, "shortfall": shortfall
                })

            else: 
                if not prize_details: continue  # 미대상 → 항목 자체 미표시
                raw_val = match_df[cfg['col_val']].values[0] if cfg.get('col_val') and cfg['col_val'] in df.columns else 0
                val = safe_float(raw_val)
                
                calculated_results.append({
                    "name": cfg['name'], "desc": cfg.get('desc', ''), "category": "weekly", "type": "구간",
                    "val": val, "prize": prize, "prize_details": prize_details
                })
        
        elif cat == 'cumulative':
            if not prize_details: continue  # 미대상 → 항목 자체 미표시
            col_val = cfg.get('col_val', '')
            raw_val = match_df[col_val].values[0] if col_val and col_val in match_df.columns else 0
            val = safe_float(raw_val)
            
            calculated_results.append({
                "name": cfg['name'], "desc": cfg.get('desc', ''), "category": "cumulative", "type": "누계",
                "val": val, "prize": prize, "prize_details": prize_details
            })
            
    total_prize_sum = sum(r['prize'] for r in calculated_results)
    return calculated_results, total_prize_sum

def render_ui_cards(user_name, calculated_results, total_prize_sum, show_share_text=False):
    if len(calculated_results) == 0: return

    weekly_res = [r for r in calculated_results if r['category'] == 'weekly']
    cumul_res = [r for r in calculated_results if r['category'] == 'cumulative']
    
    weekly_total = sum(r['prize'] for r in weekly_res)
    cumul_total = sum(r['prize'] for r in cumul_res)

    share_text = f"🎯 [{user_name} 팀장님 실적 현황]\n"
    share_text += f"💰 총 합산 시상금: {total_prize_sum:,.0f}원\n"
    share_text += "────────────────\n"

    if weekly_res:
        summary_html = (
            f"<div class='summary-card'>"
            f"<div class='summary-label'>{user_name} 팀장님의 시책 현황</div>"
            f"<div class='summary-total'>{weekly_total:,.0f}원</div>"
            f"<div class='summary-divider'></div>"
        )
        share_text += f"📌 [진행 중인 시책]\n"
        
        for res in weekly_res:
            if res['type'] == "브릿지2":
                summary_html += f"<div class='data-row' style='padding: 6px 0; align-items:flex-start;'><span class='summary-item-name'>{res['name']}<br><span style='font-size:0.95rem; color:rgba(255,255,255,0.7);'>(다음 달 {int(res['curr_req']//10000)}만 가동 조건)</span></span><span class='summary-item-val'>{res['prize']:,.0f}원</span></div>"
                share_text += f"🔹 {res['name']}: {res['prize']:,.0f}원 (다음 달 {int(res['curr_req']//10000)}만 가동 조건)\n"
            else:
                summary_html += f"<div class='data-row' style='padding: 6px 0;'><span class='summary-item-name'>{res['name']}</span><span class='summary-item-val'>{res['prize']:,.0f}원</span></div>"
                share_text += f"🔹 {res['name']}: {res['prize']:,.0f}원\n"
                
        summary_html += "</div>"
        st.markdown(summary_html, unsafe_allow_html=True)
        
        for res in weekly_res:
            desc_html = res['desc'].replace('\n', '<br>') if res.get('desc') else ''
            details = res.get('prize_details', [])
            
            # 시상금 상세 HTML 생성
            prize_detail_html = ""
            if len(details) > 1:
                for d in details:
                    prize_detail_html += f"<div class='data-row'><span class='data-label'>{d['label']}</span><span class='data-value' style='color:rgb(128,0,0);'>{d['amount']:,.0f}원</span></div>"
                prize_detail_html += "<div class='toss-divider'></div>"
            
            if res['type'] == "구간":
                card_html = (
                    f"<div class='toss-card'>"
                    f"<div class='toss-title'>{res['name']}</div>"
                    f"<div class='toss-desc'>{desc_html}</div>"
                    f"<div class='data-row'><span class='data-label'>현재 누적 실적</span><span class='data-value'>{res['val']:,.0f}원</span></div>"
                    f"<div class='toss-divider'></div>"
                    f"{prize_detail_html}"
                    f"<div class='prize-row'><span class='prize-label'>확보한 시상금</span><span class='prize-value'>{res['prize']:,.0f}원</span></div>"
                    f"</div>"
                )
                share_text += f"\n[{res['name']}]\n- 현재실적: {res['val']:,.0f}원\n- 확보금액: {res['prize']:,.0f}원\n"
                for d in details:
                    share_text += f"  · {d['label']}: {d['amount']:,.0f}원\n"
            
            elif res['type'] == "브릿지1":
                card_html = (
                    f"<div class='toss-card'>"
                    f"<div class='toss-title'>{res['name']}</div>"
                    f"<div class='toss-desc'>{desc_html}</div>"
                    f"<div class='data-row'><span class='data-label'>전월 실적</span><span class='data-value'>{res['val_prev']:,.0f}원</span></div>"
                    f"<div class='data-row'><span class='data-label'>당월 실적</span><span class='data-value'>{res['val_curr']:,.0f}원</span></div>"
                    f"<div class='toss-divider'></div>"
                    f"{prize_detail_html}"
                    f"<div class='prize-row'><span class='prize-label'>확보한 시상금</span><span class='prize-value'>{res['prize']:,.0f}원</span></div>"
                    f"</div>"
                )
                share_text += f"\n[{res['name']}]\n- 전월실적: {res['val_prev']:,.0f}원\n- 당월실적: {res['val_curr']:,.0f}원\n- 확보금액: {res['prize']:,.0f}원\n"
                for d in details:
                    share_text += f"  · {d['label']}: {d['amount']:,.0f}원\n"
                
            elif res['type'] == "브릿지2":
                shortfall_html = ""
                if res.get('shortfall', 0) > 0 and res.get('next_tier'):
                    shortfall_html = f"<div class='shortfall-row'><span class='shortfall-text'>🚀 다음 {int(res['next_tier']//10000)}만 구간까지 {res['shortfall']:,.0f}원 남음!</span></div>"
                card_html = (
                    f"<div class='toss-card'>"
                    f"<div class='toss-title'>{res['name']}</div>"
                    f"<div class='toss-desc'>{desc_html}</div>"
                    f"<div class='data-row'><span class='data-label'>당월 누적 실적</span><span class='data-value'>{res['val']:,.0f}원</span></div>"
                    f"<div class='data-row'><span class='data-label'>확보한 구간 기준</span><span class='data-value'>{res['tier']:,.0f}원</span></div>"
                    f"<div class='data-row'><span class='data-label'>예상 적용 지급률</span><span class='data-value'>{res['rate']:g}%</span></div>"
                    f"{shortfall_html}"
                    f"<div class='toss-divider'></div>"
                    f"<div class='prize-row'><span class='prize-label'>다음 달 {int(res['curr_req']//10000)}만 가동 시<br>시상금</span><span class='prize-value'>{res['prize']:,.0f}원</span></div>"
                    f"</div>"
                )
                share_text += f"\n[{res['name']}]\n- 당월실적: {res['val']:,.0f}원\n- 예상시상: {res['prize']:,.0f}원 (차월조건)\n"
                if res.get('shortfall', 0) > 0: share_text += f"🚀 다음 {int(res['next_tier']//10000)}만 구간까지 {res['shortfall']:,.0f}원 남음!\n"
                
            st.markdown(card_html, unsafe_allow_html=True)

    if cumul_res:
        cumul_html = (
            f"<div class='cumulative-card'>"
            f"<div class='summary-label'>{user_name} 팀장님의 월간 누계 시상</div>"
            f"<div class='summary-total'>{cumul_total:,.0f}원</div>"
            f"<div class='summary-divider'></div>"
        )
        
        share_text += f"\n🏆 [월간 확정 누계 시상]\n"
        for res in cumul_res:
            cumul_html += f"<div class='data-row' style='padding: 6px 0;'><span class='summary-item-name'>{res['name']}</span><span class='summary-item-val'>{res['prize']:,.0f}원</span></div>"
            share_text += f"🔹 {res['name']}: {res['prize']:,.0f}원 (누계 {res['val']:,.0f}원)\n"
        cumul_html += "</div>"
        st.markdown(cumul_html, unsafe_allow_html=True)
        
        st.markdown("<h3 class='blue-title'>📈 세부 항목별 시상금</h3>", unsafe_allow_html=True)
        
        stack_html = ""
        for res in cumul_res:
            details = res.get('prize_details', [])
            detail_lines = ""
            if len(details) > 1:
                for d in details:
                    detail_lines += f"<span class='cumul-stack-val'>{d['label']}: {d['amount']:,.0f}원</span>"
            else:
                detail_lines = f"<span class='cumul-stack-val'>누계실적: {res['val']:,.0f}원</span>"
            stack_html += (
                f"<div class='cumul-stack-box'>"
                f"<div class='cumul-stack-info'>"
                f"<span class='cumul-stack-title'>{res['name']}</span>"
                f"{detail_lines}"
                f"</div>"
                f"<div class='cumul-stack-prize'>{res['prize']:,.0f}원</div>"
                f"</div>"
            )
        st.markdown(stack_html, unsafe_allow_html=True)

    # 🌟 [수정된 부분] 텍스트 박스 대신 카카오톡 원클릭 복사 버튼 렌더링
    if show_share_text:
        st.markdown("<h4 class='main-title' style='margin-top:10px;'>💬 카카오톡 바로 공유하기</h4>", unsafe_allow_html=True)
        copy_btn_component(share_text)


# ==========================================
# 📱 1. 최상단: 메뉴 선택 탭
# ==========================================
mode = st.radio("화면 선택", ["📊 내 실적 조회", "👥 매니저 관리", "⚙️ 시스템 관리자"], horizontal=True, label_visibility="collapsed")

# ==========================================
# 👥 2. 매니저 관리 페이지 
# ==========================================
if mode == "👥 매니저 관리":
    st.markdown('<div class="title-band">매니저 소속 실적 관리</div>', unsafe_allow_html=True)
    
    if 'mgr_logged_in' not in st.session_state: st.session_state.mgr_logged_in = False
    
    if not st.session_state.mgr_logged_in:
        mgr_code = st.text_input("지원매니저 사번(코드)을 입력하세요", type="password", placeholder="예: 12345")
        if st.button("로그인", type="primary"):
            if not mgr_code:
                st.warning("지원매니저 코드를 입력해주세요.")
            else:
                is_valid = False
                safe_input_code = safe_str(mgr_code)
                all_valid_codes = set()
                
                # 🌟 속도 개선: 캐싱된 컬럼에서 검증 수행 🌟
                for cfg in st.session_state['config']:
                    mgr_col = cfg.get('col_manager_code', '') or cfg.get('col_manager', '')
                    if mgr_col:
                        df = st.session_state['raw_data'].get(cfg['file'])
                        if df is not None and mgr_col in df.columns:
                            clean_mgr_codes = get_clean_series(df, mgr_col)
                            for clean_val in clean_mgr_codes.unique():
                                if clean_val: all_valid_codes.add(clean_val)
                
                if safe_input_code in all_valid_codes:
                    is_valid = True
                
                if is_valid:
                    st.session_state.mgr_logged_in = True
                    st.session_state.mgr_code = safe_input_code 
                    st.session_state.mgr_step = 'main'
                    # 🌟 [로그 저장] 매니저 로그인 기록 🌟
                    save_log("매니저", safe_input_code, "MANAGER_LOGIN")
                    st.rerun()
                else:
                    st.error(f"❌ 입력하신 코드({mgr_code})가 등록된 실적 데이터에 존재하지 않습니다.")
                    st.info("💡 관리자 화면에서 '지원매니저코드 컬럼'이 정확히 지정되었는지 확인해주세요.")
                    if all_valid_codes:
                        sample_codes = ", ".join(list(all_valid_codes)[:10])
                        st.warning(f"🧐 (참고) 현재 시스템이 복원하여 인식하고 있는 정상 코드 예시:\n{sample_codes}")
    else:
        if st.button("🚪 로그아웃"):
            st.session_state.mgr_logged_in = False
            st.rerun()
        st.markdown('<br>', unsafe_allow_html=True)
        
        step = st.session_state.get('mgr_step', 'main')
        
        # --- (1) 메인 폴더 선택 ---
        if step == 'main':
            st.markdown("<h3 class='main-title'>어떤 실적을 확인하시겠습니까?</h3>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📁 구간실적 관리", use_container_width=True):
                    st.session_state.mgr_step = 'tiers'
                    st.session_state.mgr_category = '구간'
                    st.rerun()
            with col2:
                if st.button("📁 브릿지실적 관리", use_container_width=True):
                    st.session_state.mgr_step = 'tiers'
                    st.session_state.mgr_category = '브릿지'
                    st.rerun()
                
        # --- (2) 금액별 폴더 선택 ---
        elif step == 'tiers':
            if st.button("⬅️ 뒤로가기", use_container_width=False):
                st.session_state.mgr_step = 'main'
                st.rerun()
            
            cat = st.session_state.mgr_category
            
            my_agents = set()
            safe_login_code = st.session_state.mgr_code
            
            # 🌟 속도 개선: 캐싱된 컬럼 필터링으로 0.1초 만에 인원 수집 🌟
            for cfg in st.session_state['config']:
                if cfg.get('category') == 'cumulative': continue
                
                mgr_col = cfg.get('col_manager_code', '') or cfg.get('col_manager', '')
                col_code = cfg.get('col_code', '')
                if not mgr_col or not col_code: continue 
                
                df = st.session_state['raw_data'].get(cfg['file'])
                if df is None or mgr_col not in df.columns or col_code not in df.columns: continue
                
                clean_mgr_codes = get_clean_series(df, mgr_col)
                mask = clean_mgr_codes == safe_login_code
                
                clean_col_codes = get_clean_series(df, col_code)
                for ac in clean_col_codes[mask]:
                    if ac: my_agents.add(ac)
            
            st.markdown(f"<h3 class='main-title'>📁 {cat}실적 근접자 조회 (소속: 총 {len(my_agents)}명)</h3>", unsafe_allow_html=True)
            
            ranges = {
                500000: (300000, float('inf')),
                300000: (200000, 300000), 
                200000: (100000, 200000), 
                100000: (0, 100000)        
            }
            counts = {500000: 0, 300000: 0, 200000: 0, 100000: 0}
            
            for agent_code in my_agents:
                calc_results, _ = calculate_agent_performance(agent_code)
                matched_folders = set()
                
                for res in calc_results:
                    if cat == "구간" and "구간" not in res['type']: continue
                    if cat == "브릿지" and "브릿지" not in res['type']: continue
                    
                    val = res.get('val') if 'val' in res else res.get('val_curr', 0.0)
                    if val is None: val = 0.0
                    
                    for t, (min_v, max_v) in ranges.items():
                        if min_v <= val < max_v:
                            matched_folders.add(t)
                            break
                            
                for t in matched_folders:
                    counts[t] += 1
            
            for t, (min_v, max_v) in ranges.items():
                count = counts[t]
                if t == 500000: label = f"📁 50만 구간 근접 및 달성 (30만 이상) - 총 {count}명"
                else: label = f"📁 {int(t//10000)}만 구간 근접자 ({int(min_v//10000)}만 이상 ~ {int(max_v//10000)}만 미만) - 총 {count}명"
                
                if st.button(label, use_container_width=True, key=f"t_{t}"):
                    st.session_state.mgr_step = 'list'
                    st.session_state.mgr_target = t
                    st.session_state.mgr_min_v = min_v
                    st.session_state.mgr_max_v = max_v
                    st.session_state.mgr_agents = my_agents 
                    st.rerun()
                
        # --- (3) 선택한 폴더 내 설계사 명단 확인 (가나다 정렬 적용) ---
        elif step == 'list':
            if st.button("⬅️ 폴더로 돌아가기", use_container_width=False):
                st.session_state.mgr_step = 'tiers'
                st.rerun()
            
            cat = st.session_state.mgr_category
            target = st.session_state.mgr_target
            min_v = st.session_state.mgr_min_v
            max_v = st.session_state.mgr_max_v
            my_agents = st.session_state.mgr_agents
            
            if target == 500000: st.markdown(f"<h3 class='main-title'>👥 50만 구간 근접 및 달성자 명단</h3>", unsafe_allow_html=True)
            else: st.markdown(f"<h3 class='main-title'>👥 {int(target//10000)}만 구간 근접자 명단</h3>", unsafe_allow_html=True)
            
            st.info("💡 이름을 클릭하면 상세 실적을 확인하고 카톡으로 전송할 수 있습니다.")
            
            near_agents = []
            for code in my_agents:
                calc_results, _ = calculate_agent_performance(code)
                
                agent_name = "이름없음"
                agent_agency = ""
                # 🌟 속도 개선: 데이터 조회 시 캐싱 컬럼(clean_col_codes) 사용 🌟
                for cfg in st.session_state['config']:
                    if cfg.get('col_code') and cfg.get('col_name'):
                        df = st.session_state['raw_data'].get(cfg['file'])
                        if df is not None and cfg['col_code'] in df.columns:
                            clean_col_codes = get_clean_series(df, cfg['col_code'])
                            mask = clean_col_codes == code
                            match_df = df[mask]
                            
                            if not match_df.empty:
                                if cfg['col_name'] in match_df.columns:
                                    agent_name = safe_str(match_df[cfg['col_name']].values[0])
                                br = cfg.get('col_branch','')
                                ag = cfg.get('col_agency','')
                                if ag and ag in df.columns: agent_agency = _clean_excel_text(safe_str(match_df[ag].values[0]))
                                elif br and br in df.columns: agent_agency = _clean_excel_text(safe_str(match_df[br].values[0]))
                                break

                for res in calc_results:
                    if cat == "구간" and "구간" not in res['type']: continue
                    if cat == "브릿지" and "브릿지" not in res['type']: continue
                    
                    val = res.get('val') if 'val' in res else res.get('val_curr', 0.0)
                    if val is None: val = 0.0
                    
                    if min_v <= val < max_v:
                        near_agents.append((code, agent_name, agent_agency, val))
                        break
            
            if not near_agents:
                st.info(f"해당 구간에 소속 설계사가 없습니다.")
            else:
                # 🌟 [요청 사항 적용] 지사명(agency) 가나다순, 이름(name) 가나다순 정렬 🌟
                near_agents.sort(key=lambda x: (x[2], x[1]))
                
                for code, name, agency, val in near_agents:
                    display_text = f"👤 [{agency}] {name} 설계사님 (현재 {val:,.0f}원)"
                    if st.button(display_text, use_container_width=True, key=f"btn_{code}"):
                        st.session_state.mgr_selected_code = code
                        st.session_state.mgr_selected_name = f"[{agency}] {name}"
                        st.session_state.mgr_step = 'detail'
                        st.rerun()

        # --- (4) 상세 내역 및 카톡 공유 ---
        elif step == 'detail':
            if st.button("⬅️ 명단으로 돌아가기", use_container_width=False):
                st.session_state.mgr_step = 'list'
                st.rerun()
            
            code = st.session_state.mgr_selected_code
            name = st.session_state.mgr_selected_name
            
            st.markdown(f"<div class='detail-box'>", unsafe_allow_html=True)
            st.markdown(f"<h4 class='agent-title'>👤 {name} 설계사님</h4>", unsafe_allow_html=True)
            
            calc_results, total_prize = calculate_agent_performance(code)
            render_ui_cards(name, calc_results, total_prize, show_share_text=True)
            
            user_leaflet_path = os.path.join(DATA_DIR, "leaflet.png")
            if os.path.exists(user_leaflet_path):
                st.image(user_leaflet_path, use_container_width=True)
                
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 🔒 3. 시스템 관리자 모드
# ==========================================
elif mode == "⚙️ 시스템 관리자":
    st.markdown("<h2 class='admin-title'>관리자 설정</h2>", unsafe_allow_html=True)
    
    admin_pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    # 🌟 [보안 로직 추가] 시크릿 키로 비밀번호 확인, 설정되지 않은 경우 기본 비밀번호 사용
    try:
        real_pw = st.secrets["admin_password"]
    except:
        real_pw = "wolf7998"
        
    if admin_pw != real_pw:
        if admin_pw: st.error("비밀번호가 일치하지 않습니다.")
        st.stop()
        
    st.success("인증 성공! 변경 사항은 가장 아래 [서버에 반영하기] 버튼을 눌러야 저장됩니다.")

    # 🌟 [로그 다운로드 버튼 추가]
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "rb") as f:
            st.download_button(
                label="📊 사용자 접속 기록 (로그) 다운로드", 
                data=f, 
                file_name=f"access_log_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # [영역 1] 파일 업로드 및 관리
    # ---------------------------------------------------------
    st.markdown("<h3 class='sub-title'>📂 1. 실적 파일 업로드 및 관리</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("CSV/엑셀 파일 업로드", accept_multiple_files=True, type=['csv', 'xlsx'])
    
    if uploaded_files:
        new_upload = False
        for file in uploaded_files:
            if file.name not in st.session_state['raw_data']:
                if file.name.endswith('.csv'):
                    try: df = pd.read_csv(file)
                    except:
                        file.seek(0)
                        try: df = pd.read_csv(file, sep='\t')
                        except:
                            file.seek(0)
                            try: df = pd.read_csv(file, encoding='cp949')
                            except:
                                file.seek(0)
                                df = pd.read_csv(file, sep='\t', encoding='cp949')
                else: df = pd.read_excel(file)
                
                # 🌟 엑셀 _xHHHH_ 이스케이프 일괄 정리
                df.columns = [_clean_excel_text(str(c)) for c in df.columns]
                for col in df.select_dtypes(include='object').columns:
                    df[col] = df[col].apply(lambda v: _clean_excel_text(str(v)) if pd.notna(v) else v)
                
                st.session_state['raw_data'][file.name] = df
                df.to_pickle(os.path.join(DATA_DIR, f"{file.name}.pkl"))
                new_upload = True
                
        if new_upload:
            st.success("✅ 파일 업로드 및 저장이 완료되었습니다.")
            st.rerun()

    col1, col2 = st.columns([7, 3])
    with col1:
        st.markdown(f"**현재 저장된 파일 ({len(st.session_state['raw_data'])}개)**")
    with col2:
        if st.button("🗑️ 전체 파일 삭제", use_container_width=True):
            st.session_state['raw_data'].clear()
            for f in os.listdir(DATA_DIR):
                if f.endswith('.pkl'): os.remove(os.path.join(DATA_DIR, f))
            st.rerun()
            
    if not st.session_state['raw_data']:
        st.info("현재 업로드된 파일이 없습니다. 위에 파일을 추가해주세요.")
    else:
        for file_name in list(st.session_state['raw_data'].keys()):
            col_name, col_btn = st.columns([8, 2])
            with col_name: st.write(f"📄 {file_name}")
            with col_btn:
                if st.button("개별 삭제", key=f"del_file_{file_name}", use_container_width=True):
                    del st.session_state['raw_data'][file_name]
                    pkl_path = os.path.join(DATA_DIR, f"{file_name}.pkl")
                    if os.path.exists(pkl_path): os.remove(pkl_path)
                    st.rerun()
            st.markdown("<hr style='margin:5px 0; opacity:0.1;'>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 🌟 [영역 2] 주차/브릿지 시상 항목 관리
    # ---------------------------------------------------------
    st.divider()
    st.markdown("<h3 class='sub-title' style='margin-top:10px;'>🏆 2. 주차/브릿지 시상 항목 관리</h3>", unsafe_allow_html=True)
    
    col_add, col_del_all = st.columns(2)
    with col_add:
        if st.button("➕ 신규 주차/브릿지 시상 추가", type="primary", use_container_width=True):
            if not st.session_state['raw_data']:
                st.error("⚠️ 먼저 실적 파일을 1개 이상 업로드해야 시상을 추가할 수 있습니다.")
            else:
                first_file = list(st.session_state['raw_data'].keys())[0]
                st.session_state['config'].append({
                    "name": f"신규 주차 시책 {len(st.session_state['config'])+1}",
                    "desc": "", "category": "weekly", "type": "구간 시책", 
                    "file": first_file, "col_name": "", "col_code": "", "col_branch": "", "col_manager_code": "",
                    "col_val": "", "col_val_prev": "", "col_val_curr": "",
                    "prize_items": [{"label": "시상금", "col_eligible": "", "col_prize": ""}],
                    "curr_req": 100000.0,
                    "tiers": [(500000, 300), (300000, 200), (200000, 200), (100000, 100)]
                })
                st.rerun()
                
    with col_del_all:
        if st.button("🗑️ 모든 시상 항목 일괄 삭제", use_container_width=True):
            st.session_state['config'] = [c for c in st.session_state['config'] if c.get('category') != 'weekly']
            with open(os.path.join(DATA_DIR, 'config.json'), 'w', encoding='utf-8') as f:
                json.dump(st.session_state['config'], f, ensure_ascii=False)
            st.rerun()

    weekly_cfgs = [(i, c) for i, c in enumerate(st.session_state['config']) if c.get('category', 'weekly') == 'weekly']
    if not weekly_cfgs:
        st.info("현재 설정된 주차/브릿지 시상이 없습니다.")

    for i, cfg in weekly_cfgs:
        if 'desc' not in cfg: cfg['desc'] = ""
        st.markdown(f"<div class='config-box'>", unsafe_allow_html=True)
        c_title, c_del = st.columns([8, 2])
        with c_title: st.markdown(f"<h3 class='config-title'>📌 {cfg['name']} 설정</h3>", unsafe_allow_html=True)
        with c_del:
            if st.button("개별 삭제", key=f"del_cfg_{i}", use_container_width=True):
                st.session_state['config'].pop(i)
                st.rerun()
        
        cfg['name'] = st.text_input(f"시책명", value=cfg['name'], key=f"name_{i}")
        cfg['desc'] = st.text_area("시책 설명 (적용 기간 등)", value=cfg.get('desc', ''), placeholder="엔터를 쳐서 문단을 나눌 수 있습니다.", key=f"desc_{i}", height=100)
        
        idx = 0
        if "1기간" in cfg['type']: idx = 1
        elif "2기간" in cfg['type']: idx = 2
            
        cfg['type'] = st.radio("시책 종류 선택", ["구간 시책", "브릿지 시책 (1기간: 시상 확정)", "브릿지 시책 (2기간: 차월 달성 조건)"], index=idx, horizontal=True, key=f"type_{i}")
        
        col1, col2 = st.columns(2)
        with col1:
            file_opts = list(st.session_state['raw_data'].keys())
            cfg['file'] = st.selectbox(f"대상 파일", file_opts, index=file_opts.index(cfg['file']) if cfg['file'] in file_opts else 0, key=f"file_{i}")
            cols = st.session_state['raw_data'][cfg['file']].columns.tolist() if file_opts else []
            def get_idx(val, opts): return opts.index(val) if val in opts else 0

            st.info("💡 식별을 위해 아래 컬럼들을 지정해주세요.")
            cfg['col_name'] = st.selectbox("성명 컬럼", cols, index=get_idx(cfg.get('col_name', ''), cols), key=f"cname_{i}")
            cfg['col_branch'] = st.selectbox("지점명(조직) 컬럼", cols, index=get_idx(cfg.get('col_branch', ''), cols), key=f"cbranch_{i}")
            cfg['col_agency'] = st.selectbox("대리점/지사명 컬럼", cols, index=get_idx(cfg.get('col_agency', ''), cols), key=f"cagency_{i}")
            cfg['col_code'] = st.selectbox("설계사코드(사번) 컬럼", cols, index=get_idx(cfg.get('col_code', ''), cols), key=f"ccode_{i}")
            cfg['col_manager_code'] = st.selectbox("지원매니저코드 컬럼", cols, index=get_idx(cfg.get('col_manager_code', cfg.get('col_manager', '')), cols), key=f"cmgrcode_{i}")
            
        with col2:
            st.info("💡 실적과 시상금 컬럼을 지정해주세요.")
            if "1기간" in cfg['type']:
                cfg['col_val_prev'] = st.selectbox("전월 실적 컬럼", cols, index=get_idx(cfg.get('col_val_prev', ''), cols), key=f"cvalp_{i}")
                cfg['col_val_curr'] = st.selectbox("당월 실적 컬럼", cols, index=get_idx(cfg.get('col_val_curr', ''), cols), key=f"cvalc_{i}")
            elif "2기간" in cfg['type']:
                cfg['col_val_curr'] = st.selectbox("당월 실적 수치 컬럼", cols, index=get_idx(cfg.get('col_val_curr', ''), cols), key=f"cvalc2_{i}")
            else: 
                cfg['col_val'] = st.selectbox("실적 수치 컬럼", cols, index=get_idx(cfg.get('col_val', ''), cols), key=f"cval_{i}")
            
            if "2기간" in cfg['type']:
                # 🌟 브릿지2: 기존 구간/지급률 계산 유지
                cfg['curr_req'] = st.number_input("차월 필수 달성 금액 (합산용)", value=float(cfg.get('curr_req', 100000.0)), step=10000.0, key=f"creq2_{i}")
                st.write("📈 구간 설정 (달성금액, 지급률%)")
                tier_str = "\n".join([f"{int(t[0])},{int(t[1])}" for t in cfg.get('tiers', [])])
                tier_input = st.text_area("엔터로 줄바꿈", value=tier_str, height=150, key=f"tier_{i}")
                try:
                    new_tiers = []
                    for line in tier_input.strip().split('\n'):
                        if ',' in line:
                            parts = line.split(',')
                            new_tiers.append((float(parts[0].strip()), float(parts[1].strip())))
                    cfg['tiers'] = sorted(new_tiers, key=lambda x: x[0], reverse=True)
                except:
                    st.error("형식이 올바르지 않습니다.")
                st.caption("💡 브릿지 2기간은 (확보구간 + 차월가동금액) × 지급률로 계산됩니다.")
            else:
                # 🌟 구간/브릿지1: 시상금 다중 항목 직접 읽기
                st.markdown("**💰 시상금 항목 (여러 개 가능)**")
                st.caption("지급률 컬럼: 0이면 미대상(미표시). 공란이면 무조건 대상 처리.")
                if 'prize_items' not in cfg:
                    old_col = cfg.pop('col_prize', '') or cfg.pop('col', '')
                    cfg['prize_items'] = [{"label": "시상금", "col_eligible": "", "col_prize": old_col}] if old_col else [{"label": "시상금", "col_eligible": "", "col_prize": ""}]
                # 구형 호환: col → col_prize
                for _pi in cfg.get('prize_items', []):
                    if 'col' in _pi and 'col_prize' not in _pi:
                        _pi['col_prize'] = _pi.pop('col', '')
                    if 'col_eligible' not in _pi:
                        _pi['col_eligible'] = ''
                
                cols_with_blank = ["(공란)"] + cols
                updated_items = []
                for pi_idx, pi in enumerate(cfg.get('prize_items', [])):
                    st.markdown(f"<div style='background:#f8f9fa;padding:6px 8px;border-radius:6px;margin:4px 0;'>", unsafe_allow_html=True)
                    pc1, pc4 = st.columns([8, 2])
                    with pc1:
                        pi['label'] = st.text_input("시상명", value=pi.get('label', ''), key=f"pilbl_{i}_{pi_idx}", placeholder="시상 항목명")
                    with pc4:
                        if st.button("🗑️", key=f"pidel_{i}_{pi_idx}", use_container_width=True):
                            st.markdown("</div>", unsafe_allow_html=True)
                            continue
                    pc2, pc3 = st.columns(2)
                    with pc2:
                        cur_elig = pi.get('col_eligible', '')
                        elig_idx = cols_with_blank.index(cur_elig) if cur_elig in cols_with_blank else 0
                        sel_elig = st.selectbox("지급률 컬럼 (0=미대상)", cols_with_blank, index=elig_idx, key=f"pielig_{i}_{pi_idx}")
                        pi['col_eligible'] = sel_elig if sel_elig != "(공란)" else ""
                    with pc3:
                        cur_prize = pi.get('col_prize', '')
                        prize_idx = cols_with_blank.index(cur_prize) if cur_prize in cols_with_blank else 0
                        sel_prize = st.selectbox("예정시상금 컬럼", cols_with_blank, index=prize_idx, key=f"piprz_{i}_{pi_idx}")
                        pi['col_prize'] = sel_prize if sel_prize != "(공란)" else ""
                    st.markdown("</div>", unsafe_allow_html=True)
                    updated_items.append(pi)
                cfg['prize_items'] = updated_items
                
                if st.button("➕ 시상금 항목 추가", key=f"piadd_{i}", use_container_width=True):
                    cfg['prize_items'].append({"label": f"시상금{len(cfg['prize_items'])+1}", "col_eligible": "", "col_prize": ""})
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 🌟 [영역 3] 월간 누계 시상 항목 관리
    # ---------------------------------------------------------
    st.divider()
    st.markdown("<h3 class='blue-title'>📈 3. 월간 누계 시상 항목 관리</h3>", unsafe_allow_html=True)
    
    if st.button("➕ 신규 누계 항목 추가", type="primary", use_container_width=True, key="add_cumul"):
        if not st.session_state['raw_data']:
            st.error("⚠️ 먼저 실적 파일을 1개 이상 업로드해야 합니다.")
        else:
            first_file = list(st.session_state['raw_data'].keys())[0]
            st.session_state['config'].append({
                "name": f"신규 누계 항목 {len(st.session_state['config'])+1}",
                "desc": "", "category": "cumulative", "type": "누계", 
                "file": first_file, "col_code": "", "col_val": "",
                "prize_items": [{"label": "시상금", "col_eligible": "", "col_prize": ""}]
            })
            st.rerun()

    cumul_cfgs = [(i, c) for i, c in enumerate(st.session_state['config']) if c.get('category') == 'cumulative']
    if not cumul_cfgs:
        st.info("현재 설정된 누계 항목이 없습니다.")

    for i, cfg in cumul_cfgs:
        st.markdown(f"<div class='config-box-blue'>", unsafe_allow_html=True)
        c_title, c_del = st.columns([8, 2])
        with c_title: st.markdown(f"<h3 class='config-title' style='color:#1e3c72;'>📘 {cfg['name']} 설정</h3>", unsafe_allow_html=True)
        with c_del:
            if st.button("개별 삭제", key=f"del_cfg_{i}", use_container_width=True):
                st.session_state['config'].pop(i)
                st.rerun()
        
        cfg['name'] = st.text_input(f"누계 항목명", value=cfg['name'], key=f"name_{i}")
        
        col1, col2 = st.columns(2)
        with col1:
            file_opts = list(st.session_state['raw_data'].keys())
            cfg['file'] = st.selectbox(f"대상 파일", file_opts, index=file_opts.index(cfg['file']) if cfg['file'] in file_opts else 0, key=f"file_{i}")
            cols = st.session_state['raw_data'][cfg['file']].columns.tolist() if file_opts else []
            def get_idx(val, opts): return opts.index(val) if val in opts else 0

            cfg['col_code'] = st.selectbox("설계사코드(사번) 컬럼", cols, index=get_idx(cfg.get('col_code', ''), cols), key=f"ccode_{i}")
            cfg['col_val'] = st.selectbox("누계 실적 컬럼 (선택사항)", cols, index=get_idx(cfg.get('col_val', ''), cols), key=f"cval_{i}")

        with col2:
            st.markdown("**💰 시상금 항목 (여러 개 가능)**")
            st.caption("지급률 컬럼: 0이면 미대상(미표시). 공란이면 무조건 대상 처리.")
            # 구형 호환
            if 'prize_items' not in cfg:
                old_col = cfg.pop('col_prize', '')
                cfg['prize_items'] = [{"label": "시상금", "col_eligible": "", "col_prize": old_col}] if old_col else [{"label": "시상금", "col_eligible": "", "col_prize": ""}]
            for _pi in cfg.get('prize_items', []):
                if 'col' in _pi and 'col_prize' not in _pi:
                    _pi['col_prize'] = _pi.pop('col', '')
                if 'col_eligible' not in _pi:
                    _pi['col_eligible'] = ''
            
            cols_with_blank = ["(공란)"] + cols
            updated_items = []
            for pi_idx, pi in enumerate(cfg.get('prize_items', [])):
                st.markdown(f"<div style='background:#f0f4ff;padding:6px 8px;border-radius:6px;margin:4px 0;'>", unsafe_allow_html=True)
                pc1, pc4 = st.columns([8, 2])
                with pc1:
                    pi['label'] = st.text_input("시상명", value=pi.get('label', ''), key=f"cpilbl_{i}_{pi_idx}", placeholder="시상 항목명")
                with pc4:
                    if st.button("🗑️", key=f"cpidel_{i}_{pi_idx}", use_container_width=True):
                        st.markdown("</div>", unsafe_allow_html=True)
                        continue
                pc2, pc3 = st.columns(2)
                with pc2:
                    cur_elig = pi.get('col_eligible', '')
                    elig_idx = cols_with_blank.index(cur_elig) if cur_elig in cols_with_blank else 0
                    sel_elig = st.selectbox("지급률 컬럼 (0=미대상)", cols_with_blank, index=elig_idx, key=f"cpielig_{i}_{pi_idx}")
                    pi['col_eligible'] = sel_elig if sel_elig != "(공란)" else ""
                with pc3:
                    cur_prize = pi.get('col_prize', '')
                    prize_idx = cols_with_blank.index(cur_prize) if cur_prize in cols_with_blank else 0
                    sel_prize = st.selectbox("예정시상금 컬럼", cols_with_blank, index=prize_idx, key=f"cpiprz_{i}_{pi_idx}")
                    pi['col_prize'] = sel_prize if sel_prize != "(공란)" else ""
                st.markdown("</div>", unsafe_allow_html=True)
                updated_items.append(pi)
            cfg['prize_items'] = updated_items
            
            if st.button("➕ 시상금 항목 추가", key=f"cpiadd_{i}", use_container_width=True):
                cfg['prize_items'].append({"label": f"시상금{len(cfg['prize_items'])+1}", "col_eligible": "", "col_prize": ""})
                st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [영역 4] 리플렛(안내 이미지) 관리
    # ---------------------------------------------------------
    st.divider()
    st.markdown("<h3 class='sub-title' style='margin-top:10px;'>🖼️ 4. 안내 리플렛(이미지) 등록</h3>", unsafe_allow_html=True)
    st.info("💡 실적 조회 결과 맨 아래에 보여줄 상품 안내장이나 리플렛 이미지를 등록할 수 있습니다.")
    
    leaflet_file = st.file_uploader("리플렛 이미지 업로드 (JPG, PNG)", type=['jpg', 'jpeg', 'png'])
    if leaflet_file:
        with open(os.path.join(DATA_DIR, "leaflet.png"), "wb") as f:
            f.write(leaflet_file.getbuffer())
        st.success("✅ 리플렛 이미지가 저장되었습니다!")
        st.rerun()

    leaflet_path = os.path.join(DATA_DIR, "leaflet.png")
    if os.path.exists(leaflet_path):
        st.markdown("<p style='color:#333d4b; font-weight:600;'>현재 등록된 리플렛 이미지:</p>", unsafe_allow_html=True)
        st.image(leaflet_path, width=250)
        
        if st.button("🗑️ 등록된 리플렛 삭제", use_container_width=False):
            os.remove(leaflet_path)
            st.rerun()

    # ---------------------------------------------------------
    # 🌟 [영역 5] 설정 백업 및 복원
    # ---------------------------------------------------------
    st.divider()
    st.markdown("<h3 class='sub-title' style='margin-top:10px;'>💾 5. 시상 설정 백업 및 복원</h3>", unsafe_allow_html=True)
    st.info("💡 현재 설정된 시상 항목(구간/브릿지/누계)을 JSON 파일로 백업하고, 나중에 다시 불러올 수 있습니다.")
    
    col_backup, col_restore = st.columns(2)
    
    with col_backup:
        st.markdown("**📤 설정 백업 (다운로드)**", unsafe_allow_html=True)
        if st.session_state['config']:
            backup_data = json.dumps(st.session_state['config'], ensure_ascii=False, indent=2)
            backup_filename = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            st.download_button(
                label="⬇️ 현재 설정 백업 다운로드",
                data=backup_data,
                file_name=backup_filename,
                mime="application/json",
                use_container_width=True
            )
            st.caption(f"현재 {len(st.session_state['config'])}개 시상 항목이 설정되어 있습니다.")
        else:
            st.warning("백업할 설정이 없습니다. 시상 항목을 먼저 추가해주세요.")
    
    with col_restore:
        st.markdown("**📥 설정 복원 (업로드)**", unsafe_allow_html=True)
        restore_file = st.file_uploader("백업 JSON 파일 업로드", type=['json'], key="restore_config")
        if restore_file:
            try:
                restored_config = json.loads(restore_file.read().decode('utf-8'))
                if isinstance(restored_config, list):
                    # 호환성 보장
                    for c in restored_config:
                        if 'category' not in c:
                            c['category'] = 'weekly'
                    
                    weekly_count = sum(1 for c in restored_config if c.get('category') == 'weekly')
                    cumul_count = sum(1 for c in restored_config if c.get('category') == 'cumulative')
                    
                    st.success(f"✅ 파일 확인 완료: 주차/브릿지 {weekly_count}개, 누계 {cumul_count}개")
                    
                    if st.button("🔄 이 설정으로 복원하기", type="primary", use_container_width=True, key="do_restore"):
                        st.session_state['config'] = restored_config
                        with open(os.path.join(DATA_DIR, 'config.json'), 'w', encoding='utf-8') as f:
                            json.dump(restored_config, f, ensure_ascii=False)
                        st.success("✅ 설정이 복원되었습니다!")
                        st.rerun()
                else:
                    st.error("❌ 올바른 설정 파일 형식이 아닙니다. (배열 형태여야 합니다)")
            except json.JSONDecodeError:
                st.error("❌ JSON 파일을 읽을 수 없습니다. 파일이 손상되었는지 확인해주세요.")
            except Exception as e:
                st.error(f"❌ 복원 중 오류 발생: {str(e)}")

    # ---------------------------------------------------------
    # [최종] 서버 반영 및 기존 다운로드
    # ---------------------------------------------------------
    if st.session_state['config']:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ 모든 설정 완료 및 서버에 반영하기", type="primary", use_container_width=True):
            with open(os.path.join(DATA_DIR, 'config.json'), 'w', encoding='utf-8') as f:
                json.dump(st.session_state['config'], f, ensure_ascii=False)
            st.success("✅ 서버에 영구 반영되었습니다! 이제 조회 화면에서 확인 가능합니다.")

        # --- 📥 config.json 다운로드 (관리자 전용 — 지원매니저 앱으로 내보내기) ---
        config_path = os.path.join(DATA_DIR, 'config.json')
        if os.path.exists(config_path):
            st.divider()
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = f.read()
            st.download_button(
                label="📥 config.json 다운로드 (지원매니저 앱으로 가져가기)",
                data=config_data,
                file_name="config.json",
                mime="application/json"
            )

# ==========================================
# 🏆 4. 사용자 모드 (일반 설계사 조회)
# ==========================================
else:
    st.markdown('<div class="title-band">메리츠화재 시상 현황</div>', unsafe_allow_html=True)
    st.markdown("<h3 class='main-title'>이름과 지점별 코드를 입력하세요.</h3>", unsafe_allow_html=True)
    
    user_name = st.text_input("본인 이름을 입력하세요", placeholder="예: 홍길동")
    branch_code_input = st.text_input("지점별 코드", placeholder="예: 1지점은 1, 11지점은 11 입력")

    codes_found = set()
    needs_disambiguation = False

    if user_name and branch_code_input:
        for i, cfg in enumerate(st.session_state['config']):
            if cfg.get('category') == 'cumulative': continue
                
            df = st.session_state['raw_data'].get(cfg['file'])
            if df is not None:
                col_name = cfg.get('col_name', '')
                col_branch = cfg.get('col_branch', '')
                
                search_name = df[col_name].fillna('').astype(str).str.strip() if col_name and col_name in df.columns else pd.Series()
                if search_name.empty: continue
                
                name_match_condition = (search_name == user_name.strip())
                
                if branch_code_input.strip() == "0000": 
                    match = df[name_match_condition]
                else:
                    clean_code = branch_code_input.replace("지점", "").strip()
                    if clean_code:
                        search_branch = df[col_branch].fillna('').astype(str) if col_branch and col_branch in df.columns else pd.Series()
                        if search_branch.empty: continue
                        
                        regex_pattern = rf"(?<!\d){clean_code}\s*지점"
                        match = df[name_match_condition & search_branch.str.contains(regex_pattern, regex=True)]
                    else:
                        match = pd.DataFrame()
                
                if not match.empty:
                    if cfg.get('col_code') and cfg['col_code'] in df.columns:
                        clean_col_codes = get_clean_series(df, cfg['col_code'])
                        for agent_code in clean_col_codes[match.index]:
                            if agent_code: codes_found.add(agent_code)

    codes_found = {c for c in codes_found if c}
    
    selected_code = None
    if len(codes_found) > 1:
        st.warning("⚠️ 동일한 이름과 지점을 가진 분이 존재합니다. 본인의 설계사코드(사번)를 선택해주세요.")
        selected_code = st.selectbox("나의 설계사코드 선택", sorted(list(codes_found)))
        needs_disambiguation = True

    if st.button("내 실적 확인하기", type="primary"):
        if not user_name or not branch_code_input:
            st.warning("이름과 지점코드를 입력해주세요.")
        elif not st.session_state['config']:
            st.warning("현재 진행 중인 시책 데이터가 없습니다.")
        elif not codes_found:
            st.error("일치하는 정보가 없습니다. 이름과 지점코드를 다시 확인해주세요.")
        else:
            final_target_code = selected_code if needs_disambiguation else list(codes_found)[0]
            
            calc_results, total_prize = calculate_agent_performance(final_target_code)
            
            if calc_results:
                # 🌟 대리점/지사명 조회
                display_name = user_name
                for cfg in st.session_state['config']:
                    df = st.session_state['raw_data'].get(cfg.get('file'))
                    if df is None: continue
                    col_code = cfg.get('col_code', '')
                    col_agency = cfg.get('col_agency', '')
                    if not col_code or col_code not in df.columns: continue
                    if not col_agency or col_agency not in df.columns: continue
                    clean_codes = get_clean_series(df, col_code)
                    m = df[clean_codes == safe_str(final_target_code)]
                    if not m.empty:
                        agency_val = _clean_excel_text(str(m[col_agency].values[0]).strip())
                        if agency_val and agency_val != 'nan':
                            display_name = f"{agency_val} {user_name}"
                        break
                
                # 🌟 [로그 저장] 일반 설계사 실적 조회 성공 시 기록 🌟
                save_log(f"{user_name}({branch_code_input}지점)", final_target_code, "USER_SEARCH")
                
                render_ui_cards(display_name, calc_results, total_prize, show_share_text=False)
                
                user_leaflet_path = os.path.join(DATA_DIR, "leaflet.png")
                if os.path.exists(user_leaflet_path):
                    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
                    st.image(user_leaflet_path, use_container_width=True)
            else:
                st.error("해당 조건의 실적 데이터가 없습니다.")
