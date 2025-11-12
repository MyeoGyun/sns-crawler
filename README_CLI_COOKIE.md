# CLI 쿠키 입력 가이드

## 🎯 개요

터미널에서 직접 쿠키를 **복사-붙여넣기**로 입력하여 로그인하는 가장 간단한 버전입니다.

### ✨ 특징

- ✅ **즉시 사용**: .env 파일 생성 없이 바로 실행
- ✅ **복사-붙여넣기**: Chrome에서 쿠키 복사 → 터미널에 붙여넣기
- ✅ **선택적 저장**: 입력한 쿠키를 .env로 저장 가능
- ✅ **사용자 친화적**: 단계별 가이드 제공

---

## 🚀 빠른 시작

### 1단계: Chrome에서 쿠키 추출

1. **Chrome 브라우저**에서 https://x.com 로그인
2. **F12** (개발자 도구) 열기
3. **Application** 탭 → **Cookies** → **https://x.com**
4. 필요한 쿠키 값 복사:
   - `auth_token` - 인증 토큰 (필수)
   - `ct0` - CSRF 토큰 (필수)
   - `twid` - 사용자 ID (선택)

**쿠키 복사 방법:**
- 쿠키 이름 클릭 → Value 열의 값 더블클릭 → Ctrl+C (복사)

---

### 2단계: 프로그램 실행

```bash
python quote_extractor_cookie_input.py
```

---

### 3단계: 쿠키 붙여넣기

프로그램이 각 쿠키를 물어보면 **Ctrl+V**로 붙여넣기:

```
1. auth_token 쿠키 값을 입력하세요:
   (Chrome에서 auth_token 값을 복사하여 붙여넣기)
AUTH_TOKEN: [Ctrl+V로 붙여넣기]
✅ AUTH_TOKEN 입력 완료

2. ct0 쿠키 값을 입력하세요:
   (Chrome에서 ct0 값을 복사하여 붙여넣기)
CT0: [Ctrl+V로 붙여넣기]
✅ CT0 입력 완료

3. twid 쿠키 값 (선택, 엔터로 건너뛰기):
TWID: [선택사항 - 엔터로 건너뛰기 가능]

4. guest_id 쿠키 값 (선택, 엔터로 건너뛰기):
GUEST_ID: [선택사항 - 엔터로 건너뛰기 가능]
```

---

### 4단계: .env 저장 여부 선택

```
입력한 쿠키를 .env 파일로 저장하시겠습니까? (y/n, 엔터 = n): y
[성공] 쿠키를 .env 파일로 저장했습니다
[안내] 다음 실행 시 quote_extractor_env.py로 자동 로그인 가능
```

**저장하면:**
- `.env` 파일 생성됨
- 다음부터는 `quote_extractor_env.py` 실행 시 자동 로그인

**저장 안 하면:**
- 이번만 사용하고 끝
- 다음에 다시 쿠키 입력 필요

---

### 5단계: 인용글 추출

```
인용글 URL: https://x.com/user/status/123/quotes
저장 파일명 (엔터 = quotes.csv): ⏎
최대 스크롤 (엔터 = 무제한): ⏎
브라우저 숨김? (y/n, 엔터 = n): ⏎

============================================================
[정보] Chrome 드라이버 시작...
[정보] Twitter 접속 중...
[정보] 쿠키 로드 중...
[성공] 3개 쿠키 로드 완료
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

## 📋 필수 vs 선택 쿠키

| 쿠키 이름 | 필수 여부 | 설명 |
|----------|----------|------|
| **auth_token** | ✅ 필수 | Twitter 로그인 인증 토큰 |
| **ct0** | ✅ 필수 | CSRF 보호 토큰 |
| **twid** | ⏭️ 선택 | 사용자 ID (안정성 향상) |
| **guest_id** | ⏭️ 선택 | 게스트 ID (선택) |

**최소 요구사항**: `auth_token` + `ct0` 2개만 입력하면 작동합니다!

---

## 🎬 사용 예시

### 예시 1: 최소 입력 (필수 쿠키만)

```bash
$ python quote_extractor_cookie_input.py

📌 필수 쿠키 (반드시 필요):

1. auth_token 쿠키 값을 입력하세요:
AUTH_TOKEN: abc123def456...
✅ AUTH_TOKEN 입력 완료

