"""
GA 시상 현황 — 대리점별 시책 파일 관리
- 관리자: 대리점 선택 → 월/주차 선택 → 시상 파일(이미지) 등록
- 조회:   대리점 검색 → 등록된 시상 파일 열람
"""

import streamlit as st
import json, os, copy, base64
from agents import AGENT_LIST

# ── 설정 ─────────────────────────────────────────────────────
ADMIN_PASSWORD = "meritz0505"
DATA_FILE = "awards_data.json"

MONTHS = [f"{m}월" for m in range(1, 13)]
WEEKS = ["1주차", "2주차", "3주차", "4주차", "5주차"]

st.set_page_config(
    page_title="GA 시상 현황",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
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
if "page" not in st.session_state:
    st.session_state.page = "viewer"
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'Pretendard',-apple-system,sans-serif!important}
.stApp{background:#f5f5f7!important}

/* 사이드바 */
section[data-testid="stSidebar"]{background:#1a0000!important}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div{color:#f0e0e0!important}
section[data-testid="stSidebar"] .stButton>button{
  background:rgba(255,255,255,.08)!important;color:#f0e0e0!important;
  border:1px solid rgba(255,255,255,.18)!important;border-radius:10px!important;font-weight:600!important}
section[data-testid="stSidebar"] .stButton>button:hover{background:rgba(128,0,0,.55)!important}
section[data-testid="stSidebar"] [data-testid="stButton-primary"]>button{
  background:#800000!important;border-color:#a00000!important;color:#fff!important}

/* 헤더 */
.top-bar{
  background:linear-gradient(135deg,#800000 0%,#5a0000 55%,#380000 100%);
  border-radius:16px;padding:1.4rem 2rem;color:#fff;margin-bottom:1.2rem;
  box-shadow:0 6px 24px rgba(128,0,0,.22);position:relative;overflow:hidden}
.top-bar::before{content:'';position:absolute;top:-50%;right:-3%;
  width:260px;height:260px;background:rgba(255,255,255,.04);border-radius:50%}
.top-title{font-size:1.4rem;font-weight:800;letter-spacing:-.02em;margin:0}
.top-sub{font-size:.82rem;opacity:.6;margin-top:.2rem}

.sec-label{font-size:.75rem;font-weight:700;color:#800000;
  letter-spacing:.08em;text-transform:uppercase;margin:1.2rem 0 .6rem}

/* 기간 태그 */
.period-tag{display:inline-block;background:#800000;color:#fff;
  border-radius:20px;padding:.25rem .8rem;font-size:.78rem;font-weight:700;margin:.2rem .3rem .2rem 0}
.period-tag-outline{display:inline-block;background:#fff;color:#800000;border:1.5px solid #800000;
  border-radius:20px;padding:.25rem .8rem;font-size:.78rem;font-weight:700;margin:.2rem .3rem .2rem 0;
  cursor:pointer;transition:all .15s}
.period-tag-outline:hover{background:#800000;color:#fff}

/* 파일 카드 */
.file-card{background:#fff;border-radius:14px;overflow:hidden;
  box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:1rem;border:1.5px solid #eee}
.file-card-header{background:#fafafa;padding:.7rem 1rem;border-bottom:1px solid #f0f0f0;
  display:flex;align-items:center;justify-content:space-between}
.file-card-period{font-weight:700;color:#800000;font-size:.9rem}
.file-card-count{font-size:.75rem;color:#999}

/* 검색 결과 카드 */
.result-card{background:#fff;border-radius:14px;padding:1.2rem;
  box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:.8rem;
  border-left:4px solid #800000;cursor:pointer;transition:all .15s}
.result-card:hover{box-shadow:0 4px 20px rgba(128,0,0,.12);transform:translateX(3px)}
.result-name{font-weight:700;font-size:1rem;color:#1a1a1a}
.result-periods{font-size:.78rem;color:#888;margin-top:.25rem}

.stButton>button{border-radius:9px!important;font-weight:700!important}
div[data-baseweb="select"]>div{border-radius:10px!important;font-weight:600!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1.2rem 0 .6rem'>
        <span style='font-size:2.2rem'>🏆</span><br>
        <b style='font-size:1rem;color:#ffcccc;letter-spacing:.03em'>GA 시상 현황</b>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🔍  시상 조회", use_container_width=True,
                 type="primary" if st.session_state.page == "viewer" else "secondary"):
        st.session_state.page = "viewer"
        st.rerun()
    if st.button("⚙️  관리자", use_container_width=True,
                 type="primary" if st.session_state.page == "admin" else "secondary"):
        st.session_state.page = "admin"
        st.rerun()
    st.markdown("---")
    st.caption("Meritz Fire Insurance")


# ══════════════════════════════════════════════════════════════
# 조회 화면
# ══════════════════════════════════════════════════════════════
def page_viewer():
    st.markdown("""
    <div class="top-bar">
        <div class="top-title">🔍 대리점 시상 조회</div>
        <div class="top-sub">대리점명을 검색하면 등록된 시상 파일을 확인할 수 있습니다</div>
    </div>
    """, unsafe_allow_html=True)

    # 검색
    search = st.text_input(
        "대리점명 검색",
        placeholder="대리점명을 입력하세요 (예: 가나다보험)",
        key="search_input",
        label_visibility="collapsed",
    )

    all_data = st.session_state.all_data

    # 검색 필터
    if search.strip():
        matched = {k: v for k, v in all_data.items()
                   if isinstance(v, dict) and search.strip() in k}
    else:
        matched = {k: v for k, v in all_data.items() if isinstance(v, dict)}

    if not matched:
        if search.strip():
            st.markdown(f"""<div style='text-align:center;padding:3rem;color:#bbb'>
                <div style='font-size:2.5rem'>🔍</div>
                <div style='margin-top:.5rem;font-size:.95rem'>
                    '<b>{search}</b>' 에 대한 검색 결과가 없습니다</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style='text-align:center;padding:3rem;color:#bbb'>
                <div style='font-size:2.5rem'>📋</div>
                <div style='margin-top:.5rem;font-size:.95rem'>등록된 대리점이 없습니다</div>
            </div>""", unsafe_allow_html=True)
        return

    st.markdown(f'<div class="sec-label">검색 결과 ({len(matched)}곳)</div>',
                unsafe_allow_html=True)

    for agent_name, agent_data in sorted(matched.items()):
        periods = agent_data.get("periods", {})
        period_keys = sorted(periods.keys(), reverse=True)
        period_summary = ", ".join(period_keys[:5])
        if len(period_keys) > 5:
            period_summary += f" 외 {len(period_keys)-5}건"

        img_count = sum(len(periods[pk].get("images", [])) for pk in period_keys)

        with st.expander(f"📋 {agent_name}　—　{len(period_keys)}건 등록 / 이미지 {img_count}장", expanded=False):
            if not period_keys:
                st.info("등록된 시상 파일이 없습니다.")
                continue

            # 기간 필터 탭
            selected_period = st.selectbox(
                "기간 선택",
                period_keys,
                key=f"period_sel_{agent_name}",
            )

            pdata = periods.get(selected_period, {})
            p_images = pdata.get("images", [])

            if p_images:
                st.markdown(f'<span class="period-tag">{selected_period}</span>'
                            f'<span style="font-size:.82rem;color:#888;margin-left:.5rem">'
                            f'{len(p_images)}장</span>',
                            unsafe_allow_html=True)
                for img_info in p_images:
                    try:
                        img_bytes = base64.standard_b64decode(img_info["data"])
                        st.image(img_bytes, caption=img_info.get("name", ""),
                                 use_container_width=True)
                    except Exception:
                        pass
            else:
                st.info(f"{selected_period}에 등록된 이미지가 없습니다.")


# ══════════════════════════════════════════════════════════════
# 관리자 화면
# ══════════════════════════════════════════════════════════════
def page_admin():
    st.markdown("""
    <div class="top-bar">
        <div class="top-title">⚙️ 관리자 — 시상 파일 등록</div>
        <div class="top-sub">대리점 선택 → 월/주차 선택 → 시상 이미지 업로드 → 저장</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 로그인 ─────────────────────────────────────────────────
    if not st.session_state.admin_auth:
        _, mid, _ = st.columns([1, 1.5, 1])
        with mid:
            st.markdown("""
            <div style='text-align:center;padding:2rem 0 1rem'>
                <div style='font-size:2.5rem'>🔐</div>
                <h3 style='color:#800000;margin:.5rem 0 .2rem;font-size:1.2rem'>관리자 로그인</h3>
            </div>""", unsafe_allow_html=True)
            pw = st.text_input("비밀번호", type="password", label_visibility="collapsed",
                               placeholder="비밀번호 입력", key="admin_pw_input")
            if st.button("로그인", use_container_width=True, type="primary", key="login_btn"):
                if pw == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        return

    # ── 로그아웃 ───────────────────────────────────────────────
    c_top1, c_top2 = st.columns([6, 1])
    with c_top2:
        if st.button("로그아웃", key="logout"):
            st.session_state.admin_auth = False
            st.rerun()

    # ── 대리점 선택 ────────────────────────────────────────────
    st.markdown('<div class="sec-label">1. 대리점 선택</div>', unsafe_allow_html=True)
    agent = st.selectbox("대리점", ["선택하세요"] + AGENT_LIST,
                         key="admin_agent", label_visibility="collapsed")

    if agent == "선택하세요":
        st.info("👆 대리점을 선택하세요.")
        return

    # ── 월/주차 선택 ───────────────────────────────────────────
    st.markdown('<div class="sec-label">2. 기간 선택</div>', unsafe_allow_html=True)
    c_month, c_week = st.columns(2)
    with c_month:
        month = st.selectbox("월", MONTHS, index=2, key="admin_month", label_visibility="collapsed")
    with c_week:
        week = st.selectbox("주차", WEEKS, key="admin_week", label_visibility="collapsed")

    period_key = f"{month} {week}"
    st.markdown(f'<span class="period-tag" style="font-size:.9rem">{period_key}</span>',
                unsafe_allow_html=True)

    # ── 기존 데이터 로드 ───────────────────────────────────────
    agent_data = st.session_state.all_data.get(agent, {})
    if isinstance(agent_data, list):
        agent_data = {}
    if "periods" not in agent_data:
        agent_data["periods"] = {}

    period_data = agent_data["periods"].get(period_key, {})
    existing_images = period_data.get("images", [])

    # ── 이미지 업로드 ──────────────────────────────────────────
    st.markdown('<div class="sec-label">3. 시상 파일 업로드</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "시상 이미지 업로드 (여러 장 가능)",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key=f"admin_img_{agent}_{period_key}",
        label_visibility="collapsed",
    )

    if uploaded:
        for uf in uploaded:
            file_id = f"{uf.name}_{uf.size}"
            already = any(img.get("file_id") == file_id for img in existing_images)
            if not already:
                img_bytes = uf.read()
                uf.seek(0)
                existing_images.append({
                    "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                    "name": uf.name,
                    "file_id": file_id,
                })

    # ── 등록된 이미지 미리보기 ─────────────────────────────────
    if existing_images:
        st.markdown(f'<div class="sec-label">등록된 이미지 ({len(existing_images)}장)</div>',
                    unsafe_allow_html=True)
        for idx, img_info in enumerate(existing_images):
            col_img, col_del = st.columns([6, 1])
            with col_img:
                try:
                    img_bytes = base64.standard_b64decode(img_info["data"])
                    st.image(img_bytes, caption=img_info.get("name", ""),
                             use_container_width=True)
                except Exception:
                    st.warning(f"이미지 로드 실패: {img_info.get('name','')}")
            with col_del:
                st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
                if st.button("🗑", key=f"del_img_{idx}_{period_key}"):
                    existing_images.pop(idx)
                    st.rerun()
    else:
        st.markdown("<div style='text-align:center;padding:1.5rem;color:#bbb;font-size:.9rem'>"
                    "아직 등록된 이미지가 없습니다</div>", unsafe_allow_html=True)

    # ── 저장 ───────────────────────────────────────────────────
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    if st.button("💾  저장", use_container_width=True, type="primary", key="save_admin"):
        agent_data["periods"][period_key] = {
            "images": copy.deepcopy(existing_images),
        }
        st.session_state.all_data[agent] = agent_data
        save_data(st.session_state.all_data)
        st.success(f"✅ '{agent}' — {period_key} 저장 완료! ({len(existing_images)}장)")

    # ── 이 대리점의 전체 등록 현황 ─────────────────────────────
    all_periods = agent_data.get("periods", {})
    if all_periods:
        st.markdown("---")
        st.markdown(f'<div class="sec-label">📋 {agent} 전체 등록 현황</div>',
                    unsafe_allow_html=True)
        for pk in sorted(all_periods.keys(), reverse=True):
            p_imgs = all_periods[pk].get("images", [])
            img_count = len(p_imgs)
            st.markdown(f'<span class="period-tag">{pk}</span>'
                        f'<span style="font-size:.82rem;color:#888;margin-left:.4rem">'
                        f'{img_count}장</span>', unsafe_allow_html=True)

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        if st.button("🗑 이 대리점 전체 데이터 삭제", key="del_all_agent"):
            if agent in st.session_state.all_data:
                del st.session_state.all_data[agent]
                save_data(st.session_state.all_data)
                st.success(f"'{agent}' 전체 데이터가 삭제되었습니다.")
                st.rerun()


# ══════════════════════════════════════════════════════════════
# 라우터
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "viewer":
    page_viewer()
else:
    page_admin()
