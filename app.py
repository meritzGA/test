#!/usr/bin/env python3
"""
주차브릿지 시책 지원을 두 번째 앱(매니저 실적 관리)에 추가하는 스크립트.

사용법:
  python3 add_weekly_bridge.py

이 스크립트를 app2.py와 같은 폴더에 넣고 실행하면,
app2.py를 읽어서 주차브릿지 지원을 추가한 뒤 덮어씁니다.
(원본은 app2.py.backup으로 자동 백업됩니다.)
"""
import os, sys, shutil

# ── 설정 ──
TARGET = "app2.py"  # 수정할 파일명 (필요시 변경)

if not os.path.exists(TARGET):
    # 같은 폴더에 다른 이름이면 찾아보기
    candidates = [f for f in os.listdir('.') if f.endswith('.py') and '매니저' in f or '실적' in f]
    if candidates:
        print(f"⚠️ '{TARGET}' 파일을 찾을 수 없습니다.")
        print(f"   혹시 이 파일인가요? {candidates}")
    else:
        print(f"❌ '{TARGET}' 파일을 찾을 수 없습니다. 같은 폴더에 넣어주세요.")
    sys.exit(1)

with open(TARGET, 'r', encoding='utf-8') as f:
    src = f.read()

changes = 0

def safe_replace(source, old, new, label):
    global changes
    if old not in source:
        print(f"  ⚠️ {label}: 이미 적용되었거나 원본이 다릅니다 (건너뜀)")
        return source
    result = source.replace(old, new, 1)
    changes += 1
    print(f"  ✅ {label}")
    return result

print(f"\n🔧 '{TARGET}' 파일에 주차브릿지 지원 추가 중...\n")

