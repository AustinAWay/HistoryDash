#!/usr/bin/env python3
"""
Austin Way Data Scraper

Fetches student mastery data from aphistoryforge.com API and outputs to CSV.

Usage:
    1. Copy your aph_auth cookie value to austin_way_auth.txt
    2. Run: python austin_way_scraper.py
    3. Output: austin_way_mastery.csv
"""

import json
import csv
import time
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
AUTH_FILE = BASE_DIR / 'austin_way_auth.txt'
OUTPUT_FILE = BASE_DIR / 'austin_way_mastery.csv'

API_BASE = 'https://api.aphistoryforge.com/api/guide'

# Headers to mimic browser request
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Origin': 'https://www.aphistoryforge.com',
    'Referer': 'https://www.aphistoryforge.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
}


def load_auth_cookie():
    """Load the aph_auth cookie from file."""
    if not AUTH_FILE.exists():
        print(f"ERROR: Auth file not found: {AUTH_FILE}")
        print("Create this file with your aph_auth cookie value (just the token, not 'aph_auth=')")
        return None

    token = AUTH_FILE.read_text().strip()
    if not token:
        print("ERROR: Auth file is empty")
        return None

    return token


def get_students(session):
    """Fetch list of all students from dashboard."""
    resp = session.get(f'{API_BASE}/dashboard')
    resp.raise_for_status()
    data = resp.json()
    return data.get('students', [])


def get_student_details(session, student_id, days=30):
    """Fetch detailed mastery data for a single student."""
    resp = session.get(f'{API_BASE}/students/{student_id}', params={'days': days})
    resp.raise_for_status()
    return resp.json()


def parse_student_data(data):
    """Parse student JSON into flat rows for CSV."""
    rows = []

    student = data.get('student', {})
    student_name = student.get('displayName', 'Unknown')
    student_email = student.get('email', '')
    student_courses = student.get('courses', [])

    mastery = data.get('mastery', {})
    overall_pct = mastery.get('overallPct', 0)

    skill_breakdown = data.get('skillBreakdown', [])

    # Get per-course mastery from masteryOverTime (most recent per course)
    mastery_over_time = data.get('masteryOverTime', [])
    course_mastery = {}
    for entry in mastery_over_time:
        course_id = entry.get('courseId')
        if course_id:
            # Keep the most recent (they're ordered by date)
            course_mastery[course_id] = {
                'averagePct': entry.get('averagePct', 0),
                'totalSkills': entry.get('totalSkills', 0),
                'masteredSkills': entry.get('masteredSkills', 0),
            }

    # If no skill breakdown, still create a summary row
    if not skill_breakdown:
        for course in student_courses:
            cm = course_mastery.get(course, {})
            rows.append({
                'student_name': student_name,
                'student_email': student_email,
                'course': course,
                'unit_id': '',
                'unit_name': '(No data)',
                'mastered': 0,
                'in_progress': 0,
                'not_learned': 0,
                'total': 0,
                'unit_mastery_pct': 0,
                'course_mastery_pct': cm.get('averagePct', 0),
                'overall_mastery_pct': overall_pct,
            })
        return rows

    # Process skill breakdown
    for unit in skill_breakdown:
        course_id = unit.get('courseId', '')
        unit_id = unit.get('unitId', '')
        unit_name = unit.get('unitName', '')
        mastered = unit.get('mastered', 0)
        in_progress = unit.get('inProgress', 0)
        not_learned = unit.get('notLearned', 0)
        total = unit.get('total', 0)

        unit_mastery_pct = round((mastered / total) * 100, 1) if total > 0 else 0

        cm = course_mastery.get(course_id, {})

        rows.append({
            'student_name': student_name,
            'student_email': student_email,
            'course': course_id,
            'unit_id': unit_id,
            'unit_name': unit_name,
            'mastered': mastered,
            'in_progress': in_progress,
            'not_learned': not_learned,
            'total': total,
            'unit_mastery_pct': unit_mastery_pct,
            'course_mastery_pct': cm.get('averagePct', 0),
            'overall_mastery_pct': overall_pct,
        })

    return rows


def main():
    print("Austin Way Data Scraper")
    print("=" * 50)

    # Load auth
    auth_token = load_auth_cookie()
    if not auth_token:
        return

    # Create session with auth cookie
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.set('aph_auth', auth_token, domain='api.aphistoryforge.com')

    # Fetch student list
    print("\nFetching student list...")
    try:
        students = get_students(session)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR fetching students: {e}")
        print("Your auth cookie may have expired. Get a fresh one from your browser.")
        return

    print(f"Found {len(students)} students")

    # Fetch each student's details
    all_rows = []
    for i, student in enumerate(students):
        student_id = student.get('id')
        student_name = student.get('displayName', 'Unknown')

        print(f"  [{i+1}/{len(students)}] {student_name}...", end=' ')

        try:
            details = get_student_details(session, student_id)
            rows = parse_student_data(details)
            all_rows.extend(rows)
            print(f"OK ({len(rows)} units)")
        except requests.exceptions.HTTPError as e:
            print(f"ERROR: {e}")

        # Be nice to the API
        time.sleep(0.2)

    # Write CSV
    if not all_rows:
        print("\nNo data to write!")
        return

    fieldnames = [
        'student_name', 'student_email', 'course', 'unit_id', 'unit_name',
        'mastered', 'in_progress', 'not_learned', 'total',
        'unit_mastery_pct', 'course_mastery_pct', 'overall_mastery_pct'
    ]

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows to {OUTPUT_FILE}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY BY COURSE")
    print("=" * 50)

    from collections import defaultdict
    course_stats = defaultdict(lambda: {'students': set(), 'total_mastered': 0, 'total_skills': 0})

    for row in all_rows:
        course = row['course']
        course_stats[course]['students'].add(row['student_email'])
        course_stats[course]['total_mastered'] += row['mastered']
        course_stats[course]['total_skills'] += row['total']

    for course, stats in sorted(course_stats.items()):
        n_students = len(stats['students'])
        avg_mastery = round((stats['total_mastered'] / stats['total_skills']) * 100, 1) if stats['total_skills'] > 0 else 0
        print(f"  {course}: {n_students} students, {avg_mastery}% average mastery")


if __name__ == '__main__':
    main()
