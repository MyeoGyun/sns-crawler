#!/usr/bin/env python3
# quote_extractor_gsheet.py
# 트위터 인용글 추출 → Google Sheets 자동 업로드
#
# 설치:
#   pip install selenium webdriver-manager gspread oauth2client
#
# Google Cloud 설정 필요:
#   1. https://console.cloud.google.com/ 접속
#   2. 프로젝트 생성
#   3. Google Sheets API 활성화
#   4. 서비스 계정 생성 → credentials.json 다운로드
#   5. credentials.json을 이 스크립트와 같은 폴더에 저장

import os
import time
import random
import json
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    print("[오류] gspread 또는 oauth2client가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요:")
    print("  pip install gspread oauth2client")
    exit(1)

# -----------------------
# 설정값
# -----------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SCROLL_PAUSE = 2.0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config_defaults.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# -----------------------
# 설정 로드
# -----------------------
def load_selector_config():
    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "next_button_xpaths": [
                "//div[@role='button' and .//span[normalize-space(text())='Next' or normalize-space(text())='다음']]",
            ],
            "login_button_xpaths": [
                "//div[@role='button' and .//span[normalize-space(text())='Log in' or normalize-space(text())='로그인']]",
            ],
        }

SELECTOR_CONFIG = load_selector_config()

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

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    return driver

# -----------------------
# 로그인
# -----------------------
def login_twitter(driver, login_id, login_pw, wait_sec=10):
    driver.get("https://twitter.com/i/flow/login")

    try:
        el_id = WebDriverWait(driver, wait_sec).until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        el_id.clear()
        el_id.send_keys(login_id)

        next_button_xpaths = SELECTOR_CONFIG.get("next_button_xpaths", [
            "//div[@role='button' and .//span[normalize-space(text())='Next' or normalize-space(text())='다음']]",
        ])

        def click_next_button():
            for xpath in next_button_xpaths:
                try:
                    next_btn = WebDriverWait(driver, wait_sec).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    next_btn.click()
                    time.sleep(0.2)
                    return
                except TimeoutException:
                    continue
            raise TimeoutException("Next button not found")

        try:
            click_next_button()
        except TimeoutException:
            pass

        pw_input = None
        for _ in range(3):
            try:
                pw_input = WebDriverWait(driver, wait_sec).until(
                    EC.presence_of_element_located((By.NAME, "password"))
                )
                break
            except TimeoutException:
                try:
                    alt_input = WebDriverWait(driver, wait_sec).until(
                        EC.presence_of_element_located((By.NAME, "text"))
                    )
                    alt_input.clear()
                    alt_input.send_keys(login_id)
                    try:
                        click_next_button()
                    except TimeoutException:
                        alt_input.send_keys(Keys.RETURN)
                except TimeoutException:
                    raise

        if pw_input is None:
            raise TimeoutException("Password input not found")

        pw_input.clear()
        pw_input.send_keys(login_pw)

        login_button_xpaths = SELECTOR_CONFIG.get("login_button_xpaths", [
            "//div[@role='button' and .//span[normalize-space(text())='Log in' or normalize-space(text())='로그인']]",
        ])

        try:
            for xpath in login_button_xpaths:
                try:
                    login_btn = WebDriverWait(driver, wait_sec).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    login_btn.click()
                    break
                except TimeoutException:
                    continue
        except TimeoutException:
            pw_input.submit()

        home_fragments = ("twitter.com/home", "x.com/home", "twitter.com/?", "x.com/?")

        def has_home_signal(drv):
            return any(fragment in drv.current_url for fragment in home_fragments)

        WebDriverWait(driver, wait_sec * 2).until(has_home_signal)
        return True

    except Exception as e:
        print(f"[오류] 로그인 실패: {e}")
        return False