2. ct0 쿠키 값을 입력하세요:
CT0: 9876543210abcd...
✅ CT0 입력 완료

📝 선택 쿠키 (없으면 엔터):

3. twid 쿠키 값 (선택, 엔터로 건너뛰기):
TWID: ⏎
⏭️  TWID 건너뜀

4. guest_id 쿠키 값 (선택, 엔터로 건너뛰기):
GUEST_ID: ⏎
⏭️  GUEST_ID 건너뜀

입력한 쿠키를 .env 파일로 저장하시겠습니까? (y/n): n

인용글 URL: https://x.com/user/status/123/quotes
...
[성공] 쿠키로 로그인 성공!
```

---

### 예시 2: 전체 입력 + .env 저장

```bash
$ python quote_extractor_cookie_input.py

📌 필수 쿠키 (반드시 필요):

1. auth_token 쿠키 값을 입력하세요:
AUTH_TOKEN: c2e0b648fc76a25e0a6a47815484357e67b40798
✅ AUTH_TOKEN 입력 완료

2. ct0 쿠키 값을 입력하세요:
CT0: f0c0e186675d20a2697fac82e5264f75507f1ca1088dc20c621c5a057b171ecf...
✅ CT0 입력 완료

📝 선택 쿠키 (없으면 엔터):

3. twid 쿠키 값 (선택, 엔터로 건너뛰기):
TWID: u%3D1988521787395895296
✅ TWID 입력 완료

4. guest_id 쿠키 값 (선택, 엔터로 건너뛰기):
GUEST_ID: v1%3A167890123456789012
✅ GUEST_ID 입력 완료

입력한 쿠키를 .env 파일로 저장하시겠습니까? (y/n): y
[성공] 쿠키를 .env 파일로 저장했습니다: /path/to/.env
[안내] 다음 실행 시 quote_extractor_env.py로 자동 로그인 가능

인용글 URL: https://x.com/user/status/456/quotes
...
[성공] 쿠키로 로그인 성공!
```

---

## 🆚 버전 비교

| 기능 | CLI 입력 버전 | .env 파일 버전 | 세션 저장 버전 |
|------|-------------|--------------|--------------|
| **파일명** | `quote_extractor_cookie_input.py` | `quote_extractor_env.py` | `quote_extractor_session.py` |
| **쿠키 입력** | 터미널에서 붙여넣기 | .env 파일 편집 | 자동 (첫 로그인만) |
| **사전 준비** | 없음 (바로 실행) | .env 파일 생성 | 첫 로그인 필요 |
| **편의성** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **보안** | 높음 (저장 선택) | 보통 (파일 저장) | 보통 (자동 저장) |
| **추천 상황** | 일회성 사용 | 반복 사용 | 매일 사용 |

---

## 💡 사용 시나리오

### 시나리오 1: 처음 사용 (테스트)

```bash
# 처음 사용 - 쿠키 직접 입력
python quote_extractor_cookie_input.py
# 쿠키 입력 → .env 저장 안 함 → 추출

# 잘 작동하면 다음부터 자동화
python quote_extractor_cookie_input.py
# 쿠키 입력 → .env 저장 함 (y) → 추출

# 이제 자동 로그인 버전 사용
python quote_extractor_env.py
# 쿠키 자동 로드 → 추출
```

---

### 시나리오 2: 여러 계정 사용

```bash
# 계정 A로 추출
python quote_extractor_cookie_input.py
# 계정 A 쿠키 입력 → .env 저장 안 함

# 계정 B로 추출
python quote_extractor_cookie_input.py
# 계정 B 쿠키 입력 → .env 저장 안 함
```

---

### 시나리오 3: 공용 PC

```bash
# 공용 PC에서 사용
python quote_extractor_cookie_input.py
# 쿠키 입력 → .env 저장 안 함 ← 중요!
# 추출 완료

