#!/usr/bin/env python3
"""Build APUSH Practice Tests into existing courses."""

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

QTI_BASE = "https://qti.alpha-1edtech.ai/api"
ONEROSTER_BASE = "https://api.alpha-1edtech.ai"
TOKEN_URL = "https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token"

# Pre-created courses
COURSES = {
    1: {"id": "cc78ea76-69d8-4b0a-8dfd-8031b6572770", "title": "APUSH Practice Test 1 2026"},
    2: {"id": "90a8a692-3324-4fe2-9be6-753495e0d9f5", "title": "APUSH Practice Test 2 2026"},
}

MCQ_DISTRIBUTION = {"1": 3, "2": 4, "3": 7, "4": 7, "5": 7, "6": 7, "7": 7, "8": 7, "9": 3}


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
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
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
auth = TimebackAuth(os.environ["CLIENT_ID"], os.environ["CLIENT_SECRET"])

# Load inventory
with open("uworld_items_refined.json") as f:
    data = json.load(f)
by_unit_type = data["by_unit_type"]

used_ids = set()


def select_mcqs(test_num):
    selected = []
    for unit, count in MCQ_DISTRIBUTION.items():
        available = [
            item
            for item in by_unit_type.get(unit, {}).get("MCQ", [])
            if item["item_id"] not in used_ids
        ]
        chosen = random.sample(available, min(count, len(available)))
        selected.extend(chosen)
        for item in chosen:
            used_ids.add(item["item_id"])

    # Fill to 55 from cross-unit pools
    remaining = 55 - len(selected)
    for pool in ["1-4", "5-7", "8-9"]:
        if remaining <= 0:
            break
        available = [
            item
            for item in by_unit_type.get(pool, {}).get("MCQ", [])
            if item["item_id"] not in used_ids
        ]
        take = min(remaining, len(available))
        if take > 0:
            chosen = random.sample(available, take)
            selected.extend(chosen)
            for item in chosen:
                used_ids.add(item["item_id"])
            remaining -= take
    return selected


def select_saqs(test_num):
    selected = []
    all_saqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get("SAQ", []):
            if item["item_id"] not in used_ids:
                all_saqs.append({**item, "unit": unit})

    pre_1900 = [s for s in all_saqs if s["unit"] in ["1", "2", "3", "4", "5"]]
    post_1900 = [s for s in all_saqs if s["unit"] in ["6", "7", "8", "9"]]

    for pool in [pre_1900, post_1900]:
        chosen = random.sample(pool, min(2, len(pool)))
        for item in chosen:
            used_ids.add(item["item_id"])
        selected.extend(chosen)

    while len(selected) < 4:
        remaining = [s for s in all_saqs if s["item_id"] not in used_ids]
        if not remaining:
            break
        item = random.choice(remaining)
        selected.append(item)
        used_ids.add(item["item_id"])
    return selected


def select_dbq(test_num):
    all_dbqs = []
    for unit in by_unit_type:
        for item in by_unit_type[unit].get("DBQ", []):
            if item["item_id"] not in used_ids:
                all_dbqs.append({**item, "unit": unit})
    if not all_dbqs:
        return None
    chosen = random.choice(all_dbqs)
    used_ids.add(chosen["item_id"])
    return chosen


def select_leqs(test_num):
    selected = []
    bands = [
        (["1", "2", "3"], "Units 1-3"),
        (["4", "5", "6"], "Units 4-6"),
        (["7", "8", "9"], "Units 7-9"),
    ]
    for units, band_name in bands:
        available = []
        for unit in units:
            for item in by_unit_type.get(unit, {}).get("LEQ", []):
                if item["item_id"] not in used_ids:
                    available.append({**item, "unit": unit})
        if available:
            chosen = random.choice(available)
            selected.append(chosen)
            used_ids.add(chosen["item_id"])
            print(f"    LEQ {band_name}: Unit {chosen['unit']}")
    return selected


def create_test(test_id, title, item_ids):
    payload = {
        "identifier": test_id,
        "title": title,
        "qti-test-part": [
            {
                "identifier": "main_part",
                "navigationMode": "linear",
                "submissionMode": "individual",
                "qti-assessment-section": [
                    {
                        "identifier": "main_section",
                        "title": title,
                        "visible": True,
                        "required": True,
                        "fixed": False,
                        "sequence": 1,
                        "qti-assessment-item-ref": [
                            {"identifier": iid, "href": f"{iid}.xml"} for iid in item_ids
                        ],
                    }
                ],
            }
        ],
        "qti-outcome-declaration": [
            {"identifier": "SCORE", "cardinality": "single", "baseType": "float"}
        ],
    }
    resp = session.post(
        f"{QTI_BASE}/assessment-tests", headers=auth.get_headers(), json=payload, timeout=30
    )
    if resp.status_code in (200, 201, 409):
        print(f"    Created test: {test_id} ({len(item_ids)} items)")
        return test_id
    else:
        print(f"    FAILED test {test_id}: {resp.status_code} - {resp.text[:200]}")
        return None


