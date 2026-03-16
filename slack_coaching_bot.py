#!/usr/bin/env python3
"""
Slack Coaching Bot - Send reminders and questions to AP students

SETUP:
1. Go to https://api.slack.com/apps and click "Create New App" > "From scratch"
2. Name it "AP Coaching Bot", select your workspace
3. Go to "OAuth & Permissions" > "Scopes" > "Bot Token Scopes" and add:
   - chat:write
   - users:read
   - users:read.email
4. Click "Install to Workspace" and authorize
5. Copy the "Bot User OAuth Token" (starts with xoxb-)
6. Set it as environment variable: set SLACK_BOT_TOKEN=xoxb-your-token-here
   Or paste it directly in this script (less secure)

USAGE:
  python slack_coaching_bot.py --weekly          # Send weekly schedule reminders
  python slack_coaching_bot.py --questions       # Send question files for this week's calls
  python slack_coaching_bot.py --test            # Test with one student (Gus)
  python slack_coaching_bot.py --list            # List all students and their Slack status
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    print("Please install slack_sdk: pip install slack_sdk")
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Set your token here OR use environment variable SLACK_BOT_TOKEN
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', 'xoxb-YOUR-TOKEN-HERE')

# Timezone for schedule (US Central)
TIMEZONE = 'America/Chicago'

# Questions folder path
QUESTIONS_DIR = Path(__file__).parent / 'student_plans_v3' / 'questions'

# Student data: name -> (email, slack_email if different)
STUDENTS = {
    'Gus Castillo': {'email': 'gus.castillo@alpha.school', 'course': 'AP Human Geography'},
    'Emma Cotner': {'email': 'emma.cotner@alpha.school', 'course': 'AP World History'},
    'Jackson Price': {'email': 'jackson.price@alpha.school', 'course': 'AP World History'},
    'Boris Dudarev': {'email': 'boris.dudarev@alpha.school', 'course': 'AP Human Geography'},
    'Sydney Barba': {'email': 'sydney.barba@alpha.school', 'course': 'AP Human Geography'},
    'Branson Pfiester': {'email': 'branson.pfiester@alpha.school', 'course': 'AP Human Geography', 'tier': 'Moderate'},
    'Saeed Tarawneh': {'email': 'said.tarawneh@alpha.school', 'course': 'AP World History'},
    'Aheli Shah': {'email': 'aheli.shah@alpha.school', 'course': 'AP Human Geography'},
    'Ella Dietz': {'email': 'ella.dietz@alpha.school', 'course': 'AP World History'},
    'Stella Cole': {'email': 'stella.cole@alpha.school', 'course': 'AP World History'},
    'Erika Rigby': {'email': 'erika.rigby@alpha.school', 'course': 'AP Human Geography'},
    'Grady Swanson': {'email': 'grady.swanson@alpha.school', 'course': 'AP Human Geography'},
    'Zayen Szpitalak': {'email': 'zayen.szpitalak@alpha.school', 'course': 'AP Human Geography'},
    'Adrienne Laswell': {'email': 'adrienne.laswell@alpha.school', 'course': 'AP Human Geography'},
    'Austin Lin': {'email': 'austin.lin@alpha.school', 'course': 'AP Human Geography'},
    'Jessica Owenby': {'email': 'jessica.owenby@alpha.school', 'course': 'AP Human Geography'},
    'Cruce Saunders IV': {'email': 'cruce.saunders@alpha.school', 'course': 'AP US History'},
    'Kavin Lingham': {'email': 'kavin.lingham@alpha.school', 'course': 'AP World History'},
    'Stella Grams': {'email': 'stella.grams@alpha.school', 'course': 'AP World History'},
    'Jacob Kuchinsky': {'email': 'jacob.kuchinsky@alpha.school', 'course': 'AP Human Geography'},
    'Luca Sanchez': {'email': 'luca.sanchez@alpha.school', 'course': 'AP Human Geography'},
    'Ali Romman': {'email': 'ali.romman@alpha.school', 'course': 'AP Human Geography'},
    'Benny Valles': {'email': 'benjamin.valles@alpha.school', 'course': 'AP Human Geography'},
    'Vera Li': {'email': 'vera.li@alpha.school', 'course': 'AP Human Geography'},
    'Emily Smith': {'email': 'emily.smith@alpha.school', 'course': 'AP US Government'},
    'Paty Margain-Junco': {'email': 'paty.margainjunco@alpha.school', 'course': 'AP US History'},
    'Michael Cai': {'email': 'michael.cai@alpha.school', 'course': 'AP World History'},
}

# Full schedule with week numbers for question file mapping
SCHEDULE = [
    # Week of Mar 9
    {'date': (2026, 3, 10), 'time': '08:20', 'student': 'Gus Castillo', 'week': 1},
    {'date': (2026, 3, 13), 'time': '10:30', 'student': 'Emma Cotner', 'week': 1},
    {'date': (2026, 3, 11), 'time': '09:45', 'student': 'Jackson Price', 'week': 1},
    {'date': (2026, 3, 11), 'time': '08:35', 'student': 'Boris Dudarev', 'week': 1},
    {'date': (2026, 3, 11), 'time': '09:05', 'student': 'Sydney Barba', 'week': 1},
    {'date': (2026, 3, 12), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 1},
    {'date': (2026, 3, 12), 'time': '09:05', 'student': 'Aheli Shah', 'week': 1},
    {'date': (2026, 3, 13), 'time': '10:00', 'student': 'Ella Dietz', 'week': 1},

    # Week of Mar 16
    {'date': (2026, 3, 17), 'time': '08:00', 'student': 'Stella Cole', 'week': 1},
    {'date': (2026, 3, 17), 'time': '08:45', 'student': 'Erika Rigby', 'week': 1},
    {'date': (2026, 3, 16), 'time': '09:00', 'student': 'Grady Swanson', 'week': 1},
    {'date': (2026, 3, 16), 'time': '08:50', 'student': 'Zayen Szpitalak', 'week': 1},
    {'date': (2026, 3, 18), 'time': '09:40', 'student': 'Branson Pfiester', 'week': 1},
    {'date': (2026, 3, 19), 'time': '08:20', 'student': 'Gus Castillo', 'week': 2},
    {'date': (2026, 3, 19), 'time': '09:35', 'student': 'Emma Cotner', 'week': 2},
    {'date': (2026, 3, 20), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 2},
    {'date': (2026, 3, 20), 'time': '08:35', 'student': 'Adrienne Laswell', 'week': 1},
    {'date': (2026, 3, 20), 'time': '09:05', 'student': 'Austin Lin', 'week': 1},

    # Week of Mar 23
    {'date': (2026, 3, 25), 'time': '08:00', 'student': 'Boris Dudarev', 'week': 2},
    {'date': (2026, 3, 25), 'time': '08:35', 'student': 'Sydney Barba', 'week': 2},
    {'date': (2026, 3, 26), 'time': '08:20', 'student': 'Gus Castillo', 'week': 3},
    {'date': (2026, 3, 26), 'time': '09:35', 'student': 'Emma Cotner', 'week': 3},
    {'date': (2026, 3, 27), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 3},
    {'date': (2026, 3, 27), 'time': '08:35', 'student': 'Jessica Owenby', 'week': 1},
    {'date': (2026, 3, 27), 'time': '09:05', 'student': 'Cruce Saunders IV', 'week': 1},

    # Week of Mar 30
    {'date': (2026, 4, 1), 'time': '08:00', 'student': 'Zayen Szpitalak', 'week': 2},
    {'date': (2026, 4, 1), 'time': '08:35', 'student': 'Stella Cole', 'week': 2},
    {'date': (2026, 4, 1), 'time': '09:10', 'student': 'Branson Pfiester', 'week': 2},
    {'date': (2026, 4, 2), 'time': '08:20', 'student': 'Gus Castillo', 'week': 4},
    {'date': (2026, 4, 2), 'time': '09:35', 'student': 'Emma Cotner', 'week': 4},
    {'date': (2026, 4, 3), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 4},
    {'date': (2026, 4, 3), 'time': '08:35', 'student': 'Kavin Lingham', 'week': 1},
    {'date': (2026, 4, 3), 'time': '09:05', 'student': 'Stella Grams', 'week': 1},

    # Week of Apr 6
    {'date': (2026, 4, 7), 'time': '08:00', 'student': 'Sydney Barba', 'week': 3},
    {'date': (2026, 4, 8), 'time': '08:00', 'student': 'Jacob Kuchinsky', 'week': 1},
    {'date': (2026, 4, 8), 'time': '08:35', 'student': 'Luca Sanchez', 'week': 1},
    {'date': (2026, 4, 8), 'time': '09:05', 'student': 'Boris Dudarev', 'week': 3},
    {'date': (2026, 4, 9), 'time': '08:20', 'student': 'Gus Castillo', 'week': 5},
    {'date': (2026, 4, 9), 'time': '08:35', 'student': 'Aheli Shah', 'week': 2},
    {'date': (2026, 4, 9), 'time': '09:05', 'student': 'Ella Dietz', 'week': 2},
    {'date': (2026, 4, 10), 'time': '08:00', 'student': 'Jackson Price', 'week': 2},
    {'date': (2026, 4, 10), 'time': '08:35', 'student': 'Ali Romman', 'week': 1},
    {'date': (2026, 4, 10), 'time': '09:05', 'student': 'Benny Valles', 'week': 1},

    # Week of Apr 13
    {'date': (2026, 4, 15), 'time': '08:00', 'student': 'Zayen Szpitalak', 'week': 3},
    {'date': (2026, 4, 15), 'time': '08:35', 'student': 'Stella Cole', 'week': 3},
    {'date': (2026, 4, 16), 'time': '08:20', 'student': 'Gus Castillo', 'week': 6},
    {'date': (2026, 4, 16), 'time': '08:35', 'student': 'Branson Pfiester', 'week': 3},
    {'date': (2026, 4, 16), 'time': '09:35', 'student': 'Emma Cotner', 'week': 5},
    {'date': (2026, 4, 17), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 5},
    {'date': (2026, 4, 17), 'time': '08:35', 'student': 'Vera Li', 'week': 1},
    {'date': (2026, 4, 17), 'time': '09:05', 'student': 'Emily Smith', 'week': 1},

    # Week of Apr 20 - SPRING BREAK - No calls

    # Week of Apr 27
    {'date': (2026, 4, 28), 'time': '08:00', 'student': 'Stella Cole', 'week': 4},
    {'date': (2026, 4, 29), 'time': '08:00', 'student': 'Boris Dudarev', 'week': 4},
    {'date': (2026, 4, 29), 'time': '08:35', 'student': 'Sydney Barba', 'week': 4},
    {'date': (2026, 4, 29), 'time': '09:05', 'student': 'Zayen Szpitalak', 'week': 4},
    {'date': (2026, 4, 29), 'time': '09:40', 'student': 'Branson Pfiester', 'week': 4},
    {'date': (2026, 4, 30), 'time': '08:20', 'student': 'Gus Castillo', 'week': 7},
    {'date': (2026, 4, 30), 'time': '09:35', 'student': 'Emma Cotner', 'week': 6},
    {'date': (2026, 5, 1), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 6},
    {'date': (2026, 5, 1), 'time': '08:35', 'student': 'Paty Margain-Junco', 'week': 1},
    {'date': (2026, 5, 1), 'time': '09:05', 'student': 'Michael Cai', 'week': 1},
]

# =============================================================================
# SLACK CLIENT
# =============================================================================

client = None

def init_client():
    global client
    if SLACK_BOT_TOKEN == 'xoxb-YOUR-TOKEN-HERE':
        print("ERROR: Please set your Slack Bot Token!")
        print("Either set SLACK_BOT_TOKEN environment variable or edit this script.")
        sys.exit(1)
    client = WebClient(token=SLACK_BOT_TOKEN)

def get_user_by_email(email):
    """Look up Slack user ID by email."""
    try:
        response = client.users_lookupByEmail(email=email)
        return response['user']['id']
    except SlackApiError as e:
        if e.response['error'] == 'users_not_found':
            return None
        raise

def send_dm(user_id, message, blocks=None):
    """Send a direct message to a user."""
    try:
        response = client.chat_postMessage(
            channel=user_id,
            text=message,
            blocks=blocks
        )
        return True
    except SlackApiError as e:
        print(f"  Error sending message: {e.response['error']}")
        return False

# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================

def get_weekly_reminder_message(student_name, calls_this_week):
    """Generate weekly reminder message."""
    course = STUDENTS[student_name]['course']

    if not calls_this_week:
        return None

    call_list = "\n".join([
        f"  • *{c['date'].strftime('%A %b %d')}* at *{c['time']} CT*"
        for c in calls_this_week
    ])

    message = f"""Hey {student_name.split()[0]}! :wave:

