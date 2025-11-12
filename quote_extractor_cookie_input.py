#!/usr/bin/env python3
# quote_extractor_cookie_input.py
# CLI에서 직접 쿠키를 입력받아 자동 로그인
#
# 사용법:
# python quote_extractor_cookie_input.py

import os
import time
import csv
import getpass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
# 쿠키 입력받기
# -----------------------
def get_cookies_from_user():
    """
    사용자로부터 쿠키 값을 직접 입력받기

    Returns:
        dict: 쿠키 딕셔너리 또는 None
    """
    print("\n" + "=" * 60)
    print("   쿠키 입력")
    print("=" * 60)
    print()
    print("Chrome에서 쿠키를 추출하는 방법:")
    print("1. Chrome 브라우저에서 https://x.com 로그인")
    print("2. F12 (개발자 도구) 열기")
    print("3. Application 탭 → Cookies → https://x.com")
    print("4. 아래 쿠키 값들을 복사하여 붙여넣기")
    print()
    print("자세한 가이드: README_COOKIES.md 참고")
    print("=" * 60)
    print()

    cookies = {}

    # 필수 쿠키 입력
    print("📌 필수 쿠키 (반드시 필요):")
    print()

    # AUTH_TOKEN
    print("1. auth_token 쿠키 값을 입력하세요:")
    print("   (Chrome에서 auth_token 값을 복사하여 붙여넣기)")
    auth_token = input("AUTH_TOKEN: ").strip()

    if not auth_token:
        print("\n[오류] AUTH_TOKEN은 필수입니다!")
        return None

    cookies["AUTH_TOKEN"] = auth_token
    print("✅ AUTH_TOKEN 입력 완료")
    print()

    # CT0
    print("2. ct0 쿠키 값을 입력하세요:")
    print("   (Chrome에서 ct0 값을 복사하여 붙여넣기)")
    ct0 = input("CT0: ").strip()

    if not ct0:
        print("\n[오류] CT0은 필수입니다!")
        return None

    cookies["CT0"] = ct0
    print("✅ CT0 입력 완료")
    print()

    # 선택 쿠키
    print("📝 선택 쿠키 (없으면 엔터):")
    print()

    print("3. twid 쿠키 값 (선택, 엔터로 건너뛰기):")
    twid = input("TWID: ").strip()
    if twid:
        cookies["TWID"] = twid
        print("✅ TWID 입력 완료")
    else:
        print("⏭️  TWID 건너뜀")
    print()

    print("4. guest_id 쿠키 값 (선택, 엔터로 건너뛰기):")
    guest_id = input("GUEST_ID: ").strip()
    if guest_id:
        cookies["GUEST_ID"] = guest_id
        print("✅ GUEST_ID 입력 완료")
    else:
        print("⏭️  GUEST_ID 건너뜀")
    print()

    return cookies

# -----------------------
# .env 파일로 저장
# -----------------------
def save_to_env_file(cookies):
    """
    입력받은 쿠키를 .env 파일로 저장

    Args:
        cookies: 쿠키 딕셔너리

    Returns:
        bool: 저장 성공 여부
    """
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("# Twitter/X 쿠키 설정\n")
            f.write("# 이 파일을 다른 사람과 공유하지 마세요!\n")
            f.write("\n")
            f.write("# 필수 쿠키\n")
            f.write(f"AUTH_TOKEN={cookies.get('AUTH_TOKEN', '')}\n")
            f.write(f"CT0={cookies.get('CT0', '')}\n")
            f.write("\n")
            f.write("# 선택 쿠키\n")
            f.write(f"TWID={cookies.get('TWID', '')}\n")
            f.write(f"GUEST_ID={cookies.get('GUEST_ID', '')}\n")
            f.write("\n")
            f.write("# 전체 쿠키 JSON (사용 안 함)\n")
            f.write("COOKIES_JSON=\n")

        print(f"\n[성공] 쿠키를 .env 파일로 저장했습니다: {ENV_FILE}")
        print("[안내] 다음 실행 시 quote_extractor_env.py로 자동 로그인 가능")
        return True

    except Exception as e:
        print(f"\n[경고] .env 저장 실패: {e}")
        return False

# -----------------------
# 쿠키 로드 및 적용
# -----------------------
def load_cookies_to_driver(driver, cookies):
    """
    입력받은 쿠키를 Selenium에 적용

    Args:
        driver: Selenium WebDriver
        cookies: 쿠키 딕셔너리

    Returns:
        bool: 성공 여부
    """
    try:
        # Twitter 홈페이지로 먼저 이동 (쿠키 도메인 일치 필요)
        print("[정보] Twitter 접속 중...")
        driver.get("https://x.com")
        time.sleep(2)

        print("[정보] 쿠키 로드 중...")

        # 필수 쿠키
        required_cookies = {
            "auth_token": cookies.get("AUTH_TOKEN"),
            "ct0": cookies.get("CT0"),
        }

        # 선택 쿠키
        optional_cookies = {
            "twid": cookies.get("TWID"),
            "guest_id": cookies.get("GUEST_ID"),
        }

        # 필수 쿠키 확인
        missing = [k for k, v in required_cookies.items() if not v]
        if missing:
            print(f"[오류] 필수 쿠키 누락: {', '.join(missing)}")
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
            print("[안내] Chrome에서 다시 로그인하여 새 쿠키를 가져오세요")
            print("       쿠키 만료 또는 값이 잘못되었을 수 있습니다")
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
# 파싱
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

    print("[정보] 스크롤 시작...")

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

        if new > 0:
            print(f"  → {len(all_tweets)}개 추출")

        if new == 0:
            no_new += 1
            if no_new >= 3:
                break
        else:
            no_new = 0

        last_h = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)

        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break

        scrolls += 1
        if max_scrolls and scrolls >= max_scrolls:
            break

    print(f"\n[완료] 총 {len(all_tweets)}개 추출")
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
    print("   트위터 인용글 추출 - 쿠키 직접 입력 버전")
    print("=" * 60)

    # 쿠키 입력받기
    cookies = get_cookies_from_user()
    if not cookies:
        print("\n[오류] 쿠키 입력이 취소되었습니다")
        return

    # .env 파일로 저장할지 물어보기
    print("\n" + "=" * 60)
    save_choice = input("입력한 쿠키를 .env 파일로 저장하시겠습니까? (y/n, 엔터 = n): ").strip().lower()
    if save_choice in ['y', 'yes']:
        save_to_env_file(cookies)

    # 인용글 URL 입력
    print("\n" + "=" * 60)
    url = input("인용글 URL: ").strip()
    if not url:
        print("[오류] URL을 입력하세요")
        return

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
        if not load_cookies_to_driver(driver, cookies):
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
