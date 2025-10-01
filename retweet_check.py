# twitter_rt_gui_with_login.py
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
    NoSuchElementException, TimeoutException, WebDriverException
)

from selenium.webdriver.common.keys import Keys

from PIL import Image, ImageTk

# -----------------------
# 설정값 (필요 시 조정)
# -----------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SCROLL_PAUSE = 2.0
# 사용자 간 기본 대기 시간(초)
DEFAULT_USER_DELAY = 4.0
# 타임라인 로딩 대기 범위(초)
TIMELINE_WAIT_RANGE = (3.0, 6.0)
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
    # 사용자 프로필을 재사용하고 싶다면 user_data_dir 인자에 경로를 넣어 재로그인 방지 가능
    if user_data_dir:
        opts.add_argument(f"--user-data-dir={user_data_dir}")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    return driver

# -----------------------
# 로그인 처리 (일반적 흐름: username -> next -> password)
# UI 변경될 수 있으니 요소 탐색은 신중히)
# -----------------------
def login_twitter(driver, login_id, login_pw, wait_sec=10):
    """
    로그인 시도:
    - twitter.com/login 페이지 열고 username 입력 -> next 버튼 -> password 입력 -> 로그인
    - 로그인 완료 여부는 URL 변화를 통해 확인
    반환: True/False
    """
    driver.get("https://twitter.com/i/flow/login")

    try:
        # 1) 아이디 입력 필드 대기 후 입력
        el_id = WebDriverWait(driver, wait_sec).until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        el_id.clear()
        el_id.send_keys(login_id)

        next_button_xpaths = SELECTOR_CONFIG.get("next_button_xpaths") or [
            "//div[@role='button' and .//span[normalize-space(text())='Next' or normalize-space(text())='다음']]",
            "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]",
        ]

        def click_next_button():
            last_error = None
            for xpath in next_button_xpaths:
                try:
                    next_btn = WebDriverWait(driver, wait_sec).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    next_btn.click()
                    time.sleep(0.2)
                    return
                except TimeoutException as exc:
                    last_error = exc
            if last_error:
                raise last_error

        # 2) Next 버튼 클릭 (대기 후 실행)
        try:
            click_next_button()
        except TimeoutException:
            # 일부 계정은 Next 단계 없이 바로 password 입력으로 넘어감
            pass

        # 3) 비밀번호 입력 필드 대기 후 입력(추가 확인 단계 대응)
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
            raise TimeoutException("Password input not found after additional prompts")
        pw_input.clear()
        pw_input.send_keys(login_pw)

        # 4) 로그인 버튼 클릭
        login_button_xpaths = SELECTOR_CONFIG.get("login_button_xpaths") or [
            "//div[@role='button' and .//span[normalize-space(text())='Log in' or normalize-space(text())='로그인']]",
            "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button",
        ]

        try:
            last_error = None
            for xpath in login_button_xpaths:
                try:
                    login_btn = WebDriverWait(driver, wait_sec).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    login_btn.click()
                    break
                except TimeoutException as exc:
                    last_error = exc
            else:
                if last_error:
                    raise last_error
        except TimeoutException:
            # fallback: 엔터로 제출
            pw_input.submit()

        # 5) 로그인 성공 확인 (홈 URL/홈 UI 신호 감지)
        home_fragments = ("twitter.com/home", "x.com/home", "twitter.com/?", "x.com/?")
        nav_locators = [
            (By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]'),
            (By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'),
        ]

        conditions = [EC.url_contains(fragment) for fragment in home_fragments]
        conditions.extend(EC.presence_of_element_located(locator) for locator in nav_locators)

        def has_home_signal(drv):
            if any(fragment in drv.current_url for fragment in home_fragments):
                return True
            for locator in nav_locators:
                try:
                    if drv.find_element(*locator).is_displayed():
                        return True
                except NoSuchElementException:
                    continue
            return False

        try:
            WebDriverWait(driver, wait_sec * 2).until(EC.any_of(*conditions))
        except AttributeError:
            WebDriverWait(driver, wait_sec * 2).until(has_home_signal)
        return True

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
# 백그라운드 스레드로 검사 진행 (GUI 블로킹 방지)
# -----------------------
def run_check_thread(tweet_id, usernames, login_id, login_pw, headless, tree, btn_run, btn_save, capture_dir, per_user_delay, progress_bar, progress_var, status_var=None):
    btn_run.config(state="disabled")
    btn_save.config(state="disabled")
    # 드라이버 생성 및 로그인
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
        login_ok = login_twitter(driver, login_id, login_pw)
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
        messagebox.showerror("로그인 실패", "로그인에 실패했습니다. 아이디/비밀번호를 확인하거나 개발자에게 문의해주세요.")
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

# -----------------------
# GUI 구성
# -----------------------
def build_gui():
    root = tk.Tk()
    root.title("트위터 RT 검증 도구")

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

    header = ttk.Label(main, text="트위터 RT 검증 도구", style="Header.TLabel")
    header.grid(row=0, column=0, columnspan=2, sticky="w")

    subheader = ttk.Label(
        main,
        text="이벤트 트윗 리트윗 여부를 빠르게 확인하고 캡처까지 저장하세요.",
        style="Subheader.TLabel",
    )
    subheader.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))

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

    ttk.Label(event_frame, text="이벤트 트윗 ID", style="Subheader.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
    entry_tweet = ttk.Entry(event_frame)
    entry_tweet.grid(row=0, column=1, sticky="ew", pady=(0, 6))
    attach_paste_menu(entry_tweet)

    ttk.Label(event_frame, text="당첨자 목록 (쉼표 구분)", style="Subheader.TLabel").grid(row=1, column=0, sticky="nw")
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

    ttk.Label(login_frame, text="트위터 로그인 ID", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
    entry_id = ttk.Entry(login_frame)
    entry_id.grid(row=0, column=1, sticky="ew", pady=(0, 6))
    attach_paste_menu(entry_id)

    ttk.Label(login_frame, text="트위터 비밀번호", style="Subheader.TLabel").grid(row=1, column=0, sticky="w")
    entry_pw = ttk.Entry(login_frame, show="*")
    entry_pw.grid(row=1, column=1, sticky="ew", pady=(0, 6))
    attach_paste_menu(entry_pw)

    headless_var = tk.BooleanVar(value=True)
    chk_headless = ttk.Checkbutton(login_frame, text="헤드리스 실행 (창 숨김)", variable=headless_var)
    chk_headless.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

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

        ttk.Label(frame_inner, text="Next 버튼 XPath (줄마다 1개)", style="Subheader.TLabel").grid(row=0, column=0, sticky="w")
        txt_next = tk.Text(frame_inner, width=80, height=4, relief="flat", borderwidth=1)
        txt_next.grid(row=1, column=0, sticky="ew", pady=(2, 12))
        txt_next.insert("1.0", "\n".join(SELECTOR_CONFIG.get("next_button_xpaths", [])))

        ttk.Label(frame_inner, text="로그인 버튼 XPath (줄마다 1개)", style="Subheader.TLabel").grid(row=2, column=0, sticky="w")
        txt_login = tk.Text(frame_inner, width=80, height=4, relief="flat", borderwidth=1)
        txt_login.grid(row=3, column=0, sticky="ew", pady=(2, 12))
        txt_login.insert("1.0", "\n".join(SELECTOR_CONFIG.get("login_button_xpaths", [])))

        ttk.Label(frame_inner, text="트윗 Article XPath 템플릿", style="Subheader.TLabel").grid(row=4, column=0, sticky="w")
        entry_article = ttk.Entry(frame_inner, width=80)
        entry_article.grid(row=5, column=0, sticky="ew", pady=(2, 12))
        entry_article.insert(0, SELECTOR_CONFIG.get(
            "article_xpath_template",
            "//a[contains(@href,'/status/{tweet_id}')]/ancestor::article",
        ))

        info_lbl = ttk.Label(
            frame_inner,
            text="{tweet_id} 부분은 자동으로 이벤트 트윗 ID로 치환됩니다.",
            style="Subheader.TLabel",
        )
        info_lbl.grid(row=6, column=0, sticky="w", pady=(0, 12))

        btn_row = ttk.Frame(frame_inner)
        btn_row.grid(row=7, column=0, sticky="ew")
        btn_row.columnconfigure(0, weight=1)

        def refresh_fields():
            txt_next.delete("1.0", tk.END)
            txt_login.delete("1.0", tk.END)
            entry_article.delete(0, tk.END)
            txt_next.insert("1.0", "\n".join(SELECTOR_CONFIG.get("next_button_xpaths", [])))
            txt_login.insert("1.0", "\n".join(SELECTOR_CONFIG.get("login_button_xpaths", [])))
            entry_article.insert(0, SELECTOR_CONFIG.get(
                "article_xpath_template",
                "//a[contains(@href,'/status/{tweet_id}')]/ancestor::article",
            ))

        def handle_save():
            new_next = [line.strip() for line in txt_next.get("1.0", tk.END).splitlines() if line.strip()]
            new_login = [line.strip() for line in txt_login.get("1.0", tk.END).splitlines() if line.strip()]
            new_article = entry_article.get().strip()

            if not new_next or not new_login or not new_article:
                messagebox.showerror("입력 오류", "모든 XPath 필드를 올바르게 입력해 주세요.")
                return

            global SELECTOR_CONFIG
            SELECTOR_CONFIG = {
                "next_button_xpaths": new_next,
                "login_button_xpaths": new_login,
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
    tree.heading("retweeted", text="RT 여부")
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
        tweet_id = entry_tweet.get().strip()
        users_raw = text_users.get("1.0", tk.END).strip()
        login_id = entry_id.get().strip()
        login_pw = entry_pw.get().strip()
        headless = headless_var.get()
        capture_dir = capture_dir_var.get().strip() or DEFAULT_CAPTURE_DIR
        delay_input = delay_var.get().strip() or str(DEFAULT_USER_DELAY)

        if not tweet_id or not users_raw or not login_id or not login_pw:
            messagebox.showerror("입력 오류", "모든 필수 항목(트윗 ID, 사용자 목록, 로그인 정보)을 입력해 주세요.")
            return

        if not os.path.isdir(capture_dir):
            try:
                os.makedirs(capture_dir, exist_ok=True)
            except Exception:
                messagebox.showerror("폴더 오류", "캡처 저장 폴더를 생성할 수 없습니다. 다른 경로를 선택하거나 개발자에게 문의해주세요.")
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
            messagebox.showerror("입력 오류", "당첨자 목록에 최소 한 명 이상 입력해 주세요.")
            return

        progress_var.set(0)
        progress_bar.configure(maximum=len(usernames))
        status_var.set(f"검사 중... (총 {len(usernames)}명)")

        t = threading.Thread(
            target=run_check_thread,
            args=(
                tweet_id,
                usernames,
                login_id,
                login_pw,
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
