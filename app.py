"""
manage_v2.py — GA3본부 시상 자동 관리 시스템 (Ver 2.0)
======================================================
• data/ 폴더의 Excel 파일을 자동 감지·병합
• 컬럼 패턴 분석으로 시상 구조 자동 인식
• 매니저 로그인 → 산하 설계사 실적·시상 자동 표시

배포 방법:
  1. data/ 폴더에 PRIZE_SUM_OUT_YYYYMMDD.xlsx, PRIZE_6_BRIDGE_OUT_YYYYMMDD.xlsx push
  2. Streamlit Cloud 자동 배포 → 최신 파일 자동 반영
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import re
import os
import glob
import json
import uuid
import base64
from datetime import datetime

st.set_page_config(page_title="GA3본부 시상 관리 시스템", layout="wide")

DATA_DIR = "data"
SETTINGS_FILE = "settings.json"

# ═══════════════════════════════════════════════════════
# 0. CSS (메리츠 스타일)
# ═══════════════════════════════════════════════════════
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, 'Noto Sans KR', sans-serif;
}
.toss-header {
    background-color: rgb(128, 0, 0); padding: 32px 40px;
    border-radius: 20px; margin-bottom: 24px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.toss-title { color: #fff !important; font-size: 36px; font-weight: 800; margin: 0; letter-spacing: -0.5px; }
.toss-subtitle { color: #ffcccc !important; font-size: 24px; font-weight: 700; margin-left: 10px; }
.toss-desc { color: #f2f4f6 !important; font-size: 17px; margin: 12px 0 0 0; font-weight: 500; }
.block-container { padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-width: 100% !important; }
iframe { width: 100% !important; }
@media (max-width: 768px) {
    .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    .toss-header { padding: 18px 16px; border-radius: 14px; margin-bottom: 14px; }
    .toss-title { font-size: 22px !important; }
    .toss-subtitle { font-size: 14px !important; display: block; margin-left: 0; margin-top: 4px; }
    .toss-desc { font-size: 13px !important; margin-top: 6px; }
    iframe { min-height: 60vh !important; }
    .stButton > button { width: 100% !important; padding: 10px !important; font-size: 15px !important; }
}
@media (max-width: 480px) {
    .block-container { padding-left: 0.25rem !important; padding-right: 0.25rem !important; }
    .toss-header { padding: 14px 12px; border-radius: 10px; }
    .toss-title { font-size: 19px !important; }
    .toss-subtitle { font-size: 12px !important; }
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# 1. 설정 로드
# ═══════════════════════════════════════════════════════
DEFAULT_SETTINGS = {
    "admin_password": "wolf7998",
    "clip_footer": "팀장님! 시상 부족금액 안내드려요!\n부족한 거 챙겨서 꼭 시상 많이 받아 가셨으면 좋겠습니다!\n좋은 하루 되세요!",
    "prize_labels": {
        "base": "인보험 기본",
        "상품": "상품 추가",
        "상품추가": "상품 추가2",
        "유퍼간편": "유퍼스트"
    }
}

def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                user = json.load(f)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(settings.get(k), dict):
                    settings[k].update(v)
                else:
                    settings[k] = v
        except Exception:
            pass
    return settings


# ═══════════════════════════════════════════════════════
# 2. 데이터 로딩
# ═══════════════════════════════════════════════════════
def decode_excel_text(val):
    if pd.isna(val): return val
    val_str = str(val)
    if '_x' not in val_str: return val_str
    def decode_match(m):
        try: return chr(int(m.group(1), 16))
        except: return m.group(0)
    return re.sub(r'_x([0-9a-fA-F]{4})_', decode_match, val_str)

def clean_key(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan': return ""
    s = str(val).strip().replace(" ", "").upper()
    if s.endswith('.0'): s = s[:-2]
    return s

def find_latest_files():
    """data/ 폴더에서 날짜가 가장 큰 PRIZE 파일 쌍을 찾는다."""
    if not os.path.exists(DATA_DIR):
        return None, None, None

    def _latest(pattern):
        files = glob.glob(os.path.join(DATA_DIR, pattern))
        if not files: return None
        def _date(f):
            m = re.search(r'(\d{8})', os.path.basename(f))
            return m.group(1) if m else '00000000'
        return max(files, key=_date)

    sum_path = _latest("PRIZE_SUM_OUT_*.xlsx")
    bridge_path = _latest("PRIZE_6_BRIDGE_OUT_*.xlsx")

    data_date = None
    if sum_path:
        m = re.search(r'(\d{8})', os.path.basename(sum_path))
        if m:
            d = m.group(1)
            data_date = f"{d[:4]}.{d[4:6]}.{d[6:8]}"

    return sum_path, bridge_path, data_date

@st.cache_data(show_spinner="데이터를 로딩하고 있습니다...")
def load_and_merge(_sum_path, _bridge_path):
    """두 Excel 파일을 읽고 설계사코드 기준으로 병합."""
    def _read(path):
        df = pd.read_excel(path)
        df.columns = [decode_excel_text(c) if isinstance(c, str) else c for c in df.columns]
        for col in df.columns:
            if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].apply(decode_excel_text)
        return df

    df_sum = _read(_sum_path)
    merge_col = '대리점설계사조직코드'
    df_sum['_key'] = df_sum[merge_col].apply(clean_key)

    if _bridge_path and os.path.exists(_bridge_path):
        df_bridge = _read(_bridge_path)
        df_bridge['_key'] = df_bridge[merge_col].apply(clean_key)
        # 브릿지 파일에서 SUM과 겹치지 않는 컬럼만 가져오기
        bridge_only_cols = [c for c in df_bridge.columns
                           if c not in df_sum.columns or c == '_key']
        df_merged = pd.merge(df_sum, df_bridge[bridge_only_cols],
                             on='_key', how='left')
    else:
        df_merged = df_sum.copy()

    return df_merged

def _safe_float(val):
    if pd.isna(val) or val is None: return 0.0
    try: return float(str(val).replace(',', '').strip())
    except: return 0.0


# ═══════════════════════════════════════════════════════
# 3. 시상 구조 자동 감지 엔진
# ═══════════════════════════════════════════════════════
def detect_prize_structure(df, settings):
    """컬럼명 패턴을 분석하여 시상 구조를 자동 생성.
    Returns dict:
        weeks: {N: {"perf_col", "prizes": [{"label", "elig_col", "prize_col"}]}}
        combined: [{"label", "elig_col", "prize_col"}]
        cumulative: {"perf_col", "elig_col", "prize_col"} or None
        bridge: {...} or None
        consecutive: {...} or None
        next_bridge: {...} or None
    """
    cols = set(df.columns)
    labels = settings.get('prize_labels', DEFAULT_SETTINGS['prize_labels'])

    # ── 주차별 시상 감지 ──
    # 대상 컬럼 패턴: 추가13회예정금_{N}주대상, 추가13회예정금_{N}주대상_상품 등
    week_pattern = re.compile(r'^추가13회예정금_(\d+)주대상$')
    sub_pattern = re.compile(r'^추가13회예정금_(\d+)주대상_(.+)$')
    combined_pattern = re.compile(r'^추가13회예정금_(\d+)_(\d+)주대상$')

    detected_weeks = {}
    for c in sorted(cols):
        # 기본 대상
        m = week_pattern.match(c)
        if m:
            w = int(m.group(1))
            prize_col = f'추가13회예정금_{w}주'
            if prize_col in cols:
                detected_weeks.setdefault(w, []).append({
                    'label': labels.get('base', '인보험 기본'),
                    'elig_col': c,
                    'prize_col': prize_col
                })

        # 서브 타입 대상 (_상품, _상품추가, _유퍼)
        m2 = sub_pattern.match(c)
        if m2:
            w = int(m2.group(1))
            suffix = m2.group(2)
            # 대상 suffix → 예정금 suffix 매핑
            suffix_map = {
                '상품': '상품', '상품추가': '상품추가', '유퍼': '유퍼간편'
            }
            prize_suffix = suffix_map.get(suffix, suffix)
            prize_col = f'추가13회예정금_{w}주_{prize_suffix}'
            if prize_col in cols:
                display_label = labels.get(prize_suffix, labels.get(suffix, suffix))
                detected_weeks.setdefault(w, []).append({
                    'label': display_label,
                    'elig_col': c,
                    'prize_col': prize_col
                })

    weeks = {}
    for w in sorted(detected_weeks.keys()):
        perf_col = f'실적_{w}주차'
        if perf_col not in cols:
            perf_col = None
        weeks[w] = {
            'perf_col': perf_col,
            'prizes': detected_weeks[w]
        }

    # ── 합산 주차 감지 (1_2주 등) ──
    combined = []
    for c in sorted(cols):
        m = combined_pattern.match(c)
        if m:
            a, b = m.group(1), m.group(2)
            prize_col = f'추가13회예정금_{a}_{b}주'
            if prize_col in cols:
                combined.append({
                    'label': f'{a}~{b}주 합산',
                    'elig_col': c,
                    'prize_col': prize_col
                })

    # ── 월 누계 ──
    cumulative = None
    if '추가13회예정금_월대상' in cols and '추가13회예정금계' in cols:
        cumulative = {
            'perf_col': '실적계',
            'elig_col': '추가13회예정금_월대상',
            'prize_col': '추가13회예정금계'
        }

    # ── 브릿지 (BRIDGE 파일에서 온 컬럼) ──
    bridge = None
    if '브릿지시상금' in cols:
        # 월 감지: 브릿지실적_{M}월
        b_months = sorted(set(
            int(m.group(1))
            for c in cols
            for m in [re.match(r'^브릿지실적_(\d+)월$', c)]
            if m
        ))
        prev_m = b_months[0] if len(b_months) >= 1 else None
        curr_m = b_months[1] if len(b_months) >= 2 else None
        bridge = {
            'prev_perf': f'브릿지실적_{prev_m}월' if prev_m else None,
            'curr_perf': f'브릿지실적_{curr_m}월' if curr_m else None,
            'prize_col': '브릿지시상금',
            'tier_prev': f'브릿지실적구간_{prev_m}월' if prev_m and f'브릿지실적구간_{prev_m}월' in cols else None,
            'tier_curr': f'브릿지실적구간_{curr_m}월' if curr_m and f'브릿지실적구간_{curr_m}월' in cols else None,
            'target_col': f'브릿지실적목표_{curr_m}월' if curr_m and f'브릿지실적목표_{curr_m}월' in cols else None,
            'shortfall_col': f'브릿지부족금액_{curr_m}월' if curr_m and f'브릿지부족금액_{curr_m}월' in cols else None,
            'months': b_months,
            'label_prev': f'{prev_m}월' if prev_m else '',
            'label_curr': f'{curr_m}월' if curr_m else '',
        }

    # ── 연속가동 ──
    consecutive = None
    if '연속가동시상금' in cols:
        c_months = sorted(set(
            int(m.group(1))
            for c in cols
            for m in [re.match(r'^연속가동실적_(\d+)월$', c)]
            if m
        ))
        prev_m = c_months[0] if len(c_months) >= 1 else None
        curr_m = c_months[1] if len(c_months) >= 2 else None
        consecutive = {
            'prev_perf': f'연속가동실적_{prev_m}월' if prev_m else None,
            'curr_perf': f'연속가동실적_{curr_m}월' if curr_m else None,
            'prize_col': '연속가동시상금',
            'target_col': f'연속가동실적목표_{curr_m}월' if curr_m and f'연속가동실적목표_{curr_m}월' in cols else None,
            'shortfall_col': f'연속가동부족금액_{curr_m}월' if curr_m and f'연속가동부족금액_{curr_m}월' in cols else None,
            'months': c_months,
            'label_prev': f'{prev_m}월' if prev_m else '',
            'label_curr': f'{curr_m}월' if curr_m else '',
        }

    # ── 차기 브릿지 (SUM 파일 프리뷰) ──
    next_bridge = None
    nb_pattern = re.compile(r'^브릿지실적_(\d+)_(\d+)월$')
    for c in sorted(cols):
        m = nb_pattern.match(c)
        if m:
            a, b = m.group(1), m.group(2)
            next_bridge = {
                'label': f'{a}~{b}월 브릿지',
                'perf_col': c,
                'target_col': f'브릿지실적목표_{a}_{b}월' if f'브릿지실적목표_{a}_{b}월' in cols else None,
                'shortfall_col': f'브릿지실적부족액_{a}_{b}월' if f'브릿지실적부족액_{a}_{b}월' in cols else None,
                'tier_col': f'브릿지실적구간_{a}_{b}월' if f'브릿지실적구간_{a}_{b}월' in cols else None,
            }
            break  # 하나만

    return {
        'weeks': weeks,
        'combined': combined,
        'cumulative': cumulative,
        'bridge': bridge,
        'consecutive': consecutive,
        'next_bridge': next_bridge,
    }


# ═══════════════════════════════════════════════════════
# 4. 표시용 DataFrame 빌더 + 시상금 계산
# ═══════════════════════════════════════════════════════
def build_display(my_df, ps, settings):
    """자동 감지된 구조(ps)를 바탕으로 표시용 DataFrame,
    컬럼 그룹, 시상금 맵을 생성.

    Returns: (display_df, col_groups, prize_data_map)
    """
    out = pd.DataFrame(index=my_df.index)

    # 기본 정보
    if '대리점지사명' in my_df.columns:
        out['지사'] = my_df['대리점지사명']
    if '대리점설계사명' in my_df.columns:
        out['설계사명'] = my_df['대리점설계사명']

    col_groups = []

    # ── 주차별 ──
    for w, info in ps['weeks'].items():
        grp_cols = []
        if info['perf_col'] and info['perf_col'] in my_df.columns:
            label = f'{w}주 실적'
            out[label] = my_df[info['perf_col']]
            grp_cols.append(label)

        # 주차별 시상 합계 (개별 prize_col 합산)
        prize_sum_label = f'{w}주 시상'
        prize_sum = pd.Series(0.0, index=my_df.index)
        has_any = False
        for p in info['prizes']:
            if p['prize_col'] in my_df.columns:
                vals = pd.to_numeric(my_df[p['prize_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                prize_sum += vals
                has_any = True
        if has_any:
            out[prize_sum_label] = prize_sum
            grp_cols.append(prize_sum_label)

        if grp_cols:
            col_groups.append({'name': f'{w}주차', 'cols': grp_cols})

    # ── 합산 주차 ──
    for comb in ps.get('combined', []):
        if comb['prize_col'] in my_df.columns:
            label = f"{comb['label']} 시상"
            vals = pd.to_numeric(my_df[comb['prize_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            # 대상 체크
            if comb['elig_col'] in my_df.columns:
                elig = pd.to_numeric(my_df[comb['elig_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                vals = vals.where(elig != 0, 0)
            out[label] = vals

    # ── 누계 ──
    cumul_grp = []
    if '실적계' in my_df.columns:
        out['실적 누계'] = my_df['실적계']
        cumul_grp.append('실적 누계')
    if '시상금계' in my_df.columns:
        out['기본 시상'] = my_df['시상금계']
        cumul_grp.append('기본 시상')
    if ps['cumulative'] and ps['cumulative']['prize_col'] in my_df.columns:
        vals = pd.to_numeric(my_df[ps['cumulative']['prize_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        if ps['cumulative']['elig_col'] in my_df.columns:
            elig = pd.to_numeric(my_df[ps['cumulative']['elig_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            vals = vals.where(elig != 0, 0)
        out['추가 누계'] = vals
        cumul_grp.append('추가 누계')
    if cumul_grp:
        col_groups.append({'name': '누계', 'cols': cumul_grp})

    # ── 브릿지 ──
    if ps['bridge']:
        b = ps['bridge']
        b_grp = []
        if b['prev_perf'] and b['prev_perf'] in my_df.columns:
            lbl = f"브릿지 {b['label_prev']}"
            out[lbl] = my_df[b['prev_perf']]
            b_grp.append(lbl)
        if b['curr_perf'] and b['curr_perf'] in my_df.columns:
            lbl = f"브릿지 {b['label_curr']}"
            out[lbl] = my_df[b['curr_perf']]
            b_grp.append(lbl)
        if b['prize_col'] in my_df.columns:
            out['브릿지 시상'] = my_df[b['prize_col']]
            b_grp.append('브릿지 시상')
        if b.get('shortfall_col') and b['shortfall_col'] in my_df.columns:
            out['브릿지 부족액'] = my_df[b['shortfall_col']]
            b_grp.append('브릿지 부족액')
        if b_grp:
            col_groups.append({'name': '브릿지', 'cols': b_grp})

    # ── 연속가동 ──
    if ps['consecutive']:
        c = ps['consecutive']
        c_grp = []
        if c['prev_perf'] and c['prev_perf'] in my_df.columns:
            lbl = f"연속 {c['label_prev']}"
            out[lbl] = my_df[c['prev_perf']]
            c_grp.append(lbl)
        if c['curr_perf'] and c['curr_perf'] in my_df.columns:
            lbl = f"연속 {c['label_curr']}"
            out[lbl] = my_df[c['curr_perf']]
            c_grp.append(lbl)
        if c['prize_col'] in my_df.columns:
            out['연속 시상'] = my_df[c['prize_col']]
            c_grp.append('연속 시상')
        if c.get('shortfall_col') and c['shortfall_col'] in my_df.columns:
            out['연속 부족액'] = my_df[c['shortfall_col']]
            c_grp.append('연속 부족액')
        if c_grp:
            col_groups.append({'name': '연속가동', 'cols': c_grp})

    # ── 차기 브릿지 ──
    if ps['next_bridge']:
        nb = ps['next_bridge']
        nb_grp = []
        if nb['perf_col'] in my_df.columns:
            lbl = f"{nb['label']} 실적"
            out[lbl] = my_df[nb['perf_col']]
            nb_grp.append(lbl)
        if nb.get('shortfall_col') and nb['shortfall_col'] in my_df.columns:
            lbl = f"{nb['label']} 부족"
            out[lbl] = my_df[nb['shortfall_col']]
            nb_grp.append(lbl)
        if nb_grp:
            col_groups.append({'name': nb['label'], 'cols': nb_grp})

    # ── 총 시상금 계산 ──
    total = pd.Series(0.0, index=my_df.index)
    if '시상금계and추가예정금계' in my_df.columns:
        total += pd.to_numeric(my_df['시상금계and추가예정금계'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    elif '시상금계' in my_df.columns:
        total += pd.to_numeric(my_df['시상금계'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    if ps['bridge'] and ps['bridge']['prize_col'] in my_df.columns:
        total += pd.to_numeric(my_df[ps['bridge']['prize_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    if ps['consecutive'] and ps['consecutive']['prize_col'] in my_df.columns:
        total += pd.to_numeric(my_df[ps['consecutive']['prize_col']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    out['총 시상금'] = total

    # ── 순번 삽입 ──
    out.insert(0, '순번', range(1, len(out) + 1))

    # ── 포맷팅 ──
    skip_fmt = {'순번'}
    for c in out.columns:
        if c in skip_fmt:
            continue
        out[c] = out[c].apply(_format_cell)

    # ── 시상 상세 맵 (팝업/카톡용) ──
    prize_data_map = {}
    for row_idx, (orig_idx, row) in enumerate(my_df.iterrows()):
        details = _build_prize_details(row, ps)
        if details['total'] > 0:
            prize_data_map[row_idx] = details

    return out, col_groups, prize_data_map

def _format_cell(val):
    try:
        if pd.isna(val) or str(val).strip() == '': return ''
        s = str(val).replace(',', '')
        n = float(s)
        if n == 0: return ''
        if n == int(n): return f'{int(n):,}'
        return f'{n:,.1f}'
    except:
        s = str(val).strip()
        return '' if s in ('0', '0.0', 'nan') else s

def _build_prize_details(row, ps):
    """한 행(설계사)에 대한 시상 상세 내역 구성."""
    weekly_items = []
    for w, info in ps['weeks'].items():
        week_prizes = []
        for p in info['prizes']:
            if p['prize_col'] not in row.index: continue
            elig = _safe_float(row.get(p['elig_col'], 1))
            if elig == 0: continue
            amt = _safe_float(row.get(p['prize_col'], 0))
            if amt > 0:
                week_prizes.append({'label': p['label'], 'amount': amt})
        perf = _safe_float(row.get(info['perf_col'], 0)) if info['perf_col'] else 0
        if week_prizes or perf > 0:
            weekly_items.append({
                'week': w, 'perf': perf,
                'prizes': week_prizes,
                'subtotal': sum(p['amount'] for p in week_prizes)
            })

    combined_items = []
    for comb in ps.get('combined', []):
        if comb['prize_col'] not in row.index: continue
        elig = _safe_float(row.get(comb['elig_col'], 1))
        if elig == 0: continue
        amt = _safe_float(row.get(comb['prize_col'], 0))
        if amt > 0:
            combined_items.append({'label': comb['label'], 'amount': amt})

    cumul_amt = 0
    if ps['cumulative'] and ps['cumulative']['prize_col'] in row.index:
        elig = _safe_float(row.get(ps['cumulative']['elig_col'], 1))
        if elig != 0:
            cumul_amt = _safe_float(row.get(ps['cumulative']['prize_col'], 0))

    base_prize = _safe_float(row.get('시상금계', 0))
    extra_prize = _safe_float(row.get('추가예정금계', 0))

    bridge_info = None
    if ps['bridge']:
        b = ps['bridge']
        bp = _safe_float(row.get(b['prize_col'], 0))
        bridge_info = {
            'prev': _safe_float(row.get(b['prev_perf'], 0)) if b['prev_perf'] else 0,
            'curr': _safe_float(row.get(b['curr_perf'], 0)) if b['curr_perf'] else 0,
            'prize': bp,
            'shortfall': _safe_float(row.get(b.get('shortfall_col', ''), 0)),
            'target': _safe_float(row.get(b.get('target_col', ''), 0)),
            'label_prev': b['label_prev'], 'label_curr': b['label_curr'],
        }

    consec_info = None
    if ps['consecutive']:
        c = ps['consecutive']
        cp = _safe_float(row.get(c['prize_col'], 0))
        consec_info = {
            'prev': _safe_float(row.get(c['prev_perf'], 0)) if c['prev_perf'] else 0,
            'curr': _safe_float(row.get(c['curr_perf'], 0)) if c['curr_perf'] else 0,
            'prize': cp,
            'shortfall': _safe_float(row.get(c.get('shortfall_col', ''), 0)),
            'target': _safe_float(row.get(c.get('target_col', ''), 0)),
            'label_prev': c['label_prev'], 'label_curr': c['label_curr'],
        }

    total = base_prize + extra_prize
    if bridge_info: total += bridge_info['prize']
    if consec_info: total += consec_info['prize']

    return {
        'weekly': weekly_items, 'combined': combined_items,
        'cumul_amt': cumul_amt, 'base_prize': base_prize,
        'extra_prize': extra_prize,
        'bridge': bridge_info, 'consecutive': consec_info,
        'total': total,
    }


# ═══════════════════════════════════════════════════════
# 5. 카톡 텍스트 생성
# ═══════════════════════════════════════════════════════
def build_clip_text(row_display, details, data_date, footer):
    """카카오톡 공유용 텍스트 생성."""
    agency = str(row_display.get('지사', '')).strip()
    name = str(row_display.get('설계사명', '')).strip()
    person = f"{agency} {name}".strip()
    if person and not person.endswith('님'):
        person += ' 팀장님'

    lines = []
    if data_date:
        lines.append(f"📅 {data_date} 기준")
    lines.append(f"👤 {person}")

    # 주차별
    for wi in details['weekly']:
        w = wi['week']
        lines.append(f"\n📌 {w}주차: 실적 {wi['perf']:,.0f}원")
        for p in wi['prizes']:
            lines.append(f"  · {p['label']}: {p['amount']:,.0f}원")
        if wi['subtotal'] > 0:
            lines.append(f"  → 추가시상 소계: {wi['subtotal']:,.0f}원")

    for ci in details['combined']:
        lines.append(f"\n📎 {ci['label']}: {ci['amount']:,.0f}원")

    # 브릿지
    if details['bridge'] and (details['bridge']['prize'] > 0 or details['bridge']['shortfall'] > 0):
        b = details['bridge']
        lines.append(f"\n🌉 브릿지")
        lines.append(f"  {b['label_prev']}: {b['prev']:,.0f}원 / {b['label_curr']}: {b['curr']:,.0f}원")
        if b['prize'] > 0:
            lines.append(f"  시상금: {b['prize']:,.0f}원")
        if b['shortfall'] > 0:
            lines.append(f"  🔴 부족액: {b['shortfall']:,.0f}원")

    # 연속가동
    if details['consecutive'] and (details['consecutive']['prize'] > 0 or details['consecutive']['shortfall'] > 0):
        c = details['consecutive']
        lines.append(f"\n🔗 연속가동")
        lines.append(f"  {c['label_prev']}: {c['prev']:,.0f}원 / {c['label_curr']}: {c['curr']:,.0f}원")
        if c['prize'] > 0:
            lines.append(f"  시상금: {c['prize']:,.0f}원")
        if c['shortfall'] > 0:
            lines.append(f"  🔴 부족액: {c['shortfall']:,.0f}원")

    # 총합
    lines.append(f"\n💰 총 시상금: {details['total']:,.0f}원")
    parts = []
    if details['base_prize'] > 0: parts.append(f"기본 {details['base_prize']:,.0f}")
    if details['extra_prize'] > 0: parts.append(f"추가 {details['extra_prize']:,.0f}")
    if details['bridge'] and details['bridge']['prize'] > 0:
        parts.append(f"브릿지 {details['bridge']['prize']:,.0f}")
    if details['consecutive'] and details['consecutive']['prize'] > 0:
        parts.append(f"연속 {details['consecutive']['prize']:,.0f}")
    if parts:
        lines.append(f"  ({' + '.join(parts)})")

    if footer:
        lines.append(f"\n{footer}")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════
# 6. 시상 팝업 HTML 생성
# ═══════════════════════════════════════════════════════
def build_prize_popup_html(details):
    """시상 상세 팝업용 HTML."""
    if not details or details['total'] <= 0:
        return ''

    h = '<div style="padding:5px;">'
    h += f'<div style="font-weight:800;color:#d9232e;font-size:18px;margin-bottom:4px;">💰 총 시상금: {details["total"]:,.0f}원</div>'

    parts = []
    if details['base_prize'] > 0: parts.append(f"기본 {details['base_prize']:,.0f}")
    if details['extra_prize'] > 0: parts.append(f"추가 {details['extra_prize']:,.0f}")
    if details.get('bridge') and details['bridge']['prize'] > 0:
        parts.append(f"브릿지 {details['bridge']['prize']:,.0f}")
    if details.get('consecutive') and details['consecutive']['prize'] > 0:
        parts.append(f"연속 {details['consecutive']['prize']:,.0f}")
    if parts:
        h += f'<div style="color:#888;font-size:13px;margin-bottom:12px;">({" + ".join(parts)})</div>'

    # 주차별
    for wi in details['weekly']:
        if not wi['prizes']: continue
        h += f'<div style="font-size:12px;color:#4e5968;font-weight:700;margin:8px 0 4px;border-bottom:1px solid #eee;padding-bottom:4px;">📌 {wi["week"]}주차 (실적: {wi["perf"]:,.0f}원)</div>'
        for p in wi['prizes']:
            h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#555;">{p["label"]}</span><span style="color:#d9232e;font-weight:600;">{p["amount"]:,.0f}원</span></div>'

    for ci in details['combined']:
        h += f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid #eee;margin-top:4px;"><span style="color:#555;font-weight:600;">📎 {ci["label"]}</span><span style="color:#d9232e;font-weight:700;">{ci["amount"]:,.0f}원</span></div>'

    if details.get('bridge') and details['bridge']['prize'] > 0:
        b = details['bridge']
        h += f'<div style="font-size:12px;color:#d4380d;font-weight:700;margin:8px 0 4px;border-bottom:1px solid #eee;padding-bottom:4px;">🌉 브릿지</div>'
        h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#888;">{b["label_prev"]} 실적</span><span>{b["prev"]:,.0f}원</span></div>'
        h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#888;">{b["label_curr"]} 실적</span><span>{b["curr"]:,.0f}원</span></div>'
        h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#555;font-weight:600;">시상금</span><span style="color:#d9232e;font-weight:700;">{b["prize"]:,.0f}원</span></div>'
        if b['shortfall'] > 0:
            h += f'<div style="padding:2px 0;font-size:11px;color:#888;">🔴 부족액: {b["shortfall"]:,.0f}원 (목표: {b["target"]:,.0f}원)</div>'

    if details.get('consecutive') and details['consecutive']['prize'] > 0:
        c = details['consecutive']
        h += f'<div style="font-size:12px;color:#2B6CB0;font-weight:700;margin:8px 0 4px;border-bottom:1px solid #eee;padding-bottom:4px;">🔗 연속가동</div>'
        h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#888;">{c["label_prev"]} 실적</span><span>{c["prev"]:,.0f}원</span></div>'
        h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#888;">{c["label_curr"]} 실적</span><span>{c["curr"]:,.0f}원</span></div>'
        h += f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span style="color:#555;font-weight:600;">시상금</span><span style="color:#d9232e;font-weight:700;">{c["prize"]:,.0f}원</span></div>'
        if c['shortfall'] > 0:
            h += f'<div style="padding:2px 0;font-size:11px;color:#888;">🔴 부족액: {c["shortfall"]:,.0f}원</div>'

    h += '</div>'
    return h


# ═══════════════════════════════════════════════════════
# 7. HTML 테이블 렌더링 (데스크탑 + 모바일)
# ═══════════════════════════════════════════════════════
def render_html_table(df, col_groups, prize_data_map, data_date, footer):
    """DataFrame → 반응형 HTML 테이블 (정렬/틀고정/카드뷰/복사/시상팝업)"""
    table_id = f"pt_{uuid.uuid4().hex[:8]}"
    columns = list(df.columns)
    num_cols = len(columns)
    shortfall_cols = {c for c in columns if '부족' in c}

    # 틀 고정 열 감지
    freeze_kw = ['순번', '지사', '설계사', '이름']
    freeze_count = 0
    for i, col in enumerate(columns):
        if any(kw in col for kw in freeze_kw):
            freeze_count = i + 1
    freeze_count = min(freeze_count, 4)

    has_groups = len(col_groups) > 0
    base_font = max(11, 15 - num_cols // 4)

    GROUP_COLORS = ['#2B6CB0', '#2F855A', '#9B2C2C', '#6B46C1',
                    '#B7791F', '#2C7A7B', '#C05621', '#702459']

    col_to_group = {}
    group_color_map = {}
    for gi, grp in enumerate(col_groups):
        color = GROUP_COLORS[gi % len(GROUP_COLORS)]
        group_color_map[grp['name']] = color
        for c in grp['cols']:
            col_to_group[c] = grp['name']

    group_mid = {}
    for gname in set(col_to_group.values()):
        indices = [i for i, c in enumerate(columns) if col_to_group.get(c) == gname]
        if indices: group_mid[gname] = indices[len(indices) // 2]

    group_info = []
    for i, col in enumerate(columns):
        gname = col_to_group.get(col)
        if gname is None:
            group_info.append((None, False, False, False))
        else:
            prev_g = col_to_group.get(columns[i-1]) if i > 0 else None
            next_g = col_to_group.get(columns[i+1]) if i < len(columns)-1 else None
            group_info.append((gname, prev_g != gname, next_g != gname, i == group_mid.get(gname, -1)))

    def fc(i):
        if i >= freeze_count: return ""
        c = "cf"
        if i == freeze_count - 1: c += " cfl"
        return c

    grp_h, col_h = 30, 36

    # ── 클립보드 텍스트 생성 ──
    clip_texts = []
    for row_idx, (_, row) in enumerate(df.iterrows()):
        if row_idx in prize_data_map:
            details = prize_data_map[row_idx]
        else:
            details = {'total': 0, 'weekly': [], 'combined': [], 'base_prize': 0,
                       'extra_prize': 0, 'bridge': None, 'consecutive': None, 'cumul_amt': 0}
        clip_texts.append(build_clip_text(row.to_dict(), details, data_date, footer))

    clip_b64 = base64.b64encode(json.dumps(clip_texts, ensure_ascii=False).encode('utf-8')).decode('ascii')

    # ── 시상 팝업 HTML 생성 ──
    prize_htmls = []
    for row_idx in range(len(df)):
        if row_idx in prize_data_map:
            prize_htmls.append(build_prize_popup_html(prize_data_map[row_idx]))
        else:
            prize_htmls.append('')
    prize_b64 = base64.b64encode(json.dumps(prize_htmls, ensure_ascii=False).encode('utf-8')).decode('ascii')

    # ══════════════════════ HTML 빌드 ══════════════════════
    mob_font = max(9, base_font - 2)

    html = f"""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
