#!/usr/bin/env python3
"""
Build 2 APUSH Practice Tests on Timeback

Creates two full-length practice exams following the APUSH exam recipe:
- Section I Part A: 55 MCQ (distributed by unit per CED)
- Section I Part B: 4 SAQ (Q1 secondary, Q2 primary, Q3/Q4 choice)
- Section II Part A: 1 DBQ
- Section II Part B: 3 LEQ options (Units 1-3, 4-6, 7-9)

Source: UWorld Scraping course (c123913d-00ac-44f2-97c7-d73830e4d911)
"""

import os
import json
import uuid
import random
import requests
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

# === API Setup ===
QTI_BASE = "https://qti.alpha-1edtech.ai/api"
ONEROSTER_BASE = "https://api.alpha-1edtech.ai"
TOKEN_URL = "https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token"
ORG_SOURCED_ID = "346488d3-efb9-4f56-95ea-f4a441de2370"

# === MCQ Distribution (55 questions) ===
# Based on CED percentages: U1/U9 4-6%, U2 6-8%, U3-U8 10-17%
MCQ_DISTRIBUTION = {
    '1': 3,   # 5.5% (target 4-6%)
    '2': 4,   # 7.3% (target 6-8%)
    '3': 7,   # 12.7% (target 10-17%)
    '4': 7,   # 12.7% (target 10-17%)
    '5': 7,   # 12.7% (target 10-17%)
    '6': 7,   # 12.7% (target 10-17%)
    '7': 7,   # 12.7% (target 10-17%)
    '8': 7,   # 12.7% (target 10-17%)
    '9': 3,   # 5.5% (target 4-6%)
    # Remaining 3 come from cross-unit pools
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
        resp = requests.post(TOKEN_URL, headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)

def make_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session

def make_id(prefix="apush-pt"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def load_inventory():
    """Load item inventory from UWorld course."""
    with open('uworld_items_refined.json') as f:
        data = json.load(f)
    return data['by_unit_type'], data['raw']


def select_mcqs(by_unit_type, test_num, used_ids):
    """Select 55 MCQs following CED distribution."""
    selected = []

    for unit, count in MCQ_DISTRIBUTION.items():
        available = [item for item in by_unit_type.get(unit, {}).get('MCQ', [])
                     if item['item_id'] not in used_ids]
        if len(available) < count:
            print(f"  WARNING: Unit {unit} only has {len(available)} MCQs available, need {count}")
            count = len(available)

        chosen = random.sample(available, count)
        selected.extend(chosen)
        for item in chosen:
            used_ids.add(item['item_id'])

    # Fill remaining from cross-unit pools
    remaining = 55 - len(selected)
    if remaining > 0:
        cross_unit_pools = ['1-4', '5-7', '8-9']
        for pool in cross_unit_pools:
            if remaining <= 0:
                break
            available = [item for item in by_unit_type.get(pool, {}).get('MCQ', [])
                         if item['item_id'] not in used_ids]
            take = min(remaining, len(available))
            if take > 0:
                chosen = random.sample(available, take)
                selected.extend(chosen)
                for item in chosen:
                    used_ids.add(item['item_id'])
                remaining -= take

    print(f"  Test {test_num}: Selected {len(selected)} MCQs")
    return selected


def select_saqs(by_unit_type, test_num, used_ids):
    """Select 4 SAQs: mix of units, pre/post 1900."""
    selected = []

    # Get all available SAQs across units
    all_saqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get('SAQ', []):
            if item['item_id'] not in used_ids:
                all_saqs.append({**item, 'unit': unit})

    # Try to get variety: 2 from pre-1900 (U1-5), 2 from post-1900 (U6-9)
    pre_1900 = [s for s in all_saqs if s['unit'] in ['1', '2', '3', '4', '5']]
    post_1900 = [s for s in all_saqs if s['unit'] in ['6', '7', '8', '9']]

    # Select 2 from each era if possible
    chosen_pre = random.sample(pre_1900, min(2, len(pre_1900)))
    for item in chosen_pre:
        used_ids.add(item['item_id'])

    chosen_post = random.sample(post_1900, min(2, len(post_1900)))
    for item in chosen_post:
        used_ids.add(item['item_id'])

    selected = chosen_pre + chosen_post

    # If we need more, take from whatever's left
    while len(selected) < 4:
        remaining = [s for s in all_saqs if s['item_id'] not in used_ids]
        if not remaining:
            break
        item = random.choice(remaining)
        selected.append(item)
        used_ids.add(item['item_id'])

    print(f"  Test {test_num}: Selected {len(selected)} SAQs")
    return selected


def select_dbq(by_unit_type, test_num, used_ids):
    """Select 1 DBQ."""
    all_dbqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get('DBQ', []):
            if item['item_id'] not in used_ids:
                all_dbqs.append({**item, 'unit': unit})

    if not all_dbqs:
        print(f"  WARNING: No DBQs available for Test {test_num}")
        return None

    chosen = random.choice(all_dbqs)
    used_ids.add(chosen['item_id'])
    print(f"  Test {test_num}: Selected 1 DBQ from Unit {chosen['unit']}")
    return chosen


def select_leqs(by_unit_type, test_num, used_ids):
    """Select 3 LEQs from different period bands: U1-3, U4-6, U7-9."""
    selected = []

    bands = [
        (['1', '2', '3'], 'Units 1-3'),
        (['4', '5', '6'], 'Units 4-6'),
        (['7', '8', '9'], 'Units 7-9'),
    ]

    for units, band_name in bands:
        available = []
        for unit in units:
            for item in by_unit_type.get(unit, {}).get('LEQ', []):
                if item['item_id'] not in used_ids:
                    available.append({**item, 'unit': unit})

        if available:
            chosen = random.choice(available)
            selected.append(chosen)
            used_ids.add(chosen['item_id'])
            print(f"  Test {test_num}: Selected LEQ for {band_name} from Unit {chosen['unit']}")
        else:
            print(f"  WARNING: No LEQ available for {band_name}")

    return selected


def create_assessment_test(session, auth, test_id, title, item_ids):
    """Create a QTI assessment test containing the given items."""
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
                "visible": True,
                "required": True,
                "fixed": False,
                "sequence": 1,
                "qti-assessment-item-ref": [
                    {"identifier": iid, "href": f"{iid}.xml"} for iid in item_ids
                ]
            }]
        }],
        "qti-outcome-declaration": [{"identifier": "SCORE", "cardinality": "single", "baseType": "float"}]
    }

    resp = session.post(f"{QTI_BASE}/assessment-tests", headers=auth.get_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201, 409):
        print(f"    Created test: {test_id} ({len(item_ids)} items)")
        return test_id
    else:
        print(f"    FAILED to create test {test_id}: {resp.status_code} - {resp.text[:200]}")
        return None