# -----------------------
# 파싱 (기존과 동일)
# -----------------------
def parse_quote_tweet(article):
    try:
        data = {
            "status_id": "",
            "url": "",
            "author_handle": "",
            "text": "",
            "hashtags": "",
            "time_iso_utc": "",
            "has_media": "",
            "media_urls": "",
            "is_quote": "",
            "quote_status_id": "인용X",
            "quote_time_iso_utc": "인용X",
        }

        try:
            time_link = article.find_element(By.CSS_SELECTOR, "a[href*='/status/']")
            href = time_link.get_attribute("href")
            if href:
                parts = href.split("/status/")
                if len(parts) == 2:
                    status_id = parts[1].split("?")[0]
                    data["status_id"] = status_id
                    data["url"] = f"https://x.com{parts[0].replace('https://x.com', '')}/status/{status_id}"
        except NoSuchElementException:
            return None

        try:
            profile_link = article.find_element(By.CSS_SELECTOR, "a[href^='/'][role='link']")
            profile_href = profile_link.get_attribute("href")
            if profile_href:
                username = profile_href.split("?")[0].split("/")[-1]
                if username and not username.startswith("status"):
                    data["author_handle"] = f"@{username}" if not username.startswith("@") else username
        except NoSuchElementException:
            try:
                spans = article.find_elements(By.CSS_SELECTOR, "span")
                for span in spans:
                    text = span.text.strip()
                    if text.startswith("@"):
                        data["author_handle"] = text
                        break
            except:
                pass

        try:
            tweet_text_div = article.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
            data["text"] = tweet_text_div.text.strip()

            hashtag_links = tweet_text_div.find_elements(By.CSS_SELECTOR, "a[href*='/hashtag/']")
            hashtags = []
            for link in hashtag_links:
                hashtag_text = link.text.strip()
                if hashtag_text and hashtag_text not in hashtags:
                    hashtags.append(hashtag_text)
            data["hashtags"] = ", ".join(hashtags) if hashtags else ""
        except NoSuchElementException:
            data["text"] = ""

        try:
            time_element = article.find_element(By.CSS_SELECTOR, "time[datetime]")
            datetime_attr = time_element.get_attribute("datetime")
            if datetime_attr:
                data["time_iso_utc"] = datetime_attr
        except NoSuchElementException:
            pass

        media_urls = []
        try:
            images = article.find_elements(By.CSS_SELECTOR, "img[src*='pbs.twimg.com']")
            for img in images:
                src = img.get_attribute("src")
                if src and "profile_images" not in src:
                    if "name=" in src:
                        src = src.split("&name=")[0] + "&name=large"
                    media_urls.append(src)
        except:
            pass

        try:
            videos = article.find_elements(By.CSS_SELECTOR, "video source")
            for video in videos:
                src = video.get_attribute("src")
                if src:
                    media_urls.append(src)
        except:
            pass

        if media_urls:
            data["has_media"] = "TRUE"
            data["media_urls"] = ", ".join(media_urls)
        else:
            data["has_media"] = "FALSE"
            data["media_urls"] = "인용X"

        try:
            quote_links = article.find_elements(By.CSS_SELECTOR, "div[role='link'] a[href*='/status/']")
            if quote_links:
                for link in quote_links:
                    href = link.get_attribute("href")
                    if href and "/status/" in href:
                        quote_parts = href.split("/status/")
                        if len(quote_parts) == 2:
                            quote_id = quote_parts[1].split("?")[0]
                            if quote_id != data["status_id"]:
                                data["is_quote"] = "TRUE"
                                data["quote_status_id"] = quote_id

                                try:
                                    quote_time = link.find_element(By.CSS_SELECTOR, "time[datetime]")
                                    quote_datetime = quote_time.get_attribute("datetime")
                                    if quote_datetime:
                                        data["quote_time_iso_utc"] = quote_datetime
                                except:
                                    pass
                                break
        except:
            pass

        if not data["is_quote"]:
            data["is_quote"] = "FALSE"

        return data

    except Exception as e:
        print(f"[경고] 트윗 파싱 오류: {e}")
        return None

# -----------------------
# 추출
# -----------------------
def extract_quote_tweets(driver, quotes_url, max_scrolls=None, scroll_delay=2.0):
    print(f"[정보] 인용글 페이지 접근 중: {quotes_url}")
    driver.get(quotes_url)
    time.sleep(3)

    all_tweets = []
    seen_ids = set()
    scrolls = 0
    no_new_content_count = 0

    print(f"[정보] 스크롤 시작 (최대: {max_scrolls if max_scrolls else '무제한'})")

    while True:
        try:
            articles = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
            print(f"[정보] 현재 페이지에서 {len(articles)}개 트윗 발견")
        except NoSuchElementException:
            print("[경고] 트윗을 찾을 수 없습니다.")
            break

        new_tweets_in_scroll = 0
        for article in articles:
            try:
                tweet_data = parse_quote_tweet(article)
                if tweet_data and tweet_data["status_id"]:
                    if tweet_data["status_id"] not in seen_ids:
                        seen_ids.add(tweet_data["status_id"])
                        all_tweets.append(tweet_data)
                        new_tweets_in_scroll += 1
                        print(f"  → 추출: {tweet_data['author_handle']} - {tweet_data['status_id']}")
            except Exception as e:
                print(f"[경고] 트윗 처리 오류: {e}")
                continue

        if new_tweets_in_scroll == 0:
            no_new_content_count += 1
            print(f"[정보] 새 트윗 없음 ({no_new_content_count}/3)")
            if no_new_content_count >= 3:
                print("[정보] 더 이상 새 콘텐츠가 없습니다. 종료합니다.")
                break
        else:
            no_new_content_count = 0

        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_delay)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("[정보] 페이지 끝에 도달했습니다.")
            break

        scrolls += 1
        if max_scrolls is not None and scrolls >= max_scrolls:
            print(f"[정보] 최대 스크롤 횟수({max_scrolls})에 도달했습니다.")
            break

    print(f"\n[완료] 총 {len(all_tweets)}개의 인용글 추출 완료")
    return all_tweets

