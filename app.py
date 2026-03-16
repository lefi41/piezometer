import streamlit as st
import pandas as pd
import json
from datetime import datetime

# 1. 초기 세션 상태 설정 (Tkinter의 __init__ 역할)
if 'rows' not in st.session_state:
    st.session_state.rows = 5
if 'current_data' not in st.session_state:
    st.session_state.current_data = {}

st.set_page_config(page_title="Field Piezometer Pro", layout="centered")

# 디자인 커스텀
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📟 지하수위계 현장 캘리브레이션")

# --- [카드 1: 현장 및 관리] ---
st.subheader("📍 현장 및 관리")
with st.container():
    col_s1, col_s2 = st.columns([2, 1])
    site_name = col_s1.text_input("현장명", value="Default_Site")
    
    # 불러오기 기능 (기존 load_data_dialog 대응)
    uploaded_file = st.file_report = st.file_uploader("📂 기존 데이터 불러오기 (JSON)", type="json")
    if uploaded_file is not None:
        load_data = json.load(uploaded_file)
        st.session_state.current_data = load_data
        st.success("데이터를 불러왔습니다!")

# --- [카드 2: 수위계 제원 정보] ---
with st.expander("🏗️ 수위계 제원 정보", expanded=True):
    c1, c2 = st.columns(2)
    mng_no = c1.text_input("관리번호", value=st.session_state.current_data.get("info", {}).get("관리번호", ""))
    sn = c2.text_input("수위계 S/N", value=st.session_state.current_data.get("info", {}).get("SN", ""))
    
    c3, c4, c5 = st.columns(3)
    depth_t = c3.text_input("천공심도(m)", value=st.session_state.current_data.get("info", {}).get("depth_t", ""))
    water_l = c4.text_input("수위(m)", value=st.session_state.current_data.get("info", {}).get("water_l", ""))
    inst_p = c5.text_input("설치위치(m)", value=st.session_state.current_data.get("info", {}).get("inst_p", ""))

# --- [카드 3: 성적서 정보 및 비교] ---
with st.container():
    st.subheader("📑 성적서 정보 및 비교")
    spec_lgf = st.number_input("성적서 L.G.F", format="%.7f", value=float(st.session_state.current_data.get("spec_lgf", 0.0)))

# --- [카드 4: 단계별 측정값] ---
with st.expander("🔍 설치 단계별 V/W 측정값"):
    stages = ["설치 전 측정치", "설치 후 측정치", "초기치"]
    base_inputs = {}
    for stage in stages:
        st.write(f"**{stage}**")
        sc1, sc2 = st.columns(2)
        d_val = st.session_state.current_data.get("base", {}).get(stage, {}).get("Digits", 0.0)
        t_val = st.session_state.current_data.get("base", {}).get(stage, {}).get("Temp", 0.0)
        
        dig = sc1.number_input("Digits", key=f"d_{stage}", value=float(d_val))
        temp = sc2.number_input("온도(℃)", key=f"t_{stage}", value=float(t_val))
        base_inputs[stage] = {"Digits": dig, "Temp": temp}

# --- [카드 5: 현장 캘리브레이션 (행 추가/삭제)] ---
st.subheader("⚖️ 현장 L.G.F 도출 (1m 간격)")
col_btn1, col_btn2 = st.columns(2)
if col_btn1.button("행 추가 +"): st.session_state.rows += 1
if col_btn2.button("행 삭제 -") and st.session_state.rows > 1: st.session_state.rows -= 1

calib_rows = []
for i in range(st.session_state.rows):
    cols = st.columns([1, 1.5])
    # 기존 데이터가 있으면 채워넣기
    saved_calib = st.session_state.current_data.get("calib", [])
    d_init = float(saved_calib[i]['depth']) if i < len(saved_calib) else 0.0
    v_init = float(saved_calib[i]['digits']) if i < len(saved_calib) else 0.0
    
    d = cols[0].number_input(f"수심 {i+1}", key=f"depth_{i}", value=d_init)
    v = cols[1].number_input(f"Digits {i+1}", key=f"val_{i}", value=v_init)
    calib_rows.append({"depth": d, "digits": v})

# --- [6. 결과 및 저장 기능] ---
st.divider()
if st.button("🚀 L.G.F 계산 및 비교 실행", type="primary"):
    try:
        df = pd.DataFrame(calib_rows)
        base_d, base_v = df.iloc[0]['depth'], df.iloc[0]['digits']
        lgfs = []
        for i in range(1, len(df)):
            dp = (df.iloc[i]['depth'] - base_d) * 0.1
            dv = df.iloc[i]['digits'] - base_v
            if dv != 0: lgfs.append(dp / dv)
        
        if lgfs:
            res_lgf = sum(lgfs) / len(lgfs)
            st.session_state.last_calc = res_lgf
            st.metric("현장 계산 L.G.F", f"{res_lgf:.7f}")
            
            if spec_lgf != 0:
                match_rate = (min(abs(spec_lgf), abs(res_lgf)) / max(abs(spec_lgf), abs(res_lgf))) * 100
                if match_rate >= 90: st.success(f"✅ 일치율: {match_rate:.2f}%")
                else: st.error(f"⚠️ 일치율: {match_rate:.2f}% (확인 필요)")
    except: st.error("입력값을 확인하세요.")

# --- [7. 하단 액션 버튼 (저장/내보내기)] ---
st.write("---")
save_data = {
    "info": {"관리번호": mng_no, "SN": sn, "depth_t": depth_total, "water_l": water_level, "inst_p": install_pos},
    "spec_lgf": spec_lgf,
    "base": base_inputs,
    "calib": calib_rows,
    "field_lgf": st.session_state.get('last_calc', 0)
}
json_out = json.dumps(save_data, indent=4, ensure_ascii=False)

c_f1, c_f2, c_f3 = st.columns(3)
c_f1.download_button("💾 JSON 저장", data=json_out, file_name=f"{mng_no}.json", use_container_width=True)
c_f2.download_button("📝 TXT 내보내기", data=f"현장: {site_name}\n관리번호: {mng_no}\nLGF: {st.session_state.get('last_calc', 0)}", file_name=f"{mng_no}.txt", use_container_width=True)
if c_f3.button("🔄 초기화"):
    st.session_state.current_data = {}
    st.rerun()