def create_component(comp_id, title, course_id, sort_order):
    payload = {
        "courseComponent": {
            "sourcedId": comp_id,
            "status": "active",
            "title": title,
            "sortOrder": sort_order,
            "courseSourcedId": course_id,
            "course": {"sourcedId": course_id},
            "parent": None,
            "prerequisites": [],
            "prerequisiteCriteria": "ALL",
            "metadata": {},
        }
    }
    resp = session.post(
        f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/components",
        headers=auth.get_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201, 409):
        print(f"    Created component: {title}")
        return comp_id
    else:
        print(f"    FAILED component {comp_id}: {resp.status_code} - {resp.text[:200]}")
        return None


def create_resource(res_id, title, test_id):
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
                "xp": 100,
            },
            "roles": ["primary"],
            "importance": "primary",
            "vendorResourceId": test_id,
            "vendorId": "alpha-incept",
            "applicationId": "incept",
        }
    }
    resp = session.post(
        f"{ONEROSTER_BASE}/ims/oneroster/resources/v1p2/resources/",
        headers=auth.get_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201, 409):
        print(f"    Created resource: {res_id}")
        return res_id
    else:
        print(f"    FAILED resource {res_id}: {resp.status_code} - {resp.text[:200]}")
        return None


def link_resource(cr_id, title, comp_id, res_id, sort_order):
    payload = {
        "componentResource": {
            "sourcedId": cr_id,
            "status": "active",
            "title": title,
            "sortOrder": sort_order,
            "courseComponent": {"sourcedId": comp_id},
            "resource": {"sourcedId": res_id},
            "lessonType": "quiz",
        }
    }
    resp = session.post(
        f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/component-resources",
        headers=auth.get_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201, 409):
        print(f"    Linked resource to component")
        return cr_id
    else:
        print(f"    FAILED link {cr_id}: {resp.status_code} - {resp.text[:200]}")
        return None


def main():
    results = []

    for test_num in [1, 2]:
        print(f"\n{'='*60}")
        print(f"BUILDING TEST {test_num}")
        print(f"{'='*60}")

        course_id = COURSES[test_num]["id"]
        uid = uuid.uuid4().hex[:8]

        # Select items
        print("\nSelecting items...")
        mcqs = select_mcqs(test_num)
        print(f"  MCQ: {len(mcqs)}")
        saqs = select_saqs(test_num)
        print(f"  SAQ: {len(saqs)}")
        dbq = select_dbq(test_num)
        print(f"  DBQ: 1" if dbq else "  DBQ: 0")
        print("  LEQ:")
        leqs = select_leqs(test_num)

        # Create tests and link to course
        print("\nCreating tests and linking...")

        sections = [
            (
                "sec1a",
                "Section I Part A: Multiple Choice (55 questions, 55 min)",
                "mcq",
                [m["item_id"] for m in mcqs],
            ),
            (
                "sec1b",
                "Section I Part B: Short Answer (4 questions, 40 min)",
                "saq",
                [s["item_id"] for s in saqs],
            ),
            (
                "sec2a",
                "Section II Part A: Document-Based Question (60 min)",
                "dbq",
                [dbq["item_id"]] if dbq else [],
            ),
            (
                "sec2b",
                "Section II Part B: Long Essay (choose 1 of 3, 40 min)",
                "leq",
                [l["item_id"] for l in leqs],
            ),
        ]

        for i, (sec_key, sec_title, test_type, item_ids) in enumerate(sections, 1):
            if not item_ids:
                continue
            comp_id = f"apush-pt{test_num}-{sec_key}-{uid}"
            test_id = f"apush-pt{test_num}-{test_type}-{uid}"
            res_id = f"apush-pt{test_num}-{test_type}-res-{uid}"
            cr_id = f"apush-pt{test_num}-{test_type}-cr-{uid}"

            create_component(comp_id, sec_title, course_id, i)
            create_test(test_id, f"PT{test_num} {test_type.upper()}", item_ids)
            create_resource(res_id, sec_title, test_id)
            link_resource(cr_id, sec_title, comp_id, res_id, 1)

        results.append(
            {
                "test_num": test_num,
                "course_id": course_id,
                "course_title": COURSES[test_num]["title"],
                "mcq": len(mcqs),
                "saq": len(saqs),
                "dbq": 1 if dbq else 0,
                "leq": len(leqs),
            }
        )

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    for r in results:
        print(f"\nTest {r['test_num']}: {r['course_title']}")
        print(f"  Course ID: {r['course_id']}")
        print(f"  MCQ: {r['mcq']}, SAQ: {r['saq']}, DBQ: {r['dbq']}, LEQ: {r['leq']}")

    with open("apush_practice_tests_built.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to apush_practice_tests_built.json")


if __name__ == "__main__":
    main()