# ═══════════════════════════════════════════
# 1. calculate_prize_for_code — 주차브릿지 elif 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    '''            else:
                if not prize_details: continue
                val = _safe_float_prize(_first_valid(match_df, cfg.get('col_val', '')))
                results.append({"name": cfg['name'], "category": "weekly", "type": "구간",
                    "val": val, "prize": prize, "prize_details": prize_details})''',
    
    '''            elif "주차브릿지" in p_type:
                w3 = _safe_float_prize(_first_valid(match_df, cfg.get('col_val_w3', '')))
                w3_label = cfg.get('w3_label', '3주')
                w4_label = cfg.get('w4_label', '4주')
                wb_tiers = cfg.get('weekly_bridge_tiers', [])
                tier_achieved = 0; projected_prize = 0
                for threshold, prize_amt in wb_tiers:
                    if w3 >= threshold:
                        tier_achieved = threshold; projected_prize = prize_amt; break
                next_tier = None; next_tier_prize = 0
                for threshold, prize_amt in reversed(wb_tiers):
                    if w3 < threshold: next_tier = threshold; next_tier_prize = prize_amt; break
                shortfall = max(0, (next_tier or 0) - w3) if next_tier else 0
                if w3 == 0: continue
                results.append({
                    "name": cfg['name'], "category": "weekly", "type": "주차브릿지",
                    "val_w3": w3, "tier": tier_achieved, "prize": projected_prize,
                    "next_tier": next_tier, "next_tier_prize": next_tier_prize if next_tier else 0,
                    "shortfall": shortfall, "w3_label": w3_label, "w4_label": w4_label
                })
            else:
                if not prize_details: continue
                val = _safe_float_prize(_first_valid(match_df, cfg.get('col_val', '')))
                results.append({"name": cfg['name'], "category": "weekly", "type": "구간",
                    "val": val, "prize": prize, "prize_details": prize_details})''',
    "1. calculate_prize_for_code")

# ═══════════════════════════════════════════
# 2. format_prize_clip_text — 주차브릿지 텍스트 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    '''            else:
                lines.append(f"  {r['name']}: {r['prize']:,.0f}원")
                for d in r.get('prize_details', []):
                    lines.append(f"    · {d['label']}: {d['amount']:,.0f}원")
    for r in cumul_res:''',
    
    '''            elif r['type'] == '주차브릿지':
                w3l = r.get('w3_label','3주'); w4l = r.get('w4_label','4주')
                lines.append(f"  {r['name']}: {r['prize']:,.0f}원 ({w4l} 동일 가동 시)")
                lines.append(f"    {w3l} 실적: {r.get('val_w3',0):,.0f}원 (구간: {r.get('tier',0):,.0f}원)")
                if r.get('shortfall', 0) > 0:
                    lines.append(f"    🚀 {r['shortfall']:,.0f}원 더 하면 → {r.get('next_tier_prize',0):,.0f}원")
            else:
                lines.append(f"  {r['name']}: {r['prize']:,.0f}원")
                for d in r.get('prize_details', []):
                    lines.append(f"    · {d['label']}: {d['amount']:,.0f}원")
    for r in cumul_res:''',
    "2. format_prize_clip_text")

# ═══════════════════════════════════════════
# 3. build_prize_card_html — 주차브릿지 카드 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """            else:
                h += f'<div class="m-row"><span class="m-label">{r["name"]}</span><span class="m-val" style="color:#d9232e;font-weight:700;">{pz}</span></div>'
                h += _prize_detail_sub_html(r.get('prize_details', []))
    if cumul_res:""",
    
    """            elif r['type'] == '주차브릿지':
                w3l = r.get('w3_label','3주'); w4l = r.get('w4_label','4주')
                tier_txt = f"{r.get('tier',0):,.0f}원" if r.get('tier',0) > 0 else "미달성"
                label = f"{r['name']}<br><span style='font-size:10px;color:#888;'>({w4l} 동일 가동 시)</span>"
                h += f'<div class="m-row"><span class="m-label">{label}</span><span class="m-val" style="color:#d9232e;font-weight:700;">{pz}</span></div>'
                h += f'<div class="m-row"><span class="m-label" style="padding-left:10px;font-size:11px;">· {w3l} 실적 (구간: {tier_txt})</span><span class="m-val" style="font-size:11px;">{r.get("val_w3",0):,.0f}원</span></div>'
                if r.get('shortfall', 0) > 0:
                    h += f'<div class="m-row"><span class="m-label" style="padding-left:10px;font-size:10px;color:#888;">🚀 {r["shortfall"]:,.0f}원 더 하면 → {r.get("next_tier_prize",0):,.0f}원</span><span class="m-val"></span></div>'
            else:
                h += f'<div class="m-row"><span class="m-label">{r["name"]}</span><span class="m-val" style="color:#d9232e;font-weight:700;">{pz}</span></div>'
                h += _prize_detail_sub_html(r.get('prize_details', []))
    if cumul_res:""",
    "3. build_prize_card_html")

# ═══════════════════════════════════════════
# 4. Admin 라디오 — 주차브릿지 옵션 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                type_idx = 0
                if "1기간" in cfg.get('type', ''): type_idx = 1
                elif "2기간" in cfg.get('type', ''): type_idx = 2
                cfg['type'] = st.radio("시책 종류", 
                    ["구간 시책", "브릿지 시책 (1기간: 시상 확정)", "브릿지 시책 (2기간: 당월 달성 조건)"],
                    index=type_idx, horizontal=True, key=f"ptype_{idx}")""",
    
    """                type_idx = 0
                if "1기간" in cfg.get('type', ''): type_idx = 1
                elif "2기간" in cfg.get('type', ''): type_idx = 2
                elif "주차브릿지" in cfg.get('type', ''): type_idx = 3
                cfg['type'] = st.radio("시책 종류", 
                    ["구간 시책", "브릿지 시책 (1기간: 시상 확정)", "브릿지 시책 (2기간: 당월 달성 조건)", "주차브릿지 시책 (동일주차 가동)"],
                    index=type_idx, horizontal=True, key=f"ptype_{idx}")""",
    "4. Admin 라디오 버튼")

# ═══════════════════════════════════════════
# 5. Admin 필드 — 주차브릿지 설정 UI 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                else:
                    cfg['col_val'] = st.selectbox("실적 수치 열", cols, index=_gi(cfg.get('col_val',''), cols), key=f"pval_{idx}")""",
    
    '''                elif "주차브릿지" in cfg['type']:
                    cfg['w3_label'] = st.text_input("기준 주차 라벨", value=cfg.get('w3_label','3주'), key=f"pw3lbl_{idx}")
                    cfg['w4_label'] = st.text_input("가동 주차 라벨", value=cfg.get('w4_label','4주'), key=f"pw4lbl_{idx}")
                    cfg['col_val_w3'] = st.selectbox(f"{cfg.get('w3_label','3주')} 실적 컬럼", cols, index=_gi(cfg.get('col_val_w3',''), cols), key=f"pcvalw3_{idx}")
                    st.caption(f"💡 {cfg.get('w3_label','3주')} 실적 기준, {cfg.get('w4_label','4주')} 동일 가동 시 예상 시상금")
                    st.write("📈 구간 설정 (동일 가동 기준금액, 시상금)")
                    wb_tiers = cfg.get('weekly_bridge_tiers', [(500000,3000000),(300000,1500000),(200000,800000),(100000,200000)])
                    ts = "\\n".join([f"{int(t[0])},{int(t[1])}" for t in wb_tiers])
                    ti = st.text_area("엔터로 줄바꿈 (기준금액,시상금)", value=ts, height=120, key=f"pwbtier_{idx}")
                    try:
                        nt = []
                        for line in ti.strip().split('\\n'):
                            if ',' in line:
                                p = line.split(',')
                                nt.append((float(p[0].strip()), float(p[1].strip())))
                        cfg['weekly_bridge_tiers'] = sorted(nt, key=lambda x: x[0], reverse=True)
                    except: st.error("형식 오류")
                else:
                    cfg['col_val'] = st.selectbox("실적 수치 열", cols, index=_gi(cfg.get('col_val',''), cols), key=f"pval_{idx}")''',
    "5. Admin 주차브릿지 설정 필드")

# ═══════════════════════════════════════════
# 5b. 시상금 항목 조건 — 주차브릿지 제외
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                if "2기간" in cfg['type']:
                    cfg['curr_req'] = st.number_input("당월 필수 달성 금액 (합산용)", value=float(cfg.get('curr_req', 100000.0)), step=10000.0, key=f"creq2_{idx}")""",
    
    """                if "주차브릿지" in cfg['type']:
                    pass  # 주차브릿지는 자체 구간 테이블로 시상금 산출
                elif "2기간" in cfg['type']:
                    cfg['curr_req'] = st.number_input("당월 필수 달성 금액 (합산용)", value=float(cfg.get('curr_req', 100000.0)), step=10000.0, key=f"creq2_{idx}")""",
    "5b. 시상금 항목 조건")

# ═══════════════════════════════════════════
# 6. Config import — w3/w4 필드 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                    for c in raw_data:
                        item = {
                            'name': c.get('name', ''),
                            'category': c.get('category', 'weekly'),
                            'type': c.get('type', '구간 시책'),
                            'col_code': c.get('col_code', ''),
                            'col_val': c.get('col_val', ''),
                            'col_val_prev': c.get('col_val_prev', ''),
                            'col_val_curr': c.get('col_val_curr', ''),
                            'curr_req': float(c.get('curr_req', 100000.0)),
                        }""",
    
    """                    for c in raw_data:
                        item = {
                            'name': c.get('name', ''),
                            'category': c.get('category', 'weekly'),
                            'type': c.get('type', '구간 시책'),
                            'col_code': c.get('col_code', ''),
                            'col_val': c.get('col_val', ''),
                            'col_val_prev': c.get('col_val_prev', ''),
                            'col_val_curr': c.get('col_val_curr', ''),
                            'curr_req': float(c.get('curr_req', 100000.0)),
                            'col_val_w3': c.get('col_val_w3', ''),
                            'w3_label': c.get('w3_label', '3주'),
                            'w4_label': c.get('w4_label', '4주'),
                        }""",
    "6. Config import 필드")

# ═══════════════════════════════════════════
# 6b. weekly_bridge_tiers 변환 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                        item['tiers'] = sorted(
                            [(float(t[0]), float(t[1])) for t in raw_tiers],
                            key=lambda x: x[0], reverse=True
                        ) if raw_tiers else []""",
    
    """                        item['tiers'] = sorted(
                            [(float(t[0]), float(t[1])) for t in raw_tiers],
                            key=lambda x: x[0], reverse=True
                        ) if raw_tiers else []
                        raw_wb_tiers = c.get('weekly_bridge_tiers', [])
                        item['weekly_bridge_tiers'] = sorted(
                            [(float(t[0]), float(t[1])) for t in raw_wb_tiers],
                            key=lambda x: x[0], reverse=True
                        ) if raw_wb_tiers else []""",
    "6b. weekly_bridge_tiers 변환")

# ═══════════════════════════════════════════
# 7. render_html_table 시상금 팝업 — 주차브릿지 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                    else:
                        ph += f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;"><span style="color:#555;">{r["name"]}</span><span style="color:#d9232e;font-weight:700;">{pz}</span></div>'
                        if len(r.get('prize_details', [])) > 1:
                            for d in r.get('prize_details', []):
                                ph += f'<div style="display:flex;justify-content:space-between;padding:2px 0 2px 12px;"><span style="color:#aaa;font-size:11px;">· {d["label"]}</span><span style="color:#aaa;font-size:11px;">{d["amount"]:,.0f}원</span></div>'
            if p_cumul:""",
    
    """                    elif r['type'] == '주차브릿지':
                        w3l = r.get('w3_label','3주'); w4l = r.get('w4_label','4주')
                        tier_txt = f"{r.get('tier',0):,.0f}원" if r.get('tier',0) > 0 else "미달성"
                        ph += f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;"><span style="color:#555;">{r["name"]}<br><span style="font-size:10px;color:#888;">({w4l} 동일 가동 시)</span></span><span style="color:#d9232e;font-weight:700;">{pz}</span></div>'
                        ph += f'<div style="display:flex;justify-content:space-between;padding:2px 0 2px 12px;"><span style="color:#888;font-size:11px;">{w3l} 실적 (구간: {tier_txt})</span><span style="color:#888;font-size:11px;">{r.get("val_w3",0):,.0f}원</span></div>'
                        if r.get('shortfall', 0) > 0:
                            ph += f'<div style="padding:2px 0 2px 8px;font-size:10px;color:#888;">🚀 {r["shortfall"]:,.0f}원 더 하면 → {r.get("next_tier_prize",0):,.0f}원</div>'
                    else:
                        ph += f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;"><span style="color:#555;">{r["name"]}</span><span style="color:#d9232e;font-weight:700;">{pz}</span></div>'
                        if len(r.get('prize_details', [])) > 1:
                            for d in r.get('prize_details', []):
                                ph += f'<div style="display:flex;justify-content:space-between;padding:2px 0 2px 12px;"><span style="color:#aaa;font-size:11px;">· {d["label"]}</span><span style="color:#aaa;font-size:11px;">{d["amount"]:,.0f}원</span></div>'
            if p_cumul:""",
    "7. render_html_table 시상금 팝업")

# ═══════════════════════════════════════════
# 8. Config import 미리보기 — 주차브릿지 표시
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                            if '2기간' in c['type']:
                                st.markdown(f"**전월 실적 (구간 매칭):** `{c['col_val_prev']}`")
                                st.markdown(f"**당월 실적 (가동 확인):** `{c['col_val_curr']}`")
                                st.markdown(f"**가동 금액:** {c['curr_req']:,.0f}원")
                                if c['tiers']:
                                    st.markdown("**구간:** " + " / ".join(
                                        f"{int(t[0]):,}원→{int(t[1])}%" for t in c['tiers']
                                    ))
                            elif '1기간' in c['type']:""",
    
    """                            if '2기간' in c['type']:
                                st.markdown(f"**전월 실적 (구간 매칭):** `{c['col_val_prev']}`")
                                st.markdown(f"**당월 실적 (가동 확인):** `{c['col_val_curr']}`")
                                st.markdown(f"**가동 금액:** {c['curr_req']:,.0f}원")
                                if c['tiers']:
                                    st.markdown("**구간:** " + " / ".join(
                                        f"{int(t[0]):,}원→{int(t[1])}%" for t in c['tiers']
                                    ))
                            elif '주차브릿지' in c['type']:
                                st.markdown(f"**{c.get('w3_label','3주')} 실적:** `{c.get('col_val_w3','')}`")
                                st.markdown(f"**{c.get('w4_label','4주')} 동일 가동 시 예상 시상금 산출**")
                                if c.get('weekly_bridge_tiers'):
                                    st.markdown("**구간:** " + " / ".join(
                                        f"{int(t[0]):,}원→{int(t[1]):,}원" for t in c['weekly_bridge_tiers']
                                    ))
                            elif '1기간' in c['type']:""",
    "8. Config import 미리보기")

# ═══════════════════════════════════════════
# 9. Config import 컬럼 검증 — col_val_w3 추가
# ═══════════════════════════════════════════
src = safe_replace(src,
    """                                for key in ['col_code', 'col_val', 'col_val_prev', 'col_val_curr']:""",
    """                                for key in ['col_code', 'col_val', 'col_val_prev', 'col_val_curr', 'col_val_w3']:""",
    "9. 컬럼 검증")

# ═══════════════════════════════════════════
# 저장
# ═══════════════════════════════════════════
if changes == 0:
    print("\n⚠️ 변경 사항이 없습니다. 이미 적용되었거나 파일이 다를 수 있습니다.")
else:
    # 백업
    backup = TARGET + ".backup"
    if not os.path.exists(backup):
        shutil.copy2(TARGET, backup)
        print(f"\n💾 원본 백업: {backup}")
    
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(src)
    
    print(f"\n✅ 완료! {changes}개 변경 적용됨 → {TARGET}")
    print("   주차브릿지 시책이 config.json 가져오기에서 정상 인식됩니다.")
