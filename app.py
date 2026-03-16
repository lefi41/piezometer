import os
import json
from datetime import datetime
import streamlit as st

BASE_DIR = "Sites_Data"
os.makedirs(BASE_DIR, exist_ok=True)

INFO_FIELDS = [
    ("관리번호:", "mng_no"),
    ("수위계 S/N:", "serial_no"),
    ("천공심도(m):", "bore_depth"),
    ("수위(m):", "water_level"),
    ("설치위치(m):", "install_pos"),
]

BASE_STAGES = ["설치 전 측정치", "설치 후 측정치", "초기치"]


def list_sites():
    return sorted(
        [
            d for d in os.listdir(BASE_DIR)
            if os.path.isdir(os.path.join(BASE_DIR, d))
        ]
    )


def list_records(site):
    if not site:
        return []
    site_path = os.path.join(BASE_DIR, site)
    if not os.path.isdir(site_path):
        return []
    return sorted(
        [f[:-5] for f in os.listdir(site_path) if f.endswith(".json")]
    )


def ensure_state():
    defaults = {
        "selected_site": "",
        "new_site_name": "",
        "spec_lgf": "",
        "current_lgf_field": 0.0,
        "match_rate": None,
        "calib_count": 5,
        "record_to_manage": "",
        "delete_confirm": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    for _, state_key in INFO_FIELDS:
        st.session_state.setdefault(f"info_{state_key}", "")

    for stage in BASE_STAGES:
        st.session_state.setdefault(f"base_digits_{stage}", "")
        st.session_state.setdefault(f"base_temp_{stage}", "")

    for i in range(100):
        st.session_state.setdefault(f"calib_depth_{i}", "")
        st.session_state.setdefault(f"calib_digits_{i}", "")


def clear_all():
    for _, state_key in INFO_FIELDS:
        st.session_state[f"info_{state_key}"] = ""

    st.session_state["spec_lgf"] = ""
    st.session_state["current_lgf_field"] = 0.0
    st.session_state["match_rate"] = None

    for stage in BASE_STAGES:
        st.session_state[f"base_digits_{stage}"] = ""
        st.session_state[f"base_temp_{stage}"] = ""

    for i in range(100):
        st.session_state[f"calib_depth_{i}"] = ""
        st.session_state[f"calib_digits_{i}"] = ""

    st.session_state["calib_count"] = 5


def add_site(site_name):
    site_name = site_name.strip()
    if not site_name:
        st.warning("현장명을 입력하세요.")
        return

    path = os.path.join(BASE_DIR, site_name)
    if not os.path.exists(path):
        os.makedirs(path)

    st.session_state["selected_site"] = site_name
    st.session_state["new_site_name"] = ""
    st.success(f"'{site_name}' 현장이 추가되었습니다.")


def collect_calib_rows():
    rows = []
    for i in range(st.session_state["calib_count"]):
        depth = st.session_state.get(f"calib_depth_{i}", "").strip()
        digits = st.session_state.get(f"calib_digits_{i}", "").strip()
        rows.append({"depth": depth, "digits": digits})
    return rows


def calculate_lgf():
    try:
        depths, digits = [], []

        for i in range(st.session_state["calib_count"]):
            depth_raw = st.session_state.get(f"calib_depth_{i}", "").strip()
            digits_raw = st.session_state.get(f"calib_digits_{i}", "").strip()

            if depth_raw and digits_raw:
                depths.append(float(depth_raw))
                digits.append(float(digits_raw))
            elif depth_raw or digits_raw:
                return False, f"{i + 1}번째 행은 수심과 Digits를 모두 입력해야 합니다."

        if len(depths) < 2:
            return False, "캘리브레이션 데이터는 2개 이상 입력해야 합니다."

        base_depth, base_digits = depths[0], digits[0]
        lgfs = []

        for i in range(1, len(depths)):
            dp = (depths[i] - base_depth) * 0.1
            dd = digits[i] - base_digits
            if dd != 0:
                lgfs.append(dp / dd)

        if not lgfs:
            return False, "Digits 차이가 0이어서 L.G.F를 계산할 수 없습니다."

        field_lgf = sum(lgfs) / len(lgfs)
        st.session_state["current_lgf_field"] = field_lgf
        st.session_state["match_rate"] = None

        spec_raw = st.session_state.get("spec_lgf", "").strip()
        if spec_raw:
            spec_lgf = float(spec_raw)
            if max(abs(spec_lgf), abs(field_lgf)) == 0:
                match_rate = 100.0
            else:
                match_rate = (
                    min(abs(spec_lgf), abs(field_lgf))
                    / max(abs(spec_lgf), abs(field_lgf))
                ) * 100
            st.session_state["match_rate"] = match_rate

        return True, "L.G.F 계산이 완료되었습니다."

    except ValueError:
        return False, "숫자 형식을 확인하세요."


def save_data():
    site = st.session_state.get("selected_site", "").strip()
    mng_no = st.session_state.get("info_mng_no", "").strip()

    if not site or not mng_no:
        return False, "현장명과 관리번호는 필수입니다."

    site_path = os.path.join(BASE_DIR, site)
    os.makedirs(site_path, exist_ok=True)

    data = {
        "info": {
            label: st.session_state.get(f"info_{state_key}", "")
            for label, state_key in INFO_FIELDS
        },
        "spec_lgf": st.session_state.get("spec_lgf", ""),
        "base": {
            stage: {
                "Digits": st.session_state.get(f"base_digits_{stage}", ""),
                "Temp": st.session_state.get(f"base_temp_{stage}", ""),
            }
            for stage in BASE_STAGES
        },
        "calib": collect_calib_rows(),
        "field_lgf": st.session_state.get("current_lgf_field", 0.0),
    }

    file_path = os.path.join(site_path, f"{mng_no}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return True, f"{mng_no} 데이터가 저장되었습니다."


def load_data(site, record_name):
    if not site or not record_name:
        return False, "불러올 데이터를 선택하세요."

    file_path = os.path.join(BASE_DIR, site, f"{record_name}.json")
    if not os.path.exists(file_path):
        return False, "선택한 데이터 파일이 없습니다."

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    clear_all()
    st.session_state["selected_site"] = site

    info = data.get("info", {})
    label_to_state = {label: state_key for label, state_key in INFO_FIELDS}
    for label, value in info.items():
        state_key = label_to_state.get(label)
        if state_key:
            st.session_state[f"info_{state_key}"] = value

    st.session_state["spec_lgf"] = data.get("spec_lgf", "")

    base = data.get("base", {})
    for stage in BASE_STAGES:
        stage_data = base.get(stage, {})
        st.session_state[f"base_digits_{stage}"] = stage_data.get("Digits", "")
        st.session_state[f"base_temp_{stage}"] = stage_data.get("Temp", "")

    calib = data.get("calib", [])
    st.session_state["calib_count"] = max(5, len(calib))
    for i, row in enumerate(calib):
        st.session_state[f"calib_depth_{i}"] = row.get("depth", "")
        st.session_state[f"calib_digits_{i}"] = row.get("digits", "")

    field_lgf = data.get("field_lgf", 0.0)
    try:
        st.session_state["current_lgf_field"] = float(field_lgf)
    except (ValueError, TypeError):
        st.session_state["current_lgf_field"] = 0.0

    st.session_state["match_rate"] = None
    spec_raw = str(st.session_state.get("spec_lgf", "")).strip()
    if spec_raw:
        try:
            spec_lgf = float(spec_raw)
            field_lgf = float(st.session_state["current_lgf_field"])
            if max(abs(spec_lgf), abs(field_lgf)) == 0:
                st.session_state["match_rate"] = 100.0
            else:
                st.session_state["match_rate"] = (
                    min(abs(spec_lgf), abs(field_lgf))
                    / max(abs(spec_lgf), abs(field_lgf))
                ) * 100
        except ValueError:
            st.session_state["match_rate"] = None

    return True, f"{record_name} 데이터를 불러왔습니다."


def delete_data(site, record_name):
    if not site or not record_name:
        return False, "삭제할 데이터를 선택하세요."

    file_path = os.path.join(BASE_DIR, site, f"{record_name}.json")
    if not os.path.exists(file_path):
        return False, "선택한 데이터 파일이 없습니다."

    os.remove(file_path)
    return True, f"{record_name} 데이터가 삭제되었습니다."


def build_export_text(site):
    if not site:
        return None, None

    site_path = os.path.join(BASE_DIR, site)
    if not os.path.isdir(site_path):
        return None, None

    files = sorted([f for f in os.listdir(site_path) if f.endswith(".json")])
    if not files:
        return None, None

    lines = [f"=== {site} 지하수위계 일괄 데이터 ===", ""]

    for file_name in files:
        with open(os.path.join(site_path, file_name), "r", encoding="utf-8") as f:
            data = json.load(f)

        info = data.get("info", {})
        field_lgf = data.get("field_lgf", 0)
        try:
            field_lgf_text = f"{float(field_lgf):.7f}"
        except (ValueError, TypeError):
            field_lgf_text = "0.0000000"

        lines.append(f"■ 관리번호: {info.get('관리번호:', 'N/A')}")
        lines.append(
            f"S/N: {info.get('수위계 S/N:', '')} | 현장LGF: {field_lgf_text}"
        )
        lines.append(f"성적서LGF: {data.get('spec_lgf', '미입력')}")
        lines.append("------------------------------------------")

    content = "\n".join(lines)
    now = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{site}_일괄데이터_{now}.txt"
    return filename, content


def render_header():
    st.markdown(
        """
        <div style="
            background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
            padding: 18px 24px;
            border-radius: 14px;
            margin-bottom: 20px;
        ">
            <h2 style="color: white; margin: 0;">지하수위계 현장 캘리브레이션 시스템</h2>
            <p style="color: #CBD5E1; margin: 6px 0 0 0;">Field Piezometer Pro - Streamlit Web Edition</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Field Piezometer Pro",
        page_icon="📐",
        layout="wide",
    )

    ensure_state()
    render_header()

    st.subheader("1. 현장 및 관리")
    sites = list_sites()
    site_options = [""] + sites

    if st.session_state["selected_site"] not in site_options:
        st.session_state["selected_site"] = site_options[0]

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.selectbox(
            "현장 선택",
            options=site_options,
            key="selected_site",
            format_func=lambda x: "현장을 선택하세요" if x == "" else x,
        )

    with col2:
        st.text_input("새 현장명", key="new_site_name", placeholder="예: OO현장 A구간")

    with col3:
        st.write("")
        st.write("")
        if st.button("+ 새 현장 추가", use_container_width=True):
            add_site(st.session_state.get("new_site_name", ""))
            st.rerun()

    selected_site = st.session_state.get("selected_site", "")
    export_filename, export_text = build_export_text(selected_site)
    if export_text:
        st.download_button(
            "TXT 내보내기",
            data=export_text.encode("utf-8"),
            file_name=export_filename,
            mime="text/plain",
        )

    st.divider()

    st.subheader("2. 수위계 제원 정보")
    cols = st.columns(2)
    for i, (label, state_key) in enumerate(INFO_FIELDS):
        with cols[i % 2]:
            st.text_input(label, key=f"info_{state_key}")

    st.divider()

    st.subheader("3. 성적서(Spec) 정보 및 비교")
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.text_input("성적서 L.G.F", key="spec_lgf", placeholder="예: 0.0001234")
    with col2:
        match_rate = st.session_state.get("match_rate")
        if match_rate is None:
            st.info("성적서 대비 일치율: - %")
        else:
            if match_rate >= 90:
                st.success(f"성적서 대비 일치율: {match_rate:.2f} %")
            else:
                st.error(f"성적서 대비 일치율: {match_rate:.2f} %")

    st.divider()

    st.subheader("4. 설치 단계별 V/W 측정값")
    header_cols = st.columns([1.2, 1, 1])
    header_cols[0].markdown("**구분**")
    header_cols[1].markdown("**Digits (Hz²/1000)**")
    header_cols[2].markdown("**온도 (℃)**")

    for stage in BASE_STAGES:
        row_cols = st.columns([1.2, 1, 1])
        row_cols[0].write(stage)
        row_cols[1].text_input(
            f"{stage}_digits",
            key=f"base_digits_{stage}",
            label_visibility="collapsed",
        )
        row_cols[2].text_input(
            f"{stage}_temp",
            key=f"base_temp_{stage}",
            label_visibility="collapsed",
        )

    st.divider()

    st.subheader("5. 현장 L.G.F 도출 측정 (1m 간격)")
    btn_cols = st.columns([1, 1, 4])

    with btn_cols[0]:
        if st.button("행 추가 +", use_container_width=True):
            st.session_state["calib_count"] += 1
            st.rerun()

    with btn_cols[1]:
        if st.button("행 삭제 -", use_container_width=True):
            if st.session_state["calib_count"] > 1:
                idx = st.session_state["calib_count"] - 1
                st.session_state[f"calib_depth_{idx}"] = ""
                st.session_state[f"calib_digits_{idx}"] = ""
                st.session_state["calib_count"] -= 1
            st.rerun()

    head_cols = st.columns([0.5, 1, 1])
    head_cols[0].markdown("**No.**")
    head_cols[1].markdown("**수심(m)**")
    head_cols[2].markdown("**측정 Digits**")

    for i in range(st.session_state["calib_count"]):
        row_cols = st.columns([0.5, 1, 1])
        row_cols[0].write(i + 1)
        row_cols[1].text_input(
            f"depth_{i}",
            key=f"calib_depth_{i}",
            label_visibility="collapsed",
            placeholder="예: 1.0",
        )
        row_cols[2].text_input(
            f"digits_{i}",
            key=f"calib_digits_{i}",
            label_visibility="collapsed",
            placeholder="예: 12345.67",
        )

    st.divider()

    st.subheader("6. 계산 결과")
    if st.button("L.G.F 계산 및 비교 실행", use_container_width=True, type="primary"):
        ok, msg = calculate_lgf()
        if ok:
            st.success(msg)
        else:
            st.warning(msg)

    current_lgf = st.session_state.get("current_lgf_field", 0.0)
    if current_lgf:
        st.metric("현장 계산 L.G.F", f"{current_lgf:.7f}")
    else:
        st.metric("현장 계산 L.G.F", "-")

    st.divider()

    st.subheader("7. 저장 / 불러오기 / 삭제")
    action_cols = st.columns([1, 1])

    with action_cols[0]:
        if st.button("데이터 저장", use_container_width=True):
            ok, msg = save_data()
            if ok:
                st.success(msg)
            else:
                st.warning(msg)

    with action_cols[1]:
        if st.button("초기화", use_container_width=True):
            clear_all()
            st.success("입력값을 초기화했습니다.")
            st.rerun()

    records = list_records(selected_site)
    record_options = [""] + records
    if st.session_state["record_to_manage"] not in record_options:
        st.session_state["record_to_manage"] = ""

    col1, col2 = st.columns([2, 1])

    with col1:
        st.selectbox(
            "저장된 데이터 목록",
            options=record_options,
            key="record_to_manage",
            format_func=lambda x: "데이터를 선택하세요" if x == "" else x,
        )

    with col2:
        st.checkbox("삭제 확인", key="delete_confirm")

    manage_cols = st.columns([1, 1])

    with manage_cols[0]:
        if st.button("데이터 불러오기", use_container_width=True):
            ok, msg = load_data(selected_site, st.session_state.get("record_to_manage", ""))
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(msg)

    with manage_cols[1]:
        if st.button("데이터 삭제", use_container_width=True):
            if not st.session_state.get("delete_confirm", False):
                st.warning("삭제 확인을 체크하세요.")
            else:
                ok, msg = delete_data(selected_site, st.session_state.get("record_to_manage", ""))
                if ok:
                    st.session_state["record_to_manage"] = ""
                    st.session_state["delete_confirm"] = False
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning(msg)

    st.caption("기존 Tkinter 버전과 동일한 JSON 저장 형식을 유지하므로 기존 데이터도 그대로 읽을 수 있습니다.")


if __name__ == "__main__":
    main()
