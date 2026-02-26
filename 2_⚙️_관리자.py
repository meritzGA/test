"""
⚙️ 관리자 페이지
- 데이터 업로드/삭제/병합 (조인 키 선택 포함)
- 시상 JSON 업로드
- 매니저 로그인/활동 모니터링
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

from utils.database import (
    init_db, save_uploaded_file, delete_uploaded_file, get_uploaded_files,
    get_raw_data, get_raw_columns, merge_data, get_merged_data, get_merged_columns,
    delete_merged_data, get_all_message_summary, get_login_summary,
    get_login_logs, save_prize_json, get_prize_json, delete_prize_json,
    cleanup_old_month_logs
)

st.set_page_config(page_title="관리자 페이지", page_icon="⚙️", layout="wide")
init_db()

# ──────────────────────────────────────────
# 관리자 인증
# ──────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    try:
        ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin1!")
    except Exception:
        ADMIN_PASSWORD = "admin1!"

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("⚙️ 관리자 로그인")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            admin_pw = st.text_input("관리자 비밀번호", type="password")
            if st.button("로그인", use_container_width=True, type="primary"):
                if admin_pw == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# ──────────────────────────────────────────
# 관리자 메인
# ──────────────────────────────────────────
st.title("⚙️ 관리자 페이지")

tab_data, tab_monitor = st.tabs(["📂 데이터 관리", "📊 활동 모니터링"])

# ══════════════════════════════════════════
# TAB 1: 데이터 관리
# ══════════════════════════════════════════
with tab_data:
    st.subheader("📂 파일 업로드 및 데이터 병합")

    # 현재 업로드 상태
    uploaded_files = get_uploaded_files()
    file_a_exists = any(f["file_type"] == "FILE_A" for f in uploaded_files)
    file_b_exists = any(f["file_type"] == "FILE_B" for f in uploaded_files)

    # ── 파일 업로드 영역 ──
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 📄 파일 A 업로드")
        if file_a_exists:
            fa = next(f for f in uploaded_files if f["file_type"] == "FILE_A")
            st.success(f"✅ {fa['file_name']} ({fa['row_count']:,}행 × {fa['col_count']}열)")
            if st.button("🗑️ 파일 A 삭제", key="del_a"):
                delete_uploaded_file("FILE_A")
                delete_merged_data()
                st.rerun()
        else:
            file_a = st.file_uploader("파일 A (xlsx/csv)", type=["xlsx", "csv"], key="upload_a")
            if file_a:
                with st.spinner("파일 읽는 중..."):
                    if file_a.name.endswith(".csv"):
                        df_a = pd.read_csv(file_a)
                    else:
                        df_a = pd.read_excel(file_a)
                    save_uploaded_file(df_a, file_a.name, "FILE_A")
                    st.success(f"✅ {file_a.name} 업로드 완료! ({len(df_a):,}행)")
                    st.rerun()

    with col_b:
        st.markdown("#### 📄 파일 B 업로드")
        if file_b_exists:
            fb = next(f for f in uploaded_files if f["file_type"] == "FILE_B")
            st.success(f"✅ {fb['file_name']} ({fb['row_count']:,}행 × {fb['col_count']}열)")
            if st.button("🗑️ 파일 B 삭제", key="del_b"):
                delete_uploaded_file("FILE_B")
                delete_merged_data()
                st.rerun()
        else:
            file_b = st.file_uploader("파일 B (xlsx/csv)", type=["xlsx", "csv"], key="upload_b")
            if file_b:
                with st.spinner("파일 읽는 중..."):
                    if file_b.name.endswith(".csv"):
                        df_b = pd.read_csv(file_b)
                    else:
                        df_b = pd.read_excel(file_b)
                    save_uploaded_file(df_b, file_b.name, "FILE_B")
                    st.success(f"✅ {file_b.name} 업로드 완료! ({len(df_b):,}행)")
                    st.rerun()

    st.markdown("---")

    # ── 조인 키 선택 및 병합 ──
    if file_a_exists and file_b_exists:
        st.subheader("🔗 데이터 병합 설정")

        cols_a = get_raw_columns("FILE_A")
        cols_b = get_raw_columns("FILE_B")

        col_sel_a, col_sel_b = st.columns(2)
        with col_sel_a:
            st.markdown("**파일 A 조인 키 컬럼**")
            # 기본값: 본인고객번호가 있으면 선택
            default_a = cols_a.index("본인고객번호") if "본인고객번호" in cols_a else 0
            join_col_a = st.selectbox("파일 A 조인 키", cols_a, index=default_a, key="join_a")

            # 미리보기
            df_a_preview = get_raw_data("FILE_A")
            if not df_a_preview.empty:
                st.caption(f"샘플 값: {', '.join(str(v) for v in df_a_preview[join_col_a].head(3).tolist())}")

        with col_sel_b:
            st.markdown("**파일 B 조인 키 컬럼**")
            default_b = cols_b.index("본인고객번호") if "본인고객번호" in cols_b else 0
            join_col_b = st.selectbox("파일 B 조인 키", cols_b, index=default_b, key="join_b")

            df_b_preview = get_raw_data("FILE_B")
            if not df_b_preview.empty:
                st.caption(f"샘플 값: {', '.join(str(v) for v in df_b_preview[join_col_b].head(3).tolist())}")

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("🔗 데이터 병합 (Outer Join)", use_container_width=True, type="primary"):
                with st.spinner("데이터 병합 중..."):
                    merged = merge_data("FILE_A", "FILE_B", join_col_a, join_col_b)
                    if not merged.empty:
                        st.success(f"✅ 병합 완료! {len(merged):,}행 × {len(merged.columns)}열")
                        st.rerun()
                    else:
                        st.error("병합 결과가 비어있습니다. 조인 키를 확인하세요.")

        with col_btn2:
            if st.button("🗑️ 병합 데이터 삭제", use_container_width=True):
                delete_merged_data()
                st.info("병합 데이터가 삭제되었습니다.")
                st.rerun()

    elif file_a_exists or file_b_exists:
        st.info("💡 두 파일을 모두 업로드하면 병합할 수 있습니다. 한 파일만 있어도 단독으로 사용 가능합니다.")

        # 단일 파일 병합 (사실상 복사)
        if file_a_exists and st.button("📄 파일 A만 사용"):
            df = get_raw_data("FILE_A")
            import sqlite3
            from utils.database import get_connection
            conn = get_connection()
            df.to_sql("merged_data", conn, if_exists="replace", index=False)
            conn.commit()
            conn.close()
            st.success("파일 A 데이터를 병합 데이터로 설정했습니다.")
            st.rerun()

        if file_b_exists and st.button("📄 파일 B만 사용"):
            df = get_raw_data("FILE_B")
            from utils.database import get_connection
            conn = get_connection()
            df.to_sql("merged_data", conn, if_exists="replace", index=False)
            conn.commit()
            conn.close()
            st.success("파일 B 데이터를 병합 데이터로 설정했습니다.")
            st.rerun()

    # ── 병합 데이터 미리보기 ──
    merged_df = get_merged_data()
    if not merged_df.empty:
        st.markdown("---")
        st.subheader(f"📋 병합 데이터 미리보기 ({len(merged_df):,}행)")

        # 매니저코드 컬럼 기준 요약
        mgr_cols = [c for c in merged_df.columns if "매니저코드" in c or "지원매니저코드" in c]
        if mgr_cols:
            for mc in mgr_cols:
                unique_count = merged_df[mc].dropna().nunique()
                st.caption(f"  `{mc}` 고유값: {unique_count}개")

        st.dataframe(merged_df.head(50), use_container_width=True, height=300)

    # ── 시상 JSON 업로드 ──
    st.markdown("---")
    st.subheader("🏆 시상 JSON 업로드")

    existing_json = get_prize_json()
    if existing_json:
        if isinstance(existing_json, list):
            st.success(f"✅ 시상 JSON 로드됨 ({len(existing_json)}건)")
        else:
            st.success(f"✅ 시상 JSON 로드됨 ({len(existing_json)}키)")
        if st.button("🗑️ 시상 JSON 삭제"):
            delete_prize_json()
            st.rerun()

    json_file = st.file_uploader("시상 JSON 파일", type=["json"], key="upload_json")
    if json_file:
        try:
            json_data = json.load(json_file)
            save_prize_json(json_data)
            st.success("시상 JSON 업로드 완료!")
            st.rerun()
        except json.JSONDecodeError:
            st.error("유효한 JSON 파일이 아닙니다.")


# ══════════════════════════════════════════
# TAB 2: 활동 모니터링
# ══════════════════════════════════════════
with tab_monitor:
    st.subheader("📊 매니저 활동 모니터링")
    st.caption(f"기준월: {datetime.now().strftime('%Y년 %m월')} (매월 1일 초기화)")

    # 이전 달 로그 정리
    cleanup_old_month_logs()

    # ── 로그인 현황 ──
    st.markdown("### 🔑 로그인 현황")
    login_summary = get_login_summary()
    if not login_summary.empty:
        st.metric("당월 로그인 매니저", f"{len(login_summary)}명")
        st.dataframe(login_summary, use_container_width=True, hide_index=True)
    else:
        st.info("당월 로그인 기록이 없습니다.")

    st.markdown("---")

    # ── 메시지 발송 현황 ──
    st.markdown("### 📤 메시지 발송 현황")
    msg_summary = get_all_message_summary()

    if not msg_summary.empty:
        # 전체 요약
        msg_labels = {1: "① 인사말", 2: "② 리플렛", 3: "③ 시상안내", 4: "④ 시상+실적"}

        # 유형별 총계
        st.markdown("#### 유형별 총계")
        type_summary = msg_summary.groupby("메시지유형").agg(
            총발송인원=("발송인원", "sum"),
            총발송횟수=("발송횟수", "sum"),
            매니저수=("매니저코드", "nunique")
        ).reset_index()
        type_summary["메시지유형"] = type_summary["메시지유형"].map(lambda x: msg_labels.get(x, str(x)))

        scols = st.columns(4)
        for i, (_, row) in enumerate(type_summary.iterrows()):
            if i < 4:
                with scols[i]:
                    st.metric(
                        label=row["메시지유형"],
                        value=f"{int(row['총발송인원'])}명",
                        delta=f"{int(row['총발송횟수'])}회 / {int(row['매니저수'])}매니저"
                    )

        st.markdown("---")

        # ── 매니저별 상세 (피벗) ──
        st.markdown("#### 매니저별 상세")

        # 피벗 테이블: 매니저 × 메시지유형
        msg_summary_display = msg_summary.copy()
        msg_summary_display["메시지유형_라벨"] = msg_summary_display["메시지유형"].map(
            lambda x: msg_labels.get(x, str(x))
        )

        # 발송인원 피벗
        pivot_customers = msg_summary_display.pivot_table(
            index=["매니저코드", "매니저명"],
            columns="메시지유형_라벨",
            values="발송인원",
            fill_value=0,
            aggfunc="sum"
        ).reset_index()
        pivot_customers.columns.name = None

        st.markdown("**발송 인원 (명)**")
        st.dataframe(pivot_customers, use_container_width=True, hide_index=True)

        # 발송횟수 피벗
        pivot_counts = msg_summary_display.pivot_table(
            index=["매니저코드", "매니저명"],
            columns="메시지유형_라벨",
            values="발송횟수",
            fill_value=0,
            aggfunc="sum"
        ).reset_index()
        pivot_counts.columns.name = None

        st.markdown("**발송 횟수 (회)**")
        st.dataframe(pivot_counts, use_container_width=True, hide_index=True)

        # CSV 다운로드
        st.download_button(
            "📥 발송 현황 CSV 다운로드",
            data=msg_summary.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"message_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("당월 메시지 발송 기록이 없습니다.")

    st.markdown("---")

    # ── 최근 로그인 이력 ──
    st.markdown("### 📝 최근 로그인 이력")
    login_logs = get_login_logs()
    if not login_logs.empty:
        st.dataframe(login_logs.head(100), use_container_width=True, hide_index=True)
    else:
        st.info("로그인 이력이 없습니다.")
