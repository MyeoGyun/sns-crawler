# 트위터/X 인용글(Quotes) 추출 도구

## 📖 개요

트위터/X의 특정 게시글에 달린 인용글(Quotes)을 자동으로 추출하여 CSV 파일로 저장하는 CLI 도구입니다.

## ✨ 주요 기능

- 인용글 페이지 자동 스크롤 및 데이터 수집
- 사용자 아이디, 본문, URL, 해시태그, 미디어 등 추출
- CSV 형식으로 저장 (Excel/Google Sheets 호환)
- 중복 제거 및 무한 스크롤 지원

## 📋 추출 데이터

| 필드 | 설명 | 예시 |
|------|------|------|
| `status_id` | 트윗 고유 ID | 1234567890 |
| `url` | 절대 URL | https://x.com/user/status/1234567890 |
| `author_handle` | 작성자 핸들 | @user_name |
| `text` | 본문 (해시태그 포함) | "좋아요! #해시태그" |
| `hashtags` | 해시태그 리스트 | ["#해시태그", "#태그2"] |
| `time_iso_utc` | ISO 타임스탬프 (UTC) | 2025-01-15T10:00:00.000Z |
| `has_media` | 미디어 존재 여부 | true / false |
| `media_urls` | 미디어 URL 리스트 | ["https://pbs.twimg.com/..."] |
| `is_quote` | 인용 여부 | true / false |
| `quote_status_id` | 인용한 트윗 ID | 9999999999 또는 "인용X" |
| `quote_time_iso_utc` | 인용한 트윗 타임스탬프 | 2025-01-14T08:00:00.000Z 또는 "인용X" |

## 🚀 사용 방법

### 1. 의존성 설치

```bash
pip install selenium
```

Chrome 및 ChromeDriver가 설치되어 있어야 합니다.

### 2. 기본 사용법

```bash
python quote_extractor.py \
  --url "https://x.com/lottewellfood/status/1983036567561351382/quotes" \
  --username "your_twitter_id" \
  --password "your_password" \
  --output "quotes_result.csv"
```

### 3. 고급 옵션

```bash
python quote_extractor.py \
  --url "인용글_페이지_URL" \
  --username "트위터_아이디" \
  --password "트위터_비밀번호" \
  --output "저장할_파일명.csv" \
  --max-scrolls 50 \              # 최대 스크롤 횟수 제한
  --headless \                     # 브라우저 숨김 모드
  --scroll-delay 3.0               # 스크롤 간 대기시간(초)
```

### 4. 옵션 설명

| 옵션 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `--url` | ✅ | 인용글 페이지 URL | - |
| `--username` | ✅ | 트위터 로그인 ID | - |
| `--password` | ✅ | 트위터 비밀번호 | - |
| `--output` | | 출력 CSV 파일 경로 | quotes.csv |
| `--max-scrolls` | | 최대 스크롤 횟수 (무제한: 생략) | 무제한 |
| `--headless` | | 헤드리스 모드 (브라우저 숨김) | false |
| `--scroll-delay` | | 스크롤 간 대기시간(초) | 2.0 |

## 📊 출력 예시

**CSV 파일 (quotes.csv):**
```csv
status_id,url,author_handle,text,hashtags,time_iso_utc,has_media,media_urls,is_quote,quote_status_id,quote_time_iso_utc
1234567890,https://x.com/user_A/status/1234567890,@user_A,"사실 전 호지차도 사랑합니다 #나뚜루호지차 #나뚜루미식파","[""#나뚜루호지차"",""#나뚜루미식파""]",2025-01-15T10:00:00.000Z,true,"[""https://pbs.twimg.com/media/xxx.jpg""]",true,9999999999,2025-01-14T08:00:00.000Z
5555555555,https://x.com/user_B/status/5555555555,@user_B,"좋아요!","[]",2025-01-15T11:00:00.000Z,false,인용X,false,인용X,인용X
```

## 🔧 트러블슈팅

### 1. 로그인 실패
- 트위터 ID/비밀번호를 확인하세요
- 2단계 인증(2FA)이 활성화된 경우 현재 미지원
- VPN 사용 시 차단될 수 있습니다

### 2. ChromeDriver 오류
```bash
# ChromeDriver 설치 확인
which chromedriver

# Chrome 버전 확인
google-chrome --version
# 또는
chromium --version
```

ChromeDriver와 Chrome 버전이 일치해야 합니다.

### 3. 트윗이 추출되지 않음
- `--headless` 옵션을 제거하고 브라우저를 보면서 실행
- `--scroll-delay` 값을 늘려보세요 (예: 5.0)
- 트위터 페이지 구조가 변경되었을 수 있습니다 (개발자에게 문의)

### 4. 차단 방지
- `--scroll-delay`를 높게 설정 (3.0 이상)
- `--max-scrolls`로 한 번에 너무 많이 수집하지 않기
- 여러 번 나눠서 실행

## 📝 주의사항

1. **트위터 이용약관 준수**: 개인적인 용도로만 사용하세요
2. **속도 제한**: 너무 빠르게 수집 시 차단될 수 있습니다
3. **데이터 정확성**: DOM 구조 변경 시 일부 필드가 누락될 수 있습니다
4. **비밀번호 보안**: 명령어 기록에 비밀번호가 남을 수 있으니 주의하세요

## 🔄 다음 단계

CLI 테스트가 완료되면 GUI 버전도 개발 예정입니다.

## 📞 지원

문제가 발생하면 다음 정보와 함께 개발자에게 문의하세요:
- 오류 메시지
- 실행 명령어
- Python 버전, Chrome 버전
