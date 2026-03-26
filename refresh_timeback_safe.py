#!/usr/bin/env python3
"""
Safe Timeback refresh - fetches latest data and writes to temp file for review.
Does NOT overwrite the original file.

Usage:
    python refresh_timeback_safe.py
    # Review the output, then manually copy if it looks good
"""

import os
import re
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'adam_ss_bundle'

# API config
TOKEN_URL = "https://prod-beyond-timeback-api-2-idp.auth.us-east-1.amazoncognito.com/oauth2/token"
API_BASE = "https://api.alpha-1edtech.ai"


def load_credentials():
    """Load Timeback credentials from .env file."""
    env_file = BASE_DIR / '.env'
    content = env_file.read_text().strip()
    data = {}
    for line in content.split('\n'):
        line = line.strip().rstrip(',')
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip().strip('"')
            val = val.strip().strip('"')
            data[key] = val
    return data.get('client_id'), data.get('client_secret')


def get_token(client_id, client_secret):
    """Get OAuth token."""
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def resource_key(tb_id):
    """Extract resource key (e.g., 'r109177') from item ID."""
    m = re.search(r'(r\d+)', str(tb_id))
    return m.group(1) if m else str(tb_id)


def fetch_all_progress(token, enrollments):
    """Fetch progress for all enrollments from API."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    all_progress = []
    total = len(enrollments)

    for idx, (_, row) in enumerate(enrollments.iterrows()):
        student_tb_id = row['student_timeback_id']
        student_alpha_id = row['student_alpha_id']
        course_tb_id = row['course_timeback_id']

        print(f"  [{idx+1}/{total}] {student_alpha_id} / {course_tb_id}...", end=" ")

        try:
            url = f"{API_BASE}/powerpath/lessonPlans/getCourseProgress/{course_tb_id}/student/{student_tb_id}"
            resp = requests.get(url, headers=headers, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                line_items = data.get('lineItems', [])

                completed_count = 0
                for item in line_items:
                    item_tb_id = item.get('courseComponentResourceSourcedId', '')
                    results = item.get('results', [])

                    if results:
                        # Get latest result by scoreDate
                        latest = max(results, key=lambda x: x.get('scoreDate', ''))
                        completed_at = latest.get('scoreDate')
                        text_score = latest.get('textScore')
                        score = latest.get('score')

                        # Only use score as accuracy for graded items (textScore is null)
                        accuracy = score if text_score is None and score is not None else None

                        all_progress.append({
                            'student_alpha_id': student_alpha_id,
                            'student_timeback_id': student_tb_id,
                            'course_timeback_id': course_tb_id,
                            'item_tb_id': item_tb_id,
                            'rkey': resource_key(item_tb_id),
                            'completed_at': completed_at,
                            'accuracy': accuracy,
                        })
                        completed_count += 1

                print(f"{completed_count} completed")
            else:
                print(f"ERROR {resp.status_code}")

        except Exception as e:
            print(f"ERROR: {e}")

    return all_progress


def main():
    print("Timeback Safe Refresh")
    print("=" * 60)
    print()

    # Load credentials
    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        print("ERROR: No credentials found in .env")
        return

    # Get token
    print("Getting auth token...")
    token = get_token(client_id, client_secret)
    print("OK")
    print()

    # Load enrollments
    enrollments_file = DATA_DIR / 'ap_social_studies_enrollments.csv'
    enrollments = pd.read_csv(enrollments_file)
    print(f"Loaded {len(enrollments)} enrollments")

    # Load lesson details (scaffold)
    lesson_details_file = DATA_DIR / 'ap_social_studies_lesson_details_combined.csv'
    lesson_details = pd.read_csv(lesson_details_file)
    lesson_details['rkey'] = lesson_details['item_tb_id'].apply(resource_key)
    print(f"Loaded {len(lesson_details)} lesson items")
    print()

    # Fetch all progress
    print("Fetching progress from API...")
    all_progress = fetch_all_progress(token, enrollments)
    print()
    print(f"Total completed items from API: {len(all_progress)}")

    if not all_progress:
        print("ERROR: No progress data returned!")
        return

    # Build progress dataframe
    progress_df = pd.DataFrame(all_progress)

    # Find completion date range
    dates = pd.to_datetime(progress_df['completed_at']).dt.date
    print(f"Completion date range: {dates.min()} to {dates.max()}")
    print()

    # Build scaffold by crossing enrollments with lesson details
    # Use only needed columns from enrollments to avoid duplication
    enroll_cols = ['student_alpha_id', 'student_timeback_id', 'course_timeback_id']
    scaffold = enrollments[enroll_cols].merge(
        lesson_details,
        on='course_timeback_id',
        how='inner'
    )
    print(f"Scaffold rows: {len(scaffold)}")

    # Merge with progress (left join to keep all scaffold rows)
    learning_data = scaffold.merge(
        progress_df[['student_alpha_id', 'course_timeback_id', 'rkey', 'completed_at', 'accuracy']],
        on=['student_alpha_id', 'course_timeback_id', 'rkey'],
        how='left'
    )

    completed_rows = learning_data['completed_at'].notna().sum()
    print(f"Rows with completion: {completed_rows}")
    print()

    # Compare with existing file
    existing_file = DATA_DIR / 'ap_social_studies_learning_data.csv'
    if existing_file.exists():
        existing = pd.read_csv(existing_file)
        existing_completed = existing['completed_at'].notna().sum()
        print("COMPARISON WITH EXISTING FILE:")
        print(f"  Existing rows: {len(existing)}, completed: {existing_completed}")
        print(f"  New rows: {len(learning_data)}, completed: {completed_rows}")

        if completed_rows > existing_completed:
            print(f"  +{completed_rows - existing_completed} new completions")
        elif completed_rows < existing_completed:
            print(f"  WARNING: {existing_completed - completed_rows} FEWER completions!")
    print()

    # Save to temp file
    output_file = DATA_DIR / 'ap_social_studies_learning_data_NEW.csv'

    # Reorder columns to match expected format
    col_order = [
        'student_alpha_id', 'student_timeback_id', 'course_on_timeback', 'course_timeback_id',
        'unit_title', 'unit_sort_order', 'lesson_title', 'item_title', 'item_tb_id',
        'test_type', 'accuracy', 'completed_at'
    ]
    # Only include columns that exist
    col_order = [c for c in col_order if c in learning_data.columns]
    learning_data = learning_data[col_order]

    learning_data['snapshot_date'] = datetime.now().strftime('%Y-%m-%d')
    learning_data.to_csv(output_file, index=False)

    print(f"Saved to: {output_file}")
    print()
    print("Review the file, then if it looks good:")
    print(f"  copy {output_file.name} ap_social_studies_learning_data.csv")


if __name__ == '__main__':
    main()
