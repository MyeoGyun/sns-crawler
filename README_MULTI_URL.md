# 다중 URL 처리 가이드

## 🚀 개요

**하나의 브라우저 세션**에서 여러 인용글 URL을 순차적으로 처리하는 도구입니다.

### ✨ 주요 특징

| 기능 | 설명 |
|------|------|
| 🔐 **단일 로그인** | 한 번만 로그인, 여러 URL 처리 |
| 🌐 **단일 브라우저** | 새 창 열지 않고 URL만 변경 |
| 📊 **통합 저장** | 모든 결과를 하나의 CSV에 저장 |
| 📍 **출처 추적** | 어느 URL에서 추출되었는지 기록 |
| ⚡ **효율적** | 브라우저 재시작 오버헤드 없음 |

---

## 📋 사용 방법

### 방법 1: 여러 URL 직접 입력 (쉼표로 구분)

```bash
python quote_extractor_multi.py \
  --urls "https://x.com/user1/status/123/quotes,https://x.com/user2/status/456/quotes" \
  --username "your_twitter_id" \
  --password "your_password" \
  --output "all_quotes.csv"
```

**Windows CMD:**
```cmd
python quote_extractor_multi.py ^
  --urls "https://x.com/user1/status/123/quotes,https://x.com/user2/status/456/quotes" ^
  --username "your_id" ^
  --password "your_password"
```

---

### 방법 2: 파일에서 URL 목록 읽기 ⭐ (추천)

**1단계: URL 목록 파일 생성**

`urls.txt` 파일 생성:
```
https://x.com/lottewellfood/status/1983036567561351382/quotes
https://x.com/another_user/status/1234567890123456789/quotes
https://x.com/third_user/status/9876543210987654321/quotes
```

**팁:**
- 한 줄에 하나씩 URL 입력
- `#`으로 시작하는 줄은 주석 (무시됨)
- 빈 줄은 자동으로 무시됨

**2단계: 실행**

```bash
python quote_extractor_multi.py \
  --url-file urls.txt \
  --username "your_twitter_id" \
  --password "your_password" \
  --max-scrolls 10 \
  --output "all_quotes.csv"
```

---

### 방법 3: 단일 URL 처리

```bash
python quote_extractor_multi.py \
  --url "https://x.com/lottewellfood/status/1983036567561351382/quotes" \
  --username "your_id" \
  --password "your_password"
```

---

## ⚙️ 옵션 설명

### 필수 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--url` | 단일 URL | `--url "https://..."` |
| `--urls` | 여러 URL (쉼표 구분) | `--urls "url1,url2,url3"` |
| `--url-file` | URL 목록 파일 | `--url-file urls.txt` |
| `--username` | 트위터 ID | `--username "my_id"` |
| `--password` | 트위터 비밀번호 | `--password "my_pw"` |

**⚠️ --url, --urls, --url-file 중 하나만 선택**

### 선택 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--output` | quotes_multi.csv | 출력 CSV 파일명 |
| `--max-scrolls` | 무제한 | 각 URL당 최대 스크롤 횟수 |
| `--scroll-delay` | 2.0 | 스크롤 간 대기시간(초) |
| `--url-delay` | 3.0 | URL 전환 간 대기시간(초) |
| `--headless` | false | 브라우저 숨김 모드 |

---

## 📊 출력 CSV 형식

기존 컬럼 + **source_url** 컬럼 추가:

```csv
status_id,url,author_handle,text,hashtags,...,source_url
1234567890,https://x.com/user/status/1234567890,@user,"본문...",#태그,...,https://x.com/original/status/123/quotes
```

**source_url**: 해당 인용글이 어느 URL에서 추출되었는지 기록

---

## 🎯 실행 예시

### 예시 1: 빠른 테스트 (3개 URL)

```bash
python quote_extractor_multi.py \
  --urls "url1,url2,url3" \
  --username "my_id" \
  --password "my_pw" \
  --max-scrolls 3 \
  --output "test.csv"
```

**실행 과정:**
```
[정보] 총 3개 URL 처리 예정
  1. url1
  2. url2
  3. url3

[정보] Chrome 드라이버 시작...
[정보] 트위터 로그인...
[성공] 로그인 완료

============================================================

[1/3] 처리 중...
[정보] 인용글 페이지 접근: url1
  → 15개 추출
  → 다음 URL 이동까지 3.0초 대기...

[2/3] 처리 중...
[정보] 인용글 페이지 접근: url2
  → 22개 추출
  → 다음 URL 이동까지 3.0초 대기...

[3/3] 처리 중...
[정보] 인용글 페이지 접근: url3
  → 18개 추출

============================================================
[완료] 전체 처리 완료: 총 55개 인용글 추출

[완료] CSV 저장: test.csv
  - 총 55개 레코드
```

---