# -----------------------
# Google Sheets 업로드
# -----------------------
def upload_to_google_sheets(tweets, sheet_name, credentials_path=CREDENTIALS_PATH):
    """
    Google Sheets에 데이터 업로드

    Args:
        tweets: 트윗 데이터 리스트
        sheet_name: 구글 시트 이름
        credentials_path: credentials.json 경로
    """
    if not tweets:
        print("[경고] 업로드할 데이터가 없습니다.")
        return False

    if not os.path.exists(credentials_path):
        print(f"[오류] credentials.json 파일을 찾을 수 없습니다: {credentials_path}")
        print("\n설정 방법:")
        print("1. https://console.cloud.google.com/ 접속")
        print("2. 프로젝트 생성")
        print("3. Google Sheets API 활성화")
        print("4. 서비스 계정 생성 → JSON 키 다운로드")
        print("5. credentials.json으로 이름 변경 후 스크립트 폴더에 저장")
        return False

    try:
        # Google Sheets 인증
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(creds)

        print(f"[정보] Google Sheets 연결 중: {sheet_name}")

        # 스프레드시트 열기 또는 생성
        try:
            sheet = client.open(sheet_name).sheet1
            print(f"[정보] 기존 시트 '{sheet_name}' 열기 성공")
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(sheet_name)
            sheet = spreadsheet.sheet1
            print(f"[정보] 새 시트 '{sheet_name}' 생성 완료")

            # 공유 가능하도록 설정 (선택사항)
            # spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')

        # 헤더 작성
        headers = [
            "status_id",
            "url",
            "author_handle",
            "text",
            "hashtags",
            "time_iso_utc",
            "has_media",
            "media_urls",
            "is_quote",
            "quote_status_id",
            "quote_time_iso_utc",
        ]

        # 기존 데이터 삭제 (선택사항)
        sheet.clear()

        # 헤더 추가
        sheet.append_row(headers)

        # 데이터 추가
        for tweet in tweets:
            row = [
                tweet.get("status_id", ""),
                tweet.get("url", ""),
                tweet.get("author_handle", ""),
                tweet.get("text", ""),
                tweet.get("hashtags", ""),
                tweet.get("time_iso_utc", ""),
                tweet.get("has_media", ""),
                tweet.get("media_urls", ""),
                tweet.get("is_quote", ""),
                tweet.get("quote_status_id", "인용X"),
                tweet.get("quote_time_iso_utc", "인용X"),
            ]
            sheet.append_row(row)

        # 시트 URL 가져오기
        spreadsheet_url = client.open(sheet_name).url

        print(f"\n[완료] Google Sheets 업로드 성공!")
        print(f"  - 시트 이름: {sheet_name}")
        print(f"  - 총 레코드: {len(tweets)}개")
        print(f"  - URL: {spreadsheet_url}")
        print(f"\n브라우저에서 확인: {spreadsheet_url}")

        return True

    except Exception as e:
        print(f"[오류] Google Sheets 업로드 실패: {e}")
        return False

# -----------------------
# 메인
# -----------------------
def main():
    parser = argparse.ArgumentParser(
        description="트위터/X 인용글 추출 → Google Sheets 자동 업로드",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--url", required=True, help="인용글 페이지 URL")
    parser.add_argument("--username", required=True, help="트위터 로그인 ID")
    parser.add_argument("--password", required=True, help="트위터 비밀번호")
    parser.add_argument("--sheet-name", default="Twitter Quotes", help="구글 시트 이름 (기본: Twitter Quotes)")
    parser.add_argument("--max-scrolls", type=int, default=None, help="최대 스크롤 횟수")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    parser.add_argument("--scroll-delay", type=float, default=2.0, help="스크롤 간 대기시간(초)")

    args = parser.parse_args()

    print("[정보] Chrome 드라이버 시작 중...")
    driver = None
    try:
        driver = make_driver(headless=args.headless)
    except Exception as e:
        print(f"[오류] 드라이버 생성 실패: {e}")
        return

    try:
        print("[정보] 트위터 로그인 중...")
        if not login_twitter(driver, args.username, args.password):
            print("[오류] 로그인 실패")
            return

        print("[성공] 로그인 완료\n")

        tweets = extract_quote_tweets(
            driver,
            args.url,
            max_scrolls=args.max_scrolls,
            scroll_delay=args.scroll_delay
        )

        if tweets:
            upload_to_google_sheets(tweets, args.sheet_name)
        else:
            print("[경고] 추출된 인용글이 없습니다.")

    except KeyboardInterrupt:
        print("\n[정보] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"[오류] 실행 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print("[정보] 드라이버 종료")

if __name__ == "__main__":
    main()
