#!/usr/bin/env python3
"""Add instruction pages to each section of the APUSH practice tests."""

import json
import requests
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Parse .env
with open('.env') as f:
    content = '{' + f.read().strip() + '}'
    creds = json.loads(content)

CLIENT_ID = creds['client_id']
CLIENT_SECRET = creds['client_secret']
print(f'Using credentials for: {creds["owner_name"]}')

QTI_BASE = 'https://qti.alpha-1edtech.ai/api'
ONEROSTER_BASE = 'https://api.alpha-1edtech.ai'
TOKEN_URL = 'https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token'

COURSES = {
    1: {'id': 'cc78ea76-69d8-4b0a-8dfd-8031b6572770', 'title': 'APUSH Practice Test 1 2026'},
    2: {'id': '90a8a692-3324-4fe2-9be6-753495e0d9f5', 'title': 'APUSH Practice Test 2 2026'},
}

# Instructions for each section
INSTRUCTIONS = {
    'sec1a': {
        'title': 'Section I, Part A: Multiple Choice Instructions',
        'content': """<h2>Section I, Part A: Multiple-Choice Questions</h2>
<p><strong>Time:</strong> 55 minutes</p>
<p><strong>Questions:</strong> 55 questions</p>
<p><strong>Weight:</strong> 40% of your exam score</p>
<hr/>
<h3>Instructions</h3>
<p>Answer <strong>all 55 questions</strong>. Each question has four answer choices. Select the best answer for each question.</p>
<p>Questions are organized in sets of 3-4 questions based on a stimulus (primary source, secondary source, image, map, or chart). Read each stimulus carefully before answering the related questions.</p>
<h3>Tips</h3>
<ul>
<li>Pace yourself: aim for about 1 minute per question</li>
<li>Read the stimulus carefully before looking at the questions</li>
<li>Eliminate obviously wrong answers first</li>
<li>If unsure, make your best guess - there is no penalty for guessing</li>
</ul>
<p><strong>Good luck!</strong></p>"""
    },
    'sec1b': {
        'title': 'Section I, Part B: Short Answer Instructions',
        'content': """<h2>Section I, Part B: Short-Answer Questions</h2>
<p><strong>Time:</strong> 40 minutes</p>
<p><strong>Questions:</strong> 4 questions (answer 3)</p>
<p><strong>Weight:</strong> 20% of your exam score</p>
<hr/>
<h3>Instructions</h3>
<p>You must answer <strong>3 out of 4 questions</strong>:</p>
<ul>
<li><strong>Question 1 (Required):</strong> Based on a secondary source</li>
<li><strong>Question 2 (Required):</strong> Based on a primary source</li>
<li><strong>Question 3 OR Question 4 (Choose one):</strong> No stimulus - choose the one you feel most confident about</li>
</ul>
<p>Each question has three parts (a, b, c). Answer all three parts for each question you attempt.</p>
<h3>Tips</h3>
<ul>
<li>Spend about 13 minutes per question</li>
<li>Write in complete sentences but be concise</li>
<li>Directly address what each part asks</li>
<li>Use specific historical evidence to support your answers</li>
<li>For Questions 3 and 4, read both before choosing which to answer</li>
</ul>
<p><strong>Good luck!</strong></p>"""
    },
    'sec2a': {
        'title': 'Section II, Part A: DBQ Instructions',
        'content': """<h2>Section II, Part A: Document-Based Question (DBQ)</h2>
<p><strong>Time:</strong> 60 minutes (includes 15-minute reading period)</p>
<p><strong>Questions:</strong> 1 question</p>
<p><strong>Weight:</strong> 25% of your exam score</p>
<hr/>
<h3>Instructions</h3>
<p>Write an essay that responds to the prompt. Use evidence from <strong>all or all but one</strong> of the documents provided, plus your own outside knowledge of history.</p>
<h3>Recommended Timing</h3>
<ul>
<li><strong>First 15 minutes:</strong> Read the documents and plan your essay</li>
<li><strong>Remaining 45 minutes:</strong> Write your essay</li>
</ul>
<h3>Scoring Reminders</h3>
<p>Your essay will be scored on:</p>
<ul>
<li><strong>Thesis (1 point):</strong> Make a historically defensible claim that responds to the prompt</li>
<li><strong>Contextualization (1 point):</strong> Describe the broader historical context</li>
<li><strong>Evidence (3 points):</strong> Use documents and outside knowledge effectively</li>
<li><strong>Analysis & Reasoning (2 points):</strong> Analyze the documents and demonstrate complex understanding</li>
</ul>
<p><strong>Good luck!</strong></p>"""
    },
    'sec2b': {
        'title': 'Section II, Part B: Long Essay Instructions',
        'content': """<h2>Section II, Part B: Long Essay Question (LEQ)</h2>
<p><strong>Time:</strong> 40 minutes</p>
<p><strong>Questions:</strong> 3 options (choose 1)</p>
<p><strong>Weight:</strong> 15% of your exam score</p>
<hr/>
<h3>Instructions</h3>
<p>Choose <strong>ONE</strong> of the three essay prompts. Each prompt covers a different time period:</p>
<ul>
<li><strong>Option 1:</strong> Periods 1-3 (1491-1800)</li>
<li><strong>Option 2:</strong> Periods 4-6 (1800-1898)</li>
<li><strong>Option 3:</strong> Periods 7-9 (1890-Present)</li>
</ul>
<p>All three prompts will ask you to apply the same historical thinking skill (such as causation, comparison, or continuity and change over time).</p>
<h3>Scoring Reminders</h3>
<p>Your essay will be scored on:</p>
<ul>
<li><strong>Thesis (1 point):</strong> Make a historically defensible claim</li>
<li><strong>Contextualization (1 point):</strong> Describe the broader historical context</li>
<li><strong>Evidence (2 points):</strong> Use specific historical evidence</li>
<li><strong>Analysis & Reasoning (2 points):</strong> Demonstrate complex understanding</li>
</ul>
<h3>Tips</h3>
<ul>
<li>Choose the prompt you know the most about</li>
<li>Spend 5 minutes planning before writing</li>
<li>Use specific historical examples, not generalizations</li>
</ul>
<p><strong>Good luck!</strong></p>"""
    },
}


class TimebackAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._expires_at = None

    def get_headers(self):
        if not self._token or datetime.now() >= self._expires_at:
            self._refresh()
        return {'Authorization': f'Bearer {self._token}', 'Content-Type': 'application/json'}

    def _refresh(self):
        resp = requests.post(
            TOKEN_URL,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data['access_token']
        self._expires_at = datetime.now() + timedelta(seconds=data['expires_in'] - 300)


def make_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    return session


session = make_session()
auth = TimebackAuth(CLIENT_ID, CLIENT_SECRET)


def create_stimulus(stim_id, title, content):
    payload = {'identifier': stim_id, 'title': title, 'content': content}
    resp = session.post(f'{QTI_BASE}/stimuli', headers=auth.get_headers(), json=payload, timeout=30)
    ok = resp.status_code in (200, 201, 409)
    print(f'  Stimulus {stim_id}: {"OK" if ok else "FAIL " + str(resp.status_code)}')
    return stim_id if ok else None


def create_resource(res_id, title, stim_id):
    payload = {
        'resource': {
            'sourcedId': res_id,
            'status': 'active',
            'title': title,
            'metadata': {
                'type': 'qti',
                'subType': 'qti-stimulus',
                'language': 'en-US',
                'lessonType': 'alpha-read-article',
                'assessmentType': 'alpha-read',
                'allowRetake': True,
                'displayType': 'interactive',
                'showResults': True,
                'url': f'{QTI_BASE}/stimuli/{stim_id}',
                'xp': 0,
            },
            'roles': ['primary'],
            'importance': 'primary',
            'vendorResourceId': stim_id,
            'vendorId': 'alpha-incept',
            'applicationId': 'incept',
        }
    }
    resp = session.post(
        f'{ONEROSTER_BASE}/ims/oneroster/resources/v1p2/resources/',
        headers=auth.get_headers(),
        json=payload,
        timeout=30,
    )
    ok = resp.status_code in (200, 201, 409)
    print(f'  Resource {res_id}: {"OK" if ok else "FAIL " + str(resp.status_code)}')
    return res_id if ok else None


def link_resource(cr_id, title, comp_id, res_id, sort_order):
    payload = {
        'componentResource': {
            'sourcedId': cr_id,
            'status': 'active',
            'title': title,
            'sortOrder': sort_order,
            'courseComponent': {'sourcedId': comp_id},
            'resource': {'sourcedId': res_id},
            'lessonType': 'alpha-read-article',
        }
    }
    resp = session.post(
        f'{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/component-resources',
        headers=auth.get_headers(),
        json=payload,
        timeout=30,
    )
    ok = resp.status_code in (200, 201, 409)
    print(f'  Link: {"OK" if ok else "FAIL " + str(resp.status_code)}')
    return cr_id if ok else None


# Component IDs from earlier linking
COMP_IDS = {
    1: {
        'sec1a': 'apush-pt1-sec1a-linked',
        'sec1b': 'apush-pt1-sec1b-linked',
        'sec2a': 'apush-pt1-sec2a-linked',
        'sec2b': 'apush-pt1-sec2b-linked',
    },
    2: {
        'sec1a': 'apush-pt2-sec1a-linked',
        'sec1b': 'apush-pt2-sec1b-linked',
        'sec2a': 'apush-pt2-sec2a-linked',
        'sec2b': 'apush-pt2-sec2b-linked',
    },
}

for test_num in [1, 2]:
    print(f'\n{"="*50}')
    print(f'Adding Instructions to Test {test_num}')
    print(f'{"="*50}')

    for sec_key, instr in INSTRUCTIONS.items():
        print(f'\n{sec_key}:')
        stim_id = f'apush-pt{test_num}-{sec_key}-instr'
        res_id = f'apush-pt{test_num}-{sec_key}-instr-res'
        cr_id = f'apush-pt{test_num}-{sec_key}-instr-cr'
        comp_id = COMP_IDS[test_num][sec_key]

        create_stimulus(stim_id, instr['title'], instr['content'])
        create_resource(res_id, instr['title'], stim_id)
        # Sort order 0 puts instructions before the quiz (which is sort order 1)
        link_resource(cr_id, instr['title'], comp_id, res_id, 0)

print('\n' + '=' * 50)
print('COMPLETE!')
print('=' * 50)
