"""
Instagram 댓글 수집기
사용법: python instagram/comment_extractor.py
"""

import asyncio
import os
import sys
import time
import csv
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
import threading

# 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

# DOM 셀렉터 후보
COMMENT_ITEM_SELECTORS = [
    # 게시글 본문
    "article ul li",
    "article div ul li",
    # 피드에서 모달로 열렸을 때
    "div[role='dialog'] article ul li",
    "div[role='dialog'] ul li",
    # 혹시 모를 기타 케이스
    "section ul li",
    "main ul li",
]

LOAD_MORE_BUTTON_SELECTORS = [
    # 전체 댓글 더보기
    'button:has-text("댓글 더 보기")',
    'button:has-text("View all comments")',
    'button:has-text("View more comments")',
    'button:has-text("모두 보기")',
    'button:has-text("Load more comments")',
    'div[role="button"]:has-text("댓글 더 보기")',
    'span:has-text("댓글 더 보기")',
    # 숨김 댓글 / 추가 댓글
    'button:has-text("댓글")',
]

REPLY_EXPANDER_SELECTORS = [
    'button:has-text("답글 보기")',
    'button:has-text("답글")',
    'button:has-text("View replies")',
    'button:has-text("Hide replies")',
    'button:has-text("View all replies")',
]

# -----------------------
# 필수 라이브러리 확인
# -----------------------
def check_dependencies():
    """필수 라이브러리 설치 여부 확인"""
    print(f"\n{'═' * 70}")
    print(f"  📦 필수 라이브러리 확인 중...")
    print(f"{'═' * 70}\n")

    required = {
        'playwright': 'playwright',
        'openpyxl': 'openpyxl',
        'Pillow': 'PIL',
    }

    missing = []
    installed = []

    for display_name, import_name in required.items():
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', '알 수 없음')
            installed.append(f"  ✅ {display_name:20s} {version}")
        except ImportError:
            missing.append(display_name)

    for msg in installed:
        print(msg)

    if missing:
        print(f"\n{'─' * 70}")
        print(f"  ❌ 다음 라이브러리가 설치되지 않았습니다:")
        for lib in missing:
            print(f"      • {lib}")
        print(f"\n  설치 명령어:")
        print(f"      pip install {' '.join(missing)}")
        print(f"{'─' * 70}\n")
        sys.exit(1)

    print(f"\n{'─' * 70}")
    print(f"  ✅ 모든 필수 라이브러리가 설치되어 있습니다")
    print(f"{'─' * 70}\n")


# -----------------------
# 쿠키 관리
# -----------------------
def get_cookies_from_user():
    """사용자로부터 쿠키 값을 직접 입력받기"""
    print(f"\n{'═' * 70}")
    print(f"  🔑 Instagram 쿠키 입력")
    print(f"{'═' * 70}")
    print(f"\n  📋 Instagram 쿠키 가져오기:")
    print(f"      1. Chrome에서 instagram.com 로그인")
    print(f"      2. F12 > Application > Cookies > https://www.instagram.com")
    print(f"      3. 다음 쿠키 값을 복사:")
    print(f"         • sessionid (필수)")
    print(f"         • csrftoken (필수)")
    print(f"         • ds_user_id (선택)")
    print(f"\n{'─' * 70}\n")

    sessionid = input("  sessionid: ").strip()
    if not sessionid:
        return None

    csrftoken = input("  csrftoken: ").strip()
    if not csrftoken:
        return None

    ds_user_id = input("  ds_user_id (엔터 = 건너뛰기): ").strip()

    cookies = {
        "SESSIONID": sessionid,
        "CSRFTOKEN": csrftoken,
    }

    if ds_user_id:
        cookies["DS_USER_ID"] = ds_user_id

    return cookies


