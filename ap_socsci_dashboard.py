#!/usr/bin/env python3
"""
AP Social Studies Dashboard

Unified view of all AP Gov, APUSH, AP World, and APHG students.
Combines data from:
- Timeback (tracker + XP)
- Austin Way (adaptive platform mastery)
- Practice Tests

Run: python ap_socsci_dashboard.py
Open: http://localhost:5001
"""

import os
import re
import csv
import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

# Also try loading credentials from JSON-format .env if standard dotenv failed
def load_env_from_json():
    """Try to load credentials from JSON-format .env file."""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        try:
            content = env_file.read_text().strip()
            if content.startswith('{'):
                data = json.loads(content)
            else:
                # Parse JSON-like format without braces
                data = {}
                for line in content.split('\n'):
                    line = line.strip().rstrip(',')
                    if ':' in line:
                        key, val = line.split(':', 1)
                        key = key.strip().strip('"')
                        val = val.strip().strip('"')
                        data[key] = val

            if 'client_id' in data and not os.environ.get('TIMEBACK_CLIENT_ID'):
                os.environ['TIMEBACK_CLIENT_ID'] = data['client_id']
            if 'client_secret' in data and not os.environ.get('TIMEBACK_CLIENT_SECRET'):
                os.environ['TIMEBACK_CLIENT_SECRET'] = data['client_secret']
        except Exception:
            pass

load_env_from_json()

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'adam_ss_bundle'

# =============================================================================
# COURSE MAPPINGS
# =============================================================================

# Map between different course name formats
COURSE_NORMALIZE = {
    'AP Human Geography - PP100': 'APHG',
    'AP Human Geography': 'APHG',
    'AP Psychology': 'APPSY',
    'AP United States Government - PP 100': 'APGOV',
    'AP US Government - PP 100': 'APGOV',
    'AP United States History - PP100': 'APUSH',
    'AP US History - PP100': 'APUSH',
    'AP World History: Modern - PP100': 'APWH',
    'AP World History': 'APWH',
    'APHG': 'APHG',
    'APGOV': 'APGOV',
    'APUSH': 'APUSH',
    'APWH': 'APWH',
}

# Timeback course IDs to normalized names
TIMEBACK_COURSE_MAP = {
    'AP Human Geography - PP100': 'APHG',
    'AP United States Government - PP 100': 'APGOV',
    'AP United States History - PP100': 'APUSH',
    'AP World History: Modern - PP100': 'APWH',
}

# Total XP per course (from lesson details)
COURSE_TOTAL_XP = {
    'APHG': 3445,
    'APGOV': 4107,
    'APUSH': 6134,
    'APWH': 5338,
}

# Total skills per course (from Austin Way)
COURSE_TOTAL_SKILLS = {
    'APHG': 413,
    'APGOV': 396,
    'APUSH': 539,
    'APWH': 544,
}

# XP per skill ratio
XP_PER_SKILL = {
    course: COURSE_TOTAL_XP.get(course, 0) / COURSE_TOTAL_SKILLS.get(course, 1)
    for course in ['APHG', 'APGOV', 'APUSH', 'APWH']
}

# Practice test deadline
PT_DEADLINE = datetime(2026, 4, 16).date()

# Maximum reasonable XP/day (above this is "impossible")
MAX_REASONABLE_XP_PER_DAY = 150

# Minimum recommended XP/day (floor for recommendations)
MIN_RECOMMENDED_XP_PER_DAY = 30

# FRQ weakness threshold (if MCQ - FRQ >= this, recommend FRQ practice)
FRQ_WEAKNESS_THRESHOLD = 15

# Non-CED units (intro + exam prep) - marked with asterisk in display
# Unit 0 = intro for all courses
NON_CED_UNITS = {
    'APHG': ['0'],           # Only intro (Units 1-7 are CED)
    'APGOV': ['0', '6'],     # Intro + Unit 6 Exam Prep
    'APUSH': ['0'],          # Only intro (Units 1-9 are CED)
    'APWH': ['0', '10'],     # Intro + Unit 10 Test Prep
}

# Name aliases (registration name -> tracker name)
# Used when formal names differ from nicknames
NAME_ALIASES = {
    'august castillo': 'gus castillo',
    'benjamin valles': 'benny valles',
    'greyson walker': 'grey walker',
    'alexander mathew': 'alex mathew',
    'madelena price': 'maddie price',
    'patricia margain': 'paty margain-junco',
    'walter saunders': 'cruce saunders iv',
    'sara way': 'sara beth way',
    'mollie anne mcdougald': 'mollie mcdougald',
    'juliana orloff': 'ju orloff',
    'said tarawneh': 'saeed tarawneh',
}


def count_school_days(start_date, end_date):
    """Count weekdays (Mon-Fri) between two dates, exclusive of start, inclusive of end."""
    count = 0
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if current.weekday() < 5:  # Mon=0 through Fri=4
            count += 1
        current += timedelta(days=1)
    return max(count, 1)  # Minimum 1 to avoid division by zero

# Mini-courses available for hole-filling
MINI_COURSES = {
    'APHG': [
        {'id': 's4-r2-mc1-5ff6309d', 'name': 'DTM Application', 'units': ['u2']},
        {'id': 's4-r2-mc2-bf633a64', 'name': 'Boundary Types', 'units': ['u4']},
        {'id': 's4-r2-mc3-a673e09c', 'name': 'Centripetal/Centrifugal', 'units': ['u4']},
    ],
    'APWH': [
        {'id': 's4-r1r3-mc1-a120a364', 'name': 'China (Han to Qing)', 'units': ['u1', 'u3']},
        {'id': 's4-r1r3-mc2-83cb26f8', 'name': 'Russia (Kievan Rus to Soviet)', 'units': ['u3', 'u5', 'u7']},
        {'id': 's4-r1r3-mc3-c1b3d384', 'name': 'Ottoman Empire', 'units': ['u3']},
    ],
}

# =============================================================================
# DATA LOADING
# =============================================================================

def load_all_data():
    """Load and merge all data sources."""

    # 1. Tracker data (Phase 3 Tracker Excel)
    tracker_file = BASE_DIR / 'Phase 3 Tracker - AP Progress AY 25-26.xlsx'
    if tracker_file.exists():
        tracker_students = pd.read_excel(tracker_file, sheet_name='Students')
        tracker_practice = pd.read_excel(tracker_file, sheet_name='practice_test_data')
    else:
        tracker_students = pd.DataFrame()
        tracker_practice = pd.DataFrame()

    # Filter to SocSci courses
    socsci_courses = ['Geography', 'World History', 'United States History', 'Government']
    if len(tracker_students) > 0:
        tracker_students = tracker_students[
            tracker_students['Course'].str.contains('|'.join(socsci_courses), case=False, na=False)
        ].copy()

    # Filter to only registered AP test takers (by student AND course)
    registration_file = BASE_DIR / 'AP_2026_student_analysis_March_24th.xlsx'
    if registration_file.exists() and len(tracker_students) > 0:
        registrations = pd.read_excel(registration_file)
        # Get SocSci registrations
        socsci_reg = registrations[
            registrations['course_enrolled_in'].str.contains('|'.join(socsci_courses), case=False, na=False)
        ]
        # Build set of registered (name, course) pairs
        registered_pairs = set()
        for _, row in socsci_reg.iterrows():
            name = f"{row['student_first_name']} {row['student_last_name']}".strip().lower()
            # Normalize registration course to match tracker format
            reg_course = row['course_enrolled_in']
            if 'Geography' in reg_course:
                norm_course = 'Geography'
            elif 'World History' in reg_course:
                norm_course = 'World History'
            elif 'United States History' in reg_course or 'US History' in reg_course:
                norm_course = 'United States History'
            elif 'Government' in reg_course:
                norm_course = 'Government'
            else:
                norm_course = reg_course
            registered_pairs.add((name, norm_course))
            # Also add any known aliases (e.g., August -> Gus)
            if name in NAME_ALIASES:
                registered_pairs.add((NAME_ALIASES[name], norm_course))

        # Filter tracker to only registered (student, course) pairs
        def is_registered(row):
            student = row['Student'].lower().strip()
            course = row['Course']
            for kw in ['Geography', 'World History', 'United States History', 'Government']:
                if kw in course:
                    return (student, kw) in registered_pairs
            return False

        tracker_students = tracker_students[tracker_students.apply(is_registered, axis=1)].copy()

    # Load student dimension to get alpha_id mapping
    students_file = DATA_DIR / 'ap_social_studies_students.csv'
    if students_file.exists():
        students_dim = pd.read_csv(students_file)
        # Create name -> id mapping
        name_to_id = dict(zip(students_dim['student'], students_dim['student_id']))
        # Add alpha_id to tracker
        if len(tracker_students) > 0:
            tracker_students['student_alpha_id'] = tracker_students['Student'].map(name_to_id)

    # 2. Austin Way data
    aw_mastery_file = BASE_DIR / 'austin_way_mastery.csv'
    aw_daily_file = BASE_DIR / 'austin_way_daily.csv'

    if aw_mastery_file.exists():
        aw_mastery_raw = pd.read_csv(aw_mastery_file)
        # Get per-student-course summary
        aw_summary = aw_mastery_raw.groupby(['student_name', 'student_email', 'course']).agg({
            'course_mastery_pct': 'first',
            'mastered': 'sum',
            'total': 'sum'
        }).reset_index()
    else:
        aw_mastery_raw = pd.DataFrame()
        aw_summary = pd.DataFrame()

    if aw_daily_file.exists():
        aw_daily = pd.read_csv(aw_daily_file)
        # Get recent activity (last 14 days)
        aw_activity = aw_daily.groupby(['Student', 'Email']).agg({
            'Completed': 'sum',
            'Planned': 'sum',
            'Date': 'max'
        }).reset_index()
        aw_activity['completion_rate'] = (aw_activity['Completed'] / aw_activity['Planned'] * 100).fillna(0).round(0)
    else:
        aw_activity = pd.DataFrame()

    # 3. Practice test data - get most recent per student
    if len(tracker_practice) > 0:
        practice_socsci = tracker_practice[
            tracker_practice['course'].str.contains('|'.join(socsci_courses), case=False, na=False)
        ].copy()
        practice_socsci['test_rank'] = practice_socsci['test'].map({'Final': 1, 'Mid-term': 2})
        practice_recent = practice_socsci.sort_values(['student', 'test_rank']).drop_duplicates('student', keep='first')
    else:
        practice_recent = pd.DataFrame()

    # 4. Timeback learning data (for XP calculations)
    timeback_file = DATA_DIR / 'ap_social_studies_learning_data.csv'
    if timeback_file.exists():
        timeback_data = pd.read_csv(timeback_file)
        timeback_data['completed'] = timeback_data['completed_at'].notna()
    else:
        timeback_data = pd.DataFrame()

    # 5. Lesson details (for XP values)
    lesson_details_file = DATA_DIR / 'ap_social_studies_lesson_details_combined.csv'
    if lesson_details_file.exists():
        lesson_details = pd.read_csv(lesson_details_file)
    else:
        lesson_details = pd.DataFrame()

    # Load raw Austin Way daily for XP calculations
    if aw_daily_file.exists():
        aw_daily_raw = pd.read_csv(aw_daily_file)
    else:
        aw_daily_raw = pd.DataFrame()

    return {
        'tracker': tracker_students,
        'practice': practice_recent,
        'aw_mastery': aw_summary,
        'aw_mastery_raw': aw_mastery_raw,
        'aw_activity': aw_activity,
        'aw_daily_raw': aw_daily_raw,
        'timeback': timeback_data,
        'lesson_details': lesson_details
    }


