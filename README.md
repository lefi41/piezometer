# Piezometer Streamlit App

지하수위계 현장 캘리브레이션 시스템의 Streamlit 배포용 버전입니다.

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub + Streamlit Community Cloud 배포

1. 이 폴더를 GitHub 저장소에 업로드
2. Streamlit Community Cloud에서 저장소 연결
3. Entry point를 `app.py`로 지정
4. 배포

## 주의

- 이 앱은 `Sites_Data/` 폴더에 JSON 파일로 데이터를 저장합니다.
- Streamlit Community Cloud에서는 로컬 파일 저장이 영구 보장되지 않으므로,
  앱 안의 `백업 ZIP 다운로드` 기능으로 수시 백업하는 것을 권장합니다.
- `백업 ZIP 업로드`로 이전 데이터 복원이 가능합니다.
