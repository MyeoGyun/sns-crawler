# 쿠키로 로그인하기 가이드

## 🍪 개요

직접 추출한 쿠키를 사용하여 자동 로그인하는 방법입니다.

---

## 🎯 쿠키 추출 방법

### 1단계: 브라우저에서 Twitter 로그인

Chrome 브라우저에서 https://x.com 로그인

### 2단계: 개발자 도구 열기

**F12** 또는 **Ctrl+Shift+I** (Mac: Cmd+Option+I)

### 3단계: Application 탭 → Cookies

```
Application 탭
  └─ Storage
      └─ Cookies
          └─ https://x.com  ← 클릭
```

### 4단계: 필수 쿠키 복사

| 쿠키 이름 | 설명 | 필수 |
|----------|------|------|
| `auth_token` | 인증 토큰 | ✅ 필수 |
| `ct0` | CSRF 토큰 | ✅ 필수 |
| `twid` | 트위터 ID | 선택 |
| `guest_id` | 게스트 ID | 선택 |

**복사 방법:**
1. 쿠키 이름 클릭 (예: `auth_token`)
2. Value 값 복사 (우클릭 → Copy 또는 더블클릭 → Ctrl+C)

---

## 📝 방법 1: .env 파일 사용 (추천)

### 1단계: .env 파일 생성

```bash
# .env.example을 복사
cp .env.example .env

# 또는 수동으로 생성
```

### 2단계: .env 파일 편집

```env
# .env 파일 내용

AUTH_TOKEN=여기에_auth_token_값_붙여넣기
CT0=여기에_ct0_값_붙여넣기
TWID=여기에_twid_값_붙여넣기
GUEST_ID=여기에_guest_id_값_붙여넣기
```

**예시:**
```env
AUTH_TOKEN=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
CT0=9876543210abcdef1234567890fedcba09876543210
TWID=u%3D1234567890123456789
GUEST_ID=v1%3A167890123456789012
```

### 3단계: 실행

```bash
python quote_extractor_env.py
```

**실행 과정:**
```
[정보] .env 파일 로드 완료: 4개 항목
[정보] Twitter 접속 중...
[정보] 개별 쿠키 로드 중...
[성공] 4개 쿠키 로드 완료
[정보] 세션 검증 중...
[성공] 쿠키로 로그인 성공!
```

---

## 💻 방법 2: 전체 쿠키 JSON 사용

### 1단계: 모든 쿠키를 JSON으로 복사

**Chrome 개발자 도구에서:**
1. **Application** → **Cookies** → **https://x.com**
2. 쿠키 목록에서 **우클릭**
3. **Copy all as JSON** (확장 프로그램 필요할 수 있음)

**또는 수동:**
```javascript
// Console 탭에서 실행
copy(JSON.stringify(document.cookie.split('; ').map(c => {
    const [name, value] = c.split('=');
    return {name, value, domain: '.x.com', path: '/'};
})))
```

### 2단계: .env 파일에 붙여넣기

```env
COOKIES_JSON=[{"name":"auth_token","value":"abc123...","domain":".x.com","path":"/"},{"name":"ct0","value":"987654...","domain":".x.com","path":"/"}]
```

**⚠️ 주의: 한 줄로 작성해야 함!**

### 3단계: 실행

```bash
python quote_extractor_env.py
```

---

## 🔧 .env 파일 형식

### 기본 형식 (.env.example)

```env
# Twitter/X 쿠키 설정

# 필수 쿠키
AUTH_TOKEN=your_auth_token_here
CT0=your_ct0_csrf_token_here

# 선택 쿠키
TWID=your_twid_here
GUEST_ID=your_guest_id_here

# 전체 쿠키 JSON (선택)
COOKIES_JSON=
```

### 실제 예시 (.env)

```env
# 개별 쿠키 방식
AUTH_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
CT0=1234567890abcdef1234567890abcdef12345678
TWID=u%3D9876543210987654321
GUEST_ID=v1%3A167123456789012345

# 또는 JSON 방식 (위 개별 쿠키 주석 처리 후)
# COOKIES_JSON=[{"name":"auth_token","value":"a1b2c3...","domain":".x.com"},...]
```

---

## ✅ 작동 원리

### 1️⃣ .env 파일 읽기

```python
load_env()
# → AUTH_TOKEN, CT0 등 읽기
```

### 2️⃣ Twitter 페이지 접속

```python
driver.get("https://x.com")
# → 쿠키 도메인 일치 필요
```

### 3️⃣ 쿠키 추가

```python
driver.add_cookie({
    "name": "auth_token",
    "value": "abc123...",
    "domain": ".x.com"
})
```