def calculate_student_xp(timeback_data, lesson_details, aw_daily_raw, student_name, student_id, course):
    """Calculate unified XP earned and daily rate from both Timeback and Austin Way."""
    import re
    from collections import defaultdict

    today = datetime.now().date()
    cutoff = today - timedelta(days=14)

    # Initialize daily XP dict for last 14 days
    daily_xp = defaultdict(float)

    # === PART 1: Timeback XP ===
    tb_total_xp = 0
    if len(timeback_data) > 0 and len(lesson_details) > 0 and student_id:
        # Normalize course name for Timeback
        tb_course = None
        for tb_name, norm in TIMEBACK_COURSE_MAP.items():
            if norm == course:
                tb_course = tb_name
                break

        if tb_course:
            # Filter to this student and course
            student_data = timeback_data[
                (timeback_data['student_alpha_id'] == student_id) &
                (timeback_data['course_on_timeback'] == tb_course) &
                (timeback_data['completed'] == True)
            ].copy()

            if len(student_data) > 0:
                def resource_key(tb_id):
                    m = re.search(r'(r\d+)', str(tb_id))
                    return m.group(1) if m else str(tb_id)

                student_data['rkey'] = student_data['item_tb_id'].apply(resource_key)
                lesson_details_course = lesson_details[lesson_details['course_on_timeback'] == tb_course].copy()
                lesson_details_course['rkey'] = lesson_details_course['item_tb_id'].apply(resource_key)

                merged = student_data.merge(
                    lesson_details_course[['rkey', 'item_xp']],
                    on='rkey',
                    how='left'
                )
                merged['item_xp'] = merged['item_xp'].fillna(0)

                # Total XP from Timeback
                tb_total_xp = merged['item_xp'].sum()

                # Daily XP from Timeback (last 14 days)
                merged['completed_date'] = pd.to_datetime(merged['completed_at']).dt.date
                recent = merged[merged['completed_date'] >= cutoff]
                for date, xp in recent.groupby('completed_date')['item_xp'].sum().items():
                    daily_xp[date] += xp

    # === PART 2: Austin Way XP (converted from completed tasks) ===
    aw_total_xp = 0
    xp_per_skill = XP_PER_SKILL.get(course, 10)

    if len(aw_daily_raw) > 0:
        # Match by student name (first name match, case insensitive)
        first_name = student_name.lower().split()[0]
        aw_student = aw_daily_raw[
            (aw_daily_raw['Student'].str.lower().str.split().str[0] == first_name) &
            (aw_daily_raw['Course'] == course)
        ].copy()

        if len(aw_student) > 0:
            aw_student['Date'] = pd.to_datetime(aw_student['Date']).dt.date
            aw_student['xp_equiv'] = aw_student['Completed'] * xp_per_skill

            # Total AW XP (all time in the data)
            aw_total_xp = aw_student['xp_equiv'].sum()

            # Daily AW XP (last 14 days)
            recent_aw = aw_student[aw_student['Date'] >= cutoff]
            for date, xp in recent_aw.groupby('Date')['xp_equiv'].sum().items():
                daily_xp[date] += xp

    # === COMBINE ===
    total_xp = tb_total_xp + aw_total_xp

    # Daily rate (average over school days in last 14 calendar days)
    school_days_in_window = count_school_days(cutoff, today)
    daily_rate = sum(daily_xp.values()) / school_days_in_window

    # Convert dates to strings for JSON
    daily_xp_str = {str(k): float(v) for k, v in daily_xp.items()}

    return {
        'total_xp': int(total_xp),
        'tb_xp': int(tb_total_xp),
        'aw_xp': int(aw_total_xp),
        'daily_rate': round(daily_rate, 1),
        'daily_xp': daily_xp_str
    }


def calculate_unit_combined_progress(student_name, student_id, course, timeback_data, aw_mastery_raw):
    """
    Calculate unit-by-unit combined progress.
    For each unit, take max(Timeback completion %, Austin Way mastery %).
    Return average across all units.
    """
    import re

    # Get Timeback course name
    tb_course = None
    for tb_name, norm in TIMEBACK_COURSE_MAP.items():
        if norm == course:
            tb_course = tb_name
            break

    # === Timeback unit completion ===
    tb_unit_pct = {}
    if tb_course and len(timeback_data) > 0 and student_id:
        student_tb = timeback_data[
            (timeback_data['student_alpha_id'] == student_id) &
            (timeback_data['course_on_timeback'] == tb_course)
        ]
        if len(student_tb) > 0:
            for unit_title, group in student_tb.groupby('unit_title'):
                completed = group['completed_at'].notna().sum()
                total = len(group)
                pct = (completed / total * 100) if total > 0 else 0
                # Extract unit number (e.g., "Unit 1:" -> "1")
                match = re.search(r'Unit\s*(\d+)', str(unit_title))
                if match:
                    unit_num = match.group(1)
                    tb_unit_pct[unit_num] = pct

    # === Austin Way unit mastery ===
    aw_unit_pct = {}
    if len(aw_mastery_raw) > 0:
        name_normalized = student_name.lower().strip()
        student_aw = aw_mastery_raw[
            (aw_mastery_raw['student_name'].str.lower().str.strip() == name_normalized) &
            (aw_mastery_raw['course'] == course)
        ]
        for _, row in student_aw.iterrows():
            unit_id = str(row.get('unit_id', ''))
            mastery = row.get('unit_mastery_pct', 0)
            if unit_id.startswith('u') and pd.notna(mastery):
                unit_num = unit_id[1:]  # "u1" -> "1"
                aw_unit_pct[unit_num] = float(mastery)

    # === Combine unit-by-unit (take max) ===
    all_units = set(tb_unit_pct.keys()) | set(aw_unit_pct.keys())
    # Filter to actual units (0+), using CED numbering from unit titles
    content_units = [u for u in all_units if u.isdigit() and int(u) >= 0]

    if not content_units:
        return {'combined_progress': 0, 'unit_details': []}

    unit_details = []
    total_pct = 0
    non_ced_for_course = NON_CED_UNITS.get(course, ['0'])
    for unit_num in sorted(content_units, key=int):
        tb_pct = tb_unit_pct.get(unit_num, 0)
        aw_pct = aw_unit_pct.get(unit_num, 0)
        combined = max(tb_pct, aw_pct)
        total_pct += combined
        unit_details.append({
            'unit': unit_num,
            'timeback': round(tb_pct, 1),
            'austin_way': round(aw_pct, 1),
            'combined': round(combined, 1),
            'non_ced': unit_num in non_ced_for_course
        })

    combined_progress = total_pct / len(content_units) if content_units else 0

    return {
        'combined_progress': round(combined_progress, 1),
        'unit_details': unit_details
    }


def calculate_test_performance(student_id, course, timeback_data):
    """
    Calculate MCQ vs FRQ accuracy from Timeback test data.
    Returns dict with mcq_accuracy, frq_accuracy, and whether FRQ is a weakness.
    """
    # Get Timeback course name
    tb_course = None
    for tb_name, norm in TIMEBACK_COURSE_MAP.items():
        if norm == course:
            tb_course = tb_name
            break

    result = {
        'mcq_accuracy': None,
        'frq_accuracy': None,
        'mcq_count': 0,
        'frq_count': 0,
        'frq_weak': False
    }

    if not tb_course or len(timeback_data) == 0 or not student_id:
        return result

    # Filter to this student's completed tests
    student_tests = timeback_data[
        (timeback_data['student_alpha_id'] == student_id) &
        (timeback_data['course_on_timeback'] == tb_course) &
        (timeback_data['completed_at'].notna()) &
        (timeback_data['accuracy'].notna())
    ]

    if len(student_tests) == 0:
        return result

    # Split by test type
    mcq_tests = student_tests[student_tests['test_type'].str.contains('mcq', case=False, na=False)]
    frq_tests = student_tests[student_tests['test_type'].str.contains('frq', case=False, na=False)]

    if len(mcq_tests) > 0:
        result['mcq_accuracy'] = round(mcq_tests['accuracy'].astype(float).mean(), 1)
        result['mcq_count'] = len(mcq_tests)

    if len(frq_tests) > 0:
        result['frq_accuracy'] = round(frq_tests['accuracy'].astype(float).mean(), 1)
        result['frq_count'] = len(frq_tests)

    # Determine if FRQ is a weakness (MCQ - FRQ >= threshold)
    if result['mcq_accuracy'] is not None and result['frq_accuracy'] is not None:
        if result['mcq_accuracy'] - result['frq_accuracy'] >= FRQ_WEAKNESS_THRESHOLD:
            result['frq_weak'] = True

    return result


