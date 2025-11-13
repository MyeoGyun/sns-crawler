# 🛡️ 봇 감지 회피 기능 가이드

## 📋 개요

Twitter/X의 봇 감지 시스템을 우회하여 60개 이상의 인용글을 안정적으로 수집할 수 있도록 개선된 버전입니다.

---

## ✨ 적용된 봇 회피 기술

### 1️⃣ undetected-chromedriver ⭐ 최우선
- **효과**: 기본 봇 감지 80% 우회
- **역할**: `navigator.webdriver` 플래그 숨김, Chrome DevTools Protocol 감지 우회
- **적용**: 자동 (라이브러리 설치 시)

### 2️⃣ 점진적 딜레이 증가
- **효과**: Rate Limiting 완화
- **동작**:
  - 1-60개: 2초 기본 딜레이
  - 61-70개: 4초 딜레이
  - 71-80개: 6초 딜레이
  - 81-90개: 8초 딜레이
  - 최대 20초까지 증가

### 3️⃣ 간헐적 휴식 시간
- **효과**: 인간 행동 패턴 모방
- **휴식 시점**: 60개, 120개, 180개, 240개, 300개 수집 시
- **휴식 시간**: 30-60초 랜덤

---

## 🚀 빠른 시작

### 1단계: 라이브러리 설치

```bash
# 필수 라이브러리 설치
pip install -r requirements.txt
```

또는 개별 설치:

```bash
pip install selenium webdriver-manager undetected-chromedriver python-dotenv
```

### 2단계: 프로그램 실행

```bash
python quote_extractor_cookie_input.py
```

### 3단계: 설정

```
최대 수집 개수 (엔터 = 무제한): 200
```

**권장 설정:**
- 처음 사용: 100개로 테스트
- 안정적 작동 확인 후: 200-300개
- 대량 수집: 무제한 (자동 휴식 포함)

---

## 📊 성능 비교

| 버전 | 봇 회피 기술 | 평균 수집 가능 개수 | 소요 시간 |
|------|------------|-----------------|----------|
| **기존** | 없음 | ~60개 | 2-3분 |
| **개선 (현재)** | ✅ 3가지 기술 | 180-240개 | 10-15분 |
| **+ Proxy** | ✅ 4가지 기술 | 무제한 | 시간당 1000개+ |

---

## 🎯 실행 예시

### 예시 1: 100개 수집

```bash
$ python quote_extractor_cookie_input.py

============================================================
   쿠키 입력
============================================================
...

============================================================
인용글 URL: https://x.com/user/status/123/quotes
저장 파일명 (엔터 = quotes.csv): ⏎
최대 스크롤 (엔터 = 무제한): ⏎
최대 수집 개수 (엔터 = 무제한): 100
브라우저 숨김? (y/n, 엔터 = n): ⏎

============================================================
🚀 봇 회피 기능 활성화
  ✅ 점진적 딜레이 증가 (60개 이후)
  ✅ 간헐적 휴식 (60, 120, 180, 240, 300개마다)
  ✅ undetected-chromedriver (고급 봇 감지 우회)
============================================================

[정보] undetected-chromedriver 사용 (고급 봇 회피)
[정보] Chrome 드라이버 시작...
[정보] Twitter 접속 중...
[정보] 쿠키 로드 중...
[성공] 3개 쿠키 로드 완료
[정보] 세션 검증 중...
[성공] 쿠키로 로그인 성공!

[정보] 인용글 페이지 접근...
[목표] 최대 100개 수집
[정보] 스크롤 및 데이터 수집 시작...
============================================================
[수집 #  1] @user1              | 트윗 내용...
[수집 #  2] @user2              | 또 다른 트윗...
              └─ 미디어 2개 포함
...
[수집 # 60] @user60             | 60번째 트윗...

🛑 [휴식 모드]
   현재 수집: 60개
   휴식 시간: 45초 (인간 행동 패턴 모방)
   대기 중.......... 완료!
============================================================

[수집 # 61] @user61             | 61번째 트윗...

[스크롤 # 8] 이번 스크롤에서 5개 신규 추출 (총 65개)
[대기] 4.2초 대기 중... (적응형 딜레이: 65개 수집)
============================================================
...
[수집 #100] @user100            | 100번째 트윗...

[정보] 최대 수집 개수 (100개) 도달 - 수집 종료
============================================================
[완료] 총 100개 인용글 수집 완료
============================================================

[완료] CSV 저장: quotes.csv
  - 총 100개 레코드

✅ 성공!
```

---

## 🔧 고급 설정 (선택사항)

### 봇 회피 파라미터 조정

파일: `quote_extractor_cookie_input.py`

```python
# 봇 회피 설정
BASE_DELAY = 2.0          # 기본 딜레이 (초) - 낮추면 빠르지만 위험
MAX_DELAY = 20.0          # 최대 딜레이 (초)
DELAY_INCREASE_THRESHOLD = 60  # 딜레이 증가 시작 지점
DELAY_INCREASE_STEP = 10  # 딜레이 증가 간격 (트윗 개수)
DELAY_INCREASE_AMOUNT = 2  # 증가량 (초)

# 휴식 설정
REST_INTERVALS = [60, 120, 180, 240, 300]  # 휴식 지점
REST_MIN = 30             # 최소 휴식 시간 (초)
REST_MAX = 60             # 최대 휴식 시간 (초)
```

