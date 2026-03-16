#!/usr/bin/env python3
"""
Interactive Slack Bot Listener - Responds to student messages

SETUP:
1. In your Slack App settings (api.slack.com/apps):
   - Go to "Socket Mode" and enable it
   - Generate an App-Level Token with "connections:write" scope
   - Go to "Event Subscriptions" and enable events
   - Subscribe to bot events: message.im, app_mention
   - Go to "OAuth & Permissions" and add scopes: im:history, im:read, im:write

2. Set environment variables:
   - SLACK_BOT_TOKEN=xoxb-your-bot-token
   - SLACK_APP_TOKEN=xapp-your-app-token

RUN: python slack_bot_listener.py
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:
    print("Please install slack_bolt: pip install slack_bolt")
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / 'dashboard_config.json'
INTERACTIONS_FILE = BASE_DIR / 'slack_interactions.json'

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

# Load tokens - check config file first, then env vars
config = load_config()
SLACK_BOT_TOKEN = config.get('slack_token') or os.environ.get('SLACK_BOT_TOKEN', '')
SLACK_APP_TOKEN = config.get('slack_app_token') or os.environ.get('SLACK_APP_TOKEN', '')

# Student data (same as other files)
STUDENTS = {
    'Gus Castillo': {'email': 'gus.castillo@alpha.school', 'course': 'AP Human Geography'},
    'Emma Cotner': {'email': 'emma.cotner@alpha.school', 'course': 'AP World History'},
    'Jackson Price': {'email': 'jackson.price@alpha.school', 'course': 'AP World History'},
    'Boris Dudarev': {'email': 'boris.dudarev@alpha.school', 'course': 'AP Human Geography'},
    'Sydney Barba': {'email': 'sydney.barba@alpha.school', 'course': 'AP Human Geography'},
    'Branson Pfiester': {'email': 'branson.pfiester@alpha.school', 'course': 'AP Human Geography'},
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

# Build email -> name lookup
EMAIL_TO_NAME = {info['email']: name for name, info in STUDENTS.items()}

# Schedule (same as other files)
SCHEDULE = [
    {'date': (2026, 3, 10), 'time': '08:20', 'student': 'Gus Castillo', 'week': 1},
    {'date': (2026, 3, 13), 'time': '10:30', 'student': 'Emma Cotner', 'week': 1},
    {'date': (2026, 3, 11), 'time': '09:45', 'student': 'Jackson Price', 'week': 1},
    {'date': (2026, 3, 11), 'time': '08:35', 'student': 'Boris Dudarev', 'week': 1},
    {'date': (2026, 3, 11), 'time': '09:05', 'student': 'Sydney Barba', 'week': 1},
    {'date': (2026, 3, 12), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 1},
    {'date': (2026, 3, 12), 'time': '09:05', 'student': 'Aheli Shah', 'week': 1},
    {'date': (2026, 3, 13), 'time': '10:00', 'student': 'Ella Dietz', 'week': 1},
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
    {'date': (2026, 3, 25), 'time': '08:00', 'student': 'Boris Dudarev', 'week': 2},
    {'date': (2026, 3, 25), 'time': '08:35', 'student': 'Sydney Barba', 'week': 2},
    {'date': (2026, 3, 26), 'time': '08:20', 'student': 'Gus Castillo', 'week': 3},
    {'date': (2026, 3, 26), 'time': '09:35', 'student': 'Emma Cotner', 'week': 3},
    {'date': (2026, 3, 27), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 3},
    {'date': (2026, 3, 27), 'time': '08:35', 'student': 'Jessica Owenby', 'week': 1},
    {'date': (2026, 3, 27), 'time': '09:05', 'student': 'Cruce Saunders IV', 'week': 1},
    {'date': (2026, 4, 1), 'time': '08:00', 'student': 'Zayen Szpitalak', 'week': 2},
    {'date': (2026, 4, 1), 'time': '08:35', 'student': 'Stella Cole', 'week': 2},
    {'date': (2026, 4, 1), 'time': '09:10', 'student': 'Branson Pfiester', 'week': 2},
    {'date': (2026, 4, 2), 'time': '08:20', 'student': 'Gus Castillo', 'week': 4},
    {'date': (2026, 4, 2), 'time': '09:35', 'student': 'Emma Cotner', 'week': 4},
    {'date': (2026, 4, 3), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 4},
    {'date': (2026, 4, 3), 'time': '08:35', 'student': 'Kavin Lingham', 'week': 1},
    {'date': (2026, 4, 3), 'time': '09:05', 'student': 'Stella Grams', 'week': 1},
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
    {'date': (2026, 4, 15), 'time': '08:00', 'student': 'Zayen Szpitalak', 'week': 3},
    {'date': (2026, 4, 15), 'time': '08:35', 'student': 'Stella Cole', 'week': 3},
    {'date': (2026, 4, 16), 'time': '08:20', 'student': 'Gus Castillo', 'week': 6},
    {'date': (2026, 4, 16), 'time': '08:35', 'student': 'Branson Pfiester', 'week': 3},
    {'date': (2026, 4, 16), 'time': '09:35', 'student': 'Emma Cotner', 'week': 5},
    {'date': (2026, 4, 17), 'time': '08:00', 'student': 'Saeed Tarawneh', 'week': 5},
    {'date': (2026, 4, 17), 'time': '08:35', 'student': 'Vera Li', 'week': 1},
    {'date': (2026, 4, 17), 'time': '09:05', 'student': 'Emily Smith', 'week': 1},
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
# INTERACTION LOGGING
# =============================================================================

def load_interactions():
    if INTERACTIONS_FILE.exists():
        with open(INTERACTIONS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_interaction(user_email, user_name, message, response, is_student):
    interactions = load_interactions()
    interactions.append({
        'timestamp': datetime.now().isoformat(),
        'user_email': user_email,
        'user_name': user_name,
        'message': message,
        'response': response,
        'is_student': is_student
    })
    # Keep last 500 interactions
    interactions = interactions[-500:]
    with open(INTERACTIONS_FILE, 'w') as f:
        json.dump(interactions, f, indent=2)

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def get_student_schedule(student_name):
    """Get all upcoming calls for a student."""
    today = datetime.now().date()
    calls = []
    for c in SCHEDULE:
        call_date = datetime(*c['date']).date()
        if c['student'] == student_name and call_date >= today:
            calls.append({
                'date': call_date,
                'time': c['time'],
                'week': c['week']
            })
    return sorted(calls, key=lambda x: x['date'])

def get_next_call(student_name):
    """Get the next upcoming call for a student."""
    calls = get_student_schedule(student_name)
    return calls[0] if calls else None

def handle_help():
    return """Here are the commands I understand:

