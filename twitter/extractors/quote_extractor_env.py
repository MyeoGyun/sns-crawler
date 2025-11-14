#!/usr/bin/env python3
# quote_extractor_env.py
# .env 파일에서 쿠키를 로드하여 자동 로그인
#
# 사용법:
# 1. .env.example을 .env로 복사
# 2. .env 파일에 쿠키 값 입력
# 3. python quote_extractor_env.py 실행

import os
import time
import csv
import json
import getpass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    AUTO_DRIVER = True
except ImportError:
    AUTO_DRIVER = False

# -----------------------
# 설정값
# -----------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SCROLL_PAUSE = 2.0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

# -----------------------
# .env 파일 로드
# -----------------------
def load_env():
    """
    .env 파일에서 환경변수 로드

    Returns:
        dict: 환경변수 딕셔너리
    """
    env_vars = {}

    if not os.path.exists(ENV_FILE):
        print(f"[경고] .env 파일이 없습니다: {ENV_FILE}")
        print("[안내] .env.example을 .env로 복사하고 쿠키 값을 입력하세요")
        return env_vars

    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 주석과 빈 줄 무시
                if not line or line.startswith("#"):
                    continue

                # KEY=VALUE 파싱
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if value:  # 빈 값 무시
                        env_vars[key] = value

        print(f"[정보] .env 파일 로드 완료: {len(env_vars)}개 항목")
        return env_vars

    except Exception as e:
        print(f"[오류] .env 파일 로드 실패: {e}")
        return {}

# -----------------------
# 쿠키 로드 및 적용
# -----------------------
def load_cookies_from_env(driver, env_vars):
    """
    .env 파일의 쿠키를 Selenium에 적용

    Args:
        driver: Selenium WebDriver
        env_vars: 환경변수 딕셔너리

    Returns:
        bool: 성공 여부
    """
    try:
        # Twitter 홈페이지로 먼저 이동 (쿠키 도메인 일치 필요)
        print("[정보] Twitter 접속 중...")
        driver.get("https://x.com")
        time.sleep(2)

        # 방법 1: COOKIES_JSON 사용 (전체 쿠키 JSON)
        if "COOKIES_JSON" in env_vars and env_vars["COOKIES_JSON"]:
            print("[정보] COOKIES_JSON에서 쿠키 로드 중...")
            try:
                cookies = json.loads(env_vars["COOKIES_JSON"])

                for cookie in cookies:
                    try:
                        # 필수 필드만 추출
                        cookie_dict = {
                            "name": cookie.get("name"),
                            "value": cookie.get("value"),
                        }

                        # 선택 필드
                        if "domain" in cookie:
                            cookie_dict["domain"] = cookie["domain"]
                        if "path" in cookie:
                            cookie_dict["path"] = cookie["path"]
                        if "secure" in cookie:
                            cookie_dict["secure"] = cookie["secure"]
                        if "httpOnly" in cookie:
                            cookie_dict["httpOnly"] = cookie["httpOnly"]

                        driver.add_cookie(cookie_dict)
                    except Exception as e:
                        print(f"[경고] 쿠키 추가 실패 ({cookie.get('name', 'unknown')}): {e}")
                        continue

                print(f"[성공] {len(cookies)}개 쿠키 로드 완료")

            except json.JSONDecodeError as e:
                print(f"[오류] COOKIES_JSON 파싱 실패: {e}")
                return False

        # 방법 2: 개별 쿠키 사용
        else:
            print("[정보] 개별 쿠키 로드 중...")

            # 필수 쿠키
            required_cookies = {
                "auth_token": env_vars.get("AUTH_TOKEN"),
                "ct0": env_vars.get("CT0"),
            }

            # 선택 쿠키
            optional_cookies = {
                "twid": env_vars.get("TWID"),
                "guest_id": env_vars.get("GUEST_ID"),
            }

            # 필수 쿠키 확인
            missing = [k for k, v in required_cookies.items() if not v]
            if missing:
                print(f"[오류] 필수 쿠키 누락: {', '.join(missing)}")
                print("[안내] .env 파일에 AUTH_TOKEN과 CT0을 입력하세요")
                return False

            # 쿠키 추가
            cookies_added = 0
            for name, value in {**required_cookies, **optional_cookies}.items():
                if value:
                    try:
                        driver.add_cookie({
                            "name": name,
                            "value": value,
                            "domain": ".x.com",
                            "path": "/",
                        })
                        cookies_added += 1
                    except Exception as e:
                        print(f"[경고] 쿠키 추가 실패 ({name}): {e}")

            print(f"[성공] {cookies_added}개 쿠키 로드 완료")

        # 쿠키 적용 확인
        print("[정보] 세션 검증 중...")
        driver.get("https://x.com/home")
        time.sleep(3)

        # 로그인 상태 확인
        if is_logged_in(driver):
            print("[성공] 쿠키로 로그인 성공!")
            return True
        else:
            print("[오류] 쿠키가 유효하지 않습니다")
            print("[안내] 브라우저에서 다시 로그인하여 새 쿠키를 가져오세요")
            return False

    except Exception as e:
        print(f"[오류] 쿠키 로드 실패: {e}")
        return False

