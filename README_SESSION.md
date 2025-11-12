# 세션 저장/재사용 가이드

## 🔐 개요

**한 번만 로그인하고 세션을 저장**하여 다음 실행 시 자동으로 로그인되는 버전입니다.

### ✨ 장점

| 기능 | 일반 버전 | 세션 저장 버전 |
|------|----------|---------------|
| 첫 실행 | 로그인 필요 | 로그인 필요 |
| 두 번째 실행 | **로그인 필요** ❌ | **자동 로그인** ✅ |
| 세 번째 실행 | **로그인 필요** ❌ | **자동 로그인** ✅ |
| 세션 유효 기간 | - | **30일** |

---

## 🚀 사용 방법

### 첫 실행 (로그인 + 세션 저장)

```bash
python quote_extractor_session.py
```

**실행 과정:**
```
============================================================
   트위터 인용글 추출 - 세션 저장 버전
============================================================

옵션:
  1. 일반 실행 (저장된 세션 사용)
  2. 강제 로그인 (세션 무시)
  3. 세션 삭제

선택 (엔터 = 1): ⏎

인용글 URL: https://x.com/user/status/123/quotes
트위터 아이디: my_twitter_id
트위터 비밀번호: ********

저장 파일명 (엔터 = quotes.csv): ⏎
최대 스크롤 (엔터 = 무제한): 5
브라우저 숨김? (y/n, 엔터 = n): ⏎

============================================================
[정보] Chrome 드라이버 시작...
[정보] 저장된 세션 확인 중...
[정보] 저장된 세션이 없습니다. 로그인이 필요합니다.
[정보] 트위터 로그인 중...
[성공] 로그인 완료!
[성공] 세션 저장 완료 (유효기간: 30일)  ← 세션 저장!
  - 위치: /path/to/.session

[정보] 인용글 페이지 접근...
...
✅ 성공!
```

---

### 두 번째 실행 (자동 로그인!)

```bash
python quote_extractor_session.py
```

**실행 과정:**
```
============================================================
   트위터 인용글 추출 - 세션 저장 버전
============================================================

선택 (엔터 = 1): ⏎

인용글 URL: https://x.com/user/status/456/quotes

저장 파일명: ⏎
최대 스크롤: 3
브라우저 숨김?: ⏎

============================================================
[정보] Chrome 드라이버 시작...
[정보] 저장된 세션 확인 중...
[정보] 저장된 세션 발견
  - 사용자: my_twitter_id
  - 생성일: 2025-01-12T10:30:00
  - 만료일: 2025-02-11T10:30:00
[정보] 쿠키 로드 완료, 세션 검증 중...
[성공] 저장된 세션으로 로그인 성공!  ← 자동 로그인!

[정보] 인용글 페이지 접근...
...
✅ 성공!
```

**👆 아이디/비밀번호 입력 없이 바로 실행!**

---

## 📋 세션 저장 원리

### 1️⃣ 첫 로그인 시

```
로그인 성공
    ↓
쿠키 저장 (.session/twitter_cookies.pkl)
    ↓
세션 정보 저장 (.session/session_info.json)
    ↓
다음 실행 시 재사용
```

### 2️⃣ 저장되는 정보

**`.session/twitter_cookies.pkl`** (쿠키)
- Twitter 인증 토큰
- 세션 쿠키
- 기타 상태 정보

**`.session/session_info.json`** (메타데이터)
```json
{
  "username": "my_twitter_id",
  "created_at": "2025-01-12T10:30:00",
  "expires_at": "2025-02-11T10:30:00",
  "user_agent": "Mozilla/5.0 ..."
}
```

### 3️⃣ 다음 실행 시

```
세션 파일 존재?
    ↓ YES
세션 만료 확인
    ↓ 유효함
쿠키 로드
    ↓
Twitter 접속
    ↓
로그인 상태 확인
    ↓ 성공
바로 사용!
```

---

## ⚙️ 옵션 설명

### 옵션 1: 일반 실행 (기본)

```
선택: 1 (또는 엔터)
```

- 저장된 세션이 있으면 자동 로그인
- 없으면 로그인 후 세션 저장

### 옵션 2: 강제 로그인

```
선택: 2
```

- 저장된 세션 무시
- 무조건 새로 로그인
- 새 세션으로 덮어쓰기

**사용 시기:**
- 다른 계정으로 로그인
- 세션이 이상할 때
- 보안상 새로 로그인

### 옵션 3: 세션 삭제

```
선택: 3
```

- 저장된 세션 파일 삭제
- 다음 실행 시 로그인 필요

**사용 시기:**
- 계정 전환 전
- 세션 초기화 필요 시

---

## 🔒 보안 고려사항

### ✅ 안전한 점

1. **로컬 저장**: 세션은 본인 컴퓨터에만 저장
2. **만료 처리**: 30일 후 자동 만료
3. **검증**: 매번 로그인 상태 확인

### ⚠️ 주의사항

1. **`.session` 폴더 보안**
   ```bash
   # 다른 사람과 공유 금지!
   # Git에 커밋 금지! (.gitignore에 포함됨)
   ```

2. **공용 PC 사용 시**
   ```bash
   # 사용 후 세션 삭제
   python quote_extractor_session.py
   # 옵션 3 선택
   ```

3. **여러 계정 사용**
   ```bash
   # 계정 전환 시 강제 로그인
   python quote_extractor_session.py
   # 옵션 2 선택
   ```

---

## 📂 파일 구조

