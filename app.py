"""
GA 시상 계산기 — 섬네일 + 카드뉴스 버전
입력 → 섬네일 목록 → 클릭 → 좌(시상 사진) / 우(카드뉴스 시상금)
"""

import streamlit as st
import json, os, copy, base64
from agents import AGENT_LIST

# ── 설정 ─────────────────────────────────────────────────────
DATA_FILE = "awards_data.json"
PERF_LEVELS = [10, 20, 30, 50]

st.set_page_config(
    page_title="GA 시상 계산기",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════
# 데이터 I/O
# ══════════════════════════════════════════════════════════════
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "all_data" not in st.session_state:
    st.session_state.all_data = load_data()
if "view_agent" not in st.session_state:
    st.session_state.view_agent = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

def fmt_won(v: float) -> str:
    return f"{int(round(v)):,}원"

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'Pretendard',-apple-system,sans-serif!important}
.stApp{background:#f5f5f7!important}

/* 헤더 */
.top-bar{
  background:linear-gradient(135deg,#800000 0%,#5a0000 55%,#380000 100%);
  border-radius:16px;padding:1.4rem 2rem;color:#fff;margin-bottom:1.2rem;
  box-shadow:0 6px 24px rgba(128,0,0,.22);position:relative;overflow:hidden}
.top-bar::before{content:'';position:absolute;top:-50%;right:-3%;
  width:260px;height:260px;background:rgba(255,255,255,.04);border-radius:50%}
.top-title{font-size:1.4rem;font-weight:800;letter-spacing:-.02em;margin:0}
.top-sub{font-size:.82rem;opacity:.6;margin-top:.2rem}

/* 섬네일 카드 */
.thumb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:1rem;margin:1rem 0}
.thumb-card{background:#fff;border-radius:14px;overflow:hidden;cursor:pointer;
  box-shadow:0 2px 12px rgba(0,0,0,.07);transition:all .2s;border:2px solid transparent}
.thumb-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(128,0,0,.15);
  border-color:#800000}
.thumb-img{width:100%;height:130px;object-fit:cover;display:block}
.thumb-noimg{width:100%;height:130px;background:#f0e8e8;display:flex;
  align-items:center;justify-content:center;font-size:2.5rem;color:#caa}
.thumb-info{padding:.7rem .8rem}
.thumb-name{font-size:.85rem;font-weight:700;color:#1a1a1a;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.thumb-summary{font-size:.72rem;color:#999;margin-top:.2rem}
.thumb-total{font-size:.82rem;font-weight:800;color:#800000;margin-top:.3rem}

/* 상세 뷰 - 카드뉴스 */
.detail-header{display:flex;align-items:center;gap:.8rem;margin-bottom:1rem}
.detail-agent{font-size:1.3rem;font-weight:800;color:#800000}
.detail-back{font-size:.85rem;color:#999;cursor:pointer;text-decoration:underline}

.card-news{display:flex;flex-direction:column;gap:.8rem}
.award-card{background:linear-gradient(135deg,#fff 0%,#fef8f8 100%);
  border-radius:16px;padding:1.2rem 1.4rem;
  border-left:5px solid #800000;
  box-shadow:0 2px 10px rgba(0,0,0,.05);
  transition:transform .15s}
.award-card:hover{transform:translateX(4px)}
.award-perf{font-size:.78rem;font-weight:600;color:#999;letter-spacing:.04em;text-transform:uppercase}
.award-main{display:flex;align-items:baseline;justify-content:space-between;margin-top:.3rem}
.award-rate{font-size:.92rem;font-weight:600;color:#555}
.award-amount{font-size:1.4rem;font-weight:800;color:#800000}

.total-card{background:linear-gradient(135deg,#800000 0%,#5a0000 100%);
  border-radius:16px;padding:1.2rem 1.4rem;color:#fff;
  box-shadow:0 4px 16px rgba(128,0,0,.25)}
.total-label{font-size:.82rem;font-weight:600;opacity:.7}
.total-amount{font-size:1.8rem;font-weight:800;margin-top:.2rem}

/* 섹션 라벨 */
.sec-label{font-size:.75rem;font-weight:700;color:#800000;
  letter-spacing:.08em;text-transform:uppercase;margin:1.2rem 0 .6rem}

.stButton>button{border-radius:9px!important;font-weight:700!important}
div[data-baseweb="select"]>div{border-radius:10px!important;font-weight:600!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 헤더
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="top-bar">
    <div class="top-title">🏆 GA 시상 계산기</div>
    <div class="top-sub">대리점 시상 정보를 등록하고, 섬네일을 클릭하면 카드뉴스로 확인할 수 있습니다</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 상세 보기 모드
# ══════════════════════════════════════════════════════════════
if st.session_state.view_agent and not st.session_state.edit_mode:
    agent = st.session_state.view_agent
    agent_data = st.session_state.all_data.get(agent, {})
    if isinstance(agent_data, list):
        agent_data = {}

    images = agent_data.get("images", [])
    rates = agent_data.get("rates", {})

    # 뒤로가기
    if st.button("← 목록으로 돌아가기", key="back_btn"):
        st.session_state.view_agent = None
        st.rerun()

    st.markdown(f'<div class="detail-agent">📋 {agent}</div>', unsafe_allow_html=True)
    st.markdown("")

    # 좌: 사진 / 우: 카드뉴스
    col_img, col_cards = st.columns([1, 1], gap="large")

    with col_img:
        if images:
            for img_info in images:
                try:
                    img_bytes = base64.standard_b64decode(img_info["data"])
                    st.image(img_bytes, caption=img_info.get("name", ""),
                             use_container_width=True)
                except Exception:
                    pass
        else:
            st.markdown("""<div style='background:#f8f0f0;border-radius:14px;
                padding:4rem 2rem;text-align:center;color:#caa'>
                <div style='font-size:3rem'>📷</div>
                <div style='margin-top:.5rem;font-size:.9rem'>등록된 시상 이미지가 없습니다</div>
            </div>""", unsafe_allow_html=True)

    with col_cards:
        st.markdown('<div class="card-news">', unsafe_allow_html=True)

        total = 0
        for perf in PERF_LEVELS:
            perf_won = perf * 10_000
            rate = float(rates.get(str(perf), 0))
            amount = perf_won * rate / 100
            total += amount

            st.markdown(f"""
            <div class="award-card">
                <div class="award-perf">실적 {perf}만원</div>
                <div class="award-main">
                    <div class="award-rate">시상률 {rate:.1f}%</div>
                    <div class="award-amount">{fmt_won(amount)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="total-card">
            <div class="total-label">총 시상금 합계</div>
            <div class="total-amount">{fmt_won(total)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    # 수정 버튼
    if st.button("✏️ 수정하기", key="edit_from_view", use_container_width=True):
        st.session_state.edit_mode = True
        st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════
# 입력/편집 모드
# ══════════════════════════════════════════════════════════════
if st.session_state.edit_mode:
    editing_agent = st.session_state.view_agent
    if st.button("← 취소하고 돌아가기", key="cancel_edit"):
        st.session_state.edit_mode = False
        st.rerun()

    st.markdown(f'<div class="sec-label">✏️ {editing_agent} 수정</div>', unsafe_allow_html=True)

    agent_data = st.session_state.all_data.get(editing_agent, {})
    if isinstance(agent_data, list):
        agent_data = {}

    saved_images = agent_data.get("images", [])
    saved_rates = agent_data.get("rates", {})

    # 이미지 업로드
    uploaded = st.file_uploader(
        "시상 이미지 업로드 (여러 장 가능)",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key=f"edit_img_{editing_agent}",
    )
    if uploaded:
        for uf in uploaded:
            file_id = f"{uf.name}_{uf.size}"
            already = any(img.get("file_id") == file_id for img in saved_images)
            if not already:
                img_bytes = uf.read()
                uf.seek(0)
                saved_images.append({
                    "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                    "name": uf.name,
                    "file_id": file_id,
                })

    if saved_images:
        st.markdown(f'<div class="sec-label">등록된 이미지 ({len(saved_images)}장)</div>',
                    unsafe_allow_html=True)
        img_cols = st.columns(min(len(saved_images), 4))
        for idx, img_info in enumerate(saved_images):
            with img_cols[idx % 4]:
                try:
                    img_bytes = base64.standard_b64decode(img_info["data"])
                    st.image(img_bytes, use_container_width=True)
                except Exception:
                    pass
        if st.button("🗑 이미지 전체 삭제", key="del_imgs_edit"):
            saved_images.clear()
            st.rerun()

    # 시상률 입력
    st.markdown('<div class="sec-label">실적별 시상률 입력</div>', unsafe_allow_html=True)
    rates = {}
    for perf in PERF_LEVELS:
        c1, c2, c3 = st.columns([2, 3, 4])
        with c1:
            st.markdown(f"<div style='padding:.45rem 0;font-weight:700;font-size:1rem'>"
                        f"{perf}만원</div>", unsafe_allow_html=True)
        with c2:
            rate = st.number_input(
                f"{perf}만 시상률", min_value=0.0, max_value=10000.0,
                value=float(saved_rates.get(str(perf), 0.0)),
                step=10.0, format="%.1f",
                key=f"edit_rate_{perf}", label_visibility="collapsed",
            )
        with c3:
            amount = perf * 10_000 * rate / 100
            color = "#800000" if amount > 0 else "#ccc"
            st.markdown(f"<div style='padding:.4rem 0;font-size:1.1rem;font-weight:800;"
                        f"color:{color};text-align:right'>= {fmt_won(amount)}</div>",
                        unsafe_allow_html=True)
        rates[str(perf)] = rate

    # 저장
    if st.button("💾 저장", use_container_width=True, type="primary", key="save_edit"):
        st.session_state.all_data[editing_agent] = {
            "images": copy.deepcopy(saved_images),
            "rates": copy.deepcopy(rates),
        }
        save_data(st.session_state.all_data)
        st.session_state.edit_mode = False
        st.success(f"✅ '{editing_agent}' 저장 완료!")
        st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════
# 메인 — 새 등록 + 섬네일 목록
# ══════════════════════════════════════════════════════════════

# ── 새 대리점 등록 ────────────────────────────────────────────
with st.expander("➕ 새 대리점 시상 등록", expanded=False):
    selected_new = st.selectbox(
        "대리점 선택", ["선택하세요"] + AGENT_LIST,
        key="new_agent_select", label_visibility="collapsed",
    )

    if selected_new != "선택하세요":
        agent_data = st.session_state.all_data.get(selected_new, {})
        if isinstance(agent_data, list):
            agent_data = {}

        saved_images = agent_data.get("images", [])
        saved_rates = agent_data.get("rates", {})

        # 이미지 업로드
        uploaded = st.file_uploader(
            "시상 이미지 업로드",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key=f"new_img_{selected_new}",
        )
        if uploaded:
            for uf in uploaded:
                file_id = f"{uf.name}_{uf.size}"
                already = any(img.get("file_id") == file_id for img in saved_images)
                if not already:
                    img_bytes = uf.read()
                    uf.seek(0)
                    saved_images.append({
                        "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                        "name": uf.name,
                        "file_id": file_id,
                    })

        # 시상률 입력
        st.markdown('<div class="sec-label">실적별 시상률</div>', unsafe_allow_html=True)
        rates = {}
        for perf in PERF_LEVELS:
            c1, c2, c3 = st.columns([2, 3, 4])
            with c1:
                st.markdown(f"<div style='padding:.45rem 0;font-weight:700'>{perf}만원</div>",
                            unsafe_allow_html=True)
            with c2:
                rate = st.number_input(
                    f"{perf}만", min_value=0.0, max_value=10000.0,
                    value=float(saved_rates.get(str(perf), 0.0)),
                    step=10.0, format="%.1f",
                    key=f"new_rate_{perf}", label_visibility="collapsed",
                )
            with c3:
                amount = perf * 10_000 * rate / 100
                color = "#800000" if amount > 0 else "#ccc"
                st.markdown(f"<div style='padding:.4rem 0;font-weight:800;color:{color};"
                            f"text-align:right'>= {fmt_won(amount)}</div>",
                            unsafe_allow_html=True)
            rates[str(perf)] = rate

        if st.button("💾 저장", use_container_width=True, type="primary", key="save_new"):
            st.session_state.all_data[selected_new] = {
                "images": copy.deepcopy(saved_images),
                "rates": copy.deepcopy(rates),
            }
            save_data(st.session_state.all_data)
            st.success(f"✅ '{selected_new}' 저장 완료!")
            st.rerun()

# ── 섬네일 목록 ──────────────────────────────────────────────
saved_agents = {k: v for k, v in st.session_state.all_data.items()
                if isinstance(v, dict) and v.get("rates")}

if not saved_agents:
    st.markdown("""<div style='text-align:center;padding:4rem;color:#bbb'>
        <div style='font-size:3.5rem'>📋</div>
        <div style='margin-top:.8rem;font-weight:600;font-size:1rem'>
            등록된 대리점이 없습니다<br>
            <span style='font-size:.88rem;font-weight:400'>위의 '새 대리점 시상 등록'을 클릭하여 추가하세요</span>
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

st.markdown(f'<div class="sec-label">등록된 대리점 ({len(saved_agents)}곳) — 클릭하면 상세보기</div>',
            unsafe_allow_html=True)

# 섬네일을 그리드로 표시
cols = st.columns(4)
for idx, (agent_name, agent_data) in enumerate(sorted(saved_agents.items())):
    rates = agent_data.get("rates", {})
    images = agent_data.get("images", [])

    # 총 시상금 계산
    total = sum(perf * 10_000 * float(rates.get(str(perf), 0)) / 100
                for perf in PERF_LEVELS)

    # 시상률 요약
    rate_summary = " / ".join(f"{rates.get(str(p), 0)}%" for p in PERF_LEVELS)

    col = cols[idx % 4]
    with col:
        with st.container(border=True):
            # 이미지 섬네일
            if images:
                try:
                    img_bytes = base64.standard_b64decode(images[0]["data"])
                    st.image(img_bytes, use_container_width=True)
                except Exception:
                    st.markdown("<div style='height:80px;background:#f8f0f0;border-radius:8px;"
                                "display:flex;align-items:center;justify-content:center;"
                                "font-size:2rem;color:#daa'>📷</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='height:80px;background:#f8f0f0;border-radius:8px;"
                            "display:flex;align-items:center;justify-content:center;"
                            "font-size:2rem;color:#daa'>📷</div>", unsafe_allow_html=True)

            # 이름 + 요약
            st.markdown(f"<div style='font-weight:700;font-size:.9rem;color:#1a1a1a;"
                        f"margin:.4rem 0 .1rem;white-space:nowrap;overflow:hidden;"
                        f"text-overflow:ellipsis'>{agent_name}</div>",
                        unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.72rem;color:#999'>{rate_summary}</div>",
                        unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.88rem;font-weight:800;color:#800000;"
                        f"margin-top:.3rem'>{fmt_won(total)}</div>",
                        unsafe_allow_html=True)

            # 클릭 버튼
            if st.button("상세보기", key=f"view_{agent_name}", use_container_width=True):
                st.session_state.view_agent = agent_name
                st.session_state.edit_mode = False
                st.rerun()
