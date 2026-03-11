import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="연락처 매니저", page_icon="📇", layout="wide")

# ── CSS ──
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    [data-testid="stSidebar"] { background-color: #181b23; }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stDataEditor"] { border: 1px solid #2a2f3d; border-radius: 8px; }
    .stat-card {
        background: #181b23; border: 1px solid #2a2f3d; border-radius: 10px;
        padding: 14px 18px; text-align: center;
    }
    .stat-num { font-size: 28px; font-weight: 700; margin: 0; }
    .stat-label { font-size: 12px; color: #838899; margin: 0; }
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ──
if "df" not in st.session_state:
    st.session_state.df = None
    st.session_state.df_original = None
    st.session_state.filename = ""

# ── 사이드바: 파일 업로드 & 필터 ──
with st.sidebar:
    st.markdown("## 📇 연락처 매니저")
    st.markdown("---")
    
    uploaded = st.file_uploader(
        "파일 업로드", type=["csv", "xlsx", "xls", "tsv", "txt"],
        help="CSV, Excel, TSV 파일 지원"
    )
    
    if uploaded:
        try:
            ext = uploaded.name.split(".")[-1].lower()
            if ext in ("xlsx", "xls"):
                df = pd.read_excel(uploaded, dtype=str).fillna("")
            elif ext == "tsv":
                df = pd.read_csv(uploaded, sep="\t", dtype=str).fillna("")
            else:
                # CSV: try utf-8, fallback cp949
                try:
                    df = pd.read_csv(uploaded, dtype=str, encoding="utf-8").fillna("")
                except UnicodeDecodeError:
                    uploaded.seek(0)
                    df = pd.read_csv(uploaded, dtype=str, encoding="cp949").fillna("")
            
            st.session_state.df = df.copy()
            st.session_state.df_original = df.copy()
            st.session_state.filename = uploaded.name
        except Exception as e:
            st.error(f"파일 읽기 실패: {e}")
    
    if st.session_state.df is not None:
        df = st.session_state.df
        fields = list(df.columns)
        
        st.markdown("---")
        st.markdown("### 🔍 필터")
        
        # 필터 개수
        if "filter_count" not in st.session_state:
            st.session_state.filter_count = 0
        
        col_add, col_reset = st.columns(2)
        with col_add:
            if st.button("➕ 조건 추가", use_container_width=True):
                st.session_state.filter_count += 1
        with col_reset:
            if st.button("🔄 초기화", use_container_width=True):
                st.session_state.filter_count = 0
        
        filters = []
        for i in range(st.session_state.filter_count):
            with st.container():
                st.markdown(f"**조건 {i+1}**")
                c1, c2 = st.columns(2)
                with c1:
                    fld = st.selectbox("필드", [""] + fields, key=f"ff_{i}")
                with c2:
                    op = st.selectbox("연산", [
                        "포함", "일치", "시작", "끝남", "미포함",
                        "비어있음", "비어있지 않음", ">", "<", "≥", "≤"
                    ], key=f"fo_{i}")
                
                val = ""
                if op not in ("비어있음", "비어있지 않음"):
                    val = st.text_input("값", key=f"fv_{i}")
                
                if fld:
                    filters.append({"field": fld, "op": op, "value": val})
        
        st.markdown("---")
        st.markdown("### 📊 정렬")
        sort_field = st.selectbox("정렬 기준", ["없음"] + fields)
        sort_dir = st.radio("방향", ["오름차순", "내림차순"], horizontal=True)
        
        st.markdown("---")
        st.markdown("### ✏️ 일괄 수정")
        st.caption("아래에서 조건 필터링 후 해당 행들을 일괄 수정합니다.")
        bulk_field = st.selectbox("수정할 필드", [""] + fields, key="bulk_f")
        bulk_value = st.text_input("변경할 값", key="bulk_v")
        if st.button("🔄 일괄 적용", use_container_width=True, type="primary"):
            if bulk_field:
                mask = pd.Series([True] * len(df))
                for f in filters:
                    mask = mask & _apply_filter(df, f)
                count = mask.sum()
                st.session_state.df.loc[mask, bulk_field] = bulk_value
                st.success(f"{count}건 수정 완료")
                st.rerun()


def _apply_filter(df, f):
    """필터 조건을 Series mask로 반환"""
    col = df[f["field"]].astype(str).str.lower()
    val = str(f["value"]).lower()
    op = f["op"]
    
    if op == "포함":
        return col.str.contains(val, na=False)
    elif op == "일치":
        return col == val
    elif op == "시작":
        return col.str.startswith(val, na=False)
    elif op == "끝남":
        return col.str.endswith(val, na=False)
    elif op == "미포함":
        return ~col.str.contains(val, na=False)
    elif op == "비어있음":
        return col.str.strip() == ""
    elif op == "비어있지 않음":
        return col.str.strip() != ""
    elif op in (">", "<", "≥", "≤"):
        num_col = pd.to_numeric(df[f["field"]], errors="coerce")
        num_val = pd.to_numeric(f["value"], errors="coerce")
        if pd.isna(num_val):
            return pd.Series([True] * len(df))
        if op == ">": return num_col > num_val
        if op == "<": return num_col < num_val
        if op == "≥": return num_col >= num_val
        if op == "≤": return num_col <= num_val
    return pd.Series([True] * len(df))


# ── 메인 영역 ──
if st.session_state.df is None:
    st.markdown("""
    <div style="text-align:center; padding: 100px 20px;">
        <div style="font-size: 64px; margin-bottom: 20px;">📇</div>
        <h1 style="font-size: 28px; font-weight: 700; margin-bottom: 8px;">연락처 매니저</h1>
        <p style="color: #838899; font-size: 16px; line-height: 1.8;">
            왼쪽 사이드바에서 CSV / Excel 파일을 업로드하세요.<br>
            정렬 · 필터 · 편집 · 일괄 수정 후 다운로드할 수 있습니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    df = st.session_state.df.copy()
    fields = list(df.columns)
    
    # 전체 검색
    search = st.text_input("🔍 전체 검색", placeholder="이름, 전화번호, 이메일 등 검색...")
    
    # 검색 적용
    if search.strip():
        q = search.lower()
        mask = pd.Series([False] * len(df))
        for col in fields:
            mask = mask | df[col].astype(str).str.lower().str.contains(q, na=False)
        df = df[mask]
    
    # 필터 적용
    if "filter_count" in st.session_state:
        for i in range(st.session_state.filter_count):
            fld = st.session_state.get(f"ff_{i}", "")
            op = st.session_state.get(f"fo_{i}", "포함")
            val = st.session_state.get(f"fv_{i}", "")
            if fld and fld in fields:
                f = {"field": fld, "op": op, "value": val}
                df = df[_apply_filter(df, f)]
    
    # 정렬 적용
    if "sort_field" in dir() and sort_field != "없음" and sort_field in df.columns:
        # 숫자 정렬 시도
        try:
            sort_key = pd.to_numeric(df[sort_field], errors="raise")
            df = df.assign(__sort_key=sort_key).sort_values(
                "__sort_key", ascending=(sort_dir == "오름차순")
            ).drop(columns=["__sort_key"])
        except (ValueError, TypeError):
            df = df.sort_values(sort_field, ascending=(sort_dir == "오름차순"), key=lambda x: x.str.lower())
    
    # 통계
    total = len(st.session_state.df)
    filtered = len(df)
    changed = 0
    if st.session_state.df_original is not None:
        try:
            changed = (st.session_state.df != st.session_state.df_original).sum().sum()
        except Exception:
            pass
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><p class="stat-num">{total}</p><p class="stat-label">전체 연락처</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><p class="stat-num" style="color:#4e8bff">{filtered}</p><p class="stat-label">조회 결과</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><p class="stat-num" style="color:#ffb445">{changed}</p><p class="stat-label">수정된 셀</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><p class="stat-num" style="color:#38d97a">{len(fields)}</p><p class="stat-label">필드 수</p></div>', unsafe_allow_html=True)
    
    st.markdown("")
    
    # 데이터 에디터
    edited_df = st.data_editor(
        df.reset_index(drop=True),
        use_container_width=True,
        num_rows="dynamic",
        height=500,
        key="data_editor"
    )
    
    # 편집 내용 반영
    if edited_df is not None:
        # 원본 인덱스에 맞춰 업데이트
        st.session_state.df = edited_df.copy()
    
    # 다운로드
    st.markdown("")
    dc1, dc2, dc3 = st.columns([1, 1, 4])
    
    with dc1:
        csv_data = st.session_state.df.to_csv(index=False, encoding="utf-8-sig")
        out_name = st.session_state.filename.rsplit(".", 1)[0] + "_수정.csv"
        st.download_button(
            "⬇️ CSV 다운로드", csv_data, out_name,
            mime="text/csv", use_container_width=True
        )
    
    with dc2:
        buf = io.BytesIO()
        st.session_state.df.to_excel(buf, index=False, engine="openpyxl")
        out_name_xl = st.session_state.filename.rsplit(".", 1)[0] + "_수정.xlsx"
        st.download_button(
            "⬇️ Excel 다운로드", buf.getvalue(), out_name_xl,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
