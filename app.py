"""
GA 시상 계산기
- 관리자 화면: 비번 인증 → 대리점별 시상 항목 CRUD + 저장
- 조회 화면:   대리점 선택 → 실적별 시상금 표시 (토스풍 디자인, 다크레드 #800000)
"""

import streamlit as st
import json
import os
import copy
from agents import AGENT_LIST

# ── 설정 ─────────────────────────────────────────────────────
ADMIN_PASSWORD = "meritz0505"
DATA_FILE = "awards_data.json"
DEFAULT_PERFS = [100_000, 200_000, 300_000, 500_000]

st.set_page_config(
    page_title="GA 시상 계산기",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# 데이터 영속성 (JSON 파일)
# ══════════════════════════════════════════════════════════════
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════
# 계산 유틸
# ══════════════════════════════════════════════════════════════
def calc_award(award: dict, perf: int) -> float:
    if award["type"] == "정률":
        return perf * award["rate"] / 100
    # 구간별
    total = 0.0
    for t in sorted(award["tiers"], key=lambda x: x["from"]):
        lo, hi, rt = t["from"], t["to"], t["rate"]
        if perf <= lo:
            break
        applicable = min(perf, hi if hi != -1 else perf) - lo
        if applicable > 0:
            total += applicable * rt / 100
    return total

def fmt_won(v: float) -> str:
    return f"{int(round(v)):,}원"

def fmt_man(v: int) -> str:
    if v % 10_000 == 0:
        return f"{v // 10_000}만원"
    return f"{v:,}원"

# ══════════════════════════════════════════════════════════════
# 세션 상태 초기화
# ══════════════════════════════════════════════════════════════
if "page" not in st.session_state:
    st.session_state.page = "viewer"          # viewer | admin
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False
if "all_data" not in st.session_state:
    st.session_state.all_data = load_data()   # {agent: [award, ...]}
if "edit_awards" not in st.session_state:
    st.session_state.edit_awards = []         # 편집 중인 대리점 시상 목록
if "edit_agent" not in st.session_state:
    st.session_state.edit_agent = None
if "add_mode" not in st.session_state:
    st.session_state.add_mode = False
if "editing_idx" not in st.session_state:
    st.session_state.editing_idx = None       # 수정 중인 항목 인덱스


# ══════════════════════════════════════════════════════════════
# 사이드바 네비게이션
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1rem 0 0.5rem'>
        <span style='font-size:2rem'>🏆</span><br>
        <b style='font-size:1.1rem;color:#800000'>GA 시상 계산기</b>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if st.button("📊  실적별 시상 조회", use_container_width=True,
                 type="primary" if st.session_state.page == "viewer" else "secondary"):
        st.session_state.page = "viewer"
        st.rerun()

    if st.button("⚙️  관리자 설정", use_container_width=True,
                 type="primary" if st.session_state.page == "admin" else "secondary"):
        st.session_state.page = "admin"
        st.rerun()

    st.markdown("---")
    st.caption("Meritz Fire Insurance")


# ══════════════════════════════════════════════════════════════
# ██████████████  조회 화면 (토스 스타일)  ██████████████████████
# ══════════════════════════════════════════════════════════════
VIEWER_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* 전체 배경 */
.stApp { background: #f5f5f7; }

/* 사이드바 */
section[data-testid="stSidebar"] {
    background: #1a0000 !important;
}
section[data-testid="stSidebar"] * { color: #f0e0e0 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    color: #f0e0e0 !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(128,0,0,0.6) !important;
}
section[data-testid="stSidebar"] [data-testid="stButton-primary"] > button {
    background: #800000 !important;
    border-color: #800000 !important;
}

/* 헤더 배너 */
.viewer-hero {
    background: linear-gradient(135deg, #800000 0%, #5a0000 50%, #3a0000 100%);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(128,0,0,0.3);
    position: relative;
    overflow: hidden;
}
.viewer-hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
}
.viewer-hero::after {
    content: '';
    position: absolute;
    bottom: -30%;
    right: 15%;
    width: 200px;
    height: 200px;
    background: rgba(255,255,255,0.04);
    border-radius: 50%;
}
.hero-title {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0 0 0.3rem;
}
.hero-sub {
    font-size: 0.9rem;
    opacity: 0.75;
    font-weight: 400;
}

/* 실적 선택 칩 */
.perf-selector {
    display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0;
}

/* 결과 카드 컨테이너 */
.result-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
}
/* 실적 카드 */
.perf-card {
    background: white;
    border-radius: 16px;
    padding: 1.4rem 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border: 2px solid transparent;
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
}
.perf-card.active {
    border-color: #800000;
    box-shadow: 0 4px 20px rgba(128,0,0,0.18);
}
.perf-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #800000, #cc0000);
    opacity: 0;
    transition: opacity 0.2s;
}
.perf-card.active::before { opacity: 1; }

