# Raspberry Pi 디지털 사이니지

교내 TV에 이미지 자료를 USB로 옮기던 작업을 줄이기 위해 만든 Raspberry Pi 기반
자동 콘텐츠 송출 프로젝트입니다. Google Drive 또는 로컬 웹 업로드로 받은 이미지를
슬라이드쇼 영상으로 변환하고 전체 화면으로 반복 재생합니다.

## 담당 범위와 결과

- Raspberry Pi·Linux 실행 환경과 TV 자동 재생 흐름 구성
- Google Drive 변경 감지 및 원격 콘텐츠 동기화
- Flask 기반 이미지 업로드 UI와 최대 20개 파일 처리
- Pillow·MoviePy 기반 비율 유지 리사이즈 및 H.264 영상 생성
- 팀장으로 역할 분담, 개발 방향과 현장 적용 가능성 검토

핵심 기능은 2024년 교내 프로젝트에서 AI 코딩 에이전트 없이 구현했습니다. 2026년
공개 저장소 하드닝에서는 AI를 코드 리뷰와 정형 리팩터링에 활용하되, 기존 동작 보존,
보안 경계와 최종 수용 판정은 직접 수행했습니다. 구체적인 구분과 검토 기준은
[`docs/AI_DEVELOPMENT.md`](docs/AI_DEVELOPMENT.md)에 기록했습니다.

## 실행 모드

### 1. Google Drive 폴링

`main.py`가 Drive 폴더의 이미지 변경을 주기적으로 확인하고, 변경 시 영상을 다시 만들어
`mpv`로 재생합니다. 인증은 프로그램 시작 시점에 수행하며 Drive 읽기 권한만 요청합니다.

### 2. 로컬 웹 업로드

`webserver_main.py`가 `0.0.0.0:5000`에서 업로드 페이지를 제공합니다. 파일명은 저장 전에
정규화하고 확장자와 실제 이미지 내용을 함께 검사해 PNG/JPEG/GIF만 허용하며, 요청 전체
크기는 기본 50 MiB로 제한합니다.

> 인증 기능이 없는 교내·로컬 네트워크용 도구입니다. 인터넷에 직접 노출하지 마세요.

## 설치

Python 3.10 이상과 시스템 명령 `ffmpeg`, `mpv`가 필요합니다.

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Google Drive 모드 설정

1. Google Cloud에서 Drive API와 서비스 계정을 생성합니다.
2. JSON 키를 저장소 밖에 보관하고 대상 Drive 폴더를 서비스 계정에 공유합니다.
3. 환경 변수를 설정한 뒤 실행합니다.

```bash
export GOOGLE_SERVICE_ACCOUNT_FILE=/secure/path/service-account.json
export GOOGLE_DRIVE_FOLDER_ID=your-folder-id
python main.py
```

선택 설정:

- `SLIDESHOW_CHECK_INTERVAL`: Drive 확인 주기(초), 기본 60
- `SLIDESHOW_IMAGE_DURATION`: 이미지 한 장 표시 시간(초), 기본 60
- `SLIDESHOW_DEFAULT_IMAGE`: 오류 시 표시할 선택적 이미지 경로

## 웹 업로드 모드 실행

```bash
python webserver_main.py
```

브라우저에서 `http://<raspberry-pi-ip>:5000`으로 접속합니다.

## 검증

```bash
pip install -r requirements-dev.txt
python -m ruff check main.py webserver_main.py slideshow.py upload_utils.py tests
python -m compileall -q .
python -m unittest discover -s tests -v
```

같은 검증은 [GitHub Actions](.github/workflows/ci.yml)에서 깨끗한 Python 환경에 의존성을
설치한 뒤 반복합니다.
