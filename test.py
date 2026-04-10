import sys

content = sys.stdin.read()

# PATCH 1: Simplified clip text format
old1 = '''        lines = []
        lines.append("📋 메리츠 시상 현황 안내")
        if data_date:
            lines.append(f"📅 기준일: {data_date}")
        lines.append("")
        lines.append(f"👤 {person_line}")
        lines.append("")
        
        current_group = None
        for c in data_cols:
            if '코드' in c or '번호' in c:
                continue
            val = str(row[c]) if not pd.isna(row[c]) else ''
            if not val.strip() or val == '0':
                continue
            
            grp = col_to_grp.get(c)
            is_goal = any(kw in c for kw in goal_keywords)
            
            if grp and grp != current_group:
                if current_group is not None:
                    lines.append("")
                lines.append(f"━━ {grp} ━━")
                current_group = grp
            elif grp is None and not is_goal and current_group is not None:
                lines.append("")
                current_group = None
            
            if '부족금액' in c:
                lines.append(f"🔴 {c}: {val}")
            elif '다음목표' in c:
                lines.append(f"🎯 {c}: {val}")
            else:
                lines.append(f"  {c}: {val}")'''

new1 = '''        # ★ PATCH 1: 간소화된 멘트 포맷
        lines = []
        if data_date:
            lines.append(f"📅 {data_date} 기준")
        lines.append(f"👤 {person_line}")
        
        normal_lines = []
        goal_lines = []
        for c in data_cols:
            if '코드' in c or '번호' in c:
                continue
            val = str(row[c]) if not pd.isna(row[c]) else ''
            if not val.strip() or val == '0':
                continue
            
            if '부족금액' in c:
                goal_lines.append(f"  🔴 {c}: {val}")
            elif '다음목표' in c:
                goal_lines.append(f"  🎯 {c}: {val}")
            else:
                normal_lines.append(f"  ▸ {c}: {val}")
        
        if normal_lines:
            lines.append("")
            lines.extend(normal_lines)
        if goal_lines:
            lines.append("")
            lines.extend(goal_lines)'''

# PATCH 2: Fix fallbackCopy JS
old2 = """    function fallbackCopy(text, btn) {{
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, 999999);
        var ok = false;
        try {{ ok = document.execCommand('copy'); }} catch(e) {{}}
        document.body.removeChild(ta);
        if (ok) {{
            showCopied(btn);
            return;
        }}
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(text).then(function() {{
                showCopied(btn);
            }}).catch(function() {{
                showOverlay(text);
            }});
            return;
        }}
        showOverlay(text);
    }}"""

new2 = """    function fallbackCopy(text, btn) {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(text).then(function() {{
                showCopied(btn);
            }}).catch(function() {{
                execCopyFallback(text, btn);
            }});
            return;
        }}
        execCopyFallback(text, btn);
    }}
    function execCopyFallback(text, btn) {{
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;opacity:0.01;z-index:-1;';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, ta.value.length);
        var ok = false;
        try {{ ok = document.execCommand('copy'); }} catch(e) {{}}
        document.body.removeChild(ta);
        if (ok) {{ showCopied(btn); return; }}
        showOverlay(text);
    }}"""

# PATCH 3: Fix overlay copy textarea
old3 = "        tmp.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;';"
new3 = """        tmp.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;opacity:0.01;z-index:-1;';
        tmp.setAttribute('readonly', '');"""

# PATCH 4: Simplify prize clip text header
old4 = '''    lines = ["", "💰 예상 시상금 현황", f"  총 시상금: {total:,.0f}원"]'''
new4 = '''    lines = ["", f"💰 예상 시상금: {total:,.0f}원"]'''

patches = [(old1, new1), (old2, new2), (old3, new3), (old4, new4)]

for i, (old, new) in enumerate(patches):
    if old in content:
        content = content.replace(old, new, 1)
        print(f"✅ Patch {i+1} applied", file=sys.stderr)
    else:
        print(f"❌ Patch {i+1} NOT FOUND", file=sys.stderr)

sys.stdout.write(content)
