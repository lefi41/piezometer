import streamlit as st
import pandas as pd
import json
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="수위계 Pro", layout="centered")

# CSS로 기존 앱 느낌 내기
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3em; border-radius: 10px; }
    .main { background-color: #F5F7FA; }
    </style>
    """, unsafe_allow_html=True)

st.title("📟 지하수위계 캘리브레이션")

# --- 1. 현장 및 관리 (기존 카드 1) ---
with st.container():
    st.subheader("📍 현장 및 관리")
    site_name = st.text_input("현장명 입력", "Default_Site")
    
    # 웹은 로컬 폴더 생성이 제한적이므로 세션 상태를 활용해 목록 관리 흉내
    if 'history' not in st.session_state:
        st.session_state.history = []

# --- 2. 수위계 제원 정보 (기존 카드 2) ---
with st.expander("🏗️ 수위계 제원 정보", expanded=True):
    col1, col2 = st.columns(2)
    mng_no = col1.text_input("관리번호", placeholder="예: GW-1")
    sn = col2.text_input("수위계 S/N")
    
    col3, col4, col5 = st.columns(3)
    depth_total = col3.text_input("천공심도(m)")
    water_level = col4.text_input("수위(m)")
    install_pos = col5.text_input("설치위치(m)")

# --- 3. 성적서 LGF 및 비교 (기존 카드 3) ---
with st.container():
    st.subheader("📑 성적서 정보 및 비교")
    spec_lgf = st.number_input("성적서 L.G.F 입력", format="%.7f", step=0.0000001)

# --- 4. 단계별 측정값 (기존 카드 4) ---
with st.expander("🔍 설치 단계별 V/W 측정값"):
    stages = ["설치 전 측정치", "설치 후 측정치", "초기치"]
    base_data = {}
    for stage in stages:
        st.write(f"**{stage}**")
        c1, c2 = st.columns(2)
        dig = c1.number_input("Digits", key=f"d_{stage}", format="%.1f")
        temp = c2.number_input("온도(℃)", key=f"t_{stage}", format="%.1f")
        base_data[stage] = {"Digits": dig, "Temp": temp}

# --- 5. 현장 캘리브레이션 (기존 카드 5: 행 추가/삭제 기능) ---
st.subheader("⚖️ 현장 L.G.F 도출 (1m 간격)")

# 세션 상태를 이용해 '행 추가/삭제' 구현
if 'rows' not in st.session_state:
    st.session_state.rows = 5

c_btn1, c_btn2 = st.columns(2)
if c_btn1.button("행 추가 +"):
    st.session_state.rows += 1
if c_btn2.button("행 삭제 -") and st.session_state.rows > 1:
    st.session_state.rows -= 1

calib_list = []
for i in range(st.session_state.rows):
    cols = st.columns([1, 1.5])
    d = cols[0].number_input(f"수심 {i+1}(m)", key=f"depth_{i}", step=1.0)
    v = cols[1].number_input(f"Digits {i+1}", key=f"val_{i}", format="%.1f")
    calib_list.append({"depth": d, "digits": v})

# --- 6. 결과 계산 및 저장 ---
st.divider()

if st.button("🚀 L.G.F 계산 및 비교 실행", type="primary"):
    df = pd.DataFrame(calib_list)
    try:
        base_d, base_v = df.iloc[0]['depth'], df.iloc[0]['digits']
        lgfs = []
        for i in range(1, len(df)):
            dp = (df.iloc[i]['depth'] - base_d) * 0.1
            dv = df.iloc[i]['digits'] - base_v
            if dv != 0: lgfs.append(dp / dv)
        
        if lgfs:
            res_lgf = sum(lgfs) / len(lgfs)
            st.session_state.current_lgf = res_lgf
            st.metric("현장 계산 L.G.F", f"{res_lgf:.7f}")
            
            if spec_lgf != 0:
                match_rate = (min(abs(spec_lgf), abs(res_lgf)) / max(abs(spec_lgf), abs(res_lgf))) * 100
                if match_rate >= 90:
                    st.success(f"✅ 성적서 대비 일치율: {match_rate:.2f}%")
                else:
                    st.error(f"⚠️ 성적서 대비 일치율: {match_rate:.2f}% (확인 필요)")
    except Exception as e:
        st.error("데이터 계산 중 오류가 발생했습니다.")

# --- 7. 하단 버튼 (저장 및 내보내기) ---
col_f1, col_f2 = st.columns(2)

# JSON 데이터 생성 (기존 save_data 대응)
save_obj = {
    "site": site_name,
    "info": {"관리번호": mng_no, "SN": sn},
    "spec_lgf": spec_lgf,
    "base": base_data,
    "calib": calib_list,
    "field_lgf": st.session_state.get('current_lgf', 0)
}
json_str = json.dumps(save_obj, indent=4, ensure_ascii=False)

col_f1.download_button("💾 데이터 저장 (JSON)", data=json_str, file_name=f"{mng_no}.json")
col_f2.button("🔄 초기화", on_click=lambda: st.runtime.scriptrunner.script_run_context.add_script_run_request())