Here's your AP coaching schedule for this week:

{call_list}

*Before each call, please complete:*
• Your assigned FRQ/SAQ practice
• Model drawing exercises (if APHG)
• Review your question file (I'll send it the day before)

See you soon! :books:"""

    return message

def get_question_file_message(student_name, week_num, call_date, call_time):
    """Generate message with question file content."""
    course = STUDENTS[student_name]['course']

    # Build filename
    clean_name = student_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"{clean_name}_week{week_num}.md"
    filepath = QUESTIONS_DIR / filename

    if not filepath.exists():
        return None, None

    # Read question content
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract just the questions (before the rubric/details sections)
    # Split on the details tag to hide rubrics
    questions_only = content.split('<details>')[0].strip()

    # Truncate if too long for Slack (4000 char limit per message)
    if len(questions_only) > 3500:
        questions_only = questions_only[:3500] + "\n\n_(truncated - see full file for complete questions)_"

    intro = f"""Hey {student_name.split()[0]}! :books:

Your coaching call is *tomorrow* ({call_date.strftime('%A %b %d')} at {call_time} CT).

Here are your practice questions to complete *before* we meet:

---

"""

    outro = """

---

:point_right: *Complete these before our call!*
• Write out your answers
• Check the rubric AFTER you're done (it's in your question file)
• Note any questions you have

