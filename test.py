import streamlit as st
import os
import json
import re
from pathlib import Path
from PIL import Image
import openpyxl

# ── 설정 ──
AGENT_XLSX = "agent.xlsx"          # 대리점 리스트 엑셀
MAPPING_FILE = "mapping.json"      # 파일명↔대리점 매핑 저장

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# ── 베이스명 추출 ──
# aplus1 → aplus,  aplus_2 → aplus,  a1_1 → a1,  a1 → a1 (그대로)
# 규칙:
#   1) 구분자(_-)가 있으면 항상 분리: a1_1 → a1, prime-2 → prime
#   2) 구분자 없이 숫자만 붙으면 베이스가 2자 이상일 때만 분리: aplus1 → aplus, a1 → (그대로)
SEP_SUFFIX = re.compile(r"[_\-]\d+$")        # 구분자 + 숫자
BARE_SUFFIX = re.compile(r"\d+$")            # 숫자만

def get_base_stem(stem):
    """파일명에서 뒤쪽 숫자 접미사를 제거한 베이스명 반환 (없으면 None)"""
    # 1) 구분자 패턴 우선 (_1, -2)
    m = SEP_SUFFIX.search(stem)
    if m:
        base = stem[:m.start()]
        if base:
            return base
    # 2) 구분자 없는 숫자 (aplus1) — 베이스 2자 이상만 허용
    m = BARE_SUFFIX.search(stem)
    if m and m.start() >= 2:
        base = stem[:m.start()]
        return base
    return None

def find_match(stem, mapping):
    """
    1) stem 정확히 매핑에 있으면 → (매핑된 대리점, stem)
    2) 베이스명이 매핑에 있으면 → (매핑된 대리점, base)
    3) 못 찾으면 → (None, None)
    """
    if stem in mapping:
        return mapping[stem], stem
    base = get_base_stem(stem)
    if base and base in mapping:
        return mapping[base], base
    return None, None

st.set_page_config(page_title="대리점 시상 매칭 관리", layout="wide")

