# social_media_verification_tool.py
# 트위터 리트윗 검증 + 인스타그램 댓글 검증 통합 도구
# 실행 전: pip install selenium pillow
# Chrome & chromedriver 버전 일치 필요
# Mac/Windows 양쪽에서 동작하도록 설계됨

import os
import time
import random
import csv
import threading
import tkinter as tk
from io import BytesIO
from tkinter import ttk, filedialog, messagebox
import json
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException
)

from PIL import Image, ImageTk

# -----------------------
# 설정값 (필요 시 조정)
# -----------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SCROLL_PAUSE = 2.0
# 사용자 간 기본 대기 시간(초)
DEFAULT_USER_DELAY = 10.0
# 타임라인 로딩 대기 범위(초)
TIMELINE_WAIT_RANGE = (10.0, 13.0)
# None: 스크롤 제한 없이 콘텐츠 끝까지 탐색
MAX_SCROLLS_PER_PROFILE = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CAPTURE_DIR = os.path.join(BASE_DIR, "captures")
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config_defaults.json")
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ICON_PATH = os.path.join(BASE_DIR, "free-icon-music-12784989.png")


def load_selector_config():
    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            defaults = json.load(f)
    except Exception:
        defaults = {
            "next_button_xpaths": [
                "//div[@role='button' and .//span[normalize-space(text())='Next' or normalize-space(text())='다음']]",
                "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]",
            ],
            "login_button_xpaths": [
                "//div[@role='button' and .//span[normalize-space(text())='Log in' or normalize-space(text())='로그인']]",
                "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button",
            ],
            "article_xpath_template": "//a[contains(@href,'/status/{tweet_id}')]/ancestor::article",
        }

    if os.path.isfile(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            for key, value in overrides.items():
                defaults[key] = value
        except Exception:
            print("[경고] 사용자 설정 파일을 불러오지 못했습니다. 기본값을 사용합니다.")
    return defaults


def save_user_config(config_data):
    try:
        with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    except Exception:
        messagebox.showerror("설정 저장 오류", "설정 파일을 저장할 수 없습니다. 경로 권한을 확인해 주세요.")


def reset_user_config():
    if os.path.isfile(USER_CONFIG_PATH):
        try:
            os.remove(USER_CONFIG_PATH)
        except Exception:
            messagebox.showerror("설정 초기화 오류", "설정을 초기화할 수 없습니다. 파일 권한을 확인해 주세요.")


SELECTOR_CONFIG = load_selector_config()

# -----------------------
# Selenium 드라이버 생성
# -----------------------
def make_driver(headless=True, user_data_dir=None):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"user-agent={USER_AGENT}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1200,2000")
    # 라이트 모드 강제 설정
    opts.add_argument("--force-dark-mode=0")
    opts.add_experimental_option("prefs", {"profile.default_content_setting_values.prefers_color_scheme": 1})
    # 사용자 프로필을 재사용하고 싶다면 user_data_dir 인자에 경로를 넣어 재로그인 방지 가능
    if user_data_dir:
        opts.add_argument(f"--user-data-dir={user_data_dir}")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver

# -----------------------
# 수동 로그인 대기 처리
# -----------------------
def wait_for_manual_login(driver, wait_sec=300, platform="twitter"):
    """
    사용자가 수동으로 로그인할 때까지 대기:
    - 플랫폼 로그인 페이지를 열어 사용자가 직접 로그인하도록 함
    - 로그인 완료 여부는 URL 변화와 홈 페이지 요소를 통해 확인
    - 최대 wait_sec 동안 대기 (기본 5분)
    반환: True/False
    """
    if platform == "instagram":
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(2)
        messagebox.showinfo(
            "수동 로그인 필요",
            "브라우저 창에서 직접 Instagram에 로그인해주세요.\n로그인이 완료되면 자동으로 진행됩니다.\n\n(최대 5분 대기)"
        )
    else:
        # twitter.com은 x.com으로 자동 리디렉션됨
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(2)  # 페이지 로드 대기
        messagebox.showinfo(
            "수동 로그인 필요",
            "브라우저 창에서 직접 X(Twitter)에 로그인해주세요.\n로그인이 완료되면 자동으로 진행됩니다.\n\n(최대 5분 대기)"
        )

    try:
        if platform == "instagram":
            # 인스타그램 로그인 확인
            def has_instagram_login(drv):
                current_url = drv.current_url
                # 로그인 페이지가 아니면 성공
                if "/accounts/login" not in current_url:
                    # 추가 확인: 주요 요소 존재
                    try:
                        # 네비게이션 바나 프로필 링크 확인
                        elements = drv.find_elements(By.CSS_SELECTOR, 'a[href*="/accounts/edit"]')
                        if elements:
                            return True
                        # URL이 instagram.com이고 로그인 페이지가 아니면
                        if "instagram.com" in current_url and "/accounts" not in current_url:
                            return True
                    except:
                        pass
                return False

            WebDriverWait(driver, wait_sec).until(has_instagram_login)
            time.sleep(2)
            return True
        else:
            # 트위터 로그인 확인
            home_fragments = ("/home", "twitter.com/?", "x.com/?")
            nav_locators = [
                (By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]'),
                (By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'),
                (By.CSS_SELECTOR, '[data-testid="primaryColumn"]'),
                (By.CSS_SELECTOR, '[aria-label="Home"]'),
            ]

            def has_home_signal(drv):
                """로그인 완료 감지 - URL 체크 및 홈 요소 확인"""
                current_url = drv.current_url

                # URL 기반 체크
                if any(fragment in current_url for fragment in home_fragments):
                    # 추가로 페이지 요소 확인
                    for locator in nav_locators:
                        try:
                            element = drv.find_element(*locator)
                            if element.is_displayed():
                                return True
                        except NoSuchElementException:
                            continue
                    # URL이 홈이면 요소가 없어도 True
                    if "/home" in current_url:
                        return True

                return False

            # 5분 동안 로그인 완료 대기
            WebDriverWait(driver, wait_sec).until(has_home_signal)
            time.sleep(2)  # 페이지 완전히 로드 대기
            return True

    except TimeoutException:
        messagebox.showerror("로그인 시간 초과", "5분 내에 로그인을 완료하지 못했습니다.")
        return False
    except Exception as e:
        raise RuntimeError("login_error") from e

# -----------------------
# 요소 스크린샷 헬퍼 (트윗 전체 영역 보장)
# -----------------------
def save_element_screenshot(driver, element, save_path):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
    time.sleep(0.3)
    try:
        rect = driver.execute_script(
            "const r = arguments[0].getBoundingClientRect();"
            "return {left: r.left, top: r.top, width: r.width, height: r.height, dpr: window.devicePixelRatio || 1};",
            element,
        )
        if not rect:
            raise ValueError("Bounding rect unavailable")

        screenshot = Image.open(BytesIO(driver.get_screenshot_as_png()))
        left = int(rect["left"] * rect["dpr"])
        top = int(rect["top"] * rect["dpr"])
        right = left + int(rect["width"] * rect["dpr"])
        bottom = top + int(rect["height"] * rect["dpr"])

        # ensure bounds within screenshot
        right = min(right, screenshot.width)
        bottom = min(bottom, screenshot.height)

        if right <= left or bottom <= top:
            raise ValueError("Invalid crop bounds")

        element_img = screenshot.crop((left, top, right, bottom))
        element_img.save(save_path)
        return True
    except Exception:
        # fallback: 전체 페이지 캡처로 대체
        try:
            driver.save_screenshot(save_path)
            return True
        except Exception:
            messagebox.showerror("캡처 오류", "캡처 저장 중 오류가 발생했습니다. 개발자에게 문의해주세요.")
            return False

# -----------------------
# 프로필에서 특정 트윗 ID 존재 여부 및 캡처
# -----------------------
def check_profile_and_capture(driver, username, tweet_id, capture_dir, max_scrolls=MAX_SCROLLS_PER_PROFILE):
    username = username.lstrip("@").strip()
    profile_url = f"https://twitter.com/{username}"
    target_fragment = f"/status/{tweet_id}"
    found = False
    capture_path = ""
    article_xpath_template = SELECTOR_CONFIG.get(
        "article_xpath_template",
        "//a[contains(@href,'/status/{tweet_id}')]/ancestor::article",
    )
    try:
        driver.get(profile_url)
    except Exception:
        messagebox.showerror("프로필 오류", f"{username} 프로필을 불러오지 못했습니다. 아이디가 잘못되었거나 직접 확인이 필요합니다.")
        return False, ""

    wait_min, wait_max = TIMELINE_WAIT_RANGE
    time.sleep(random.uniform(wait_min, wait_max))

    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    while True:
        page_src = driver.page_source
        if target_fragment in page_src:
            # 리트윗/언급 발견: 구체적 DOM 요소를 찾아 스크린샷 시도
            found = True
            try:
                # 위치 기반으로 article ancestor 추출
                # 트윗 링크를 포함하는 a[href*="/status/{tweet_id}"]를 찾고 그 조상 article을 캡처
                xpath = article_xpath_template.format(tweet_id=tweet_id)
                articles = driver.find_elements(By.XPATH, xpath)
                # 첫 번째 article을 캡처
                if articles:
                    el = articles[0]
                    fname = f"{username}_{tweet_id}.png"
                    save_path = os.path.join(capture_dir, fname)
                    if save_element_screenshot(driver, el, save_path):
                        capture_path = save_path
                    else:
                        capture_path = ""
                else:
                    # fallback: 전체 페이지 캡처
                    fname = f"{username}_{tweet_id}_page.png"
                    save_path = os.path.join(capture_dir, fname)
                    driver.save_screenshot(save_path)
                    capture_path = save_path
            except Exception:
                try:
                    fname = f"{username}_{tweet_id}_page.png"
                    save_path = os.path.join(capture_dir, fname)
                    driver.save_screenshot(save_path)
                    capture_path = save_path
                except Exception:
                    messagebox.showerror("캡처 오류", f"{username}의 트윗 캡처에 실패했습니다. 개발자에게 문의해주세요.")
                    capture_path = ""
            break

        # 스크롤 더 로드
        if random.random() < 0.15:
            midpoint = driver.execute_script("return document.body.scrollHeight * 0.5")
            driver.execute_script("window.scrollTo(0, arguments[0]);", midpoint)
            time.sleep(random.uniform(SCROLL_PAUSE * 0.5, SCROLL_PAUSE * 1.5))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        pause = random.uniform(SCROLL_PAUSE, SCROLL_PAUSE * 4)
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolls += 1
        if max_scrolls is not None and scrolls >= max_scrolls:
            break

    return found, capture_path

# -----------------------
# 인스타그램 댓글 검증 관련 함수들
# -----------------------
def check_instagram_comment_and_capture(driver, post_url, username, capture_dir):
    """
    인스타그램 게시글에서 특정 사용자의 댓글을 찾고 캡처 (강화된 로직)
    """
    username = username.lstrip("@").strip()
    found = False
    capture_path = ""

    try:
        driver.get(post_url)
    except Exception:
        messagebox.showerror("게시글 오류", f"게시글을 불러오지 못했습니다: {post_url}")
        return False, ""

    # 페이지 로딩 대기
    time.sleep(random.uniform(4.0, 6.0))

    try:
        # 1단계: 댓글 섹션 찾기 및 확장
        print(f"[{username}] 댓글 섹션 로딩 중...")

        # 댓글 더보기 버튼 클릭 (여러 번 시도)
        for attempt in range(8):
            try:
                # 다양한 "댓글 더보기" 버튼 셀렉터
                load_more_selectors = [
                    "//span[contains(text(), '댓글') and contains(text(), '모두 보기')]",
                    "//button[contains(text(), 'View all')]",
                    "//span[contains(text(), 'View all')]//parent::button",
                    "//div[@role='button']//span[contains(text(), 'comment')]",
                ]

                clicked = False
                for selector in load_more_selectors:
                    try:
                        buttons = driver.find_elements(By.XPATH, selector)
                        for btn in buttons:
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(0.5)
                                btn.click()
                                time.sleep(1.5)
                                clicked = True
                                print(f"[{username}] 댓글 더보기 클릭 ({attempt + 1})")
                                break
                        if clicked:
                            break
                    except:
                        continue

                if not clicked:
                    # 더 이상 버튼이 없으면 스크롤
                    driver.execute_script("window.scrollBy(0, 300);")
                    time.sleep(1.0)
            except:
                pass

        # 2단계: 사용자 검색 (다양한 방법)
        print(f"[{username}] 사용자 검색 중...")

        # 방법 1: 프로필 링크로 검색 (가장 확실함)
        profile_link_selectors = [
            f"//a[@href='/{username}/']",
            f"//a[contains(@href, '/{username}/')]",
            f"//a[@href='/{username}' or @href='/{username}/']",
        ]

        comment_element = None
        for selector in profile_link_selectors:
            try:
                links = driver.find_elements(By.XPATH, selector)
                print(f"[{username}] 프로필 링크 {len(links)}개 발견")

                for link in links:
                    try:
                        # 링크가 댓글 영역 내에 있는지 확인
                        # 부모 요소를 올라가면서 댓글 컨테이너 찾기
                        parent_selectors = [
                            "./ancestor::ul//li",  # 댓글 목록의 li
                            "./ancestor::div[@role='button']",  # 버튼 역할의 div
                            "./ancestor::article//div[contains(@style, 'padding')]",  # article 내 패딩 div
                        ]

                        for parent_sel in parent_selectors:
                            try:
                                container = link.find_element(By.XPATH, parent_sel)
                                # 댓글 텍스트가 있는지 확인
                                if container.text and len(container.text) > len(username):
                                    comment_element = container
                                    found = True
                                    print(f"[{username}] ✓ 댓글 발견! (방법: {parent_sel})")
                                    break
                            except:
                                continue

                        if found:
                            break
                    except:
                        continue

                if found:
                    break
            except:
                continue

        # 방법 2: 페이지 소스에서 직접 검색 (fallback)
        if not found:
            page_source = driver.page_source
            if f'"{username}"' in page_source or f"'{username}'" in page_source or f"/{username}/" in page_source:
                print(f"[{username}] 페이지 소스에서 발견 (전체 페이지 캡처)")
                found = True
                fname = f"instagram_{username}_full_page.png"
                save_path = os.path.join(capture_dir, fname)
                driver.save_screenshot(save_path)
                capture_path = save_path

        # 3단계: 댓글 캡처
        if found and comment_element:
            fname = f"instagram_{username}_comment.png"
            save_path = os.path.join(capture_dir, fname)

            # 댓글을 화면 중앙으로 스크롤
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", comment_element)
            time.sleep(1.5)

            # 캡처 시도
            if save_element_screenshot(driver, comment_element, save_path):
                capture_path = save_path
                print(f"[{username}] ✓ 댓글 캡처 완료: {save_path}")
            else:
                # fallback: 전체 페이지
                fname = f"instagram_{username}_fallback.png"
                save_path = os.path.join(capture_dir, fname)
                driver.save_screenshot(save_path)
                capture_path = save_path
                print(f"[{username}] ⚠ fallback 캡처: {save_path}")

    except Exception as e:
        print(f"[{username}] Error: {e}")
        # 에러 발생 시에도 페이지 캡처 시도
        try:
            fname = f"instagram_{username}_error.png"
            save_path = os.path.join(capture_dir, fname)
            driver.save_screenshot(save_path)
            capture_path = save_path
        except:
            pass

    return found, capture_path

# -----------------------
# 백그라운드 스레드로 검사 진행 (GUI 블로킹 방지)
# -----------------------
def run_check_thread(tweet_id, usernames, login_id, login_pw, headless, tree, btn_run, btn_save, capture_dir, per_user_delay, progress_bar, progress_var, status_var=None):
    btn_run.config(state="disabled")
    btn_save.config(state="disabled")
    # 드라이버 생성 및 수동 로그인 대기
    driver = None
    try:
        driver = make_driver(headless=headless)
    except Exception:
        messagebox.showerror("드라이버 오류", "ChromeDriver 실행 중 오류가 발생했습니다. 개발자에게 문의해주세요.")
        btn_run.config(state="normal")
        btn_save.config(state="disabled")
        if progress_var is not None:
            progress_var.set(0)
        if status_var is not None:
            status_var.set("드라이버 오류")
        return

    try:
        login_ok = wait_for_manual_login(driver)
    except RuntimeError:
        driver.quit()
        messagebox.showerror("로그인 오류", "로그인 중 오류가 발생했습니다. 개발자에게 문의해주세요.")
        btn_run.config(state="normal")
        btn_save.config(state="disabled")
        if progress_var is not None:
            progress_var.set(0)
        if status_var is not None:
            status_var.set("로그인 오류")
        return

    if not login_ok:
        # 로그인 실패 시 드라이버 닫고 상태 복원
        driver.quit()
        messagebox.showerror("로그인 실패", "로그인에 실패했습니다. 다시 시도해주세요.")
        btn_run.config(state="normal")
        btn_save.config(state="disabled")
        if progress_var is not None:
            progress_var.set(0)
        if status_var is not None:
            status_var.set("로그인 실패")
        return

    # 테이블 초기화
    for row in tree.get_children():
        tree.delete(row)

    total = len(usernames)
    if progress_bar is not None and progress_var is not None:
        progress_bar.configure(maximum=max(total, 1))
        progress_var.set(0)
    tqdm_bar = tqdm(total=total, desc="검사 진행", leave=False) if tqdm and total else None
    for idx, user in enumerate(usernames):
        # 느리게, 무작위 딜레이로 차단 위험 완화
        delay = max(per_user_delay, 0)
        if idx and idx % random.randint(3, 5) == 0:
            time.sleep(random.uniform(delay + 4.0, delay + 8.0))
        time.sleep(random.uniform(delay, delay + 2.5))
        found, capture = check_profile_and_capture(driver, user, tweet_id, capture_dir)
        tree.insert("", "end", values=(
            user,
            "YES" if found else "NO",
            capture if capture else "",
        ))
        if status_var is not None:
            status_var.set(f"검사 중... ({idx + 1}/{total})")
        if progress_var is not None:
            progress_var.set(idx + 1)
        if tqdm_bar is not None:
            tqdm_bar.update(1)

    # 완료 후 드라이버 닫기
    driver.quit()
    btn_save.config(state="normal")
    btn_run.config(state="normal")
    if status_var is not None:
        status_var.set("검사 완료")
    if progress_var is not None:
        progress_var.set(total)
    if tqdm_bar is not None:
        tqdm_bar.close()
    messagebox.showinfo("완료", "검사가 완료됨. 결과를 저장하세요.")

# 인스타그램 댓글 검사 스레드
def run_instagram_check_thread(post_url, usernames, headless, tree, btn_run, btn_save, capture_dir, per_user_delay, progress_bar, progress_var, status_var=None):
    btn_run.config(state="disabled")
    btn_save.config(state="disabled")
    driver = None

    try:
        driver = make_driver(headless=headless)
    except Exception:
        messagebox.showerror("드라이버 오류", "ChromeDriver 실행 중 오류가 발생했습니다.")
        btn_run.config(state="normal")
        btn_save.config(state="disabled")
        if progress_var is not None:
            progress_var.set(0)
        if status_var is not None:
            status_var.set("드라이버 오류")
        return

    try:
        login_ok = wait_for_manual_login(driver, platform="instagram")
    except RuntimeError:
        driver.quit()
        messagebox.showerror("로그인 오류", "인스타그램 로그인 중 오류가 발생했습니다.")
        btn_run.config(state="normal")
        btn_save.config(state="disabled")
        if progress_var is not None:
            progress_var.set(0)
        if status_var is not None:
            status_var.set("로그인 오류")
        return

    if not login_ok:
        driver.quit()
        messagebox.showerror("로그인 실패", "인스타그램 로그인에 실패했습니다.")
        btn_run.config(state="normal")
        btn_save.config(state="disabled")
        if progress_var is not None:
            progress_var.set(0)
        if status_var is not None:
            status_var.set("로그인 실패")
        return

    # 테이블 초기화
    for row in tree.get_children():
        tree.delete(row)

    total = len(usernames)
    if progress_bar is not None and progress_var is not None:
        progress_bar.configure(maximum=max(total, 1))
        progress_var.set(0)

    for idx, user in enumerate(usernames):
        delay = max(per_user_delay, 0)
        if idx > 0:
            time.sleep(random.uniform(delay, delay + 2.5))

        found, capture = check_instagram_comment_and_capture(driver, post_url, user, capture_dir)
        tree.insert("", "end", values=(
            user,
            "YES" if found else "NO",
            capture if capture else "",
        ))

        if status_var is not None:
            status_var.set(f"검사 중... ({idx + 1}/{total})")
        if progress_var is not None:
            progress_var.set(idx + 1)

    driver.quit()
    btn_save.config(state="normal")
    btn_run.config(state="normal")
    if status_var is not None:
        status_var.set("검사 완료")
    if progress_var is not None:
        progress_var.set(total)
    messagebox.showinfo("완료", "인스타그램 댓글 검사가 완료되었습니다.")

# -----------------------
# GUI 구성
# -----------------------
def build_gui():
    root = tk.Tk()
    root.title("소셜미디어 검증 도구")

    if os.path.isfile(ICON_PATH):
        try:
            icon_image = Image.open(ICON_PATH)
            icon_photo = ImageTk.PhotoImage(icon_image)
            root.iconphoto(False, icon_photo)
            root._icon_photo = icon_photo  # prevent garbage collection
        except Exception:
            print("[경고] 아이콘을 로드할 수 없어 기본 아이콘을 사용합니다.")
    bg_color = "#1f1f1f"
    card_bg = "#2b2b2b"
    accent_color = "#f0f0f0"
    muted_color = "#bbbbbb"

    root.configure(bg=bg_color)
    root.minsize(960, 640)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("Main.TFrame", background=bg_color)
    style.configure("Card.TLabelframe", background=card_bg, bordercolor="#3a3a3a", borderwidth=1, padding=(16, 12))
    style.configure("Card.TLabelframe.Label", background=card_bg, foreground=accent_color, font=("Helvetica", 12, "bold"))
    style.configure("Primary.TButton", font=("Helvetica", 11, "bold"), padding=(12, 6), foreground="#f5f5f5")
    style.configure("Secondary.TButton", font=("Helvetica", 11), padding=(12, 6), foreground=accent_color)
    style.map("Primary.TButton", background=[("disabled", "#555555"), ("!disabled", "#404040")])
    style.map("Secondary.TButton", background=[("disabled", "#555555"), ("!disabled", "#333333")])
    style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), foreground=accent_color, background=bg_color)
    style.configure("Subheader.TLabel", font=("Helvetica", 11), foreground=muted_color, background=bg_color)
    style.configure("Treeview", background=card_bg, fieldbackground=card_bg, bordercolor=bg_color, foreground=accent_color)
    style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"), foreground=accent_color, background="#333333")
    style.map("Treeview", background=[("selected", "#404040")], foreground=[("selected", "#ffffff")])
    style.configure("Horizontal.TScrollbar", background=bg_color, troughcolor="#2a2a2a")
    style.configure("Vertical.TScrollbar", background=bg_color, troughcolor="#2a2a2a")
    style.configure("TProgressbar", troughcolor="#2a2a2a", background="#555555", bordercolor="#2a2a2a", lightcolor="#555555", darkcolor="#555555")
    style.configure("Horizontal.TProgressbar", troughcolor="#2a2a2a", background="#555555", bordercolor="#2a2a2a")

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    main = ttk.Frame(root, style="Main.TFrame", padding=(24, 20, 24, 16))
    main.grid(row=0, column=0, sticky="nsew")
    main.columnconfigure(0, weight=3)
    main.columnconfigure(1, weight=2)
    main.rowconfigure(5, weight=1)

    header = ttk.Label(main, text="소셜미디어 검증 도구", style="Header.TLabel")
    header.grid(row=0, column=0, columnspan=2, sticky="w")

    # 모드 선택 프레임
    mode_frame = ttk.Frame(main, style="Main.TFrame")
    mode_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))

    mode_var = tk.StringVar(value="twitter")

    ttk.Radiobutton(
        mode_frame,
        text="트위터 리트윗 검증",
        variable=mode_var,
        value="twitter",
        style="Secondary.TButton"
    ).pack(side="left", padx=(0, 10))

    ttk.Radiobutton(
        mode_frame,
        text="인스타그램 댓글 검증",
        variable=mode_var,
        value="instagram",
        style="Secondary.TButton"
    ).pack(side="left")

    event_frame = ttk.Frame(main, style="Main.TFrame")
    event_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 12))
    event_frame.columnconfigure(1, weight=1)

    def attach_paste_menu(widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="붙여넣기", command=lambda: widget.event_generate('<<Paste>>'))

        def show(event):
            menu.tk_popup(event.x_root, event.y_root)
            menu.grab_release()
            return "break"

        widget.bind("<Button-3>", show)
        widget.bind("<Button-2>", show)

    label_event_id = ttk.Label(event_frame, text="이벤트 트윗 ID / 인스타 게시글 URL", style="Subheader.TLabel")
    label_event_id.grid(row=0, column=0, sticky="w", pady=(0, 6))
    entry_tweet = ttk.Entry(event_frame)
    entry_tweet.grid(row=0, column=1, sticky="ew", pady=(0, 6))
    attach_paste_menu(entry_tweet)

    label_users = ttk.Label(event_frame, text="당첨자 목록 (쉼표 구분)", style="Subheader.TLabel")
    label_users.grid(row=1, column=0, sticky="nw")
    text_users = tk.Text(event_frame, width=40, height=5, wrap="word", relief="flat", borderwidth=0)
    text_users.grid(row=1, column=1, sticky="nsew")
    text_users.configure(bg="#f5f5f5", fg="#222222", highlightbackground="#a0a0a0", highlightthickness=1, insertbackground="#222222")
    event_frame.rowconfigure(1, weight=1)
    attach_paste_menu(text_users)

    ttk.Label(event_frame, text="캡처 저장 폴더", style="Subheader.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 0))
    capture_dir_var = tk.StringVar(value=DEFAULT_CAPTURE_DIR)

    capture_frame = ttk.Frame(event_frame, style="Main.TFrame")
    capture_frame.grid(row=2, column=1, sticky="ew", pady=(10, 0))
    capture_frame.columnconfigure(0, weight=1)

    entry_capture = ttk.Entry(capture_frame, textvariable=capture_dir_var)
    entry_capture.grid(row=0, column=0, sticky="ew")
    attach_paste_menu(entry_capture)

    def choose_capture_dir():
        path = filedialog.askdirectory(initialdir=capture_dir_var.get() or os.getcwd(), title="캡처 저장 폴더 선택")
        if path:
            capture_dir_var.set(path)

    btn_capture = ttk.Button(capture_frame, text="폴더 선택", style="Secondary.TButton", command=choose_capture_dir)
    btn_capture.grid(row=0, column=1, padx=(8, 0))

    ttk.Label(event_frame, text="사용자 간 대기시간(초)", style="Subheader.TLabel").grid(row=3, column=0, sticky="w", pady=(10, 0))
    delay_var = tk.StringVar(value=str(DEFAULT_USER_DELAY))
    entry_delay = ttk.Entry(event_frame, textvariable=delay_var)
    entry_delay.grid(row=3, column=1, sticky="w", pady=(10, 0))
    attach_paste_menu(entry_delay)

    login_frame = ttk.Frame(main, style="Main.TFrame")
    login_frame.grid(row=2, column=1, sticky="nsew")
    login_frame.columnconfigure(1, weight=1)

    # 수동 로그인 안내 메시지
    login_info = ttk.Label(
        login_frame,
        text="※ 검사 시작 후 브라우저 창에서\n직접 트위터에 로그인해주세요.",
        style="Subheader.TLabel",
        justify="left"
    )
    login_info.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

    headless_var = tk.BooleanVar(value=False)
    chk_headless = ttk.Checkbutton(login_frame, text="헤드리스 실행 (창 숨김) - 수동 로그인시 비활성화 권장", variable=headless_var)
    chk_headless.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    action_frame = ttk.Frame(main, style="Main.TFrame")
    action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 12))
    action_frame.columnconfigure(0, weight=1)
    action_frame.columnconfigure(1, weight=0)
    action_frame.columnconfigure(2, weight=0)

    def open_advanced_settings():
        dialog = tk.Toplevel(root)
        dialog.title("고급 설정")
        dialog.configure(bg=bg_color)
        dialog.resizable(False, False)
        dialog.transient(root)

        frame_inner = ttk.Frame(dialog, padding=16)
        frame_inner.pack(fill="both", expand=True)

        ttk.Label(frame_inner, text="트윗 Article XPath 템플릿", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        entry_article = ttk.Entry(frame_inner, width=80)
        entry_article.grid(row=1, column=0, sticky="ew", pady=(2, 12))
        entry_article.insert(0, SELECTOR_CONFIG.get(
            "article_xpath_template",
            "//a[contains(@href,'/status/{tweet_id}')]/ancestor::article",
        ))

        info_lbl = ttk.Label(
            frame_inner,
            text="{tweet_id} 부분은 자동으로 이벤트 트윗 ID로 치환됩니다.",
            style="Subheader.TLabel",
        )
        info_lbl.grid(row=2, column=0, sticky="w", pady=(0, 12))

        btn_row = ttk.Frame(frame_inner)
        btn_row.grid(row=3, column=0, sticky="ew")
        btn_row.columnconfigure(0, weight=1)

        def refresh_fields():
            entry_article.delete(0, tk.END)
            entry_article.insert(0, SELECTOR_CONFIG.get(
                "article_xpath_template",
                "//a[contains(@href,'/status/{tweet_id}')]/ancestor::article",
            ))

        def handle_save():
            new_article = entry_article.get().strip()

            if not new_article:
                messagebox.showerror("입력 오류", "XPath 필드를 올바르게 입력해 주세요.")
                return

            global SELECTOR_CONFIG
            SELECTOR_CONFIG = {
                "next_button_xpaths": SELECTOR_CONFIG.get("next_button_xpaths", []),
                "login_button_xpaths": SELECTOR_CONFIG.get("login_button_xpaths", []),
                "article_xpath_template": new_article,
            }
            save_user_config(SELECTOR_CONFIG)
            messagebox.showinfo("설정 저장", "변경 사항이 저장되었습니다.")

        def handle_reset():
            if not messagebox.askyesno("설정 초기화", "XPath 설정을 기본값으로 되돌릴까요?"):
                return
            reset_user_config()
            global SELECTOR_CONFIG
            SELECTOR_CONFIG = load_selector_config()
            refresh_fields()
            messagebox.showinfo("설정 초기화", "기본 설정으로 복원되었습니다.")

        ttk.Button(btn_row, text="저장", style="Primary.TButton", command=handle_save).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btn_row, text="기본값 복원", style="Secondary.TButton", command=handle_reset).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(btn_row, text="닫기", style="Secondary.TButton", command=dialog.destroy).grid(row=0, column=3)

        dialog.grab_set()

    btn_settings = ttk.Button(action_frame, text="고급 설정", style="Secondary.TButton", command=open_advanced_settings)
    btn_settings.grid(row=0, column=0, sticky="w")

    btn_run = ttk.Button(action_frame, text="검사 시작", style="Primary.TButton")
    btn_run.grid(row=0, column=1, padx=(0, 8))

    btn_save = ttk.Button(action_frame, text="CSV로 저장", style="Secondary.TButton", state="disabled")
    btn_save.grid(row=0, column=2)

    separator = ttk.Separator(main)
    separator.grid(row=4, column=0, columnspan=2, sticky="ew")

    tree_frame = ttk.Frame(main, style="Main.TFrame")
    tree_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
    tree_frame.columnconfigure(0, weight=1)
    tree_frame.rowconfigure(0, weight=1)

    cols = ("username", "retweeted", "capture_path")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        height=12,
    )
    tree.heading("username", text="사용자")
    tree.heading("retweeted", text="발견 여부")
    tree.heading("capture_path", text="캡처 파일 경로")
    tree.column("username", width=220)
    tree.column("retweeted", width=90, anchor="center")
    tree.column("capture_path", width=420)

    scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scroll_y.grid(row=0, column=1, sticky="ns")
    scroll_x.grid(row=1, column=0, sticky="ew")

    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(main, variable=progress_var, maximum=1, mode="determinate")
    progress_bar.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 4))

    status_var = tk.StringVar(value="대기 중")
    status_bar = ttk.Label(main, textvariable=status_var, style="Subheader.TLabel", anchor="w")
    status_bar.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 0))

    def save_csv_action():
        if not tree.get_children():
            messagebox.showinfo("정보", "저장할 결과가 없습니다.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "retweeted", "capture_path"])
            for r in tree.get_children():
                vals = tree.item(r, "values")
                writer.writerow(vals)
        messagebox.showinfo("저장완료", f"저장됨: {path}")

    btn_save.config(command=save_csv_action)

    def on_run_click():
        mode = mode_var.get()
        event_input = entry_tweet.get().strip()
        users_raw = text_users.get("1.0", tk.END).strip()
        headless = headless_var.get()
        capture_dir = capture_dir_var.get().strip() or DEFAULT_CAPTURE_DIR
        delay_input = delay_var.get().strip() or str(DEFAULT_USER_DELAY)

        if not event_input or not users_raw:
            if mode == "twitter":
                messagebox.showerror("입력 오류", "트윗 ID와 사용자 목록을 입력해 주세요.")
            else:
                messagebox.showerror("입력 오류", "게시글 URL과 사용자 목록을 입력해 주세요.")
            return

        if not os.path.isdir(capture_dir):
            try:
                os.makedirs(capture_dir, exist_ok=True)
            except Exception:
                messagebox.showerror("폴더 오류", "캡처 저장 폴더를 생성할 수 없습니다.")
                return

        try:
            per_user_delay = float(delay_input)
            if per_user_delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("입력 오류", "사용자 간 대기시간은 0 이상의 숫자로 입력해 주세요.")
            return

        usernames = [x.strip() for x in users_raw.split(",") if x.strip()]
        if not usernames:
            messagebox.showerror("입력 오류", "사용자 목록에 최소 한 명 이상 입력해 주세요.")
            return

        progress_var.set(0)
        progress_bar.configure(maximum=len(usernames))
        status_var.set(f"검사 중... (총 {len(usernames)}명)")

        if mode == "twitter":
            t = threading.Thread(
                target=run_check_thread,
                args=(
                    event_input,  # tweet_id
                    usernames,
                    None,  # login_id (사용 안함)
                    None,  # login_pw (사용 안함)
                    headless,
                    tree,
                    btn_run,
                    btn_save,
                    capture_dir,
                    per_user_delay,
                    progress_bar,
                    progress_var,
                    status_var,
                ),
                daemon=True,
            )
        else:  # instagram
            t = threading.Thread(
                target=run_instagram_check_thread,
                args=(
                    event_input,  # post_url
                    usernames,
                    headless,
                    tree,
                    btn_run,
                    btn_save,
                    capture_dir,
                    per_user_delay,
                    progress_bar,
                    progress_var,
                    status_var,
                ),
                daemon=True,
            )
        t.start()

    btn_run.config(command=on_run_click)

    root.mainloop()

if __name__ == "__main__":
    build_gui()
