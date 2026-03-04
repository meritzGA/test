"""
GA 시상 현황 — 대리점별 시책 파일 관리
- 관리자: 대리점 선택 → 월/주차 선택 → 시상 파일(이미지) 등록
- 조회:   대리점 검색 → 등록된 시상 파일 열람 (화면 맞춤)
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

.period-tag{display:inline-block;background:#800000;color:#fff;
  border-radius:20px;padding:.25rem .8rem;font-size:.78rem;font-weight:700;margin:.2rem .3rem .2rem 0}

/* 조회 결과 - 화면 맞춤 이미지 */
.viewer-agent-name{font-size:1.3rem;font-weight:800;color:#800000;
  margin:.5rem 0 .2rem;padding-bottom:.5rem;border-bottom:2px solid #800000}
.viewer-period-label{font-size:.95rem;font-weight:700;color:#333;margin:1rem 0 .5rem}
.viewer-img-wrap{width:100%;margin-bottom:.8rem;display:flex;justify-content:center}
.viewer-img-wrap img{max-height:88vh;max-width:100%;width:auto;height:auto;
  object-fit:contain;display:block;border-radius:10px;
  box-shadow:0 2px 12px rgba(0,0,0,.08)}

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

    all_data = st.session_state.all_data

    # 등록된 대리점만 필터
    registered = [k for k, v in all_data.items() if isinstance(v, dict) and v.get("periods")]

    # 검색 (selectbox + 텍스트 검색 혼합)
    search = st.text_input(
        "대리점명 검색",
        placeholder="대리점명을 입력하세요",
        key="search_input",
        label_visibility="collapsed",
    )

    # 검색어가 있으면 필터
    if search.strip():
        matched = [name for name in registered if search.strip() in name]
    else:
        matched = []

    # 검색어 없으면 안내
    if not search.strip():
        st.markdown("""<div style='text-align:center;padding:4rem;color:#bbb'>
            <div style='font-size:3rem'>🔍</div>
            <div style='margin-top:.6rem;font-weight:500;font-size:1rem'>
                대리점명을 입력하여 검색하세요</div>
        </div>""", unsafe_allow_html=True)
        return

    # 검색 결과 없음
    if not matched:
        st.markdown(f"""<div style='text-align:center;padding:3rem;color:#bbb'>
            <div style='font-size:2.5rem'>📋</div>
            <div style='margin-top:.5rem;font-size:.95rem'>
                '<b>{search}</b>'에 대한 검색 결과가 없습니다</div>
        </div>""", unsafe_allow_html=True)
        return

    # 여러 개 매칭되면 선택
    if len(matched) == 1:
        selected = matched[0]
    else:
        selected = st.selectbox(
            f"{len(matched)}개 대리점 검색됨 — 선택하세요",
            matched,
            key="viewer_select",
            label_visibility="collapsed",
        )

    # ── 선택된 대리점 시상 파일 표시 ──────────────────────────
    agent_data = all_data.get(selected, {})
    periods = agent_data.get("periods", {})
    period_keys = sorted(periods.keys(), reverse=True)

    st.markdown(f'<div class="viewer-agent-name">📋 {selected}</div>', unsafe_allow_html=True)

    if not period_keys:
        st.info("등록된 시상 파일이 없습니다.")
        return

    # 기간 선택
    selected_period = st.selectbox(
        "기간 선택",
        period_keys,
        key="viewer_period",
    )

    pdata = periods.get(selected_period, {})
    p_images = pdata.get("images", [])

    st.markdown(f'<span class="period-tag" style="font-size:.95rem">{selected_period}</span>'
                f'<span style="font-size:.82rem;color:#888;margin-left:.5rem">'
                f'{len(p_images)}장</span>',
                unsafe_allow_html=True)

    if not p_images:
        st.info(f"{selected_period}에 등록된 시상 파일이 없습니다.")
        return

    # 이미지를 화면 폭에 맞춰 표시 (HTML img + width:100%)
    for img_info in p_images:
        try:
            b64_data = img_info["data"]
            media_type = img_info.get("media_type", "image/png")
            name = img_info.get("name", "")

            # 확장자로 media_type 추정
            if not media_type or media_type == "image/png":
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else "png"
                mt_map = {"png": "image/png", "jpg": "image/jpeg",
                          "jpeg": "image/jpeg", "webp": "image/webp"}
                media_type = mt_map.get(ext, "image/png")

            st.markdown(f"""
            <div class="viewer-img-wrap">
                <img src="data:{media_type};base64,{b64_data}" alt="{name}">
            </div>
            """, unsafe_allow_html=True)

            if name:
                st.caption(name)
        except Exception:
            pass


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

    # ── 백업 / 복원 (항상 표시) ────────────────────────────────
    with st.expander("💾 데이터 백업 / 복원", expanded=False):
        bc1, bc2 = st.columns(2, gap="large")
        with bc1:
            st.markdown("**📥 백업 다운로드**")
            st.caption("모든 대리점 데이터 다운로드 (이미지 포함)")
            backup_json = json.dumps(st.session_state.all_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 전체 백업 다운로드",
                data=backup_json.encode("utf-8"),
                file_name="ga_awards_backup.json",
                mime="application/json",
                use_container_width=True,
                key="backup_download",
            )
            agent_count = len([k for k, v in st.session_state.all_data.items()
                               if isinstance(v, dict) and v.get("periods")])
            st.caption(f"등록 대리점: {agent_count}곳")
        with bc2:
            st.markdown("**📤 백업 복원**")
            st.caption("백업 파일 업로드 시 기존 데이터를 덮어씁니다")
            restore_file = st.file_uploader(
                "백업 JSON 파일 업로드",
                type=["json"],
                key="restore_upload",
                label_visibility="collapsed",
            )
            if restore_file:
                try:
                    restore_data = json.loads(restore_file.read().decode("utf-8"))
                    restore_count = len([k for k, v in restore_data.items()
                                         if isinstance(v, dict) and v.get("periods")])
                    st.info(f"📋 백업 파일: {restore_count}개 대리점 데이터 감지")
                    if st.button("⚠️ 복원 실행 (기존 데이터 덮어쓰기)",
                                 use_container_width=True, type="primary", key="restore_btn"):
                        st.session_state.all_data = restore_data
                        save_data(restore_data)
                        st.success(f"✅ 복원 완료! ({restore_count}개 대리점)")
                        st.rerun()
                except json.JSONDecodeError:
                    st.error("올바른 JSON 파일이 아닙니다.")
                except Exception as e:
                    st.error(f"복원 오류: {e}")

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
                ext = uf.name.rsplit(".", 1)[-1].lower() if "." in uf.name else "png"
                mt_map = {"png": "image/png", "jpg": "image/jpeg",
                          "jpeg": "image/jpeg", "webp": "image/webp"}
                existing_images.append({
                    "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                    "media_type": mt_map.get(ext, "image/png"),
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

    # ── 전체 등록 현황 ─────────────────────────────────────────
    all_periods = agent_data.get("periods", {})
    if all_periods:
        st.markdown("---")
        st.markdown(f'<div class="sec-label">📋 {agent} 전체 등록 현황</div>',
                    unsafe_allow_html=True)
        for pk in sorted(all_periods.keys(), reverse=True):
            p_imgs = all_periods[pk].get("images", [])
            st.markdown(f'<span class="period-tag">{pk}</span>'
                        f'<span style="font-size:.82rem;color:#888;margin-left:.4rem">'
                        f'{len(p_imgs)}장</span>', unsafe_allow_html=True)

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
