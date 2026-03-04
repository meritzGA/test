"""
GA 시상 계산기 v3
- 관리자: 시상 이미지 업로드 → Claude AI 자동 분석 → 항목 편집/추가/삭제 → 저장
- 조회:   대리점 선택 → 실적별 시상금 테이블
"""

import streamlit as st
import json, os, copy, base64, re
import anthropic
from agents import AGENT_LIST

# ── 설정 ─────────────────────────────────────────────────────
ADMIN_PASSWORD = "meritz0505"
DATA_FILE      = "awards_data.json"
DEFAULT_PERFS  = [100_000, 200_000, 300_000, 500_000]
st.set_page_config(
    page_title="GA 시상 계산기",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API 키: session_state(직접입력) → st.secrets → 환경변수 ──
def _get_api_key() -> str:
    # 1순위: 관리자가 화면에서 직접 입력한 키
    if st.session_state.get("manual_api_key", "").strip():
        return st.session_state.manual_api_key.strip()
    # 2순위: st.secrets
    try:
        v = st.secrets["ANTHROPIC_API_KEY"]
        if v and v.strip():
            return v.strip()
    except Exception:
        pass
    # 3순위: 환경변수
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()

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

# ══════════════════════════════════════════════════════════════
# 계산 유틸
# ══════════════════════════════════════════════════════════════
def calc_award(award: dict, perf: int) -> float:
    if award["type"] == "정률":
        return perf * award["rate"] / 100
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
# Claude AI 이미지 분석
# ══════════════════════════════════════════════════════════════
ANALYSIS_PROMPT = """
당신은 보험 GA(General Agent) 시상 계획서 이미지를 분석하는 전문가입니다.

이미지에서 시상 항목들을 추출하여 아래 JSON 형식으로만 응답하세요.
다른 텍스트, 설명, 마크다운 코드블록 없이 순수 JSON만 출력하세요.

형식:
{
  "awards": [
    {
      "name": "시상 항목명",
      "desc": "시상 내용 설명 (간략히)",
      "type": "정률" 또는 "구간별",
      "rate": 숫자 (정률인 경우 %, 구간별이면 null),
      "tiers": [
        {"from": 시작원(정수), "to": 끝원(정수, 무제한이면 -1), "rate": 퍼센트(숫자)}
      ] (구간별인 경우, 정률이면 null)
    }
  ]
}

규칙:
- 금액은 모두 '원' 단위 정수로 변환 (예: 10만 → 100000)
- 시책률/지급률이 % 단위이면 그대로, 비율(0.x)이면 ×100 변환
- 구간이 "10만 이상"처럼 상한 없으면 to=-1
- 이미지에서 읽기 어렵거나 불명확한 값은 최선을 다해 추정
- 시상 항목이 없으면 {"awards": []} 반환
"""

def analyze_image_with_claude(image_bytes: bytes, media_type: str) -> list[dict]:
    """Claude Vision으로 시상 이미지 분석 → award 리스트 반환"""
    key = _get_api_key()   # 항상 최신 키 재조회 (secrets 반영)
    client = anthropic.Anthropic(api_key=key, timeout=50.0)
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {"type": "text", "text": ANALYSIS_PROMPT},
            ],
        }],
    )

    raw = response.content[0].text.strip()
    # JSON 블록만 추출
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    parsed = json.loads(raw)
    return parsed.get("awards", [])

# ══════════════════════════════════════════════════════════════
# 세션 상태 초기화
# ══════════════════════════════════════════════════════════════
_defaults = {
    "page": "viewer",
    "admin_auth": False,
    "all_data": None,
    "edit_agent": None,
    "edit_awards": [],     # 현재 편집 중인 시상 목록
    "editing_idx": None,   # 수정 폼 열린 인덱스
    "add_mode": False,
    "analyzing": False,
    "last_uploaded": None,
    "manual_api_key": "", # 업로드된 파일명 (중복 분석 방지)
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.all_data is None:
    st.session_state.all_data = load_data()

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'Pretendard',-apple-system,sans-serif!important}

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

