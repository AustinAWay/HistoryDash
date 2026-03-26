# Timeback API Guide for Claude Code Users

> **Audience**: Non-technical team members using Claude Code to create and manage AP course content on Timeback.
>
> **Last updated**: 2026-03-25

---

## Quick Start: End-to-End Course Creation Checklist

If you have content ready and want to publish a course, follow this sequence exactly. Each step references the detailed section below.

```
PHASE 1: SETUP
  □ Get credentials (Section 2)
  □ Set TIMEBACK_CLIENT_ID and TIMEBACK_CLIENT_SECRET in .env
  □ pip install requests python-dotenv
  □ Copy the auth code from Section 2 into your script

PHASE 2: CREATE CONTENT (QTI API — all items exist independently)
  □ Create articles/stimuli for reading passages (Section 3)
     → Save each stimulus_id (you'll link them to items)
  □ Create MCQ items (Section 4)
     → Include stimulusRef if the MCQ references an article
     → Save each item_id
  □ Create FRQ items (Section 5)
     → Include grader URL if auto-scored
     → Save each item_id

PHASE 3: GROUP INTO TESTS (QTI API — tests are containers of items)
  □ Group your item_ids by topic/unit
  □ Create assessment tests — one per quiz/exam (Section 6)
     → A "Topic 1.1 Quiz" test might contain 10 MCQ item_ids
     → A "Unit 1 Exam" test might contain 30 item_ids
     → Save each test_id

PHASE 4: BUILD COURSE STRUCTURE (OneRoster API — the skeleton)
  □ Create the course (Section 8, Step 3)
     → Save the course_id
  □ Create unit components (Section 8, Step 4)
     → parent: null (top-level)
     → Save each unit_component_id
  □ Create topic components nested under units (Section 8, Step 4)
     → parent: the unit_component_id
     → Save each topic_component_id

PHASE 5: LINK CONTENT TO STRUCTURE (OneRoster API — wiring it together)
  For each test:
  □ Create a resource pointing to the QTI test (Section 8, Step 5a)
     → Set lessonType: "quiz", subType: "qti-test"
     → Save each resource_id
  □ Create a component-resource linking the resource to a topic (Section 8, Step 5b)
     → Set lessonType: "quiz" (must match the resource)

  For each article:
  □ Create a resource pointing to the QTI stimulus (Section 8, Step 5a)
     → Set lessonType: "alpha-read-article", subType: "qti-stimulus"
  □ Create a component-resource linking it to a topic (Section 8, Step 5b)
     → Set lessonType: "alpha-read-article"

PHASE 6: VERIFY
  □ Fetch the syllabus and check the structure (Section 13)
  □ Spot-check a few items via GET (Section 9)
```

### Expected Input Format

If you're feeding content to a Claude Code agent, structure your MCQs like this (JSON or CSV):

```json
{
  "topic": "3.1",
  "stem": "Which of the following best describes the role of ATP?",
  "choices": {"A": "Stores genetic information", "B": "Primary energy currency", "C": "Catalyzes reactions", "D": "Transports oxygen"},
  "correct": "B",
  "explanation": "ATP is the primary energy currency of the cell...",
  "difficulty": "medium",
  "ek": "3.1.A.1"
}
```

FRQs:
```json
{
  "topic": "3.1",
  "prompt": "Describe the process of cellular respiration...",
  "model_answer": "Cellular respiration consists of three stages...",
  "rubric": "3 points: Names all three stages. 2 points: Correct ATP yield...",
  "difficulty": "hard",
  "frq_type": "long"
}
```

Articles:
```json
{
  "topic": "3.1",
  "title": "Cellular Respiration Overview",
  "body_html": "<p>Cellular respiration is the process...</p>"
}
```

### Ordering Rules

- **Items before tests** — you need item_ids to create a test
- **Tests before resources** — you need test_ids to create resources
- **Course before components** — you need course_id to create components
- **Components before component-resources** — you need component_ids to link resources
- **Articles can be created anytime** — but create them before the MCQs that reference them (you need the stimulus_id for `stimulusRef`)

### Constants & Conventions (For Agents)

These values are always the same across all courses:

```python
import uuid

# API base URLs
QTI_BASE = "https://qti.alpha-1edtech.ai/api"
ONEROSTER_BASE = "https://api.alpha-1edtech.ai"

# Organization ID (always this value for Incept courses)
ORG_SOURCED_ID = "346488d3-efb9-4f56-95ea-f4a441de2370"

# Generating identifiers
def make_id(prefix="s4"):          return f"{prefix}-{uuid.uuid4().hex[:12]}"
def make_stim_id():                return f"s4-stim-{uuid.uuid4().hex[:12]}"
def make_test_id(slug):            return f"s4-test-{slug}-{uuid.uuid4().hex[:8]}"
def make_comp_id(slug):            return f"s4-comp-{slug}-{uuid.uuid4().hex[:8]}"
def make_res_id(slug):             return f"s4-res-{slug}-{uuid.uuid4().hex[:8]}"
def make_cr_id(slug):              return f"s4-cr-{slug}-{uuid.uuid4().hex[:8]}"
```

**Status codes to handle**:
- `200` or `201` = success
- `409` = already exists (treat as success for idempotent retries)
- `401` = token expired (auth class auto-refreshes, but if you see this, re-call `auth.get_headers()`)
- `429` = rate limited (the `make_session()` retry logic handles this automatically)

**JSON POST is safe for**: `choice`, `extended-text`, `order`, `text-entry`.
**Use XML format for everything else** (hotspot, gap-match, hottext, etc.) — see Section 12.

---

## Table of Contents

