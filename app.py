"""
매니저 활동관리 시스템 - 메인 페이지
"""

import streamlit as st
from utils.database import init_db

st.set_page_config(
    page_title="매니저 활동관리 시스템",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB 초기화
init_db()

st.title("📋 매니저 활동관리 시스템")
st.markdown("---")

st.markdown("""
### 페이지 안내

**👈 왼쪽 사이드바에서 페이지를 선택하세요.**

| 페이지 | 설명 |
|--------|------|
| **📱 매니저** | 매니저 로그인 → 사용인 목록 → 카카오톡 메시지 발송 |
| **⚙️ 관리자** | 데이터 업로드/병합, 매니저 활동 모니터링 |
""")

st.info("💡 **모바일 사용 시**: 좌측 상단 `>` 버튼을 눌러 사이드바를 열 수 있습니다.")