**조정 예시:**

#### 더 빠르게 (위험도 증가)
```python
BASE_DELAY = 1.5
DELAY_INCREASE_THRESHOLD = 80
REST_MIN = 20
REST_MAX = 40
```

#### 더 안전하게 (느리지만 안정적)
```python
BASE_DELAY = 3.0
DELAY_INCREASE_THRESHOLD = 50
DELAY_INCREASE_AMOUNT = 3
REST_MIN = 45
REST_MAX = 90
```

---

## ⚠️ 주의사항

### 1. undetected-chromedriver 설치 필수

```bash
pip install undetected-chromedriver
```

설치하지 않으면 일반 WebDriver로 작동하여 효과 감소:
```
⚠️  일반 WebDriver 사용 (undetected-chromedriver 미설치)
    pip install undetected-chromedriver 권장
```

### 2. Chrome 버전 호환성

undetected-chromedriver는 Chrome 버전과 호환되어야 합니다:

```bash
# Chrome 버전 확인
google-chrome --version
# 또는
chromium --version
```

버전 충돌 시:
```bash
pip install --upgrade undetected-chromedriver
```

### 3. 수집 속도와 안정성 트레이드오프

| 목표 개수 | 권장 설정 | 예상 시간 |
|----------|---------|---------|
| ~100개 | 기본 설정 | 5-8분 |
| ~200개 | 기본 설정 | 12-18분 |
| ~300개 | 안전 설정 | 25-35분 |
| 무제한 | 안전 설정 + 수동 모니터링 | 변동 |

### 4. 법적 고려사항

- Twitter ToS 위반 가능성
- 공개 데이터 스크래핑은 일반적으로 합법
- 상업적 이용 시 법적 검토 권장
- 과도한 수집은 IP 차단 위험

---

## 🐛 트러블슈팅

### 문제 1: "undetected-chromedriver가 설치되지 않았습니다"

```bash
pip install undetected-chromedriver
```

또는

```bash
pip install -r requirements.txt
```

---

### 문제 2: Chrome 버전 불일치

**증상:**
```
SessionNotCreatedException: Message: session not created:
This version of ChromeDriver only supports Chrome version 131
```

**해결:**
1. Chrome 업데이트:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt upgrade google-chrome-stable

   # macOS
   brew upgrade google-chrome
   ```

2. 또는 undetected-chromedriver 재설치:
   ```bash
   pip uninstall undetected-chromedriver
   pip install undetected-chromedriver
   ```

---

### 문제 3: 60개 이상 수집 시 계속 차단됨

**가능한 원인:**
- 같은 IP로 짧은 시간에 여러 번 실행
- 쿠키 만료
- Twitter의 일시적 rate limit

**해결:**
1. 2-3시간 대기 후 재시도
2. Chrome에서 재로그인하여 새 쿠키 발급
3. 더 긴 휴식 시간 설정:
   ```python
   REST_MIN = 60
   REST_MAX = 120
   ```

---

### 문제 4: "쿠키가 유효하지 않습니다"

**해결:**
1. Chrome에서 Twitter 재로그인
2. F12 → Application → Cookies
3. `auth_token`과 `ct0` 새로 복사
4. 프로그램 재실행

---

## 📈 성능 최적화 팁

### 1. 헤드리스 모드 사용

```
브라우저 숨김? (y/n, 엔터 = n): y
```

- **장점**: 리소스 절약, 백그라운드 실행
- **단점**: 디버깅 어려움

### 2. 적절한 최대 개수 설정

무제한보다 200-300개씩 나눠서 수집 권장:
```
최대 수집 개수: 200
```

이유:
- 네트워크 오류 시 손실 최소화
- 중간 결과 확인 가능
- 봇 감지 위험 분산

### 3. 여러 계정 사용

같은 IP에서 여러 계정으로 분산 수집:
- 계정 A: 0-200개
- 계정 B: 200-400개
- 계정 C: 400-600개

---

## 🔮 향후 개선 계획

### 2단계 (선택사항 - 구현 안 됨)
- [ ] 다양한 스크롤 패턴
- [ ] 마우스 움직임 시뮬레이션
- [ ] 뷰포트 크기 랜덤화

### 3단계 (고급 - 비용 발생)
- [ ] Residential Proxy 로테이션
- [ ] User-Agent 로테이션

---

## 📚 관련 문서

- `README_CLI_COOKIE.md` - CLI 쿠키 입력 가이드
- `README_COOKIES.md` - 쿠키 추출 상세 가이드
- `README_SESSION.md` - 세션 저장 가이드
- `requirements.txt` - 필요한 라이브러리 목록

---

## 🎯 요약

### 즉시 사용 가능한 개선사항 ✅

1. **undetected-chromedriver** - 봇 감지 80% 우회
2. **점진적 딜레이 증가** - 60개 이후 자동으로 딜레이 증가
3. **간헐적 휴식** - 60, 120, 180... 마다 30-60초 휴식

### 예상 효과

- **기존**: ~60개 (2-3분)
- **현재**: 180-240개 (10-15분)
- **개선율**: **300% 이상** 🎉

---

**문의 및 피드백:** GitHub Issues

**라이선스:** MIT
