# How To: Build Timeback Learning Data

This doc explains how to build a student-course-item level learning data table from the Timeback API. Use this to track per-item completion and accuracy for any Timeback course.

## Overview

The pipeline produces a **tidy table** with one row per (student, course, item). Each row tells you: did the student complete this item, and if graded, what was their accuracy?

Three data sources feed into it:

1. **Enrollments** (`dim_enrollments.csv`) — which students are in which courses
2. **Lesson details** (per-course CSVs) — the scaffold of all active items in a course (units, lessons, items, test_type)
3. **Course progress API** — per-student completion data from the PowerPath endpoint

## Step 1: Get Student-Course Pairs from Enrollments

```
dim_enrollments.csv
```

Filter to the courses you care about. Each row gives you:
- `student_timeback_id` — UUID used by the API
- `student_alpha_id` — our student ID
- `course_on_timeback` — course name
- `course_timeback_id` — course UUID used by the API

Example: filter to AP Social Studies courses to get ~66 enrollment rows across 53 students and 5 courses.

## Step 2: Build the Scaffold from Lesson Details

```
warehouse/dimensions/lesson_details/timeback_lesson_details/{course}_timeback_lesson_details.csv
```

Each CSV has one row per **active item** in a course. Columns:

| Column | Description |
|---|---|
| `course_on_timeback` | Course name |
| `course_timeback_id` | Course UUID |
| `unit_title` | Unit name (top of tree) |
| `unit_sort_order` | Unit sequence number |
| `lesson_title` | Lesson name (leaf component in the tree) |
| `lesson_sort_order` | Lesson sequence number |
| `item_title` | Item name (video, reading, quiz, test) |
| `item_sort_order` | Item sequence within lesson |
| `item_xp` | XP value (0 for videos/readings, >0 for graded) |
| `item_tb_id` | Resource ID (e.g. `PYSYC24-r177152-v1`) |
| `test_type` | Classification — see below |

### test_type values

| Value | Meaning | Has accuracy score? |
|---|---|---|
| `not_test` | Video, reading, article | No |
| `topic_test` | Graded quiz within a lesson | Yes |
| `unit_mcq_test` | End-of-unit MCQ assessment | Yes |
| `unit_frq_test` | End-of-unit FRQ/SAQ/LEQ/DBQ | Yes |
| `cumulative_mcq_test` | Cumulative review MCQ | Yes |
| `cumulative_frq_test` | Cumulative review FRQ | Yes |

### Build the tidy scaffold

Cross the enrollments with lesson details to get one row per (student, course, item):

```python
scaffold = enrollments.merge(lesson_details, on="course_timeback_id", how="inner")
# Result: one row per (student, course, item) — all items start as "not completed"
```

This is your base table. For AP Social Studies: ~53 students x ~1,775 items across 5 courses.

## Step 3: Fetch Completion from the API

For each (student, course) pair, call:

```
GET /powerpath/lessonPlans/getCourseProgress/{course_timeback_id}/student/{student_timeback_id}
```

**Auth:** Same OAuth2 token as all other Timeback API calls (Cognito client credentials flow).

**Response:** A JSON array of items. Each item:

```json
{
  "courseComponentResourceSourcedId": "PYSYC24-l12-r177152-v1",
  "title": "The Neuron and Neural Firing",
  "results": [
    {
      "score": 100,
      "textScore": null,
      "scoreDate": "2026-01-15T17:08:22.348Z",
      "scoreStatus": "fully graded"
    }
  ]
}
```

### Interpreting the response

- **`results` is empty** → student has not attempted this item
- **`results` has entries** → student completed it. Look at the latest entry (by `scoreDate`) if multiple (retakes).
- **`textScore = "Completed"`** → reading or video. `score` is 0. No accuracy to extract.
- **`textScore = null`** → graded test/quiz. `score` is the accuracy (0-100).
- **`scoreDate`** → when they completed it (ISO timestamp).

### Flatten to a table

From each API response, extract:

| Field | Source |
|---|---|
| `completed_at` | `results[latest].scoreDate` (empty if not attempted) |
| `accuracy` | `results[latest].score` (only when `textScore` is null) |

