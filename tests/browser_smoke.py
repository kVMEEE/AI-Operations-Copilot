"""Run against an explicitly started local server; no external network required."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8010');parser.add_argument('--screenshot',default='/tmp/aiops-browser.png');args=parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000}); errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url);page.locator('#description').fill('<img src=x onerror="window.injected=true"> Synthetic database')
        page.locator('#mode').select_option('llm');page.locator('#submit').click()
        page.wait_for_function("document.querySelector('#status').textContent.startsWith('completed')")
        assert 'deterministic' in page.locator('#modes').inner_text()
        assert 'fallback' in page.locator('#modes').inner_text()
        assert 'Database' in page.locator('#hypotheses').inner_text()
        assert 'Inspect contention and connection evidence' in page.locator('#report').inner_text()
        assert 'Prerequisites:' in page.locator('#report').inner_text()
        assert 'Operational impact:' in page.locator('#report').inner_text()
        assert 'frequency' in page.locator('#evidence').inner_text()
        assert page.locator('#citations').inner_text()
        assert page.evaluate('window.injected') is None
        assert page.locator('#report script, #report img, #report iframe').count()==0
        page.reload();page.locator('#history button').first.wait_for();page.locator('#history button').first.click()
        page.wait_for_function("document.querySelector('#status').textContent.startsWith('completed')")
        page.screenshot(path=args.screenshot,full_page=True)
        assert not errors,errors
        browser.close();print('PASS browser: submission, fallback, evidence, citations, persistent history, injection escaping, no JavaScript errors')
if __name__=='__main__':main()
