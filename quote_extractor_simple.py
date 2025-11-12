#!/usr/bin/env python3
# quote_extractor_simple.py
# 간단하게 시작하는 대화형 버전
# 명령줄 인자 없이 실행하면 대화형으로 입력 받음
#
# 실행: python quote_extractor_simple.py

import os
import time
import random
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
from selenium.webdriver.common.keys import Keys

try:
    from webdriver_manager.chrome import ChromeDriverManager
    AUTO_DRIVER = True
except ImportError:
    AUTO_DRIVER = False
    print("[정보] webdriver-manager 미설치 - 수동 ChromeDriver 경로 사용")

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

    if AUTO_DRIVER:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        driver = webdriver.Chrome(options=opts)

    driver.set_page_load_timeout(60)
    return driver

# -----------------------
# 로그인
# -----------------------
def login_twitter(driver, login_id, login_pw, wait_sec=10):
    print("[정보] 트위터 로그인 중...")
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
        print("[성공] 로그인 완료!")
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
        return None

# -----------------------
# 추출
# -----------------------
def extract_quote_tweets(driver, quotes_url, max_scrolls=None, scroll_delay=2.0):
    print(f"\n[정보] 인용글 페이지 접근 중...")
    driver.get(quotes_url)
    time.sleep(3)

    all_tweets = []
    seen_ids = set()
    scrolls = 0
    no_new_content_count = 0

    print(f"[정보] 스크롤 및 데이터 수집 시작...")
    print("=" * 60)

    while True:
        try:
            articles = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
        except NoSuchElementException:
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

                        # 각 트윗 추출 시 즉시 로그 출력
                        text_preview = tweet_data["text"][:50] + "..." if len(tweet_data["text"]) > 50 else tweet_data["text"]
                        print(f"[수집 #{len(all_tweets):3d}] {tweet_data['author_handle']:20s} | {text_preview}")

                        # 미디어 정보 표시
                        if tweet_data["has_media"] == "TRUE":
                            media_count = len(tweet_data["media_urls"].split(", "))
                            print(f"              └─ 미디어 {media_count}개 포함")

            except Exception:
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

    print("\n" + "=" * 60)
    print(f"[완료] 총 {len(all_tweets)}개 인용글 수집 완료")
    print("=" * 60)
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
    ]

    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for tweet in tweets:
                writer.writerow(tweet)

        print(f"\n[완료] CSV 저장: {output_path}")
        print(f"  - 총 {len(tweets)}개 레코드")
        print(f"  - 위치: {os.path.abspath(output_path)}")

    except Exception as e:
        print(f"[오류] CSV 저장 실패: {e}")

# -----------------------
# 대화형 입력
# -----------------------
def get_user_input():
    print("=" * 60)
    print("   트위터/X 인용글 추출 도구 - 간편 실행 버전")
    print("=" * 60)
    print()

    # URL 입력
    while True:
        url = input("인용글 페이지 URL을 입력하세요: ").strip()
        if "/quotes" in url or "/status/" in url:
            if "/quotes" not in url:
                url = url.rstrip("/") + "/quotes"
            break
        else:
            print("[오류] 올바른 트위터 인용글 URL을 입력하세요.")
            print("예시: https://x.com/user/status/1234567890/quotes")

    # 트위터 로그인 정보
    username = input("\n트위터 아이디를 입력하세요: ").strip()
    password = getpass.getpass("트위터 비밀번호를 입력하세요 (입력 내용 숨김): ")

    # 출력 파일명
    default_output = "quotes.csv"
    output = input(f"\n저장할 파일명 (엔터 = {default_output}): ").strip()
    if not output:
        output = default_output
    if not output.endswith(".csv"):
        output += ".csv"

    # 고급 옵션
    print("\n고급 옵션 (엔터 = 기본값 사용)")

    max_scrolls_input = input("  최대 스크롤 횟수 (엔터 = 무제한): ").strip()
    max_scrolls = None
    if max_scrolls_input:
        try:
            max_scrolls = int(max_scrolls_input)
        except ValueError:
            print("  [경고] 잘못된 값, 무제한으로 설정")
            max_scrolls = None

    headless_input = input("  브라우저 숨김 모드? (y/n, 엔터 = n): ").strip().lower()
    headless = headless_input in ['y', 'yes']

    return {
        "url": url,
        "username": username,
        "password": password,
        "output": output,
        "max_scrolls": max_scrolls,
        "headless": headless,
    }

# -----------------------
# 메인
# -----------------------
def main():
    try:
        # 대화형 입력
        config = get_user_input()

        print("\n" + "=" * 60)
        print("설정 확인:")
        print(f"  URL: {config['url']}")
        print(f"  저장 파일: {config['output']}")
        print(f"  최대 스크롤: {config['max_scrolls'] if config['max_scrolls'] else '무제한'}")
        print(f"  브라우저 숨김: {'예' if config['headless'] else '아니오'}")
        print("=" * 60)

        confirm = input("\n시작하시겠습니까? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("[취소] 종료합니다.")
            return

        # 드라이버 생성
        print("\n[정보] Chrome 드라이버 시작...")
        driver = None
        try:
            driver = make_driver(headless=config['headless'])
        except Exception as e:
            print(f"[오류] 드라이버 생성 실패: {e}")
            print("\n해결 방법:")
            print("  1. Chrome 브라우저 설치 확인")
            print("  2. pip install webdriver-manager 실행")
            return

        try:
            # 로그인
            if not login_twitter(driver, config['username'], config['password']):
                print("[오류] 로그인 실패")
                return

            # 추출
            tweets = extract_quote_tweets(
                driver,
                config['url'],
                max_scrolls=config['max_scrolls'],
                scroll_delay=2.0
            )

            # 저장
            if tweets:
                save_to_csv(tweets, config['output'])
                print(f"\n✅ 성공적으로 완료되었습니다!")
            else:
                print("[경고] 추출된 인용글이 없습니다.")

        except KeyboardInterrupt:
            print("\n[정보] 사용자에 의해 중단되었습니다.")
        except Exception as e:
            print(f"\n[오류] 실행 중 오류: {e}")
        finally:
            if driver:
                driver.quit()
                print("[정보] 브라우저 종료")

    except KeyboardInterrupt:
        print("\n[정보] 종료합니다.")
    except Exception as e:
        print(f"[오류] {e}")

if __name__ == "__main__":
    main()