## Step 4: Left Join Scaffold with Progress

Join the scaffold (Step 2) with the flattened progress (Step 3):

```python
# The API returns component-resource IDs: "PYSYC24-l12-r177152-v1"
# The scaffold uses resource IDs:         "PYSYC24-r177152-v1"
# Match on the shared resource key: extract "r177152" from both

import re
def resource_key(tb_id):
    m = re.search(r"(r\d+)", str(tb_id))
    return m.group(1) if m else str(tb_id)

scaffold["rkey"] = scaffold["item_tb_id"].apply(resource_key)
progress["rkey"] = progress["item_tb_id"].apply(resource_key)

learning_data = scaffold.merge(
    progress[["student_timeback_id", "course_timeback_id", "rkey", "completed_at", "accuracy"]],
    on=["student_timeback_id", "course_timeback_id", "rkey"],
    how="left"
)
```

**Why left join from scaffold?** The scaffold contains only **active** items (filtered during lesson details build). The progress API may return extra items that are inactive/deleted on the course. The scaffold is the authoritative item list for computing completion %.

## Step 5: Compute Metrics

Now you have a tidy table. Metrics are straightforward:

```python
# Per (student, course):
total_items = len(group)
completed = group["completed_at"].notna().sum()
completion_pct = completed / total_items * 100

# Accuracy (graded tests only):
graded = group[group["test_type"] != "not_test"]
graded_done = graded[graded["completed_at"].notna()]
accuracy = graded_done["accuracy"].astype(float).mean()

# MCQ vs FRQ accuracy:
mcq = graded_done[graded_done["test_type"].str.contains("mcq")]
frq = graded_done[graded_done["test_type"].str.contains("frq")]
mcq_accuracy = mcq["accuracy"].astype(float).mean()
frq_accuracy = frq["accuracy"].astype(float).mean()

# Per (student, course, unit):
# Same logic, just group by unit_title instead
```

## Data Files Reference

| File | Location | Rows | What |
|---|---|---|---|
| Enrollments | `warehouse/dimensions/enrollments/dim_enrollments.csv` | ~2,300 | All student-course enrollments |
| Students | `warehouse/dimensions/students/dim_students_enriched.csv` | ~105 | Student dimension (name, grade, campus, timeback_id) |
| Lesson details | `warehouse/dimensions/lesson_details/timeback_lesson_details/*.csv` | ~3,900 total | Per-course item scaffold (9 AP courses) |
| Learning data | `warehouse/facts/timeback/timeback__learning_data.csv` | ~38,600 | Pre-built fact table (all AP courses) |

### AP Social Studies courses

| Course | Timeback ID | Items | Students |
|---|---|---|---|
| AP Human Geography - PP100 | HUMG20-v1 | 272 | 21 |
| AP Psychology | PYSYC24-v1 | 538 | 13 |
| AP US Government - PP 100 | UGOV23-v1 | 278 | 7 |
| AP US History - PP100 | USHI23-v1 | 380 | 13 |
| AP World History: Modern - PP100 | WORH23-v1 | 307 | 12 |

### Pre-bundled Social Studies data

Ready-to-use CSVs for the 5 courses above:

```
ap_tracker/output/adam_ss_bundle/
  ap_social_studies_enrollments.csv          — 66 rows
  ap_social_studies_students.csv             — 53 students
  ap_social_studies_lesson_details_combined.csv — 1,775 items
  ap_social_studies_learning_data.csv        — 25,376 rows
  + 5 individual lesson detail CSVs
```

## Refresh

To refresh the learning data with latest progress from the API:

```bash
# Full pipeline (enrollment + lesson details + learning data)
python timeback/scripts/refresh_timeback.py

# Just learning data (if lesson details haven't changed)
python timeback/scripts/build_learning_data.py

# Rebuild AP tracker after refresh
python ap_tracker/scripts/build_ap_tracker.py
```

Lesson details are semi-static (course structure rarely changes). The learning data fetch takes ~30 seconds for all 96 student-course pairs.