.perf-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #800000;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.perf-amount {
    font-size: 1.6rem;
    font-weight: 800;
    color: #1a1a1a;
    letter-spacing: -0.03em;
    line-height: 1.2;
}
.perf-unit {
    font-size: 0.95rem;
    font-weight: 500;
    color: #666;
}

/* 시상 항목 상세 카드 */
.award-detail-card {
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.award-name {
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 0.2rem;
}
.award-desc-text {
    font-size: 0.82rem;
    color: #888;
    margin-bottom: 1rem;
}
.award-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f0f0f0;
}
.award-row:last-child { border-bottom: none; }
.award-row-label {
    font-size: 0.85rem;
    color: #555;
    font-weight: 500;
}
.award-row-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: #800000;
}

/* 총합 배너 */
.total-banner {
    background: linear-gradient(135deg, #800000, #5a0000);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 1rem 0;
    box-shadow: 0 4px 20px rgba(128,0,0,0.25);
}
.total-label { font-size: 0.9rem; opacity: 0.8; }
.total-amount { font-size: 2rem; font-weight: 800; letter-spacing: -0.03em; }

/* 섹션 타이틀 */
.section-label {
    font-size: 0.8rem;
    font-weight: 700;
    color: #800000;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 1.5rem 0 0.75rem;
}

/* 빈 상태 */
.empty-state {
    text-align: center;
    padding: 3rem;
    color: #aaa;
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-text { font-size: 1rem; font-weight: 500; }

/* 배지 */
.type-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: 0.5rem;
    vertical-align: middle;
}
.badge-flat { background: #fff0f0; color: #800000; }
.badge-tier { background: #f0f4ff; color: #2040a0; }

/* selectbox 커스텀 */
div[data-baseweb="select"] > div {
    border-radius: 12px !important;
    border-color: #e0e0e0 !important;
    background: white !important;
    font-weight: 600 !important;
}

/* 합계 테이블 */
.sum-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-top: 1rem;
}
.sum-table th {
    background: #800000;
    color: white;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    font-weight: 700;
    text-align: right;
}
.sum-table th:first-child { text-align: left; }
.sum-table td {
    padding: 0.7rem 1rem;
    font-size: 0.9rem;
    border-bottom: 1px solid #f5f5f5;
    text-align: right;
}
.sum-table td:first-child { text-align: left; font-weight: 600; color: #333; }
.sum-table tr:last-child td {
    background: #fff8f8;
    font-weight: 800;
    color: #800000;
    border-bottom: none;
}
.sum-table tr:hover td { background: #fdf5f5; }

/* 실적 입력 */
.stTextInput input {
    border-radius: 12px !important;
    border: 1px solid #e0e0e0 !important;
    font-weight: 600 !important;
}
</style>
"""

# ══════════════════════════════════════════════════════════════
# 관리자 화면 CSS
# ══════════════════════════════════════════════════════════════
ADMIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, sans-serif !important;
}
.stApp { background: #fafafa; }

section[data-testid="stSidebar"] {
    background: #1a0000 !important;
}
section[data-testid="stSidebar"] * { color: #f0e0e0 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    color: #f0e0e0 !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(128,0,0,0.6) !important;
}
section[data-testid="stSidebar"] [data-testid="stButton-primary"] > button {
    background: #800000 !important;
    border-color: #800000 !important;
}

.admin-header {
    background: #1a0000;
    color: white;
    padding: 1.2rem 1.8rem;
    border-radius: 14px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.admin-header-title { font-size: 1.3rem; font-weight: 800; }
.admin-header-sub { font-size: 0.82rem; opacity: 0.6; margin-top: 2px; }

.admin-section {
    background: white;
    border-radius: 14px;
    padding: 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    border: 1px solid #f0f0f0;
}
.admin-section-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: #800000;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #f5e5e5;
}

.award-item-card {
    background: #fafafa;
    border: 1px solid #ebebeb;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.6rem;
    transition: all 0.15s;
}
.award-item-card:hover { border-color: #800000; background: #fff8f8; }
.award-item-name { font-weight: 700; color: #1a1a1a; font-size: 0.95rem; }
.award-item-meta { font-size: 0.78rem; color: #888; margin-top: 2px; }

.save-bar {
    position: sticky;
    bottom: 0;
    background: white;
    padding: 1rem;
    border-top: 1px solid #f0f0f0;
    border-radius: 0 0 14px 14px;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.08);
    z-index: 100;
}

/* 버튼 공통 */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 700 !important;
    transition: all 0.15s !important;
}

div[data-baseweb="select"] > div {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

.stTextInput input, .stNumberInput input {
    border-radius: 8px !important;
}
</style>
"""


# ══════════════════════════════════════════════════════════════
# ██  조회 화면  █████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════
def page_viewer():
    st.markdown(VIEWER_CSS, unsafe_allow_html=True)

    # 헤더 배너
    st.markdown("""
    <div class="viewer-hero">
        <div class="hero-title">🏆 GA 시상 계산기</div>
        <div class="hero-sub">대리점을 선택하면 실적별 시상금을 확인할 수 있습니다</div>
    </div>
    """, unsafe_allow_html=True)

    col_sel, col_perf = st.columns([2, 3], gap="large")

    with col_sel:
        st.markdown('<div class="section-label">대리점 선택</div>', unsafe_allow_html=True)
        selected_agent = st.selectbox(
            "대리점",
            options=["대리점을 선택하세요"] + AGENT_LIST,
            label_visibility="collapsed",
            key="viewer_agent",
        )

    with col_perf:
        st.markdown('<div class="section-label">실적 기준 (만원, 쉼표 구분)</div>', unsafe_allow_html=True)
        perf_input = st.text_input(
            "실적",
            value="10, 20, 30, 50",
            label_visibility="collapsed",
            key="viewer_perfs",
        )

    try:
        perf_list = [int(x.strip()) * 10_000 for x in perf_input.split(",") if x.strip().isdigit()]
        if not perf_list:
            perf_list = DEFAULT_PERFS
    except Exception:
        perf_list = DEFAULT_PERFS

    # 대리점 미선택
    if selected_agent == "대리점을 선택하세요":
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🏢</div>
            <div class="empty-text">대리점을 선택해 주세요</div>
        </div>
        """, unsafe_allow_html=True)
        return

    awards = st.session_state.all_data.get(selected_agent, [])

    # 시상 미등록
    if not awards:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-icon">📋</div>
            <div class="empty-text"><b>{selected_agent}</b>에 등록된 시상 항목이 없습니다<br>
            <span style="font-size:0.85rem;color:#bbb">관리자 화면에서 시상 항목을 추가하세요</span></div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── 실적별 총합 카드 ──────────────────────────────────────
    st.markdown(f'<div class="section-label">{selected_agent} · 실적별 총 시상금</div>', unsafe_allow_html=True)

    # 총합 테이블
    perf_labels = [fmt_man(p) for p in perf_list]
    header_cells = "".join(f"<th>{lbl}</th>" for lbl in perf_labels)
    totals = [sum(calc_award(aw, p) for aw in awards) for p in perf_list]

    rows_html = ""
    for aw in awards:
        cells = "".join(
            f"<td>{fmt_won(calc_award(aw, p))}</td>" for p in perf_list
        )
        badge = f"<span class='type-badge badge-flat'>정률</span>" if aw["type"] == "정률" else \
                f"<span class='type-badge badge-tier'>구간</span>"
        rows_html += f"<tr><td>{aw['name']}{badge}</td>{cells}</tr>"

    total_cells = "".join(f"<td>{fmt_won(t)}</td>" for t in totals)
    rows_html += f"<tr><td>✅ 합계</td>{total_cells}</tr>"

    st.markdown(f"""
    <table class="sum-table">
        <thead><tr>
            <th>시상항목</th>{header_cells}
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

    # ── 시상 항목 상세 ────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:2rem">시상 항목별 상세</div>',
                unsafe_allow_html=True)

    for aw in awards:
        badge_cls = "badge-flat" if aw["type"] == "정률" else "badge-tier"
        badge_txt = "정률" if aw["type"] == "정률" else "구간별"

        rows_inner = ""
        for p, lbl in zip(perf_list, perf_labels):
            amt = calc_award(aw, p)
            rows_inner += f"""
            <div class="award-row">
                <span class="award-row-label">체결 {lbl}</span>
                <span class="award-row-value">{fmt_won(amt)}</span>
            </div>"""

        if aw["type"] == "정률":
            method_info = f"전체 실적 × {aw['rate']}%"
        else:
            tier_strs = []
            for t in aw["tiers"]:
                lo = fmt_man(t["from"])
                hi = fmt_man(t["to"]) if t["to"] != -1 else "이상"
                tier_strs.append(f"{lo}~{hi}: {t['rate']}%")
            method_info = " / ".join(tier_strs)

        st.markdown(f"""
        <div class="award-detail-card">
            <div class="award-name">
                {aw['name']}
                <span class="type-badge {badge_cls}">{badge_txt}</span>
            </div>
            <div class="award-desc-text">{aw.get('desc', '') or method_info}</div>
            {rows_inner}
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# ██  관리자 화면  ████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════
def render_tier_editor(tiers: list, key_prefix: str) -> list:
    """구간 편집기 — 현재 tiers 반환"""
    updated = []
    to_remove = None

    c0, c1, c2, c3, c4 = st.columns([0.3, 2, 2, 2, 0.5])
    c0.markdown("**#**")
    c1.markdown("**하한(만원)**")
    c2.markdown("**상한(만원)**")
    c3.markdown("**률(%)**")

    for i, t in enumerate(tiers):
        c0, c1, c2, c3, c4 = st.columns([0.3, 2, 2, 2, 0.5])
        c0.markdown(f"<div style='padding-top:0.5rem;color:#888'>{i+1}</div>", unsafe_allow_html=True)
        lo = c1.number_input("", min_value=0, value=t["from"] // 10_000,
                             key=f"{key_prefix}_lo_{i}", label_visibility="collapsed")
        hi_str = "" if t["to"] == -1 else str(t["to"] // 10_000)
        hi_inp = c2.text_input("", value=hi_str, placeholder="이상(무제한)",
                               key=f"{key_prefix}_hi_{i}", label_visibility="collapsed")
        rt = c3.number_input("", min_value=0.0, max_value=10000.0, value=float(t["rate"]),
                             step=10.0, key=f"{key_prefix}_rt_{i}", label_visibility="collapsed")
        if c4.button("✕", key=f"{key_prefix}_del_{i}") and len(tiers) > 1:
            to_remove = i

        hi_val = -1 if hi_inp.strip() == "" else int(hi_inp) * 10_000
        updated.append({"from": lo * 10_000, "to": hi_val, "rate": rt})

    if to_remove is not None:
        updated.pop(to_remove)
        return updated, True   # (list, need_rerun)

    if st.button("＋ 구간 추가", key=f"{key_prefix}_add"):
        last = updated[-1]
        new_lo = last["to"] if last["to"] != -1 else (last["from"] + 100_000)
        updated.append({"from": new_lo, "to": -1, "rate": 100.0})
        return updated, True

    return updated, False


def award_form(prefix: str, init: dict | None = None) -> dict | None:
    """
    시상 항목 입력 폼.
    저장 클릭 시 dict 반환, 취소/미완성 시 None 반환.
    """
    init = init or {}
    name = st.text_input("시상 이름 *", value=init.get("name", ""),
                         key=f"{prefix}_name", placeholder="예: 장기보험 GA 시상")
    desc = st.text_input("시상 내용", value=init.get("desc", ""),
                         key=f"{prefix}_desc", placeholder="예: 장기 실적 기준 지급")
    atype = st.radio("계산 방식", ["정률", "구간별"], horizontal=True,
                     index=0 if init.get("type", "정률") == "정률" else 1,
                     key=f"{prefix}_type")

    result = None
    if atype == "정률":
        rate = st.number_input("시책률 (%)", min_value=0.0, max_value=10000.0,
                               value=float(init.get("rate") or 100.0),
                               step=10.0, key=f"{prefix}_rate",
                               help="실적 전체에 동일 비율 적용")

        col_save, col_cancel = st.columns(2)
        if col_save.button("✅ 저장", key=f"{prefix}_save", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("시상 이름을 입력하세요.")
            else:
                result = {"name": name.strip(), "desc": desc.strip(),
                          "type": "정률", "rate": rate, "tiers": None}
        if col_cancel.button("취소", key=f"{prefix}_cancel", use_container_width=True):
            result = "cancel"
    else:
        st.markdown("**구간 설정**")
        tier_key = f"{prefix}_tiers_state"
        if tier_key not in st.session_state:
            st.session_state[tier_key] = copy.deepcopy(
                init.get("tiers") or [{"from": 0, "to": 100_000, "rate": 100.0}]
            )
        new_tiers, need_rerun = render_tier_editor(st.session_state[tier_key], prefix)
        st.session_state[tier_key] = new_tiers
        if need_rerun:
            st.rerun()

        col_save, col_cancel = st.columns(2)
        if col_save.button("✅ 저장", key=f"{prefix}_save", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("시상 이름을 입력하세요.")
            else:
                result = {"name": name.strip(), "desc": desc.strip(),
                          "type": "구간별", "rate": None,
                          "tiers": copy.deepcopy(st.session_state[tier_key])}
        if col_cancel.button("취소", key=f"{prefix}_cancel", use_container_width=True):
            result = "cancel"

    return result


def page_admin():
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)

    # ── 비밀번호 인증 ──────────────────────────────────────────
    if not st.session_state.admin_auth:
        st.markdown("""
        <div style='max-width:420px;margin:4rem auto;text-align:center'>
            <div style='font-size:3rem'>🔐</div>
            <h2 style='color:#800000;margin:0.5rem 0 0.2rem'>관리자 로그인</h2>
            <p style='color:#888;font-size:0.9rem'>관리자 비밀번호를 입력하세요</p>
        </div>
        """, unsafe_allow_html=True)

        col_c = st.columns([1, 2, 1])[1]
        with col_c:
            pw = st.text_input("비밀번호", type="password", label_visibility="collapsed",
                               placeholder="비밀번호 입력", key="admin_pw_input")
            if st.button("로그인", use_container_width=True, type="primary"):
                if pw == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        return

    # ── 관리자 헤더 ────────────────────────────────────────────
    col_h, col_logout = st.columns([5, 1])
    with col_h:
        st.markdown("""
        <div class="admin-header">
            <span style="font-size:1.8rem">⚙️</span>
            <div>
                <div class="admin-header-title">관리자 설정</div>
                <div class="admin-header-sub">대리점별 시상 항목을 관리하고 저장합니다</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_logout:
        if st.button("로그아웃", key="logout"):
            st.session_state.admin_auth = False
            st.rerun()

    # ── 대리점 선택 ────────────────────────────────────────────
    col_a, col_b = st.columns([3, 1], gap="medium")
    with col_a:
        with st.container():
            st.markdown('<div class="admin-section">', unsafe_allow_html=True)
            st.markdown('<div class="admin-section-title">대리점 선택</div>', unsafe_allow_html=True)
            agent = st.selectbox("대리점", ["대리점을 선택하세요"] + AGENT_LIST,
                                 label_visibility="collapsed", key="admin_agent")
            st.markdown('</div>', unsafe_allow_html=True)

        # 대리점 변경 시 편집 목록 로드
        if agent != "대리점을 선택하세요":
            if st.session_state.edit_agent != agent:
                st.session_state.edit_agent = agent
                st.session_state.edit_awards = copy.deepcopy(
                    st.session_state.all_data.get(agent, [])
                )
                st.session_state.add_mode = False
                st.session_state.editing_idx = None

    if agent == "대리점을 선택하세요":
        st.info("👆 대리점을 선택하면 시상 항목을 관리할 수 있습니다.")
        return

    awards = st.session_state.edit_awards

    with col_b:
        st.markdown('<div class="admin-section">', unsafe_allow_html=True)
        st.markdown('<div class="admin-section-title">현황</div>', unsafe_allow_html=True)
        st.metric("등록 시상 수", f"{len(awards)}개")
        saved = st.session_state.all_data.get(agent, [])
        saved_cnt = len(saved)
        st.caption(f"저장된 항목: {saved_cnt}개")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 시상 항목 목록 ─────────────────────────────────────────
    left_col, right_col = st.columns([5, 4], gap="large")

    with left_col:
        st.markdown('<div class="admin-section">', unsafe_allow_html=True)
        st.markdown('<div class="admin-section-title">시상 항목 목록</div>', unsafe_allow_html=True)

        if not awards:
            st.markdown('<p style="color:#aaa;text-align:center;padding:1.5rem 0">등록된 시상 항목이 없습니다</p>',
                        unsafe_allow_html=True)
        else:
            for i, aw in enumerate(awards):
                is_editing = st.session_state.editing_idx == i
                badge = "정률" if aw["type"] == "정률" else "구간별"
                rate_info = f"{aw['rate']}%" if aw["type"] == "정률" else f"{len(aw['tiers'])}구간"

                bg = "#fff8f8" if is_editing else "#fafafa"
                border = "2px solid #800000" if is_editing else "1px solid #ebebeb"

                st.markdown(f"""
                <div class="award-item-card" style="background:{bg};border:{border}">
                    <div class="award-item-name">{aw['name']}
                        <span style='font-size:0.72rem;background:#f5e5e5;color:#800000;
                        padding:1px 7px;border-radius:20px;margin-left:6px;font-weight:600'>
                        {badge} · {rate_info}</span>
                    </div>
                    <div class="award-item-meta">{aw.get('desc') or '(설명 없음)'}</div>
                </div>
                """, unsafe_allow_html=True)

                btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 3])
                if btn_c1.button("✏️ 수정", key=f"edit_{i}", use_container_width=True):
                    st.session_state.editing_idx = i
                    st.session_state.add_mode = False
                    st.rerun()
                if btn_c2.button("🗑 삭제", key=f"del_{i}", use_container_width=True):
                    awards.pop(i)
                    if st.session_state.editing_idx == i:
                        st.session_state.editing_idx = None
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # ── 저장 버튼 ────────────────────────────────────────
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("💾  저장 (대리점 전체 시상 확정)", use_container_width=True,
                     type="primary", key="save_btn"):
            st.session_state.all_data[agent] = copy.deepcopy(awards)
            save_data(st.session_state.all_data)
            st.success(f"✅ '{agent}' 시상 항목이 저장되었습니다! ({len(awards)}개)")

        if st.button("＋ 시상 항목 추가", use_container_width=True, key="add_btn"):
            st.session_state.add_mode = True
            st.session_state.editing_idx = None
            st.rerun()

    # ── 오른쪽: 추가 / 수정 폼 ───────────────────────────────
    with right_col:
        if st.session_state.add_mode:
            st.markdown('<div class="admin-section">', unsafe_allow_html=True)
            st.markdown('<div class="admin-section-title">새 시상 항목 추가</div>', unsafe_allow_html=True)
            result = award_form("add_form")
            if result == "cancel":
                st.session_state.add_mode = False
                st.rerun()
            elif result is not None:
                awards.append(result)
                st.session_state.add_mode = False
                # 구간 임시 상태 삭제
                if "add_form_tiers_state" in st.session_state:
                    del st.session_state["add_form_tiers_state"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.editing_idx is not None:
            idx = st.session_state.editing_idx
            if 0 <= idx < len(awards):
                st.markdown('<div class="admin-section">', unsafe_allow_html=True)
                st.markdown(f'<div class="admin-section-title">시상 항목 수정 — #{idx+1}</div>',
                            unsafe_allow_html=True)
                result = award_form(f"edit_form_{idx}", init=copy.deepcopy(awards[idx]))
                if result == "cancel":
                    st.session_state.editing_idx = None
                    st.rerun()
                elif result is not None:
                    awards[idx] = result
                    st.session_state.editing_idx = None
                    # 구간 임시 상태 삭제
                    key = f"edit_form_{idx}_tiers_state"
                    if key in st.session_state:
                        del st.session_state[key]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='text-align:center;padding:3rem 1rem;color:#ccc'>
                <div style='font-size:2.5rem'>📝</div>
                <div style='margin-top:0.5rem;font-weight:500'>
                    항목을 선택하거나<br>추가 버튼을 눌러주세요
                </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 라우터
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "viewer":
    page_viewer()
else:
    page_admin()
