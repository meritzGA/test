import streamlit as st
import os
import json
import re
from pathlib import Path
from PIL import Image
import openpyxl

# ── 경로 설정 (스크립트 기준 상대경로) ──
BASE_DIR = Path(__file__).resolve().parent
AGENT_XLSX = BASE_DIR / "agent.xlsx"
MAPPING_FILE = BASE_DIR / "mapping.json"
IMG_ROOT = BASE_DIR / "시상"

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

# ── 매핑 ──
def load_mapping():
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

# ── 폴더 탐색 ──
def list_week_folders():
    """시상/ 아래 하위 폴더 목록"""
    if not IMG_ROOT.is_dir():
        return []
    return sorted([d.name for d in IMG_ROOT.iterdir() if d.is_dir()])

def scan_folder(folder_path):
    files = []
    p = Path(folder_path)
    if not p.is_dir():
        return files
    for f in sorted(p.iterdir()):
        if f.suffix.lower() in IMG_EXTS:
            stem = f.stem
            files.append({
                "stem": stem,
                "base": get_base_stem(stem),
                "filename": f.name,
                "path": str(f),
            })
    return files

def show_image(f, **kwargs):
    try:
        st.image(Image.open(f["path"]), **kwargs)
    except:
        st.text("(미리보기 불가)")


st.set_page_config(page_title="대리점 시상 매칭 관리", layout="wide")

def main():
    st.title("📋 대리점 시상 매칭 관리")

    # ── 대리점 리스트 ──
    if not AGENT_XLSX.exists():
        st.error(f"`agent.xlsx`가 없습니다. 스크립트와 같은 폴더에 넣어주세요.\n\n경로: `{AGENT_XLSX}`")
        st.stop()
    agents = load_agents(str(AGENT_XLSX))
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

    # ════════════════════════════════════
    #  폴더 선택
    # ════════════════════════════════════
    week_folders = list_week_folders()

    if week_folders:
        st.subheader("📁 주차 폴더 선택")
        selected_week = st.selectbox(
            "시상 폴더",
            options=week_folders,
            format_func=lambda x: f"시상/{x}/",
            help=f"repo 내 `시상/` 폴더 아래의 주차별 하위폴더입니다. (경로: {IMG_ROOT})",
        )
        target_folder = IMG_ROOT / selected_week
    else:
        st.subheader("📁 폴더 경로 지정")
        st.info(
            "repo에 `시상/` 폴더가 없습니다.\n\n"
            "아래에 직접 경로를 입력하거나, repo에 다음 구조를 만들어주세요:\n"
            "```\n시상/\n  2604_1/\n    a1.png\n    aba.jpg\n  2604_2/\n    ...\n```"
        )
        selected_week = None
        target_folder = None

    # 직접 경로 입력 (항상 표시)
    with st.expander("📂 경로 직접 입력", expanded=not week_folders):
        custom_path = st.text_input(
            "폴더 절대 경로 또는 상대 경로",
            placeholder="예: 시상/2604_1  또는  /mount/src/test/시상/2604_1",
        )
        if custom_path:
            p = Path(custom_path)
            if not p.is_absolute():
                p = BASE_DIR / p
            if p.is_dir():
                target_folder = p
                st.success(f"✅ 폴더 확인됨: `{p}`")
            else:
                st.error(f"❌ 폴더를 찾을 수 없습니다: `{p}`")
                # 해당 상위 폴더 내용 보여주기
                parent = p.parent
                if parent.is_dir():
                    contents = sorted([x.name for x in parent.iterdir()])
                    st.caption(f"`{parent}` 안의 항목: {', '.join(contents[:20])}")
                target_folder = None

    if not target_folder:
        st.stop()

    # ════════════════════════════════════
    #  폴더 스캔
    # ════════════════════════════════════
    files = scan_folder(target_folder)
    if not files:
        st.warning(f"해당 폴더에 이미지 파일이 없습니다: `{target_folder}`")
        st.stop()

    st.success(f"✅ `{target_folder.name}/` 에서 {len(files)}개 이미지 발견")

    # ── 매칭 분류 ──
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

    # ── 탭 ──
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