def create_course(session, auth, course_id, title, course_code):
    """Create a new course on OneRoster."""
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
                "goals": {
                    "dailyXp": 25,
                    "dailyLessons": 1,
                    "dailyAccuracy": 80,
                    "dailyActiveMinutes": 25,
                    "dailyMasteredUnits": 2
                }
            }
        }
    }

    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses",
                        headers=auth.get_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201, 409):
        print(f"  Created course: {title} ({course_id})")
        return course_id
    else:
        print(f"  FAILED to create course: {resp.status_code} - {resp.text[:200]}")
        return None


def create_component(session, auth, comp_id, title, course_id, sort_order, parent_id=None):
    """Create a course component (unit/section)."""
    payload = {
        "courseComponent": {
            "sourcedId": comp_id,
            "status": "active",
            "title": title,
            "sortOrder": sort_order,
            "courseSourcedId": course_id,
            "course": {"sourcedId": course_id},
            "parent": {"sourcedId": parent_id} if parent_id else None,
            "prerequisites": [],
            "prerequisiteCriteria": "ALL",
            "metadata": {}
        }
    }

    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/components",
                        headers=auth.get_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201, 409):
        return comp_id
    else:
        print(f"    FAILED to create component {comp_id}: {resp.status_code}")
        return None


def create_resource(session, auth, res_id, title, test_id):
    """Create a resource pointing to a QTI test."""
    payload = {
        "resource": {
            "sourcedId": res_id,
            "status": "active",
            "title": title,
            "metadata": {
                "type": "qti",
                "subType": "qti-test",
                "questionType": "custom",
                "language": "en-US",
                "lessonType": "quiz",
                "assessmentType": "quiz",
                "allowRetake": True,
                "displayType": "interactive",
                "showResults": True,
                "url": f"{QTI_BASE}/assessment-tests/{test_id}",
                "xp": 100
            },
            "roles": ["primary"],
            "importance": "primary",
            "vendorResourceId": test_id,
            "vendorId": "alpha-incept",
            "applicationId": "incept"
        }
    }

    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/resources/v1p2/resources/",
                        headers=auth.get_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201, 409):
        return res_id
    else:
        print(f"    FAILED to create resource {res_id}: {resp.status_code}")
        return None


