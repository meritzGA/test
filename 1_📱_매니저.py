"""
📱 매니저 페이지
- 매니저코드 + 비밀번호 로그인
- 매칭된 사용인 리스트
- 4가지 메시지 옵션으로 카카오톡 공유
- 당월 발송 이력 확인 (매월 1일 초기화)
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

from utils.database import (
    init_db, get_merged_data, get_merged_columns,
    get_users_by_manager, log_message, get_message_logs_for_customer,
    log_login, get_message_summary_for_manager, cleanup_old_month_logs,
    get_prize_json
)
from utils.kakao_share import (
    render_kakao_share_button,
    build_greeting_message, build_prize_message, build_performance_message
)

st.set_page_config(page_title="매니저 페이지", page_icon="📱", layout="wide")
init_db()

# 매월 초기화 체크
cleanup_old_month_logs()

# ──────────────────────────────────────────
# 환경변수 / secrets
# ──────────────────────────────────────────
MANAGER_PASSWORD = os.environ.get("MANAGER_PASSWORD", "")
if not MANAGER_PASSWORD:
    try:
        MANAGER_PASSWORD = st.secrets.get("MANAGER_PASSWORD", "meritz1!")
    except Exception:
        MANAGER_PASSWORD = "meritz1!"

KAKAO_JS_KEY = os.environ.get("KAKAO_JS_KEY", "")
if not KAKAO_JS_KEY:
    try:
        KAKAO_JS_KEY = st.secrets.get("KAKAO_JS_KEY", "")
    except Exception:
        KAKAO_JS_KEY = ""

# ──────────────────────────────────────────
# 매니저코드 컬럼 설정 (관리자가 설정하면 여기서 읽어옴)
# ──────────────────────────────────────────
def get_manager_code_columns():
    """merged_data에서 매니저코드로 쓸 수 있는 컬럼 반환"""
    cols = get_merged_columns()
    # 기본 매니저 컬럼 후보
    candidates = ["매니저코드", "지원매니저코드", "매니저코드_A", "매니저코드_B",
                   "지원매니저코드_A", "지원매니저코드_B"]
    found = [c for c in candidates if c in cols]
    if not found:
        # '매니저' 또는 'manager'가 포함된 컬럼 검색
        found = [c for c in cols if "매니저코드" in c or "매니저" in c.lower()]
    return found if found else cols[:2]  # 못찾으면 앞 2개


def get_customer_display_columns():
    """사용인 표시에 사용할 컬럼"""
    cols = get_merged_columns()
    # 표시할 기본 컬럼
    display_candidates = [
        "본인고객번호", "본인고객ID",
        "매니저코드", "매니저명", "지원매니저코드", "지원매니저명",
        "현재대리점설계사조직명", "대리점설계사명", "조직상태",
        "인보험실적", "목표금액", "인정실적", "부족금액", "구간",
        "독려구분", "현재월연속가동",
        "실적_1주차", "실적_2주차", "실적_3주차", "실적_4주차", "실적_5주차",
        "시상금계", "추가예정금계", "시상금계and추가예정금계"
    ]
    # 접미사 포함 검색
    found = []
    for c in cols:
        base = c.replace("_A", "").replace("_B", "")
        if base in display_candidates or c in display_candidates:
            found.append(c)
    return found if found else cols[:15]


# ──────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "manager_code" not in st.session_state:
    st.session_state.manager_code = ""
if "manager_name" not in st.session_state:
    st.session_state.manager_name = ""
if "selected_customer" not in st.session_state:
    st.session_state.selected_customer = None
if "custom_greeting" not in st.session_state:
    st.session_state.custom_greeting = ""


# ──────────────────────────────────────────
# 로그인 화면
# ──────────────────────────────────────────
def show_login():
    st.title("📱 매니저 로그인")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔑 로그인")
            manager_code = st.text_input("매니저코드", placeholder="매니저코드를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")

            if st.button("로그인", use_container_width=True, type="primary"):
                if not manager_code:
                    st.error("매니저코드를 입력하세요.")
                    return
                if password != MANAGER_PASSWORD:
                    st.error("비밀번호가 올바르지 않습니다.")
                    return

                # 매니저코드가 데이터에 존재하는지 확인
                mgr_cols = get_manager_code_columns()
                users = get_users_by_manager(manager_code, mgr_cols)

                if users.empty:
                    st.error("해당 매니저코드로 매칭된 사용인이 없습니다. 매니저코드를 확인해주세요.")
                    return

                # 매니저명 추출
                manager_name = ""
                for col in ["매니저명", "매니저명_A", "지원매니저명", "지원매니저명_B"]:
                    if col in users.columns:
                        names = users[col].dropna().unique()
                        if len(names) > 0:
                            manager_name = str(names[0])
                            break

                st.session_state.logged_in = True
                st.session_state.manager_code = manager_code
                st.session_state.manager_name = manager_name

                # 로그인 로그 기록
                log_login(manager_code, manager_name)

                st.rerun()


# ──────────────────────────────────────────
# 메인 화면 (로그인 후)
# ──────────────────────────────────────────
def show_main():
    # 헤더
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title(f"📱 {st.session_state.manager_name} 매니저님")
        st.caption(f"매니저코드: {st.session_state.manager_code} | 기준월: {datetime.now().strftime('%Y년 %m월')}")
    with col_h2:
        if st.button("🚪 로그아웃", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.manager_code = ""
            st.session_state.selected_customer = None
            st.rerun()

    st.markdown("---")

    # 사용인 목록 로드
    mgr_cols = get_manager_code_columns()
    users_df = get_users_by_manager(st.session_state.manager_code, mgr_cols)

    if users_df.empty:
        st.warning("매칭된 사용인이 없습니다.")
        return

    # 발송 요약
    summary = get_message_summary_for_manager(st.session_state.manager_code)
    msg_labels = {1: "인사말", 2: "리플렛", 3: "시상안내", 4: "시상+실적"}

    st.subheader("📊 당월 발송 현황")
    scols = st.columns(4)
    for i, (msg_type, label) in enumerate(msg_labels.items()):
        with scols[i]:
            info = summary.get(msg_type, {"customers": 0, "count": 0})
            st.metric(
                label=f"({msg_type}) {label}",
                value=f"{info['customers']}명",
                delta=f"{info['count']}회 발송"
            )

    st.markdown("---")

    # ── 사용인 리스트와 상세보기 ──
    col_list, col_detail = st.columns([2, 3])

    with col_list:
        st.subheader(f"👥 사용인 목록 ({len(users_df)}명)")

        # 검색
        search = st.text_input("🔍 검색", placeholder="이름/코드/조직 검색...")

        # 고객번호/이름 컬럼 찾기
        cust_num_col = None
        cust_name_col = None
        org_name_col = None

        for c in users_df.columns:
            if "본인고객번호" in c and cust_num_col is None:
                cust_num_col = c
            if "대리점설계사" in c and "명" in c and cust_name_col is None:
                cust_name_col = c
            if "대리점설계사조직명" in c and org_name_col is None:
                org_name_col = c

        if cust_num_col is None:
            cust_num_col = users_df.columns[0]
        if cust_name_col is None:
            # 설계사명 또는 고객ID
            for c in users_df.columns:
                if "설계사명" in c or "고객" in c:
                    cust_name_col = c
                    break
            if cust_name_col is None:
                cust_name_col = users_df.columns[1] if len(users_df.columns) > 1 else users_df.columns[0]

        # 검색 필터
        display_df = users_df.copy()
        if search:
            mask = display_df.apply(lambda row: search.lower() in str(row.values).lower(), axis=1)
            display_df = display_df[mask]

        # 사용인 리스트 표시
        for idx, row in display_df.iterrows():
            cust_num = str(row.get(cust_num_col, ""))
            cust_name = str(row.get(cust_name_col, ""))
            org_name = str(row.get(org_name_col, "")) if org_name_col else ""

            # 당월 발송 이력 체크
            logs = get_message_logs_for_customer(st.session_state.manager_code, cust_num)
            sent_types = set(l["message_type"] for l in logs)
            badges = " ".join([f"{'✅' if t in sent_types else '⬜'}" for t in [1, 2, 3, 4]])

            label = f"**{cust_name}** ({org_name})\n{badges}"

            if st.button(
                f"{cust_name} | {org_name} | {badges}",
                key=f"user_{idx}",
                use_container_width=True
            ):
                st.session_state.selected_customer = {
                    "index": idx,
                    "number": cust_num,
                    "name": cust_name,
                    "org": org_name,
                    "row": row.to_dict()
                }
                st.rerun()

    with col_detail:
        if st.session_state.selected_customer:
            show_customer_detail(st.session_state.selected_customer)
        else:
            st.info("👈 왼쪽 목록에서 사용인을 선택하세요.")


def show_customer_detail(customer: dict):
    """선택된 사용인 상세 + 메시지 발송"""
    cust_name = customer["name"]
    cust_num = customer["number"]
    cust_row = customer["row"]
    manager_name = st.session_state.manager_name
    manager_code = st.session_state.manager_code

    st.subheader(f"📋 {cust_name}")
    st.caption(f"고객번호: {cust_num} | 소속: {customer['org']}")

    # 당월 발송 이력
    logs = get_message_logs_for_customer(manager_code, cust_num)
    sent_types = set(l["message_type"] for l in logs)

    msg_labels = {1: "인사말", 2: "리플렛", 3: "시상안내", 4: "시상+실적"}
    status_cols = st.columns(4)
    for i, (mt, label) in enumerate(msg_labels.items()):
        with status_cols[i]:
            if mt in sent_types:
                st.success(f"✅ ({mt}){label}")
            else:
                st.warning(f"⬜ ({mt}){label}")

    st.markdown("---")

    # 주요 실적 정보 표시
    perf_keys = ["인보험실적", "목표금액", "인정실적", "부족금액", "구간", "독려구분",
                 "현재월연속가동", "실적_1주차", "실적_2주차", "실적_3주차", "실적_4주차", "실적_5주차"]

    with st.expander("📈 실적 상세", expanded=False):
        perf_data = {}
        for key in cust_row:
            base = key.replace("_A", "").replace("_B", "")
            if base in perf_keys or key in perf_keys:
                val = cust_row[key]
                if val is not None and str(val) != "nan":
                    perf_data[key] = val
        if perf_data:
            perf_df = pd.DataFrame([perf_data])
            st.dataframe(perf_df, use_container_width=True)
        else:
            st.caption("실적 데이터 없음")

    # 시상 정보
    prize_keys = ["시상금계", "추가예정금계", "시상금계and추가예정금계", "한화시책",
                  "지급예정금1", "총지급예정금", "시상금총액_메클_메리츠plus"]
    prize_from_row = {}
    for key in cust_row:
        base = key.replace("_A", "").replace("_B", "")
        if base in prize_keys or key in prize_keys:
            val = cust_row[key]
            if val is not None and str(val) != "nan":
                prize_from_row[key] = val

    # 외부 JSON 시상 데이터
    prize_json = get_prize_json()
    prize_for_customer = {}
    if prize_json:
        # JSON에서 해당 고객 찾기
        if isinstance(prize_json, list):
            for item in prize_json:
                if str(item.get("본인고객번호", "")) == str(cust_num) or \
                   str(item.get("customer_number", "")) == str(cust_num):
                    prize_for_customer = item
                    break
        elif isinstance(prize_json, dict):
            prize_for_customer = prize_json.get(str(cust_num), {})

    st.markdown("---")
    st.subheader("📤 메시지 발송")

    tab1, tab2, tab3, tab4 = st.tabs([
        "① 인사말 보내기", "② 리플렛 보내기", "③ 시상 안내하기", "④ 시상+실적 안내하기"
    ])

    # ── (1) 인사말 보내기 ──
    with tab1:
        greeting_text = st.text_area(
            "인사말 입력",
            value=st.session_state.custom_greeting,
            placeholder="안녕하세요! 이번 달도 화이팅입니다!",
            key=f"greeting_{cust_num}"
        )
        if greeting_text:
            st.session_state.custom_greeting = greeting_text
            msg = build_greeting_message(manager_name, cust_name, greeting_text)
            st.text_area("미리보기", msg, height=120, disabled=True, key=f"preview1_{cust_num}")
            render_kakao_share_button(msg, "카카오톡으로 인사말 보내기", KAKAO_JS_KEY,
                                       button_id=f"kakao1_{cust_num}")
            if st.button("✅ 발송 완료 기록", key=f"log1_{cust_num}", type="primary"):
                log_message(manager_code, manager_name, cust_num, cust_name, 1)
                st.success("인사말 발송이 기록되었습니다!")
                st.rerun()

    # ── (2) 리플렛 보내기 ──
    with tab2:
        leaflet_file = st.file_uploader("리플렛 파일 첨부", type=["png", "jpg", "jpeg", "pdf"],
                                         key=f"leaflet_{cust_num}")
        if leaflet_file:
            st.success(f"📎 {leaflet_file.name} 첨부됨")
            msg = f"📎 {manager_name} 매니저가 {cust_name}님께 리플렛을 보냈습니다.\n\n첨부파일: {leaflet_file.name}"
            st.text_area("미리보기", msg, height=100, disabled=True, key=f"preview2_{cust_num}")
            st.info("💡 카카오톡 공유 후, 리플렛 파일을 직접 전송해주세요.")
            render_kakao_share_button(msg, "카카오톡으로 리플렛 안내 보내기", KAKAO_JS_KEY,
                                       button_id=f"kakao2_{cust_num}")
            if st.button("✅ 발송 완료 기록", key=f"log2_{cust_num}", type="primary"):
                log_message(manager_code, manager_name, cust_num, cust_name, 2)
                st.success("리플렛 발송이 기록되었습니다!")
                st.rerun()

    # ── (3) 시상 안내하기 ──
    with tab3:
        combined_prize = {**prize_from_row, **prize_for_customer}
        if combined_prize:
            # 표시용 정리
            display_prize = {k: v for k, v in combined_prize.items()
                            if k not in ["본인고객번호", "customer_number", "본인고객ID"]}
            st.dataframe(pd.DataFrame([display_prize]), use_container_width=True)
            msg = build_prize_message(cust_name, display_prize)
            st.text_area("미리보기", msg, height=200, disabled=True, key=f"preview3_{cust_num}")
            render_kakao_share_button(msg, "카카오톡으로 시상 안내 보내기", KAKAO_JS_KEY,
                                       button_id=f"kakao3_{cust_num}")
            if st.button("✅ 발송 완료 기록", key=f"log3_{cust_num}", type="primary"):
                log_message(manager_code, manager_name, cust_num, cust_name, 3)
                st.success("시상 안내 발송이 기록되었습니다!")
                st.rerun()
        else:
            st.warning("시상 데이터가 없습니다. 관리자에게 시상 JSON 업로드를 요청하세요.")

    # ── (4) 시상+실적 안내하기 ──
    with tab4:
        combined_prize = {**prize_from_row, **prize_for_customer}
        display_prize = {k: v for k, v in combined_prize.items()
                        if k not in ["본인고객번호", "customer_number", "본인고객ID"]}
        if perf_data or display_prize:
            if perf_data:
                st.markdown("**📈 실적**")
                st.dataframe(pd.DataFrame([perf_data]), use_container_width=True)
            if display_prize:
                st.markdown("**🏆 시상**")
                st.dataframe(pd.DataFrame([display_prize]), use_container_width=True)

            msg = build_performance_message(cust_name, perf_data, display_prize)
            st.text_area("미리보기", msg, height=250, disabled=True, key=f"preview4_{cust_num}")
            render_kakao_share_button(msg, "카카오톡으로 시상+실적 안내 보내기", KAKAO_JS_KEY,
                                       button_id=f"kakao4_{cust_num}")
            if st.button("✅ 발송 완료 기록", key=f"log4_{cust_num}", type="primary"):
                log_message(manager_code, manager_name, cust_num, cust_name, 4)
                st.success("시상+실적 안내 발송이 기록되었습니다!")
                st.rerun()
        else:
            st.warning("실적 및 시상 데이터가 없습니다.")


# ──────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────
if st.session_state.logged_in:
    show_main()
else:
    show_login()
