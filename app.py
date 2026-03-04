import streamlit as st
import pandas as pd
import json
from agents import AGENT_LIST

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="GA 시상 계산기",
    page_icon="🏆",
    layout="wide",
)

# ── 스타일 ───────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem; font-weight: 700; color: #1e3a5f;
        padding-bottom: 0.3rem; border-bottom: 3px solid #1e3a5f; margin-bottom: 1.2rem;
    }
    .section-title {
        font-size: 1.1rem; font-weight: 600; color: #1e3a5f;
        background: #eef4fb; padding: 0.5rem 0.8rem;
        border-left: 4px solid #1e3a5f; border-radius: 2px; margin: 1rem 0 0.6rem 0;
    }
    .award-card {
        background: #f8fbff; border: 1px solid #d0e4f7;
        border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    }
    .result-box {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        color: white; border-radius: 10px; padding: 1.5rem;
        margin-top: 1rem;
    }
    .result-amount {
        font-size: 1.4rem; font-weight: 700; color: #ffd700;
    }
    .tier-badge {
        display: inline-block; background: #1e3a5f; color: white;
        border-radius: 20px; padding: 2px 12px; font-size: 0.85rem; font-weight: 600;
    }
    .stButton > button {
        background: #1e3a5f; color: white; border: none;
        border-radius: 6px; padding: 0.4rem 1.2rem; font-weight: 600;
    }
    .stButton > button:hover { background: #2d6a9f; }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ─────────────────────────────────────────
if "awards" not in st.session_state:
    st.session_state.awards = []   # 시상 항목 리스트
if "add_mode" not in st.session_state:
    st.session_state.add_mode = False

# ── 유틸 함수 ────────────────────────────────────────────────
DEFAULT_TIERS = [100_000, 200_000, 300_000, 500_000]   # 10만/20만/30만/50만

def fmt_won(v: float) -> str:
    """원화 표시 (소수점 없이, 천 단위 콤마)"""
    return f"{int(round(v)):,}원"

def fmt_rate(r: float) -> str:
    return f"{r:.0f}%"

def calc_flat(perf: int, rate: float) -> float:
    """정률: 실적 × 시책률"""
    return perf * rate / 100

def calc_tiered(perf: int, tiers: list[dict]) -> float:
    """
    구간별: 각 구간 [(from, to, rate), ...] 에서 해당 구간 실적에 률 적용 후 합산.
    tiers = [{"from": 0, "to": 100000, "rate": 100}, {"from": 100000, "to": 200000, "rate": 150}, ...]
    to=-1 이면 무제한 상한.
    """
    total = 0.0
    sorted_tiers = sorted(tiers, key=lambda x: x["from"])
    for t in sorted_tiers:
        lo = t["from"]
        hi = t["to"] if t["to"] != -1 else perf
        if perf <= lo:
            break
        applicable = min(perf, hi) - lo
        if applicable > 0:
            total += applicable * t["rate"] / 100
    return total

def calc_award(award: dict, perf: int) -> float:
    if award["type"] == "정률":
        return calc_flat(perf, award["rate"])
    else:
        return calc_tiered(perf, award["tiers"])

def remove_award(idx: int):
    st.session_state.awards.pop(idx)

# ── 헤더 ─────────────────────────────────────────────────────
st.markdown('<div class="main-title">🏆 GA 시상 계산기</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1, 2], gap="large")

# ══════════════════════════════════════════════════════════════
# 왼쪽 패널 : 대리점 선택 + 시상 항목 등록
# ══════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="section-title">📌 대리점 선택</div>', unsafe_allow_html=True)
    selected_agent = st.selectbox(
        "대리점을 선택하세요",
        options=["-- 선택 --"] + sorted(AGENT_LIST),
        label_visibility="collapsed",
    )

    # ── 실적 기준 설정 ─────────────────────────────────────────
    st.markdown('<div class="section-title">📊 실적 기준 설정</div>', unsafe_allow_html=True)

    custom_tiers_str = st.text_input(
        "시산 기준 실적 (만원, 쉼표 구분)",
        value="10, 20, 30, 50",
        help="예: 10, 20, 30, 50  →  10만/20만/30만/50만원 체결 시 시상액 계산",
    )
    try:
        perf_tiers = [int(x.strip()) * 10_000 for x in custom_tiers_str.split(",") if x.strip()]
        if not perf_tiers:
            perf_tiers = DEFAULT_TIERS
    except ValueError:
        st.warning("숫자를 쉼표로 구분해 입력하세요.")
        perf_tiers = DEFAULT_TIERS

    # ── 시상 항목 등록 ─────────────────────────────────────────
    st.markdown('<div class="section-title">🎁 시상 항목 등록</div>', unsafe_allow_html=True)

    if st.button("＋ 시상 항목 추가", use_container_width=True):
        st.session_state.add_mode = True

    # 항목 추가 폼
    if st.session_state.add_mode:
        with st.container(border=True):
            st.markdown("**새 시상 항목**")
            a_name = st.text_input("시상 이름", key="new_name", placeholder="예: 장기보험 시상")
            a_desc = st.text_input("시상 내용", key="new_desc", placeholder="예: 장기 실적 기준 정률 지급")
            a_type = st.radio("계산 방식", ["정률", "구간별"], horizontal=True, key="new_type")

            if a_type == "정률":
                a_rate = st.number_input(
                    "시책률 (%)", min_value=0.0, max_value=10000.0,
                    value=100.0, step=10.0, key="new_rate",
                    help="실적 전체에 동일 률 적용. 예: 100% → 실적과 동일 금액 지급"
                )
                preview_tiers = None
            else:
                st.markdown("**구간 설정** (구간 하한/상한/률 입력)")
                st.caption("상한을 비워두면 '이상' 으로 처리됩니다.")

                if "new_tiers" not in st.session_state:
                    st.session_state.new_tiers = [{"from": 0, "to": 100_000, "rate": 100.0}]

                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.markdown("**하한(만원)**")
                c2.markdown("**상한(만원)**")
                c3.markdown("**률(%)**")
                c4.markdown("&nbsp;")

                updated_tiers = []
                to_remove = None
                for i, tier in enumerate(st.session_state.new_tiers):
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    lo_val = c1.number_input("", min_value=0, value=tier["from"]//10_000,
                                             key=f"t_lo_{i}", label_visibility="collapsed")
                    hi_str = "" if tier["to"] == -1 else str(tier["to"] // 10_000)
                    hi_input = c2.text_input("", value=hi_str,
                                             key=f"t_hi_{i}", label_visibility="collapsed",
                                             placeholder="이상")
                    rt_val = c3.number_input("", min_value=0.0, value=float(tier["rate"]),
                                             step=10.0, key=f"t_rt_{i}", label_visibility="collapsed")
                    if c4.button("✕", key=f"del_tier_{i}") and len(st.session_state.new_tiers) > 1:
                        to_remove = i

                    hi_val = -1 if hi_input.strip() == "" else int(hi_input) * 10_000
                    updated_tiers.append({"from": lo_val * 10_000, "to": hi_val, "rate": rt_val})

                if to_remove is not None:
                    st.session_state.new_tiers.pop(to_remove)
                    st.rerun()
                else:
                    st.session_state.new_tiers = updated_tiers

                if st.button("＋ 구간 추가", key="add_tier_btn"):
                    last = st.session_state.new_tiers[-1]
                    new_lo = last["to"] if last["to"] != -1 else (last["from"] + 100_000)
                    st.session_state.new_tiers.append({"from": new_lo, "to": -1, "rate": 100.0})
                    st.rerun()

                preview_tiers = st.session_state.new_tiers
                a_rate = None

            ca, cb = st.columns(2)
            if ca.button("✅ 저장", use_container_width=True):
                if not a_name.strip():
                    st.error("시상 이름을 입력하세요.")
                else:
                    entry = {
                        "name": a_name.strip(),
                        "desc": a_desc.strip(),
                        "type": a_type,
                        "rate": a_rate if a_type == "정률" else None,
                        "tiers": preview_tiers if a_type == "구간별" else None,
                    }
                    st.session_state.awards.append(entry)
                    st.session_state.add_mode = False
                    if "new_tiers" in st.session_state:
                        del st.session_state.new_tiers
                    st.rerun()
            if cb.button("❌ 취소", use_container_width=True):
                st.session_state.add_mode = False
                if "new_tiers" in st.session_state:
                    del st.session_state.new_tiers
                st.rerun()

    # ── 등록된 시상 항목 목록 ──────────────────────────────────
    if st.session_state.awards:
        st.markdown(f"**등록된 시상 항목 ({len(st.session_state.awards)}개)**")
        for i, aw in enumerate(st.session_state.awards):
            with st.container():
                cols = st.columns([5, 1])
                with cols[0]:
                    badge = "📐 정률" if aw["type"] == "정률" else "📊 구간별"
                    rate_info = f"{aw['rate']}%" if aw["type"] == "정률" else f"{len(aw['tiers'])}구간"
                    st.markdown(
                        f"<div class='award-card'>"
                        f"<b>{aw['name']}</b> &nbsp; <small>{badge} · {rate_info}</small><br>"
                        f"<small style='color:#555'>{aw['desc'] or '(내용 없음)'}</small>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    if st.button("🗑", key=f"del_{i}", help="삭제"):
                        remove_award(i)
                        st.rerun()

# ══════════════════════════════════════════════════════════════
# 오른쪽 패널 : 시상 계산 결과
# ══════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div class="section-title">💰 시상 계산 결과</div>', unsafe_allow_html=True)

    if selected_agent == "-- 선택 --":
        st.info("👈 왼쪽에서 대리점을 선택하세요.")
    elif not st.session_state.awards:
        st.info("👈 시상 항목을 하나 이상 추가하세요.")
    else:
        st.markdown(f"**대리점:** `{selected_agent}`")

        # ── 결과 테이블 ─────────────────────────────────────────
        tier_labels = [f"{p//10_000}만원" for p in perf_tiers]
        rows = []
        for aw in st.session_state.awards:
            row = {"시상항목": aw["name"], "계산방식": aw["type"]}
            for label, perf in zip(tier_labels, perf_tiers):
                amt = calc_award(aw, perf)
                row[label] = fmt_won(amt)
            rows.append(row)

        # 합계 행
        total_row = {"시상항목": "✅ 합계", "계산방식": "—"}
        for label, perf in zip(tier_labels, perf_tiers):
            total = sum(calc_award(aw, perf) for aw in st.session_state.awards)
            total_row[label] = fmt_won(total)
        rows.append(total_row)

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "시상항목": st.column_config.TextColumn("시상항목", width="medium"),
                "계산방식": st.column_config.TextColumn("방식", width="small"),
            },
        )

        # ── 카드형 상세 결과 ─────────────────────────────────────
        st.markdown("---")
        st.markdown("**📋 실적별 상세 내역**")
        cols_result = st.columns(len(perf_tiers))

        for col, (label, perf) in zip(cols_result, zip(tier_labels, perf_tiers)):
            with col:
                total = sum(calc_award(aw, perf) for aw in st.session_state.awards)
                st.markdown(
                    f"""
                    <div style='background:#1e3a5f;color:white;border-radius:10px;
                                padding:1rem;text-align:center;margin-bottom:0.5rem'>
                        <div style='font-size:0.9rem;opacity:0.8'>체결 실적</div>
                        <div style='font-size:1.3rem;font-weight:700;color:#ffd700'>{label}</div>
                        <div style='font-size:0.8rem;opacity:0.7;margin-top:0.5rem'>총 시상액</div>
                        <div style='font-size:1.1rem;font-weight:700'>{fmt_won(total)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                for aw in st.session_state.awards:
                    amt = calc_award(aw, perf)
                    st.markdown(
                        f"<div style='font-size:0.8rem;padding:2px 4px'>"
                        f"<b>{aw['name']}</b>: {fmt_won(amt)}</div>",
                        unsafe_allow_html=True,
                    )

        # ── 시상 항목 상세 정보 ──────────────────────────────────
        st.markdown("---")
        st.markdown("**🔍 시상 항목 설정 상세**")
        for aw in st.session_state.awards:
            with st.expander(f"📌 {aw['name']}  ({aw['type']})"):
                if aw["desc"]:
                    st.markdown(f"**내용:** {aw['desc']}")
                if aw["type"] == "정률":
                    st.markdown(f"**시책률:** {aw['rate']}%")
                    st.markdown(f"**계산식:** 체결실적 × {aw['rate']}%")
                else:
                    tier_data = []
                    for t in aw["tiers"]:
                        lo = f"{t['from']//10_000}만원"
                        hi = f"{t['to']//10_000}만원" if t["to"] != -1 else "이상"
                        tier_data.append({"구간 하한": lo, "구간 상한": hi, "시책률": f"{t['rate']}%"})
                    st.dataframe(pd.DataFrame(tier_data), hide_index=True, use_container_width=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.caption("GA 시상 계산기 · Meritz Fire Insurance")
