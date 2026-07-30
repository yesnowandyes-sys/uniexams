#!/usr/bin/env python3
"""Probe the Pearson VUE test player DOM during 'Explain Answer' to find correct answer markers."""
import asyncio
from playwright.async_api import async_playwright

URL = "https://www.pearsonvue.com/us/en/redirects/uatuk/esat-mathematics1.html"

async def scroll_question(page):
    try:
        content = await page.query_selector("#abe-contentPane")
        if content:
            await content.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            await asyncio.sleep(0.3)
            await content.evaluate("el => el.scrollTo(0, 0)")
            await asyncio.sleep(0.3)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.2)
        await page.evaluate("window.scrollTo(0, 0)")
    except:
        pass

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # Navigate to first question
        for i in range(5):
            btn = await page.query_selector("button:has-text('Next')")
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(3)
                import re
                body = await page.inner_text("body")
                m = re.search(r'(\d+)\s+of\s+(\d+)', body)
                if m:
                    print(f"Reached question {m.group(1)} of {m.group(2)}")
                    break

        # Probe questions 1, 2, 3, 4, 5
        for qnum in range(1, 6):
            print(f"\n{'='*60}")
            print(f"PROBING QUESTION {qnum}")
            print(f"{'='*60}")

            await scroll_question(page)

            # Select A
            try:
                radio = await page.query_selector("#abe-contentPane input[type='radio'][value='A']")
                if radio:
                    await radio.click(timeout=3000)
                    await asyncio.sleep(0.5)
            except:
                pass

            # Before clicking Explain Answer - dump radio button states
            print("\n--- Radio buttons BEFORE Explain ---")
            radios_info = await page.evaluate("""() => {
                const radios = document.querySelectorAll("#abe-contentPane input[type='radio']");
                return Array.from(radios).map(r => {
                    const id = r.id;
                    const val = r.value;
                    const checked = r.checked;
                    // Walk up to find parent containers and their classes
                    let parentInfo = [];
                    let p = r;
                    for (let i = 0; i < 8; i++) {
                        p = p.parentElement;
                        if (!p) break;
                        if (p.className || p.id) {
                            parentInfo.push({
                                tag: p.tagName,
                                id: p.id,
                                class: p.className,
                                dataAttrs: Object.keys(p.dataset).reduce((acc, k) => { acc[k] = p.dataset[k]; return acc; }, {})
                            });
                        }
                    }
                    // Check for labels
                    const label = document.querySelector(`label[for='${id}']`);
                    const labelClass = label ? label.className : null;
                    return { id, val, checked, parentInfo, labelClass };
                });
            }""")
            for r in radios_info:
                if r['parentInfo']:
                    print(f"  Radio {r['val']}: checked={r['checked']}, labelClass={r['labelClass']}")
                    for pi in r['parentInfo'][:3]:
                        print(f"    <{pi['tag']} id='{pi['id']}' class='{pi['class']}'>")

            # Click Explain Answer
            explain_btn = await page.query_selector("button:has-text('Explain Answer')")
            if explain_btn and await explain_btn.is_visible():
                await page.evaluate("document.querySelectorAll('.ui-widget-overlay').forEach(el => el.remove());")
                try:
                    await explain_btn.click(timeout=10000)
                except:
                    await explain_btn.click(force=True, timeout=5000)
                await asyncio.sleep(3)

                print("\n--- Radio buttons AFTER Explain (during dialog) ---")
                radios_after = await page.evaluate("""() => {
                    const radios = document.querySelectorAll("#abe-contentPane input[type='radio']");
                    return Array.from(radios).map(r => {
                        const id = r.id;
                        const val = r.value;
                        const checked = r.checked;
                        let parentInfo = [];
                        let p = r;
                        for (let i = 0; i < 8; i++) {
                            p = p.parentElement;
                            if (!p) break;
                            if (p.className || p.id) {
                                parentInfo.push({
                                    tag: p.tagName,
                                    id: p.id,
                                    class: p.className,
                                });
                            }
                        }
                        const label = document.querySelector(`label[for='${id}']`);
                        const labelClass = label ? label.className : null;
                        return { id, val, checked, parentInfo, labelClass };
                    });
                }""")
                for r in radios_after:
                    print(f"  Radio {r['val']}: checked={r['checked']}, labelClass={r['labelClass']}")
                    for pi in r['parentInfo'][:3]:
                        if pi['class']:
                            print(f"    <{pi['tag']} id='{pi['id']}' class='{pi['class']}'>")

                # Check for answer key labels
                print("\n--- Answer Key Labels ---")
                key_labels = await page.evaluate("""() => {
                    const labels = document.querySelectorAll('.abe-displayAnswerKeyLabel, .abe-correctAnswer, .correct, .correct-answer');
                    return Array.from(labels).map(l => ({ tag: l.tagName, class: l.className, text: l.innerText.substring(0, 100), id: l.id }));
                }""")
                for l in key_labels:
                    print(f"  <{l['tag']} class='{l['class']}' id='{l['id']}'> = {l['text'][:80]}")

                # Check for any element with "correct" in class name
                print("\n--- Elements with 'correct' in class ---")
                correct_elems = await page.evaluate("""() => {
                    const all = document.querySelectorAll('[class*="correct"], [class*="Correct"], [class*="right"], [class*="answer-key"]');
                    return Array.from(all).slice(0, 20).map(e => ({
                        tag: e.tagName,
                        class: e.className,
                        id: e.id,
                        text: e.innerText.substring(0, 80),
                        html: e.innerHTML.substring(0, 200)
                    }));
                }""")
                for e in correct_elems:
                    print(f"  <{e['tag']} class='{e['class']}' id='{e['id']}'> text={e['text'][:60]}")

                # Check for any element with data-correct or data-answer
                print("\n--- Elements with data-correct/data-answer ---")
                data_elems = await page.evaluate("""() => {
                    const all = document.querySelectorAll('[data-correct], [data-answer], [data-correct-answer]');
                    return Array.from(all).slice(0, 20).map(e => ({
                        tag: e.tagName,
                        class: e.className,
                        id: e.id,
                        text: e.innerText.substring(0, 80),
                        attrs: Object.keys(e.dataset).reduce((acc,k)=>{acc[k]=e.dataset[k];return acc;},{})
                    }));
                }""")
                for e in data_elems:
                    print(f"  <{e['tag']} data={JSON.stringify(e['attrs'])}> text={e['text'][:60]}")

                # Check the solution dialog content
                print("\n--- Solution Dialog Content ---")
                dialog_info = await page.evaluate("""() => {
                    const dialog = document.querySelector('#abe-solutionDialog') || document.querySelector('.ui-dialog-content');
                    if (!dialog) return null;
                    return {
                        html: dialog.innerHTML.substring(0, 2000),
                        text: dialog.innerText.substring(0, 500),
                        visible: dialog.offsetParent !== null
                    };
                }""")
                if dialog_info:
                    print(f"  Visible: {dialog_info['visible']}")
                    print(f"  Text: {dialog_info['text'][:300]}")
                    print(f"  HTML (first 1000): {dialog_info['html'][:1000]}")

                # Check for selected/clicked class on labels
                print("\n--- Label classes detail ---")
                label_details = await page.evaluate("""() => {
                    const labels = document.querySelectorAll('#abe-contentPane label');
                    return Array.from(labels).map(l => ({
                        for: l.getAttribute('for'),
                        class: l.className,
                        text: l.innerText.substring(0, 60)
                    }));
                }""")
                for l in label_details:
                    if l['class']:
                        print(f"  label[for='{l['for']}'] class='{l['class']}' text={l['text'][:40]}")

                # Screenshot
                await page.screenshot(path=f"/tmp/probe_q{qnum}.png", full_page=False)
                print(f"\n  Screenshot: /tmp/probe_q{qnum}.png")

                # Close dialog
                close_btn = await page.query_selector(".ui-dialog-titlebar-close")
                if close_btn:
                    await close_btn.click(timeout=2000)
                    await asyncio.sleep(1)
            else:
                print("  No 'Explain Answer' button found!")

            # Navigate to next question
            btn = await page.query_selector("button:has-text('Next')")
            if btn and await btn.is_visible():
                await btn.click(timeout=10000)
                await asyncio.sleep(3)

        await browser.close()

asyncio.run(main())