*schedule* - See all your upcoming coaching calls
*next* - See your next coaching call
*help* - Show this help message

You can also just chat with me and I'll pass your message along to your coach!"""

def handle_schedule(student_name):
    calls = get_student_schedule(student_name)
    if not calls:
        return "You don't have any upcoming calls scheduled."

    lines = ["Here are your upcoming coaching calls:\n"]
    for c in calls[:5]:  # Show next 5
        lines.append(f"  *{c['date'].strftime('%A %b %d')}* at *{c['time']} CT* (Week {c['week']})")

    if len(calls) > 5:
        lines.append(f"\n...and {len(calls) - 5} more")

    return "\n".join(lines)

def handle_next(student_name):
    call = get_next_call(student_name)
    if not call:
        return "You don't have any upcoming calls scheduled."

    days_until = (call['date'] - datetime.now().date()).days
    if days_until == 0:
        when = "today"
    elif days_until == 1:
        when = "tomorrow"
    else:
        when = f"in {days_until} days"

    return f"Your next coaching call is *{when}*:\n\n  *{call['date'].strftime('%A %b %d')}* at *{call['time']} CT* (Week {call['week']})\n\nSee you then!"

def handle_unknown_student():
    return "Hi! I'm the AP Coaching Bot. It looks like you're not currently enrolled in the coaching program. If you think this is an error, please contact your learning coach."

def handle_general_message(student_name, message):
    """For non-command messages, acknowledge and log for coach review."""
    return f"Thanks for your message! I've noted it down and your coach will see it. If you need something urgently, try emailing them directly.\n\nType *help* to see what I can do."

# =============================================================================
# SLACK APP
# =============================================================================

app = App(token=SLACK_BOT_TOKEN)

@app.event("message")
def handle_message(event, say, client):
    # Ignore bot messages
    if event.get('bot_id') or event.get('subtype'):
        return

    user_id = event.get('user')
    text = event.get('text', '').strip().lower()
    original_text = event.get('text', '').strip()

    # Look up user email
    try:
        user_info = client.users_info(user=user_id)
        user_email = user_info['user']['profile'].get('email', '')
        user_display = user_info['user']['profile'].get('real_name', 'Unknown')
    except Exception as e:
        print(f"Error looking up user: {e}")
        user_email = ''
        user_display = 'Unknown'

    # Check if this is a known student
    student_name = EMAIL_TO_NAME.get(user_email)
    is_student = student_name is not None

    # Handle commands
    if text == 'help':
        response = handle_help()
    elif text == 'schedule':
        if is_student:
            response = handle_schedule(student_name)
        else:
            response = handle_unknown_student()
    elif text == 'next':
        if is_student:
            response = handle_next(student_name)
        else:
            response = handle_unknown_student()
    else:
        # General message
        if is_student:
            response = handle_general_message(student_name, original_text)
        else:
            response = handle_unknown_student()

    # Log the interaction
    save_interaction(
        user_email=user_email,
        user_name=student_name or user_display,
        message=original_text,
        response=response,
        is_student=is_student
    )

    # Send response
    say(response)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {student_name or user_display}: {original_text[:50]}...")

# =============================================================================
# MAIN
# =============================================================================

def main():
    if not SLACK_BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set")
        print("Set it with: set SLACK_BOT_TOKEN=xoxb-your-token")
        sys.exit(1)

    if not SLACK_APP_TOKEN:
        print("ERROR: SLACK_APP_TOKEN not set")
        print("Set it with: set SLACK_APP_TOKEN=xapp-your-token")
        print("\nTo get an app token:")
        print("1. Go to api.slack.com/apps > Your App > Basic Information")
        print("2. Scroll to 'App-Level Tokens' and generate one with 'connections:write' scope")
        sys.exit(1)

    print("=" * 50)
    print("AP Coaching Bot - Interactive Listener")
    print("=" * 50)
    print(f"Interactions logged to: {INTERACTIONS_FILE}")
    print(f"Known students: {len(STUDENTS)}")
    print("\nCommands: help, schedule, next")
    print("\nListening for messages... (Ctrl+C to stop)\n")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == '__main__':
    main()
