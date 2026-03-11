import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="연락처 매니저", page_icon="📇", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f7f8fb; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e5e7ee; }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stDataEditor"] { border: 1px solid #e0e3eb; border-radius: 10px; overflow: hidden; }
    .stat-card {
        background: #ffffff; border: 1px solid #e5e7ee; border-radius: 12px;
        padding: 16px 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stat-num { font-size: 30px; font-weight: 700; margin: 0; color: #1a1d27; }
    .stat-label { font-size: 12px; color: #8b90a5; margin: 4px 0 0 0; }
    .hero-box {
        background: #ffffff; border: 1px solid #e5e7ee; border-radius: 16px;
        padding: 60px 30px; text-align: center; margin: 40px auto; max-width: 500px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .hero-box h1 { font-size: 26px; font-weight: 700; color: #1a1d27; margin: 12px 0 8px; }
    .hero-box p { color: #8b90a5; font-size: 15px; line-height: 1.8; }
    .stDownloadButton > button {
        background: #ffffff !important; border: 1px solid #e0e3eb !important;
        color: #1a1d27 !important; font-weight: 600 !important; border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# 유틸
# ═══════════════════════════════════════

def apply_filter(df, f):
    col = df[f["field"]].astype(str).str.lower()
    val = str(f["value"]).lower()
    op = f["op"]
    if op == "포함": return col.str.contains(val, na=False)
    if op == "일치": return col == val
    if op == "시작": return col.str.startswith(val, na=False)
    if op == "끝남": return col.str.endswith(val, na=False)
    if op == "미포함": return ~col.str.contains(val, na=False)
    if op == "비어있음": return col.str.strip() == ""
    if op == "비어있지 않음": return col.str.strip() != ""
    if op in (">", "<", "≥", "≤"):
        num_col = pd.to_numeric(df[f["field"]], errors="coerce")
        num_val = pd.to_numeric(f["value"], errors="coerce")
        if pd.isna(num_val): return pd.Series([True] * len(df), index=df.index)
        if op == ">": return num_col > num_val
        if op == "<": return num_col < num_val
        if op == "≥": return num_col >= num_val
        if op == "≤": return num_col <= num_val
    return pd.Series([True] * len(df), index=df.index)


def load_file(uploaded):
    ext = uploaded.name.split(".")[-1].lower()
    if ext in ("xlsx", "xls"):
        return pd.read_excel(uploaded, dtype=str).fillna("")
    elif ext == "tsv":
        return pd.read_csv(uploaded, sep="\t", dtype=str).fillna("")
    else:
        try:
            return pd.read_csv(uploaded, dtype=str, encoding="utf-8").fillna("")
        except UnicodeDecodeError:
            uploaded.seek(0)
            return pd.read_csv(uploaded, dtype=str, encoding="cp949").fillna("")


def get_filters():
    """세션에서 현재 활성 필터 목록을 읽어옴"""
    filters = []
    for i in range(st.session_state.get("filter_count", 0)):
        fld = st.session_state.get(f"ff_{i}", "")
        op = st.session_state.get(f"fo_{i}", "포함")
        val = st.session_state.get(f"fv_{i}", "")
        if fld:
            filters.append({"field": fld, "op": op, "value": val})
    return filters


# ═══════════════════════════════════════
# 세션 초기화
# ═══════════════════════════════════════

for key, default in [
    ("df", None), ("df_original", None), ("filename", ""),
    ("filter_count", 0), ("delete_log", 0), ("select_all", False),
    ("uploaded_file_id", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ═══════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════

with st.sidebar:
    st.markdown("## 📇 연락처 매니저")
    st.markdown("---")

    uploaded = st.file_uploader(
        "파일 업로드", type=["csv", "xlsx", "xls", "tsv", "txt"],
        help="CSV, Excel, TSV 파일 지원"
    )

    # ★ 새 파일일 때만 처리 (이름+사이즈로 판별)
    if uploaded is not None:
        file_id = f"{uploaded.name}_{uploaded.size}"
        if file_id != st.session_state.uploaded_file_id:
            try:
                raw = load_file(uploaded)
                raw.insert(0, "_idx", range(len(raw)))
                st.session_state.df = raw.copy()
                st.session_state.df_original = raw.copy()
                st.session_state.filename = uploaded.name
                st.session_state.filter_count = 0
                st.session_state.delete_log = 0
                st.session_state.select_all = False
                st.session_state.uploaded_file_id = file_id
                st.rerun()
            except Exception as e:
                st.error(f"파일 읽기 실패: {e}")

    if st.session_state.df is not None:
        user_fields = [c for c in st.session_state.df.columns if c != "_idx"]

        # ── 필터 ──
        st.markdown("---")
        st.markdown("### 🔍 필터")

        col_add, col_reset = st.columns(2)
        with col_add:
            if st.button("➕ 조건 추가", use_container_width=True):
                st.session_state.filter_count += 1
                st.rerun()
        with col_reset:
            if st.button("🔄 초기화", use_container_width=True):
                st.session_state.filter_count = 0
                st.rerun()

        for i in range(st.session_state.filter_count):
            st.markdown(f"**조건 {i+1}**")
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("필드", [""] + user_fields, key=f"ff_{i}")
            with c2:
                st.selectbox("연산", [
                    "포함", "일치", "시작", "끝남", "미포함",
                    "비어있음", "비어있지 않음", ">", "<", "≥", "≤"
                ], key=f"fo_{i}")
            op_val = st.session_state.get(f"fo_{i}", "포함")
            if op_val not in ("비어있음", "비어있지 않음"):
                st.text_input("값", key=f"fv_{i}")

        # ── 정렬 ──
        st.markdown("---")
        st.markdown("### 📊 정렬")
        sort_field = st.selectbox("정렬 기준", ["없음"] + user_fields, key="sort_field")
        sort_dir = st.radio("방향", ["오름차순", "내림차순"], horizontal=True, key="sort_dir")

        # ── 일괄 수정 (필터 기준) ──
        st.markdown("---")
        st.markdown("### ✏️ 일괄 수정 (필터 기준)")
        st.caption("현재 필터 조건에 해당하는 행을 일괄 변경합니다.")
        bulk_field = st.selectbox("수정할 필드", [""] + user_fields, key="bulk_f")
        bulk_value = st.text_input("변경할 값", key="bulk_v")
        if st.button("✅ 일괄 적용", use_container_width=True, type="primary"):
            if bulk_field:
                mask = pd.Series([True] * len(st.session_state.df), index=st.session_state.df.index)
                for f in get_filters():
                    if f["field"] in user_fields:
                        mask = mask & apply_filter(st.session_state.df, f)
                count = int(mask.sum())
                st.session_state.df.loc[mask, bulk_field] = bulk_value
                st.toast(f"✅ {count}건 수정 완료")
                st.rerun()


# ═══════════════════════════════════════
# 메인 영역
# ═══════════════════════════════════════

if st.session_state.df is None:
    st.markdown("""
    <div class="hero-box">
        <div style="font-size: 56px;">📇</div>
        <h1>연락처 매니저</h1>
        <p>
            왼쪽 사이드바에서 CSV / Excel 파일을 업로드하세요.<br>
            정렬 · 필터 · 편집 · 삭제 · 일괄 수정 후 다운로드할 수 있습니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── 데이터 준비 ──
master = st.session_state.df.copy()
user_fields = [c for c in master.columns if c != "_idx"]
view = master.copy()

# 전체 검색
search = st.text_input("🔍 전체 검색", placeholder="이름, 전화번호, 이메일 등 검색...", key="search")
if search.strip():
    q = search.lower()
    mask = pd.Series([False] * len(view), index=view.index)
    for col in user_fields:
        mask = mask | view[col].astype(str).str.lower().str.contains(q, na=False)
    view = view[mask]

# 필터 적용
for f in get_filters():
    if f["field"] in user_fields:
        view = view[apply_filter(view, f)]

# 정렬
sort_field = st.session_state.get("sort_field", "없음")
sort_dir = st.session_state.get("sort_dir", "오름차순")
if sort_field != "없음" and sort_field in view.columns:
    try:
        sk = pd.to_numeric(view[sort_field], errors="raise")
        view = view.assign(__sk=sk).sort_values("__sk", ascending=(sort_dir == "오름차순")).drop(columns=["__sk"])
    except (ValueError, TypeError):
        view = view.sort_values(sort_field, ascending=(sort_dir == "오름차순"), key=lambda x: x.str.lower())

# ── 통계 ──
total = len(master)
filtered = len(view)
changed = 0
if st.session_state.df_original is not None:
    try:
        orig = st.session_state.df_original
        m_sub = master.set_index("_idx")[user_fields]
        o_sub = orig.set_index("_idx")[user_fields]
        common_idx = m_sub.index.intersection(o_sub.index)
        if len(common_idx) > 0:
            changed = int((m_sub.loc[common_idx] != o_sub.loc[common_idx]).sum().sum())
    except Exception:
        pass

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-card"><p class="stat-num">{total}</p><p class="stat-label">전체 연락처</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card"><p class="stat-num" style="color:#3b82f6">{filtered}</p><p class="stat-label">조회 결과</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-card"><p class="stat-num" style="color:#f59e0b">{changed}</p><p class="stat-label">수정된 셀</p></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="stat-card"><p class="stat-num" style="color:#ef4444">{st.session_state.delete_log}</p><p class="stat-label">삭제된 행</p></div>', unsafe_allow_html=True)

st.markdown("")

# ── 선택 버튼 ──
sel_cols = st.columns([1, 1, 4])
with sel_cols[0]:
    if st.button("☑️ 모두 선택", use_container_width=True):
        st.session_state.select_all = True
        st.rerun()
with sel_cols[1]:
    if st.button("⬜ 모두 해제", use_container_width=True):
        st.session_state.select_all = False
        st.rerun()

# ── 테이블 ──
display = view[user_fields + ["_idx"]].reset_index(drop=True).copy()
display.insert(0, "선택", st.session_state.select_all)

edited = st.data_editor(
    display,
    use_container_width=True,
    height=500,
    column_config={
        "선택": st.column_config.CheckboxColumn("선택", default=False, width="small"),
        "_idx": None,
    },
    disabled=["_idx"],
    hide_index=True,
    key="main_editor",
)

# 선택 집계
selected_mask = edited["선택"] == True
selected_count = int(selected_mask.sum())
selected_idxs = edited.loc[selected_mask, "_idx"].tolist()

st.markdown("")

# ── 액션 ──
st.markdown("#### 🎯 선택 항목 작업")
act_cols = st.columns([1.2, 1, 1.2, 1])

with act_cols[0]:
    delete_clicked = st.button(
        f"🗑️ 선택 삭제 ({selected_count}건)",
        use_container_width=True,
        disabled=(selected_count == 0),
        type="primary" if selected_count > 0 else "secondary",
    )
with act_cols[1]:
    edit_field = st.selectbox("수정 필드", [""] + user_fields, key="sel_edit_f", label_visibility="collapsed")
with act_cols[2]:
    edit_value = st.text_input("변경값", key="sel_edit_v", label_visibility="collapsed", placeholder="변경할 값")
with act_cols[3]:
    edit_clicked = st.button(
        f"✏️ 수정 ({selected_count}건)",
        use_container_width=True,
        disabled=(selected_count == 0 or not edit_field),
    )

if delete_clicked and selected_count > 0:
    st.session_state.df = st.session_state.df[~st.session_state.df["_idx"].isin(selected_idxs)].reset_index(drop=True)
    st.session_state.delete_log += selected_count
    st.session_state.select_all = False
    st.toast(f"✅ {selected_count}건 삭제 완료")
    st.rerun()

if edit_clicked and selected_count > 0 and edit_field:
    mask = st.session_state.df["_idx"].isin(selected_idxs)
    st.session_state.df.loc[mask, edit_field] = edit_value
    st.session_state.select_all = False
    st.toast(f"✅ {selected_count}건 '{edit_field}' 수정 완료")
    st.rerun()

# ── 셀 직접 편집 저장 ──
st.markdown("")
st.markdown("#### 💾 셀 편집")
st.caption("테이블에서 셀을 직접 수정한 뒤 아래 버튼을 눌러 저장하세요.")
if st.button("💾 셀 편집 내용 저장"):
    update_count = 0
    for _, row in edited.iterrows():
        idx_val = row["_idx"]
        m = st.session_state.df["_idx"] == idx_val
        if m.any():
            for col in user_fields:
                new_val = str(row[col]) if pd.notna(row[col]) else ""
                old_val = str(st.session_state.df.loc[m, col].values[0])
                if new_val != old_val:
                    st.session_state.df.loc[m, col] = new_val
                    update_count += 1
    if update_count > 0:
        st.toast(f"✅ {update_count}개 셀 저장 완료")
        st.rerun()
    else:
        st.info("변경된 셀이 없습니다.")

# ── 다운로드 ──
st.markdown("---")
dc1, dc2, dc3 = st.columns([1, 1, 4])
export_df = st.session_state.df[user_fields]

with dc1:
    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
    out_csv = st.session_state.filename.rsplit(".", 1)[0] + "_수정.csv"
    st.download_button("⬇️ CSV 다운로드", csv_data, out_csv, mime="text/csv", use_container_width=True)

with dc2:
    buf = io.BytesIO()
    export_df.to_excel(buf, index=False, engine="openpyxl")
    out_xl = st.session_state.filename.rsplit(".", 1)[0] + "_수정.xlsx"
    st.download_button("⬇️ Excel 다운로드", buf.getvalue(), out_xl,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True)
