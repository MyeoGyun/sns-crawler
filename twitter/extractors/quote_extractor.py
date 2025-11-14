#!/usr/bin/env python3
# quote_extractor.py
# 트위터/X 인용글(Quotes) 추출 도구
# 실행 전: pip install selenium
# Chrome & chromedriver 버전 일치 필요

import os
import time
import random
import csv
import json
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException
)
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
    """로그인 관련 설정 로드 (기존 코드 재사용)"""
    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config
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
# Selenium 드라이버 생성
# -----------------------
def make_driver(headless=True):
    """Chrome WebDriver 생성"""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"user-agent={USER_AGENT}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1200,2000")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    return driver

# -----------------------
# 로그인 처리 (기존 코드 재사용)
# -----------------------
def login_twitter(driver, login_id, login_pw, wait_sec=10):
    """
    트위터 로그인
    반환: True/False
    """
    driver.get("https://twitter.com/i/flow/login")

    try:
        # 1) 아이디 입력
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

        # 2) Next 버튼 클릭
        try:
            click_next_button()
        except TimeoutException:
            pass

        # 3) 비밀번호 입력
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

        # 4) 로그인 버튼 클릭
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

        # 5) 로그인 성공 확인
        home_fragments = ("twitter.com/home", "x.com/home", "twitter.com/?", "x.com/?")

        def has_home_signal(drv):
            if any(fragment in drv.current_url for fragment in home_fragments):
                return True
            return False

        WebDriverWait(driver, wait_sec * 2).until(has_home_signal)
        return True

    except Exception as e:
        print(f"[오류] 로그인 실패: {e}")
        return False

# -----------------------
# 인용글 데이터 파싱
# -----------------------
def parse_quote_tweet(article):
    """
    단일 article 요소에서 인용글 데이터 추출
    반환: dict 또는 None
    """
    try:
        data = {
            "status_id": "",
            "url": "",
            "author_handle": "",
            "text": "",
            "hashtags": [],
            "time_iso_utc": "",
            "has_media": False,
            "media_urls": [],
            "is_quote": False,
            "quote_status_id": "인용X",
            "quote_time_iso_utc": "인용X",
        }

        # 1) status_id 및 url 추출
        try:
            # 시간 링크에서 URL 추출
            time_link = article.find_element(By.CSS_SELECTOR, "a[href*='/status/']")
            href = time_link.get_attribute("href")
            if href:
                # URL 파싱: https://x.com/username/status/1234567890
                parts = href.split("/status/")
                if len(parts) == 2:
                    status_id = parts[1].split("?")[0]  # 쿼리 제거
                    data["status_id"] = status_id
                    data["url"] = f"https://x.com{parts[0].replace('https://x.com', '')}/status/{status_id}"
        except NoSuchElementException:
            return None

        # 2) author_handle 추출
        try:
            # 프로필 링크에서 사용자명 추출
            profile_link = article.find_element(By.CSS_SELECTOR, "a[href^='/'][role='link']")
            profile_href = profile_link.get_attribute("href")
            if profile_href:
                username = profile_href.split("?")[0].split("/")[-1]
                if username and not username.startswith("status"):
                    data["author_handle"] = f"@{username}" if not username.startswith("@") else username
        except NoSuchElementException:
            # 대안: span 텍스트에서 @로 시작하는 텍스트 찾기
            try:
                spans = article.find_elements(By.CSS_SELECTOR, "span")
                for span in spans:
                    text = span.text.strip()
                    if text.startswith("@"):
                        data["author_handle"] = text
                        break
            except:
                pass

        # 3) text 및 hashtags 추출
        try:
            tweet_text_div = article.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
            data["text"] = tweet_text_div.text.strip()

            # 해시태그 추출
            hashtag_links = tweet_text_div.find_elements(By.CSS_SELECTOR, "a[href*='/hashtag/']")
            hashtags = []
            for link in hashtag_links:
                hashtag_text = link.text.strip()
                if hashtag_text and hashtag_text not in hashtags:
                    hashtags.append(hashtag_text)
            data["hashtags"] = hashtags
        except NoSuchElementException:
            data["text"] = ""

        # 4) time_iso_utc 추출
        try:
            time_element = article.find_element(By.CSS_SELECTOR, "time[datetime]")
            datetime_attr = time_element.get_attribute("datetime")
            if datetime_attr:
                data["time_iso_utc"] = datetime_attr
        except NoSuchElementException:
            pass

        # 5) has_media 및 media_urls 추출
        media_urls = []
        try:
            # 이미지
            images = article.find_elements(By.CSS_SELECTOR, "img[src*='pbs.twimg.com']")
            for img in images:
                src = img.get_attribute("src")
                if src and "profile_images" not in src:  # 프로필 이미지 제외
                    # 고화질 이미지 URL로 변경
                    if "name=" in src:
                        src = src.split("&name=")[0] + "&name=large"
                    media_urls.append(src)
        except:
            pass

        try:
            # 비디오
            videos = article.find_elements(By.CSS_SELECTOR, "video source")
            for video in videos:
                src = video.get_attribute("src")
                if src:
                    media_urls.append(src)
        except:
            pass

        if media_urls:
            data["has_media"] = True
            data["media_urls"] = media_urls
        else:
            data["media_urls"] = "인용X"

        # 6) is_quote 및 quote.* 추출 (인용 트윗 내에 다른 트윗이 포함된 경우)
        try:
            # 인용 트윗이 다른 트윗을 포함하는 경우
            quote_links = article.find_elements(By.CSS_SELECTOR, "div[role='link'] a[href*='/status/']")
            if quote_links:
                for link in quote_links:
                    href = link.get_attribute("href")
                    if href and "/status/" in href:
                        # 자신의 status_id와 다른 경우만 인용으로 간주
                        quote_parts = href.split("/status/")
                        if len(quote_parts) == 2:
                            quote_id = quote_parts[1].split("?")[0]
                            if quote_id != data["status_id"]:
                                data["is_quote"] = True
                                data["quote_status_id"] = quote_id

                                # 인용글의 타임스탬프 추출 시도
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

        return data

    except Exception as e:
        print(f"[경고] 트윗 파싱 오류: {e}")
        return None

