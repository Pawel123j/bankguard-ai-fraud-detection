import os
import re
import sys
import subprocess
from pathlib import Path
from playwright.sync_api import expect
from accessibility import assert_accessible
from browser_support import browser, static_site, application

REPO = Path(__file__).resolve().parents[1]

def test_bankguard_import_session_cases(tmp_path):
    repo = REPO
    python = os.environ.get('E2E_API_PYTHON', sys.executable)
    with static_site(REPO / 'frontend/dist') as url:
        env = {'BANKGUARD_DATABASE_URL': 'sqlite:///' + str(tmp_path / 'bankguard.db'),
               'BANKGUARD_JWT_SECRET': 'isolated-browser-test-only-signing-key', 'BANKGUARD_CORS_ORIGINS': url}
        seed = "from app.database import init_db,SessionLocal; from app.models import Analyst; from app.security import hash_password; init_db(); db=SessionLocal(); db.add(Analyst(email='browser@example.com', full_name='Browser Test', password_hash=hash_password('browser-test-only'))); db.commit(); db.close()"
        subprocess.run([python, '-c', seed], cwd=repo / 'backend', env={**os.environ, **env}, check=True)
        with application('bankguard', [python, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18321'], repo / 'backend', 'http://127.0.0.1:18321/health', env), browser() as b:
            page = b.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url)
            assert_accessible(page, REPO, "login")
            page.get_by_label('Email', exact=True).fill('browser@example.com')
            page.get_by_label('Password', exact=True).fill('browser-test-only')
            page.get_by_role('button', name='Sign in', exact=True).click()
            assert_accessible(page, REPO, 'dashboard')
            page.get_by_role('button', name=re.compile('Transactions$')).click()
            page.locator('input[type=file]').set_input_files(repo / 'backend/data/sample_transactions.csv')
            page.get_by_role('button', name='Import', exact=True).click()
            expect(page.get_by_text(re.compile('Imported [1-9].*transactions'))).to_be_visible()
            page.get_by_role('button', name=re.compile('Cases$')).click()
            card = page.locator('.case-card').first
            case_id = card.locator('select').get_attribute('aria-label')
            card.locator('textarea').fill('Reviewed in browser regression')
            card.get_by_role('button', name='Save notes').click()
            expect(card.get_by_role('button', name='Save notes')).to_be_enabled()
            card.locator('select').select_option('INVESTIGATING')
            page.reload()
            case = page.locator('.case-card').filter(has=page.get_by_label(case_id, exact=True))
            expect(case.locator('textarea')).to_have_value('Reviewed in browser regression')
            expect(case.locator('select')).to_have_value('INVESTIGATING')
            # A failed write keeps the draft and exposes a retryable UI error.
            page.route('**/api/cases/*', lambda route: route.fulfill(status=500, body='Temporary write failure'))
            case.get_by_role('button', name='Save notes').click()
            expect(page.get_by_text('Temporary write failure', exact=True)).to_be_visible()
            expect(case.locator('textarea')).to_have_value('Reviewed in browser regression')
            page.unroute('**/api/cases/*')
            # Saving unchanged notes must not erase the persisted text.
            case.get_by_role('button', name='Save notes').click()
            expect(case.get_by_role('button', name='Save notes')).to_be_enabled()
            page.reload()
            expect(page.locator('.case-card').filter(has=page.get_by_label(case_id, exact=True)).locator('textarea')).to_have_value('Reviewed in browser regression')
            page.get_by_role('button', name=re.compile('Sign out|Logout|Log out')).click()
            expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_visible()
            assert page.evaluate("sessionStorage.getItem('bankguard.access_token')") is None
            page.reload()
            expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_visible()
            # A stale UI flag in another tab cannot create an authenticated UI.
            page.evaluate("localStorage.setItem('bankguard-authenticated','true')")
            page.reload()
            expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_visible()
            page.get_by_label('Email', exact=True).fill('browser@example.com')
            page.get_by_label('Password', exact=True).fill('browser-test-only')
            page.get_by_role('button', name='Sign in', exact=True).click()
            expect(page.get_by_role('button', name='Sign out', exact=True)).to_be_visible()
            page.evaluate("sessionStorage.setItem('bankguard.access_token','invalid-token')")
            page.reload()
            expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_visible()
            assert page.evaluate("sessionStorage.getItem('bankguard.access_token')") is None
            assert not errors, errors
