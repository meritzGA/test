"""
카카오톡 공유 기능 모듈
- Kakao JavaScript SDK를 사용한 공유하기 화면 열기
- 클립보드 복사 폴백
"""

import streamlit.components.v1 as components
import urllib.parse
import json


def render_kakao_share_button(
    message_text: str,
    button_label: str = "카카오톡으로 공유",
    kakao_js_key: str = "",
    link_url: str = "",
    button_id: str = "kakao-share-btn",
    height: int = 55
):
    """
    카카오톡 공유 버튼 렌더링

    - kakao_js_key가 있으면: Kakao SDK로 공유 화면 열기
    - 없으면: 클립보드 복사 + 카카오톡 열기 안내
    """
    # 메시지 텍스트 이스케이프
    escaped_msg = json.dumps(message_text, ensure_ascii=False)
    safe_link = link_url or "https://www.meritzfire.com"

    if kakao_js_key:
        html_code = f"""
        <script src="https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js"></script>
        <style>
            .kakao-btn {{
                display: inline-flex; align-items: center; gap: 8px;
                background: #FEE500; color: #191919; border: none;
                padding: 10px 20px; border-radius: 8px; font-size: 14px;
                font-weight: 600; cursor: pointer; font-family: -apple-system, sans-serif;
            }}
            .kakao-btn:hover {{ background: #F5DC00; }}
            .kakao-btn svg {{ width: 20px; height: 20px; }}
            .status {{ font-size: 12px; color: #666; margin-top: 4px; }}
        </style>
        <button class="kakao-btn" id="{button_id}" onclick="shareKakao()">
            <svg viewBox="0 0 24 24" fill="#191919"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg>
            {button_label}
        </button>
        <div class="status" id="status-{button_id}"></div>
        <script>
            if (!Kakao.isInitialized()) {{
                Kakao.init('{kakao_js_key}');
            }}
            function shareKakao() {{
                try {{
                    Kakao.Share.sendDefault({{
                        objectType: 'text',
                        text: {escaped_msg},
                        link: {{
                            mobileWebUrl: '{safe_link}',
                            webUrl: '{safe_link}'
                        }}
                    }});
                }} catch(e) {{
                    // SDK 실패 시 클립보드 복사 폴백
                    copyToClipboard();
                }}
            }}
            function copyToClipboard() {{
                navigator.clipboard.writeText({escaped_msg}).then(function() {{
                    document.getElementById('status-{button_id}').innerText = '✅ 메시지가 클립보드에 복사되었습니다. 카카오톡에 붙여넣기 해주세요.';
                }});
            }}
        </script>
        """
    else:
        # Kakao JS Key가 없을 때: 클립보드 복사 방식
        html_code = f"""
        <style>
            .kakao-btn {{
                display: inline-flex; align-items: center; gap: 8px;
                background: #FEE500; color: #191919; border: none;
                padding: 10px 20px; border-radius: 8px; font-size: 14px;
                font-weight: 600; cursor: pointer; font-family: -apple-system, sans-serif;
            }}
            .kakao-btn:hover {{ background: #F5DC00; }}
            .kakao-btn svg {{ width: 20px; height: 20px; }}
            .status {{ font-size: 12px; color: #666; margin-top: 4px; }}
        </style>
        <button class="kakao-btn" id="{button_id}" onclick="copyAndShare()">
            <svg viewBox="0 0 24 24" fill="#191919"><path d="M12 3C6.48 3 2 6.58 2 10.9c0 2.78 1.8 5.22 4.51 6.6-.2.73-.72 2.64-.82 3.05-.13.5.18.49.38.36.16-.11 2.5-1.7 3.51-2.39.79.11 1.6.17 2.42.17 5.52 0 10-3.58 10-7.9S17.52 3 12 3z"/></svg>
            {button_label}
        </button>
        <div class="status" id="status-{button_id}"></div>
        <script>
            function copyAndShare() {{
                const msg = {escaped_msg};
                navigator.clipboard.writeText(msg).then(function() {{
                    document.getElementById('status-{button_id}').innerHTML =
                        '✅ 클립보드에 복사 완료!&nbsp;&nbsp;<a href="kakaotalk://launch" style="color:#3B82F6;">카카오톡 열기</a>';
                }}).catch(function() {{
                    // fallback for older browsers
                    var ta = document.createElement('textarea');
                    ta.value = msg;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    document.getElementById('status-{button_id}').innerText = '✅ 클립보드에 복사 완료! 카카오톡에서 붙여넣기 해주세요.';
                }});
            }}
        </script>
        """

    components.html(html_code, height=height)


def build_greeting_message(manager_name: str, customer_name: str, custom_text: str) -> str:
    """인사말 메시지 생성"""
    return f"""안녕하세요, {customer_name}님!
{manager_name} 매니저입니다.

{custom_text}"""


def build_prize_message(customer_name: str, prize_info: dict) -> str:
    """시상 안내 메시지 생성"""
    lines = [f"📊 {customer_name}님 시상 현황 안내"]
    lines.append("─" * 20)
    for key, value in prize_info.items():
        if isinstance(value, (int, float)):
            lines.append(f"▪ {key}: {value:,.0f}원")
        else:
            lines.append(f"▪ {key}: {value}")
    return "\n".join(lines)


def build_performance_message(customer_name: str, perf_info: dict, prize_info: dict = None) -> str:
    """실적+시상 안내 메시지 생성"""
    lines = [f"📊 {customer_name}님 실적 & 시상 현황"]
    lines.append("─" * 20)

    lines.append("\n📈 실적 현황")
    for key, value in perf_info.items():
        if isinstance(value, (int, float)):
            lines.append(f"  ▪ {key}: {value:,.0f}")
        else:
            lines.append(f"  ▪ {key}: {value}")

    if prize_info:
        lines.append("\n🏆 시상 현황")
        for key, value in prize_info.items():
            if isinstance(value, (int, float)):
                lines.append(f"  ▪ {key}: {value:,.0f}원")
            else:
                lines.append(f"  ▪ {key}: {value}")

    return "\n".join(lines)