See you tomorrow! :rocket:"""

    full_message = intro + questions_only + outro

    return full_message, filename

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def get_calls_for_week(start_date):
    """Get all calls within a week of start_date."""
    end_date = start_date + timedelta(days=7)

    calls = []
    for call in SCHEDULE:
        call_date = datetime(*call['date'])
        if start_date <= call_date < end_date:
            calls.append({
                'date': call_date,
                'time': call['time'],
                'student': call['student'],
                'week': call['week']
            })

    return calls

def get_calls_for_student_this_week(student_name, start_date=None):
    """Get a specific student's calls for this week."""
    if start_date is None:
        # Default to this week (Monday)
        today = datetime.now()
        start_date = today - timedelta(days=today.weekday())

    week_calls = get_calls_for_week(start_date)
    return [c for c in week_calls if c['student'] == student_name]

def send_weekly_reminders(test_mode=False):
    """Send weekly schedule reminders to all students with calls this week."""
    print("\n=== Sending Weekly Reminders ===\n")

    # Get this week's calls
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_calls = get_calls_for_week(week_start)

    # Group by student
    student_calls = {}
    for call in week_calls:
        student = call['student']
        if student not in student_calls:
            student_calls[student] = []
        student_calls[student].append(call)

    print(f"Found {len(student_calls)} students with calls this week.\n")

    sent = 0
    failed = 0

    for student_name, calls in student_calls.items():
        if test_mode and student_name != 'Gus Castillo':
            continue

        email = STUDENTS[student_name]['email']
        print(f"  {student_name} ({email})...")

        user_id = get_user_by_email(email)
        if not user_id:
            print(f"    NOT FOUND in Slack")
            failed += 1
            continue

        message = get_weekly_reminder_message(student_name, calls)
        if message and send_dm(user_id, message):
            print(f"    Sent!")
            sent += 1
        else:
            print(f"    Failed to send")
            failed += 1

    print(f"\n=== Summary: {sent} sent, {failed} failed ===\n")

