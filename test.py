import streamlit as st
import os
import json
import re
import io
from pathlib import Path
from PIL import Image
import openpyxl

# ── 경로 설정 ──
BASE_DIR = Path(__file__).resolve().parent
AGENT_XLSX = BASE_DIR / "agent.xlsx"
MAPPING_FILE = BASE_DIR / "mapping.json"

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# ── 베이스명 추출 ──
SEP_SUFFIX = re.compile(r"[_\-]\d+$")
BARE_SUFFIX = re.compile(r"\d+$")

def get_base_stem(stem):
    m = SEP_SUFFIX.search(stem)
    if m:
        base = stem[:m.start()]
        if base:
            return base
    m = BARE_SUFFIX.search(stem)
    if m and m.start() >= 2:
        return stem[:m.start()]
    return None

def find_match(stem, mapping):
    if stem in mapping:
        return mapping[stem], stem
    base = get_base_stem(stem)
    if base and base in mapping:
        return mapping[base], base
    return None, None

# ── 대리점 리스트 ──
@st.cache_data
def load_agents(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    return [str(r[0]).strip() for r in ws.iter_rows(min_row=1, values_only=True) if r[0]]

@st.cache_data
def load_agents_from_bytes(data: bytes):
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.active
    return [str(r[0]).strip() for r in ws.iter_rows(min_row=1, values_only=True) if r[0]]

# ── 매핑 ──
def load_mapping():
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

# ── 업로드 이미지 처리 ──
def process_uploaded_images(uploaded_files):
    files = []
    for uf in uploaded_files:
        if Path(uf.name).suffix.lower() not in IMG_EXTS:
            continue
        stem = Path(uf.name).stem
        files.append({
            "stem": stem,
            "base": get_base_stem(stem),
            "filename": uf.name,
            "uploaded": uf,
        })
    return sorted(files, key=lambda x: x["filename"])

def show_image(f, **kwargs):
    try:
        f["uploaded"].seek(0)
        st.image(f["uploaded"], **kwargs)
    except:
        st.text("(미리보기 불가)")


st.set_page_config(page_title="대리점 시상 매칭 관리", layout="wide")

def main():
    st.title("📋 대리점 시상 매칭 관리")

    # ══════════════════════════════════
    #  대리점 리스트 로드
    # ══════════════════════════════════
    if AGENT_XLSX.exists():
        agents = load_agents(str(AGENT_XLSX))
    else:
        st.warning("`agent.xlsx`가 repo에 없습니다. 업로드해주세요.")
        uploaded_xlsx = st.file_uploader("📄 agent.xlsx 업로드", type=["xlsx"])
        if uploaded_xlsx:
            agents = load_agents_from_bytes(uploaded_xlsx.read())
        else:
            st.stop()

    mapping = load_mapping()

    # ── 사이드바 ──
    with st.sidebar:
        st.header("📎 매핑 현황")
        st.metric("등록된 매핑", f"{len(mapping)}개")
        if mapping:
            with st.expander("매핑 목록", expanded=False):
                for k, v in sorted(mapping.items()):
                    st.text(f"{k} → {v}")
            if st.button("⚠️ 전체 초기화", type="secondary"):
                save_mapping({})
                st.rerun()
        st.divider()
        st.header("📂 대리점 리스트")
        st.info(f"총 {len(agents)}개")
        with st.expander("전체 목록"):
            for i, a in enumerate(agents, 1):
                st.text(f"{i}. {a}")

    # ══════════════════════════════════
    #  시상 이미지 업로드
    # ══════════════════════════════════
    st.subheader("📁 시상 이미지 업로드")
    st.caption(
        "로컬 PC의 주차별 시상 폴더에서 이미지를 선택해주세요. "
        "(Ctrl+A로 폴더 내 전체 선택 가능)"
    )

    uploaded = st.file_uploader(
        "시상 이미지 선택",
        type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded:
        st.info("로컬 시상 폴더에서 이미지 파일들을 선택해주세요.")
        st.stop()

    files = process_uploaded_images(uploaded)
    if not files:
        st.warning("업로드된 파일 중 이미지가 없습니다.")
        st.stop()

    st.success(f"✅ {len(files)}개 이미지 업로드됨")

    # ══════════════════════════════════
    #  매칭 분류
    # ══════════════════════════════════
    matched, unmatched = [], []
    for f in files:
        agent, matched_key = find_match(f["stem"], mapping)
        if agent:
            suffix = ""
            if matched_key and matched_key != f["stem"]:
                suffix = f["stem"][len(matched_key):]
            matched.append({
                **f, "agent": agent,
                "matched_key": matched_key, "suffix": suffix,
            })
        else:
            unmatched.append(f)

    # ══════════════════════════════════
    #  탭
    # ══════════════════════════════════
    tab1, tab2, tab3 = st.tabs([
        f"🔗 매칭 완료 ({len(matched)})",
        f"❓ 미매칭 ({len(unmatched)})",
        "🖼️ 전체 미리보기",
    ])

    with tab1:
        if not matched:
            st.info("아직 매칭된 파일이 없습니다.")
        else:
            for f in matched:
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                with c1:
                    show_image(f, width=120)
                with c2:
                    st.markdown(f"**파일:** `{f['filename']}`")
                    if f["suffix"]:
                        st.caption(f"베이스: `{f['matched_key']}` · 접미사: `{f['suffix']}`")
                with c3:
                    st.markdown(f"**대리점:** {f['agent']}")
                with c4:
                    if st.button("해제", key=f"un_{f['stem']}"):
                        del mapping[f["matched_key"]]
                        save_mapping(mapping)
                        st.rerun()
                st.divider()

    with tab2:
        if not unmatched:
            st.success("🎉 모든 파일이 매칭되었습니다!")
        else:
            st.warning(f"{len(unmatched)}개 파일 매칭 필요")
            already = set(mapping.values())

            for f in unmatched:
                st.divider()
                c1, c2, c3 = st.columns([1, 3, 2])
                with c1:
                    show_image(f, width=150)
                with c2:
                    st.markdown(f"### 📄 `{f['filename']}`")
                    save_key = f["stem"]
                    if f["base"]:
                        suffix = f["stem"][len(f["base"]):]
                        st.caption(f"베이스명: **{f['base']}** · 접미사: `{suffix}`")
                        save_key = f["base"]
                    else:
                        st.caption(f"파일명: **{f['stem']}**")

                    search_key = (f["base"] or f["stem"]).lower()
                    suggestions = [
                        a for a in agents
                        if search_key in a.lower() or a.lower() in search_key
                    ]
                    if suggestions:
                        st.info(f"💡 추천: {', '.join(suggestions)}")

                with c3:
                    ua = [a for a in agents if a not in already]
                    opts = ["-- 선택 --"] + ua
                    if already:
                        opts.append("───── 이미 매칭됨 ─────")
                        opts.extend(sorted(already))

                    sel = st.selectbox(
                        "대리점", opts,
                        key=f"sel_{f['stem']}",
                        label_visibility="collapsed",
                    )
                    if st.button("✅ 저장", key=f"sv_{f['stem']}", type="primary"):
                        if sel and sel != "-- 선택 --" and not sel.startswith("─"):
                            mapping[save_key] = sel
                            save_mapping(mapping)
                            st.rerun()
                        else:
                            st.error("대리점을 선택해주세요.")

    with tab3:
        n = 3
        for i in range(0, len(files), n):
            cols = st.columns(n)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(files):
                    break
                f = files[idx]
                with col:
                    a, _ = find_match(f["stem"], mapping)
                    show_image(f, use_container_width=True)
                    st.caption(f"📄 {f['filename']}")
                    st.caption(f"🏢 {a or '❓ 미매칭'}")

    # ── 수동 매핑 ──
    st.divider()
    with st.expander("🔧 수동 매핑 추가"):
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            ms = st.text_input("파일명 (확장자 제외)", key="ms")
        with c2:
            ma = st.selectbox("대리점", ["-- 선택 --"] + agents, key="ma")
        with c3:
            st.write("")
            st.write("")
            if st.button("추가", key="madd", type="primary"):
                if ms and ma != "-- 선택 --":
                    mapping[ms] = ma
                    save_mapping(mapping)
                    st.rerun()


if __name__ == "__main__":
    main()
