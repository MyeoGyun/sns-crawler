# 간단 시작 가이드

## 🚀 가장 쉬운 실행 방법

**명령줄 인자 없이 바로 실행!** 대화형으로 필요한 정보를 입력받습니다.

---

## 📦 설치

### 1단계: Python 패키지 설치

```bash
pip install selenium webdriver-manager
```

### 2단계: 스크립트 다운로드

GitHub에서 다운로드 또는 Git clone

---

## ▶️ 실행 방법

### 간단 실행 (추천!)

```bash
python quote_extractor_simple.py
```

**그게 끝입니다!** 나머지는 프로그램이 물어봅니다.

---

## 💬 실행 예시

```
============================================================
   트위터/X 인용글 추출 도구 - 간편 실행 버전
============================================================

인용글 페이지 URL을 입력하세요: https://x.com/lottewellfood/status/1983036567561351382/quotes

트위터 아이디를 입력하세요: my_twitter_id
트위터 비밀번호를 입력하세요 (입력 내용 숨김): ********

저장할 파일명 (엔터 = quotes.csv): my_quotes.csv

고급 옵션 (엔터 = 기본값 사용)
  최대 스크롤 횟수 (엔터 = 무제한): 10
  브라우저 숨김 모드? (y/n, 엔터 = n): n

============================================================
설정 확인:
  URL: https://x.com/lottewellfood/status/1983036567561351382/quotes
  저장 파일: my_quotes.csv
  최대 스크롤: 10
  브라우저 숨김: 아니오
============================================================

시작하시겠습니까? (y/n): y

[정보] Chrome 드라이버 시작...
[정보] 트위터 로그인 중...
[성공] 로그인 완료!

[정보] 인용글 페이지 접근 중...
[정보] 스크롤 시작...
  → 현재까지 15개 추출됨
  → 현재까지 32개 추출됨
  → 현재까지 48개 추출됨

[완료] 총 48개 추출 완료

[완료] CSV 저장: my_quotes.csv
  - 총 48개 레코드
  - 위치: C:\Users\YourName\Documents\my_quotes.csv

✅ 성공적으로 완료되었습니다!
[정보] 브라우저 종료
```

---

## 📋 입력 항목

### 필수 입력

1. **인용글 페이지 URL**
   - 예: `https://x.com/user/status/1234567890/quotes`
   - `/quotes`가 없으면 자동으로 추가됨

2. **트위터 아이디**
   - 로그인할 계정 ID

3. **트위터 비밀번호**
   - 입력 시 화면에 표시되지 않음 (보안)

### 선택 입력 (엔터 = 기본값)

4. **저장할 파일명**
   - 기본값: `quotes.csv`
   - `.csv` 확장자 자동 추가

5. **최대 스크롤 횟수**
   - 기본값: 무제한
   - 숫자 입력 시 해당 횟수만큼만 스크롤

6. **브라우저 숨김 모드**
   - 기본값: `n` (브라우저 보임)
   - `y` 입력 시 숨김 모드

---

## ⚡ 빠른 시작 (기본값 사용)

모든 선택 항목에서 **엔터**만 누르면:
- 파일명: `quotes.csv`
- 스크롤: 무제한
- 브라우저: 보임

```bash
python quote_extractor_simple.py

# URL 입력
# 아이디 입력
# 비밀번호 입력
# 엔터 (파일명)
# 엔터 (스크롤)
# 엔터 (브라우저)
# y (시작 확인)
```

---

## 🆚 다른 버전과 비교

| 버전 | 실행 방법 | 난이도 | 추천 대상 |
|------|----------|--------|-----------|
| **quote_extractor_simple.py** | `python xxx.py` | ⭐ 쉬움 | **처음 사용자** |
| quote_extractor_windows.py | `python xxx.py --url "..." --username ...` | ⭐⭐ 보통 | 명령줄 익숙한 사용자 |
| quote_extractor_multi.py | 위와 동일 (여러 URL) | ⭐⭐⭐ 어려움 | 대량 처리 |
| quote_extractor_gsheet.py | 위와 동일 + credentials.json | ⭐⭐⭐⭐ 복잡 | 팀 협업 |