# -----------------------
# 로그인 상태 확인
# -----------------------
def is_logged_in(driver, timeout=5):
    """현재 로그인 상태인지 확인"""
    try:
        if "x.com/home" in driver.current_url or "twitter.com/home" in driver.current_url:
            return True

        home_indicators = [
            (By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]'),
            (By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'),
        ]

        for by, selector in home_indicators:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
                if element.is_displayed():
                    return True
            except:
                continue

        return False
    except:
        return False

# -----------------------
# Selenium 드라이버
# -----------------------
def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"user-agent={USER_AGENT}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1200,2000")

    if AUTO_DRIVER:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        driver = webdriver.Chrome(options=opts)

    driver.set_page_load_timeout(60)
    return driver

# -----------------------
# 파싱 (간략화)
# -----------------------
def parse_quote_tweet(article):
    """트윗 파싱"""
    try:
        data = {
            "status_id": "", "url": "", "author_handle": "", "text": "",
            "hashtags": "", "time_iso_utc": "", "has_media": "",
            "media_urls": "", "is_quote": "FALSE",
            "quote_status_id": "인용X", "quote_time_iso_utc": "인용X",
        }

        # status_id 및 url
        time_link = article.find_element(By.CSS_SELECTOR, "a[href*='/status/']")
        href = time_link.get_attribute("href")
        if href:
            parts = href.split("/status/")
            if len(parts) == 2:
                status_id = parts[1].split("?")[0]
                data["status_id"] = status_id
                data["url"] = f"https://x.com{parts[0].replace('https://x.com', '')}/status/{status_id}"

        # author_handle
        profile_link = article.find_element(By.CSS_SELECTOR, "a[href^='/'][role='link']")
        profile_href = profile_link.get_attribute("href")
        if profile_href:
            username = profile_href.split("?")[0].split("/")[-1]
            if username and not username.startswith("status"):
                data["author_handle"] = f"@{username}"

        # text 및 hashtags
        tweet_text_div = article.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
        data["text"] = tweet_text_div.text.strip()
        hashtag_links = tweet_text_div.find_elements(By.CSS_SELECTOR, "a[href*='/hashtag/']")
        hashtags = [link.text.strip() for link in hashtag_links]
        data["hashtags"] = ", ".join(hashtags)

        # time
        time_element = article.find_element(By.CSS_SELECTOR, "time[datetime]")
        data["time_iso_utc"] = time_element.get_attribute("datetime")

        # media
        images = article.find_elements(By.CSS_SELECTOR, "img[src*='pbs.twimg.com']")
        media_urls = [img.get_attribute("src") for img in images if "profile_images" not in img.get_attribute("src")]
        if media_urls:
            data["has_media"] = "TRUE"
            data["media_urls"] = ", ".join(media_urls)
        else:
            data["has_media"] = "FALSE"
            data["media_urls"] = "인용X"

        return data
    except:
        return None