### 4️⃣ 로그인 확인

```python
driver.get("https://x.com/home")
# → 로그인 상태 검증
```

---

## 🔒 보안 주의사항

### ⚠️ 절대 하지 말 것

- ❌ .env 파일을 Git에 커밋
- ❌ .env 파일을 다른 사람과 공유
- ❌ 쿠키를 공개 게시판에 올림

### ✅ 안전한 사용

```bash
# .env 파일은 .gitignore에 포함됨
# 개인 컴퓨터에만 저장

# 공용 PC 사용 후
rm .env  # 쿠키 삭제
```

### 🔐 쿠키 유효 기간

- Twitter 쿠키는 보통 **수 주 ~ 수 개월** 유효
- 만료 시 브라우저에서 재로그인 후 새 쿠키 추출

---

## 🆚 방법 비교

| 방법 | 장점 | 단점 | 추천 |
|------|------|------|------|
| **개별 쿠키** | 간단, 가독성 좋음 | 쿠키 개수 제한 | ⭐⭐⭐ |
| **JSON 쿠키** | 모든 쿠키 포함 | 복잡, 가독성 나쁨 | ⭐⭐ |
| **세션 저장** | 자동화, 편리 | 코드 복잡 | ⭐⭐⭐⭐ |

---

## 🐛 트러블슈팅

### 문제 1: ".env 파일이 없습니다"

**해결:**
```bash
# .env.example 복사
cp .env.example .env

# 또는 직접 생성
touch .env
# 내용 작성
```

---

### 문제 2: "필수 쿠키 누락"

**원인:** AUTH_TOKEN 또는 CT0 값이 비어있음

**해결:**
1. 브라우저 개발자 도구 재확인
2. 로그인 상태 확인
3. 쿠키 값 정확히 복사

---

### 문제 3: "쿠키가 유효하지 않습니다"

**원인:**
- 쿠키 만료
- 잘못된 값 복사
- 브라우저와 다른 계정

**해결:**
```bash
# 브라우저에서 재로그인
# 새 쿠키 복사
# .env 파일 업데이트
```

---

### 문제 4: COOKIES_JSON 파싱 오류

**원인:** JSON 형식 오류

**확인:**
```python
# Python으로 검증
import json
cookies_str = '여기에_COOKIES_JSON_값_붙여넣기'
json.loads(cookies_str)  # 오류 없으면 OK
```

**해결:**
- JSON을 한 줄로 작성
- 따옴표 이스케이프 확인
- 쉼표, 대괄호 확인

---

## 📊 실행 예시

### 성공 케이스

```bash
$ python quote_extractor_env.py

============================================================
   트위터 인용글 추출 - .env 쿠키 버전
============================================================

[정보] .env 파일 로드 완료: 4개 항목
인용글 URL: https://x.com/user/status/123/quotes
저장 파일명 (엔터 = quotes.csv): ⏎
최대 스크롤 (엔터 = 무제한): 5
브라우저 숨김? (y/n, 엔터 = n): ⏎

============================================================
[정보] Chrome 드라이버 시작...
[정보] Twitter 접속 중...
[정보] 개별 쿠키 로드 중...
[성공] 4개 쿠키 로드 완료
[정보] 세션 검증 중...
[성공] 쿠키로 로그인 성공!  ← 성공!

[정보] 인용글 페이지 접근...
[정보] 스크롤 시작...
  → 15개 추출
  → 28개 추출

[완료] 총 28개 추출

[완료] CSV 저장: quotes.csv
  - 총 28개 레코드

✅ 성공!
```

---

## 💡 팁

### 팁 1: 쿠키 백업

```bash
# .env 파일 백업
cp .env .env.backup

# 다른 계정 사용 시
cp .env.backup .env
```

### 팁 2: 여러 계정

```bash
# 계정별 .env 파일
.env.account1
.env.account2

# 사용 시 복사
cp .env.account1 .env
python quote_extractor_env.py
```

### 팁 3: 쿠키 자동 갱신

주기적으로 브라우저에서 새 쿠키 추출하여 .env 업데이트

---

## 🔗 관련 파일

- `.env.example` - 쿠키 입력 양식
- `quote_extractor_env.py` - 실행 스크립트
- `.gitignore` - .env 파일 제외 (Git)

---

## 📝 요약

**간단 3단계:**

1. **쿠키 추출**
   - F12 → Application → Cookies → https://x.com
   - auth_token, ct0 복사

2. **.env 파일 작성**
   ```env
   AUTH_TOKEN=복사한_값
   CT0=복사한_값
   ```

3. **실행**
   ```bash
   python quote_extractor_env.py
   ```

**로그인 없이 바로 사용!** 🎉