### 예시 2: 파일로 대량 처리

**urls.txt:**
```
# 2025년 1월 캠페인
https://x.com/brand/status/111/quotes
https://x.com/brand/status/222/quotes
https://x.com/brand/status/333/quotes
https://x.com/brand/status/444/quotes
https://x.com/brand/status/555/quotes

# 2025년 2월 캠페인
https://x.com/brand/status/666/quotes
https://x.com/brand/status/777/quotes
```

**실행:**
```bash
python quote_extractor_multi.py \
  --url-file urls.txt \
  --username "my_id" \
  --password "my_pw" \
  --output "campaign_quotes.csv" \
  --headless
```

---

## 🔧 장점 vs 단점

### ✅ 장점

| 항목 | 다중 URL 버전 | 기존 버전 (단일 URL) |
|------|--------------|---------------------|
| 로그인 횟수 | **1회** | URL마다 반복 |
| 브라우저 재시작 | **없음** | URL마다 재시작 |
| 속도 | **빠름** | 느림 |
| 결과 통합 | **자동** | 수동 병합 필요 |
| 출처 추적 | **자동** | 수동 기록 필요 |

### ⚠️ 주의사항

1. **URL 간 대기 시간**
   - 너무 빠르게 전환 시 차단 위험
   - `--url-delay` 최소 3초 권장

2. **세션 유지**
   - 긴 시간 실행 시 세션 만료 가능
   - 10개 이하 URL 처리 권장

3. **에러 처리**
   - 특정 URL 실패 시 다음 URL 계속 진행
   - 전체 결과에는 성공한 것만 포함

---

## 🆚 버전 비교

| 스크립트 | 용도 | URL 수 | 브라우저 |
|---------|------|--------|---------|
| `quote_extractor.py` | 기본 (Linux/Mac) | 1개 | 단일 세션 |
| `quote_extractor_windows.py` | Windows 최적화 | 1개 | 단일 세션 |
| `quote_extractor_multi.py` | **다중 URL 처리** | **여러 개** | **단일 세션 재사용** |
| `quote_extractor_gsheet.py` | Google Sheets 업로드 | 1개 | 단일 세션 |

---

## 📝 URLs 파일 작성 팁

### 기본 형식
```
https://x.com/user1/status/123/quotes
https://x.com/user2/status/456/quotes
```

### 주석 활용
```
# 1월 캠페인
https://x.com/brand/status/111/quotes
https://x.com/brand/status/222/quotes

# 2월 캠페인
https://x.com/brand/status/333/quotes
```

### Excel/Google Sheets에서 생성

1. 스프레드시트에 URL 목록 작성
2. 한 열에 모든 URL 입력
3. 텍스트 파일로 저장 (`.txt`)

---

## 🔄 워크플로우 예시

### 시나리오: 월별 이벤트 분석

```bash
# 1월
python quote_extractor_multi.py \
  --url-file jan_events.txt \
  --username "analyst_id" \
  --password "pw" \
  --output "jan_quotes.csv"

# 2월
python quote_extractor_multi.py \
  --url-file feb_events.txt \
  --username "analyst_id" \
  --password "pw" \
  --output "feb_quotes.csv"

# 결과 병합 (Python pandas 또는 Excel)
```

---

## 🚨 트러블슈팅

### 1. "처리할 URL이 없습니다"

**원인:** URL 파일이 비어있거나 형식 오류

**해결:**
```bash
# 파일 내용 확인
cat urls.txt  # Linux/Mac
type urls.txt  # Windows

# 빈 줄과 주석 제외하고 실제 URL이 있는지 확인
```

---

### 2. 중간에 멈춤

**원인:** 특정 URL 처리 중 에러

**해결:**
- 에러 메시지 확인
- 해당 URL 제거 후 재실행
- `--url-delay` 값 증가 (예: 5.0)

---

### 3. 세션 만료

**원인:** 너무 많은 URL 처리 시 로그인 세션 만료

**해결:**
- URL을 5-10개씩 나눠서 처리
- 파일을 여러 개로 분할

---

## 💡 베스트 프랙티스

1. **첫 테스트**
   - 2-3개 URL로 먼저 테스트
   - `--max-scrolls 3` 설정
   - `--headless` 제외 (브라우저 확인)

2. **본격 실행**
   - URL 목록 파일 사용
   - `--headless` 옵션 추가
   - `--url-delay 3.0` 이상 설정

3. **대량 처리**
   - 10개 단위로 분할
   - 시간대 분산 (차단 방지)

---

## 📞 지원

문제 발생 시:
1. 에러 메시지 전체 복사
2. 사용한 명령어 복사
3. URL 개수 확인
4. urls.txt 내용 확인 (개인정보 제거 후)

---

**이제 여러 인용글 URL을 효율적으로 처리할 수 있습니다!** 🚀