/* 배경 */
.stApp{background:#f4f4f6!important}

/* 조회 히어로 */
.hero-banner{
  background:linear-gradient(135deg,#800000 0%,#5a0000 55%,#380000 100%);
  border-radius:18px;padding:2rem 2.5rem;color:#fff;margin-bottom:1.5rem;
  box-shadow:0 8px 32px rgba(128,0,0,.28);position:relative;overflow:hidden}
.hero-banner::before{content:'';position:absolute;top:-60%;right:-5%;
  width:320px;height:320px;background:rgba(255,255,255,.05);border-radius:50%}
.hero-title{font-size:1.6rem;font-weight:800;letter-spacing:-.02em;margin:0 0 .3rem}
.hero-sub{font-size:.88rem;opacity:.72}

.section-label{font-size:.75rem;font-weight:700;color:#800000;
  letter-spacing:.08em;text-transform:uppercase;margin:1.4rem 0 .65rem}

/* 합계 테이블 */
.sum-table{width:100%;border-collapse:collapse;background:#fff;
  border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.07);margin-top:.8rem}
.sum-table th{background:#800000;color:#fff;padding:.7rem 1rem;
  font-size:.82rem;font-weight:700;text-align:right}
.sum-table th:first-child{text-align:left}
.sum-table td{padding:.65rem 1rem;font-size:.88rem;border-bottom:1px solid #f5f5f5;text-align:right}
.sum-table td:first-child{text-align:left;font-weight:600;color:#222}
.sum-table tr:last-child td{background:#fff6f6;font-weight:800;color:#800000;border-bottom:none}
.sum-table tr:not(:last-child):hover td{background:#fdf4f4}

/* 배지 */
.type-badge{display:inline-block;font-size:.68rem;font-weight:700;
  padding:1px 8px;border-radius:20px;margin-left:.4rem;vertical-align:middle}
.badge-flat{background:#fff0f0;color:#800000}
.badge-tier{background:#eff3ff;color:#2040b0}

/* 관리자 헤더 */
.admin-header-bar{background:#1a0000;color:#fff;padding:1.1rem 1.6rem;
  border-radius:14px;margin-bottom:1.2rem;display:flex;align-items:center;gap:1rem}
.admin-header-title{font-size:1.2rem;font-weight:800}
.admin-header-sub{font-size:.8rem;opacity:.6;margin-top:2px}

/* 관리자 섹션 소제목 */
.admin-sec-title{font-size:.75rem;font-weight:700;color:#800000;
  letter-spacing:.08em;text-transform:uppercase;margin:0 0 .7rem;padding:0}

/* 시상 카드 (관리자 목록) */
.aw-card{background:#fafafa;border:1.5px solid #ebebeb;border-radius:10px;
  padding:.85rem 1rem;margin-bottom:.5rem;transition:border-color .15s,background .15s}
.aw-card.editing{background:#fff8f8;border-color:#800000}
.aw-card-name{font-weight:700;color:#1a1a1a;font-size:.93rem}
.aw-card-meta{font-size:.76rem;color:#999;margin-top:2px}

/* 이미지 업로드 존 */
.upload-zone{background:#fff;border:2px dashed #d0d0d0;border-radius:14px;
  padding:1.5rem;text-align:center;transition:border-color .2s}
.upload-zone:hover{border-color:#800000}

/* AI 분석 뱃지 */
.ai-badge{background:linear-gradient(90deg,#800000,#cc2200);
  color:#fff;border-radius:8px;padding:.3rem .8rem;font-size:.78rem;font-weight:700;
  display:inline-block;margin-bottom:.6rem}

/* 버튼 */
.stButton>button{border-radius:9px!important;font-weight:700!important;transition:all .15s!important}
div[data-baseweb="select"]>div{border-radius:10px!important;font-weight:600!important}
.stTextInput input,.stNumberInput input{border-radius:8px!important}
</style>
"""

# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1.2rem 0 .6rem'>
        <span style='font-size:2.2rem'>🏆</span><br>
        <b style='font-size:1rem;color:#ffcccc;letter-spacing:.03em'>GA 시상 계산기</b>
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
# 조회 화면
# ══════════════════════════════════════════════════════════════
def page_viewer():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🏆 GA 시상 계산기</div>
        <div class="hero-sub">대리점을 선택하면 실적별 시상금을 한눈에 확인할 수 있습니다</div>
    </div>
    """, unsafe_allow_html=True)

    col_sel, col_perf = st.columns([2, 3], gap="large")
    with col_sel:
        st.markdown('<div class="section-label">대리점 선택</div>', unsafe_allow_html=True)
        selected = st.selectbox("대리점", ["대리점을 선택하세요"] + AGENT_LIST,
                                label_visibility="collapsed", key="viewer_agent")
    with col_perf:
        st.markdown('<div class="section-label">실적 기준 (만원, 쉼표 구분)</div>',
                    unsafe_allow_html=True)
        perf_input = st.text_input("실적", value="10, 20, 30, 50",
                                   label_visibility="collapsed", key="viewer_perfs")

    try:
        perf_list = [int(x.strip()) * 10_000 for x in perf_input.split(",") if x.strip().isdigit()]
        if not perf_list:
            perf_list = DEFAULT_PERFS
    except Exception:
        perf_list = DEFAULT_PERFS

    if selected == "대리점을 선택하세요":
        st.markdown("""<div style='text-align:center;padding:3.5rem;color:#bbb'>
            <div style='font-size:3rem'>🏢</div>
            <div style='margin-top:.6rem;font-weight:500'>대리점을 선택해 주세요</div>
        </div>""", unsafe_allow_html=True)
        return

    _d = st.session_state.all_data.get(selected, {})
    awards = _d if isinstance(_d, list) else _d.get("awards", [])

    if not awards:
        st.markdown(f"""<div style='text-align:center;padding:3.5rem;color:#bbb'>
            <div style='font-size:3rem'>📋</div>
            <div style='margin-top:.6rem;font-weight:600;color:#555'>{selected}</div>
            <div style='font-size:.88rem;margin-top:.3rem'>등록된 시상 항목이 없습니다<br>
            관리자 화면에서 시상 이미지를 업로드하세요</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown(f'<div class="section-label">{selected} · 실적별 총 시상금</div>',
                unsafe_allow_html=True)

    perf_labels = [fmt_man(p) for p in perf_list]
    header_cells = "".join(f"<th>{lbl}</th>" for lbl in perf_labels)
    rows_html = ""
    for aw in awards:
        badge_cls = "badge-flat" if aw["type"] == "정률" else "badge-tier"
        badge_txt = "정률" if aw["type"] == "정률" else "구간"
        cells = "".join(f"<td>{fmt_won(calc_award(aw, p))}</td>" for p in perf_list)
        rows_html += (f"<tr><td>{aw['name']}"
                      f"<span class='type-badge {badge_cls}'>{badge_txt}</span></td>{cells}</tr>")
    total_cells = "".join(
        f"<td>{fmt_won(sum(calc_award(aw, p) for aw in awards))}</td>" for p in perf_list)
    rows_html += f"<tr><td>✅ 합계</td>{total_cells}</tr>"

    st.markdown(f"""
    <table class="sum-table">
        <thead><tr><th>시상항목</th>{header_cells}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 관리자 — 구간 편집기
# ══════════════════════════════════════════════════════════════
def render_tier_editor(tiers: list, key_prefix: str):
    updated, to_remove = [], None
    c0,c1,c2,c3,c4 = st.columns([0.3,2,2,2,0.6])
    c0.markdown("**#**"); c1.markdown("**하한(만원)**")
    c2.markdown("**상한(만원)**"); c3.markdown("**률(%)**")

    for i, t in enumerate(tiers):
        c0,c1,c2,c3,c4 = st.columns([0.3,2,2,2,0.6])
        c0.markdown(f"<div style='padding:.5rem 0;color:#999'>{i+1}</div>", unsafe_allow_html=True)
        lo = c1.number_input("하한", min_value=0, value=t["from"]//10_000,
                             key=f"{key_prefix}_lo_{i}", label_visibility="collapsed")
        hi_str = "" if t["to"] == -1 else str(t["to"]//10_000)
        hi_inp = c2.text_input("상한", value=hi_str, placeholder="이상(∞)",
                               key=f"{key_prefix}_hi_{i}", label_visibility="collapsed")
        rt = c3.number_input("률", min_value=0.0, max_value=10000.0, value=float(t["rate"]),
                             step=10.0, key=f"{key_prefix}_rt_{i}", label_visibility="collapsed")
        if c4.button("✕", key=f"{key_prefix}_del_{i}") and len(tiers) > 1:
            to_remove = i
        hi_val = -1 if hi_inp.strip() == "" else int(hi_inp)*10_000
        updated.append({"from": lo*10_000, "to": hi_val, "rate": rt})

    if to_remove is not None:
        updated.pop(to_remove)
        return updated, True
    if st.button("＋ 구간 추가", key=f"{key_prefix}_addtier"):
        last = updated[-1]
        new_lo = last["to"] if last["to"] != -1 else (last["from"]+100_000)
        updated.append({"from": new_lo, "to": -1, "rate": 100.0})
        return updated, True
    return updated, False


# ══════════════════════════════════════════════════════════════
# 관리자 — 시상 항목 폼 (추가/수정 공용)
# ══════════════════════════════════════════════════════════════
def award_form(prefix: str, init: dict | None = None) -> dict | None:
    init = init or {}
    name = st.text_input("시상 이름 *", value=init.get("name",""),
                         key=f"{prefix}_name", placeholder="예: 장기보험 GA 시상")
    desc = st.text_input("시상 내용 (선택)", value=init.get("desc",""),
                         key=f"{prefix}_desc", placeholder="예: 장기 실적 기준 지급")
    atype = st.radio("계산 방식", ["정률","구간별"], horizontal=True,
                     index=0 if init.get("type","정률")=="정률" else 1,
                     key=f"{prefix}_type")
    result = None
    if atype == "정률":
        rate = st.number_input("시책률 (%)", min_value=0.0, max_value=10000.0,
                               value=float(init.get("rate") or 100.0),
                               step=10.0, key=f"{prefix}_rate")
        cs, cc = st.columns(2)
        if cs.button("✅ 저장", key=f"{prefix}_save", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("시상 이름을 입력하세요.")
            else:
                result = {"name":name.strip(),"desc":desc.strip(),
                          "type":"정률","rate":rate,"tiers":None}
        if cc.button("취소", key=f"{prefix}_cancel", use_container_width=True):
            result = "cancel"
    else:
        st.markdown("**구간 설정**")
        tk = f"{prefix}_tiers_state"
        if tk not in st.session_state:
            st.session_state[tk] = copy.deepcopy(
                init.get("tiers") or [{"from":0,"to":100_000,"rate":100.0}])
        new_tiers, need_rerun = render_tier_editor(st.session_state[tk], prefix)
        st.session_state[tk] = new_tiers
        if need_rerun:
            st.rerun()
        cs, cc = st.columns(2)
        if cs.button("✅ 저장", key=f"{prefix}_save", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("시상 이름을 입력하세요.")
            else:
                result = {"name":name.strip(),"desc":desc.strip(),
                          "type":"구간별","rate":None,
                          "tiers":copy.deepcopy(st.session_state[tk])}
        if cc.button("취소", key=f"{prefix}_cancel", use_container_width=True):
            result = "cancel"
    return result


# ══════════════════════════════════════════════════════════════
# 관리자 화면
# ══════════════════════════════════════════════════════════════
def page_admin():
    st.markdown(CSS, unsafe_allow_html=True)

    # ── 로그인 ─────────────────────────────────────────────────
    if not st.session_state.admin_auth:
        _, mid, _ = st.columns([1,1.6,1])
        with mid:
            st.markdown("""
            <div style='text-align:center;padding:3rem 0 1.5rem'>
                <div style='font-size:3rem'>🔐</div>
                <h3 style='color:#800000;margin:.5rem 0 .2rem;font-size:1.3rem'>관리자 로그인</h3>
                <p style='color:#aaa;font-size:.88rem'>관리자 비밀번호를 입력하세요</p>
            </div>""", unsafe_allow_html=True)
            pw = st.text_input("비밀번호", type="password",
                               label_visibility="collapsed",
                               placeholder="비밀번호 입력", key="admin_pw_input")
            if st.button("로그인", use_container_width=True, type="primary", key="login_btn"):
                if pw == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        return

    # ── 헤더 ───────────────────────────────────────────────────
    ch, co = st.columns([6,1])
    with ch:
        st.markdown("""
        <div class="admin-header-bar">
            <span style='font-size:1.7rem'>⚙️</span>
            <div>
                <div class="admin-header-title">관리자 설정</div>
                <div class="admin-header-sub">시상 이미지 업로드 → AI 자동 분석 → 항목 편집 → 저장</div>
            </div>
        </div>""", unsafe_allow_html=True)
    with co:
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        if st.button("로그아웃", key="logout", use_container_width=True):
            st.session_state.admin_auth = False
            st.rerun()

    # ── 대리점 선택 ────────────────────────────────────────────
    ca, cb = st.columns([4,1], gap="medium")
    with ca:
        with st.container(border=True):
            st.markdown('<p class="admin-sec-title">대리점 선택</p>', unsafe_allow_html=True)
            agent = st.selectbox("대리점", ["대리점을 선택하세요"] + AGENT_LIST,
                                 label_visibility="collapsed", key="admin_agent")

    if agent != "대리점을 선택하세요" and st.session_state.edit_agent != agent:
        st.session_state.edit_agent = agent
        saved = st.session_state.all_data.get(agent, {})
        # 구버전(list) / 신버전(dict) 모두 호환
        if isinstance(saved, list):
            st.session_state.edit_awards = copy.deepcopy(saved)
        else:
            st.session_state.edit_awards = copy.deepcopy(saved.get("awards", []))
        st.session_state.editing_idx = None
        st.session_state.add_mode = False
        st.session_state.last_uploaded = None

    if agent == "대리점을 선택하세요":
        st.info("👆 대리점을 선택하면 시상 항목을 관리할 수 있습니다.")
        return

    awards = st.session_state.edit_awards

    # 현황 카드도 구버전 호환
    def _saved_count(agent):
        s = st.session_state.all_data.get(agent, {})
        if isinstance(s, list):
            return len(s)
        return len(s.get("awards", []))

    with cb:
        with st.container(border=True):
            st.markdown('<p class="admin-sec-title">현황</p>', unsafe_allow_html=True)
            st.metric("시상 항목", f"{len(awards)}개")
            st.caption(f"저장됨: {_saved_count(agent)}개")

    # ══════════════════════════════════════════════════════════
    # 메인 레이아웃: 좌(업로드+목록) / 우(폼)
    # ══════════════════════════════════════════════════════════
    left_col, right_col = st.columns([5, 4], gap="large")

    # ── 좌: 이미지 업로드 + AI 분석 ───────────────────────────
    with left_col:

        with st.container(border=True):
            st.markdown('<p class="admin-sec-title">📷 시상 이미지 업로드 & AI 분석</p>',
                        unsafe_allow_html=True)

            # API 키 직접 입력 (secrets/env 설정 없이도 사용 가능)
            with st.expander("🔑 Anthropic API 키 설정", expanded=not bool(_get_api_key())):
                manual_key = st.text_input(
                    "API 키를 직접 입력하세요 (sk-ant-...)",
                    value=st.session_state.get("manual_api_key", ""),
                    type="password",
                    key="api_key_input",
                    placeholder="sk-ant-api03-...",
                    help="여기에 입력한 키가 최우선으로 사용됩니다.",
                )
                if manual_key != st.session_state.get("manual_api_key", ""):
                    st.session_state.manual_api_key = manual_key
                    st.rerun()
                cur_key = _get_api_key()
                if cur_key:
                    masked = cur_key[:12] + "..." + cur_key[-4:]
                    st.success(f"✅ 키 준비됨: `{masked}`")
                else:
                    st.warning("API 키가 없습니다. 위에 직접 입력하거나 Streamlit Secrets에 설정하세요.")

            uploaded = st.file_uploader(
                "시상 계획서 이미지를 업로드하세요",
                type=["png","jpg","jpeg","webp"],
                key="award_image",
                label_visibility="collapsed",
            )

            if uploaded:
                st.image(uploaded, caption="업로드된 시상 이미지", use_container_width=True)

                # 새 파일이면 분석 버튼 활성화
                file_id = f"{uploaded.name}_{uploaded.size}"
                already_analyzed = st.session_state.last_uploaded == file_id

                if already_analyzed:
                    st.success("✅ 이 이미지는 이미 분석되었습니다. 아래 목록을 확인하세요.")
                    if st.button("🔄 다시 분석", use_container_width=True, key="reanalyze_btn"):
                        st.session_state.last_uploaded = None
                        st.rerun()
                else:
                    api_key = _get_api_key()
                    if api_key and st.button("🤖 AI로 시상 항목 자동 추출", use_container_width=True,
                                     type="primary", key="analyze_btn"):
                            with st.spinner("Claude AI가 시상 이미지를 분석 중입니다..."):
                                try:
                                    img_bytes = uploaded.read()
                                    mt_map = {"png":"image/png","jpg":"image/jpeg",
                                              "jpeg":"image/jpeg","webp":"image/webp"}
                                    ext = uploaded.name.rsplit(".",1)[-1].lower()
                                    media_type = mt_map.get(ext, "image/jpeg")

                                    extracted = analyze_image_with_claude(img_bytes, media_type)

                                    if extracted:
                                        # 기존 항목에 병합 (중복 이름 제외)
                                        existing_names = {a["name"] for a in awards}
                                        added = 0
                                        for aw in extracted:
                                            if aw["name"] not in existing_names:
                                                awards.append(aw)
                                                existing_names.add(aw["name"])
                                                added += 1
                                        st.session_state.last_uploaded = file_id
                                        st.success(f"✅ {len(extracted)}개 항목 추출 완료! "
                                                   f"(신규 추가: {added}개)")
                                        st.rerun()
                                    else:
                                        st.warning("이미지에서 시상 항목을 찾을 수 없었습니다. "
                                                   "수동으로 추가해 주세요.")
                                except json.JSONDecodeError:
                                    st.error("AI 응답 파싱 오류. 다시 시도해 주세요.")
                                except Exception as e:
                                    st.error(f"분석 오류: {e}")

        # ── 시상 항목 목록 ─────────────────────────────────────
        with st.container(border=True):
            st.markdown('<p class="admin-sec-title">시상 항목 목록</p>', unsafe_allow_html=True)

            if not awards:
                st.markdown(
                    "<p style='color:#bbb;text-align:center;padding:1.5rem 0'>"
                    "이미지를 업로드하거나 아래 버튼으로 직접 추가하세요</p>",
                    unsafe_allow_html=True)
            else:
                for i, aw in enumerate(awards):
                    is_editing = st.session_state.editing_idx == i
                    badge = "정률" if aw["type"] == "정률" else "구간별"
                    rate_info = (f"{aw['rate']}%" if aw["type"] == "정률"
                                 else f"{len(aw['tiers'])}구간")
                    card_cls = "aw-card editing" if is_editing else "aw-card"
                    # AI 분석 항목 표시
                    ai_mark = ""

                    st.markdown(f"""
                    <div class="{card_cls}">
                        <div class="aw-card-name">{aw['name']}{ai_mark}
                            <span style='font-size:.7rem;background:#f5e5e5;color:#800000;
                            padding:1px 7px;border-radius:20px;margin-left:6px;font-weight:700'>
                            {badge} · {rate_info}</span>
                        </div>
                        <div class="aw-card-meta">{aw.get('desc') or '(설명 없음)'}</div>
                    </div>""", unsafe_allow_html=True)

                    bc1, bc2, bc3 = st.columns([1,1,3])
                    if bc1.button("✏️ 수정", key=f"edit_{i}", use_container_width=True):
                        st.session_state.editing_idx = i
                        st.session_state.add_mode = False
                        st.rerun()
                    if bc2.button("🗑 삭제", key=f"del_{i}", use_container_width=True):
                        awards.pop(i)
                        if st.session_state.editing_idx == i:
                            st.session_state.editing_idx = None
                        st.rerun()

        # 저장 / 추가 버튼
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        if st.button("💾  저장 — 대리점 시상 확정", use_container_width=True,
                     type="primary", key="save_btn"):
            if agent not in st.session_state.all_data:
                st.session_state.all_data[agent] = {}
            st.session_state.all_data[agent]["awards"] = copy.deepcopy(awards)
            save_data(st.session_state.all_data)
            st.success(f"✅  '{agent}' 시상 항목 저장 완료! ({len(awards)}개)")

        if st.button("＋  시상 항목 직접 추가", use_container_width=True, key="add_btn"):
            st.session_state.add_mode = True
            st.session_state.editing_idx = None
            st.rerun()

    # ── 우: 추가/수정 폼 ───────────────────────────────────────
    with right_col:
        if st.session_state.add_mode:
            with st.container(border=True):
                st.markdown('<p class="admin-sec-title">새 시상 항목 추가</p>',
                            unsafe_allow_html=True)
                result = award_form("add_form")
            if result == "cancel":
                st.session_state.add_mode = False
                st.session_state.pop("add_form_tiers_state", None)
                st.rerun()
            elif result is not None:
                awards.append(result)
                st.session_state.add_mode = False
                st.session_state.pop("add_form_tiers_state", None)
                st.rerun()

        elif st.session_state.editing_idx is not None:
            idx = st.session_state.editing_idx
            if 0 <= idx < len(awards):
                with st.container(border=True):
                    st.markdown(f'<p class="admin-sec-title">시상 항목 수정 #{idx+1}</p>',
                                unsafe_allow_html=True)
                    result = award_form(f"edit_form_{idx}", init=copy.deepcopy(awards[idx]))
                if result == "cancel":
                    st.session_state.editing_idx = None
                    st.session_state.pop(f"edit_form_{idx}_tiers_state", None)
                    st.rerun()
                elif result is not None:
                    awards[idx] = result
                    st.session_state.editing_idx = None
                    st.session_state.pop(f"edit_form_{idx}_tiers_state", None)
                    st.rerun()
        else:
            st.markdown("""
            <div style='text-align:center;padding:4rem 1rem;color:#ccc'>
                <div style='font-size:2.5rem'>🤖</div>
                <div style='margin-top:.6rem;font-weight:500;font-size:.92rem'>
                    이미지를 업로드하면 AI가<br>시상 항목을 자동으로 추출합니다<br><br>
                    <span style='font-size:.82rem'>항목을 선택하면 수정할 수 있습니다</span>
                </div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 라우터
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "viewer":
    page_viewer()
else:
    page_admin()