def link_resource_to_component(session, auth, cr_id, title, comp_id, res_id, sort_order):
    """Link a resource to a component."""
    payload = {
        "componentResource": {
            "sourcedId": cr_id,
            "status": "active",
            "title": title,
            "sortOrder": sort_order,
            "courseComponent": {"sourcedId": comp_id},
            "resource": {"sourcedId": res_id},
            "lessonType": "quiz"
        }
    }

    resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/component-resources",
                        headers=auth.get_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201, 409):
        return cr_id
    else:
        print(f"    FAILED to link resource: {resp.status_code}")
        return None


def build_practice_test(session, auth, test_num, by_unit_type, used_ids):
    """Build one complete practice test course."""

    print(f"\n{'='*60}")
    print(f"BUILDING APUSH PRACTICE TEST {test_num}")
    print(f"{'='*60}")

    # Generate IDs
    uid = uuid.uuid4().hex[:8]
    course_id = f"APUSH-PT{test_num}-2026-{uid}"
    course_code = f"APUSH-PT{test_num}-2026"
    course_title = f"APUSH Practice Test {test_num}"

    # Select items
    print("\n--- Selecting Items ---")
    mcqs = select_mcqs(by_unit_type, test_num, used_ids)
    saqs = select_saqs(by_unit_type, test_num, used_ids)
    dbq = select_dbq(by_unit_type, test_num, used_ids)
    leqs = select_leqs(by_unit_type, test_num, used_ids)

    # Create course
    print("\n--- Creating Course ---")
    if not create_course(session, auth, course_id, course_title, course_code):
        return None

    # Create section components and tests
    print("\n--- Creating Sections ---")
    sections = []

    # Section I Part A: MCQ
    mcq_comp_id = f"{course_id}-sec1a"
    create_component(session, auth, mcq_comp_id, "Section I Part A: Multiple Choice (55 questions, 55 min)", course_id, 1)
    mcq_test_id = f"{course_id}-mcq-test"
    mcq_item_ids = [m['item_id'] for m in mcqs]
    create_assessment_test(session, auth, mcq_test_id, f"Practice Test {test_num} - MCQ", mcq_item_ids)
    mcq_res_id = f"{course_id}-mcq-res"
    create_resource(session, auth, mcq_res_id, "Multiple Choice Questions", mcq_test_id)
    link_resource_to_component(session, auth, f"{course_id}-mcq-cr", "Multiple Choice Questions", mcq_comp_id, mcq_res_id, 1)

    # Section I Part B: SAQ
    saq_comp_id = f"{course_id}-sec1b"
    create_component(session, auth, saq_comp_id, "Section I Part B: Short Answer (4 questions, 40 min)", course_id, 2)
    saq_test_id = f"{course_id}-saq-test"
    saq_item_ids = [s['item_id'] for s in saqs]
    create_assessment_test(session, auth, saq_test_id, f"Practice Test {test_num} - SAQ", saq_item_ids)
    saq_res_id = f"{course_id}-saq-res"
    create_resource(session, auth, saq_res_id, "Short Answer Questions", saq_test_id)
    link_resource_to_component(session, auth, f"{course_id}-saq-cr", "Short Answer Questions", saq_comp_id, saq_res_id, 1)

    # Section II Part A: DBQ
    dbq_comp_id = f"{course_id}-sec2a"
    create_component(session, auth, dbq_comp_id, "Section II Part A: Document-Based Question (60 min)", course_id, 3)
    if dbq:
        dbq_test_id = f"{course_id}-dbq-test"
        create_assessment_test(session, auth, dbq_test_id, f"Practice Test {test_num} - DBQ", [dbq['item_id']])
        dbq_res_id = f"{course_id}-dbq-res"
        create_resource(session, auth, dbq_res_id, "Document-Based Question", dbq_test_id)
        link_resource_to_component(session, auth, f"{course_id}-dbq-cr", "Document-Based Question", dbq_comp_id, dbq_res_id, 1)

    # Section II Part B: LEQ
    leq_comp_id = f"{course_id}-sec2b"
    create_component(session, auth, leq_comp_id, "Section II Part B: Long Essay (choose 1 of 3, 40 min)", course_id, 4)
    leq_test_id = f"{course_id}-leq-test"
    leq_item_ids = [l['item_id'] for l in leqs]
    create_assessment_test(session, auth, leq_test_id, f"Practice Test {test_num} - LEQ Options", leq_item_ids)
    leq_res_id = f"{course_id}-leq-res"
    create_resource(session, auth, leq_res_id, "Long Essay Questions (Choose 1)", leq_test_id)
    link_resource_to_component(session, auth, f"{course_id}-leq-cr", "Long Essay Questions (Choose 1)", leq_comp_id, leq_res_id, 1)

    print(f"\n--- COMPLETE ---")
    print(f"Course ID: {course_id}")
    print(f"Course Code: {course_code}")
    print(f"Title: {course_title}")

    return {
        'course_id': course_id,
        'course_code': course_code,
        'title': course_title,
        'mcq_count': len(mcqs),
        'saq_count': len(saqs),
        'dbq_count': 1 if dbq else 0,
        'leq_count': len(leqs)
    }