---

## 🔧 트러블슈팅

### 1. "올바른 트위터 인용글 URL을 입력하세요"

**원인:** URL 형식이 잘못됨

**해결:**
```
✅ 올바른 형식:
https://x.com/user/status/1234567890/quotes
https://twitter.com/user/status/1234567890/quotes

❌ 잘못된 형식:
https://x.com/user
https://x.com/user/status/1234567890  (quotes 없음)
```

---

### 2. "드라이버 생성 실패"

**원인:** Chrome 또는 ChromeDriver 문제

**해결:**
```bash
# ChromeDriver 자동 설치 패키지 설치
pip install webdriver-manager

# Chrome 브라우저 설치 확인
# Windows: C:\Program Files\Google\Chrome\Application\chrome.exe
# Mac: /Applications/Google Chrome.app
```

---

### 3. "로그인 실패"

**원인:** 아이디/비밀번호 오류 또는 2단계 인증

**해결:**
- 아이디/비밀번호 재확인
- 2단계 인증(2FA) 비활성화 (일시적)
- VPN 사용 시 비활성화

---

### 4. 비밀번호 입력 시 아무것도 안 보임

**정상입니다!** 보안을 위해 `getpass` 모듈이 입력을 숨깁니다.
- 그냥 타이핑하고 엔터 누르세요
- 실수했다면 Ctrl+C로 취소 후 재실행

---

## 💡 팁

### 팁 1: 브라우저를 보면서 실행

처음에는 **브라우저 숨김 모드를 사용하지 마세요** (엔터 또는 `n`)
- 무슨 일이 일어나는지 확인 가능
- 문제 발생 시 쉽게 파악

### 팁 2: 적은 스크롤로 테스트

처음에는 **최대 스크롤 3-5회**로 테스트:
```
최대 스크롤 횟수 (엔터 = 무제한): 3
```

### 팁 3: 파일명에 날짜 포함

```
저장할 파일명: quotes_20250112.csv
```

### 팁 4: 중단하려면

실행 중 언제든지 `Ctrl + C`로 중단 가능

---

## 📁 파일 저장 위치

기본적으로 **스크립트와 같은 폴더**에 저장됩니다.

**예시:**
```
프로젝트 폴더/
  ├── quote_extractor_simple.py
  └── quotes.csv  ← 여기 생성됨!
```

**전체 경로는 완료 시 출력됩니다:**
```
[완료] CSV 저장: quotes.csv
  - 위치: C:\Users\YourName\Documents\Projects\quotes.csv
```

---

## 🎯 완벽한 첫 실행 가이드

### 1. 준비
```bash
# 패키지 설치
pip install selenium webdriver-manager

# Chrome 설치 확인 (브라우저)
```

### 2. 실행
```bash
python quote_extractor_simple.py
```

### 3. 입력 (예시)
```
URL: https://x.com/lottewellfood/status/1983036567561351382/quotes
아이디: my_twitter_id
비밀번호: ******** (입력은 숨겨짐)
파일명: (엔터 - 기본값)
스크롤: 5
브라우저: (엔터 - 보임)
시작: y
```

### 4. 기다리기
- 브라우저가 자동으로 열림
- 로그인 진행
- 스크롤하며 데이터 수집
- 자동으로 종료

### 5. 결과 확인
- 같은 폴더에 `quotes.csv` 생성됨
- Excel/Google Sheets에서 열기

---

## 🚀 다음 단계

간단 버전으로 익숙해지면:

1. **Windows 버전** - 더 많은 옵션
   ```bash
   python quote_extractor_windows.py --url "..." --username "..." --password "..."
   ```

2. **다중 URL 버전** - 여러 URL 한 번에
   ```bash
   python quote_extractor_multi.py --url-file urls.txt --username "..." --password "..."
   ```

3. **Google Sheets 버전** - 자동 업로드
   ```bash
   python quote_extractor_gsheet.py --url "..." --sheet-name "..." --username "..." --password "..."
   ```

---

**가장 쉽게 시작하세요!** 🎉

명령어 하나면 끝:
```bash
python quote_extractor_simple.py
```
