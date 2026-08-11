# Linux-Project

라즈베리파이에서 Google Drive에 올라온 이미지를 이어붙여 슬라이드쇼 영상으로 재생하는 소규모 Python 프로젝트. 두 가지 모드로 구성.

## 구성

### 1) `main.py` — Google Drive 폴링 → 영상 자동 재생
- Google Drive 특정 폴더를 주기적으로 확인
- 새/변경된 이미지가 있으면 `moviepy`로 이미지당 60초짜리 슬라이드쇼 `.mp4` 생성
- 생성된 영상을 라즈베리파이에서 자동 재생

### 2) `webserver_main.py` — Flask 업로드 서버 → 영상 자동 재생
- 라즈베리파이에서 Flask 웹서버를 띄워 이미지 업로드 UI 제공
- 업로드된 이미지로 동일하게 슬라이드쇼 영상 생성 및 재생

## 세팅

### Google Drive 모드 (`main.py`)

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성 → Drive API 활성화 → **서비스 계정** 생성 후 JSON 키 다운로드
2. 다운로드한 JSON을 프로젝트 루트에 `service_account_key.json`으로 저장 (**커밋 금지**, `.gitignore` 처리됨)
3. 스크립트가 사용할 Google Drive 폴더를 만들고, 그 폴더를 서비스 계정 이메일(`...@...iam.gserviceaccount.com`)과 공유
4. `main.py` 상단의 `FOLDER_ID`를 자신의 폴더 ID로 교체

### 공통 의존성

```bash
pip install google-auth google-api-python-client moviepy pillow pytz flask
```

## 실행

```bash
# Drive 폴링 모드
python main.py

# 웹서버 모드
python webserver_main.py
```

## 참고

이 저장소는 학습·개인 실습용 코드이며 프로덕션용이 아님. `service_account_key.json`, `images/`, `resized_images/`, 생성 `.mp4` 파일은 커밋에서 제외됨(`.gitignore`).