def calculate_recommendation(student_name, course, xp_to_90, daily_xp_rate, late_for_pt, aw_mastery_raw, test_perf=None, unit_details=None):
    """
    Calculate recommendation for students:

    For LATE students:
    - Speed: Just need to work harder (required <= 2x current, and achievable)
    - Holes: Has specific weak units (before frontier), recommend mini-courses
    - Impossible: Can't make it even at max effort

    For ON-TRACK students:
    - Hole-Fill: Has holes (weak units BEFORE their frontier)
    - FRQ: FRQ accuracy significantly lower than MCQ
    - Stay: Balanced, keep doing what they're doing

    A "hole" is a unit the student has passed through but didn't learn.
    Units they haven't reached yet are just incomplete, not holes.
    """
    # Initialize test_perf if not provided
    if test_perf is None:
        test_perf = {'frq_weak': False, 'mcq_accuracy': None, 'frq_accuracy': None}
    if unit_details is None:
        unit_details = []

    # Build unit name lookup from Austin Way data
    unit_names = {}
    if len(aw_mastery_raw) > 0:
        name_normalized = student_name.lower().strip()
        student_units = aw_mastery_raw[
            (aw_mastery_raw['student_name'].str.lower().str.strip() == name_normalized) &
            (aw_mastery_raw['course'] == course)
        ]
        for _, row in student_units.iterrows():
            unit_id = str(row.get('unit_id', ''))
            unit_names[unit_id] = row.get('unit_name', f'Unit {unit_id}')

    # Find the "frontier" - highest unit where student has done meaningful work (>20% combined)
    # Units BEFORE frontier with <60% are "holes"
    # Units AT or AFTER frontier with <60% are just "incomplete"
    frontier = 0
    for ud in unit_details:
        unit_num = ud.get('unit', '')
        combined = ud.get('combined', 0)
        try:
            unit_int = int(unit_num)
            if combined > 20 and unit_int > frontier:
                frontier = unit_int
        except (ValueError, TypeError):
            pass

    # Identify holes (weak units BEFORE frontier) vs incomplete (at/after frontier)
    holes = []
    incomplete = []
    for ud in unit_details:
        unit_num = ud.get('unit', '')
        combined = ud.get('combined', 0)
        try:
            unit_int = int(unit_num)
        except (ValueError, TypeError):
            continue

        if combined < 60:
            unit_id = f'u{unit_num}'
            non_ced = ud.get('non_ced', False)
            unit_info = {
                'unit_id': unit_id,
                'unit_name': unit_names.get(unit_id, f'Unit {unit_num}'),
                'mastery': int(combined),
                'non_ced': non_ced
            }
            if unit_int < frontier:
                holes.append(unit_info)
            else:
                incomplete.append(unit_info)

    # For backward compatibility, weak_units = holes only (not incomplete)
    weak_units = holes

    # Find matching mini-courses for weak units
    recommended_courses = []
    if course in MINI_COURSES:
        weak_unit_ids = {u['unit_id'] for u in weak_units}
        for mc in MINI_COURSES[course]:
            if any(u in weak_unit_ids for u in mc['units']):
                recommended_courses.append(mc)

    # === ON-TRACK STUDENTS ===
    if not late_for_pt:
        has_holes = len(holes) > 0
        has_frq_weakness = test_perf.get('frq_weak', False)
        mcq = test_perf.get('mcq_accuracy', 0) or 0
        frq = test_perf.get('frq_accuracy', 0) or 0

        # Both holes AND FRQ weakness
        if has_holes and has_frq_weakness:
            hole_units = ', '.join([h['unit_id'].replace('u', '') for h in holes])
            return {
                'rec': 'Hole+FRQ',
                'detail': f'Hole in unit(s) {hole_units} (before frontier {frontier}), then FRQ practice',
                'weak_units': holes,
                'courses': recommended_courses,
                'frontier': frontier,
                'incomplete': incomplete
            }
        # Just holes
        if has_holes:
            hole_units = ', '.join([h['unit_id'].replace('u', '') for h in holes])
            return {
                'rec': 'Hole-Fill',
                'detail': f'Hole in unit(s) {hole_units} — revisit before moving on (frontier: unit {frontier})',
                'weak_units': holes,
                'courses': recommended_courses,
                'frontier': frontier,
                'incomplete': incomplete
            }
        # Just FRQ weakness
        if has_frq_weakness:
            return {
                'rec': 'FRQ',
                'detail': f'FRQ accuracy ({frq:.0f}%) trails MCQ ({mcq:.0f}%) — intensive FRQ practice recommended',
                'weak_units': [],
                'courses': [],
                'frontier': frontier,
                'incomplete': incomplete
            }
        # Course complete - needs practice test for new baseline
        # Check if student has finished (frontier at last content unit, no incomplete, or already at 90%)
        # Last content units: APHG=7, APGOV=5, APUSH=9, APWH=9
        last_content_unit = {'APHG': 7, 'APGOV': 5, 'APUSH': 9, 'APWH': 9}.get(course, 9)
        course_complete = (
            len(incomplete) == 0 or
            xp_to_90 <= 0 or
            frontier >= last_content_unit
        )
        if course_complete:
            return {
                'rec': 'PT',
                'detail': 'Course complete — take practice test for new baseline',
                'weak_units': [],
                'courses': [],
                'frontier': frontier,
                'incomplete': incomplete
            }
        # Otherwise, stay the course
        return {
            'rec': 'Stay',
            'detail': f'On track — continue through remaining units (frontier: unit {frontier})',
            'weak_units': [],
            'courses': [],
            'frontier': frontier,
            'incomplete': incomplete
        }

    # === LATE STUDENTS ===
    # Calculate school days remaining and required XP/day
    today = datetime.now().date()
    days_remaining = count_school_days(today, PT_DEADLINE)
    if (PT_DEADLINE - today).days <= 0:
        return {'rec': 'Impossible', 'detail': 'Deadline has passed', 'courses': [], 'weak_units': holes, 'frontier': frontier, 'incomplete': incomplete}

    required_xp_per_day = max(xp_to_90 / days_remaining, MIN_RECOMMENDED_XP_PER_DAY)

    # Determine recommendation
    if required_xp_per_day > MAX_REASONABLE_XP_PER_DAY:
        return {
            'rec': 'Impossible',
            'detail': f'Need {int(required_xp_per_day)} XP/day but max reasonable is {MAX_REASONABLE_XP_PER_DAY}',
            'required_xp_day': int(required_xp_per_day),
            'days_remaining': days_remaining,
            'weak_units': holes,
            'courses': recommended_courses,
            'frontier': frontier,
            'incomplete': incomplete
        }

    # If they have actual holes (not just incomplete) and matching courses, recommend hole-filling
    if holes and recommended_courses and daily_xp_rate > 0 and required_xp_per_day <= 1.5 * daily_xp_rate:
        hole_units = ', '.join([h['unit_id'].replace('u', '') for h in holes])
        return {
            'rec': 'Holes',
            'detail': f'Fill holes in unit(s) {hole_units} with targeted courses',
            'required_xp_day': int(required_xp_per_day),
            'days_remaining': days_remaining,
            'weak_units': holes,
            'courses': recommended_courses,
            'frontier': frontier,
            'incomplete': incomplete
        }

    # If they just need to speed up (achievable increase)
    if daily_xp_rate > 0 and required_xp_per_day <= 2 * daily_xp_rate:
        multiplier = required_xp_per_day / daily_xp_rate if daily_xp_rate > 0 else 999
        return {
            'rec': 'Speed',
            'detail': f'Need {multiplier:.1f}x current pace ({int(required_xp_per_day)} vs {int(daily_xp_rate)} XP/day)',
            'required_xp_day': int(required_xp_per_day),
            'days_remaining': days_remaining,
            'weak_units': holes,
            'courses': recommended_courses,
            'frontier': frontier,
            'incomplete': incomplete
        }

    # If they have actual holes and courses available, still recommend holes
    if holes and recommended_courses:
        hole_units = ', '.join([h['unit_id'].replace('u', '') for h in holes])
        return {
            'rec': 'Holes',
            'detail': f'Focus on holes in unit(s) {hole_units}',
            'required_xp_day': int(required_xp_per_day),
            'days_remaining': days_remaining,
            'weak_units': holes,
            'courses': recommended_courses,
            'frontier': frontier,
            'incomplete': incomplete
        }

    # Otherwise it's a speed issue (but harder)
    return {
        'rec': 'Speed',
        'detail': f'Need to increase to {int(required_xp_per_day)} XP/day',
        'required_xp_day': int(required_xp_per_day),
        'days_remaining': days_remaining,
        'weak_units': holes,
        'courses': [],
        'frontier': frontier,
        'incomplete': incomplete
    }


