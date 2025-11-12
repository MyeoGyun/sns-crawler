#!/usr/bin/env python3
# quote_extractor_multi.py
# 여러 인용글 URL을 하나의 브라우저 세션에서 순차 처리
#
# 특징:
# - 로그인 한 번만 수행
# - 여러 URL을 순차적으로 처리 (새 창 열지 않음)
# - 모든 결과를 하나의 CSV에 통합 저장
#
# 설치: pip install selenium webdriver-manager

import os
import time
import random
import csv
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

# -----------------------
# 설정값
# -----------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SCROLL_PAUSE = 2.0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config_defaults.json")

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
# 파싱
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
            "source_url": "",  # 어느 인용글 페이지에서 추출되었는지
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
    print(f"[정보] 인용글 페이지 접근: {quotes_url}")
    driver.get(quotes_url)
    time.sleep(3)

    all_tweets = []
    seen_ids = set()
    scrolls = 0
    no_new_content_count = 0

    print("[정보] 스크롤 및 데이터 수집 시작...")
    print("=" * 60)

    while True:
        try:
            articles = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
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
                        tweet_data["source_url"] = quotes_url  # 출처 URL 기록
                        all_tweets.append(tweet_data)
                        new_tweets_in_scroll += 1

                        # 각 트윗 추출 시 즉시 로그 출력
                        text_preview = tweet_data["text"][:50] + "..." if len(tweet_data["text"]) > 50 else tweet_data["text"]
                        print(f"[수집 #{len(all_tweets):3d}] {tweet_data['author_handle']:20s} | {text_preview}")

                        # 미디어 정보 표시
                        if tweet_data["has_media"] == "TRUE":
                            media_count = len(tweet_data["media_urls"].split(", "))
                            print(f"              └─ 미디어 {media_count}개 포함")

            except Exception as e:
                continue

        # 스크롤 정보 표시
        scrolls += 1
        scroll_info = f"[스크롤 #{scrolls:2d}]"
        if max_scrolls:
            scroll_info += f" ({scrolls}/{max_scrolls})"

        if new_tweets_in_scroll > 0:
            print(f"\n{scroll_info} 이번 스크롤에서 {new_tweets_in_scroll}개 신규 추출 (총 {len(all_tweets)}개)")
        else:
            print(f"\n{scroll_info} 신규 데이터 없음 (중복 또는 끝)")
            no_new_content_count += 1

        if new_tweets_in_scroll == 0:
            if no_new_content_count >= 3:
                print("[정보] 연속 3회 신규 데이터 없음 - 수집 종료")
                break
        else:
            no_new_content_count = 0

        # 스크롤 실행
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 스크롤 대기
        if scrolls < 3:
            print(f"[대기] 페이지 로딩 중... ({scroll_delay}초)")
        time.sleep(scroll_delay)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("[정보] 페이지 끝 도달 - 수집 종료")
            break

        if max_scrolls is not None and scrolls >= max_scrolls:
            print(f"[정보] 최대 스크롤 횟수 ({max_scrolls}회) 도달 - 수집 종료")
            break

        print("=" * 60)

    print(f"\n[완료] 이 URL에서 총 {len(all_tweets)}개 추출")
    return all_tweets

# -----------------------
# CSV 저장
# -----------------------
def save_to_csv(tweets, output_path):
    if not tweets:
        print("[경고] 저장할 데이터가 없습니다.")
        return

    fieldnames = [
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
        "source_url",  # 추가: 어느 페이지에서 추출되었는지
    ]

    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for tweet in tweets:
                writer.writerow(tweet)

        print(f"\n[완료] CSV 저장: {output_path}")
        print(f"  - 총 {len(tweets)}개 레코드")

    except Exception as e:
        print(f"[오류] CSV 저장 실패: {e}")

