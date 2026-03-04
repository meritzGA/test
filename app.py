"""
GA 시상 계산기 — 심플 버전
대리점 선택 → 시상 이미지 업로드 → 실적별 시상률 입력 → 시상금 자동 계산
"""

import streamlit as st
import json, os, copy, base64
from agents import AGENT_LIST

# ── 설정 ─────────────────────────────────────────────────────
DATA_FILE = "awards_data.json"
PERF_LEVELS = [10, 20, 30, 50]  # 만원 단위

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

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'Pretendard',-apple-system,sans-serif!important}
.stApp{background:#f7f7f9!important}

.top-bar{
  background:linear-gradient(135deg,#800000 0%,#5a0000 55%,#380000 100%);
  border-radius:16px;padding:1.6rem 2rem;color:#fff;margin-bottom:1.4rem;
  box-shadow:0 6px 24px rgba(128,0,0,.25);position:relative;overflow:hidden}
.top-bar::before{content:'';position:absolute;top:-50%;right:-3%;
  width:280px;height:280px;background:rgba(255,255,255,.04);border-radius:50%}
.top-title{font-size:1.5rem;font-weight:800;letter-spacing:-.02em;margin:0}
.top-sub{font-size:.85rem;opacity:.65;margin-top:.25rem}

.agent-name{font-size:1.3rem;font-weight:800;color:#800000;margin:.8rem 0 .4rem;
  padding-bottom:.4rem;border-bottom:2px solid #800000}

.calc-table{width:100%;border-collapse:separate;border-spacing:0;
  background:#fff;border-radius:14px;overflow:hidden;
  box-shadow:0 2px 12px rgba(0,0,0,.06);margin:.6rem 0 1rem}
.calc-table th{background:#800000;color:#fff;padding:.7rem 1rem;
  font-size:.82rem;font-weight:700;text-align:center}
.calc-table th:first-child{text-align:left;width:20%}
.calc-table th:nth-child(2){width:30%}
.calc-table th:nth-child(3){width:10%;font-size:1rem}
.calc-table th:last-child{text-align:right;width:40%}
.calc-table td{padding:.6rem 1rem;font-size:.95rem;
  border-bottom:1px solid #f0f0f0;text-align:center;vertical-align:middle}
.calc-table td:first-child{text-align:left;font-weight:700;color:#333;font-size:1rem}
.calc-table td:last-child{text-align:right;font-weight:800;color:#800000;font-size:1.05rem}
.calc-table tr:last-child td{border-bottom:none}
.calc-table tr:hover td{background:#fef8f8}

.total-row td{background:#fff5f5!important;border-top:2px solid #800000!important;
  font-weight:800!important;color:#800000!important;font-size:1.1rem!important}
.total-row td:first-child{font-size:1rem!important}

.img-section{background:#fff;border-radius:14px;padding:1rem;
  box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:1rem}
.img-section-title{font-size:.78rem;font-weight:700;color:#800000;
  letter-spacing:.06em;text-transform:uppercase;margin-bottom:.6rem}

.save-success{background:#f0fff0;border:1px solid #4caf50;border-radius:10px;
  padding:.6rem 1rem;color:#2e7d32;font-weight:600;text-align:center;margin:.6rem 0}

.stButton>button{border-radius:9px!important;font-weight:700!important}
div[data-baseweb="select"]>div{border-radius:10px!important;font-weight:600!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════════════
def fmt_won(v: float) -> str:
    return f"{int(round(v)):,}원"

# ══════════════════════════════════════════════════════════════
# 헤더
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="top-bar">
    <div class="top-title">🏆 GA 시상 계산기</div>
    <div class="top-sub">대리점 선택 → 시상 이미지 업로드 → 실적별 시상률 입력 → 시상금 자동 계산</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 대리점 선택
# ══════════════════════════════════════════════════════════════
selected = st.selectbox(
    "대리점을 선택하세요",
    ["대리점을 선택하세요"] + AGENT_LIST,
    key="agent_select",
    label_visibility="collapsed",
)

if selected == "대리점을 선택하세요":
    st.markdown("""<div style='text-align:center;padding:4rem;color:#bbb'>
        <div style='font-size:3.5rem'>🏢</div>
        <div style='margin-top:.8rem;font-weight:600;font-size:1.1rem'>대리점을 선택해 주세요</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── 선택된 대리점 데이터 로드 ──────────────────────────────────
agent_data = st.session_state.all_data.get(selected, {})
if isinstance(agent_data, list):
    # 구버전 호환: list → dict 변환
    agent_data = {}

st.markdown(f'<div class="agent-name">📋 {selected}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 이미지 업로드/표시
# ══════════════════════════════════════════════════════════════
saved_images = agent_data.get("images", [])

# 이미지 업로드
uploaded = st.file_uploader(
    "시상 계획서 이미지 업로드 (여러 장 가능)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    key=f"img_upload_{selected}",
    label_visibility="collapsed",
)

# 새 이미지가 업로드되면 세션에 추가
if uploaded:
    for uf in uploaded:
        file_id = f"{uf.name}_{uf.size}"
        already = any(img.get("file_id") == file_id for img in saved_images)
        if not already:
            img_bytes = uf.read()
            uf.seek(0)  # 리셋
            saved_images.append({
                "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                "name": uf.name,
                "file_id": file_id,
            })

# 저장된 이미지 표시
if saved_images:
    for idx, img_info in enumerate(saved_images):
        try:
            img_bytes = base64.standard_b64decode(img_info["data"])
            st.image(img_bytes, caption=img_info.get("name", "시상 이미지"),
                     use_container_width=True)
        except Exception:
            pass
    # 이미지 전체 삭제 버튼
    if st.button("🗑 이미지 전체 삭제", key="del_all_img"):
        saved_images.clear()
        st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# 실적별 시상률 입력 + 시상금 계산
# ══════════════════════════════════════════════════════════════
saved_rates = agent_data.get("rates", {})

st.markdown("""
<table class="calc-table">
    <thead>
        <tr>
            <th>실적</th>
            <th>시상률 (%)</th>
            <th>=</th>
            <th>시상금</th>
        </tr>
    </thead>
</table>
""", unsafe_allow_html=True)

rates = {}
total_awards = {}

for perf in PERF_LEVELS:
    perf_won = perf * 10_000
    perf_label = f"{perf}만원"
    default_rate = float(saved_rates.get(str(perf), 0.0))

    c1, c2, c3, c4 = st.columns([2, 3, 0.5, 4])

    with c1:
        st.markdown(f"<div style='font-size:1.05rem;font-weight:700;color:#333;"
                    f"padding:.45rem 0'>{perf_label}</div>", unsafe_allow_html=True)

    with c2:
        rate = st.number_input(
            f"{perf}만 시상률",
            min_value=0.0,
            max_value=10000.0,
            value=default_rate,
            step=10.0,
            format="%.1f",
            key=f"rate_{perf}",
            label_visibility="collapsed",
        )

    with c3:
        st.markdown("<div style='text-align:center;font-size:1.3rem;font-weight:700;"
                    "color:#999;padding:.3rem 0'>=</div>", unsafe_allow_html=True)

    with c4:
        award_amount = perf_won * rate / 100
        color = "#800000" if award_amount > 0 else "#ccc"
        st.markdown(f"<div style='font-size:1.15rem;font-weight:800;color:{color};"
                    f"text-align:right;padding:.4rem 0'>{fmt_won(award_amount)}</div>",
                    unsafe_allow_html=True)

    rates[str(perf)] = rate
    total_awards[perf] = award_amount

# ── 합계 ─────────────────────────────────────────────────────
total = sum(total_awards.values())
st.markdown("---")
tc1, tc2 = st.columns([5.5, 4])
with tc1:
    st.markdown("<div style='font-size:1rem;font-weight:700;color:#800000;"
                "padding:.3rem 0'>✅ 총 시상금 합계</div>", unsafe_allow_html=True)
with tc2:
    st.markdown(f"<div style='font-size:1.4rem;font-weight:800;color:#800000;"
                f"text-align:right;padding:.2rem 0'>{fmt_won(total)}</div>",
                unsafe_allow_html=True)

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 저장
# ══════════════════════════════════════════════════════════════
if st.button("💾  저장", use_container_width=True, type="primary", key="save_btn"):
    st.session_state.all_data[selected] = {
        "images": copy.deepcopy(saved_images),
        "rates": copy.deepcopy(rates),
    }
    save_data(st.session_state.all_data)
    st.success(f"✅ '{selected}' 저장 완료!")
