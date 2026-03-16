import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

APP_TITLE = "지하수위계 현장 캘리브레이션 시스템"
BASE_DIR = Path("Sites_Data")
BASE_DIR.mkdir(exist_ok=True)

INFO_FIELDS = [
    ("관리번호:", "mng_no"),
    ("수위계 S/N:", "serial_no"),
    ("천공심도(m):", "bore_depth"),
    ("수위(m):", "water_level"),
    ("설치위치(m):", "install_pos"),
]

BASE_STAGES = ["설치 전 측정치", "설치 후 측정치", "초기치"]


def init_state():
    defaults = {
        "selected_site": "",
        "new_site_name": "",
        "spec_lgf": "",
        "current_lgf_field": None,
        "match_rate": None,
        "calib_count": 5,
        "record_to_manage": "",
        "delete_confirm": False,
        "cloud_notice_closed": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    for _, key in INFO_FIELDS:
        st.session_state.setdefault(f"info_{key}", "")

    for stage in BASE_STAGES:
        st.session_state.setdefault(f"base_digits_{stage}", "")
        st.session_state.setdefault(f"base_temp_{stage}", "")

    for i in range(100):
        st.session_state.setdefault(f"calib_depth_{i}", "")
        st.session_state.setdefault(f"calib_digits_{i}", "")


def list_sites():
    return sorted([p.name for p in BASE_DIR.iterdir() if p.is_dir()])


def ensure_site_dir(site: str) -> Path:
    path = BASE_DIR / site
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_records(site: str):
    if not site:
        return []
    site_path = BASE_DIR / site
    if not site_path.exists():
        return []
    return sorted([p.stem for p in site_path.glob("*.json")])


def add_site(site_name: str):
    site_name = site_name.strip()
    if not site_name:
        return False, "현장명을 입력하세요."
    ensure_site_dir(site_name)
    st.session_state["selected_site"] = site_name
    st.session_state["new_site_name"] = ""
    return True, f"'{site_name}' 현장이 추가되었습니다."


def clear_inputs():
    for _, key in INFO_FIELDS:
        st.session_state[f"info_{key}"] = ""

    st.session_state["spec_lgf"] = ""
    st.session_state["current_lgf_field"] = None
    st.session_state["match_rate"] = None

    for stage in BASE_STAGES:
        st.session_state[f"base_digits_{stage}"] = ""
        st.session_state[f"base_temp_{stage}"] = ""

    for i in range(100):
        st.session_state[f"calib_depth_{i}"] = ""
        st.session_state[f"calib_digits_{i}"] = ""

    st.session_state["calib_count"] = 5


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
                return False, f"{i + 1}번째 행은 수심과 측정 Digits를 모두 입력해야 합니다."

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
            return False, "Digits 차이가 모두 0이어서 L.G.F를 계산할 수 없습니다."

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


def build_payload():
    return {
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
        "field_lgf": st.session_state.get("current_lgf_field", None),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_data():
    site = st.session_state.get("selected_site", "").strip()
    mng_no = st.session_state.get("info_mng_no", "").strip()
    if not site or not mng_no:
        return False, "현장명과 관리번호는 필수입니다."

    site_path = ensure_site_dir(site)
    file_path = site_path / f"{mng_no}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(build_payload(), f, indent=4, ensure_ascii=False)

    return True, f"{mng_no} 데이터가 저장되었습니다."


def load_data(site: str, record_name: str):
    if not site or not record_name:
        return False, "불러올 데이터를 선택하세요."

    file_path = BASE_DIR / site / f"{record_name}.json"
    if not file_path.exists():
        return False, "선택한 데이터 파일이 없습니다."

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    clear_inputs()
    st.session_state["selected_site"] = site

    label_to_key = {label: key for label, key in INFO_FIELDS}
    for label, value in data.get("info", {}).items():
        state_key = label_to_key.get(label)
        if state_key:
            st.session_state[f"info_{state_key}"] = value

    st.session_state["spec_lgf"] = str(data.get("spec_lgf", ""))

    base = data.get("base", {})
    for stage in BASE_STAGES:
        stage_data = base.get(stage, {})
        st.session_state[f"base_digits_{stage}"] = str(stage_data.get("Digits", ""))
        st.session_state[f"base_temp_{stage}"] = str(stage_data.get("Temp", ""))

    calib = data.get("calib", [])
    st.session_state["calib_count"] = max(5, len(calib))
    for i, row in enumerate(calib):
        st.session_state[f"calib_depth_{i}"] = str(row.get("depth", ""))
        st.session_state[f"calib_digits_{i}"] = str(row.get("digits", ""))

    field_lgf = data.get("field_lgf", None)
    st.session_state["current_lgf_field"] = float(field_lgf) if field_lgf not in (None, "") else None

    st.session_state["match_rate"] = None
    spec_raw = str(st.session_state.get("spec_lgf", "")).strip()
    if spec_raw and st.session_state["current_lgf_field"] is not None:
        try:
            spec_lgf = float(spec_raw)
            field_val = float(st.session_state["current_lgf_field"])
            if max(abs(spec_lgf), abs(field_val)) == 0:
                st.session_state["match_rate"] = 100.0
            else:
                st.session_state["match_rate"] = (
                    min(abs(spec_lgf), abs(field_val)) / max(abs(spec_lgf), abs(field_val))
                ) * 100
        except ValueError:
            pass

    return True, f"{record_name} 데이터를 불러왔습니다."


def delete_data(site: str, record_name: str):
    if not site or not record_name:
        return False, "삭제할 데이터를 선택하세요."

    file_path = BASE_DIR / site / f"{record_name}.json"
    if not file_path.exists():
        return False, "선택한 데이터 파일이 없습니다."

    file_path.unlink()
    return True, f"{record_name} 데이터가 삭제되었습니다."


def build_site_txt(site: str):
    if not site:
        return None, None
    site_path = BASE_DIR / site
    if not site_path.exists():
        return None, None

    files = sorted(site_path.glob("*.json"))
    if not files:
        return None, None

    lines = [f"=== {site} 지하수위계 일괄 데이터 ===", ""]
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        info = data.get("info", {})
        field_lgf = data.get("field_lgf", None)
        field_text = f"{float(field_lgf):.7f}" if field_lgf not in (None, "") else "-"
        lines.append(f"■ 관리번호: {info.get('관리번호:', 'N/A')}")
        lines.append(f"S/N: {info.get('수위계 S/N:', '')} | 현장LGF: {field_text}")
        lines.append(f"성적서LGF: {data.get('spec_lgf', '미입력')}")
        lines.append("------------------------------------------")

    now = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{site}_일괄데이터_{now}.txt", "\n".join(lines)


def build_backup_zip(site: str | None = None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if site:
            target_sites = [site]
        else:
            target_sites = list_sites()

        for site_name in target_sites:
            site_path = BASE_DIR / site_name
            if not site_path.exists():
                continue
            for file_path in site_path.glob("*.json"):
                zf.write(file_path, arcname=str(file_path.relative_to(BASE_DIR)))

    buffer.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"piezometer_backup_{site or 'all'}_{ts}.zip"
    return filename, buffer.getvalue()


def import_backup_zip(uploaded_file):
    try:
        with zipfile.ZipFile(uploaded_file) as zf:
            imported = 0
            for member in zf.namelist():
                if member.endswith("/") or not member.lower().endswith(".json"):
                    continue
                parts = Path(member).parts
                if len(parts) < 2:
                    continue
                site_name = parts[0]
                filename = parts[-1]
                ensure_site_dir(site_name)
                data = zf.read(member)
                with open(BASE_DIR / site_name / filename, "wb") as f:
                    f.write(data)
                imported += 1
        if imported == 0:
            return False, "ZIP 안에 가져올 JSON 데이터가 없습니다."
        return True, f"백업 ZIP에서 {imported}개 파일을 가져왔습니다."
    except zipfile.BadZipFile:
        return False, "올바른 ZIP 파일이 아닙니다."


def render_top_notice():
    st.markdown(
        """
        <div style="background:linear-gradient(90deg,#0f172a,#1e293b);padding:18px 22px;border-radius:16px;margin-bottom:16px;">
            <div style="font-size:28px;font-weight:700;color:#fff;">지하수위계 현장 캘리브레이션 시스템</div>
            <div style="font-size:14px;color:#cbd5e1;margin-top:6px;">Field Piezometer Pro · Streamlit Community Cloud Ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "클라우드 배포용 버전입니다. 현장 데이터는 로컬 JSON으로 저장되며, 백업 ZIP 다운로드/업로드 기능을 함께 사용하면 관리가 편합니다."
    )


def render_site_section():
    st.subheader("1. 현장 및 관리")
    sites = list_sites()
    site_options = [""] + sites
    if st.session_state["selected_site"] not in site_options:
        st.session_state["selected_site"] = ""

    c1, c2, c3 = st.columns([1.5, 1.5, 1])
    with c1:
        st.selectbox(
            "현장 선택",
            site_options,
            key="selected_site",
            format_func=lambda x: "현장을 선택하세요" if x == "" else x,
        )
    with c2:
        st.text_input("새 현장명", key="new_site_name", placeholder="예: OO현장 A구간")
    with c3:
        st.write("")
        st.write("")
        if st.button("+ 새 현장 추가", use_container_width=True):
            ok, msg = add_site(st.session_state.get("new_site_name", ""))
            (st.success if ok else st.warning)(msg)
            st.rerun()

    selected_site = st.session_state.get("selected_site", "")
    txt_name, txt_data = build_site_txt(selected_site)
    d1, d2 = st.columns(2)
    with d1:
        if txt_data:
            st.download_button(
                "TXT 내보내기",
                data=txt_data.encode("utf-8"),
                file_name=txt_name,
                mime="text/plain",
                use_container_width=True,
            )
        else:
            st.button("TXT 내보내기", disabled=True, use_container_width=True)
    with d2:
        backup_name, backup_bytes = build_backup_zip(selected_site if selected_site else None)
        st.download_button(
            "백업 ZIP 다운로드",
            data=backup_bytes,
            file_name=backup_name,
            mime="application/zip",
            use_container_width=True,
        )

    uploaded = st.file_uploader("백업 ZIP 업로드", type=["zip"])
    if uploaded is not None:
        ok, msg = import_backup_zip(uploaded)
        (st.success if ok else st.warning)(msg)
        if ok:
            st.rerun()


def render_info_section():
    st.subheader("2. 수위계 제원 정보")
    cols = st.columns(2)
    for i, (label, key) in enumerate(INFO_FIELDS):
        with cols[i % 2]:
            st.text_input(label, key=f"info_{key}")


def render_spec_section():
    st.subheader("3. 성적서(Spec) 정보 및 비교")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.text_input("성적서 L.G.F", key="spec_lgf", placeholder="예: 0.0001234")
    with c2:
        match_rate = st.session_state.get("match_rate")
        if match_rate is None:
            st.info("성적서 대비 일치율: - %")
        elif match_rate >= 90:
            st.success(f"성적서 대비 일치율: {match_rate:.2f} %")
        else:
            st.error(f"성적서 대비 일치율: {match_rate:.2f} %")


def render_base_section():
    st.subheader("4. 설치 단계별 V/W 측정값")
    h = st.columns([1.3, 1, 1])
    h[0].markdown("**구분**")
    h[1].markdown("**Digits (Hz²/1000)**")
    h[2].markdown("**온도 (℃)**")

    for stage in BASE_STAGES:
        row = st.columns([1.3, 1, 1])
        row[0].write(stage)
        row[1].text_input(
            f"{stage}_digits",
            key=f"base_digits_{stage}",
            label_visibility="collapsed",
        )
        row[2].text_input(
            f"{stage}_temp",
            key=f"base_temp_{stage}",
            label_visibility="collapsed",
        )


def render_calib_section():
    st.subheader("5. 현장 L.G.F 도출 측정 (1m 간격)")
    b1, b2, _ = st.columns([1, 1, 4])
    with b1:
        if st.button("행 추가 +", use_container_width=True):
            st.session_state["calib_count"] += 1
            st.rerun()
    with b2:
        if st.button("행 삭제 -", use_container_width=True):
            if st.session_state["calib_count"] > 1:
                idx = st.session_state["calib_count"] - 1
                st.session_state[f"calib_depth_{idx}"] = ""
                st.session_state[f"calib_digits_{idx}"] = ""
                st.session_state["calib_count"] -= 1
            st.rerun()

    head = st.columns([0.5, 1, 1])
    head[0].markdown("**No.**")
    head[1].markdown("**수심(m)**")
    head[2].markdown("**측정 Digits**")

    for i in range(st.session_state["calib_count"]):
        row = st.columns([0.5, 1, 1])
        row[0].write(i + 1)
        row[1].text_input(
            f"depth_{i}",
            key=f"calib_depth_{i}",
            placeholder="예: 1.0",
            label_visibility="collapsed",
        )
        row[2].text_input(
            f"digits_{i}",
            key=f"calib_digits_{i}",
            placeholder="예: 12345.67",
            label_visibility="collapsed",
        )


def render_result_section():
    st.subheader("6. 계산 결과")
    if st.button("L.G.F 계산 및 비교 실행", type="primary", use_container_width=True):
        ok, msg = calculate_lgf()
        (st.success if ok else st.warning)(msg)

    lgf = st.session_state.get("current_lgf_field")
    st.metric("현장 계산 L.G.F", f"{lgf:.7f}" if lgf is not None else "-")


def render_manage_section():
    st.subheader("7. 저장 / 불러오기 / 삭제")
    a1, a2 = st.columns(2)
    with a1:
        if st.button("데이터 저장", use_container_width=True):
            ok, msg = save_data()
            (st.success if ok else st.warning)(msg)
    with a2:
        if st.button("입력 초기화", use_container_width=True):
            clear_inputs()
            st.success("입력값을 초기화했습니다.")
            st.rerun()

    records = list_records(st.session_state.get("selected_site", ""))
    options = [""] + records
    if st.session_state["record_to_manage"] not in options:
        st.session_state["record_to_manage"] = ""

    m1, m2 = st.columns([2, 1])
    with m1:
        st.selectbox(
            "저장된 데이터 목록",
            options,
            key="record_to_manage",
            format_func=lambda x: "데이터를 선택하세요" if x == "" else x,
        )
    with m2:
        st.checkbox("삭제 확인", key="delete_confirm")

    x1, x2 = st.columns(2)
    with x1:
        if st.button("데이터 불러오기", use_container_width=True):
            ok, msg = load_data(st.session_state.get("selected_site", ""), st.session_state.get("record_to_manage", ""))
            (st.success if ok else st.warning)(msg)
            if ok:
                st.rerun()
    with x2:
        if st.button("데이터 삭제", use_container_width=True):
            if not st.session_state.get("delete_confirm", False):
                st.warning("삭제 확인을 체크하세요.")
            else:
                ok, msg = delete_data(st.session_state.get("selected_site", ""), st.session_state.get("record_to_manage", ""))
                (st.success if ok else st.warning)(msg)
                if ok:
                    st.session_state["record_to_manage"] = ""
                    st.session_state["delete_confirm"] = False
                    st.rerun()


def render_footer_notes():
    st.markdown("---")
    st.caption("팁: 현장 데이터는 계산 후 저장하고, 작업 종료 전 ZIP 백업을 받아두면 클라우드 환경에서 안전합니다.")


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="📐", layout="wide")
    init_state()
    render_top_notice()
    render_site_section()
    st.markdown("---")
    render_info_section()
    st.markdown("---")
    render_spec_section()
    st.markdown("---")
    render_base_section()
    st.markdown("---")
    render_calib_section()
    st.markdown("---")
    render_result_section()
    st.markdown("---")
    render_manage_section()
    render_footer_notes()


if __name__ == "__main__":
    main()
