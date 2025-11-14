/**
 * Playwright를 사용한 인스타그램 댓글 구조 분석
 * 예시: node analyze_instagram_playwright.js
 */

const { chromium } = require('playwright');

async function analyzeInstagramComment() {
    const browser = await chromium.launch({
        headless: false,
        args: ['--force-dark-mode=0']
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    const page = await context.newPage();

    const testUrl = 'https://www.instagram.com/p/DPU_Po0Eryk/';
    const testUsername = 'tpot_21';

    console.log('='.repeat(60));
    console.log('인스타그램 댓글 구조 분석 (Playwright)');
    console.log('='.repeat(60));
    console.log(`\n게시글 URL: ${testUrl}`);
    console.log(`검색할 사용자: ${testUsername}`);

    try {
        // 게시글 로드
        console.log('\n게시글 로딩...');
        await page.goto(testUrl, { waitUntil: 'networkidle' });
        await page.waitForTimeout(5000);

        console.log('\n⚠️ 브라우저 창에서 인스타그램에 로그인해주세요.');
        console.log('로그인 후 엔터를 눌러주세요...');

        // 사용자 입력 대기 (터미널)
        await new Promise(resolve => {
            process.stdin.once('data', resolve);
        });

        console.log('\n댓글 분석 시작...\n');
        await page.waitForTimeout(2000);

        // 1. 댓글 더보기 버튼 찾기
        console.log('1. 댓글 더보기 버튼 찾기...');
        const loadMoreSelectors = [
            'span:has-text("댓글")',
            'span:has-text("View")',
            'button:has-text("View all")',
            'div[role="button"]:has-text("comment")'
        ];

        for (const selector of loadMoreSelectors) {
            const count = await page.locator(selector).count();
            if (count > 0) {
                console.log(`   ✓ 발견: ${selector} (${count}개)`);

                // 클릭 시도
                try {
                    await page.locator(selector).first().click({ timeout: 2000 });
                    console.log(`   → 클릭 성공!`);
                    await page.waitForTimeout(2000);
                } catch (e) {
                    console.log(`   → 클릭 불가`);
                }
            }
        }

        // 2. 스크롤하여 댓글 로드
        console.log('\n2. 스크롤하여 댓글 로드...');
        for (let i = 0; i < 5; i++) {
            await page.evaluate(() => window.scrollBy(0, 300));
            await page.waitForTimeout(1000);
            console.log(`   스크롤 ${i + 1}/5`);
        }

        // 3. 사용자명으로 검색
        console.log(`\n3. '${testUsername}' 사용자 검색...`);

        // 프로필 링크 검색
        const profileLinkSelectors = [
            `a[href="/${testUsername}/"]`,
            `a[href*="/${testUsername}"]`,
        ];

        let foundLinks = [];
        for (const selector of profileLinkSelectors) {
            const links = await page.locator(selector).all();
            if (links.length > 0) {
                console.log(`   ✓ ${selector}: ${links.length}개 발견`);
                foundLinks.push(...links);

                // 첫 번째 링크 분석
                if (links.length > 0) {
                    const firstLink = links[0];
                    const text = await firstLink.textContent();
                    const parent = firstLink.locator('..');
                    const parentTag = await parent.evaluate(el => el.tagName);

                    console.log(`\n   첫 번째 링크 분석:`);
                    console.log(`   - 텍스트: ${text}`);
                    console.log(`   - 부모 태그: ${parentTag}`);

                    // 댓글 컨테이너 찾기
                    try {
                        // 여러 부모 패턴 시도
                        const ancestorSelectors = [
                            'xpath=./ancestor::li',
                            'xpath=./ancestor::div[@role="button"]',
                            'xpath=./ancestor::ul',
                        ];

                        for (const ancestorSel of ancestorSelectors) {
                            try {
                                const ancestor = firstLink.locator(ancestorSel).first();
                                const ancestorExists = await ancestor.count() > 0;

                                if (ancestorExists) {
                                    const ancestorText = await ancestor.textContent();
                                    const ancestorTag = await ancestor.evaluate(el => el.tagName);
                                    console.log(`   - 상위 컨테이너 (${ancestorSel}): ${ancestorTag}`);
                                    console.log(`   - 컨테이너 텍스트 길이: ${ancestorText.length}자`);
                                    console.log(`   - 텍스트 샘플: ${ancestorText.substring(0, 100)}...`);

                                    // 스크린샷 저장
                                    await ancestor.screenshot({
                                        path: `instagram_comment_container_${testUsername}.png`
                                    });
                                    console.log(`   ✓ 스크린샷 저장됨!`);
                                    break;
                                }
                            } catch (e) {
                                // 다음 셀렉터 시도
                            }
                        }
                    } catch (e) {
                        console.log(`   - 상위 컨테이너 찾기 실패: ${e.message}`);
                    }
                }
            } else {
                console.log(`   ✗ ${selector}: 없음`);
            }
        }

        // 4. 페이지 구조 분석
        console.log('\n4. 페이지 구조 분석...');

        // 모든 링크 찾기
        const allLinks = await page.locator('a').all();
        console.log(`   전체 링크 수: ${allLinks.length}개`);

        // 사용자명이 포함된 링크 필터링
        let matchingLinks = 0;
        for (const link of allLinks) {
            const href = await link.getAttribute('href');
            if (href && href.includes(testUsername)) {
                matchingLinks++;
            }
        }
        console.log(`   '${testUsername}' 포함 링크: ${matchingLinks}개`);

        // 5. HTML 구조 출력
        console.log('\n5. 댓글 영역 HTML 구조...');
        const articleContent = await page.locator('article').first().innerHTML();

        // testUsername이 포함된 부분 찾기
        if (articleContent.includes(testUsername)) {
            const index = articleContent.indexOf(testUsername);
            const snippet = articleContent.substring(Math.max(0, index - 200), index + 200);
            console.log(`\n   HTML 스니펫:`);
            console.log(`   ${snippet.replace(/\n/g, ' ').substring(0, 300)}...`);
        } else {
            console.log(`   ⚠️ article에서 '${testUsername}' 찾을 수 없음`);
        }

        // 전체 페이지 스크린샷
        await page.screenshot({ path: `instagram_full_page_${testUsername}.png`, fullPage: true });
        console.log(`\n   ✓ 전체 페이지 스크린샷 저장됨!`);

        console.log('\n' + '='.repeat(60));
        console.log('분석 완료!');
        console.log('='.repeat(60));

        console.log('\n브라우저를 10초 후 종료합니다...');
        await page.waitForTimeout(10000);

    } catch (error) {
        console.error(`\n❌ 오류 발생: ${error.message}`);
    } finally {
        await browser.close();
    }
}

analyzeInstagramComment().catch(console.error);
