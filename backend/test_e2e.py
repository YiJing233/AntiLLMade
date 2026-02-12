import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / 'backend'
FRONTEND_DIR = ROOT_DIR / 'frontend'
FRONTEND_BASE_URL = 'http://127.0.0.1:5173'
BACKEND_BASE_URL = 'http://127.0.0.1:8000'


def _wait_for_url(url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1.5)
            if response.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutError(f'Timed out waiting for {url}')


@pytest.fixture(scope='session')
def e2e_stack(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp('e2e-db')

    backend_env = os.environ.copy()
    backend_env['RAILWAY_VOLUME_MOUNT_PATH'] = str(db_dir)

    backend_proc = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
        cwd=BACKEND_DIR,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    frontend_proc = subprocess.Popen(
        ['npm', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173'],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_url(f'{BACKEND_BASE_URL}/health')
        _wait_for_url(FRONTEND_BASE_URL)
        yield
    finally:
        for proc in (frontend_proc, backend_proc):
            proc.terminate()
        for proc in (frontend_proc, backend_proc):
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture()
def page(e2e_stack):
    playwright = pytest.importorskip('playwright.sync_api')

    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()


def test_navigation_between_sources_and_digest(page):
    playwright = pytest.importorskip('playwright.sync_api')

    page.goto(FRONTEND_BASE_URL)

    playwright.expect(page.get_by_role('heading', name='订阅源管理')).to_be_visible()
    page.get_by_role('link', name='Digest').click()
    playwright.expect(page.get_by_role('heading', name='长上下文资讯阅读站')).to_be_visible()
    page.get_by_role('link', name='Sources').click()
    playwright.expect(page.get_by_role('heading', name='订阅源管理')).to_be_visible()


def test_subscription_crud_flow(page):
    playwright = pytest.importorskip('playwright.sync_api')

    page.goto(f'{FRONTEND_BASE_URL}/sources')

    page.get_by_placeholder('订阅源名称').fill('Playwright Source')
    page.get_by_placeholder('订阅源链接').fill('https://playwright.example.com/feed.xml')
    page.get_by_placeholder('分类').fill('E2E')
    page.get_by_role('button', name='添加订阅源').click()

    card = page.locator('article', has_text='Playwright Source').first
    playwright.expect(card).to_be_visible()

    card.get_by_role('button', name='移除').click()
    playwright.expect(card).not_to_be_visible()


def test_digest_view_and_empty_state(page):
    playwright = pytest.importorskip('playwright.sync_api')

    page.goto(f'{FRONTEND_BASE_URL}/digest')

    playwright.expect(page.get_by_text('AI 理解驱动的 RSS 日报')).to_be_visible()
    playwright.expect(page.get_by_label('日报日期')).to_be_visible()
    playwright.expect(page.get_by_text('暂无日报内容。')).to_be_visible()