def send_question_files(days_ahead=1, test_mode=False):
    """Send question files to students with calls in X days."""
    print(f"\n=== Sending Question Files (calls in {days_ahead} day(s)) ===\n")

    target_date = datetime.now() + timedelta(days=days_ahead)
    target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Find calls on target date
    calls_on_date = []
    for call in SCHEDULE:
        call_date = datetime(*call['date'])
        if call_date.date() == target_date.date():
            calls_on_date.append(call)

    print(f"Found {len(calls_on_date)} calls on {target_date.strftime('%A %b %d')}.\n")

    sent = 0
    failed = 0

    for call in calls_on_date:
        student_name = call['student']

        if test_mode and student_name != 'Gus Castillo':
            continue

        email = STUDENTS[student_name]['email']
        call_date = datetime(*call['date'])

        print(f"  {student_name} (Week {call['week']})...")

        user_id = get_user_by_email(email)
        if not user_id:
            print(f"    NOT FOUND in Slack")
            failed += 1
            continue

        message, filename = get_question_file_message(
            student_name, call['week'], call_date, call['time']
        )

        if not message:
            print(f"    No question file found: {filename}")
            failed += 1
            continue

        if send_dm(user_id, message):
            print(f"    Sent! ({filename})")
            sent += 1
        else:
            print(f"    Failed to send")
            failed += 1

    print(f"\n=== Summary: {sent} sent, {failed} failed ===\n")

def list_students():
    """List all students and check if they're in Slack."""
    print("\n=== Student Slack Status ===\n")

    found = 0
    not_found = 0

    for name, info in sorted(STUDENTS.items()):
        email = info['email']
        user_id = get_user_by_email(email)

        if user_id:
            print(f"  [OK] {name} - {email}")
            found += 1
        else:
            print(f"  [--] {name} - {email} (NOT IN SLACK)")
            not_found += 1

    print(f"\n=== Summary: {found} found, {not_found} not found ===\n")

# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='AP Coaching Slack Bot')
    parser.add_argument('--weekly', action='store_true', help='Send weekly reminders')
    parser.add_argument('--questions', action='store_true', help='Send question files for tomorrow\'s calls')
    parser.add_argument('--questions-today', action='store_true', help='Send question files for today\'s calls')
    parser.add_argument('--test', action='store_true', help='Test mode (only send to Gus)')
    parser.add_argument('--list', action='store_true', help='List students and Slack status')

    args = parser.parse_args()

    if not any([args.weekly, args.questions, args.questions_today, args.list]):
        parser.print_help()
        return

    init_client()

    if args.list:
        list_students()

    if args.weekly:
        send_weekly_reminders(test_mode=args.test)

    if args.questions:
        send_question_files(days_ahead=1, test_mode=args.test)

    if args.questions_today:
        send_question_files(days_ahead=0, test_mode=args.test)

if __name__ == '__main__':
    main()