def load_cookies_from_env():
    """Load cookies from .env file"""
    if not os.path.exists(ENV_FILE):
        print(f"  ❌ .env 파일을 찾을 수 없습니다: {ENV_FILE}")
        return None

    cookies = {}
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key.startswith('INSTAGRAM_'):
                    cookie_name = key.replace('INSTAGRAM_', '')
                    cookies[cookie_name] = value

    if not cookies.get('SESSIONID') or not cookies.get('CSRFTOKEN'):
        print(f"  ❌ .env 파일에 필수 쿠키가 없습니다 (INSTAGRAM_SESSIONID, INSTAGRAM_CSRFTOKEN)")
        return None

    print(f"  ✅ .env 파일에서 {len(cookies)}개 쿠키 로드 완료")
    return cookies


def save_to_env_file(cookies):
    """Save cookies to .env file"""
    print(f"\n{'─' * 70}")
    print(f"  💾 쿠키를 .env 파일로 저장 중...")

    env_content = "# Instagram 인증 쿠키\n"
    for key, value in cookies.items():
        env_content += f"INSTAGRAM_{key}={value}\n"

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print(f"  ✅ .env 파일 저장 완료: {ENV_FILE}")
    print(f"{'─' * 70}\n")


async def load_cookies_to_context(context, cookies):
    """Playwright context에 쿠키 로드"""
    try:
        print(f"\n{'─' * 70}")
        print(f"  🔑 쿠키 로드 중...")

        cookie_list = []

        if cookies.get("SESSIONID"):
            cookie_list.append({
                "name": "sessionid",
                "value": cookies["SESSIONID"],
                "domain": ".instagram.com",
                "path": "/",
            })

        if cookies.get("CSRFTOKEN"):
            cookie_list.append({
                "name": "csrftoken",
                "value": cookies["CSRFTOKEN"],
                "domain": ".instagram.com",
                "path": "/",
            })

        if cookies.get("DS_USER_ID"):
            cookie_list.append({
                "name": "ds_user_id",
                "value": cookies["DS_USER_ID"],
                "domain": ".instagram.com",
                "path": "/",
            })

        await context.add_cookies(cookie_list)
        print(f"  ✅ {len(cookie_list)}개 쿠키 로드 완료")
        print(f"{'─' * 70}\n")
        return True

    except Exception as e:
        print(f"  ❌ 쿠키 로드 실패: {e}")
        print(f"{'─' * 70}\n")
        return False


# -----------------------
# DOM 구조 분석 (디버깅용)
# -----------------------
async def analyze_dom_structure(page):
    """실제 Instagram DOM 구조를 분석하여 출력"""
    print(f"\n{'═' * 70}")
    print(f"  🔍 DOM 구조 분석 중...")
    print(f"{'═' * 70}\n")

    # 댓글 컨테이너 찾기
    selectors_to_test = [
        'ul[role="list"]',  # 댓글 리스트
        'div[role="dialog"]',  # 모달
        'article',  # 게시글
        'ul',  # 일반 리스트
        'li',  # 리스트 아이템
    ]

    for selector in selectors_to_test:
        count = await page.locator(selector).count()
        print(f"  {selector:30s} : {count}개 발견")

    # 첫 번째 댓글 구조 분석
    print(f"\n{'─' * 70}")
    print(f"  📝 댓글 요소 상세 분석:")
    print(f"{'─' * 70}\n")

    # 다양한 패턴으로 댓글 찾기 시도
    comment_patterns = [
        'ul li',
        'div[role="button"]',
        'span:has-text("좋아요")',
        'time[datetime]',
        'h2 + div + div ul li',  # 댓글 리스트 아이템
        'span[dir="auto"]',  # 텍스트 span
    ]

    for pattern in comment_patterns:
        count = await page.locator(pattern).count()
        if count > 0:
            print(f"  ✓ {pattern:40s} : {count}개")
            if count <= 5:  # 5개 이하면 텍스트도 출력
                for i in range(min(count, 3)):
                    try:
                        text = await page.locator(pattern).nth(i).inner_text()
                        print(f"      [{i}] {text[:100]}")
                    except:
                        pass

    # 페이지 HTML 일부 저장 (디버깅용)
    try:
        html_content = await page.content()
        debug_file = "instagram_debug.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n  💾 전체 HTML 저장: {debug_file}")
    except:
        pass

    print(f"\n{'═' * 70}\n")