# 쿠키 파일이 남지 않아 안전
```

---

## 🔒 보안 고려사항

### ✅ 안전한 사용

1. **터미널 히스토리 주의**
   - 쿠키 값은 터미널 히스토리에 남을 수 있음
   - 공용 PC에서는 .env 저장 안 함 권장

2. **.env 저장 선택**
   - 개인 PC: .env 저장 → 편리
   - 공용 PC: .env 저장 안 함 → 안전

3. **Git 커밋 방지**
   - `.gitignore`에 `.env` 포함됨
   - 실수로 커밋될 위험 없음

### ⚠️ 주의사항

- **쿠키 유효 기간**: 수 주 ~ 수 개월
- **만료 시**: Chrome에서 재로그인 → 새 쿠키 추출
- **다른 사람과 공유 금지**: 쿠키 = 로그인 인증

---

## 🐛 트러블슈팅

### 문제 1: "AUTH_TOKEN은 필수입니다!"

**원인:** 빈 값 입력 또는 엔터만 누름

**해결:**
1. Chrome 개발자 도구 다시 열기
2. Application → Cookies → https://x.com
3. `auth_token` 값 정확히 복사
4. 터미널에 붙여넣기

---

### 문제 2: "쿠키가 유효하지 않습니다"

**원인:**
- 쿠키 만료
- 잘못된 값 복사
- 로그아웃됨

**해결:**
```bash
# Chrome에서 재로그인
# 새 쿠키 복사
# 다시 실행
python quote_extractor_cookie_input.py
```

---

### 문제 3: 쿠키 값이 너무 길어서 복사 실패

**증상:** ct0 값이 매우 긴 경우 (100자 이상)

**해결:**
```
1. Chrome 개발자 도구에서 쿠키 값 클릭
2. 우클릭 → Edit "Value"
3. Ctrl+A (전체 선택) → Ctrl+C (복사)
4. 터미널에 Ctrl+V (붙여넣기)
```

---

### 문제 4: .env 파일이 이미 존재

**증상:**
```
[성공] 쿠키를 .env 파일로 저장했습니다
```
그런데 기존 .env 내용이 덮어씌워짐

**해결:** 기존 .env 백업
```bash
# 기존 .env 백업
cp .env .env.backup

# 프로그램 실행
python quote_extractor_cookie_input.py
```

---

## 🔄 다음 단계

### 이 프로그램 사용 후

1. **쿠키를 .env로 저장했다면:**
   ```bash
   # 다음부터는 자동 로그인 버전 사용
   python quote_extractor_env.py
   ```

2. **저장 안 했다면:**
   ```bash
   # 매번 쿠키 입력하거나
   python quote_extractor_cookie_input.py

   # .env 파일 수동 작성
   nano .env
   # 또는
   python quote_extractor_env.py
   ```

3. **매일 사용한다면:**
   ```bash
   # 세션 저장 버전으로 업그레이드
   python quote_extractor_session.py
   # 첫 로그인 후 자동 로그인 (30일간)
   ```

---

## 📊 입력 시간 비교

| 방법 | 첫 실행 | 두 번째 실행 | 열 번째 실행 |
|------|--------|------------|------------|
| **CLI 입력** | 2분 | 2분 | 2분 |
| **CLI → .env 저장** | 2분 | 10초 | 10초 |
| **.env 파일** | 3분 (파일 작성) | 10초 | 10초 |
| **세션 저장** | 2분 (로그인) | 5초 | 5초 |

**결론**: 일회성 사용은 CLI 입력, 반복 사용은 .env 또는 세션 저장 추천!

---

## 🎯 권장 사용 흐름

```
첫 사용
  ↓
CLI 입력 버전으로 테스트
  ↓
작동 확인
  ↓
반복 사용 필요?
  ↓ YES          ↓ NO
.env로 저장    그대로 사용
  ↓
quote_extractor_env.py 사용
  ↓
매일 사용?
  ↓ YES
세션 저장 버전으로 업그레이드
(quote_extractor_session.py)
```

---

## 🔗 관련 문서

- `README_COOKIES.md` - 쿠키 추출 상세 가이드
- `README_ENV.md` - .env 파일 사용 가이드 (작성 예정)
- `README_SESSION.md` - 세션 저장 가이드
- `.env.example` - .env 파일 템플릿

---

## 📝 요약

**가장 간단한 3단계:**

1. **Chrome에서 쿠키 복사**
   - F12 → Application → Cookies → https://x.com
   - auth_token, ct0 복사

2. **프로그램 실행 & 붙여넣기**
   ```bash
   python quote_extractor_cookie_input.py
   ```
   - 쿠키 붙여넣기

3. **추출**
   - URL 입력 → 자동 추출

**복잡한 파일 편집 없이 바로 시작!** 🎉
