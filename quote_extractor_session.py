#!/usr/bin/env python3
# quote_extractor_session.py
# 세션 저장/재사용 버전 - 한 번만 로그인하고 쿠키 재사용
#
# 특징:
# - 첫 실행: 로그인 후 쿠키 저장
# - 이후 실행: 저장된 쿠키로 자동 로그인
# - 세션 만료 시 자동 재로그인
#
# 실행: python quote_extractor_session.py

import os
import time
import random
import csv
import json
import pickle
import getpass
from datetime import datetime, timedelta
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

# -----------------------
# 설정값
# -----------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SCROLL_PAUSE = 2.0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config_defaults.json")

# 세션 저장 경로
SESSION_DIR = os.path.join(BASE_DIR, ".session")
COOKIES_FILE = os.path.join(SESSION_DIR, "twitter_cookies.pkl")
SESSION_INFO_FILE = os.path.join(SESSION_DIR, "session_info.json")

# 세션 유효 기간 (일)
SESSION_VALID_DAYS = 30

# -----------------------
# 세션 디렉토리 생성
# -----------------------
def init_session_dir():
    """세션 저장 디렉토리 생성"""
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)
        print(f"[정보] 세션 디렉토리 생성: {SESSION_DIR}")

# -----------------------
# 쿠키 저장
# -----------------------
def save_cookies(driver, username):
    """
    현재 세션의 쿠키를 파일로 저장

    Args:
        driver: Selenium WebDriver
        username: 트위터 아이디 (파일명 구분용)
    """
    try:
        init_session_dir()

        # 쿠키 저장
        cookies = driver.get_cookies()
        with open(COOKIES_FILE, "wb") as f:
            pickle.dump(cookies, f)

        # 세션 정보 저장 (생성 시간, 사용자명 등)
        session_info = {
            "username": username,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=SESSION_VALID_DAYS)).isoformat(),
            "user_agent": USER_AGENT,
        }
        with open(SESSION_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(session_info, f, indent=2, ensure_ascii=False)

        print(f"[성공] 세션 저장 완료 (유효기간: {SESSION_VALID_DAYS}일)")
        print(f"  - 위치: {SESSION_DIR}")
        return True

    except Exception as e:
        print(f"[경고] 세션 저장 실패: {e}")
        return False

# -----------------------
# 쿠키 로드
# -----------------------
def load_cookies(driver):
    """
    저장된 쿠키를 로드하여 세션 복원

    Args:
        driver: Selenium WebDriver

    Returns:
        bool: 로드 성공 여부
    """
    try:
        # 파일 존재 확인
        if not os.path.exists(COOKIES_FILE):
            print("[정보] 저장된 세션이 없습니다. 로그인이 필요합니다.")
            return False

        # 세션 정보 확인
        if os.path.exists(SESSION_INFO_FILE):
            with open(SESSION_INFO_FILE, "r", encoding="utf-8") as f:
                session_info = json.load(f)

            # 만료 확인
            expires_at = datetime.fromisoformat(session_info["expires_at"])
            if datetime.now() > expires_at:
                print("[정보] 세션이 만료되었습니다. 재로그인이 필요합니다.")
                return False

            print(f"[정보] 저장된 세션 발견")
            print(f"  - 사용자: {session_info.get('username', 'unknown')}")
            print(f"  - 생성일: {session_info.get('created_at', 'unknown')}")
            print(f"  - 만료일: {session_info.get('expires_at', 'unknown')}")

        # Twitter 홈페이지로 먼저 이동 (쿠키 도메인 일치 필요)
        driver.get("https://twitter.com")
        time.sleep(2)

        # 쿠키 로드
        with open(COOKIES_FILE, "rb") as f:
            cookies = pickle.load(f)

        for cookie in cookies:
            try:
                # sameSite 속성 처리 (Selenium 호환성)
                if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = 'None'
                driver.add_cookie(cookie)
            except Exception as e:
                # 일부 쿠키 실패해도 계속 진행
                continue

        print("[정보] 쿠키 로드 완료, 세션 검증 중...")

        # 세션 유효성 검증
        driver.get("https://twitter.com/home")
        time.sleep(3)

        # 로그인 상태 확인
        if is_logged_in(driver):
            print("[성공] 저장된 세션으로 로그인 성공!")
            return True
        else:
            print("[정보] 세션이 유효하지 않습니다. 재로그인이 필요합니다.")
            return False

    except Exception as e:
        print(f"[경고] 세션 로드 실패: {e}")
        return False

# -----------------------
# 로그인 상태 확인
# -----------------------
def is_logged_in(driver, timeout=5):
    """
    현재 로그인 상태인지 확인

    Args:
        driver: Selenium WebDriver
        timeout: 대기 시간

    Returns:
        bool: 로그인 여부
    """
    try:
        # 홈 URL 확인
        if "twitter.com/home" in driver.current_url or "x.com/home" in driver.current_url:
            return True

        # 홈 탭 또는 사이드바 요소 확인
        home_indicators = [
            (By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]'),
            (By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'),
            (By.XPATH, "//a[@aria-label='Home' or @aria-label='홈']"),
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

    except Exception:
        return False

# -----------------------
# 세션 삭제
# -----------------------
def clear_session():
    """저장된 세션 삭제"""
    try:
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
        if os.path.exists(SESSION_INFO_FILE):
            os.remove(SESSION_INFO_FILE)
        print("[정보] 저장된 세션이 삭제되었습니다.")
        return True
    except Exception as e:
        print(f"[경고] 세션 삭제 실패: {e}")
        return False

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
# 로그인 (기존 코드)
# -----------------------
def login_twitter(driver, login_id, login_pw, wait_sec=10):
    """트위터 로그인"""
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

        time.sleep(5)

        if is_logged_in(driver):
            print("[성공] 로그인 완료!")
            return True
        else:
            print("[오류] 로그인 실패")
            return False

    except Exception as e:
        print(f"[오류] 로그인 실패: {e}")
        return False

# -----------------------
# 로그인 또는 세션 복원
# -----------------------
def login_or_restore_session(driver, username=None, password=None, force_login=False):
    """
    세션 복원 시도, 실패 시 로그인

    Args:
        driver: Selenium WebDriver
        username: 트위터 아이디 (로그인 필요 시)
        password: 트위터 비밀번호 (로그인 필요 시)
        force_login: True면 세션 무시하고 강제 로그인

    Returns:
        bool: 성공 여부
    """
    # 강제 로그인 모드
    if force_login:
        print("[정보] 강제 로그인 모드")
        if username and password:
            if login_twitter(driver, username, password):
                save_cookies(driver, username)
                return True
        return False

    # 세션 복원 시도
    print("[정보] 저장된 세션 확인 중...")
    if load_cookies(driver):
        return True

    # 세션 복원 실패 - 로그인 필요
    print("\n[정보] 로그인이 필요합니다.")

    if not username:
        username = input("트위터 아이디: ").strip()
    if not password:
        password = getpass.getpass("트위터 비밀번호 (입력 숨김): ")

    if login_twitter(driver, username, password):
        save_cookies(driver, username)
        return True

    return False

# -----------------------
# 파싱 및 추출 함수들 (기존과 동일)
# -----------------------
def parse_quote_tweet(article):
    """트윗 파싱"""
    try:
        data = {
            "status_id": "", "url": "", "author_handle": "", "text": "",
            "hashtags": "", "time_iso_utc": "", "has_media": "",
            "media_urls": "", "is_quote": "", "quote_status_id": "인용X",
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
        except:
            pass

        try:
            tweet_text_div = article.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
            data["text"] = tweet_text_div.text.strip()
            hashtag_links = tweet_text_div.find_elements(By.CSS_SELECTOR, "a[href*='/hashtag/']")
            hashtags = [link.text.strip() for link in hashtag_links if link.text.strip()]
            data["hashtags"] = ", ".join(hashtags) if hashtags else ""
        except:
            pass

        try:
            time_element = article.find_element(By.CSS_SELECTOR, "time[datetime]")
            data["time_iso_utc"] = time_element.get_attribute("datetime")
        except:
            pass

        media_urls = []
        try:
            images = article.find_elements(By.CSS_SELECTOR, "img[src*='pbs.twimg.com']")
            for img in images:
                src = img.get_attribute("src")
                if src and "profile_images" not in src:
                    media_urls.append(src.split("&name=")[0] + "&name=large" if "name=" in src else src)
        except:
            pass

        if media_urls:
            data["has_media"] = "TRUE"
            data["media_urls"] = ", ".join(media_urls)
        else:
            data["has_media"] = "FALSE"
            data["media_urls"] = "인용X"

        data["is_quote"] = "FALSE"
        return data

    except Exception:
        return None

def extract_quote_tweets(driver, quotes_url, max_scrolls=None, scroll_delay=2.0):
    """인용글 추출"""
    print(f"\n[정보] 인용글 페이지 접근...")
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
        except:
            break

        new_tweets = 0
        for article in articles:
            tweet_data = parse_quote_tweet(article)
            if tweet_data and tweet_data["status_id"] and tweet_data["status_id"] not in seen_ids:
                seen_ids.add(tweet_data["status_id"])
                all_tweets.append(tweet_data)
                new_tweets += 1

                # 각 트윗 추출 시 즉시 로그 출력
                text_preview = tweet_data["text"][:50] + "..." if len(tweet_data["text"]) > 50 else tweet_data["text"]
                print(f"[수집 #{len(all_tweets):3d}] {tweet_data['author_handle']:20s} | {text_preview}")

                # 미디어 정보 표시
                if tweet_data["has_media"] == "TRUE":
                    media_count = len(tweet_data["media_urls"].split(", "))
                    print(f"              └─ 미디어 {media_count}개 포함")

        # 스크롤 정보 표시
        scrolls += 1
        scroll_info = f"[스크롤 #{scrolls:2d}]"
        if max_scrolls:
            scroll_info += f" ({scrolls}/{max_scrolls})"

        if new_tweets > 0:
            print(f"\n{scroll_info} 이번 스크롤에서 {new_tweets}개 신규 추출 (총 {len(all_tweets)}개)")
        else:
            print(f"\n{scroll_info} 신규 데이터 없음 (중복 또는 끝)")
            no_new_content_count += 1

        if new_tweets == 0:
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

        if max_scrolls and scrolls >= max_scrolls:
            print(f"[정보] 최대 스크롤 횟수 ({max_scrolls}회) 도달 - 수집 종료")
            break

        print("=" * 60)

    print("\n" + "=" * 60)
    print(f"[완료] 총 {len(all_tweets)}개 인용글 수집 완료")
    print("=" * 60)
    return all_tweets

def save_to_csv(tweets, output_path):
    """CSV 저장"""
    if not tweets:
        print("[경고] 저장할 데이터 없음")
        return

    fieldnames = ["status_id", "url", "author_handle", "text", "hashtags",
                  "time_iso_utc", "has_media", "media_urls", "is_quote",
                  "quote_status_id", "quote_time_iso_utc"]

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
    print("=" * 60)
    print("   트위터 인용글 추출 - 세션 저장 버전")
    print("=" * 60)
    print()

    # 옵션 선택
    print("옵션:")
    print("  1. 일반 실행 (저장된 세션 사용)")
    print("  2. 강제 로그인 (세션 무시)")
    print("  3. 세션 삭제")

    choice = input("\n선택 (엔터 = 1): ").strip() or "1"

    if choice == "3":
        clear_session()
        return

    force_login = (choice == "2")

    # URL 입력
    url = input("\n인용글 URL: ").strip()
    if "/quotes" not in url:
        url = url.rstrip("/") + "/quotes"

    # 로그인 정보 (세션 없을 때만 필요)
    username = None
    password = None

    if force_login or not os.path.exists(COOKIES_FILE):
        username = input("트위터 아이디: ").strip()
        password = getpass.getpass("트위터 비밀번호 (입력 숨김): ")

    # 출력 파일
    output = input(f"저장 파일명 (엔터 = quotes.csv): ").strip() or "quotes.csv"
    if not output.endswith(".csv"):
        output += ".csv"

    # 고급 옵션
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

        # 로그인 또는 세션 복원
        if not login_or_restore_session(driver, username, password, force_login):
            print("[오류] 로그인 실패")
            return

        # 추출
        tweets = extract_quote_tweets(driver, url, max_scrolls=max_scrolls)

        # 저장
        if tweets:
            save_to_csv(tweets, output)
            print(f"\n✅ 성공!")
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