1. [Overview: How Timeback Works](#1-overview-how-timeback-works)
2. [Authentication](#2-authentication)
3. [Creating an Article (Stimulus)](#3-creating-an-article-stimulus)
4. [Creating an MCQ (Multiple Choice Question)](#4-creating-an-mcq)
5. [Creating an FRQ (Free Response Question)](#5-creating-an-frq)
6. [Creating a Quiz / Assessment Test](#6-creating-a-quiz--assessment-test)
7. [Creating a PP100 Exercise](#7-creating-a-pp100-exercise)
8. [Building a Course Structure](#8-building-a-course-structure)
9. [Getting an Item](#9-getting-an-item)
10. [Updating an Item](#10-updating-an-item)
11. [Updating Metadata Only](#11-updating-metadata-only)
12. [Updating via Raw XML](#12-updating-via-raw-xml)
13. [Fetching a Full Course (Syllabus Pull)](#13-fetching-a-full-course-syllabus-pull)
14. [Getting All Items in a Course (The 3-Hop Chain)](#14-getting-all-items-in-a-course-the-3-hop-chain)
15. [Lesson Types Reference](#15-lesson-types-reference)
16. [Gotchas and Hard-Won Lessons](#16-gotchas-and-hard-won-lessons)
17. [Quick Reference: Endpoints](#17-quick-reference-endpoints)

---

## 1. Overview: How Timeback Works

Timeback is built on **three layers of APIs**:

| Layer | What it does | Base URL |
|-------|-------------|----------|
| **QTI API** | Stores assessment content (questions, articles, tests) | `https://qti.alpha-1edtech.ai/api` |
| **OneRoster API** | Stores course structure (courses, units, resources, links) | `https://api.alpha-1edtech.ai` |
| **PowerPath API** | Convenience layer that reads from both (for fetching) | `https://api.alpha-1edtech.ai` |

**The mental model**: Content (questions, articles) lives in QTI. Structure (courses, units, what-goes-where) lives in OneRoster. PowerPath lets you read the whole thing as one tree.

### Content Hierarchy

```
Course (OneRoster)
├── Unit 1 (CourseComponent)
│   ├── Topic 1.1 (CourseComponent, parent = Unit 1)
│   │   ├── Article: Topic 1.1 (Resource → Stimulus)
│   │   ├── Video: Topic 1.1 (Resource → external URL)
│   │   └── Quiz: Topic 1.1 (Resource → Assessment Test)
│   │       ├── MCQ Item 1 (Assessment Item)
│   │       ├── MCQ Item 2 (Assessment Item)
│   │       └── FRQ Item 1 (Assessment Item)
│   └── Topic 1.2 ...
├── Unit 2 ...
└── Practice Exam (CourseComponent)
    └── Full Exam (Resource → Assessment Test with 60 items)
```

### API Documentation Links

- QTI API docs: https://qti.alpha-1edtech.ai/scalar/
- OneRoster API docs: https://api.alpha-1edtech.ai/scalar/
- PowerPath API docs: https://api.alpha-1edtech.ai/scalar?api=powerpath-api
- OpenAPI specs: append `/openapi.yaml` to any base URL

---

## 2. Authentication

All Timeback APIs use **OAuth 2.0 client credentials**. You need a `CLIENT_ID` and `CLIENT_SECRET`.

### Getting Credentials

1. Open the [TimeBack Credentials Request Sheet](https://docs.google.com/spreadsheets/d/1Rmawpuot_kmpKwMo1JQRhXKIuCndI_m1-3mnhe9ouEg/edit?gid=0#gid=0)
2. Add your name, email, and app name on the **Production** tab
3. Email `support@reachbeyond.ai` to notify them
4. Credentials arrive via a secure Infisical link

### Environment Setup

Create a `.env` file in your project root:

```
TIMEBACK_CLIENT_ID=your-client-id-here
TIMEBACK_CLIENT_SECRET=your-client-secret-here
```

> **Never commit `.env` to git.** It should already be in `.gitignore`.

### How Authentication Works

```
POST https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET
```

Response:
```json
{
  "access_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

Then use the token in all subsequent requests:
```
Authorization: Bearer eyJ...
Content-Type: application/json
```

**The token expires after 1 hour.** The Python snippet below auto-refreshes it 5 minutes before expiry so you never need to think about it.

### Python: Reusable Auth + Session Setup

Copy this into your script (or into a shared `auth.py` file) — every example in this guide uses it:

```python
import os
import uuid
import requests
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── API base URLs ─────────────────────────────────────────────────
QTI_BASE = "https://qti.alpha-1edtech.ai/api"
ONEROSTER_BASE = "https://api.alpha-1edtech.ai"
TOKEN_URL = "https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token"

# ── Auth (auto-refreshing) ───────────────────────────────────────
class TimebackAuth:
    """OAuth2 client-credentials auth with automatic token refresh."""
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._expires_at = None

    def get_headers(self):
        if not self._token or datetime.now() >= self._expires_at:
            self._refresh()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

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

# ── Session with retry logic ─────────────────────────────────────
def make_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session

# ── Quick setup ──────────────────────────────────────────────────
def get_client():
    """Returns (session, auth) ready for API calls."""
    cid = os.environ["TIMEBACK_CLIENT_ID"]
    csec = os.environ["TIMEBACK_CLIENT_SECRET"]
    return make_session(), TimebackAuth(cid, csec)

# Usage:
# session, auth = get_client()
# resp = session.get(f"{QTI_BASE}/assessment-items/{item_id}", headers=auth.get_headers())
```

> **Setup**: Set `TIMEBACK_CLIENT_ID` and `TIMEBACK_CLIENT_SECRET` as environment variables (or in a `.env` file loaded with `python-dotenv`).

---

## 3. Creating an Article (Stimulus)

Articles are called **stimuli** in QTI. They are standalone HTML content that can be linked to questions.

### Endpoint

```
POST https://qti.alpha-1edtech.ai/api/stimuli
```

### Payload

```json
{
  "identifier": "s4-stim-abc123def456",
  "title": "Cellular Respiration Overview",
  "content": "<p>Cellular respiration is the process by which cells break down glucose...</p>"
}
```

### Field Guide

| Field | Required | Description |
|-------|----------|-------------|
| `identifier` | Yes | Unique ID. Use format `s4-stim-{12 hex chars}`. |
| `title` | Yes | Human-readable title. |
| `content` | Yes | HTML body of the article. Wrap in `<p>` tags. |

### Response

```json
{
  "identifier": "s4-stim-abc123def456",
  "_id": "..."
}
```

Status: `201 Created`

### Python Example

```python
session, auth = get_client()  # see Section 2 for get_client()

identifier = f"s4-stim-{uuid.uuid4().hex[:12]}"
payload = {
    "identifier": identifier,
    "title": "Cellular Respiration Overview",
    "content": "<p>Cellular respiration is the process...</p>",
}

resp = session.post(f"{QTI_BASE}/stimuli", headers=auth.get_headers(), json=payload, timeout=30)
if resp.status_code in (200, 201):
    stim_id = resp.json().get("identifier", identifier)
    print(f"Created stimulus: {stim_id}")
```

---

## 4. Creating an MCQ

MCQs are **choice** type assessment items.

### Endpoint

```
POST https://qti.alpha-1edtech.ai/api/assessment-items
```

### Payload

```json
{
  "identifier": "s4-a1b2c3d4e5f6",
  "title": "Cellular Respiration MCQ 1",
  "type": "choice",
  "interaction": {
    "type": "choice",
    "responseIdentifier": "RESPONSE",
    "shuffle": false,
    "maxChoices": 1,
    "questionStructure": {
      "prompt": "<p>Which of the following best describes the role of ATP in cellular respiration?</p>",
      "choices": [
        {"identifier": "A", "content": "It stores genetic information"},
        {"identifier": "B", "content": "It serves as the primary energy currency of the cell"},
        {"identifier": "C", "content": "It catalyzes enzymatic reactions"},
        {"identifier": "D", "content": "It transports oxygen to tissues"}
      ]
    }
  },
  "responseDeclarations": [
    {
      "identifier": "RESPONSE",
      "cardinality": "single",
      "baseType": "identifier",
      "correctResponse": {"value": ["B"]}
    }
  ],
  "outcomeDeclarations": [
    {"identifier": "FEEDBACK", "cardinality": "single", "baseType": "identifier"},
    {"identifier": "FEEDBACK-INLINE", "cardinality": "single", "baseType": "identifier"}
  ],
  "responseProcessing": {
    "templateType": "match_correct",
    "responseDeclarationIdentifier": "RESPONSE",
    "outcomeIdentifier": "FEEDBACK",
    "correctResponseIdentifier": "CORRECT",
    "incorrectResponseIdentifier": "INCORRECT",
    "inlineFeedback": {
      "outcomeIdentifier": "FEEDBACK-INLINE",
      "variableIdentifier": "RESPONSE"
    }
  },
  "metadata": {
    "topic": "3.1",
    "difficulty": "medium",
    "ek": "3.1.A.1",
    "bloom": "Understand"
  }
}
```

### Linking to an Article (Stimulus)

If the MCQ references a reading passage, add a `stimulusRef` field at the top level:

```json
{
  "stimulusRef": {
    "identifier": "s4-stim-abc123def456-ref",
    "href": "stimuli/s4-stim-abc123def456",
    "title": "Reference Material"
  }
}
```

### Response

```json
{
  "identifier": "s4-a1b2c3d4e5f6",
  "_id": "..."
}
```

Status: `201 Created`

### Python Example

```python
session, auth = get_client()  # see Section 2

identifier = f"s4-{uuid.uuid4().hex[:12]}"
payload = {
    "identifier": identifier,
    "title": "Cellular Respiration MCQ 1",
    "type": "choice",
    "interaction": {
        "type": "choice",
        "responseIdentifier": "RESPONSE",
        "shuffle": False,
        "maxChoices": 1,
        "questionStructure": {
            "prompt": "<p>Which of the following best describes the role of ATP?</p>",
            "choices": [
                {"identifier": "A", "content": "It stores genetic information"},
                {"identifier": "B", "content": "It serves as the primary energy currency of the cell"},
                {"identifier": "C", "content": "It catalyzes enzymatic reactions"},
                {"identifier": "D", "content": "It transports oxygen to tissues"},
            ],
        },
    },
    "responseDeclarations": [
        {"identifier": "RESPONSE", "cardinality": "single", "baseType": "identifier",
         "correctResponse": {"value": ["B"]}}
    ],
    "outcomeDeclarations": [
        {"identifier": "FEEDBACK", "cardinality": "single", "baseType": "identifier"},
        {"identifier": "FEEDBACK-INLINE", "cardinality": "single", "baseType": "identifier"},
    ],
    "responseProcessing": {
        "templateType": "match_correct",
        "responseDeclarationIdentifier": "RESPONSE",
        "outcomeIdentifier": "FEEDBACK",
        "correctResponseIdentifier": "CORRECT",
        "incorrectResponseIdentifier": "INCORRECT",
        "inlineFeedback": {"outcomeIdentifier": "FEEDBACK-INLINE", "variableIdentifier": "RESPONSE"},
    },
    "metadata": {"topic": "3.1", "difficulty": "medium", "ek": "3.1.A.1"},
}

# Optional: link to an article
# payload["stimulusRef"] = {
#     "identifier": "s4-stim-abc123def456-ref",
#     "href": "stimuli/s4-stim-abc123def456",
#     "title": "Reference Material",
# }

resp = session.post(f"{QTI_BASE}/assessment-items", headers=auth.get_headers(), json=payload, timeout=30)
if resp.status_code in (200, 201):
    item_id = resp.json().get("identifier", identifier)
    print(f"Created MCQ: {item_id}")
```

---

## 5. Creating an FRQ

FRQs are **extended-text** type assessment items.

### Endpoint

```
POST https://qti.alpha-1edtech.ai/api/assessment-items
```

### Payload

```json
{
  "identifier": "s4-f1r2q3a4b5c6",
  "title": "Cellular Respiration FRQ",
  "type": "extended-text",
  "interaction": {
    "type": "extended-text",
    "responseIdentifier": "RESPONSE",
    "questionStructure": {
      "prompt": "<p>Describe the process of cellular respiration, including the three main stages and the net ATP yield from one molecule of glucose.</p>"
    }
  },
  "responseDeclarations": [
    {
      "identifier": "RESPONSE",
      "cardinality": "single",
      "baseType": "string"
    }
  ],
  "outcomeDeclarations": [
    {"identifier": "SCORE", "cardinality": "single", "baseType": "float"},
    {"identifier": "FEEDBACK", "cardinality": "single", "baseType": "identifier"}
  ],
  "responseProcessing": {
    "templateType": "match_correct"
  },
  "metadata": {
    "topic": "3.1",
    "difficulty": "hard",
    "modelAnswer": "Cellular respiration consists of three stages: glycolysis, the Krebs cycle, and oxidative phosphorylation...",
    "rubric": "<p><strong>3 points:</strong> Names all three stages. <strong>2 points:</strong> Correct ATP yield (30-32). <strong>1 point:</strong> Location of each stage.</p>"
  }
}
```

### Adding an External Grader (Auto-Scoring)

For FRQs that should be auto-graded by an AI grader, replace `responseProcessing`:

```json
{
  "responseProcessing": {
    "customOperator": {
      "class": "com.alpha-1edtech.ExternalApiScore",
      "definition": "https://your-grader-lambda.lambda-url.us-east-1.on.aws/grade-bio-frq/score"
    }
  }
}
```

### Python Example

```python
session, auth = get_client()  # see Section 2

identifier = f"s4-{uuid.uuid4().hex[:12]}"
payload = {
    "identifier": identifier,
    "title": "Cellular Respiration FRQ",
    "type": "extended-text",
    "interaction": {
        "type": "extended-text",
        "responseIdentifier": "RESPONSE",
        "questionStructure": {
            "prompt": "<p>Describe the process of cellular respiration...</p>",
        },
    },
    "responseDeclarations": [
        {"identifier": "RESPONSE", "cardinality": "single", "baseType": "string"}
    ],
    "outcomeDeclarations": [
        {"identifier": "SCORE", "cardinality": "single", "baseType": "float"},
        {"identifier": "FEEDBACK", "cardinality": "single", "baseType": "identifier"},
    ],
    "responseProcessing": {"templateType": "match_correct"},
    "metadata": {
        "topic": "3.1",
        "difficulty": "hard",
        "modelAnswer": "Cellular respiration consists of three stages...",
        "rubric": "<p><strong>3 points:</strong> Names all three stages...</p>",
    },
}

resp = session.post(f"{QTI_BASE}/assessment-items", headers=auth.get_headers(), json=payload, timeout=30)
if resp.status_code in (200, 201):
    item_id = resp.json().get("identifier", identifier)
    print(f"Created FRQ: {item_id}")
```

---

## 6. Creating a Quiz / Assessment Test

A quiz (assessment test) is a **container** that groups assessment items together. Students see these as a single quiz/exam.

### Endpoint

```
POST https://qti.alpha-1edtech.ai/api/assessment-tests
```

### Payload

```json
{
  "identifier": "s4-test-topic-3-1-quiz-a1b2c3d4",
  "title": "Topic 3.1 Quiz",
  "qti-test-part": [
    {
      "identifier": "main_part",
      "navigationMode": "linear",
      "submissionMode": "individual",
      "qti-assessment-section": [
        {
          "identifier": "main_section",
          "title": "Topic 3.1 Quiz",
          "visible": true,
          "required": true,
          "fixed": false,
          "sequence": 1,
          "qti-assessment-item-ref": [
            {"identifier": "s4-item-001", "href": "s4-item-001.xml"},
            {"identifier": "s4-item-002", "href": "s4-item-002.xml"},
            {"identifier": "s4-item-003", "href": "s4-item-003.xml"}
          ]
        }
      ]
    }
  ],
  "qti-outcome-declaration": [
    {"identifier": "SCORE", "cardinality": "single", "baseType": "float"}
  ]
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `qti-assessment-item-ref` | Array of item references. Each needs `identifier` (the item ID) and `href` (item ID + `.xml`). |
| `navigationMode` | `"linear"` = students go in order. `"nonlinear"` = students can jump around. |
| `submissionMode` | `"individual"` = submit one at a time. `"simultaneous"` = submit all at once. |

### Response

```json
{
  "identifier": "s4-test-topic-3-1-quiz-a1b2c3d4",
  "_id": "..."
}
```

---

## 7. Creating a PP100 Exercise

**PP100 (PowerPath 100)** is not a separate content type — it's a regular quiz/assessment test that's configured with specific metadata to behave as a mastery exercise. The key difference is in **how you create the OneRoster resource** that wraps it.

A PP100 exercise uses `lessonType: "quiz"` and `xp: 100` in the resource metadata. The PowerPath engine handles the adaptive behavior.

See [Section 8: Building a Course Structure](#8-building-a-course-structure) for how to create the resource with the right metadata. The assessment test itself is created exactly like a regular quiz (Section 6).

### PP100 vs Quiz vs Practice Exam

| Type | `lessonType` | `assessmentType` | `xp` | Behavior |
|------|-------------|-------------------|------|----------|
| Topic Quiz | `"quiz"` | `"quiz"` | `100` | Standard quiz, retakeable |
| Article | `"alpha-read-article"` | `"alpha-read"` | `100` | Reading + comprehension |
| Practice Exam | `"quiz"` | `"quiz"` | `100` | Full-length timed exam |

---

## 8. Building a Course Structure

Creating content on Timeback is a **5-step process**. Content (items, tests, articles) lives in QTI. Structure (courses, units, the links between them) lives in OneRoster.

### Step 1: Create Assessment Items

Create your MCQs and FRQs (Sections 4-5).

### Step 2: Create Assessment Tests

Group items into tests/quizzes (Section 6).

### Step 3: Create the Course

```
POST https://api.alpha-1edtech.ai/ims/oneroster/rostering/v1p2/courses
```

```json
{
  "course": {
    "sourcedId": "APBIO-v2-20260305",
    "status": "active",
    "title": "AP Biology",
    "courseCode": "APBIO-v2-20260305",
    "grades": ["10", "11", "12"],
    "subjects": ["Science", "Biology"],
    "subjectCodes": [],
    "org": {"sourcedId": "346488d3-efb9-4f56-95ea-f4a441de2370"},
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
```

> **Note**: `org.sourcedId` is the Alpha org ID. Use the value shown above.

### Step 4: Create Course Components (Units and Topics)

Components are the folders in the course tree. They can be nested (units contain topics).

```
POST https://api.alpha-1edtech.ai/ims/oneroster/rostering/v1p2/courses/components
```

**Creating a Unit:**
```json
{
  "courseComponent": {
    "sourcedId": "apbio-unit-1",
    "status": "active",
    "title": "Unit 1: Chemistry of Life",
    "sortOrder": 1,
    "courseSourcedId": "APBIO-v2-20260305",
    "course": {"sourcedId": "APBIO-v2-20260305"},
    "parent": null,
    "prerequisites": [],
    "prerequisiteCriteria": "ALL",
    "metadata": {}
  }
}
```

**Creating a Topic (nested under a Unit):**
```json
{
  "courseComponent": {
    "sourcedId": "apbio-topic-1-1",
    "status": "active",
    "title": "Topic 1.1: Structure of Water",
    "sortOrder": 1,
    "courseSourcedId": "APBIO-v2-20260305",
    "course": {"sourcedId": "APBIO-v2-20260305"},
    "parent": {"sourcedId": "apbio-unit-1"},
    "prerequisites": [],
    "prerequisiteCriteria": "ALL",
    "metadata": {}
  }
}
```

> The `parent` field is what creates nesting. `null` = top-level (unit). Set to a unit's `sourcedId` = nested under that unit.

### Step 5: Create Resources and Link Them

This is a two-part step. First you create a **resource** (which points to QTI content), then you create a **component-resource** (which links that resource into a specific spot in the course tree).

**5a. Create a Resource:**

```
POST https://api.alpha-1edtech.ai/ims/oneroster/resources/v1p2/resources/
```

```json
{
  "resource": {
    "sourcedId": "apbio-res-quiz-1-1",
    "status": "active",
    "metadata": {
      "type": "qti",
      "subType": "qti-test",
      "questionType": "custom",
      "language": "en-US",
      "lessonType": "quiz",
      "assessmentType": "quiz",
      "allowRetake": true,
      "displayType": "interactive",
      "showResults": true,
      "url": "https://qti.alpha-1edtech.ai/api/assessment-tests/s4-test-topic-1-1-quiz",
      "xp": 100
    },
    "title": "Topic 1.1 Quiz",
    "roles": ["primary"],
    "importance": "primary",
    "vendorResourceId": "s4-test-topic-1-1-quiz",
    "vendorId": "alpha-incept",
    "applicationId": "incept"
  }
}
```

**For articles (stimuli), use this metadata instead:**

```json
{
  "metadata": {
    "type": "qti",
    "subType": "qti-stimulus",
    "language": "en-US",
    "lessonType": "alpha-read-article",
    "assessmentType": "alpha-read",
    "allowRetake": true,
    "displayType": "interactive",
    "showResults": true,
    "url": "https://qti.alpha-1edtech.ai/api/stimuli/s4-stim-abc123",
    "xp": 100
  }
}
```

**For videos:**

```json
{
  "metadata": {
    "type": "video",
    "subType": "qti-stimulus",
    "language": "en-US",
    "lessonType": "alpha-read-article",
    "url": "https://your-video-host.com/video.mp4",
    "xp": 100
  }
}
```

**5b. Link Resource to Component:**

```
POST https://api.alpha-1edtech.ai/ims/oneroster/rostering/v1p2/courses/component-resources
```

```json
{
  "componentResource": {
    "sourcedId": "apbio-cr-quiz-1-1",
    "status": "active",
    "title": "Topic 1.1 Quiz",
    "sortOrder": 1,
    "courseComponent": {"sourcedId": "apbio-topic-1-1"},
    "resource": {"sourcedId": "apbio-res-quiz-1-1"},
    "lessonType": "quiz"
  }
}
```

> **Important**: `lessonType` must be set on BOTH the resource metadata AND the component-resource. If they don't match, rendering can break.

### Python Example: Full Module Creation (All 5 Steps)

This does everything: creates a QTI test, a course component, a resource, and links them together.

```python
session, auth = get_client()  # see Section 2

course_id = "APBIO-v2-20260305"  # your existing course
item_ids = ["s4-item-001", "s4-item-002", "s4-item-003"]  # items to include
uid = uuid.uuid4().hex[:8]

# Step 2: Create the QTI test
test_id = f"s4-test-topic-1-1-quiz-{uid}"
test_payload = {
    "identifier": test_id,
    "title": "Topic 1.1 Quiz",
    "qti-test-part": [{
        "identifier": "main_part",
        "navigationMode": "linear",
        "submissionMode": "individual",
        "qti-assessment-section": [{
            "identifier": "main_section",
            "title": "Topic 1.1 Quiz",
            "visible": True, "required": True, "fixed": False, "sequence": 1,
            "qti-assessment-item-ref": [
                {"identifier": iid, "href": f"{iid}.xml"} for iid in item_ids
            ],
        }],
    }],
    "qti-outcome-declaration": [{"identifier": "SCORE", "cardinality": "single", "baseType": "float"}],
}
resp = session.post(f"{QTI_BASE}/assessment-tests", headers=auth.get_headers(), json=test_payload, timeout=30)
assert resp.status_code in (200, 201), f"Test creation failed: {resp.status_code}"
print(f"Created test: {test_id}")

# Step 4: Create a course component (nested under a unit)
comp_id = f"s4-comp-topic-1-1-quiz-{uid}"
comp_payload = {
    "courseComponent": {
        "sourcedId": comp_id, "status": "active",
        "title": "Topic 1.1 Quiz", "sortOrder": 1,
        "courseSourcedId": course_id,
        "course": {"sourcedId": course_id},
        "parent": {"sourcedId": "apbio-unit-1"},  # nest under unit
        "prerequisites": [], "prerequisiteCriteria": "ALL", "metadata": {},
    }
}
resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/components",
                    headers=auth.get_headers(), json=comp_payload, timeout=30)
assert resp.status_code in (200, 201), f"Component creation failed: {resp.status_code}"

# Step 5a: Create a resource pointing to the test
res_id = f"s4-res-topic-1-1-quiz-{uid}"
res_payload = {
    "resource": {
        "sourcedId": res_id, "status": "active",
        "title": "Topic 1.1 Quiz",
        "metadata": {
            "type": "qti", "subType": "qti-test", "lessonType": "quiz",
            "assessmentType": "quiz", "questionType": "custom", "language": "en-US",
            "allowRetake": True, "displayType": "interactive", "showResults": True,
            "url": f"{QTI_BASE}/assessment-tests/{test_id}", "xp": 100,
        },
        "vendorResourceId": test_id, "vendorId": "alpha-incept", "applicationId": "incept",
    }
}
resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/resources/v1p2/resources/",
                    headers=auth.get_headers(), json=res_payload, timeout=30)
assert resp.status_code in (200, 201), f"Resource creation failed: {resp.status_code}"

# Step 5b: Link resource to component
cr_id = f"s4-cr-topic-1-1-quiz-{uid}"
cr_payload = {
    "componentResource": {
        "sourcedId": cr_id, "status": "active",
        "title": "Topic 1.1 Quiz", "sortOrder": 1,
        "courseComponent": {"sourcedId": comp_id},
        "resource": {"sourcedId": res_id},
        "lessonType": "quiz",
    }
}
resp = session.post(f"{ONEROSTER_BASE}/ims/oneroster/rostering/v1p2/courses/component-resources",
                    headers=auth.get_headers(), json=cr_payload, timeout=30)
assert resp.status_code in (200, 201), f"Link creation failed: {resp.status_code}"

print(f"Module complete: test={test_id}, component={comp_id}, resource={res_id}")
```

---

## 9. Getting an Item

### Get a Single Assessment Item

```
GET https://qti.alpha-1edtech.ai/api/assessment-items/{item_id}
Authorization: Bearer {token}
```

**Response** (MCQ example):
```json
{
  "identifier": "qti-item-abc123...",
  "title": "Question Title",
  "type": "choice",
  "content": {
    "qti-assessment-item": {
      "qti-item-body": {
        "qti-choice-interaction": {
          "qti-prompt": "Question text...",
          "qti-simple-choice": [
            {"_attributes": {"identifier": "A"}, "_": "Choice A text"},
            {"_attributes": {"identifier": "B"}, "_": "Choice B text"}
          ]
        }
      }
    }
  },
  "responseDeclarations": [
    {"correctResponse": {"value": ["A"]}}
  ],
  "metadata": {
    "topic": "3.1",
    "difficulty": "medium"
  },
  "rawXml": "<qti-assessment-item>...</qti-assessment-item>"
}
```

> **Note**: The GET response uses a nested `content.qti-assessment-item` structure that is DIFFERENT from the flat `interaction` structure used for POST/PUT. Don't try to PUT back the exact GET response — you need to transform it.

### Get an Assessment Test

```
GET https://qti.alpha-1edtech.ai/api/assessment-tests/{test_id}
Authorization: Bearer {token}
```

### Get a Stimulus (Article)

```
GET https://qti.alpha-1edtech.ai/api/stimuli/{stimulus_id}
Authorization: Bearer {token}
```

---

## 10. Updating an Item

Updating an item requires a **full PUT** — you must send the complete item structure, not just the changed fields.

### Endpoint

```
PUT https://qti.alpha-1edtech.ai/api/assessment-items/{item_id}
Authorization: Bearer {token}
Content-Type: application/json
```

### Workflow: GET → Transform → PUT

1. **GET** the current item
2. **Extract** the data from the nested `content.qti-assessment-item` structure
3. **Rebuild** in the flat `interaction` format
4. **Apply** your changes
5. **PUT** the updated payload

### MCQ Update Payload

```json
{
  "type": "choice",
  "identifier": "qti-item-abc123...",
  "title": "Updated Question Title",
  "metadata": {
    "topic": "3.1",
    "difficulty": "hard"
  },
  "interaction": {
    "type": "choice",
    "responseIdentifier": "RESPONSE",
    "shuffle": false,
    "maxChoices": 1,
    "questionStructure": {
      "prompt": "<p>Updated question text here</p>",
      "choices": [
        {"identifier": "A", "content": "Updated choice A"},
        {"identifier": "B", "content": "Updated choice B"},
        {"identifier": "C", "content": "Updated choice C"},
        {"identifier": "D", "content": "Updated choice D"}
      ]
    }
  },
  "responseDeclarations": [
    {
      "identifier": "RESPONSE",
      "cardinality": "single",
      "baseType": "identifier",
      "correctResponse": {"value": ["B"]}
    }
  ],
  "outcomeDeclarations": [
    {"identifier": "FEEDBACK", "cardinality": "single", "baseType": "identifier"},
    {"identifier": "FEEDBACK-INLINE", "cardinality": "single", "baseType": "identifier"}
  ],
  "responseProcessing": {
    "templateType": "match_correct",
    "responseDeclarationIdentifier": "RESPONSE",
    "outcomeIdentifier": "FEEDBACK",
    "correctResponseIdentifier": "CORRECT",
    "incorrectResponseIdentifier": "INCORRECT",
    "inlineFeedback": {
      "outcomeIdentifier": "FEEDBACK-INLINE",
      "variableIdentifier": "RESPONSE"
    }
  }
}
```

### Preserving Stimulus Links

If the item had a stimulus attached, include it in the PUT:

```json
{
  "stimulus": {"identifier": "s4-stim-abc123def456"}
}
```

> If you omit `stimulus` from a PUT, the link is removed.

---

## 11. Updating Metadata Only

To update just metadata (e.g., adding a `topic` tag), you still need to rebuild the full payload. This is our "PATCH-style PUT" pattern:

1. GET the item
2. Merge your metadata updates into the existing metadata
3. Rebuild the full interaction payload from the GET response
4. PUT the whole thing back

```python
session, auth = get_client()  # see Section 2

# 1. GET the current item
resp = session.get(f"{QTI_BASE}/assessment-items/{item_id}", headers=auth.get_headers(), timeout=30)
item_data = resp.json()

# 2. Merge your metadata updates
current_meta = item_data.get("metadata", {})
current_meta["topic"] = "3.1"
current_meta["difficulty"] = "hard"

# 3. Rebuild the full payload from the GET response
#    (You MUST include the interaction structure — see Section 10 for the full pattern)
ai = item_data["content"]["qti-assessment-item"]
body = ai["qti-item-body"]
interaction = body.get("qti-choice-interaction", {})
if isinstance(interaction, list):
    interaction = interaction[0]

# Extract prompt text (simplified — real HTML may need deeper parsing)
prompt = interaction.get("qti-prompt", "")
if isinstance(prompt, dict):
    prompt = prompt.get("_", "")

# Extract choices
raw_choices = interaction.get("qti-simple-choice", [])
if isinstance(raw_choices, dict):
    raw_choices = [raw_choices]
choices = []
for c in raw_choices:
    cid = c.get("_attributes", {}).get("identifier", "")
    text = c.get("_", "")
    choices.append({"identifier": cid, "content": text})

# Get correct answer
correct_id = item_data["responseDeclarations"][0]["correctResponse"]["value"][0]

# 4. PUT the rebuilt payload
payload = {
    "type": item_data["type"],
    "identifier": item_id,
    "title": item_data["title"],
    "metadata": current_meta,
    "interaction": {
        "type": "choice", "responseIdentifier": "RESPONSE",
        "shuffle": False, "maxChoices": 1,
        "questionStructure": {"prompt": prompt, "choices": choices},
    },
    "responseDeclarations": [
        {"identifier": "RESPONSE", "cardinality": "single", "baseType": "identifier",
         "correctResponse": {"value": [correct_id]}}
    ],
    "outcomeDeclarations": [
        {"identifier": "FEEDBACK", "cardinality": "single", "baseType": "identifier"},
        {"identifier": "FEEDBACK-INLINE", "cardinality": "single", "baseType": "identifier"},
    ],
    "responseProcessing": {
        "templateType": "match_correct",
        "responseDeclarationIdentifier": "RESPONSE",
        "outcomeIdentifier": "FEEDBACK",
        "correctResponseIdentifier": "CORRECT",
        "incorrectResponseIdentifier": "INCORRECT",
        "inlineFeedback": {"outcomeIdentifier": "FEEDBACK-INLINE", "variableIdentifier": "RESPONSE"},
    },
}

resp = session.put(f"{QTI_BASE}/assessment-items/{item_id}",
                   headers=auth.get_headers(), json=payload, timeout=30)
print(f"Update: {resp.status_code}")
```

> This example is for MCQ (`choice`) items. For FRQ (`extended-text`) items, adjust the interaction and response declarations accordingly (see Section 5).

---

## 12. Updating via Raw XML

For complex QTI interaction types, or when you need precise control, use the **XML format**:

### Endpoint

```
PUT https://qti.alpha-1edtech.ai/api/assessment-items/{item_id}
Content-Type: application/json
```

### Payload

```json
{
  "format": "xml",
  "xml": "<qti-assessment-item xmlns=\"http://www.imsglobal.org/xsd/imsqtiasi_v3p0\" identifier=\"item-id\" title=\"Title\" ...>full XML here</qti-assessment-item>"
}
```

You can also include metadata alongside the XML:

```json
{
  "format": "xml",
  "xml": "<qti-assessment-item ...>...</qti-assessment-item>",
  "metadata": {
    "topic": "3.1",
    "difficulty": "medium"
  }
}
```

### When to Use XML Format

**Always use XML format for these interaction types:**
- `hotspot`
- `graphic-gap-match`
- `gap-match`
- `hottext`
- `match` (complex variants)
- `associate`
- Any type with custom response processing (e.g., external grader FRQs)

**JSON format is safe for:**
- `choice` (MCQ)
- `extended-text` (FRQ)
- `order`
- `text-entry`

> **Why?** The API's JSON-to-XML converter silently drops child elements for complex interaction types. Items posted via JSON may appear to succeed (200 response) but render broken. We learned this the hard way.

---

## 13. Fetching a Full Course (Syllabus Pull)

To see everything in a course at once:

### Endpoint

```
GET https://api.alpha-1edtech.ai/powerpath/syllabus/{course_id}
Authorization: Bearer {token}
```

### Response Structure

```json
{
  "syllabus": {
    "course": {
      "sourcedId": "APBIO-v2-20260305",
      "title": "AP Biology"
    },
    "subComponents": [
      {
        "sourcedId": "apbio-unit-1",
        "title": "Unit 1: Chemistry of Life",
        "sortOrder": 1,
        "componentResources": [
          {
            "title": "Topic 1.1 Quiz",
            "sortOrder": 1,
            "lessonType": "quiz",
            "resource": {
              "sourcedId": "apbio-res-quiz-1-1",
              "vendorResourceId": "s4-test-topic-1-1-quiz",
              "metadata": {
                "type": "qti",
                "subType": "qti-test",
                "url": "https://qti.alpha-1edtech.ai/api/assessment-tests/s4-test-topic-1-1-quiz",
                "lessonType": "quiz"
              }
            }
          },
          {
            "title": "Article: Topic 1.1",
            "sortOrder": 2,
            "lessonType": "alpha-read-article",
            "resource": {
              "sourcedId": "apbio-res-article-1-1",
              "metadata": {
                "type": "qti",
                "subType": "qti-stimulus",
                "url": "https://qti.alpha-1edtech.ai/api/stimuli/s4-stim-abc123",
                "lessonType": "alpha-read-article"
              }
            }
          }
        ],
        "subComponents": [
          {
            "sourcedId": "apbio-topic-1-1",
            "title": "Topic 1.1: Structure of Water",
            "sortOrder": 1,
            "componentResources": []
          }
        ]
      }
    ]
  }
}
```

### How to Identify Resource Types in the Syllabus

Each `componentResource` has a `resource.metadata` block. Here's how to tell what it is:

| `metadata.subType` | `metadata.type` | `url` contains | It's a... |
|----|----|----|-----|
| `"qti-test"` | `"qti"` | `assessment-tests/` | Quiz / Assessment |
| `"qti-stimulus"` | `"qti"` | `stimuli/` | Article |
| — | `"video"` | — | Video |
| — | `"assessment-bank"` | — | Assessment bank (container of tests) |

### Extracting the QTI ID from the URL

The QTI test or stimulus ID is the last segment of the `metadata.url`:

```
url: "https://qti.alpha-1edtech.ai/api/assessment-tests/s4-test-topic-1-1-quiz"
                                                         ^^^^^^^^^^^^^^^^^^^^^^^^
                                                         This is the test_id
```

Or use `metadata.vendorResourceId` or `resource.vendorResourceId` — same value.

### Quick Python: Fetch Just the Syllabus

```python
session, auth = get_client()  # see Section 2

resp = session.get(f"{TIMEBACK_BASE}/powerpath/syllabus/YOUR-COURSE-ID",
                   headers=auth.get_headers(), timeout=60)
resp.raise_for_status()
syllabus = resp.json()

# Save for inspection
import json
with open("syllabus.json", "w") as f:
    json.dump(syllabus, f, indent=2)
```

> To get ALL items (not just the syllabus structure), see Section 14 — the full 4-hop chain with a copy-pasteable script.

---

## 14. Getting All Items in a Course (The 3-Hop Chain)

The most common task: "Give me every question in this course." This requires **3 API calls in sequence**, hopping across two different APIs.

### The Chain

```
   PowerPath API                          QTI API
   ─────────────                          ───────

   ① GET /powerpath/syllabus/{course_id}
      │
      │  Walk the tree, collect all resource URLs where
      │  metadata.subType == "qti-test"
      │
      ▼
   List of test IDs
      │
      │  For each test_id:
      │
      ▼
   ② GET /assessment-tests/{test_id}
      │
      │  Extract item IDs from:
      │  qti-test-part[].qti-assessment-section[].qti-assessment-item-ref[].identifier
      │
      ▼
   List of item IDs
      │
      │  For each item_id:
      │
      ▼
   ③ GET /assessment-items/{item_id}
      │
      │  Check for qti-assessment-stimulus-ref in the item
      │  Collect unique stimulus IDs
      │
      ▼
   ④ GET /stimuli/{stimulus_id}        ← for each unique stimulus
      │
      ▼
   Full question content + associated reading passages/figures
```

### Step-by-Step

#### Hop 1: Get the Syllabus

```
GET https://api.alpha-1edtech.ai/powerpath/syllabus/{course_id}
Authorization: Bearer {token}
```

Walk the response tree recursively. For each `componentResource`, check if it's a test:

```python
# Pseudocode
for component in syllabus["syllabus"]["subComponents"]:
    for cr in component["componentResources"]:
        metadata = cr["resource"]["metadata"]
        if metadata.get("subType") == "qti-test":
            url = metadata["url"]
            test_id = url.rstrip("/").split("/")[-1]
            # → collect test_id
    # Don't forget to recurse into component["subComponents"]!
```

> **Watch out**: Components can be nested (units → topics → sub-topics). You must walk `subComponents` recursively or you'll miss items.

#### Hop 2: Get Each Assessment Test

```
GET https://qti.alpha-1edtech.ai/api/assessment-tests/{test_id}
Authorization: Bearer {token}
```

Response:
```json
{
  "identifier": "s4-test-topic-1-1-quiz",
  "title": "Topic 1.1 Quiz",
  "qti-test-part": [
    {
      "identifier": "main_part",
      "qti-assessment-section": [
        {
          "identifier": "main_section",
          "qti-assessment-item-ref": [
            {"identifier": "s4-item-001", "href": "s4-item-001.xml"},
            {"identifier": "s4-item-002", "href": "s4-item-002.xml"},
            {"identifier": "s4-item-003", "href": "s4-item-003.xml"}
          ]
        }
      ]
    }
  ]
}
```

Extract the item IDs:

```python
item_ids = []
for part in test_data["qti-test-part"]:
    for section in part["qti-assessment-section"]:
        for item_ref in section["qti-assessment-item-ref"]:
            item_ids.append(item_ref["identifier"])
```

#### Hop 3: Get Each Assessment Item

```
GET https://qti.alpha-1edtech.ai/api/assessment-items/{item_id}
Authorization: Bearer {token}
```

This returns the full question content (see [Section 9](#9-getting-an-item) for the response structure).

### Handling Assessment Banks

Some courses use **assessment banks** — these are containers that hold multiple tests. You'll find them in the syllabus with `metadata.type == "assessment-bank"`.

```json
{
  "resource": {
    "metadata": {
      "type": "assessment-bank",
      "resources": ["test-id-1", "test-id-2", "test-id-3"]
    }
  }
}
```

For banks, the child test IDs are in `metadata.resources[]`. Fetch each one the same way (Hop 2 → Hop 3).

### Collecting Stimuli (Articles) Along the Way

While walking the syllabus, also grab stimulus references:

```python
if metadata.get("subType") == "qti-stimulus":
    url = metadata["url"]
    stim_id = url.rstrip("/").split("/")[-1]
    # → collect stim_id
```

Then fetch the article:

```
GET https://qti.alpha-1edtech.ai/api/stimuli/{stim_id}
```

> **Note**: Some stimuli also live at `/assessment-stimuli/{id}` (older endpoint). Try both — if `/stimuli/` returns 404, fall back to `/assessment-stimuli/`.

### Hop 4: Pull Stimuli Referenced by Items

Many items reference a **stimulus** (reading passage, data table, figure) that the student sees alongside the question. This reference is NOT in the syllabus — it's embedded inside each item. If you skip this step, you'll have questions that say "Based on the passage above..." with no passage.

After fetching an item (Hop 3), check for the stimulus reference:

```json
{
  "content": {
    "qti-assessment-item": {
      "qti-assessment-stimulus-ref": {
        "_attributes": {"identifier": "s4-stim-abc123"}
      }
    }
  }
}
```

The `identifier` in `qti-assessment-stimulus-ref._attributes` is the stimulus ID. Fetch it:

```
GET https://qti.alpha-1edtech.ai/api/stimuli/{stimulus_id}
Authorization: Bearer {token}
```

Response:
```json
{
  "identifier": "s4-stim-abc123",
  "title": "Cellular Respiration Data",
  "content": "<p>Table 1 shows the rate of ATP production...</p>",
  "rawXml": "<qti-assessment-stimulus>...</qti-assessment-stimulus>"
}
```

> **Important**: The stimulus ref can be a single object OR a list. Always normalize:
> ```python
> stim_ref = qti_item.get("qti-assessment-stimulus-ref", [])
> if isinstance(stim_ref, dict):
>     stim_ref = [stim_ref]  # normalize to list
> for ref in stim_ref:
>     stim_id = ref.get("_attributes", {}).get("identifier", "")
> ```

> **Dedup**: Multiple items in the same test often share the same stimulus (e.g., 4 questions about the same passage). Collect stimulus IDs in a set so you only fetch each one once.

> **Two endpoints**: Some older stimuli live at `/assessment-stimuli/{id}` instead of `/stimuli/{id}`. Our Python code tries both — if `/stimuli/` returns 404, try `/assessment-stimuli/`.

### Complete Python Example

Copy-pasteable script. Uses only the `get_client()` function from Section 2 (copy that into your script first).

```python
"""Get all items in a course — the full 4-hop chain."""

# Paste the get_client(), make_session(), TimebackAuth, QTI_BASE, ONEROSTER_BASE
# code from Section 2 above this line (or import from your own auth.py).

TIMEBACK_BASE = "https://api.alpha-1edtech.ai"

session, auth = get_client()
COURSE_ID = "YOUR-COURSE-ID"  # ← replace this

# ── Hop 1: Get syllabus and find all tests ────────────────────────
resp = session.get(f"{TIMEBACK_BASE}/powerpath/syllabus/{COURSE_ID}",
                   headers=auth.get_headers(), timeout=60)
resp.raise_for_status()
syllabus = resp.json()

# Walk the tree recursively to collect test IDs
test_refs = []

def walk_components(components, path=""):
    for comp in components:
        title = comp.get("title", "")
        current_path = f"{path} > {title}" if path else title

        for cr in comp.get("componentResources", []):
            resource = cr.get("resource", {})
            metadata = resource.get("metadata", {})
            if metadata.get("subType") == "qti-test":
                url = metadata.get("url", "")
                test_id = url.rstrip("/").split("/")[-1] if "assessment-tests/" in url else ""
                if test_id:
                    test_refs.append({"test_id": test_id, "title": cr.get("title", ""), "path": current_path})

        # Recurse into nested components
        walk_components(comp.get("subComponents", []), current_path)

syllabus_data = syllabus.get("syllabus", syllabus)
walk_components(syllabus_data.get("subComponents", []))
print(f"Found {len(test_refs)} tests")

# ── Hop 2 + 3: For each test, get items ──────────────────────────
all_questions = []
stimulus_ids_seen = set()

for tref in test_refs:
    # Hop 2: Get the test
    resp = session.get(f"{QTI_BASE}/assessment-tests/{tref['test_id']}",
                       headers=auth.get_headers(), timeout=30)
    if resp.status_code != 200:
        print(f"  SKIP test {tref['test_id']}: {resp.status_code}")
        continue
    test_data = resp.json()

    # Extract item IDs
    item_ids = []
    for part in test_data.get("qti-test-part", []):
        for section in part.get("qti-assessment-section", []):
            for item_ref in section.get("qti-assessment-item-ref", []):
                item_ids.append(item_ref["identifier"])

    print(f"  {tref['title']}: {len(item_ids)} items")

    # Hop 3: Get each item
    for item_id in item_ids:
        resp = session.get(f"{QTI_BASE}/assessment-items/{item_id}",
                           headers=auth.get_headers(), timeout=30)
        if resp.status_code != 200:
            continue
        item_data = resp.json()

        all_questions.append({
            "id": item_data.get("identifier", ""),
            "title": item_data.get("title", ""),
            "type": item_data.get("type", ""),
            "metadata": item_data.get("metadata", {}),
            "test_title": tref["title"],
            "path": tref["path"],
            "raw": item_data,  # keep full data if you need to parse choices etc.
        })

        # Check for stimulus reference
        qti_item = item_data.get("content", {}).get("qti-assessment-item", {})
        stim_ref = qti_item.get("qti-assessment-stimulus-ref", [])
        if isinstance(stim_ref, dict):
            stim_ref = [stim_ref]
        for ref in stim_ref:
            sid = ref.get("_attributes", {}).get("identifier", "")
            if sid:
                stimulus_ids_seen.add(sid)

# ── Hop 4: Fetch all referenced stimuli ──────────────────────────
all_stimuli = {}
for stim_id in stimulus_ids_seen:
    for endpoint in ("stimuli", "assessment-stimuli"):  # try both
        resp = session.get(f"{QTI_BASE}/{endpoint}/{stim_id}",
                           headers=auth.get_headers(), timeout=30)
        if resp.status_code == 200:
            all_stimuli[stim_id] = resp.json()
            break

print(f"\nTotal: {len(all_questions)} questions, {len(all_stimuli)} stimuli")

# ── Save to JSON ─────────────────────────────────────────────────
import json
with open("course_questions.json", "w") as f:
    json.dump(all_questions, f, indent=2)
with open("course_stimuli.json", "w") as f:
    json.dump(all_stimuli, f, indent=2)
print("Saved to course_questions.json and course_stimuli.json")
```

---

## 15. Lesson Types Reference

The `lessonType` field controls how content renders in the student UI.

| lessonType | What it is | Used for |
|------------|-----------|----------|
| `"quiz"` | Interactive quiz/exercise | MCQ quizzes, FRQ practice, PP100, practice exams |
| `"alpha-read-article"` | Reading content | Articles, stimuli, videos |
| `"alpha-read"` | Reading assessment | Article + comprehension questions |

### Resource Metadata Combos

| Content Type | `type` | `subType` | `lessonType` | `assessmentType` |
|-------------|--------|-----------|-------------|-----------------|
| MCQ Quiz | `"qti"` | `"qti-test"` | `"quiz"` | `"quiz"` |
| FRQ Practice | `"qti"` | `"qti-test"` | `"quiz"` | `"quiz"` |
| Article | `"qti"` | `"qti-stimulus"` | `"alpha-read-article"` | `"alpha-read"` |
| Video | `"video"` | `"qti-stimulus"` | `"alpha-read-article"` | — |

---

## 16. Gotchas and Hard-Won Lessons

These are things that burned us and aren't in any official documentation.

### 1. JSON POST silently breaks complex QTI types

The API's JSON-to-XML converter drops child elements like `<qti-hotspot-choice>`, `<qti-gap-text>`, `<qti-hottext>`, and `<qti-area-mapping>`. You'll get a `200 OK` but the item renders broken.

**Rule**: Use `{"format": "xml", "xml": "..."}` for anything that isn't `choice`, `extended-text`, `order`, or `text-entry`.

### 2. GET and PUT use different formats

The GET response wraps everything in `content.qti-assessment-item.qti-item-body...`. The PUT expects the flat `interaction.questionStructure...` format. You can't just GET an item and PUT it back unchanged.

### 3. PUT is a full replace, not a patch

If you PUT an item without `stimulus`, the stimulus link is removed. If you PUT without `metadata`, metadata is cleared. Always include everything.

### 4. `lessonType` must match in two places

Set `lessonType` on BOTH:
- The resource's `metadata.lessonType`
- The component-resource's `lessonType`

If they don't match, the content may not render correctly in the student UI.

### 5. Token expires after 1 hour

The OAuth token is valid for 3600 seconds. For batch operations, use the `TimebackAuth` class from Section 2 which auto-refreshes 5 minutes before expiry.

### 6. Retry on transient errors

Always use retry logic for `429` (rate limit), `500`, `502`, `503`, `504`. The `make_session()` function from Section 2 has this built in:

```python
session = make_session()  # Retries 3x with exponential backoff
```

### 7. 409 Conflict = already exists (not an error)

When creating resources, a `409` usually means the item already exists. Treat it as success for idempotent operations.

### 8. Identifier formats

We use these conventions:
- Assessment items: `s4-{12 hex chars}`
- Stimuli: `s4-stim-{12 hex chars}`
- Tests: `s4-test-{slug}-{8 hex chars}`
- Components: `s4-comp-{slug}-{8 hex chars}`
- Resources: `s4-res-{slug}-{8 hex chars}`
- Component-resources: `s4-cr-{slug}-{8 hex chars}`

### 9. FRQ external grader XML structure

FRQs with external graders need a specific XML structure with `API_RESPONSE`, `GRADING_RESPONSE`, `FEEDBACK_VISIBILITY` outcome declarations and a rubric block. Use the raw XML format (`{"format": "xml", "xml": "..."}`) to create these — see Section 12. The key element is the `customOperator` with class `com.alpha-1edtech.ExternalApiScore` (see Section 5 for the JSON shortcut that works for simple cases).

### 10. The org sourcedId is always the same

When creating courses, the organization reference is always:
```json
"org": {"sourcedId": "346488d3-efb9-4f56-95ea-f4a441de2370"}
```

---

## 17. Quick Reference: Endpoints

### QTI API (`https://qti.alpha-1edtech.ai/api`)

| Action | Method | Endpoint |
|--------|--------|----------|
| Create MCQ/FRQ | POST | `/assessment-items` |
| Get item | GET | `/assessment-items/{id}` |
| Update item (JSON) | PUT | `/assessment-items/{id}` |
| Update item (XML) | PUT | `/assessment-items/{id}` with `{"format": "xml", "xml": "..."}` |
| Create article | POST | `/stimuli` |
| Get article | GET | `/stimuli/{id}` |
| Update article | PUT | `/stimuli/{id}` |
| Create quiz/test | POST | `/assessment-tests` |
| Get quiz/test | GET | `/assessment-tests/{id}` |

### OneRoster API (`https://api.alpha-1edtech.ai`)

| Action | Method | Endpoint |
|--------|--------|----------|
| Create course | POST | `/ims/oneroster/rostering/v1p2/courses` |
| Create component | POST | `/ims/oneroster/rostering/v1p2/courses/components` |
| Create resource | POST | `/ims/oneroster/resources/v1p2/resources/` |
| Link resource to component | POST | `/ims/oneroster/rostering/v1p2/courses/component-resources` |

### PowerPath API (`https://api.alpha-1edtech.ai`)

| Action | Method | Endpoint |
|--------|--------|----------|
| Get full course tree | GET | `/powerpath/syllabus/{course_id}` |

### Auth

| Action | Method | Endpoint |
|--------|--------|----------|
| Get token | POST | `https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token` |

---

## Appendix: Dependencies

Every Python example in this guide uses only the standard library plus `requests`:

```bash
pip install requests
```

If you want to use `python-dotenv` to load `.env` files automatically:

```bash
pip install python-dotenv
```

Then at the top of your script:
```python
from dotenv import load_dotenv
load_dotenv()  # loads TIMEBACK_CLIENT_ID and TIMEBACK_CLIENT_SECRET from .env
```

---

*This guide was written from real operational experience building 7+ AP courses on Timeback. All code examples are self-contained and copy-pasteable — just add your credentials.*