# -----------------------
# 인용글 페이지 스크롤 및 추출
# -----------------------
def extract_quote_tweets(driver, quotes_url, max_scrolls=None, scroll_delay=2.0):
    """
    인용글 페이지에서 모든 인용글 추출

    Args:
        driver: Selenium WebDriver
        quotes_url: 인용글 페이지 URL (예: https://x.com/.../status/.../quotes)
        max_scrolls: 최대 스크롤 횟수 (None = 무제한)
        scroll_delay: 스크롤 간 대기 시간(초)

    Returns:
        list: 추출된 인용글 데이터 리스트
    """
    print(f"[정보] 인용글 페이지 접근 중: {quotes_url}")
    driver.get(quotes_url)
    time.sleep(3)  # 초기 로딩 대기

    all_tweets = []
    seen_ids = set()
    scrolls = 0
    no_new_content_count = 0

    print(f"[정보] 스크롤 시작 (최대: {max_scrolls if max_scrolls else '무제한'})")

    while True:
        # 현재 페이지의 모든 article 요소 찾기
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

        # 스크롤 다운
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_delay)

        # 새 콘텐츠 로딩 확인
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
# CSV 저장
# -----------------------
def save_to_csv(tweets, output_path):
    """
    추출된 트윗 데이터를 CSV로 저장

    Args:
        tweets: 트윗 데이터 리스트
        output_path: 저장할 CSV 파일 경로
    """
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
    ]

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for tweet in tweets:
                # JSON array로 변환
                row = tweet.copy()
                row["hashtags"] = json.dumps(row["hashtags"], ensure_ascii=False)
                if isinstance(row["media_urls"], list):
                    row["media_urls"] = json.dumps(row["media_urls"], ensure_ascii=False)

                writer.writerow(row)

        print(f"[완료] CSV 저장 완료: {output_path}")
        print(f"  - 총 {len(tweets)}개 레코드")

    except Exception as e:
        print(f"[오류] CSV 저장 실패: {e}")

# -----------------------
# 메인 실행
# -----------------------
def main():
    parser = argparse.ArgumentParser(
        description="트위터/X 인용글(Quotes) 추출 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python quote_extractor.py \\
    --url "https://x.com/lottewellfood/status/1983036567561351382/quotes" \\
    --username "your_twitter_id" \\
    --password "your_password" \\
    --output "quotes_result.csv" \\
    --max-scrolls 50
        """
    )

    parser.add_argument("--url", required=True, help="인용글 페이지 URL")
    parser.add_argument("--username", required=True, help="트위터 로그인 ID")
    parser.add_argument("--password", required=True, help="트위터 비밀번호")
    parser.add_argument("--output", default="quotes.csv", help="출력 CSV 파일 경로 (기본: quotes.csv)")
    parser.add_argument("--max-scrolls", type=int, default=None, help="최대 스크롤 횟수 (기본: 무제한)")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드 실행")
    parser.add_argument("--scroll-delay", type=float, default=2.0, help="스크롤 간 대기시간(초, 기본: 2.0)")

    args = parser.parse_args()

    # 드라이버 생성
    print("[정보] Chrome 드라이버 시작 중...")
    driver = None
    try:
        driver = make_driver(headless=args.headless)
    except Exception as e:
        print(f"[오류] 드라이버 생성 실패: {e}")
        return

    try:
        # 로그인
        print("[정보] 트위터 로그인 중...")
        if not login_twitter(driver, args.username, args.password):
            print("[오류] 로그인 실패. 종료합니다.")
            return

        print("[성공] 로그인 완료\n")

        # 인용글 추출
        tweets = extract_quote_tweets(
            driver,
            args.url,
            max_scrolls=args.max_scrolls,
            scroll_delay=args.scroll_delay
        )

        # CSV 저장
        if tweets:
            save_to_csv(tweets, args.output)
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