def build_unified_table(data):
    """Build the unified student table."""
    tracker = data['tracker']
    practice = data['practice']
    aw_mastery = data['aw_mastery']
    aw_mastery_raw = data['aw_mastery_raw']
    aw_activity = data['aw_activity']
    aw_daily_raw = data['aw_daily_raw']
    timeback = data['timeback']
    lesson_details = data['lesson_details']

    if len(tracker) == 0:
        return []

    rows = []

    for _, t in tracker.iterrows():
        student_name = t['Student']
        student_id = t.get('student_alpha_id', '')
        email = student_name.lower().replace(' ', '.') + '@alpha.school'  # Approximate
        course_full = t['Course']

        # Simplify course name
        if 'Geography' in course_full:
            course = 'APHG'
        elif 'World History' in course_full:
            course = 'APWH'
        elif 'United States History' in course_full:
            course = 'APUSH'
        elif 'Government' in course_full:
            course = 'APGOV'
        else:
            course = course_full

        # Tracker data
        progress = t.get('Progress', 0)
        mcq = t.get('MCQ', None)
        frq = t.get('FRQ', None)

        # Austin Way mastery for this course
        aw_course_match = aw_mastery[
            (aw_mastery['student_name'].str.lower().str.contains(student_name.lower().split()[0], na=False)) &
            (aw_mastery['course'] == course)
        ] if len(aw_mastery) > 0 else pd.DataFrame()

        aw_mastery_pct = aw_course_match['course_mastery_pct'].iloc[0] if len(aw_course_match) > 0 else None

        # Austin Way activity
        aw_act_match = aw_activity[
            aw_activity['Student'].str.lower().str.contains(student_name.lower().split()[0], na=False)
        ] if len(aw_activity) > 0 else pd.DataFrame()

        aw_completed = int(aw_act_match['Completed'].iloc[0]) if len(aw_act_match) > 0 else None
        aw_last_active = aw_act_match['Date'].iloc[0] if len(aw_act_match) > 0 else None
        aw_rate = int(aw_act_match['completion_rate'].iloc[0]) if len(aw_act_match) > 0 else None

        # Practice test - match on full name AND course
        pt_match = pd.DataFrame()
        if len(practice) > 0:
            # Simplify course name for matching
            if 'Geography' in course_full:
                course_match = 'Geography'
            elif 'World History' in course_full:
                course_match = 'World History'
            elif 'United States History' in course_full:
                course_match = 'United States History'
            elif 'Government' in course_full:
                course_match = 'Government'
            else:
                course_match = course_full.split(' - ')[0]

            # Try exact match first
            name_lower = student_name.lower().strip()
            pt_match = practice[
                (practice['student'].str.lower().str.strip() == name_lower) &
                (practice['course'].str.contains(course_match, case=False, na=False))
            ]
            # If no exact match, try matching first AND last name (both required)
            if len(pt_match) == 0:
                name_parts = name_lower.split()
                if len(name_parts) >= 2:
                    first, last = name_parts[0], name_parts[-1]
                    # Both first and last must match as whole words (not substrings)
                    pt_match = practice[
                        (practice['course'].str.contains(course_match, case=False, na=False))
                    ].copy()
                    if len(pt_match) > 0:
                        # Check each candidate
                        matches = []
                        for idx, row in pt_match.iterrows():
                            pt_name = row['student'].lower().strip()
                            pt_parts = pt_name.replace('-', ' ').split()
                            # First name must match start, last name must match end
                            if pt_parts and pt_parts[0] == first and pt_parts[-1] == last:
                                matches.append(idx)
                        pt_match = pt_match.loc[matches] if matches else pd.DataFrame()

        pt_score = int(pt_match['ap_score (from albert calculator)'].iloc[0]) if len(pt_match) > 0 and pd.notna(pt_match['ap_score (from albert calculator)'].iloc[0]) else None
        pt_mcq = int(pt_match['final_mcq_accuracy'].iloc[0] * 100) if len(pt_match) > 0 and pd.notna(pt_match['final_mcq_accuracy'].iloc[0]) else None
        pt_frq = int(pt_match['final_frq_accuracy'].iloc[0] * 100) if len(pt_match) > 0 and pd.notna(pt_match['final_frq_accuracy'].iloc[0]) else None

        # Calculate XP data
        xp_data = calculate_student_xp(timeback, lesson_details, aw_daily_raw, student_name, student_id, course)
        current_xp = xp_data['total_xp']
        daily_xp_rate = xp_data['daily_rate']

        # Calculate COMBINED progress unit-by-unit (take max per unit, then average)
        unit_progress_data = calculate_unit_combined_progress(
            student_name, student_id, course, timeback, aw_mastery_raw
        )
        combined_progress = unit_progress_data['combined_progress']
        unit_details = unit_progress_data['unit_details']

        # Calculate XP to 90% using COMBINED progress
        # Note: PT 4+ students still see actual progress (may have holes to address)
        current_mastery = combined_progress / 100
        target_mastery = 0.90
        total_skills = COURSE_TOTAL_SKILLS.get(course, 0)
        xp_per_skill = XP_PER_SKILL.get(course, 10)

        # Skills remaining = (90% - current%) * total_skills
        # XP remaining = skills_remaining * xp_per_skill
        if current_mastery < target_mastery and total_skills > 0:
            skills_remaining = (target_mastery - current_mastery) * total_skills
            xp_to_90 = int(skills_remaining * xp_per_skill)
        else:
            xp_to_90 = 0

        # Projected date to 90%
        # April 16, 2026 is the practice test deadline
        pt_deadline = datetime(2026, 4, 16).date()
        late_for_pt = False
        projected_date = None

        if daily_xp_rate > 0 and xp_to_90 > 0:
            days_to_90 = xp_to_90 / daily_xp_rate
            projected_date = (datetime.now() + timedelta(days=days_to_90)).date()
            # Cap at reasonable future (2 years)
            if days_to_90 > 730:
                projected_90_str = '>2y'
                late_for_pt = True
            else:
                projected_90_str = projected_date.strftime('%b %d')
                late_for_pt = projected_date > pt_deadline
        elif xp_to_90 == 0:
            projected_90_str = 'Done'
            late_for_pt = False
        else:
            projected_90_str = 'Never'
            late_for_pt = True

        # Calculate combined/estimated readiness
        scores = []
        if mcq is not None and pd.notna(mcq):
            scores.append(mcq)
        if frq is not None and pd.notna(frq):
            scores.append(frq)
        if aw_mastery_pct is not None:
            scores.append(aw_mastery_pct)

        combined_est = round(sum(scores) / len(scores), 0) if scores else None

        # Calculate test performance (MCQ vs FRQ from Timeback)
        test_perf = calculate_test_performance(student_id, course, timeback)

        # Calculate recommendation first (needed for risk assessment)
        rec_data = calculate_recommendation(
            student_name, course, xp_to_90, daily_xp_rate, late_for_pt, aw_mastery_raw, test_perf, unit_details
        )

        # Risk assessment - factors in both knowledge AND deadline
        risk = 'Unknown'
        if pt_score is not None:
            # Have PT score - use it as primary indicator
            if pt_score <= 2:
                risk = 'Critical'
            elif pt_score == 3:
                risk = 'At Risk'
            elif pt_score == 4:
                risk = 'On Track'
            else:
                risk = 'Strong'
        elif combined_est is not None:
            if combined_est < 50:
                risk = 'Critical'
            elif combined_est < 65:
                risk = 'At Risk'
            elif combined_est < 80:
                risk = 'On Track'
            else:
                risk = 'Strong'

        # Override risk if deadline makes it impossible/unlikely
        # BUT don't override if they have a PT score of 4+ (they've proven readiness)
        if pt_score is None or pt_score < 4:
            if rec_data['rec'] == 'Impossible':
                if risk in ('On Track', 'Strong', 'Unknown'):
                    risk = 'Critical'
            elif rec_data['rec'] in ('Speed', 'Holes'):
                if risk in ('On Track', 'Strong', 'Unknown'):
                    risk = 'At Risk'

        rows.append({
            'student': student_name,
            'student_id': student_id,
            'course': course,
            'timeback_progress': round(progress, 1) if pd.notna(progress) else None,
            'aw_mastery': int(aw_mastery_pct) if aw_mastery_pct is not None else None,
            'combined_progress': round(combined_progress, 1),
            'unit_details': unit_details,
            'mcq': round(mcq, 1) if pd.notna(mcq) else None,
            'frq': round(frq, 1) if pd.notna(frq) else None,
            'aw_completed_14d': aw_completed,
            'aw_rate': aw_rate,
            'aw_last_active': aw_last_active,
            'pt_score': pt_score,
            'pt_mcq': pt_mcq,
            'pt_frq': pt_frq,
            'combined_est': int(combined_est) if combined_est is not None else None,
            'risk': risk,
            'current_xp': current_xp,
            'tb_xp': xp_data['tb_xp'],
            'aw_xp': xp_data['aw_xp'],
            'daily_xp': daily_xp_rate,
            'xp_to_90': xp_to_90,
            'projected_90': projected_90_str,
            'late_for_pt': late_for_pt,
            'recommendation': rec_data['rec'],
            'rec_detail': rec_data.get('detail', ''),
            'rec_required_xp': rec_data.get('required_xp_day', 0),
            'rec_days': rec_data.get('days_remaining', 0),
            'weak_units': rec_data.get('weak_units', []),
            'rec_courses': rec_data.get('courses', []),
            'frontier': rec_data.get('frontier', 0),
            'incomplete': rec_data.get('incomplete', []),
            'tb_mcq_accuracy': test_perf.get('mcq_accuracy'),
            'tb_frq_accuracy': test_perf.get('frq_accuracy'),
            'frq_weak': test_perf.get('frq_weak', False),
        })

    return rows


def get_student_timeseries(data, student_name, course):
    """Get daily unified XP time series for a student (Timeback + Austin Way)."""
    import re
    from collections import defaultdict

    timeback = data['timeback']
    lesson_details = data['lesson_details']
    tracker = data['tracker']
    aw_daily_raw = data['aw_daily_raw']

    today = datetime.now().date()
    all_days = pd.date_range(end=today, periods=30).date

    # Initialize daily data
    daily_data = {d: {'tb_xp': 0, 'tb_items': 0, 'aw_xp': 0, 'aw_items': 0} for d in all_days}

    # Find student ID
    student_match = tracker[tracker['Student'] == student_name]
    student_id = student_match['student_alpha_id'].iloc[0] if len(student_match) > 0 else None

    # === TIMEBACK XP ===
    tb_course = None
    for tb_name, norm in TIMEBACK_COURSE_MAP.items():
        if norm == course:
            tb_course = tb_name
            break

    if tb_course and len(timeback) > 0 and student_id:
        def resource_key(tb_id):
            m = re.search(r'(r\d+)', str(tb_id))
            return m.group(1) if m else str(tb_id)

        student_data = timeback[
            (timeback['student_alpha_id'] == student_id) &
            (timeback['course_on_timeback'] == tb_course) &
            (timeback['completed_at'].notna())
        ].copy()

        if len(student_data) > 0:
            student_data['rkey'] = student_data['item_tb_id'].apply(resource_key)
            lesson_details_course = lesson_details[lesson_details['course_on_timeback'] == tb_course].copy()
            lesson_details_course['rkey'] = lesson_details_course['item_tb_id'].apply(resource_key)

            merged = student_data.merge(
                lesson_details_course[['rkey', 'item_xp']],
                on='rkey',
                how='left'
            )
            merged['item_xp'] = merged['item_xp'].fillna(0)
            merged['completed_date'] = pd.to_datetime(merged['completed_at']).dt.date

            for date, group in merged.groupby('completed_date'):
                if date in daily_data:
                    daily_data[date]['tb_xp'] = group['item_xp'].sum()
                    daily_data[date]['tb_items'] = len(group)

    # === AUSTIN WAY XP ===
    xp_per_skill = XP_PER_SKILL.get(course, 10)

    if len(aw_daily_raw) > 0:
        first_name = student_name.lower().split()[0]
        aw_student = aw_daily_raw[
            (aw_daily_raw['Student'].str.lower().str.split().str[0] == first_name) &
            (aw_daily_raw['Course'] == course)
        ].copy()

        if len(aw_student) > 0:
            aw_student['Date'] = pd.to_datetime(aw_student['Date']).dt.date
            for _, row in aw_student.iterrows():
                date = row['Date']
                if date in daily_data:
                    daily_data[date]['aw_xp'] = row['Completed'] * xp_per_skill
                    daily_data[date]['aw_items'] = row['Completed']

    # Build result
    result = []
    for date in all_days:
        d = daily_data[date]
        result.append({
            'date': str(date),
            'xp': int(d['tb_xp'] + d['aw_xp']),
            'tb_xp': int(d['tb_xp']),
            'aw_xp': int(d['aw_xp']),
            'items': int(d['tb_items'] + d['aw_items'])
        })

    return result


# =============================================================================
# DATA REFRESH
# =============================================================================

try:
    import browser_cookie3
    BROWSER_COOKIES_AVAILABLE = True
except ImportError:
    BROWSER_COOKIES_AVAILABLE = False

# Timeback API URLs
TIMEBACK_TOKEN_URL = "https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token"
TIMEBACK_API_BASE = "https://api.alpha-1edtech.ai"

# Austin Way API
AUSTIN_WAY_API_BASE = "https://api.aphistoryforge.com/api/guide"
AUSTIN_WAY_AUTH_FILE = BASE_DIR / "austin_way_auth.txt"
AUSTIN_WAY_OUTPUT_FILE = BASE_DIR / "austin_way_mastery.csv"

# Timeback output
TIMEBACK_LEARNING_DATA_FILE = DATA_DIR / "ap_social_studies_learning_data.csv"


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
            TIMEBACK_TOKEN_URL,
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


def make_retry_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def harvest_austin_way_cookie():
    """Harvest aph_auth cookie from browser and save to auth file."""
    if not BROWSER_COOKIES_AVAILABLE:
        return {"success": False, "message": "browser-cookie3 not installed"}

    # Try different browsers
    browsers = [
        ('Chrome', browser_cookie3.chrome),
        ('Firefox', browser_cookie3.firefox),
        ('Edge', browser_cookie3.edge),
    ]

    for browser_name, browser_fn in browsers:
        try:
            cj = browser_fn(domain_name='.aphistoryforge.com')
            for cookie in cj:
                if cookie.name == 'aph_auth':
                    # Save to file
                    AUSTIN_WAY_AUTH_FILE.write_text(cookie.value)
                    return {
                        "success": True,
                        "message": f"Harvested aph_auth cookie from {browser_name}",
                        "browser": browser_name
                    }
        except Exception as e:
            continue

    return {"success": False, "message": "No aph_auth cookie found in any browser. Please sign in at aphistoryforge.com first."}