*{{box-sizing:border-box}}html,body{{margin:0;padding:0;font-family:'Pretendard',-apple-system,'Noto Sans KR',sans-serif}}
.tw{{width:100%;max-height:85vh;overflow:auto;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08);-webkit-overflow-scrolling:touch}}
.pt{{width:max-content;min-width:100%;border-collapse:separate;border-spacing:0;white-space:nowrap;font-size:{base_font}px}}
.pt thead th{{background:#4e5968;color:#fff;font-weight:700;text-align:center;border:1px solid #3d4654;position:sticky;z-index:2;cursor:pointer;user-select:none}}
.pt .rg th{{top:0;height:{grp_h}px;padding:4px 6px;cursor:default}}.pt .rg .ge{{background:#4e5968;border-bottom-color:#4e5968}}
.pt .rg .gc{{border-left:none;border-right:none}}.pt .rg .gc-f{{border-left:1px solid #3d4654;border-right:none}}
.pt .rg .gc-l{{border-left:none;border-right:1px solid #3d4654}}.pt .rg .gc-s{{border-left:1px solid #3d4654;border-right:1px solid #3d4654}}
.pt .rc th{{top:{grp_h if has_groups else 0}px;height:{col_h}px;padding:6px 10px}}.pt .rc th .gb{{display:none;height:4px;border-radius:2px;margin:0 auto 3px;width:80%}}
.pt thead th:hover{{background:#3d4654}}.sa{{margin-left:3px;font-size:10px;opacity:.5}}.sa.active{{opacity:1}}
.pt tbody td{{text-align:center;padding:6px 10px;border:1px solid #e5e8eb;white-space:nowrap;background:#fff}}
.pt tbody tr:nth-child(even) td{{background:#f7f8fa}}.pt tbody tr:hover td{{background:#eef1f6}}
.sc{{color:rgb(128,0,0);font-weight:700}}
.cf{{position:sticky;z-index:1}}thead th.cf{{z-index:3}}.cfl{{box-shadow:2px 0 5px rgba(0,0,0,.08)}}
@media(max-width:768px){{.tw{{max-height:75vh;border-radius:8px}}.pt{{font-size:{mob_font}px}}.pt thead th,.pt tbody td{{padding:4px 5px}}
.pt .rg{{display:none}}.pt .rc th{{top:0!important;padding:5px 5px 4px}}.pt .rc th .gb{{display:block}}.sa{{font-size:8px;margin-left:1px}}.cfl{{box-shadow:2px 0 3px rgba(0,0,0,.12)}}}}
@media(max-width:480px){{.pt{{font-size:{max(8,mob_font-1)}px}}.pt thead th,.pt tbody td{{padding:3px}}.pt .rc th .gb{{height:3px;margin-bottom:2px}}}}
.dv{{display:block}}.mv{{display:none}}
@media(max-width:768px){{.dv{{display:none!important}}.mv{{display:block!important}}}}
.mv{{padding:0 4px;max-height:80vh;overflow-y:auto;-webkit-overflow-scrolling:touch}}
.mc{{background:#fff;border-radius:12px;margin-bottom:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);border:1px solid #e5e8eb}}
.mh{{display:flex;align-items:center;flex-wrap:wrap;padding:14px;cursor:pointer;gap:6px;position:relative}}
.mn{{background:#4e5968;color:#fff;font-size:11px;font-weight:700;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.mname{{font-size:16px;font-weight:700;color:#191f28}}
.ms{{display:flex;gap:6px;margin-left:auto;flex-shrink:0}}
.chev{{font-size:10px;color:#8b95a1;margin-left:6px;transition:transform .2s}}
.mc.open .chev{{transform:rotate(180deg)}}
.mb{{max-height:0;overflow:hidden;transition:max-height .3s ease;border-top:1px solid #f2f4f6}}
.mc.open .mb{{max-height:3000px}}
.mgl{{font-size:12px;font-weight:700;color:#4e5968;padding:8px 14px 4px;margin-top:4px}}
.mr{{display:flex;justify-content:space-between;padding:6px 14px;font-size:14px}}
.mr:nth-child(even){{background:#f9fafb}}.ml{{color:#6b7684;font-weight:500;flex-shrink:0;margin-right:12px}}.mval{{color:#191f28;font-weight:600;text-align:right}}
.mr.msc .mval{{color:rgb(128,0,0);font-weight:800}}
.mcopy{{width:100%;padding:10px;border:none;border-radius:10px;background:linear-gradient(135deg,#FEE500,#F5D600);color:#3C1E1E;font-size:14px;font-weight:700;cursor:pointer;transition:all .2s;box-shadow:0 2px 6px rgba(0,0,0,.08)}}
.mcopy:active{{transform:scale(.97)}}.mcopy.copied{{background:linear-gradient(135deg,#22C55E,#16A34A);color:#fff}}
.dcopy{{border:none;border-radius:6px;padding:4px 10px;background:#FEE500;color:#3C1E1E;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;transition:all .15s}}
.dcopy:hover{{background:#F5D600}}.dcopy.copied{{background:#22C55E;color:#fff}}
</style>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
"""

    # ── 데스크탑 테이블 ──
    html += '<div class="dv">'
    html += f'<div class="tw" id="wrap_{table_id}"><table class="pt" id="{table_id}"><thead>'

    if has_groups:
        html += '<tr class="rg">'
        for i, col in enumerate(columns):
            gname, is_f, is_l, is_t = group_info[i]
            f_cls = fc(i)
            if gname is None:
                html += f'<th class="ge {f_cls}" data-col="{i}"></th>'
            else:
                gc = group_color_map.get(gname, '#364152')
                if is_f and is_l: b_cls = "gc-s"
                elif is_f: b_cls = "gc-f"
                elif is_l: b_cls = "gc-l"
                else: b_cls = "gc"
                text = gname if is_t else ""
                html += f'<th class="{b_cls} {f_cls}" style="background:{gc}" data-col="{i}">{text}</th>'
        html += '<th class="ge" data-col="-1"></th></tr>'

    html += '<tr class="rc">'
    for i, col in enumerate(columns):
        f_cls = fc(i)
        gname = col_to_group.get(col)
        bar = f'<div class="gb" style="background:{group_color_map.get(gname,"")}"></div>' if gname else ''
        html += f'<th class="{f_cls}" data-col="{i}" onclick="sortT(this)">{bar}{col} <span class="sa">▲▼</span></th>'
    html += '<th data-col="-1" style="min-width:50px;cursor:default">복사</th></tr></thead><tbody>'

    for row_idx, (_, row) in enumerate(df.iterrows()):
        html += '<tr>'
        for i, col in enumerate(columns):
            val = row[col]
            cv = "" if pd.isna(val) else str(val)
            f_cls = fc(i)
            extra = " sc" if col in shortfall_cols and cv else ""
            html += f'<td class="{f_cls}{extra}" data-col="{i}">{cv}</td>'
        html += f'<td data-col="-1"><button class="dcopy" onclick="copyC({row_idx},this,event)">📋</button>'
        if row_idx in prize_data_map:
            html += f'<button class="dcopy" onclick="showP({row_idx},event)" style="margin-left:2px">💰</button>'
        html += '</td></tr>'
    html += '</tbody></table></div></div>'

    # ── 모바일 카드 뷰 ──
    html += '<div class="mv">'
    for row_idx, (_, row) in enumerate(df.iterrows()):
        name_val = str(row.get('설계사명', '')) if '설계사명' in columns else ''
        agency_val = str(row.get('지사', '')) if '지사' in columns else ''
        num_val = str(row.get('순번', row_idx + 1)) if '순번' in columns else str(row_idx + 1)

        # 요약 배지
        badges = []
        total_col_val = str(row.get('총 시상금', '')).strip()
        if total_col_val and total_col_val != '0' and total_col_val != '':
            badges.append(f'<span style="background:#fff3e0;color:#d9232e;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700">💰{total_col_val}</span>')
        for c in columns:
            if '부족' in c:
                v = str(row[c]).strip()
                if v and v != '' and v != '0':
                    badges.append(f'<span style="background:#FFF5F5;color:rgb(128,0,0);padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700">🔴 {c}: {v}</span>')

        html += f'<div class="mc"><div class="mh" onclick="this.parentElement.classList.toggle(\'open\')">'
        html += f'<span class="mn">{num_val}</span><span class="mname">{name_val}</span>'
        if badges:
            html += f'<span class="ms">{" ".join(badges)}</span>'
        html += '<span class="chev">&#9660;</span></div><div class="mb">'

        # 복사 버튼
        html += f'<div style="padding:10px 14px 6px;text-align:center"><button class="mcopy" onclick="copyC({row_idx},this,event)">📋 카톡 보내기</button>'
        if row_idx in prize_data_map:
            html += f'<button class="mcopy" onclick="showP({row_idx},event)" style="background:#fff3e0;color:#d9232e;border:1px solid #ffd4a8;margin-top:4px">💰 시상금 상세</button>'
        html += '</div>'

        # 카드 본문
        if agency_val and agency_val != '0':
            html += f'<div class="mr"><span class="ml">지사</span><span class="mval">{agency_val}</span></div>'

        current_grp = None
        for c in columns:
            if c in ('순번', '지사', '설계사명'): continue
            v = str(row[c]).strip() if not pd.isna(row[c]) else ''
            if not v or v == '0': continue
            grp = col_to_group.get(c)
            if grp and grp != current_grp:
                gc = group_color_map.get(grp, '#4e5968')
                html += f'<div class="mgl" style="border-left:3px solid {gc};padding-left:8px">{grp}</div>'
                current_grp = grp
            elif grp is None and current_grp is not None:
                current_grp = None
            extra = ' msc' if c in shortfall_cols else ''
            html += f'<div class="mr{extra}"><span class="ml">{c}</span><span class="mval">{v}</span></div>'

        # 시상 카드 (모바일)
        if row_idx in prize_data_map:
            details = prize_data_map[row_idx]
            h_prize = '<div style="margin-top:8px;padding:10px;background:#fff8f0;border-radius:10px;border:1px solid #ffd4a8;">'
            h_prize += f'<div style="font-weight:800;color:#d9232e;font-size:15px;margin-bottom:4px">💰 총 시상금: {details["total"]:,.0f}원</div>'
            # 간략 합계
            parts = []
            if details['base_prize'] > 0: parts.append(f"기본 {details['base_prize']:,.0f}")
            if details['extra_prize'] > 0: parts.append(f"추가 {details['extra_prize']:,.0f}")
            if details.get('bridge') and details['bridge']['prize'] > 0: parts.append(f"브릿지 {details['bridge']['prize']:,.0f}")
            if details.get('consecutive') and details['consecutive']['prize'] > 0: parts.append(f"연속 {details['consecutive']['prize']:,.0f}")
            if parts:
                h_prize += f'<div style="font-size:11px;color:#888;margin-bottom:6px">({" + ".join(parts)})</div>'
            h_prize += '</div>'
            html += h_prize

        html += '</div></div>'
    html += '</div>'

    # ── 팝업 오버레이 ──
    html += """
<div id="co" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:99999;justify-content:center;align-items:center;padding:20px" onclick="if(event.target===this)this.style.display='none'">
<div style="background:#fff;border-radius:16px;padding:20px;width:100%;max-width:500px;max-height:70vh;box-shadow:0 10px 40px rgba(0,0,0,.3)">
<h3 style="margin:0 0 10px;font-size:16px">📋 아래 텍스트를 복사하세요</h3>
<textarea id="cta" style="width:100%;height:200px;border:1px solid #ddd;border-radius:8px;padding:10px;font-size:14px;resize:none;font-family:inherit;box-sizing:border-box"></textarea>
<button id="ccb" onclick="doCopy()" style="margin-top:10px;width:100%;padding:12px;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;background:#FEE500;color:#3C1E1E">📋 복사하기</button>
<button onclick="document.getElementById('co').style.display='none'" style="margin-top:6px;width:100%;padding:12px;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;background:#f2f4f6;color:#333">닫기</button>
</div></div>
<div id="po" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:99999;justify-content:center;align-items:center;padding:20px" onclick="if(event.target===this)this.style.display='none'">
<div style="background:#fff;border-radius:16px;padding:24px;width:100%;max-width:450px;max-height:70vh;overflow-y:auto;box-shadow:0 10px 40px rgba(0,0,0,.3)">
<h3 style="margin:0 0 12px;font-size:17px">💰 시상금 상세 조회</h3>
<div id="pc"></div>
<button onclick="document.getElementById('po').style.display='none'" style="margin-top:12px;width:100%;padding:12px;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;background:#f2f4f6;color:#333">닫기</button>
</div></div>
"""

    html += f'<div id="__cb" style="display:none">{clip_b64}</div>'
    html += f'<div id="__pb" style="display:none">{prize_b64}</div>'

    html += f"""
<script>
var FC={freeze_count},cd=[],ph=[],ok=false;
function isMob(){{return window.innerWidth<=768}}
function _ld(){{try{{var c=document.getElementById('__cb'),p=document.getElementById('__pb');if(!c||!p)return;cd=JSON.parse(_d(c.textContent.trim()));ph=JSON.parse(_d(p.textContent.trim()));ok=true}}catch(e){{console.error(e)}}}}
function _d(b){{try{{var bin=atob(b),u=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return new TextDecoder('utf-8').decode(u)}}catch(e){{return decodeURIComponent(escape(atob(b)))}}}}
function copyC(i,btn,e){{e.stopPropagation();if(!ok){{alert('데이터를 불러오지 못했습니다.');return}}var t=cd[i];if(!t){{alert('복사할 내용이 없습니다.');return}}if(isMob()&&navigator.share){{navigator.share({{text:t}}).then(function(){{_fb(btn)}}).catch(function(){{_so(t)}});return}}_so(t)}}
function _so(t){{var o=document.getElementById('co'),ta=document.getElementById('cta');ta.value=t;o.style.display='flex';setTimeout(function(){{ta.focus();ta.select();ta.setSelectionRange(0,ta.value.length)}},100)}}
function doCopy(){{var ta=document.getElementById('cta'),t=ta.value;if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).then(function(){{_od(true)}}).catch(function(){{_tc(ta)}});return}}_tc(ta)}}
function _tc(ta){{ta.readOnly=false;ta.focus();ta.select();ta.setSelectionRange(0,ta.value.length);var r=false;try{{r=document.execCommand('copy')}}catch(e){{}}if(r)_od(true);else{{_od(false);ta.focus();ta.select()}}}}
function _od(r){{var b=document.getElementById('ccb');if(r){{b.textContent='✅ 복사 완료!';b.style.background='#22C55E';b.style.color='#fff';setTimeout(function(){{document.getElementById('co').style.display='none';b.textContent='📋 복사하기';b.style.background='#FEE500';b.style.color='#3C1E1E'}},1200)}}else{{b.textContent='⚠️ Ctrl+C로 복사하세요';b.style.background='#f59e0b';b.style.color='#fff'}}}}
function _fb(b){{var o=b.innerHTML;b.classList.add('copied');b.innerHTML='✅ 복사 완료!';setTimeout(function(){{b.classList.remove('copied');b.innerHTML=o}},1500)}}
function showP(i,e){{if(e)e.stopPropagation();if(!ok){{alert('데이터를 불러오지 못했습니다.');return}}var h=ph[i];if(!h){{alert('시상금 데이터가 없습니다.');return}}document.getElementById('pc').innerHTML=h;document.getElementById('po').style.display='flex'}}
function applyF(){{var t=document.getElementById("{table_id}");var fc=isMob()?Math.min(FC,2):FC;if(!t||fc===0)return;var fr=t.querySelector("tbody tr");if(!fr)return;var lp=[],cl=0;for(var i=0;i<fc;i++){{lp.push(cl);if(fr.cells[i])cl+=fr.cells[i].offsetWidth}}t.querySelectorAll(".cf").forEach(function(c){{var idx=parseInt(c.getAttribute("data-col"));if(!isNaN(idx)&&idx<fc){{c.style.left=lp[idx]+"px";c.style.position="sticky";c.style.zIndex=c.tagName==="TH"?"3":"1"}}else if(!isNaN(idx)&&idx>=fc){{c.style.position="static";c.style.boxShadow="none"}}}})}}
function autoR(){{if(!window.frameElement)return;var vh=window.parent.innerHeight||900;if(isMob()){{var mv=document.querySelector('.mv');if(mv)window.frameElement.style.height=Math.min(mv.scrollHeight+20,Math.round(vh*.80))+"px"}}else{{var w=document.getElementById("wrap_{table_id}");if(w)window.frameElement.style.height=Math.min(w.scrollHeight+4,Math.round(vh*.85))+"px"}}}}
var ss={{}};
function sortT(th){{var t=document.getElementById("{table_id}"),tb=t.querySelector("tbody"),rows=Array.from(tb.querySelectorAll("tr"));var ci=parseInt(th.getAttribute("data-col"));if(isNaN(ci))return;var asc=ss[ci]!==true;ss={{}};ss[ci]=asc;rows.sort(function(a,b){{var aT=(a.cells[ci]?a.cells[ci].textContent:'').trim(),bT=(b.cells[ci]?b.cells[ci].textContent:'').trim();var aN=parseFloat(aT.replace(/,/g,"")),bN=parseFloat(bT.replace(/,/g,""));if(aT===""&&bT==="")return 0;if(aT==="")return 1;if(bT==="")return -1;if(!isNaN(aN)&&!isNaN(bN))return asc?aN-bN:bN-aN;return asc?aT.localeCompare(bT,'ko'):bT.localeCompare(aT,'ko')}});rows.forEach(function(r){{tb.appendChild(r)}});var allR=tb.querySelectorAll("tr");allR.forEach(function(r,i){{if(r.cells[0])r.cells[0].textContent=i+1}});t.querySelectorAll("thead th").forEach(function(h){{var ar=h.querySelector(".sa");if(!ar)return;var hi=parseInt(h.getAttribute("data-col"));if(hi===ci){{ar.textContent=asc?"▲":"▼";ar.className="sa active"}}else{{ar.textContent="▲▼";ar.className="sa"}}}});setTimeout(autoR,50)}}
window.addEventListener('load',function(){{_ld();applyF();autoR()}});
window.addEventListener('resize',function(){{applyF();autoR()}});
</script>"""
    return html


# ═══════════════════════════════════════════════════════
# 8. 메인 앱
# ═══════════════════════════════════════════════════════
def main():
    settings = load_settings()

    # 사이드바
    st.sidebar.title("메뉴")
    menu = st.sidebar.radio("이동", ["매니저 화면 (로그인)", "관리자 화면 (상태)"])

    # 데이터 로드
    sum_path, bridge_path, data_date = find_latest_files()

    if not sum_path:
        st.title("📊 GA3본부 시상 관리 시스템")
        st.error(f"❌ `{DATA_DIR}/` 폴더에 PRIZE_SUM_OUT_*.xlsx 파일이 없습니다.")
        st.markdown("""
        ### 📁 설정 방법
        1. 프로젝트 루트에 `data/` 폴더를 만드세요
        2. 아래 파일들을 넣고 GitHub에 push하세요:
           - `PRIZE_SUM_OUT_YYYYMMDD.xlsx`
           - `PRIZE_6_BRIDGE_OUT_YYYYMMDD.xlsx`
        3. Streamlit Cloud가 자동으로 최신 파일을 감지합니다
        """)
        st.stop()

    df_merged = load_and_merge(sum_path, bridge_path)
    prize_struct = detect_prize_structure(df_merged, settings)

    if menu == "관리자 화면 (상태)":
        show_admin(df_merged, prize_struct, sum_path, bridge_path, data_date, settings)
    else:
        show_manager(df_merged, prize_struct, data_date, settings)


def show_admin(df, ps, sum_path, bridge_path, data_date, settings):
    """최소 관리자 화면 — 상태 확인 + settings.json 안내"""
    st.title("⚙️ 시스템 상태")

    pw = st.text_input("🔒 관리자 비밀번호", type="password")
    if pw != settings.get('admin_password', 'wolf7998'):
        if pw:
            st.error("비밀번호가 틀립니다.")
        st.stop()

    st.success("✅ 로그인 성공")

    # 데이터 상태
    st.header("📁 로드된 데이터")
    st.markdown(f"- **SUM 파일**: `{os.path.basename(sum_path)}`")
    st.markdown(f"- **BRIDGE 파일**: `{os.path.basename(bridge_path)}`" if bridge_path else "- **BRIDGE 파일**: 없음")
    st.markdown(f"- **데이터 기준일**: {data_date or '감지 안됨'}")
    st.markdown(f"- **총 행 수**: {len(df):,}명")

    # 감지된 시상 구조
    st.header("🔍 자동 감지된 시상 구조")

    st.subheader("📌 주차별 시상")
    for w, info in ps['weeks'].items():
        with st.expander(f"{w}주차 — {len(info['prizes'])}개 항목", expanded=False):
            st.markdown(f"**실적 컬럼**: `{info['perf_col']}`")
            for p in info['prizes']:
                st.markdown(f"- **{p['label']}**: 대상=`{p['elig_col']}` → 시상=`{p['prize_col']}`")

    if ps['combined']:
        st.subheader("📎 합산 주차")
        for c in ps['combined']:
            st.markdown(f"- **{c['label']}**: `{c['elig_col']}` → `{c['prize_col']}`")

    if ps['cumulative']:
        st.subheader("📈 월 누계")
        st.markdown(f"- 실적: `{ps['cumulative']['perf_col']}` / 대상: `{ps['cumulative']['elig_col']}` → `{ps['cumulative']['prize_col']}`")

    if ps['bridge']:
        st.subheader("🌉 브릿지")
        b = ps['bridge']
        st.markdown(f"- {b['label_prev']}: `{b['prev_perf']}` / {b['label_curr']}: `{b['curr_perf']}`")
        st.markdown(f"- 시상금: `{b['prize_col']}` / 부족액: `{b.get('shortfall_col', '없음')}`")

    if ps['consecutive']:
        st.subheader("🔗 연속가동")
        c = ps['consecutive']
        st.markdown(f"- {c['label_prev']}: `{c['prev_perf']}` / {c['label_curr']}: `{c['curr_perf']}`")
        st.markdown(f"- 시상금: `{c['prize_col']}` / 부족액: `{c.get('shortfall_col', '없음')}`")

    if ps['next_bridge']:
        st.subheader("🔮 차기 브릿지")
        nb = ps['next_bridge']
        st.markdown(f"- {nb['label']}: `{nb['perf_col']}` / 부족: `{nb.get('shortfall_col', '없음')}`")

    st.divider()
    st.header("📝 설정 변경 안내")
    st.markdown("""
    시상 라벨이나 카톡 문구를 변경하려면 프로젝트 루트의 `settings.json`을 수정하세요:
    ```json
    {
      "admin_password": "wolf7998",
      "clip_footer": "카톡 하단 인사말...",
      "prize_labels": {
        "base": "인보험 기본",
        "상품": "상품 추가",
        "상품추가": "상품 추가2",
        "유퍼간편": "유퍼스트"
      }
    }
    ```
    """)


def show_manager(df, ps, data_date, settings):
    """매니저 화면 — 로그인 후 산하 설계사 실적 표시"""
    manager_col = '지원매니저코드'
    manager_name_col = '지원매니저명'

    if manager_col not in df.columns:
        st.title("👤 매니저 전용 실적 현황")
        st.error(f"데이터에 `{manager_col}` 컬럼이 없습니다.")
        st.stop()

    with st.form("login_form"):
        manager_code = st.text_input("🔑 매니저 코드를 입력하세요", type="password")
        submit = st.form_submit_button("로그인 및 조회")

    if not (submit and manager_code):
        st.title("👤 매니저 전용 실적 현황")
        st.info("매니저 코드를 입력하고 [로그인 및 조회]를 눌러주세요.")
        return

    code_clean = clean_key(manager_code)
    df['_mgr_key'] = df[manager_col].apply(clean_key)
    my_df = df[df['_mgr_key'] == code_clean].copy()

    if my_df.empty:
        # 부분 매칭 시도
        mask = df['_mgr_key'].str.contains(code_clean, na=False)
        my_df = df[mask].copy()

    if my_df.empty:
        st.error(f"❌ 매니저 코드 '{manager_code}'에 일치하는 데이터가 없습니다.")
        return

    # 매니저 이름
    manager_name = "매니저"
    if manager_name_col in my_df.columns:
        names = my_df[manager_name_col].dropna()
        if not names.empty:
            manager_name = str(names.iloc[0])

    # 정렬 (지사 → 설계사명)
    sort_cols = []
    if '대리점지사명' in my_df.columns: sort_cols.append('대리점지사명')
    if '대리점설계사명' in my_df.columns: sort_cols.append('대리점설계사명')
    if sort_cols:
        my_df = my_df.sort_values(by=sort_cols)

    # 표시 데이터 빌드
    display_df, col_groups, prize_data_map = build_display(my_df, ps, settings)

    # 헤더
    date_html = f"<span style='font-size:14px;color:rgba(255,255,255,0.85);float:right;margin-top:8px'>📅 {data_date}</span>" if data_date else ""
    st.markdown(f"""
    <div class='toss-header'>
        {date_html}
        <h1 class='toss-title'>{manager_name} <span class='toss-subtitle'>({code_clean})</span></h1>
        <p class='toss-desc'>산하 팀장분들의 실적·시상 현황입니다. (총 {len(display_df)}명)</p>
    </div>
    """, unsafe_allow_html=True)

    # HTML 테이블 렌더
    footer = settings.get('clip_footer', DEFAULT_SETTINGS['clip_footer'])
    table_html = render_html_table(display_df, col_groups, prize_data_map, data_date, footer)
    components.html(table_html, height=800, scrolling=False)


if __name__ == "__main__":
    main()
