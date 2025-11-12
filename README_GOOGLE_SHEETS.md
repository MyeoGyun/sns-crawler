# Google Sheets 자동 업로드 가이드

## 📊 개요

트위터 인용글을 추출하여 **자동으로 Google Sheets에 업로드**하는 도구입니다.

**장점:**
- ✅ CSV 파일 필요 없음
- ✅ 실시간으로 구글 시트에 저장
- ✅ 여러 사람과 공유 가능
- ✅ 언제 어디서나 접근 가능

---

## 🚀 사용 방법

### 1단계: Google Cloud 설정 (최초 1회만)

#### 1-1. Google Cloud Console 접속
https://console.cloud.google.com/

#### 1-2. 프로젝트 생성
1. 좌측 상단 프로젝트 선택 → **새 프로젝트**
2. 프로젝트 이름: `Twitter Quote Extractor`
3. **만들기** 클릭

#### 1-3. Google Sheets API 활성화
1. 좌측 메뉴 → **API 및 서비스** → **라이브러리**
2. 검색창에 `Google Sheets API` 입력
3. **Google Sheets API** 선택 → **사용** 클릭

#### 1-4. 서비스 계정 생성
1. 좌측 메뉴 → **API 및 서비스** → **사용자 인증 정보**
2. 상단 **+ 사용자 인증 정보 만들기** → **서비스 계정** 선택
3. 서비스 계정 이름: `twitter-quote-service`
4. **만들기 및 계속** 클릭
5. 역할: **편집자** 선택 (또는 생략)
6. **완료** 클릭

#### 1-5. JSON 키 다운로드
1. 생성된 서비스 계정 클릭
2. **키** 탭 선택
3. **키 추가** → **새 키 만들기**
4. 키 유형: **JSON** 선택
5. **만들기** 클릭 → 자동으로 JSON 파일 다운로드됨

#### 1-6. credentials.json 저장
다운로드한 JSON 파일을:
- 파일명을 `credentials.json`으로 변경
- `quote_extractor_gsheet.py`와 **같은 폴더**에 저장

```
프로젝트 폴더/
  ├── quote_extractor_gsheet.py
  ├── credentials.json  ← 여기!
  └── config_defaults.json
```

---

### 2단계: 패키지 설치

```bash
pip install selenium webdriver-manager gspread oauth2client
```

---

### 3단계: 실행

```bash
python quote_extractor_gsheet.py \
  --url "https://x.com/lottewellfood/status/1983036567561351382/quotes" \
  --username "your_twitter_id" \
  --password "your_password" \
  --sheet-name "Twitter Quotes" \
  --max-scrolls 10
```

**옵션:**
- `--url`: 인용글 페이지 URL (필수)
- `--username`: 트위터 ID (필수)
- `--password`: 트위터 비밀번호 (필수)
- `--sheet-name`: 구글 시트 이름 (기본: "Twitter Quotes")
- `--max-scrolls`: 최대 스크롤 횟수 (기본: 무제한)
- `--headless`: 브라우저 숨김 모드
- `--scroll-delay`: 스크롤 간 대기시간(초)

---

### 4단계: Google Sheets 확인

실행 완료 후 출력되는 URL을 브라우저에서 열면 결과 확인 가능!

```
[완료] Google Sheets 업로드 성공!
  - 시트 이름: Twitter Quotes
  - 총 레코드: 25개
  - URL: https://docs.google.com/spreadsheets/d/xxxxx

브라우저에서 확인: https://docs.google.com/spreadsheets/d/xxxxx
```

---

## 🔧 트러블슈팅

### 1. "credentials.json을 찾을 수 없습니다"

**원인:** credentials.json이 잘못된 위치에 있음

**해결:**
```bash
# 파일 위치 확인
ls -la credentials.json

# 또는 Windows에서
dir credentials.json

# 파일이 없다면 다시 다운로드 후 저장
```

---

### 2. "Permission denied" 또는 인증 오류

**원인:** Google Sheets API가 활성화되지 않음

**해결:**
1. Google Cloud Console → API 및 서비스 → 라이브러리
2. "Google Sheets API" 검색 → 활성화
3. "Google Drive API"도 활성화 (선택사항)

---

### 3. "Spreadsheet not found"

**원인:** 서비스 계정이 시트에 접근할 수 없음

**해결 방법 1: 자동 생성**
- 스크립트가 자동으로 새 시트 생성
- credentials.json의 서비스 계정 이메일로 소유권 설정됨

**해결 방법 2: 기존 시트 공유**
1. credentials.json 열기
2. `client_email` 값 복사 (예: `xxx@xxx.iam.gserviceaccount.com`)
3. Google Sheets에서 해당 이메일과 **공유** (편집자 권한)

---

### 4. 시트가 생성되지만 내 계정에서 안 보임

**원인:** 서비스 계정이 소유자로 되어 있음

**해결:**
스크립트 실행 후 출력된 URL로 직접 접속하거나, 코드 수정:

```python
# quote_extractor_gsheet.py 파일에서 다음 줄 찾기 (약 580번째 줄)
# spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')

# 주석 제거 후 본인 이메일로 변경:
spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')
```

---

## 📋 CSV vs Google Sheets 비교

| 항목 | CSV 버전 | Google Sheets 버전 |
|------|----------|-------------------|
| 설정 | 간단 | 복잡 (최초 1회) |
| 실행 | 빠름 | 약간 느림 (업로드 시간) |
| 공유 | 어려움 | 쉬움 (URL 공유) |
| 실시간 확인 | 불가 | 가능 |
| Excel 호환 | 완벽 | Import 필요 |
| 추천 대상 | 개인 사용 | 팀 협업 |

---

## 🎯 사용 예시

### 예시 1: 빠른 테스트
```bash
python quote_extractor_gsheet.py \
  --url "https://x.com/.../quotes" \
  --username "my_id" \
  --password "my_password" \
  --sheet-name "Test Quotes" \
  --max-scrolls 3
```

### 예시 2: 전체 수집
```bash
python quote_extractor_gsheet.py \
  --url "https://x.com/.../quotes" \
  --username "my_id" \
  --password "my_password" \
  --sheet-name "Full Quotes Collection" \
  --headless
```

### 예시 3: 일별 수집 (매일 자동 실행)
```bash
# cron (Linux/Mac) 또는 작업 스케줄러 (Windows)로 자동화
python quote_extractor_gsheet.py \
  --url "https://x.com/.../quotes" \
  --username "my_id" \
  --password "my_password" \
  --sheet-name "Quotes $(date +%Y%m%d)" \
  --headless
```

---

## 🔐 보안 주의사항

1. **credentials.json 보안**
   - Git에 커밋하지 마세요! (`.gitignore`에 추가됨)
   - 다른 사람과 공유하지 마세요
   - 유출 시 Google Cloud Console에서 키 삭제

2. **트위터 비밀번호**
   - 환경 변수 사용 권장:
   ```bash
   export TWITTER_PASSWORD="your_password"
   python quote_extractor_gsheet.py --password "$TWITTER_PASSWORD" ...
   ```

---

## 💡 다음 단계

1. ✅ Google Cloud 설정 완료
2. ✅ credentials.json 다운로드 및 저장
3. ✅ 스크립트 실행
4. 📊 Google Sheets에서 데이터 확인
5. 🔄 필요 시 반복 실행

---

## 📞 지원

문제 발생 시:
1. credentials.json 위치 확인
2. Google Sheets API 활성화 확인
3. 서비스 계정 이메일 확인
4. 에러 메시지 전체 복사 후 문의