# -----------------------
# 헬퍼 유틸
# -----------------------
def normalize_text(value):
    """불필요한 공백 제거"""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def build_comment_key(comment):
    """중복 방지를 위한 고유 키 생성"""
    username = normalize_text(comment.get("username", "")).lower()
    text = normalize_text(comment.get("text", ""))
    timestamp = comment.get("timestamp", "")
    return f"{username}|{text}|{timestamp}"


async def click_first_available(page, selectors):
    """셀렉터 목록 중 클릭 가능한 첫 요소 클릭"""
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = await locator.count()
            if count == 0:
                continue
            target = locator.nth(0)
            try:
                await target.scroll_into_view_if_needed()
            except:
                pass
            await target.click(timeout=3000)
            return True
        except Exception:
            continue
    return False


async def click_load_more_comments(page):
    """댓글/답글 더보기 버튼 클릭"""
    clicked = await click_first_available(page, LOAD_MORE_BUTTON_SELECTORS)
    reply_clicked = await click_first_available(page, REPLY_EXPANDER_SELECTORS)
    return clicked or reply_clicked


async def wait_for_comment_section(page, timeout=20000):
    """댓글 섹션이 렌더링될 때까지 대기"""
    for selector in COMMENT_ITEM_SELECTORS:
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def collect_visible_comments(page, seen_ids):
    """
    time[datetime]을 기준으로 컨테이너를 찾고,
    본문은 span[dir="auto"] 내부 전체 텍스트를 추출한다.
    """

    raw_comments = await page.evaluate(
        """
        () => {
            const relativeTimePattern = '\\\\d+\\\\s*(분|시간|일|주|개월|년)';
            const relativeTimeRegex = new RegExp(`^${relativeTimePattern}$`);
            const relativeTimeInline = new RegExp(relativeTimePattern, 'g');
            const results = [];

    const commentLinks = document.querySelectorAll(
        "a[href*='/p/'][href*='/c/']"
    );
    const processedRoots = new WeakSet();

    commentLinks.forEach((link) => {
        const timeEl = link.querySelector('time[datetime]');
        if (!timeEl) {
            return;
        }
        const timestamp = timeEl.getAttribute('datetime') || '';
        if (!timestamp) {
            return;
        }

        let container = link.parentElement;
        let chosen = null;
        for (let i = 0; i < 25 && container; i += 1) {
            const hasUser = container.querySelector('a._a6hd span, a._a6hd');
            const hasBody = container.querySelector('span[dir="auto"]');
            const hasTime = container.querySelector('time[datetime]');
            const linkCount = container.querySelectorAll(
                "a[href*='/p/'][href*='/c/']"
            ).length;
            if (hasUser && hasBody && hasTime && linkCount === 1) {
                chosen = container;
            }
            if (linkCount > 1) {
                break;
            }
            container = container.parentElement;
        }

        container = chosen || container;

        if (!container || processedRoots.has(container)) {
            return;
        }
        processedRoots.add(container);

        // 사용자명
        const usernameNode =
            container.querySelector('a._a6hd span') ||
            container.querySelector('a._a6hd') ||
            container.querySelector('a[role="link"][tabindex="0"] span') ||
            container.querySelector('a[role="link"][tabindex="0"]');
        const username = usernameNode ? usernameNode.textContent.trim() : '';

                // 댓글 본문
                const metaPatterns = [
                    /^수정됨$/,
                    /^답글.*모두 보기$/,
                    /^좋아요\s*\d*/,
                    /^좋아요$/,
                    /^답글 달기$/,
                ];

                const textPieces = [];
                container.querySelectorAll('span[dir="auto"]').forEach((span) => {
                    if (span.closest('button')) {
                        return;
                    }
                    const raw = (span.textContent || '').trim();
                    if (!raw) {
                        return;
                    }
                    if (username && raw === username) {
                        return;
                    }
                    if (relativeTimeRegex.test(raw)) {
                        return;
                    }
                    if (metaPatterns.some((regex) => regex.test(raw))) {
                        return;
                    }
                    if (/^(좋아요|답글|Reply|View|좋아요를 누른 사람이)/.test(raw)) {
                        return;
                    }
                    textPieces.push(raw);
                });
                let text = textPieces.join(' ').replace(/\\s+/g, ' ').trim();

                if (!text) {
                    let fallback = (container.innerText || '').trim();
                    if (username && fallback.startsWith(username)) {
                        fallback = fallback.slice(username.length).trim();
                    }
                    fallback = fallback
                        .replace(relativeTimeInline, '')
                        .replace(/좋아요\\s*\\d*/gi, '')
                        .replace(/답글( 달기)?/gi, '')
                        .replace(/•/g, '')
                        .replace(/\\s+/g, ' ')
                        .trim();
                    if (!metaPatterns.some((regex) => regex.test(fallback))) {
                        text = fallback;
                    }
                }

                // 좋아요/답글 수
                let likes = '';
                let replies = '';
                container.querySelectorAll('button').forEach((btn) => {
                    const label = (btn.textContent || '').trim();
                    if (!label) {
                        return;
                    }
                    const numbers = label.match(/\\d+/);
                    if (/좋아요|likes?/i.test(label) && numbers && !likes) {
                        likes = numbers[0];
                    } else if (/답글|repl/i.test(label) && numbers && !replies) {
                        replies = numbers[0];
                    }
                });

                if (!username && !text) {
                    return;
                }

                results.push({
                    username,
                    text,
                    timestamp,
                    likes,
                    replies,
                });
            });

            return results;
        }
        """
    )

    harvested = []
    for comment in raw_comments or []:
        comment["username"] = normalize_text(comment.get("username", ""))
        comment["text"] = normalize_text(comment.get("text", ""))
        comment["timestamp"] = comment.get("timestamp", "")
        comment["likes"] = (comment.get("likes") or "0").strip() or "0"
        comment["replies"] = (comment.get("replies") or "0").strip() or "0"

        comment_id = build_comment_key(comment)
        if not comment_id or comment_id in seen_ids:
            continue

        seen_ids.add(comment_id)
        harvested.append(comment)

    return harvested