def refresh_austin_way():
    """Refresh Austin Way mastery data by calling the existing scraper."""
    results = {"success": False, "message": "", "rows": 0}

    try:
        import subprocess
        result = subprocess.run(
            ['python', str(BASE_DIR / 'austin_way_scraper.py')],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Parse output for row count
            output = result.stdout
            if 'Wrote' in output:
                import re
                match = re.search(r'Wrote (\d+) rows', output)
                if match:
                    results["rows"] = int(match.group(1))
            results["success"] = True
            results["message"] = f"Scraper completed. {results['rows']} rows written."
        else:
            error = result.stderr or result.stdout
            if 'expired' in error.lower() or '401' in error or 'Unauthorized' in error:
                results["message"] = "Auth cookie expired. Please sign in and paste new cookie."
            else:
                results["message"] = f"Scraper failed: {error[:200]}"

    except subprocess.TimeoutExpired:
        results["message"] = "Scraper timed out after 120 seconds"
    except Exception as e:
        results["message"] = f"Error running scraper: {e}"

    return results


def refresh_timeback():
    """Refresh Timeback learning data by calling the safe refresh script."""
    results = {"success": False, "message": "", "rows": 0}

    try:
        import subprocess
        result = subprocess.run(
            ['python', str(BASE_DIR / 'refresh_timeback_safe.py')],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes for all API calls
        )

        output = result.stdout + result.stderr

        if result.returncode == 0 and 'Saved to:' in output:
            # Parse completion count
            import re
            match = re.search(r'Rows with completion: (\d+)', output)
            if match:
                results["rows"] = int(match.group(1))

            # Check for new completions
            new_match = re.search(r'\+(\d+) new completions', output)
            if new_match:
                results["message"] = f"Refreshed with {new_match.group(1)} new completions"
            else:
                results["message"] = f"Refreshed ({results['rows']} completed items)"

            # Auto-copy the new file over the old one
            new_file = DATA_DIR / 'ap_social_studies_learning_data_NEW.csv'
            old_file = DATA_DIR / 'ap_social_studies_learning_data.csv'
            if new_file.exists():
                import shutil
                shutil.copy(new_file, old_file)

            results["success"] = True
        else:
            # Extract error message
            if 'ERROR' in output:
                error_line = [l for l in output.split('\n') if 'ERROR' in l]
                results["message"] = error_line[0] if error_line else "Unknown error"
            else:
                results["message"] = f"Script failed: {output[-500:]}"

    except subprocess.TimeoutExpired:
        results["message"] = "Refresh timed out after 5 minutes"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results


def _refresh_timeback_DISABLED():
    """DISABLED - was corrupting data. Refresh Timeback learning data from PowerPath API."""
    results = {"success": False, "message": "", "rows": 0}

    # Check for credentials
    client_id = os.environ.get("TIMEBACK_CLIENT_ID")
    client_secret = os.environ.get("TIMEBACK_CLIENT_SECRET")
    if not client_id or not client_secret:
        results["message"] = "TIMEBACK_CLIENT_ID and TIMEBACK_CLIENT_SECRET not set in .env"
        return results

    # Load enrollments
    enrollments_file = DATA_DIR / "ap_social_studies_enrollments.csv"
    if not enrollments_file.exists():
        results["message"] = f"Enrollments file not found: {enrollments_file}"
        return results

    enrollments = pd.read_csv(enrollments_file)

    # Load lesson details scaffold
    lesson_details_file = DATA_DIR / "ap_social_studies_lesson_details_combined.csv"
    if not lesson_details_file.exists():
        results["message"] = f"Lesson details file not found: {lesson_details_file}"
        return results

    lesson_details = pd.read_csv(lesson_details_file)

    try:
        auth = TimebackAuth(client_id, client_secret)
        session = make_retry_session()

        # Build resource key extraction function
        def resource_key(tb_id):
            m = re.search(r'(r\d+)', str(tb_id))
            return m.group(1) if m else str(tb_id)

        # Fetch progress for each enrollment
        all_progress = []
        for _, enrollment in enrollments.iterrows():
            student_tb_id = enrollment['student_timeback_id']
            course_tb_id = enrollment['course_timeback_id']
            student_alpha_id = enrollment['student_alpha_id']

            try:
                url = f"{TIMEBACK_API_BASE}/powerpath/lessonPlans/getCourseProgress/{course_tb_id}/student/{student_tb_id}"
                resp = session.get(url, headers=auth.get_headers(), timeout=30)

                if resp.status_code == 200:
                    items = resp.json()
                    for item in items:
                        item_tb_id = item.get('courseComponentResourceSourcedId', '')
                        results_list = item.get('results', [])

                        if results_list:
                            # Get latest result
                            latest = max(results_list, key=lambda x: x.get('scoreDate', ''))
                            completed_at = latest.get('scoreDate')
                            text_score = latest.get('textScore')
                            score = latest.get('score')

                            # Only use score as accuracy for graded items (textScore is null)
                            accuracy = score if text_score is None else None

                            all_progress.append({
                                'student_timeback_id': student_tb_id,
                                'student_alpha_id': student_alpha_id,
                                'course_timeback_id': course_tb_id,
                                'item_tb_id': item_tb_id,
                                'rkey': resource_key(item_tb_id),
                                'completed_at': completed_at,
                                'accuracy': accuracy,
                            })

                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"Error fetching progress for {student_alpha_id}/{course_tb_id}: {e}")
                continue

        # Build scaffold with resource keys
        lesson_details['rkey'] = lesson_details['item_tb_id'].apply(resource_key)

        # Drop course_on_timeback from enrollments to avoid _x/_y suffix after merge
        enrollments_clean = enrollments.drop(columns=['course_on_timeback'], errors='ignore')

        # Cross enrollments with lesson details to get full scaffold
        scaffold = enrollments_clean.merge(
            lesson_details,
            on='course_timeback_id',
            how='inner'
        )

        if all_progress:
            progress_df = pd.DataFrame(all_progress)

            # Merge scaffold with progress
            learning_data = scaffold.merge(
                progress_df[['student_timeback_id', 'course_timeback_id', 'rkey', 'completed_at', 'accuracy']],
                on=['student_timeback_id', 'course_timeback_id', 'rkey'],
                how='left'
            )
        else:
            learning_data = scaffold.copy()
            learning_data['completed_at'] = None
            learning_data['accuracy'] = None

        # Save to CSV
        learning_data.to_csv(TIMEBACK_LEARNING_DATA_FILE, index=False)

        results["success"] = True
        results["rows"] = len(learning_data)
        results["message"] = f"Wrote {len(learning_data)} rows ({len(all_progress)} completed items)"

    except Exception as e:
        results["message"] = f"Error: {e}"

    return results