# -----------------------
# 메인
# -----------------------
def main():
    parser = argparse.ArgumentParser(
        description="여러 트위터 인용글 URL을 하나의 브라우저에서 순차 처리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:

1. 여러 URL을 직접 입력 (쉼표로 구분):
  python quote_extractor_multi.py ^
    --urls "https://x.com/.../status/.../quotes,https://x.com/.../status/.../quotes" ^
    --username "your_id" ^
    --password "your_password"

2. 파일에서 URL 목록 읽기:
  python quote_extractor_multi.py ^
    --url-file urls.txt ^
    --username "your_id" ^
    --password "your_password"

3. 단일 URL 처리 (기존 방식):
  python quote_extractor_multi.py ^
    --url "https://x.com/.../status/.../quotes" ^
    --username "your_id" ^
    --password "your_password"

urls.txt 파일 형식:
  https://x.com/user1/status/123/quotes
  https://x.com/user2/status/456/quotes
  https://x.com/user3/status/789/quotes
        """
    )

    # URL 입력 방식 (3가지 중 하나 선택)
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument("--url", help="단일 인용글 페이지 URL")
    url_group.add_argument("--urls", help="여러 URL (쉼표로 구분)")
    url_group.add_argument("--url-file", help="URL 목록 파일 (한 줄에 하나씩)")

    parser.add_argument("--username", required=True, help="트위터 로그인 ID")
    parser.add_argument("--password", required=True, help="트위터 비밀번호")
    parser.add_argument("--output", default="quotes_multi.csv", help="출력 CSV 파일 (기본: quotes_multi.csv)")
    parser.add_argument("--max-scrolls", type=int, default=None, help="각 URL당 최대 스크롤 횟수")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    parser.add_argument("--scroll-delay", type=float, default=2.0, help="스크롤 간 대기시간(초)")
    parser.add_argument("--url-delay", type=float, default=3.0, help="URL 전환 간 대기시간(초)")

    args = parser.parse_args()

    # URL 목록 생성
    urls = []
    if args.url:
        urls = [args.url]
    elif args.urls:
        urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    elif args.url_file:
        try:
            with open(args.url_file, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except FileNotFoundError:
            print(f"[오류] 파일을 찾을 수 없습니다: {args.url_file}")
            return
        except Exception as e:
            print(f"[오류] 파일 읽기 실패: {e}")
            return

    if not urls:
        print("[오류] 처리할 URL이 없습니다.")
        return

    print(f"[정보] 총 {len(urls)}개 URL 처리 예정")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    print()

    # 드라이버 생성
    print("[정보] Chrome 드라이버 시작...")
    driver = None
    try:
        driver = make_driver(headless=args.headless)
    except Exception as e:
        print(f"[오류] 드라이버 생성 실패: {e}")
        return

    try:
        # 로그인 (한 번만)
        print("[정보] 트위터 로그인...")
        if not login_twitter(driver, args.username, args.password):
            print("[오류] 로그인 실패")
            return

        print("[성공] 로그인 완료\n")
        print("=" * 60)

        # 여러 URL 순차 처리
        all_tweets = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 처리 중...")

            try:
                tweets = extract_quote_tweets(
                    driver,
                    url,
                    max_scrolls=args.max_scrolls,
                    scroll_delay=args.scroll_delay
                )
                all_tweets.extend(tweets)

                # 다음 URL로 이동 전 대기
                if i < len(urls):
                    print(f"  → 다음 URL 이동까지 {args.url_delay}초 대기...")
                    time.sleep(args.url_delay)

            except Exception as e:
                print(f"  [오류] URL 처리 실패: {e}")
                continue

        print("\n" + "=" * 60)
        print(f"[완료] 전체 처리 완료: 총 {len(all_tweets)}개 인용글 추출")

        # CSV 저장
        if all_tweets:
            save_to_csv(all_tweets, args.output)
        else:
            print("[경고] 추출된 인용글이 없습니다.")

    except KeyboardInterrupt:
        print("\n[정보] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"[오류] 실행 중 오류: {e}")
    finally:
        if driver:
            driver.quit()
            print("[정보] 브라우저 종료")

if __name__ == "__main__":
    main()