# -----------------------
# 댓글 파싱
# -----------------------
async def parse_comment(li_element):
    """개별 댓글 요소에서 데이터 추출"""
    try:
        comment_data = {
            "username": "",
            "text": "",
            "timestamp": "",
            "likes": "0",
            "replies": "0",
        }

        # 사용자명 (링크 텍스트)
        try:
            username_link = li_element.locator('a[href^="/"]').first
            comment_data["username"] = await username_link.inner_text()
        except:
            pass

        # 댓글 내용 (span 태그)
        try:
            # 여러 패턴 시도
            text_patterns = [
                'span[dir="auto"]',
                'span',
                'div span',
            ]
            for pattern in text_patterns:
                text_elements = li_element.locator(pattern)
                count = await text_elements.count()
                if count > 0:
                    # 사용자명이 아닌 span 찾기
                    for i in range(count):
                        text = await text_elements.nth(i).inner_text()
                        if text and text != comment_data["username"] and len(text) > 2:
                            comment_data["text"] = text
                            break
                if comment_data["text"]:
                    break
        except:
            pass

        # 타임스탬프
        try:
            time_element = li_element.locator('time[datetime]').first
            comment_data["timestamp"] = await time_element.get_attribute('datetime')
        except:
            # datetime 속성이 없으면 텍스트 사용
            try:
                time_element = li_element.locator('time').first
                comment_data["timestamp"] = await time_element.inner_text()
            except:
                pass

        # 좋아요 수 (버튼 텍스트에서 추출)
        try:
            like_button = li_element.locator('button:has-text("좋아요"), button:has-text("likes")').first
            like_text = await like_button.inner_text()
            numbers = re.findall(r'\d+', like_text)
            if numbers:
                comment_data["likes"] = numbers[0]
        except:
            pass

        # 대댓글 수 (답글 보기 버튼)
        try:
            reply_button = li_element.locator('button:has-text("답글"), button:has-text("repl")').first
            reply_text = await reply_button.inner_text()
            numbers = re.findall(r'\d+', reply_text)
            if numbers:
                comment_data["replies"] = numbers[0]
        except:
            pass

        # 최소한 사용자명과 텍스트가 있어야 유효한 댓글
        if comment_data["username"] or comment_data["text"]:
            return comment_data
        return None

    except Exception as e:
        return None