# ── 대리점 리스트 로드 ──
@st.cache_data
def load_agents(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    agents = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        if row[0]:
            agents.append(str(row[0]).strip())
    return agents

# ── 매핑 로드/저장 ──
def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

# ── 폴더 스캔 ──
def scan_folder(folder_path):
    """이미지 파일만 반환 (확장자 제외한 이름, 베이스명, 전체경로)"""
    files = []
    if not os.path.isdir(folder_path):
        return files
    for fname in sorted(os.listdir(folder_path)):
        ext = Path(fname).suffix.lower()
        if ext in IMG_EXTS:
            stem = Path(fname).stem
            base = get_base_stem(stem)
            files.append({
                "stem": stem,
                "base": base,          # 숫자 접미사 제거한 베이스명 (없으면 None)
                "filename": fname,
                "path": os.path.join(folder_path, fname),
            })
    return files

# ── 메인 ──
def main():
    st.title("📋 대리점 시상 매칭 관리")
    st.caption("폴더를 지정하면 이미지를 스캔하고, 대리점 리스트와 매칭합니다.")

    agents = load_agents(AGENT_XLSX)
    mapping = load_mapping()

    # 사이드바: 현재 매핑 현황
    with st.sidebar:
        st.header("📎 현재 매핑 현황")
        st.metric("등록된 매핑 수", f"{len(mapping)}개")
        if mapping:
            with st.expander("매핑 목록 보기", expanded=False):
                for file_key, agent_name in sorted(mapping.items()):
                    st.text(f"{file_key} → {agent_name}")
            
            if st.button("⚠️ 전체 매핑 초기화", type="secondary"):
                save_mapping({})
                st.rerun()

        st.divider()
        st.header("📂 대리점 리스트")
        st.info(f"총 {len(agents)}개 대리점")
        with st.expander("전체 목록"):
            for i, a in enumerate(agents, 1):
                st.text(f"{i}. {a}")

    # 폴더 경로 입력
    folder_path = st.text_input(
        "📁 시상 이미지 폴더 경로",
        placeholder="예: C:\\시상\\2604_1 또는 /home/user/시상/2604_1",
        help="주차별 시상 이미지가 들어있는 폴더 경로를 입력하세요"
    )

    if not folder_path:
        st.info("폴더 경로를 입력해주세요.")
        return

    if not os.path.isdir(folder_path):
        st.error(f"❌ 폴더를 찾을 수 없습니다: {folder_path}")
        return

    # 폴더 스캔
    files = scan_folder(folder_path)
    if not files:
        st.warning("해당 폴더에 이미지 파일이 없습니다.")
        return

    st.success(f"✅ {len(files)}개 이미지 파일 발견")

    # 매칭/미매칭 분류 (베이스명 매칭 포함)
    matched = []
    unmatched = []
    for f in files:
        agent, matched_key = find_match(f["stem"], mapping)
        if agent:
            suffix = ""
            if matched_key and matched_key != f["stem"]:
                suffix = f["stem"][len(matched_key):]  # 예: "_1", "2" 등
            matched.append({**f, "agent": agent, "matched_key": matched_key, "suffix": suffix})
        else:
            unmatched.append(f)

    # ── 탭 구성 ──
    tab1, tab2, tab3 = st.tabs([
        f"🔗 매칭 완료 ({len(matched)})",
        f"❓ 미매칭 ({len(unmatched)})",
        "🖼️ 전체 미리보기"
    ])

    # ── 탭1: 매칭 완료 ──
    with tab1:
        if not matched:
            st.info("아직 매칭된 파일이 없습니다.")
        else:
            for f in matched:
                col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                with col1:
                    try:
                        img = Image.open(f["path"])
                        st.image(img, width=120)
                    except:
                        st.text("(미리보기 불가)")
                with col2:
                    st.markdown(f"**파일명:** `{f['filename']}`")
                    if f["suffix"]:
                        st.caption(f"베이스: `{f['matched_key']}` · 접미사: `{f['suffix']}`")
                with col3:
                    st.markdown(f"**대리점:** {f['agent']}")
                with col4:
                    if st.button("매칭 해제", key=f"unmatch_{f['stem']}"):
                        del mapping[f["matched_key"]]
                        save_mapping(mapping)
                        st.rerun()
                st.divider()

    # ── 탭2: 미매칭 ──
    with tab2:
        if not unmatched:
            st.success("🎉 모든 파일이 매칭되었습니다!")
        else:
            st.warning(f"{len(unmatched)}개 파일의 대리점 매칭이 필요합니다.")

            # 이미 매칭된 대리점 목록
            already_matched_agents = set(mapping.values())
            
            for f in unmatched:
                st.divider()
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    try:
                        img = Image.open(f["path"])
                        st.image(img, width=150)
                    except:
                        st.text("(미리보기 불가)")
                with col2:
                    st.markdown(f"### 📄 `{f['filename']}`")
                    # 베이스명 감지 표시
                    save_key = f["stem"]
                    if f["base"]:
                        suffix = f["stem"][len(f["base"]):]
                        st.caption(f"베이스명: **{f['base']}** · 접미사: `{suffix}`")
                        save_key = f["base"]  # 저장 시 베이스명 사용
                    else:
                        st.caption(f"파일명: **{f['stem']}**")
                    
                    # 파일명으로 유사 대리점 자동 추천
                    search_key = (f["base"] or f["stem"]).lower()
                    suggestions = [a for a in agents if search_key in a.lower() or a.lower() in search_key]
                    if suggestions:
                        st.info(f"💡 추천: {', '.join(suggestions)}")

                with col3:
                    # 미매칭 대리점만 상단에 표시
                    unmatched_agents = [a for a in agents if a not in already_matched_agents]
                    all_options = ["-- 선택 --"] + unmatched_agents
                    if already_matched_agents:
                        all_options.append("───── 이미 매칭된 대리점 ─────")
                        all_options.extend(sorted(already_matched_agents))

                    selected = st.selectbox(
                        "대리점 선택",
                        options=all_options,
                        key=f"select_{f['stem']}",
                        label_visibility="collapsed"
                    )
                    
                    if st.button("✅ 매칭 저장", key=f"save_{f['stem']}", type="primary"):
                        if selected and selected != "-- 선택 --" and not selected.startswith("─"):
                            mapping[save_key] = selected
                            save_mapping(mapping)
                            st.success(f"✅ {save_key} → {selected}")
                            st.rerun()
                        else:
                            st.error("대리점을 선택해주세요.")

    # ── 탭3: 전체 미리보기 ──
    with tab3:
        cols_per_row = 3
        for i in range(0, len(files), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(files):
                    break
                f = files[idx]
                with col:
                    agent_name, _ = find_match(f["stem"], mapping)
                    agent_label = agent_name or "❓ 미매칭"
                    try:
                        img = Image.open(f["path"])
                        st.image(img, use_container_width=True)
                    except:
                        st.text("(미리보기 불가)")
                    st.caption(f"📄 {f['filename']}")
                    st.caption(f"🏢 {agent_label}")

    # ── 하단: 일괄 매칭 도구 ──
    st.divider()
    with st.expander("🔧 수동 매핑 추가 (파일명 직접 입력)"):
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            manual_stem = st.text_input("파일명 (확장자 제외)", key="manual_stem")
        with col2:
            manual_agent = st.selectbox("대리점", ["-- 선택 --"] + agents, key="manual_agent")
        with col3:
            st.write("")  # 정렬용
            st.write("")
            if st.button("추가", key="manual_add", type="primary"):
                if manual_stem and manual_agent != "-- 선택 --":
                    mapping[manual_stem] = manual_agent
                    save_mapping(mapping)
                    st.success(f"✅ {manual_stem} → {manual_agent}")
                    st.rerun()

if __name__ == "__main__":
    main()