# -----------------------
# 추출
# -----------------------
def extract_quote_tweets(driver, quotes_url, max_scrolls=None):
    """인용글 추출"""
    print(f"\n[정보] 인용글 페이지 접근...")
    driver.get(quotes_url)
    time.sleep(3)

    all_tweets = []
    seen_ids = set()
    scrolls = 0
    no_new = 0

    print("[정보] 스크롤 및 데이터 수집 시작...")
    print("=" * 60)

    while True:
        try:
            articles = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
        except:
            break

        new = 0
        for article in articles:
            tweet = parse_quote_tweet(article)
            if tweet and tweet["status_id"] and tweet["status_id"] not in seen_ids:
                seen_ids.add(tweet["status_id"])
                all_tweets.append(tweet)
                new += 1

                # 각 트윗 추출 시 즉시 로그 출력
                text_preview = tweet["text"][:50] + "..." if len(tweet["text"]) > 50 else tweet["text"]
                print(f"[수집 #{len(all_tweets):3d}] {tweet['author_handle']:20s} | {text_preview}")

                # 미디어 정보 표시
                if tweet["has_media"] == "TRUE":
                    media_count = len(tweet["media_urls"].split(", "))
                    print(f"              └─ 미디어 {media_count}개 포함")

        # 스크롤 정보 표시
        scrolls += 1
        scroll_info = f"[스크롤 #{scrolls:2d}]"
        if max_scrolls:
            scroll_info += f" ({scrolls}/{max_scrolls})"

        if new > 0:
            print(f"\n{scroll_info} 이번 스크롤에서 {new}개 신규 추출 (총 {len(all_tweets)}개)")
        else:
            print(f"\n{scroll_info} 신규 데이터 없음 (중복 또는 끝)")
            no_new += 1

        if new == 0:
            if no_new >= 3:
                print("[정보] 연속 3회 신규 데이터 없음 - 수집 종료")
                break
        else:
            no_new = 0

        # 스크롤 실행
        last_h = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 스크롤 대기
        if scrolls < 3:
            print(f"[대기] 페이지 로딩 중... ({SCROLL_PAUSE}초)")
        time.sleep(SCROLL_PAUSE)

        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            print("[정보] 페이지 끝 도달 - 수집 종료")
            break

        if max_scrolls and scrolls >= max_scrolls:
            print(f"[정보] 최대 스크롤 횟수 ({max_scrolls}회) 도달 - 수집 종료")
            break

        print("=" * 60)

    print("\n" + "=" * 60)
    print(f"[완료] 총 {len(all_tweets)}개 인용글 수집 완료")
    print("=" * 60)
    return all_tweets

# -----------------------
# CSV 저장
# -----------------------
def save_to_csv(tweets, output_path):
    """CSV 저장"""
    if not tweets:
        print("[경고] 저장할 데이터 없음")
        return

    fieldnames = ["status_id", "url", "author_handle", "text", "hashtags",
                  "time_iso_utc", "has_media", "media_urls", "is_quote",
                  "quote_status_id", "quote_time_iso_utc"]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tweet in tweets:
            writer.writerow(tweet)

    print(f"\n[완료] CSV 저장: {output_path}")
    print(f"  - 총 {len(tweets)}개 레코드")

# -----------------------
# 메인
# -----------------------
def main():
    print("=" * 60)
    print("   트위터 인용글 추출 - .env 쿠키 버전")
    print("=" * 60)
    print()

    # .env 로드
    env_vars = load_env()
    if not env_vars:
        print("\n[오류] .env 파일을 설정하세요")
        print("\n설정 방법:")
        print("1. .env.example을 .env로 복사")
        print("2. 브라우저에서 Twitter 로그인")
        print("3. F12 → Application → Cookies → https://x.com")
        print("4. auth_token과 ct0 값을 .env에 붙여넣기")
        return

    # 입력
    url = input("인용글 URL: ").strip()
    if "/quotes" not in url:
        url = url.rstrip("/") + "/quotes"

    output = input(f"저장 파일명 (엔터 = quotes.csv): ").strip() or "quotes.csv"
    if not output.endswith(".csv"):
        output += ".csv"

    max_scrolls_input = input("최대 스크롤 (엔터 = 무제한): ").strip()
    max_scrolls = int(max_scrolls_input) if max_scrolls_input else None

    headless_input = input("브라우저 숨김? (y/n, 엔터 = n): ").strip().lower()
    headless = headless_input in ['y', 'yes']

    # 실행
    print("\n" + "=" * 60)
    driver = None
    try:
        print("[정보] Chrome 드라이버 시작...")
        driver = make_driver(headless=headless)

        # 쿠키 로드
        if not load_cookies_from_env(driver, env_vars):
            print("\n[오류] 쿠키 로드 실패")
            return

        # 추출
        tweets = extract_quote_tweets(driver, url, max_scrolls=max_scrolls)

        # 저장
        if tweets:
            save_to_csv(tweets, output)
            print("\n✅ 성공!")
        else:
            print("[경고] 추출된 데이터 없음")

    except KeyboardInterrupt:
        print("\n[정보] 중단됨")
    except Exception as e:
        print(f"\n[오류] {e}")
    finally:
        if driver:
            driver.quit()
            print("[정보] 브라우저 종료")

if __name__ == "__main__":
    main()
