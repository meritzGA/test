"""
메리츠 카톡 단체발송 시스템
나인톡 방식 (PC카톡 자동화) + GA 실적 연동
"""

import streamlit as st
import json
import os
import uuid
import pandas as pd
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────
# 데이터 경로 설정
# ─────────────────────────────────────────
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CONTACTS_FILE  = DATA_DIR / "contacts.json"
GROUPS_FILE    = DATA_DIR / "groups.json"
SETTINGS_FILE  = DATA_DIR / "settings.json"
HISTORY_FILE   = DATA_DIR / "history.json"
SCHEDULE_FILE  = DATA_DIR / "schedule.json"

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except:
            return default
    return default

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ─────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────
st.set_page_config(
    page_title="카톡 단체발송",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

* { font-family: 'Noto Sans KR', sans-serif !important; }

[data-testid="stAppViewContainer"] { background: #F0F2F6; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A237E 0%, #283593 100%) !important;
}
[data-testid="stSidebar"] * { color: #E8EAF6 !important; }
[data-testid="stSidebar"] .stRadio label { color: white !important; }

.card {
    background: white; border-radius: 12px;
    padding: 1.2rem 1.5rem; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.header-bar {
    background: linear-gradient(135deg, #FEE500 0%, #FFD600 100%);
    padding: 1rem 2rem; border-radius: 12px;
    margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 1rem;
}
.stat-card {
    background: white; border-radius: 10px;
    padding: 1rem; text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.contact-row {
    background: white; border-radius: 8px;
    padding: 0.8rem 1rem; margin: 0.3rem 0;
    border-left: 3px solid #FEE500;
    display: flex; align-items: center;
}
.badge {
    background: #E8EAF6; color: #3949AB;
    padding: 2px 8px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600;
}
.badge-반말 { background: #FFF3E0; color: #E65100; }
.badge-존칭 { background: #E8F5E9; color: #2E7D32; }
.preview-bubble {
    background: #FEE500; border-radius: 12px 12px 12px 2px;
    padding: 1rem 1.2rem; max-width: 320px;
    font-size: 0.88rem; line-height: 1.6; white-space: pre-wrap;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}
.log-terminal {
    background: #1A1A2E; color: #00FF88;
    font-family: 'Courier New', monospace !important;
    padding: 1rem; border-radius: 8px;
    height: 280px; overflow-y: auto;
    font-size: 0.82rem; white-space: pre-wrap;
}
.warn-banner {
    background: #FFF8E1; border-left: 4px solid #FFB300;
    padding: 0.8rem 1rem; border-radius: 0 8px 8px 0;
    margin: 0.5rem 0; font-size: 0.88rem;
}
.success-banner {
    background: #E8F5E9; border-left: 4px solid #43A047;
    padding: 0.8rem 1rem; border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
}
.stButton>button {
    border-radius: 8px !important; font-weight: 600 !important;
}
.primary-btn>button {
    background: #FEE500 !important; color: #1A1A1A !important;
    border: none !important;
}
.danger-btn>button {
    background: #F44336 !important; color: white !important;
    border: none !important;
}
.send-btn>button {
    background: #1A237E !important; color: #FEE500 !important;
    font-size: 1.05rem !important; padding: 0.7rem 2rem !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 세션 초기화
# ─────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "고객관리"
if "logs" not in st.session_state:
    st.session_state.logs = []
if "sending" not in st.session_state:
    st.session_state.sending = False
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = False

# ─────────────────────────────────────────
# 사이드바 네비게이션
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💬 카톡 단체발송")
    st.markdown("**메리츠화재 GA 관리 시스템**")
    st.markdown("---")

    pages = {
        "👥 고객 관리":   "고객관리",
        "✉️ 메시지 작성":  "메시지작성",
        "🚀 발 송":       "발송",
        "📅 예약 발송":   "예약발송",
        "📊 발송 내역":   "발송내역",
        "⚙️ 설 정":       "설정",
    }
    for label, key in pages.items():
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.page == key else "secondary"):
            st.session_state.page = key
            st.rerun()

    st.markdown("---")
    contacts = load_json(CONTACTS_FILE, [])
    groups   = load_json(GROUPS_FILE, ["기본"])
    st.markdown(f"**등록 고객:** {len(contacts)}명")
    st.markdown(f"**그룹 수:** {len(groups)}개")

    settings = load_json(SETTINGS_FILE, {
        "delay": 3, "search_delay": 2,
        "kakao_x": 960, "kakao_y": 60,
        "search_by": "이름"
    })

page = st.session_state.page

# ═══════════════════════════════════════════════════
# PAGE 1: 고객 관리
# ═══════════════════════════════════════════════════
if page == "고객관리":
    st.markdown("""<div class="header-bar">
        <span style="font-size:1.8rem">👥</span>
        <div>
            <h2 style="margin:0;color:#1A1A1A">고객 관리</h2>
            <span style="color:#555;font-size:0.85rem">연락처 등록 · 그룹 관리 · 호칭/존칭 설정</span>
        </div>
    </div>""", unsafe_allow_html=True)

    contacts = load_json(CONTACTS_FILE, [])
    groups   = load_json(GROUPS_FILE, ["기본"])

    tab_list, tab_add, tab_import, tab_group = st.tabs(
        ["📋 전체 명단", "➕ 고객 추가", "📥 명단 불러오기", "🗂️ 그룹 관리"]
    )

    # ── 전체 명단
    with tab_list:
        col_search, col_group_filter = st.columns([2, 1])
        with col_search:
            search_q = st.text_input("🔍 이름 검색", placeholder="이름 입력...")
        with col_group_filter:
            group_filter = st.selectbox("그룹 필터", ["전체"] + groups)

        filtered = contacts
        if search_q:
            filtered = [c for c in filtered if search_q in c.get("name","") or search_q in c.get("kakao_name","")]
        if group_filter != "전체":
            filtered = [c for c in filtered if c.get("group") == group_filter]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:1.8rem;font-weight:700;color:#1A237E">{len(contacts)}</div>
                <div style="color:#666;font-size:0.82rem">전체 고객</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            존칭_count = sum(1 for c in contacts if c.get("speech")=="존칭")
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:1.8rem;font-weight:700;color:#2E7D32">{존칭_count}</div>
                <div style="color:#666;font-size:0.82rem">존칭 발송</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            반말_count = sum(1 for c in contacts if c.get("speech")=="반말")
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:1.8rem;font-weight:700;color:#E65100">{반말_count}</div>
                <div style="color:#666;font-size:0.82rem">반말 발송</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"<br>**{len(filtered)}명** 표시 중", unsafe_allow_html=True)

        if filtered:
            # 데이터프레임으로 표시 + 편집
            df = pd.DataFrame(filtered)
            display_cols = ["name", "kakao_name", "nickname", "group", "speech", "phone"]
            display_cols = [c for c in display_cols if c in df.columns]
            col_rename = {"name":"이름","kakao_name":"카톡대화명","nickname":"호칭",
                         "group":"그룹","speech":"존칭/반말","phone":"전화번호"}
            st.dataframe(
                df[display_cols].rename(columns=col_rename),
                use_container_width=True, height=400
            )

            # 선택 삭제
            if st.button("🗑️ 전체 초기화", type="secondary"):
                if st.session_state.get("confirm_delete"):
                    save_json(CONTACTS_FILE, [])
                    st.success("초기화 완료")
                    st.session_state.confirm_delete = False
                    st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.warning("한 번 더 누르면 전체 삭제됩니다.")
        else:
            st.info("등록된 고객이 없습니다. '고객 추가' 또는 '명단 불러오기' 탭을 이용하세요.")

    # ── 고객 추가
    with tab_add:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            new_name = st.text_input("이름 *", placeholder="홍길동")
            new_kakao = st.text_input("카톡 대화명 *", placeholder="PC카톡에 표시되는 이름")
            new_nickname = st.text_input("호칭", placeholder="예: 길동씨, 팀장님")
        with col_b:
            new_group = st.selectbox("그룹", groups)
            new_speech = st.radio("존칭/반말", ["존칭", "반말"], horizontal=True)
            new_phone = st.text_input("전화번호", placeholder="01012345678")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button("➕ 고객 추가", use_container_width=False):
            if new_name and new_kakao:
                contacts = load_json(CONTACTS_FILE, [])
                contacts.append({
                    "id": str(uuid.uuid4())[:8],
                    "name": new_name,
                    "kakao_name": new_kakao,
                    "nickname": new_nickname or new_name,
                    "group": new_group,
                    "speech": new_speech,
                    "phone": new_phone
                })
                save_json(CONTACTS_FILE, contacts)
                st.success(f"✅ {new_name}님 추가 완료!")
                st.rerun()
            else:
                st.error("이름과 카톡 대화명은 필수입니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 명단 불러오기 (Excel/CSV)
    with tab_import:
        st.markdown("""<div class="warn-banner">
            ⚠️ 반드시 <strong>채팅 이력이 있는 고객만</strong> 등록하세요.
            채팅 이력 없는 발송 시 카카오 이용제한 위험이 있습니다.
        </div>""", unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Excel/CSV 파일 업로드",
            type=["xlsx","csv"],
            help="필수컬럼: 이름, 카톡대화명 / 선택: 호칭, 그룹, 존칭반말, 전화번호"
        )

        st.markdown("**Excel 양식 예시:**")
        sample_df = pd.DataFrame({
            "이름": ["홍길동","김철수"],
            "카톡대화명": ["홍길동 대표님","김철수님"],
            "호칭": ["길동이사님","철수야"],
            "그룹": ["VIP","일반"],
            "존칭반말": ["존칭","반말"],
            "전화번호": ["01012345678","01098765432"],
            "실적": ["1,200,000","980,000"],
            "달성률": ["87%","72%"]
        })
        st.dataframe(sample_df, use_container_width=True)

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)
                df.columns = df.columns.str.strip()

                col_map = {
                    "이름": "name", "카톡대화명": "kakao_name",
                    "호칭": "nickname", "그룹": "group",
                    "존칭반말": "speech", "전화번호": "phone"
                }

                if "이름" not in df.columns or "카톡대화명" not in df.columns:
                    st.error("'이름'과 '카톡대화명' 컬럼이 필수입니다.")
                else:
                    st.success(f"✅ {len(df)}명 미리보기")
                    st.dataframe(df.head(5), use_container_width=True)

                    # 추가 컬럼은 custom_fields로 저장
                    std_cols = list(col_map.keys())
                    extra_cols = [c for c in df.columns if c not in std_cols]

                    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
                    if st.button(f"📥 {len(df)}명 등록하기"):
                        contacts = load_json(CONTACTS_FILE, [])
                        existing_groups = load_json(GROUPS_FILE, ["기본"])

                        added = 0
                        for _, row in df.iterrows():
                            custom = {c: str(row[c]) for c in extra_cols if pd.notna(row.get(c,""))}
                            grp = str(row.get("그룹","기본")) if "그룹" in df.columns else "기본"
                            if grp not in existing_groups:
                                existing_groups.append(grp)

                            contacts.append({
                                "id": str(uuid.uuid4())[:8],
                                "name": str(row.get("이름","")),
                                "kakao_name": str(row.get("카톡대화명","")),
                                "nickname": str(row.get("호칭", row.get("이름",""))),
                                "group": grp,
                                "speech": str(row.get("존칭반말","존칭")),
                                "phone": str(row.get("전화번호","")),
                                "custom_fields": custom
                            })
                            added += 1

                        save_json(CONTACTS_FILE, contacts)
                        save_json(GROUPS_FILE, existing_groups)
                        st.success(f"🎉 {added}명 등록 완료!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"파일 오류: {e}")

    # ── 그룹 관리
    with tab_group:
        col_gl, col_gr = st.columns([1, 1])
        with col_gl:
            st.markdown("**그룹 목록**")
            groups = load_json(GROUPS_FILE, ["기본"])
            for i, g in enumerate(groups):
                cnt = sum(1 for c in contacts if c.get("group")==g)
                c1, c2 = st.columns([3,1])
                with c1:
                    new_gname = st.text_input(f"그룹 {i+1}", value=g, key=f"gname_{i}",
                                              label_visibility="collapsed")
                with c2:
                    if st.button("🗑️", key=f"gdel_{i}") and len(groups) > 1:
                        groups.pop(i)
                        save_json(GROUPS_FILE, groups)
                        st.rerun()
                if new_gname != g:
                    # 그룹명 변경 → 연락처도 업데이트
                    groups[i] = new_gname
                    for contact in contacts:
                        if contact.get("group") == g:
                            contact["group"] = new_gname
                    save_json(GROUPS_FILE, groups)
                    save_json(CONTACTS_FILE, contacts)
                    st.rerun()
                st.caption(f"{cnt}명")

        with col_gr:
            st.markdown("**새 그룹 추가**")
            new_group_name = st.text_input("그룹명", placeholder="예: VIP고객, 설계사팀")
            if st.button("➕ 그룹 추가"):
                if new_group_name and new_group_name not in groups:
                    groups.append(new_group_name)
                    save_json(GROUPS_FILE, groups)
                    st.success(f"'{new_group_name}' 그룹 추가!")
                    st.rerun()

# ═══════════════════════════════════════════════════
# PAGE 2: 메시지 작성
# ═══════════════════════════════════════════════════
elif page == "메시지작성":
    st.markdown("""<div class="header-bar">
        <span style="font-size:1.8rem">✉️</span>
        <div>
            <h2 style="margin:0;color:#1A1A1A">메시지 작성</h2>
            <span style="color:#555;font-size:0.85rem">개인화 템플릿 · 실적 변수 · 미리보기</span>
        </div>
    </div>""", unsafe_allow_html=True)

    contacts = load_json(CONTACTS_FILE, [])

    col_edit, col_preview = st.columns([1, 1], gap="large")

    with col_edit:
        st.markdown("### 📝 메시지 템플릿")

        # 인사말 선택
        with st.expander("💡 인사말 선택"):
            greeting_type = st.selectbox("테마", [
                "없음", "계절-봄", "계절-여름", "계절-가을", "계절-겨울",
                "월요일", "금요일", "명언", "감사", "기원"
            ])
            greetings = {
                "계절-봄": "따뜻한 봄기운과 함께 즐거운 하루 보내시길 바랍니다 🌸",
                "계절-여름": "무더운 여름, 건강하고 활기차게 보내시길 바랍니다 ☀️",
                "계절-가을": "선선한 가을바람처럼 상쾌한 하루 되세요 🍁",
                "계절-겨울": "추운 날씨에 건강 잘 챙기시고 따뜻하게 지내세요 ❄️",
                "월요일": "새로운 한 주의 시작, 활기차고 즐거운 월요일 되세요! 💪",
                "금요일": "한 주 동안 수고 많으셨습니다. 즐거운 주말 보내세요! 😊",
                "명언": "\"작은 일에도 최선을 다하는 사람이 큰일도 해낼 수 있습니다.\"",
                "감사": "항상 신뢰해 주셔서 진심으로 감사드립니다 🙏",
                "기원": "오늘도 좋은 일만 가득하시길 바랍니다! ✨",
            }
            if greeting_type != "없음":
                st.info(greetings[greeting_type])
                if st.button("➕ 메시지에 추가"):
                    current = st.session_state.get("template_text","")
                    st.session_state["template_text"] = greetings[greeting_type] + "\n\n" + current

        # 변수 도움말
        with st.expander("📌 사용 가능한 변수"):
            st.markdown("""
**기본 변수** (고객 정보에서 자동 치환)
- `{{이름}}` → 등록된 이름
- `{{호칭}}` → 설정된 호칭
- `{{그룹}}` → 그룹명

**실적 변수** (Excel 명단의 컬럼명)
- `{{실적}}` → 실적금액
- `{{달성률}}` → 달성률
- `{{순위}}` → 순위
- 기타 Excel에 입력한 컬럼명 모두 사용 가능

**날짜 변수**
- `{{오늘}}` → 오늘 날짜
- `{{이번달}}` → 이번 달
            """)

        template_default = """안녕하세요, {{호칭}}!

이번 달 실적 현황을 안내드립니다 📊

✅ 실적: {{실적}}원
🎯 달성률: {{달성률}}%

항상 수고 많으십니다.
메리츠화재 드림"""

        template = st.text_area(
            "메시지 내용 (최대 2,000자)",
            value=st.session_state.get("template_text", template_default),
            height=280, max_chars=2000, key="template_editor"
        )
        st.session_state["template_text"] = template
        st.caption(f"{len(template)}/2000자")

        # 파일 첨부 옵션
        st.markdown("**📎 파일 첨부**")
        attach_type = st.radio("첨부 유형", ["없음","이미지","링크"], horizontal=True)
        attach_value = ""
        if attach_type == "이미지":
            attach_value = st.text_input("이미지 파일 경로", placeholder="C:/image.jpg")
        elif attach_type == "링크":
            attach_value = st.text_input("URL", placeholder="https://...")

        st.session_state["attach_type"] = attach_type
        st.session_state["attach_value"] = attach_value

        # 저장
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button("💾 템플릿 저장", use_container_width=True):
            tmpl_data = {
                "text": template,
                "attach_type": attach_type,
                "attach_value": attach_value,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            save_json(DATA_DIR / "template.json", tmpl_data)
            st.success("템플릿 저장 완료!")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_preview:
        st.markdown("### 👁️ 미리보기")

        def apply_template(tmpl, contact):
            msg = tmpl
            # 날짜 치환
            msg = msg.replace("{{오늘}}", datetime.now().strftime("%Y년 %m월 %d일"))
            msg = msg.replace("{{이번달}}", datetime.now().strftime("%Y년 %m월"))
            # 기본 필드
            msg = msg.replace("{{이름}}", contact.get("name",""))
            msg = msg.replace("{{호칭}}", contact.get("nickname", contact.get("name","")))
            msg = msg.replace("{{그룹}}", contact.get("group",""))
            # custom fields
            for k, v in contact.get("custom_fields",{}).items():
                msg = msg.replace(f"{{{{{k}}}}}", str(v))
            return msg

        if contacts:
            preview_idx = st.slider("미리보기 고객", 1, min(len(contacts),10), 1) - 1
            c = contacts[preview_idx]
            preview_msg = apply_template(template, c)
            speech = c.get("speech","존칭")

            st.markdown(f"""
            <div style="background:#f5f5f5; padding:1rem; border-radius:12px; margin-bottom:1rem">
                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.8rem">
                    <div style="width:36px;height:36px;background:#FEE500;border-radius:50%;
                                display:flex;align-items:center;justify-content:center;font-weight:700">
                        {c.get('name','?')[0]}
                    </div>
                    <div>
                        <strong>{c.get('name','')}</strong>
                        <span style="color:#888;font-size:0.8rem;margin-left:0.5rem">
                            {c.get('kakao_name','')}
                        </span>
                        <span class="badge badge-{speech}" style="margin-left:0.5rem">{speech}</span>
                    </div>
                </div>
                <div class="preview-bubble">{preview_msg}</div>
            </div>
            """, unsafe_allow_html=True)

            # 전체 미리보기 목록
            st.markdown("**전체 미리보기 (상위 5명)**")
            for i, c2 in enumerate(contacts[:5]):
                msg2 = apply_template(template, c2)
                with st.expander(f"{i+1}. {c2.get('name','')} ({c2.get('speech','존칭')})"):
                    st.text(msg2)
        else:
            st.info("고객을 먼저 등록해주세요.")

        # 발송 대상 선택 요약
        st.markdown("### 📋 발송 대상 선택")
        groups = load_json(GROUPS_FILE, ["기본"])
        selected_groups = st.multiselect("발송 그룹 선택", groups, default=groups)
        selected_contacts = [c for c in contacts if c.get("group","기본") in selected_groups]
        st.info(f"선택된 발송 대상: **{len(selected_contacts)}명**")
        st.session_state["selected_groups"] = selected_groups


# ═══════════════════════════════════════════════════
# PAGE 3: 발송
# ═══════════════════════════════════════════════════
elif page == "발송":
    st.markdown("""<div class="header-bar">
        <span style="font-size:1.8rem">🚀</span>
        <div>
            <h2 style="margin:0;color:#1A1A1A">단체 발송</h2>
            <span style="color:#555;font-size:0.85rem">테스트 발송 → 확인 → 단체 발송</span>
        </div>
    </div>""", unsafe_allow_html=True)

    try:
        import pyautogui
        import pyperclip
        PYAUTOGUI_OK = True
    except ImportError:
        PYAUTOGUI_OK = False

    contacts = load_json(CONTACTS_FILE, [])
    settings = load_json(SETTINGS_FILE, {"delay":3,"search_delay":2,"kakao_x":960,"kakao_y":60,"search_by":"이름"})
    template_data = load_json(DATA_DIR / "template.json", {"text": "{{호칭}}님, 안녕하세요!"})
    template = template_data.get("text","")

    selected_groups = st.session_state.get("selected_groups", load_json(GROUPS_FILE,["기본"]))
    send_targets = [c for c in contacts if c.get("group","기본") in selected_groups]

    def apply_template(tmpl, contact):
        msg = tmpl
        msg = msg.replace("{{오늘}}", datetime.now().strftime("%Y년 %m월 %d일"))
        msg = msg.replace("{{이번달}}", datetime.now().strftime("%Y년 %m월"))
        msg = msg.replace("{{이름}}", contact.get("name",""))
        msg = msg.replace("{{호칭}}", contact.get("nickname", contact.get("name","")))
        msg = msg.replace("{{그룹}}", contact.get("group",""))
        for k, v in contact.get("custom_fields",{}).items():
            msg = msg.replace(f"{{{{{k}}}}}", str(v))
        return msg

    if not PYAUTOGUI_OK:
        st.error("⚠️ pyautogui 미설치: `pip install pyautogui pyperclip` 후 재실행")

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown("### 📋 발송 요약")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:1.6rem;font-weight:700;color:#1A237E">{len(send_targets)}</div>
                <div style="font-size:0.8rem;color:#666">발송 대상</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            est = len(send_targets) * settings.get("delay",3)
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:1.6rem;font-weight:700;color:#FF6B35">~{est//60}분</div>
                <div style="font-size:0.8rem;color:#666">예상 시간</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:1.6rem;font-weight:700;color:#388E3C">{settings.get('delay',3)}초</div>
                <div style="font-size:0.8rem;color:#666">발송 간격</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("**발송 대상 목록 (상위 10명)**")
        if send_targets:
            df_preview = pd.DataFrame(send_targets[:10])[
                [c for c in ["name","kakao_name","group","speech"] if c in pd.DataFrame(send_targets).columns]
            ]
            st.dataframe(df_preview.rename(columns={
                "name":"이름","kakao_name":"카톡대화명","group":"그룹","speech":"존칭/반말"
            }), use_container_width=True)
        else:
            st.info("발송 대상이 없습니다. 고객 관리에서 등록 후 메시지 작성에서 그룹을 선택하세요.")

        st.markdown("**메시지 미리보기**")
        if send_targets:
            preview = apply_template(template, send_targets[0])
            st.markdown(f"""<div class="preview-bubble">{preview}</div>""", unsafe_allow_html=True)

    with col_r:
        st.markdown("### 🔧 발송 실행")

        st.markdown("""<div class="warn-banner">
            ⚠️ <strong>발송 전 체크:</strong><br>
            1. PC 카카오톡 로그인 확인<br>
            2. 설정에서 검색창 좌표 확인<br>
            3. 발송 중 마우스/키보드 조작 금지
        </div>""", unsafe_allow_html=True)

        # 테스트 발송
        st.markdown("**① 테스트 발송 (본인에게)**")
        test_name = st.text_input("본인 카톡 대화명", placeholder="내 이름 (카톡에 표시되는 이름)")
        if st.button("🧪 테스트 발송", disabled=not PYAUTOGUI_OK):
            if test_name and send_targets:
                test_msg = apply_template(template, send_targets[0])
                try:
                    time.sleep(3)
                    pyautogui.click(settings["kakao_x"], settings["kakao_y"])
                    time.sleep(0.4)
                    pyautogui.hotkey("ctrl","a")
                    pyperclip.copy(test_name)
                    pyautogui.hotkey("ctrl","v")
                    time.sleep(settings["search_delay"])
                    pyautogui.press("enter")
                    time.sleep(0.8)
                    pyautogui.press("enter")
                    time.sleep(0.8)
                    pyperclip.copy(test_msg)
                    pyautogui.hotkey("ctrl","v")
                    time.sleep(0.3)
                    pyautogui.press("enter")
                    st.success("✅ 테스트 발송 완료! 메시지를 확인하세요.")
                except Exception as e:
                    st.error(f"발송 실패: {e}")
            else:
                st.warning("카톡 대화명을 입력하세요.")

        st.markdown("---")

        # 실제 단체 발송
        st.markdown("**② 단체 발송**")

        if not st.session_state.sending:
            countdown = st.empty()
            st.markdown('<div class="send-btn">', unsafe_allow_html=True)
            start_btn = st.button(
                f"💬 {len(send_targets)}명에게 단체 발송 시작",
                disabled=(not PYAUTOGUI_OK or len(send_targets)==0),
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            stop_btn = st.button("⛔ 발송 중지", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if stop_btn:
                st.session_state.stop_flag = True

        # 진행률
        progress_bar = st.progress(0)
        status_text  = st.empty()
        log_area     = st.empty()

        if "start_btn" in dir() and start_btn and send_targets and PYAUTOGUI_OK:
            st.session_state.sending = True
            st.session_state.stop_flag = False
            st.session_state.logs = []
            pyautogui.FAILSAFE = True

            history_record = {
                "id": str(uuid.uuid4())[:8],
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(send_targets),
                "results": []
            }

            for i in range(5, 0, -1):
                status_text.warning(f"⏳ {i}초 후 발송... 지금 카카오톡 창을 앞으로!")
                time.sleep(1)

            for idx, contact in enumerate(send_targets):
                if st.session_state.stop_flag:
                    st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⛔ 중지됨")
                    break

                search_key = contact.get("kakao_name", contact.get("name",""))
                msg = apply_template(template, contact)

                try:
                    pyautogui.click(settings["kakao_x"], settings["kakao_y"])
                    time.sleep(0.4)
                    pyautogui.hotkey("ctrl","a")
                    time.sleep(0.2)
                    pyperclip.copy(search_key)
                    pyautogui.hotkey("ctrl","v")
                    time.sleep(settings["search_delay"])
                    pyautogui.press("enter")
                    time.sleep(0.8)
                    pyautogui.press("enter")
                    time.sleep(0.8)
                    pyperclip.copy(msg)
                    pyautogui.hotkey("ctrl","v")
                    time.sleep(0.3)
                    pyautogui.press("enter")

                    log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {idx+1}/{len(send_targets)} {contact.get('name','')} 완료"
                    history_record["results"].append({"name":contact.get("name",""),"status":"성공"})
                except Exception as e:
                    log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {contact.get('name','')} 실패: {e}"
                    history_record["results"].append({"name":contact.get("name",""),"status":f"실패:{e}"})

                st.session_state.logs.append(log_msg)
                log_area.markdown(
                    f"""<div class="log-terminal">{"<br>".join(st.session_state.logs[-15:])}</div>""",
                    unsafe_allow_html=True
                )
                progress_bar.progress((idx+1)/len(send_targets))
                status_text.info(f"발송 중... {idx+1}/{len(send_targets)} ({contact.get('name','')})")
                time.sleep(settings["delay"])

            # 저장
            history_record["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history = load_json(HISTORY_FILE, [])
            history.insert(0, history_record)
            save_json(HISTORY_FILE, history[:50])  # 최근 50건만

            st.session_state.sending = False
            success_n = sum(1 for r in history_record["results"] if r["status"]=="성공")
            status_text.success(f"🎉 완료! 성공 {success_n}/{len(send_targets)}건")


# ═══════════════════════════════════════════════════
# PAGE 4: 예약 발송
# ═══════════════════════════════════════════════════
elif page == "예약발송":
    st.markdown("""<div class="header-bar">
        <span style="font-size:1.8rem">📅</span>
        <div>
            <h2 style="margin:0;color:#1A1A1A">예약 발송</h2>
            <span style="color:#555;font-size:0.85rem">날짜/시간 설정 · 자동 발송</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="warn-banner">
        ⚠️ <strong>예약 발송 주의사항:</strong><br>
        • 예약 시간에 PC카톡과 앱이 반드시 로그인 상태여야 합니다<br>
        • PC 화면이 꺼지면 발송이 중단됩니다<br>
        • <strong>오후 8시 ~ 오전 8시</strong>는 야간 발송 제한 시간입니다
    </div>""", unsafe_allow_html=True)

    col_a, col_b = st.columns([1,1], gap="large")

    with col_a:
        st.markdown("### 📅 예약 설정")
        sched_date = st.date_input("발송 날짜", min_value=datetime.today())
        sched_time = st.time_input("발송 시간", value=datetime.now().replace(hour=9,minute=0,second=0).time())
        sched_dt = datetime.combine(sched_date, sched_time)

        # 야간 시간 경고
        if sched_time.hour >= 20 or sched_time.hour < 8:
            st.error("🌙 야간(오후8시~오전8시) 발송은 제한됩니다.")
        else:
            st.success(f"⏰ 예약 시간: {sched_dt.strftime('%Y년 %m월 %d일 %H시 %M분')}")

        contacts = load_json(CONTACTS_FILE, [])
        groups = load_json(GROUPS_FILE, ["기본"])
        sched_groups = st.multiselect("발송 그룹", groups, default=groups)
        sched_targets = [c for c in contacts if c.get("group","기본") in sched_groups]
        st.info(f"발송 대상: **{len(sched_targets)}명**")

        template_data = load_json(DATA_DIR / "template.json", {"text":"{{호칭}}님, 안녕하세요!"})

        if st.button("📅 예약 등록"):
            if sched_time.hour >= 20 or sched_time.hour < 8:
                st.error("야간 시간 예약 불가")
            elif len(sched_targets) == 0:
                st.error("발송 대상이 없습니다.")
            else:
                schedule = load_json(SCHEDULE_FILE, [])
                schedule.append({
                    "id": str(uuid.uuid4())[:8],
                    "scheduled_at": sched_dt.strftime("%Y-%m-%d %H:%M"),
                    "groups": sched_groups,
                    "target_count": len(sched_targets),
                    "template": template_data.get("text",""),
                    "status": "대기",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_json(SCHEDULE_FILE, schedule)
                st.success(f"✅ 예약 완료! {sched_dt.strftime('%m/%d %H:%M')} 에 {len(sched_targets)}명에게 발송됩니다.")

    with col_b:
        st.markdown("### 📋 예약 내역")
        schedule = load_json(SCHEDULE_FILE, [])
        if schedule:
            for s in schedule:
                status_color = {"대기":"#FFF3E0","완료":"#E8F5E9","취소":"#FFEBEE"}.get(s["status"],"#fff")
                col1, col2 = st.columns([4,1])
                with col1:
                    st.markdown(f"""<div style="background:{status_color};padding:0.7rem;
                                border-radius:8px;margin:0.3rem 0">
                        <strong>{s['scheduled_at']}</strong> — {s['target_count']}명
                        <span class="badge" style="margin-left:0.5rem">{s['status']}</span><br>
                        <small style="color:#666">그룹: {', '.join(s['groups'])}</small>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    if s["status"] == "대기":
                        if st.button("취소", key=f"sched_cancel_{s['id']}"):
                            s["status"] = "취소"
                            save_json(SCHEDULE_FILE, schedule)
                            st.rerun()
        else:
            st.info("예약된 발송이 없습니다.")


# ═══════════════════════════════════════════════════
# PAGE 5: 발송 내역
# ═══════════════════════════════════════════════════
elif page == "발송내역":
    st.markdown("""<div class="header-bar">
        <span style="font-size:1.8rem">📊</span>
        <div>
            <h2 style="margin:0;color:#1A1A1A">발송 내역</h2>
            <span style="color:#555;font-size:0.85rem">발송 이력 · 성공/실패 확인</span>
        </div>
    </div>""", unsafe_allow_html=True)

    history = load_json(HISTORY_FILE, [])

    if history:
        # 요약 통계
        total_sent = sum(len(h.get("results",[])) for h in history)
        total_success = sum(sum(1 for r in h.get("results",[]) if r.get("status")=="성공") for h in history)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:2rem;font-weight:700;color:#1A237E">{len(history)}</div>
                <div style="color:#666">총 발송 회차</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:2rem;font-weight:700;color:#388E3C">{total_success}</div>
                <div style="color:#666">성공 건수</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            fail = total_sent - total_success
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:2rem;font-weight:700;color:#D32F2F">{fail}</div>
                <div style="color:#666">실패 건수</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        for h in history:
            results = h.get("results",[])
            s_cnt = sum(1 for r in results if r.get("status")=="성공")
            f_cnt = len(results) - s_cnt
            with st.expander(f"📤 {h.get('started_at','')} — {len(results)}명 (성공:{s_cnt} / 실패:{f_cnt})"):
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        "📥 CSV 다운로드", data=csv,
                        file_name=f"발송결과_{h.get('started_at','').replace(':','-').replace(' ','_')}.csv",
                        mime="text/csv", key=f"dl_{h.get('id','')}"
                    )
    else:
        st.info("발송 내역이 없습니다.")


# ═══════════════════════════════════════════════════
# PAGE 6: 설정
# ═══════════════════════════════════════════════════
elif page == "설정":
    st.markdown("""<div class="header-bar">
        <span style="font-size:1.8rem">⚙️</span>
        <div>
            <h2 style="margin:0;color:#1A1A1A">설정</h2>
            <span style="color:#555;font-size:0.85rem">PC카톡 연결 · 발송 속도 · 좌표 설정</span>
        </div>
    </div>""", unsafe_allow_html=True)

    settings = load_json(SETTINGS_FILE, {
        "delay": 3, "search_delay": 2,
        "kakao_x": 960, "kakao_y": 60,
        "search_by": "이름"
    })

    try:
        import pyautogui
        import pyperclip
        st.markdown("""<div class="success-banner">
            ✅ pyautogui / pyperclip 설치 확인됨
        </div>""", unsafe_allow_html=True)
    except:
        st.error("❌ pyautogui/pyperclip 미설치: `pip install pyautogui pyperclip` 실행 필요")

    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        st.markdown("### 🖱️ PC 카카오톡 좌표 설정")
        st.markdown("""<div class="warn-banner">
            카카오톡 <strong>상단 검색창</strong> 위에 마우스를 올려놓고
            아래 버튼을 눌러 좌표를 확인하세요.
        </div>""", unsafe_allow_html=True)

        kakao_x = st.number_input("검색창 X 좌표", value=settings.get("kakao_x",960), step=10)
        kakao_y = st.number_input("검색창 Y 좌표", value=settings.get("kakao_y",60),  step=10)

        if st.button("🎯 현재 마우스 위치 확인 (3초 후)"):
            try:
                import pyautogui
                st.info("3초 후 마우스 위치를 측정합니다...")
                time.sleep(3)
                pos = pyautogui.position()
                st.success(f"현재 위치: X={pos.x}, Y={pos.y}")
                st.info("위 값을 검색창 좌표에 입력하세요.")
            except:
                st.error("pyautogui 미설치")

        st.markdown("### 🔍 검색 방식")
        search_by = st.radio("카카오톡 검색 기준", ["카톡대화명","이름"],
                             index=0 if settings.get("search_by")=="카톡대화명" else 1)

    with col_r:
        st.markdown("### ⏱️ 발송 속도 설정")
        delay = st.slider("메시지 간 대기 시간 (초)", 2, 10, settings.get("delay",3),
                          help="빠를수록 계정 정지 위험. 최소 3초 권장")
        search_delay = st.slider("검색 후 대기 시간 (초)", 1, 5, settings.get("search_delay",2))

        st.markdown(f"""<div class="warn-banner">
            현재 설정으로 100명 발송 시: <strong>약 {delay*100//60}분 {delay*100%60}초</strong> 소요
        </div>""", unsafe_allow_html=True)

        st.markdown("### 🚨 긴급 중지")
        st.info("마우스를 **화면 왼쪽 상단 구석**으로 빠르게 이동하면 즉시 중단됩니다 (pyautogui FAILSAFE)")

        st.markdown("### 📦 설치 명령어")
        st.code("pip install streamlit pandas openpyxl pyautogui pyperclip", language="bash")

    if st.button("💾 설정 저장", type="primary"):
        save_json(SETTINGS_FILE, {
            "delay": delay,
            "search_delay": search_delay,
            "kakao_x": kakao_x,
            "kakao_y": kakao_y,
            "search_by": search_by
        })
        st.success("✅ 설정 저장 완료!")