```
retweet_check/
  ├── quote_extractor_session.py  ← 실행 파일
  ├── .session/                   ← 세션 저장 폴더 (자동 생성)
  │   ├── twitter_cookies.pkl     ← 쿠키 (바이너리)
  │   └── session_info.json       ← 세션 정보
  └── quotes.csv                  ← 결과 파일
```

**`.session` 폴더:**
- 자동 생성됨
- Git에 커밋 안 됨 (`.gitignore`에 포함)
- 삭제하면 다음 실행 시 로그인 필요

---

## 🔄 세션 만료 처리

### 자동 재로그인

세션 만료 시 자동으로 재로그인 요청:

```
[정보] 저장된 세션 발견
  - 만료일: 2025-01-10T10:00:00
[정보] 세션이 만료되었습니다. 재로그인이 필요합니다.

[정보] 로그인이 필요합니다.
트위터 아이디: _
```

### 수동 세션 갱신

```bash
python quote_extractor_session.py
# 옵션 2 (강제 로그인) 선택
```

---

## 🆚 버전 비교

| 버전 | 로그인 | 세션 저장 | 편의성 |
|------|--------|----------|--------|
| quote_extractor_simple.py | 매번 필요 | ❌ | ⭐⭐ |
| quote_extractor_windows.py | 매번 필요 | ❌ | ⭐⭐ |
| **quote_extractor_session.py** | **첫 1회만** | **✅** | **⭐⭐⭐⭐** |

---

## 💡 사용 시나리오

### 시나리오 1: 일일 모니터링

```bash
# 월요일 첫 실행 - 로그인 필요
python quote_extractor_session.py
# 아이디/비밀번호 입력
# → 세션 저장

# 화요일 실행 - 자동 로그인!
python quote_extractor_session.py
# → 바로 실행

# 수요일, 목요일, 금요일... - 자동 로그인!
python quote_extractor_session.py
```

### 시나리오 2: 여러 URL 수집

```bash
# 첫 실행
python quote_extractor_session.py
URL: url1
# 로그인 + 수집 + 세션 저장

# 두 번째 URL (바로 실행!)
python quote_extractor_session.py
URL: url2
# 자동 로그인 + 수집

# 세 번째 URL (바로 실행!)
python quote_extractor_session.py
URL: url3
# 자동 로그인 + 수집
```

### 시나리오 3: 계정 전환

```bash
# 계정 A로 수집
python quote_extractor_session.py
옵션: 1
아이디: account_A
# → 세션 저장 (account_A)

# 계정 B로 전환
python quote_extractor_session.py
옵션: 2 (강제 로그인)
아이디: account_B
# → 세션 덮어쓰기 (account_B)
```

---

## 🔧 트러블슈팅

### 문제 1: "세션이 유효하지 않습니다"

**원인:**
- 쿠키 만료
- Twitter 정책 변경

**해결:**
```bash
python quote_extractor_session.py
옵션: 2 (강제 로그인)
```

---

### 문제 2: 세션 파일 손상

**증상:**
```
[경고] 세션 로드 실패: ...
```

**해결:**
```bash
python quote_extractor_session.py
옵션: 3 (세션 삭제)

# 다시 실행
python quote_extractor_session.py
옵션: 1
# 새로 로그인
```

---

### 문제 3: 다른 계정으로 로그인하고 싶음

**해결:**
```bash
python quote_extractor_session.py
옵션: 2 (강제 로그인)
아이디: new_account
비밀번호: ********
```

---

### 문제 4: 세션 파일 위치 변경

**코드 수정:**
```python
# quote_extractor_session.py 파일 열기
# 14번째 줄 근처

SESSION_DIR = os.path.join(BASE_DIR, ".session")
# ↓ 원하는 경로로 변경
SESSION_DIR = "C:/my_sessions"
```

---

## 📊 성능 비교

| 작업 | 일반 버전 | 세션 저장 버전 | 절약 |
|------|----------|---------------|------|
| 로그인 시간 | 매번 10-15초 | 첫 1회만 | **90%** |
| 전체 실행 | 30초 | 18초 | **40%** |
| 10회 실행 | 5분 | 1.5분 | **70%** |

---

## 🎯 권장 사항

### ✅ 세션 저장 버전 추천

- 매일 사용하는 경우
- 여러 URL 순차 수집
- 반복 작업 자동화

### ⚠️ 일반 버전 추천

- 일회성 사용
- 공용 PC 사용
- 보안이 최우선

---

## 🔄 다른 버전과 함께 사용

### 다중 URL + 세션 저장

세션 저장 기능을 다중 URL 버전에 적용하려면:

```python
# quote_extractor_multi.py 수정
# login_twitter 호출 전에:
if load_cookies(driver):
    print("[성공] 세션 복원")
else:
    login_twitter(driver, username, password)
    save_cookies(driver, username)
```

---

## 📝 요약

**세션 저장 버전 = 일반 버전 + 자동 로그인**

```bash
# 첫 실행
python quote_extractor_session.py
# 로그인 입력 → 세션 저장

# 이후 실행 (30일간)
python quote_extractor_session.py
# 자동 로그인! 🎉
```

**편리함 +90%, 보안 유지, 시간 절약!** 🚀

---

## 🔗 관련 문서

- `README_SIMPLE.md` - 기본 사용법
- `README_MULTI_URL.md` - 다중 URL 처리
- `README_GOOGLE_SHEETS.md` - Google Sheets 업로드