# =============================================================================
# FLASK ROUTES
# =============================================================================

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>AP Social Studies Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 { margin-bottom: 10px; color: #fff; }
        .subtitle { color: #888; margin-bottom: 20px; }

        .nav { margin-bottom: 20px; }
        .nav a {
            color: #4da6ff;
            margin-right: 20px;
            text-decoration: none;
        }
        .nav a:hover { text-decoration: underline; }

        .filters {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .filters select, .filters input {
            padding: 8px 12px;
            border: 1px solid #333;
            border-radius: 4px;
            background: #252540;
            color: #fff;
            font-size: 14px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        th, td {
            padding: 8px 6px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        th {
            background: #252540;
            cursor: pointer;
            user-select: none;
            position: sticky;
            top: 0;
            white-space: nowrap;
        }
        th:hover { background: #353560; }
        th.sorted-asc::after { content: ' ▲'; }
        th.sorted-desc::after { content: ' ▼'; }

        tr:hover { background: #252540; cursor: pointer; }

        .course-tag {
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }
        .course-APHG { background: #2d5a27; }
        .course-APWH { background: #5a2727; }
        .course-APUSH { background: #27415a; }
        .course-APGOV { background: #5a4a27; }

        .risk-Critical { color: #ff4444; font-weight: bold; }
        .risk-At-Risk { color: #ffaa00; }
        .risk-On-Track { color: #88cc88; }
        .risk-Strong { color: #44ff44; }
        .risk-Unknown { color: #888; }

        .metric { font-family: monospace; }
        .metric-good { color: #88cc88; }
        .metric-ok { color: #cccc88; }
        .metric-bad { color: #cc8888; }
        .metric-null { color: #666; }

        .activity-hot { color: #44ff44; }
        .activity-warm { color: #ffaa00; }
        .activity-cold { color: #ff4444; }

        .projection-good { color: #44ff44; }
        .projection-ok { color: #ffaa00; }
        .projection-bad { color: #ff4444; }
        .projection-done { color: #88cc88; }

        .rec-stay { color: #44ff44; }
        .rec-pt { color: #44dddd; }
        .rec-hole-fill { color: #ff8844; }
        .rec-frq { color: #aa88ff; }
        .rec-hole\+frq { color: #ff88ff; font-weight: bold; }
        .rec-speed { color: #ffaa00; font-weight: bold; }
        .rec-holes { color: #ff8844; font-weight: bold; }
        .rec-impossible { color: #ff4444; font-weight: bold; }

        .summary-cards {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .card {
            background: #252540;
            padding: 12px 16px;
            border-radius: 8px;
            min-width: 120px;
        }
        .card-value { font-size: 24px; font-weight: bold; }
        .card-label { color: #888; font-size: 11px; }

        .pt-score {
            display: inline-block;
            width: 22px;
            height: 22px;
            line-height: 22px;
            text-align: center;
            border-radius: 50%;
            font-weight: bold;
            font-size: 11px;
        }
        .pt-1, .pt-2 { background: #ff4444; color: #fff; }
        .pt-3 { background: #ffaa00; color: #000; }
        .pt-4 { background: #88cc88; color: #000; }
        .pt-5 { background: #44ff44; color: #000; }

        .xp-bar {
            width: 60px;
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-left: 5px;
        }
        .xp-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #4da6ff, #44ff44);
        }
    </style>
</head>
<body>
    <h1>AP Social Studies Dashboard</h1>
    <p class="subtitle">APHG / AP World / APUSH / AP Gov — {{ students|length }} students — Exam: May 2026</p>

    <nav class="nav">
        <a href="/">Dashboard</a>
        <a href="/coaching">Coaching Calls</a>
        <a href="/refresh">Refresh Data</a>
    </nav>

    <div class="summary-cards">
        <div class="card">
            <div class="card-value" style="color: #ff4444;">{{ summary.critical }}</div>
            <div class="card-label">Critical</div>
        </div>
        <div class="card">
            <div class="card-value" style="color: #ffaa00;">{{ summary.at_risk }}</div>
            <div class="card-label">At Risk</div>
        </div>
        <div class="card">
            <div class="card-value" style="color: #88cc88;">{{ summary.on_track }}</div>
            <div class="card-label">On Track</div>
        </div>
        <div class="card">
            <div class="card-value" style="color: #666;">{{ summary.no_pt }}</div>
            <div class="card-label">No PT Score</div>
        </div>
        <div class="card">
            <div class="card-value" style="color: #ff4444;">{{ summary.late_for_pt }}</div>
            <div class="card-label">Late for Apr 16 PT</div>
        </div>
    </div>

    <div class="filters">
        <select id="filter-course">
            <option value="">All Courses</option>
            <option value="APHG">APHG</option>
            <option value="APWH">AP World</option>
            <option value="APUSH">APUSH</option>
            <option value="APGOV">AP Gov</option>
        </select>
        <select id="filter-risk">
            <option value="">All Risk Levels</option>
            <option value="Critical">Critical</option>
            <option value="At Risk">At Risk</option>
            <option value="On Track">On Track</option>
            <option value="Strong">Strong</option>
        </select>
        <select id="filter-late">
            <option value="">All Students</option>
            <option value="true">Late for Apr 16</option>
            <option value="false">On Track for Apr 16</option>
        </select>
        <input type="text" id="filter-search" placeholder="Search student...">
    </div>

    <table id="student-table">
        <thead>
            <tr>
                <th data-sort="student">Student</th>
                <th data-sort="course">Course</th>
                <th data-sort="risk">Risk</th>
                <th data-sort="pt_score">PT</th>
                <th data-sort="timeback_progress">Timeback</th>
                <th data-sort="aw_mastery">Austin Way</th>
                <th data-sort="combined_progress">Combined</th>
                <th data-sort="xp_to_90">XP to 90%</th>
                <th data-sort="projected_90">Proj 90%</th>
                <th data-sort="recommendation">Rec</th>
                <th data-sort="daily_xp">XP/SchoolDay</th>
            </tr>
        </thead>
        <tbody>
            {% for s in students %}
            <tr data-course="{{ s.course }}" data-risk="{{ s.risk }}" data-late="{{ 'true' if s.late_for_pt else 'false' }}" data-student="{{ s.student }}" onclick="window.location='/student/{{ s.student|urlencode }}/{{ s.course }}'">
                <td>{{ s.student }}</td>
                <td><span class="course-tag course-{{ s.course }}">{{ s.course }}</span></td>
                <td class="risk-{{ s.risk|replace(' ', '-') }}">{{ s.risk }}</td>
                <td>
                    {% if s.pt_score %}
                    <span class="pt-score pt-{{ s.pt_score }}">{{ s.pt_score }}</span>
                    {% else %}
                    <span class="metric-null">—</span>
                    {% endif %}
                </td>
                <td class="metric {% if s.timeback_progress and s.timeback_progress >= 90 %}metric-good{% elif s.timeback_progress and s.timeback_progress >= 70 %}metric-ok{% elif s.timeback_progress %}metric-bad{% else %}metric-null{% endif %}">
                    {{ s.timeback_progress|default('—', true) }}{% if s.timeback_progress %}%{% endif %}
                </td>
                <td class="metric {% if s.aw_mastery and s.aw_mastery >= 70 %}metric-good{% elif s.aw_mastery and s.aw_mastery >= 50 %}metric-ok{% elif s.aw_mastery %}metric-bad{% else %}metric-null{% endif %}">
                    {{ s.aw_mastery|default('—', true) }}{% if s.aw_mastery %}%{% endif %}
                </td>
                <td class="metric {% if s.combined_progress and s.combined_progress >= 90 %}metric-good{% elif s.combined_progress and s.combined_progress >= 70 %}metric-ok{% elif s.combined_progress %}metric-bad{% else %}metric-null{% endif %}">
                    {{ s.combined_progress|default('—', true) }}{% if s.combined_progress %}%{% endif %}
                </td>
                <td class="metric">
                    {% if s.xp_to_90 == 0 %}
                    <span class="metric-good">Done</span>
                    {% elif s.xp_to_90 %}
                    {{ s.xp_to_90 }}
                    {% else %}
                    <span class="metric-null">—</span>
                    {% endif %}
                </td>
                <td class="{% if s.projected_90 == 'Done' %}projection-done{% elif s.late_for_pt %}projection-bad{% else %}projection-ok{% endif %}">
                    {{ s.projected_90|default('—', true) }}
                </td>
                <td class="rec-{{ s.recommendation|lower }}">
                    {{ s.recommendation }}
                </td>
                <td class="{% if s.daily_xp >= 50 %}activity-hot{% elif s.daily_xp >= 20 %}activity-warm{% elif s.daily_xp > 0 %}activity-cold{% else %}metric-null{% endif %}">
                    {{ s.daily_xp if s.daily_xp else '—' }}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        // Sorting
        let currentSort = { column: null, desc: false };

        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', (e) => {
                e.stopPropagation();
                const column = th.dataset.sort;
                const desc = currentSort.column === column ? !currentSort.desc : false;
                currentSort = { column, desc };

                // Update header classes
                document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
                th.classList.add(desc ? 'sorted-desc' : 'sorted-asc');

                // Sort rows
                const tbody = document.querySelector('#student-table tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));

                rows.sort((a, b) => {
                    const aVal = a.children[getColumnIndex(column)].textContent.trim();
                    const bVal = b.children[getColumnIndex(column)].textContent.trim();

                    // Handle special values
                    if (aVal === 'Never' || aVal === '>2y') return desc ? -1 : 1;
                    if (bVal === 'Never' || bVal === '>2y') return desc ? 1 : -1;
                    if (aVal === 'Done') return desc ? 1 : -1;
                    if (bVal === 'Done') return desc ? -1 : 1;

                    // Handle numeric vs string
                    const aNum = parseFloat(aVal.replace('%', ''));
                    const bNum = parseFloat(bVal.replace('%', ''));

                    let cmp;
                    if (!isNaN(aNum) && !isNaN(bNum)) {
                        cmp = aNum - bNum;
                    } else if (aVal === '—' && bVal !== '—') {
                        cmp = 1;
                    } else if (aVal !== '—' && bVal === '—') {
                        cmp = -1;
                    } else {
                        cmp = aVal.localeCompare(bVal);
                    }

                    return desc ? -cmp : cmp;
                });

                rows.forEach(row => tbody.appendChild(row));
            });
        });

        function getColumnIndex(column) {
            const columns = ['student', 'course', 'risk', 'pt_score', 'timeback_progress', 'aw_mastery', 'combined_progress', 'xp_to_90', 'projected_90', 'recommendation', 'daily_xp'];
            return columns.indexOf(column);
        }

        // Filtering
        function applyFilters() {
            const courseFilter = document.getElementById('filter-course').value;
            const riskFilter = document.getElementById('filter-risk').value;
            const lateFilter = document.getElementById('filter-late').value;
            const searchFilter = document.getElementById('filter-search').value.toLowerCase();

            document.querySelectorAll('#student-table tbody tr').forEach(row => {
                const course = row.dataset.course;
                const risk = row.dataset.risk;
                const late = row.dataset.late;
                const name = row.children[0].textContent.toLowerCase();

                const matchCourse = !courseFilter || course === courseFilter;
                const matchRisk = !riskFilter || risk === riskFilter;
                const matchLate = !lateFilter || late === lateFilter;
                const matchSearch = !searchFilter || name.includes(searchFilter);

                row.style.display = (matchCourse && matchRisk && matchLate && matchSearch) ? '' : 'none';
            });
        }

        document.getElementById('filter-course').addEventListener('change', applyFilters);
        document.getElementById('filter-risk').addEventListener('change', applyFilters);
        document.getElementById('filter-late').addEventListener('change', applyFilters);
        document.getElementById('filter-search').addEventListener('input', applyFilters);
    </script>
</body>
</html>
'''

STUDENT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ student.student }} - {{ student.course }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 { margin-bottom: 5px; color: #fff; }
        .subtitle { color: #888; margin-bottom: 20px; }

        .nav { margin-bottom: 20px; }
        .nav a { color: #4da6ff; margin-right: 20px; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #252540;
            padding: 15px;
            border-radius: 8px;
        }
        .stat-value { font-size: 28px; font-weight: bold; }
        .stat-label { color: #888; font-size: 12px; margin-top: 5px; }

        .chart-container {
            background: #252540;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .chart-title { font-size: 16px; margin-bottom: 15px; }

        .bar-chart {
            display: flex;
            align-items: flex-end;
            height: 200px;
            gap: 3px;
            padding-bottom: 30px;
            position: relative;
        }
        .bar {
            flex: 1;
            background: linear-gradient(to top, #4da6ff, #44ff44);
            border-radius: 2px 2px 0 0;
            min-width: 8px;
            position: relative;
        }
        .bar:hover {
            opacity: 0.8;
        }
        .bar-label {
            position: absolute;
            bottom: -25px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 9px;
            color: #888;
            white-space: nowrap;
        }
        .bar:nth-child(7n)::after {
            content: attr(data-date);
            position: absolute;
            bottom: -25px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 9px;
            color: #888;
        }

        .y-axis {
            position: absolute;
            left: -40px;
            top: 0;
            bottom: 30px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            font-size: 10px;
            color: #666;
        }

        .metric-good { color: #88cc88; }
        .metric-ok { color: #cccc88; }
        .metric-bad { color: #cc8888; }

        .risk-Critical { color: #ff4444; }
        .risk-At-Risk { color: #ffaa00; }
        .risk-On-Track { color: #88cc88; }
        .risk-Strong { color: #44ff44; }

        .course-tag {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin-left: 10px;
        }
        .course-APHG { background: #2d5a27; }
        .course-APWH { background: #5a2727; }
        .course-APUSH { background: #27415a; }
        .course-APGOV { background: #5a4a27; }
    </style>
</head>
<body>
    <nav class="nav">
        <a href="/">← Back to Dashboard</a>
    </nav>

    <h1>{{ student.student }} <span class="course-tag course-{{ student.course }}">{{ student.course }}</span></h1>
    <p class="subtitle">
        Risk: <span class="risk-{{ student.risk|replace(' ', '-') }}">{{ student.risk }}</span>
        {% if student.pt_score %} | Practice Test: {{ student.pt_score }}{% endif %}
    </p>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value {% if student.aw_mastery and student.aw_mastery >= 70 %}metric-good{% elif student.aw_mastery and student.aw_mastery >= 50 %}metric-ok{% else %}metric-bad{% endif %}">
                {{ student.aw_mastery|default('—') }}{% if student.aw_mastery %}%{% endif %}
            </div>
            <div class="stat-label">Current Mastery</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ student.daily_xp|default('—') }}</div>
            <div class="stat-label">XP per School Day (14d avg)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ student.xp_to_90|default('—') }}</div>
            <div class="stat-label">XP to 90%</div>
        </div>
        <div class="stat-card">
            <div class="stat-value {% if student.projected_90 == 'Done' %}metric-good{% elif student.projected_90 == 'Never' %}metric-bad{% endif %}">
                {{ student.projected_90|default('—') }}
            </div>
            <div class="stat-label">Projected 90% Date</div>
        </div>
        <div class="stat-card">
            <div class="stat-value {% if student.progress and student.progress >= 90 %}metric-good{% elif student.progress and student.progress >= 70 %}metric-ok{% else %}metric-bad{% endif %}">
                {{ student.progress|default('—') }}{% if student.progress %}%{% endif %}
            </div>
            <div class="stat-label">Course Progress</div>
        </div>
        <div class="stat-card">
            <div class="stat-value {% if student.tb_mcq_accuracy and student.tb_mcq_accuracy >= 75 %}metric-good{% elif student.tb_mcq_accuracy and student.tb_mcq_accuracy >= 60 %}metric-ok{% elif student.tb_mcq_accuracy %}metric-bad{% endif %}">
                {{ student.tb_mcq_accuracy|default('—') }}{% if student.tb_mcq_accuracy %}%{% endif %}
            </div>
            <div class="stat-label">MCQ Accuracy (Timeback)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value {% if student.tb_frq_accuracy and student.tb_frq_accuracy >= 70 %}metric-good{% elif student.tb_frq_accuracy and student.tb_frq_accuracy >= 50 %}metric-ok{% elif student.tb_frq_accuracy %}metric-bad{% endif %}{% if student.frq_weak %} metric-bad{% endif %}">
                {{ student.tb_frq_accuracy|default('—') }}{% if student.tb_frq_accuracy %}%{% endif %}
                {% if student.frq_weak %}<span style="color: #ff4444; font-size: 12px;">⚠️</span>{% endif %}
            </div>
            <div class="stat-label">FRQ Accuracy (Timeback)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ student.current_xp|default(0) }}</div>
            <div class="stat-label">Total XP Earned</div>
        </div>
    </div>

    <div class="chart-container">
        <div class="chart-title">Daily XP (Last 30 Days)</div>
        <div class="bar-chart" style="margin-left: 45px;">
            {% set max_xp = timeseries|map(attribute='xp')|max if timeseries else 1 %}
            {% for day in timeseries %}
            <div class="bar"
                 style="height: {{ (day.xp / max_xp * 100) if max_xp > 0 else 0 }}%;"
                 data-date="{{ day.date[5:] }}"
                 title="{{ day.date }}: {{ day.xp }} XP ({{ day.items }} items)">
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="chart-container">
        <div class="chart-title">Projection Analysis</div>
        <p style="color: #888; margin-bottom: 10px;">
            At current rate of <strong>{{ student.daily_xp }}</strong> XP/day:
        </p>
        <ul style="color: #ccc; margin-left: 20px;">
            {% if student.xp_to_90 == 0 %}
            <li style="color: #44ff44;">Already at or above 90% mastery!</li>
            {% elif student.daily_xp and student.daily_xp > 0 %}
            <li>Need <strong>{{ student.xp_to_90 }}</strong> more XP to reach 90%</li>
            <li>At current pace: <strong>{{ (student.xp_to_90 / student.daily_xp)|round|int }}</strong> school days remaining</li>
            <li>Projected date: <strong>{{ student.projected_90 }}</strong></li>
            {% if student.projected_90 == 'Never' or student.projected_90 == '>2y' %}
            <li style="color: #ff4444;">Needs to increase daily XP significantly</li>
            {% endif %}
            {% else %}
            <li style="color: #ff4444;">No recent activity — cannot project</li>
            {% endif %}
        </ul>
    </div>

    <div class="chart-container">
        <div class="chart-title">Unit Progress (Frontier: Unit {{ student.frontier }})</div>
        <p style="color: #888; margin-bottom: 15px; font-size: 12px;">
            <span style="color: #44ff44;">■</span> Mastered (≥60%)
            <span style="color: #ff8844; margin-left: 15px;">■</span> Hole (before frontier, needs review)
            <span style="color: #666; margin-left: 15px;">■</span> Incomplete (at/after frontier)
            <span style="margin-left: 15px;">*</span> = non-CED (intro/exam prep)
        </p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            {% for ud in student.unit_details %}
            {% set is_hole = ud.combined < 60 and ud.unit|int < student.frontier %}
            {% set is_incomplete = ud.combined < 60 and ud.unit|int >= student.frontier %}
            {% set is_mastered = ud.combined >= 60 %}
            <div style="
                width: 70px;
                padding: 8px;
                border-radius: 6px;
                text-align: center;
                background: {% if is_hole %}#3d2a1a{% elif is_incomplete %}#252540{% else %}#1a3d1a{% endif %};
                border: 2px solid {% if is_hole %}#ff8844{% elif is_incomplete %}#444{% else %}#44ff44{% endif %};
            ">
                <div style="font-weight: bold; font-size: 14px; color: {% if is_hole %}#ff8844{% elif is_incomplete %}#888{% else %}#44ff44{% endif %};">
                    U{{ ud.unit }}{% if ud.non_ced %}*{% endif %}
                </div>
                <div style="font-size: 18px; font-weight: bold; color: {% if is_hole %}#ff8844{% elif is_incomplete %}#666{% else %}#44ff44{% endif %};">
                    {{ ud.combined|int }}%
                </div>
                <div style="font-size: 9px; color: #888; margin-top: 2px;">
                    {% if is_hole %}HOLE{% elif is_incomplete %}TODO{% else %}OK{% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        {% if student.weak_units %}
        <p style="color: #ff8844; margin-top: 15px; font-size: 13px;">
            <strong>Holes detected:</strong> Units passed but not learned — revisit before continuing.
        </p>
        {% elif student.incomplete %}
        <p style="color: #888; margin-top: 15px; font-size: 13px;">
            No holes — just continue through remaining units.
        </p>
        {% endif %}
    </div>

    {# Recommendation box - show for late students OR on-track students with action items #}
    {% if student.late_for_pt or student.recommendation in ['Hole-Fill', 'FRQ', 'Hole+FRQ'] %}
    <div class="chart-container" style="border-left: 4px solid {% if student.recommendation == 'Impossible' %}#ff4444{% elif student.recommendation == 'Hole+FRQ' %}#ff88ff{% elif student.recommendation in ['Holes', 'Hole-Fill'] %}#ff8844{% elif student.recommendation == 'FRQ' %}#aa88ff{% elif student.recommendation == 'PT' %}#44dddd{% elif student.recommendation == 'Stay' %}#44ff44{% else %}#ffaa00{% endif %};">
        <div class="chart-title" style="color: {% if student.recommendation == 'Impossible' %}#ff4444{% elif student.recommendation == 'Hole+FRQ' %}#ff88ff{% elif student.recommendation in ['Holes', 'Hole-Fill'] %}#ff8844{% elif student.recommendation == 'FRQ' %}#aa88ff{% elif student.recommendation == 'PT' %}#44dddd{% elif student.recommendation == 'Stay' %}#44ff44{% else %}#ffaa00{% endif %};">
            Recommendation: {{ student.recommendation }}
        </div>
        <p style="color: #ccc; margin: 10px 0;">{{ student.rec_detail }}</p>

        {% if student.rec_required_xp %}
        <p style="color: #888; margin: 10px 0;">
            Need <strong>{{ student.rec_required_xp }}</strong> XP/day to make Apr 16 deadline
            ({{ student.rec_days }} school days remaining)
        </p>
        {% endif %}

        {% if student.weak_units %}
        <div style="margin-top: 15px;">
            <p style="color: #ff8844; font-weight: bold;">Holes (units passed but not learned):</p>
            <ul style="color: #ccc; margin-left: 20px; margin-top: 5px;">
                {% for unit in student.weak_units %}
                <li>{{ unit.unit_name }}{% if unit.non_ced %}*{% endif %} — <span style="color: #ff4444;">{{ unit.mastery }}%</span></li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        {% if student.rec_courses %}
        <div style="margin-top: 15px; padding: 15px; background: #1a1a2e; border-radius: 8px;">
            <p style="color: #44ff44; font-weight: bold;">Recommended Mini-Courses:</p>
            <ul style="color: #ccc; margin-left: 20px; margin-top: 5px;">
                {% for course in student.rec_courses %}
                <li><strong>{{ course.name }}</strong> <span style="color: #888;">({{ course.id }})</span></li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        {% if student.recommendation in ['FRQ', 'Hole+FRQ'] %}
        <div style="margin-top: 15px; padding: 15px; background: #1a1a2e; border-radius: 8px;">
            <p style="color: #aa88ff; font-weight: bold;">FRQ Practice Recommended</p>
            <p style="color: #ccc; margin-top: 5px;">
                MCQ: <strong>{{ student.tb_mcq_accuracy|default('—') }}%</strong> |
                FRQ: <strong>{{ student.tb_frq_accuracy|default('—') }}%</strong>
            </p>
            <p style="color: #888; margin-top: 5px; font-size: 12px;">
                Focus on essay structure, argument development, and evidence use.
            </p>
        </div>
        {% endif %}
    </div>
    {% elif student.recommendation == 'Stay' %}
    <div class="chart-container" style="border-left: 4px solid #44ff44;">
        <div class="chart-title" style="color: #44ff44;">
            Recommendation: Stay the Course
        </div>
        <p style="color: #ccc; margin: 10px 0;">{{ student.rec_detail }}</p>
        <p style="color: #888; margin-top: 10px; font-size: 12px;">
            No weak units detected. MCQ and FRQ performance balanced. Keep up the current approach!
        </p>
    </div>
    {% endif %}
</body>
</html>
'''

COACHING_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Coaching Calls</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 { margin-bottom: 10px; color: #fff; }
        .subtitle { color: #888; margin-bottom: 20px; }
        .nav { margin-bottom: 20px; }
        .nav a { color: #4da6ff; margin-right: 20px; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }
        p { margin: 10px 0; color: #888; }
        a { color: #4da6ff; }
    </style>
</head>
<body>
    <h1>Coaching Calls</h1>
    <p class="subtitle">Schedule and call management</p>

    <nav class="nav">
        <a href="/">Dashboard</a>
        <a href="/coaching">Coaching Calls</a>
    </nav>

    <p>Coaching call functionality moved here. <a href="http://localhost:5000">Open original dashboard</a> for full features.</p>
</body>
</html>
'''


@app.route('/')
def dashboard():
    data = load_all_data()
    students = build_unified_table(data)

    # Sort by risk then name
    risk_order = {'Critical': 0, 'At Risk': 1, 'On Track': 2, 'Strong': 3, 'Unknown': 4}
    students.sort(key=lambda x: (risk_order.get(x['risk'], 5), x['student']))

    # Summary stats
    summary = {
        'critical': len([s for s in students if s['risk'] == 'Critical']),
        'at_risk': len([s for s in students if s['risk'] == 'At Risk']),
        'on_track': len([s for s in students if s['risk'] in ('On Track', 'Strong')]),
        'no_pt': len([s for s in students if s['pt_score'] is None]),
        'late_for_pt': len([s for s in students if s['late_for_pt']])
    }

    return render_template_string(DASHBOARD_HTML, students=students, summary=summary)


@app.route('/student/<student_name>/<course>')
def student_detail(student_name, course):
    data = load_all_data()
    students = build_unified_table(data)

    # Find the student
    student = None
    for s in students:
        if s['student'] == student_name and s['course'] == course:
            student = s
            break

    if not student:
        return redirect('/')

    # Get time series
    timeseries = get_student_timeseries(data, student_name, course)

    return render_template_string(STUDENT_HTML, student=student, timeseries=timeseries)


@app.route('/coaching')
def coaching():
    return render_template_string(COACHING_HTML)


@app.route('/api/students')
def api_students():
    data = load_all_data()
    students = build_unified_table(data)
    return jsonify(students)


@app.route('/api/student/<student_name>/<course>/timeseries')
def api_student_timeseries(student_name, course):
    data = load_all_data()
    timeseries = get_student_timeseries(data, student_name, course)
    return jsonify(timeseries)


REFRESH_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Data Refresh - AP Social Studies</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 { margin-bottom: 10px; color: #fff; }
        .subtitle { color: #888; margin-bottom: 20px; }
        .nav { margin-bottom: 20px; }
        .nav a { color: #4da6ff; margin-right: 20px; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }
        .card {
            background: #252540;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .card h2 { margin-bottom: 10px; font-size: 18px; }
        .success { color: #44ff44; }
        .error { color: #ff4444; }
        .pending { color: #ffaa00; }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #4da6ff;
            color: #fff;
            text-decoration: none;
            border-radius: 6px;
            margin-right: 10px;
            margin-top: 10px;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover { background: #3d8cd9; }
        .btn-secondary { background: #6b7280; }
        .btn-secondary:hover { background: #555; }
        .stats { color: #888; font-size: 14px; margin-top: 10px; }
        .note { color: #888; font-size: 12px; margin-top: 15px; padding: 10px; background: #1a1a2e; border-radius: 4px; }
    </style>
</head>
<body>
    <nav class="nav">
        <a href="/">← Back to Dashboard</a>
    </nav>

    <h1>Data Refresh</h1>
    <p class="subtitle">Pull latest data from Timeback and Austin Way</p>

    {% if results %}
    <div class="card">
        <h2>Refresh Results</h2>

        <h3 style="margin-top: 15px;">Austin Way</h3>
        {% if results.austin_way.success %}
        <p class="success">Success: {{ results.austin_way.message }}</p>
        {% else %}
        <p class="error">Failed: {{ results.austin_way.message }}</p>
        {% endif %}

        <h3 style="margin-top: 15px;">Timeback</h3>
        {% if results.timeback.success %}
        <p class="success">Success: {{ results.timeback.message }}</p>
        {% else %}
        <p class="error">Failed: {{ results.timeback.message }}</p>
        {% endif %}

        <p class="stats">Refreshed at {{ results.timestamp }}</p>

        <a href="/" class="btn" style="margin-top: 20px;">View Updated Dashboard</a>
    </div>
    {% else %}
    <div class="card">
        <h2>Refresh Options</h2>
        <p style="margin-bottom: 15px;">Click below to pull fresh data from external systems.</p>

        <a href="/refresh/all" class="btn">Refresh All Data</a>
        <a href="/refresh/austin-way" class="btn btn-secondary">Austin Way Only</a>
        <a href="/refresh/timeback" class="btn btn-secondary">Timeback Only</a>

        <div class="note">
            <strong>Requirements:</strong><br>
            - Austin Way: Valid auth cookie (auto-harvested from browser or in <code>austin_way_auth.txt</code>)<br>
            - Timeback: <code>TIMEBACK_CLIENT_ID</code> and <code>TIMEBACK_CLIENT_SECRET</code> in <code>.env</code>
        </div>

        <h3 style="margin-top: 20px;">Austin Way Auth</h3>
        <p style="margin: 10px 0; color: #888;">If Austin Way auth fails, sign into <a href="https://www.aphistoryforge.com/guide/" target="_blank" style="color: #4da6ff;">aphistoryforge.com</a>, then paste the <code>aph_auth</code> cookie below.</p>
        <form action="/refresh/save-cookie" method="POST" style="margin-top: 10px;">
            <input type="text" name="cookie" placeholder="Paste aph_auth cookie value here" style="width: 100%; padding: 10px; border: 1px solid #444; border-radius: 4px; background: #1a1a2e; color: #fff; font-family: monospace; margin-bottom: 10px;">
            <button type="submit" class="btn btn-secondary">Save Cookie</button>
        </form>
        <p style="margin-top: 10px; color: #666; font-size: 11px;">DevTools → Application → Cookies → api.aphistoryforge.com → aph_auth</p>
    </div>
    {% endif %}
</body>
</html>
'''


def backup_data_files():
    """Backup CSV files before refresh."""
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = DATA_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)

    backed_up = []

    # Backup Austin Way
    aw_file = AUSTIN_WAY_OUTPUT_FILE
    if aw_file.exists():
        backup_path = backup_dir / f'austin_way_mastery_{timestamp}.csv'
        shutil.copy(aw_file, backup_path)
        backed_up.append('austin_way_mastery.csv')

    # Backup Timeback
    tb_file = DATA_DIR / 'ap_social_studies_learning_data.csv'
    if tb_file.exists():
        backup_path = backup_dir / f'ap_social_studies_learning_data_{timestamp}.csv'
        shutil.copy(tb_file, backup_path)
        backed_up.append('ap_social_studies_learning_data.csv')

    return backed_up


@app.route('/refresh')
def refresh():
    """One-click refresh: backup, refresh all, redirect to dashboard on success."""
    # Backup first
    backup_data_files()

    # Refresh both sources
    aw_result = refresh_austin_way()
    tb_result = refresh_timeback()

    # If both succeeded, redirect to dashboard
    if aw_result["success"] and tb_result["success"]:
        return redirect('/')

    # If there's an error, show the error page
    results = {
        "austin_way": aw_result,
        "timeback": tb_result,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return render_template_string(REFRESH_ERROR_HTML, results=results)


REFRESH_ERROR_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Refresh Error - AP Social Studies</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 { margin-bottom: 10px; color: #fff; }
        .card {
            background: #252540;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            max-width: 700px;
        }
        .success { color: #44ff44; }
        .error { color: #ff4444; }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #4da6ff;
            color: #fff;
            text-decoration: none;
            border-radius: 6px;
            margin-right: 10px;
            margin-top: 10px;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover { background: #3d8cd9; }
        .btn-secondary { background: #6b7280; }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #444;
            border-radius: 4px;
            background: #1a1a2e;
            color: #fff;
            font-family: monospace;
            margin: 10px 0;
        }
        .note { color: #888; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Refresh Error</h1>

    <div class="card">
        <h3>Austin Way</h3>
        {% if results.austin_way.success %}
        <p class="success">OK: {{ results.austin_way.message }}</p>
        {% else %}
        <p class="error">Failed: {{ results.austin_way.message }}</p>
        {% if 'cookie' in results.austin_way.message|lower or 'auth' in results.austin_way.message|lower or '401' in results.austin_way.message %}
        <p style="margin-top: 15px; color: #ccc;">Sign into <a href="https://www.aphistoryforge.com/guide/" target="_blank" style="color: #4da6ff;">aphistoryforge.com</a>, then paste the <code>aph_auth</code> cookie:</p>
        <form action="/refresh/save-cookie" method="POST">
            <input type="text" name="cookie" placeholder="Paste aph_auth cookie value here">
            <button type="submit" class="btn">Save Cookie & Retry</button>
        </form>
        <p class="note">DevTools → Application → Cookies → api.aphistoryforge.com → aph_auth</p>
        {% endif %}
        {% endif %}
    </div>

    <div class="card">
        <h3>Timeback</h3>
        {% if results.timeback.success %}
        <p class="success">OK: {{ results.timeback.message }}</p>
        {% else %}
        <p class="error">Failed: {{ results.timeback.message }}</p>
        {% endif %}
    </div>

    <a href="/" class="btn btn-secondary">Back to Dashboard</a>
    <a href="/refresh" class="btn">Retry Refresh</a>
</body>
</html>
'''


@app.route('/refresh/austin-way')
def refresh_austin_way_route():
    """Refresh Austin Way data only, then redirect or show error."""
    backup_data_files()
    result = refresh_austin_way()
    if result["success"]:
        return redirect('/')
    results = {
        "austin_way": result,
        "timeback": {"success": True, "message": "Not requested", "rows": 0},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return render_template_string(REFRESH_ERROR_HTML, results=results)


@app.route('/refresh/timeback')
def refresh_timeback_route():
    """Refresh Timeback data only, then redirect or show error."""
    backup_data_files()
    result = refresh_timeback()
    if result["success"]:
        return redirect('/')
    results = {
        "austin_way": {"success": True, "message": "Not requested", "rows": 0},
        "timeback": result,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return render_template_string(REFRESH_ERROR_HTML, results=results)


@app.route('/refresh/save-cookie', methods=['POST'])
def save_cookie_route():
    """Save Austin Way cookie from form input, then retry full refresh."""
    cookie = request.form.get('cookie', '').strip()
    if cookie:
        # Strip 'aph_auth=' prefix if present
        if cookie.startswith('aph_auth='):
            cookie = cookie[9:]
        AUSTIN_WAY_AUTH_FILE.write_text(cookie)
    return redirect('/refresh')


@app.route('/refresh/harvest-cookie')
def harvest_cookie_route():
    """Harvest Austin Way cookie from browser."""
    result = harvest_austin_way_cookie()

    harvest_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cookie Harvest - AP Social Studies</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #1a1a2e;
                color: #eee;
                padding: 20px;
            }
            .nav { margin-bottom: 20px; }
            .nav a { color: #4da6ff; text-decoration: none; }
            .card {
                background: #252540;
                padding: 20px;
                border-radius: 8px;
                max-width: 600px;
            }
            .success { color: #44ff44; }
            .error { color: #ff4444; }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                background: #4da6ff;
                color: #fff;
                text-decoration: none;
                border-radius: 6px;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <nav class="nav"><a href="/refresh">← Back to Refresh</a></nav>
        <div class="card">
            <h2>Cookie Harvest</h2>
            {% if result.success %}
            <p class="success" style="margin: 15px 0;">{{ result.message }}</p>
            <a href="/refresh/austin-way" class="btn">Now Refresh Austin Way Data</a>
            {% else %}
            <p class="error" style="margin: 15px 0;">{{ result.message }}</p>
            <p style="margin-top: 15px; color: #888;">
                1. Open <a href="https://www.aphistoryforge.com/guide/" target="_blank" style="color: #4da6ff;">aphistoryforge.com/guide</a><br>
                2. Sign in with your account<br>
                3. Come back here and click the button again
            </p>
            <a href="/refresh/harvest-cookie" class="btn">Try Again</a>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(harvest_html, result=result)


if __name__ == '__main__':
    print("AP Social Studies Dashboard")
    print("=" * 50)
    print("Open: http://localhost:5001")
    print()
    app.run(debug=True, port=5001)
