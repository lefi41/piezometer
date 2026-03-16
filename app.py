import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 페이지 설정 (아이폰 최적화)
st.set_page_config(page_title="지하수위계 캘리브레이터", layout="centered")

st.title("📱 현장 수위계 캘리브레이터")

# 1. 현장 관리
st.subheader("📍 현장 관리")
site_name = st.text_input("현장명 입력", placeholder="예: OO대교 현장")

# 2. 제원 입력
with st.expander("📝 수위계 제원 정보", expanded=True):
    col1, col2 = st.columns(2)
    mng_no = col1.text_input("관리번호")
    sn = col2.text_input("S/N")
    spec_lgf = st.number_input("성적서 L.G.F", format="%.7f")

# 3. 측정 데이터 (기본 Digits)
with st.expander("🔍 설치 단계별 측정값"):
    stages = ["설치 전", "설치 후", "초기치"]
    base_data = {}
    for stage in stages:
        c1, c2 = st.columns(2)
        dig = c1.number_input(f"{stage} Digits", key=f"d_{stage}")
        temp = c2.number_input(f"{stage} 온도(℃)", key=f"t_{stage}")
        base_data[stage] = {"Digits": dig, "Temp": temp}

# 4. 현장 캘리브레이션 (표 형식 입력)
st.subheader("⚖️ 현장 L.G.F 도출")
num_rows = st.number_input("측정 횟수", min_value=2, max_value=20, value=5)

calib_data = []
for i in range(int(num_rows)):
    c1, c2 = st.columns(2)
    d = c1.number_input(f"{i+1}번 수심(m)", key=f"depth_{i}")
    v = c2.number_input(f"{i+1}번 Digits", key=f"val_{i}")
    calib_data.append({"depth": d, "digits": v})

# 5. 계산 및 결과
if st.button("계산 및 비교 실행", use_container_width=True):
    df = pd.DataFrame(calib_data)
    # LGF 계산 로직
    base_d = df.iloc[0]['depth']
    base_v = df.iloc[0]['digits']
    
    lgfs = []
    for i in range(1, len(df)):
        dp = (df.iloc[i]['depth'] - base_d) * 0.1
        dv = df.iloc[i]['digits'] - base_v
        if dv != 0:
            lgfs.append(dp / dv)
    
    if lgfs:
        field_lgf = sum(lgfs) / len(lgfs)
        st.metric("현장 계산 L.G.F", f"{field_lgf:.7f}")
        
        if spec_lgf != 0:
            match_rate = (min(abs(spec_lgf), abs(field_lgf)) / max(abs(spec_lgf), abs(field_lgf))) * 100
            color = "normal" if match_rate >= 90 else "inverse"
            st.write(f"### 성적서 대비 일치율: **{match_rate:.2f}%**")
            if match_rate < 90:
                st.error("⚠️ 일치율이 낮습니다. 센서 상태를 확인하세요.")
            else:
                st.success("✅ 성적서와 일치합니다.")

# 6. 내보내기 (TXT 다운로드)
st.subheader("📤 데이터 내보내기")
if st.button("TXT 파일 생성", use_container_width=True):
    report = f"현장명: {site_name}\n관리번호: {mng_no}\nS/N: {sn}\n"
    report += f"성적서 LGF: {spec_lgf}\n"
    report += f"계산일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    st.download_button(
        label="TXT 파일 다운로드",
        data=report,
        file_name=f"{mng_no}_report.txt",
        mime="text/plain",
        use_container_width=True
    )