# -----------------------
# 댓글 추출 (자동 스크롤)
# -----------------------
async def extract_comments_auto(page, post_url, max_scrolls=100):
    """자동 스크롤 모드로 댓글 수집"""
    print(f"\n{'═' * 70}")
    print(f"  🔄 댓글 자동 수집 시작")
    print(f"{'═' * 70}")
    print(f"  📄 게시글: {post_url}")
    print(f"  🔢 최대 스크롤: {max_scrolls}회")
    print(f"{'═' * 70}\n")

    # 게시글 로드
    await page.goto(post_url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(3000)

    # DOM 구조 분석 (디버깅)
    await analyze_dom_structure(page)

    if not await wait_for_comment_section(page):
        print("  ⚠️  댓글 섹션을 찾지 못했습니다. 로그인 여부를 확인해주세요.")
        return []

    comments = []
    seen_ids = set()
    scrolls = 0
    no_change_count = 0

    print(f"  {'─' * 66}")
    print(f"  🔄 스크롤 및 수집 시작")
    print(f"  {'─' * 66}\n")

    for scroll_num in range(1, max_scrolls + 1):
        scrolls = scroll_num

        newly_found = await collect_visible_comments(page, seen_ids)
        if newly_found:
            comments.extend(newly_found)
            no_change_count = 0
            for comment in newly_found[:3]:
                preview = (comment["text"][:60] + "...") if len(comment["text"]) > 60 else comment["text"]
                print(f"  💬 @{comment['username'] or 'unknown'} | {preview}")
        else:
            no_change_count += 1

        print(f"\n  📊 스크롤 #{scroll_num:02d} / {max_scrolls}  |  누적 {len(comments)}개 수집  |  최근 변화 {'O' if newly_found else 'X'}")

        # 더보기/답글 펼치기
        clicked = await click_load_more_comments(page)

        if not clicked:
            # 자연스러운 스크롤
            await page.mouse.wheel(0, random.randint(600, 1200))
            await page.wait_for_timeout(random.uniform(0.8, 1.4) * 1000)
        else:
            await page.wait_for_timeout(random.uniform(1.0, 1.6) * 1000)

        if no_change_count >= 5:
            print(f"\n  🏁 더 이상 새로운 데이터가 감지되지 않아 자동 종료합니다")
            break

    # 마지막으로 한 번 더 수집
    final_batch = await collect_visible_comments(page, seen_ids)
    if final_batch:
        comments.extend(final_batch)

    print(f"\n{'═' * 70}")
    print(f"  ✅ 수집 완료!")
    print(f"  {'─' * 66}")
    print(f"      📝 총 수집 댓글: {len(comments)}개")
    print(f"      🔄 총 스크롤: {scrolls}회")
    print(f"{'═' * 70}\n")

    return comments


# -----------------------
# 댓글 추출 (수동 스크롤)
# -----------------------
async def extract_comments_manual(page, post_url):
    """수동 스크롤 모드 - 사용자가 직접 스크롤"""
    print(f"\n{'═' * 70}")
    print(f"  👆 댓글 수동 수집 모드")
    print(f"{'═' * 70}")
    print(f"  📄 게시글: {post_url}")
    print(f"  💡 브라우저를 직접 스크롤하면 실시간으로 댓글을 수집합니다")
    print(f"  ⏹️  엔터 키를 누르면 수집을 종료합니다")
    print(f"{'═' * 70}\n")

    # 게시글 로드
    await page.goto(post_url, wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(3000)

    # DOM 구조 분석
    await analyze_dom_structure(page)
    if not await wait_for_comment_section(page):
        print("  ⚠️  댓글 섹션을 찾지 못했습니다. 수동 모드로 계속 대기합니다.")
    else:
        # 기본 댓글/답글 더보기 버튼 한 번 클릭 시도
        await click_load_more_comments(page)

    # 엔터 키 대기 스레드
    stop_flag = [False]

    def wait_for_enter():
        print("  ⏸️  엔터 키를 누르면 수집을 종료합니다...\n")
        input()
        stop_flag[0] = True
        print("\n  🛑 수집 종료 요청됨")

    input_thread = threading.Thread(target=wait_for_enter, daemon=True)
    input_thread.start()

    comments = []
    seen_ids = set()

    print(f"  {'─' * 66}")
    print(f"  👀 실시간 수집 중... (0.5초마다 폴링)")
    print(f"  {'─' * 66}\n")

    while not stop_flag[0]:
        await asyncio.sleep(0.5)

        new_comments = await collect_visible_comments(page, seen_ids)
        if new_comments:
            comments.extend(new_comments)
            print(f"  ➕ 신규 댓글 {len(new_comments)}개 감지 (누적 {len(comments)}개)")
            for comment in new_comments[:3]:
                preview = (comment["text"][:60] + "...") if len(comment["text"]) > 60 else comment["text"]
                print(f"     · @{comment['username'] or 'unknown'} | {preview}")

        # 브라우저가 닫혔는지 체크
        try:
            await page.evaluate("1")
        except:
            print("\n  ⚠️  브라우저가 닫혔습니다")
            break

    print(f"\n{'═' * 70}")
    print(f"  ✅ 수집 완료!")
    print(f"  {'─' * 66}")
    print(f"      📝 총 수집 댓글: {len(comments)}개")
    print(f"{'═' * 70}\n")

    return comments


# -----------------------
# 엑셀 저장
# -----------------------
def save_to_excel(comments, output_path):
    """엑셀 파일 저장"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        print("  ⚠️  openpyxl 라이브러리가 필요합니다: pip install openpyxl Pillow")
        return

    if not comments:
        print("  ⚠️  저장할 데이터 없음")
        return

    print(f"\n{'─' * 70}")
    print(f"  📊 엑셀 파일 생성 중...")
    print(f"{'─' * 70}")

    wb = Workbook()
    ws = wb.active
    ws.title = "댓글 목록"

    # 헤더
    headers = ["작성자", "댓글 내용", "작성 시간", "좋아요 수", "대댓글 수"]
    ws.append(headers)

    # 헤더 스타일
    header_fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
    header_font = Font(bold=True)
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 열 너비
    ws.column_dimensions['A'].width = 20  # 작성자
    ws.column_dimensions['B'].width = 60  # 댓글 내용
    ws.column_dimensions['C'].width = 20  # 작성 시간
    ws.column_dimensions['D'].width = 12  # 좋아요 수
    ws.column_dimensions['E'].width = 12  # 대댓글 수

    # 데이터 행
    for idx, comment in enumerate(comments, start=2):
        row_data = [
            comment.get("username", ""),
            comment.get("text", ""),
            comment.get("timestamp", ""),
            comment.get("likes", "0"),
            comment.get("replies", "0"),
        ]
        ws.append(row_data)

        # 텍스트 정렬
        for col_idx in range(1, 6):
            cell = ws.cell(row=idx, column=col_idx)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # 첫 행 고정
    ws.freeze_panes = "A2"

    # 저장
    wb.save(output_path)

    print(f"\n{'─' * 70}")
    print(f"  💾 엑셀 파일 저장 완료!")
    print(f"  {'─' * 66}")
    print(f"      📁 파일명: {output_path}")
    print(f"      📊 레코드: {len(comments)}개")
    print(f"{'─' * 70}\n")


# -----------------------
# CSV 저장
# -----------------------
def save_to_csv(comments, output_path):
    """CSV 저장"""
    if not comments:
        print("  ⚠️  저장할 데이터 없음")
        return

    fieldnames = ["작성자", "댓글 내용", "작성 시간", "좋아요 수", "대댓글 수"]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for comment in comments:
            mapped_comment = {
                "작성자": comment.get("username", ""),
                "댓글 내용": comment.get("text", ""),
                "작성 시간": comment.get("timestamp", ""),
                "좋아요 수": comment.get("likes", "0"),
                "대댓글 수": comment.get("replies", "0"),
            }
            writer.writerow(mapped_comment)

    print(f"\n{'─' * 70}")
    print(f"  💾 CSV 파일 저장 완료!")
    print(f"  {'─' * 66}")
    print(f"      📁 파일명: {output_path}")
    print(f"      📊 레코드: {len(comments)}개")
    print(f"{'─' * 70}\n")


# -----------------------
# 메인
# -----------------------
async def main():
    print(f"\n{'═' * 70}")
    print(f"  📸 Instagram 댓글 수집기")
    print(f"{'═' * 70}\n")

    # 필수 라이브러리 체크
    check_dependencies()

    # 로그인 방식 선택
    print(f"{'─' * 70}")
    print(f"  🔑 로그인 방식 선택:")
    print(f"  {'─' * 66}")
    print(f"      1. Username/Password 로그인 (간편)")
    print(f"      2. 쿠키 직접 입력")
    print(f"      3. .env 파일에서 쿠키 로드")
    print(f"  {'─' * 66}")
    login_mode = input("  선택 (1/2/3, 엔터 = 1): ").strip()

    use_login = False
    username = None
    password = None
    cookies = None

    if login_mode == '1':
        # Username/Password 방식
        use_login = True
        print(f"\n{'─' * 70}")
        print(f"  👤 Instagram 계정 정보 입력")
        print(f"{'─' * 70}")
        username = input("  Username: ").strip()
        if not username:
            print(f"  ❌ Username을 입력하세요")
            return

        import getpass
        password = getpass.getpass("  Password: ").strip()
        if not password:
            print(f"  ❌ Password를 입력하세요")
            return

    elif login_mode == '3':
        cookies = load_cookies_from_env()
        if not cookies:
            return
    else:
        cookies = get_cookies_from_user()
        if not cookies:
            print(f"\n  ❌ 쿠키 입력이 취소되었습니다")
            return

        # .env 저장 여부
        print(f"\n{'─' * 70}")
        save_choice = input("  💾 입력한 쿠키를 .env 파일로 저장하시겠습니까? (y/n, 엔터 = n): ").strip().lower()
        if save_choice in ['y', 'yes']:
            save_to_env_file(cookies)

    # 게시글 URL 입력
    print(f"\n{'─' * 70}")
    url = input("  🔗 Instagram 게시글 URL: ").strip()
    if not url:
        print(f"  ❌ URL을 입력하세요")
        return

    # 출력 파일명
    output = input(f"  📁 저장 파일명 (엔터 = comments.xlsx): ").strip() or "comments.xlsx"
    if not output.endswith(".xlsx") and not output.endswith(".csv"):
        output += ".xlsx"

    # 스크롤 모드 선택
    print(f"\n{'─' * 70}")
    print(f"  📜 스크롤 모드 선택:")
    print(f"  {'─' * 66}")
    print(f"      1. 자동 스크롤 (기본)")
    print(f"      2. 수동 스크롤 - 사용자가 직접 스크롤하면 실시간 수집")
    print(f"  {'─' * 66}")
    scroll_mode = input("  선택 (1/2, 엔터 = 1): ").strip()
    manual_scroll = scroll_mode == '2'

    # 최대 스크롤 (자동 모드만)
    max_scrolls = 100
    if not manual_scroll:
        max_scrolls_input = input(f"  🔢 최대 스크롤 (엔터 = 100): ").strip()
        max_scrolls = int(max_scrolls_input) if max_scrolls_input else 100

    # 헤드리스 모드
    headless_input = input(f"  👻 브라우저 숨김? (y/n, 엔터 = n): ").strip().lower()
    headless = headless_input in ['y', 'yes']

    # Playwright 실행
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--force-dark-mode=0',
                '--disable-blink-features=AutomationControlled'
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='ko-KR'
        )

        # Stealth 설정 (봇 감지 회피)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()

        try:
            if use_login:
                # Username/Password 로그인
                print(f"\n{'─' * 70}")
                print(f"  🔐 Instagram 로그인 중...")
                await page.goto('https://www.instagram.com/accounts/login/')
                await page.wait_for_timeout(3000)

                try:
                    await page.wait_for_selector('input[name="username"]', timeout=10000)

                    print(f"  ✍️  사용자명 입력 중...")
                    await page.fill('input[name="username"]', username)
                    await page.wait_for_timeout(1000)

                    print(f"  🔑 비밀번호 입력 중...")
                    await page.fill('input[name="password"]', password)
                    await page.wait_for_timeout(1000)

                    print(f"  🚀 로그인 버튼 클릭...")
                    await page.click('button[type="submit"]')
                    await page.wait_for_timeout(5000)

                    print(f"  ✅ 로그인 완료!")

                    # "나중에 하기" 버튼 처리
                    try:
                        not_now = page.locator('button:has-text("나중에 하기"), button:has-text("Not Now")')
                        if await not_now.count() > 0:
                            await not_now.first.click()
                            await page.wait_for_timeout(2000)
                    except:
                        pass

                    # 알림 버튼 처리
                    try:
                        not_now = page.locator('button:has-text("나중에 하기"), button:has-text("Not Now")')
                        if await not_now.count() > 0:
                            await not_now.first.click()
                            await page.wait_for_timeout(2000)
                    except:
                        pass

                except Exception as e:
                    print(f"  ❌ 로그인 실패: {e}")
                    return

                print(f"{'─' * 70}\n")

            else:
                # 쿠키 로드
                if not await load_cookies_to_context(context, cookies):
                    print(f"\n  ❌ 쿠키 로드 실패")
                    return

            # 댓글 수집
            if manual_scroll:
                comments = await extract_comments_manual(page, url)
            else:
                comments = await extract_comments_auto(page, url, max_scrolls)

            # 저장
            if comments:
                if output.endswith('.xlsx'):
                    save_to_excel(comments, output)
                else:
                    save_to_csv(comments, output)
                print(f"{'═' * 70}")
                print(f"  ✅ 모든 작업이 성공적으로 완료되었습니다!")
                print(f"{'═' * 70}\n")
            else:
                print(f"  ⚠️  추출된 데이터 없음 (DOM 구조 분석 단계)")
                print(f"  💡 위의 DOM 분석 결과를 참고하여 추출 로직을 구현해야 합니다")

        except KeyboardInterrupt:
            print(f"\n\n  ⏹️  사용자에 의해 중단됨")
        except Exception as e:
            print(f"\n  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"\n  🔚 브라우저를 5초 후 종료합니다...")
            await page.wait_for_timeout(5000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
