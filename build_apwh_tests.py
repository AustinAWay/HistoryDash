#!/usr/bin/env python3
"""Build 2 APWH Practice Tests on Timeback."""

import json
import uuid
import random
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

QTI_BASE = "https://qti.alpha-1edtech.ai/api"
ONEROSTER_BASE = "https://api.alpha-1edtech.ai"
TOKEN_URL = "https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token"
ORG_SOURCED_ID = "346488d3-efb9-4f56-95ea-f4a441de2370"

# APWH MCQ Distribution (55 questions)
# Units 1-2: 8-10% = 5 questions
# Units 3-4: 20-30% = 14 questions
# Units 5-6: 25-35% = 17 questions
# Units 7-9: 20-30% = 14 questions
# Total: 50, leaving 5 flex
MCQ_DISTRIBUTION = {
    '1': 2,   # 8-10% split
    '2': 3,   # 8-10% split
    '3': 7,   # 20-30% split
    '4': 7,   # 20-30% split
    '5': 8,   # 25-35% split
    '6': 9,   # 25-35% split
    '7': 5,   # 20-30% split
    '8': 5,   # 20-30% split
    '9': 4,   # 20-30% split
    # Total: 50, fill remaining 5 from wherever available
}

# Instructions for each section
INSTRUCTIONS = {
    'sec1a': {
        'title': 'Section I, Part A: Multiple Choice Instructions',
        'content': """<h2>Section I, Part A: Multiple-Choice Questions</h2>
<p><b>Time:</b> 55 minutes</p>
<p><b>Questions:</b> 55 questions</p>
<p><b>Weight:</b> 40% of your exam score</p>
<p>---</p>
<h3>Instructions</h3>
<p>Answer <b>all 55 questions</b>. Each question has four answer choices. Select the best answer for each question.</p>
<p>Questions are organized in sets based on a stimulus (primary source, secondary source, image, map, or chart). Read each stimulus carefully before answering the related questions.</p>
<h3>Content Coverage</h3>
<p>Units 1-2 (1200-1450): 8-10%</p>
<p>Units 3-4 (1450-1750): 20-30%</p>
<p>Units 5-6 (1750-1900): 25-35%</p>
<p>Units 7-9 (1900-Present): 20-30%</p>
<h3>Tips</h3>
<p>Pace yourself at about 1 minute per question. Read stimuli carefully. Eliminate wrong answers first. No penalty for guessing.</p>
<p><b>Good luck!</b></p>"""
    },
    'sec1b': {
        'title': 'Section I, Part B: Short Answer Instructions',
        'content': """<h2>Section I, Part B: Short-Answer Questions</h2>
<p><b>Time:</b> 40 minutes</p>
<p><b>Questions:</b> 4 questions (answer 3)</p>
<p><b>Weight:</b> 20% of your exam score</p>
<p>---</p>
<h3>Instructions</h3>
<p>You must answer <b>3 out of 4 questions</b>:</p>
<p>Question 1 (Required): Based on a secondary source</p>
<p>Question 2 (Required): Based on a primary source</p>
<p>Question 3 OR Question 4 (Choose one): No stimulus</p>
<p>Each question has three parts (a, b, c). Answer all parts for each question you attempt.</p>
<h3>Tips</h3>
<p>Spend about 13 minutes per question. Write concisely in complete sentences. Use specific historical evidence. Read both Q3 and Q4 before choosing.</p>
<p><b>Good luck!</b></p>"""
    },
    'sec2a': {
        'title': 'Section II, Part A: DBQ Instructions',
        'content': """<h2>Section II, Part A: Document-Based Question (DBQ)</h2>
<p><b>Time:</b> 60 minutes (includes 15-minute reading period)</p>
<p><b>Questions:</b> 1 question</p>
<p><b>Weight:</b> 25% of your exam score</p>
<p>---</p>
<h3>Instructions</h3>
<p>Write an essay responding to the prompt. Use evidence from all or all but one of the documents, plus your own outside knowledge. Documents will represent at least 3 world regions.</p>
<h3>Timing</h3>
<p>First 15 minutes: Read documents and plan</p>
<p>Remaining 45 minutes: Write your essay</p>
<h3>Scoring</h3>
<p>Thesis (1 pt): Historically defensible claim</p>
<p>Contextualization (1 pt): Broader historical context</p>
<p>Evidence (3 pts): Documents and outside knowledge</p>
<p>Analysis (2 pts): Complex understanding</p>
<p><b>Good luck!</b></p>"""
    },
    'sec2b': {
        'title': 'Section II, Part B: Long Essay Instructions',
        'content': """<h2>Section II, Part B: Long Essay Question (LEQ)</h2>
<p><b>Time:</b> 40 minutes</p>
<p><b>Questions:</b> 2 options (choose 1)</p>
<p><b>Weight:</b> 15% of your exam score</p>
<p>---</p>
<h3>Instructions</h3>
<p>Choose <b>ONE</b> of the two essay prompts. Each covers a different time period.</p>
<p>Both prompts test the same historical thinking skill (causation, comparison, or continuity/change).</p>
<h3>Scoring</h3>
<p>Thesis (1 pt): Historically defensible claim</p>
<p>Contextualization (1 pt): Broader historical context</p>
<p>Evidence (2 pts): Specific historical evidence</p>
<p>Analysis (2 pts): Complex understanding</p>
<h3>Tips</h3>
<p>Choose the prompt you know best. Plan for 5 minutes. Use specific examples, not generalizations.</p>
<p><b>Good luck!</b></p>"""
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
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _refresh(self):
        resp = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)


def make_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


session = make_session()
auth = TimebackAuth(CLIENT_ID, CLIENT_SECRET)

# Load APWH inventory
with open('uworld_apwh_inventory.json') as f:
    by_unit_type = json.load(f)

used_ids = set()


def select_mcqs(test_num):
    selected = []
    for unit, count in MCQ_DISTRIBUTION.items():
        available = [item for item in by_unit_type.get(unit, {}).get('MCQ', []) if item['item_id'] not in used_ids]
        chosen = random.sample(available, min(count, len(available)))
        selected.extend(chosen)
        for item in chosen:
            used_ids.add(item['item_id'])

    # Fill to 55
    remaining = 55 - len(selected)
    for unit in by_unit_type:
        if remaining <= 0:
            break
        if '-' in str(unit):
            continue
        available = [item for item in by_unit_type.get(unit, {}).get('MCQ', []) if item['item_id'] not in used_ids]
        take = min(remaining, len(available))
        if take > 0:
            chosen = random.sample(available, take)
            selected.extend(chosen)
            for item in chosen:
                used_ids.add(item['item_id'])
            remaining -= take

    print(f"  MCQ: {len(selected)}")
    return selected


def select_saqs(test_num):
    selected = []
    all_saqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get('SAQ', []):
            if item['item_id'] not in used_ids:
                all_saqs.append({**item, 'unit': unit})

    chosen = random.sample(all_saqs, min(4, len(all_saqs)))
    for item in chosen:
        used_ids.add(item['item_id'])
        selected.append(item)

    print(f"  SAQ: {len(selected)}")
    return selected


def select_dbq(test_num):
    all_dbqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get('DBQ', []):
            if item['item_id'] not in used_ids:
                all_dbqs.append({**item, 'unit': unit})

    if not all_dbqs:
        print("  DBQ: 0 (none available)")
        return None

    chosen = random.choice(all_dbqs)
    used_ids.add(chosen['item_id'])
    print(f"  DBQ: 1 (Unit {chosen['unit']})")
    return chosen


def select_leqs(test_num):
    selected = []
    all_leqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get('LEQ', []):
            if item['item_id'] not in used_ids:
                all_leqs.append({**item, 'unit': unit})

    # Take 2 LEQs
    chosen = random.sample(all_leqs, min(2, len(all_leqs)))
    for item in chosen:
        used_ids.add(item['item_id'])
        selected.append(item)
        print(f"  LEQ: Unit {item['unit']}")

    return selected


def create_course(course_id, title, course_code):
    payload = {
        "course": {
            "sourcedId": course_id,
            "status": "active",
            "title": title,
            "courseCode": course_code,
            "grades": ["10", "11", "12"],
            "subjects": ["History", "Social Studies"],
            "subjectCodes": [],
            "org": {"sourcedId": ORG_SOURCED_ID},
            "level": "AP",
            "metadata": {
                "publishStatus": "testing",
                "goals": {"dailyXp": 25, "dailyLessons": 1, "dailyAccuracy": 80, "dailyActiveMinutes": 25, "dailyMasteredUnits": 2}
            }
        }
    }
    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses", headers=auth.get_headers(), json=payload, timeout=30)
    ok = resp.status_code in (200, 201, 409)
    print(f"  Course {course_code}: {'OK' if ok else 'FAIL ' + str(resp.status_code)}")
    return course_id if ok else None


def create_test(test_id, title, item_ids):
    payload = {
        "identifier": test_id,
        "title": title,
        "qti-test-part": [{
            "identifier": "main_part",
            "navigationMode": "linear",
            "submissionMode": "individual",
            "qti-assessment-section": [{
                "identifier": "main_section",
                "title": title,
                "visible": True, "required": True, "fixed": False, "sequence": 1,
                "qti-assessment-item-ref": [{"identifier": iid, "href": f"{iid}.xml"} for iid in item_ids]
            }]
        }],
        "qti-outcome-declaration": [{"identifier": "SCORE", "cardinality": "single", "baseType": "float"}]
    }
    resp = session.post(f"{QTI_BASE}/assessment-tests", headers=auth.get_headers(), json=payload, timeout=30)
    ok = resp.status_code in (200, 201, 409)
    print(f"    Test {test_id}: {'OK' if ok else 'FAIL ' + str(resp.status_code)}")
    return test_id if ok else None


def create_component(comp_id, title, course_id, sort_order):
    payload = {
        "courseComponent": {
            "sourcedId": comp_id, "status": "active", "title": title, "sortOrder": sort_order,
            "courseSourcedId": course_id, "course": {"sourcedId": course_id},
            "parent": None, "prerequisites": [], "prerequisiteCriteria": "ALL", "metadata": {}
        }
    }
    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/components", headers=auth.get_headers(), json=payload, timeout=30)
    return comp_id if resp.status_code in (200, 201, 409) else None


def create_resource(res_id, title, test_id, is_article=False):
    if is_article:
        metadata = {
            "type": "qti", "subType": "qti-stimulus", "language": "en-US",
            "lessonType": "alpha-read-article", "assessmentType": "alpha-read",
            "allowRetake": True, "displayType": "interactive", "showResults": True,
            "url": f"{QTI_BASE}/stimuli/{test_id}", "xp": 0
        }
        lesson_type = "alpha-read-article"
    else:
        metadata = {
            "type": "qti", "subType": "qti-test", "questionType": "custom", "language": "en-US",
            "lessonType": "quiz", "assessmentType": "quiz", "allowRetake": True,
            "displayType": "interactive", "showResults": True,
            "url": f"{QTI_BASE}/assessment-tests/{test_id}", "xp": 100
        }
        lesson_type = "quiz"

    payload = {
        "resource": {
            "sourcedId": res_id, "status": "active", "title": title,
            "metadata": metadata,
            "roles": ["primary"], "importance": "primary",
            "vendorResourceId": test_id, "vendorId": "alpha-incept", "applicationId": "incept"
        }
    }
    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/resources/v1p2/resources/", headers=auth.get_headers(), json=payload, timeout=30)
    return res_id if resp.status_code in (200, 201, 409) else None


def link_resource(cr_id, title, comp_id, res_id, sort_order, is_article=False):
    payload = {
        "componentResource": {
            "sourcedId": cr_id, "status": "active", "title": title, "sortOrder": sort_order,
            "courseComponent": {"sourcedId": comp_id}, "resource": {"sourcedId": res_id},
            "lessonType": "alpha-read-article" if is_article else "quiz"
        }
    }
    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/component-resources", headers=auth.get_headers(), json=payload, timeout=30)
    return cr_id if resp.status_code in (200, 201, 409) else None


def create_stimulus(stim_id, title, content):
    payload = {"identifier": stim_id, "title": title, "content": content}
    resp = session.post(f"{QTI_BASE}/stimuli", headers=auth.get_headers(), json=payload, timeout=30)
    return stim_id if resp.status_code in (200, 201, 409) else None


results = []

for test_num in [1, 2]:
    print(f"\n{'='*60}")
    print(f"BUILDING APWH PRACTICE TEST {test_num}")
    print(f"{'='*60}")

    uid = uuid.uuid4().hex[:8]
    course_id = f"APWH-PT{test_num}-2026-{uid}"
    course_code = f"APWH-PT{test_num}-2026"
    course_title = f"APWH Practice Test {test_num} 2026"

    # Select items
    print("\nSelecting items...")
    mcqs = select_mcqs(test_num)
    saqs = select_saqs(test_num)
    dbq = select_dbq(test_num)
    leqs = select_leqs(test_num)

    # Create course
    print("\nCreating course...")
    create_course(course_id, course_title, course_code)

    # Sections
    sections = [
        ("sec1a", "Section I Part A: Multiple Choice (55 questions, 55 min)", "mcq", [m["item_id"] for m in mcqs]),
        ("sec1b", "Section I Part B: Short Answer (4 questions, 40 min)", "saq", [s["item_id"] for s in saqs]),
        ("sec2a", "Section II Part A: Document-Based Question (60 min)", "dbq", [dbq["item_id"]] if dbq else []),
        ("sec2b", "Section II Part B: Long Essay (choose 1 of 2, 40 min)", "leq", [l["item_id"] for l in leqs]),
    ]

    print("\nCreating sections...")
    comp_ids = {}
    for i, (sec_key, sec_title, test_type, item_ids) in enumerate(sections, 1):
        if not item_ids:
            continue

        comp_id = f"apwh-pt{test_num}-{sec_key}-{uid}"
        test_id = f"apwh-pt{test_num}-{test_type}-{uid}"
        res_id = f"apwh-pt{test_num}-{test_type}-res-{uid}"
        cr_id = f"apwh-pt{test_num}-{test_type}-cr-{uid}"

        comp_ids[sec_key] = comp_id

        create_component(comp_id, sec_title, course_id, i)
        create_test(test_id, f"PT{test_num} {test_type.upper()}", item_ids)
        create_resource(res_id, sec_title, test_id)
        link_resource(cr_id, sec_title, comp_id, res_id, 1)

    # Add instruction pages
    print("\nAdding instruction pages...")
    for sec_key, instr in INSTRUCTIONS.items():
        if sec_key not in comp_ids:
            continue
        stim_id = f"apwh-pt{test_num}-{sec_key}-instr-{uid}"
        res_id = f"apwh-pt{test_num}-{sec_key}-instr-res-{uid}"
        cr_id = f"apwh-pt{test_num}-{sec_key}-instr-cr-{uid}"

        create_stimulus(stim_id, instr["title"], instr["content"])
        create_resource(res_id, instr["title"], stim_id, is_article=True)
        link_resource(cr_id, instr["title"], comp_ids[sec_key], res_id, 0, is_article=True)

    results.append({
        "test_num": test_num,
        "course_id": course_id,
        "course_code": course_code,
        "course_title": course_title,
        "mcq": len(mcqs),
        "saq": len(saqs),
        "dbq": 1 if dbq else 0,
        "leq": len(leqs)
    })

print("\n" + "=" * 60)
print("COMPLETE!")
print("=" * 60)

for r in results:
    print(f"\n{r['course_title']}")
    print(f"  Course ID: {r['course_id']}")
    print(f"  Course Code: {r['course_code']}")
    print(f"  MCQ: {r['mcq']}, SAQ: {r['saq']}, DBQ: {r['dbq']}, LEQ: {r['leq']}")

# Save results
with open('apwh_practice_tests_built.json', 'w') as f:
    json.dump(results, f, indent=2)

# Update CSV
print("\nUpdating CSV...")
with open('apush_practice_tests.csv', 'r') as f:
    existing = f.read()

with open('apush_practice_tests.csv', 'w') as f:
    # Rename to generic name
    f.write("Test Name,Course Title,Course Code,Course ID\n")
    # Keep APUSH entries
    for line in existing.strip().split('\n')[1:]:
        f.write(line + '\n')
    # Add APWH entries
    for r in results:
        f.write(f"APWH Practice Test {r['test_num']},{r['course_title']},{r['course_code']},{r['course_id']}\n")

print("CSV updated: apush_practice_tests.csv")