def main():
    print("="*60)
    print("APUSH Practice Test Builder")
    print("="*60)

    # Setup
    session = make_session()
    auth = TimebackAuth(os.environ['CLIENT_ID'], os.environ['CLIENT_SECRET'])

    # Load inventory
    print("\nLoading item inventory...")
    by_unit_type, raw = load_inventory()

    # Track used items to avoid duplicates across tests
    used_ids = set()

    # Build Test 1
    test1 = build_practice_test(session, auth, 1, by_unit_type, used_ids)

    # Build Test 2
    test2 = build_practice_test(session, auth, 2, by_unit_type, used_ids)

    # Summary
    print("\n" + "="*60)
    print("BUILD COMPLETE")
    print("="*60)

    results = []
    for test in [test1, test2]:
        if test:
            results.append(test)
            print(f"\n{test['title']}")
            print(f"  Course ID: {test['course_id']}")
            print(f"  Course Code: {test['course_code']}")
            print(f"  MCQ: {test['mcq_count']}, SAQ: {test['saq_count']}, DBQ: {test['dbq_count']}, LEQ: {test['leq_count']}")

    # Save results
    with open('apush_practice_tests_built.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to apush_practice_tests_built.json")

    print("\n" + "="*60)
    print("WHERE TO FIND THEM")
    print("="*60)
    print("On Timeback, search for these course codes:")
    for test in results:
        print(f"  - {test['course_code']}")


if __name__ == "__main__":
    main()
