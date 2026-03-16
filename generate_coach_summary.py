#!/usr/bin/env python3
"""Generate a coaching call summary with pre-call and post-call tasks."""

import re
from pathlib import Path
from datetime import datetime

def parse_student_plan(filepath):
    """Extract key info from a student plan markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract name and course
    title_match = re.search(r'^# (.+?) \| (.+)$', content, re.MULTILINE)
    if not title_match:
        return None

    name = title_match.group(1)
    course = title_match.group(2)

    # Extract tier
    tier_match = re.search(r'\*\*Tier: (.+?)\*\*', content)
    tier = tier_match.group(1) if tier_match else 'Unknown'

    # Extract focus units
    focus_match = re.search(r'\*\*Your focus units:\*\* (.+)', content)
    focus_units = focus_match.group(1) if focus_match else 'None specified'

    # Extract coaching calls
    calls = []
    call_pattern = re.findall(r'\| (\d+) \| (.+?) \| (\d{2}:\d{2}) \|', content)
    for call_num, date, time in call_pattern:
        calls.append({
            'num': int(call_num),
            'date': date.strip(),
            'time': time.strip()
        })

    # Extract plan type based on tier
    plan_section = ''
    plan_match = re.search(r'## Your Plan\n\n(.+?)(?=\n---|\n## )', content, re.DOTALL)
    if plan_match:
        plan_section = plan_match.group(1).strip()

    return {
        'name': name,
        'course': course,
        'tier': tier,
        'focus_units': focus_units,
        'calls': calls,
        'plan_section': plan_section
    }


def get_focus_unit_list(focus_str):
    """Parse focus units string into a list."""
    if not focus_str or focus_str == 'None specified':
        return []
    # Handle formats like "4, 5, 7, 8" or "8"
    units = [u.strip() for u in focus_str.replace('and', ',').split(',')]
    return [u for u in units if u]


def get_question_file(student_name, week):
    """Get the question file reference for a student/week."""
    clean_name = student_name.lower().replace(" ", "_").replace("-", "_")
    return f"{clean_name}_week{week}.md"


def get_pre_call_task(student, call_num):
    """Determine what student should have done before this call."""
    tier = student['tier']
    course = student['course']
    focus = student['focus_units']
    focus_list = get_focus_unit_list(focus)
    name = student['name']

    num_focus = len(focus_list)
    qfile = get_question_file(name, call_num)

    if tier == 'Critical':
        if call_num == 1:
            unit = focus_list[0] if focus_list else '?'
            return f"📁 {qfile}: Unit {unit} Edmentum started + Model drawing"
        elif call_num <= num_focus:
            completed = focus_list[:call_num-1] if focus_list else []
            return f"📁 {qfile}: Unit(s) {', '.join(completed)} FRQ + Model done"
        else:
            return f"📁 {qfile}: All units done; review FRQs"

    elif tier == 'Intensive':
        if call_num == 1:
            return f"📁 {qfile}: Week 1 FRQ + daily practice"
        else:
            return f"📁 {qfile}: FRQ + Model from file"

    elif tier == 'Moderate':
        if call_num == 1:
            return f"📁 {qfile}: Weeks 1-2 work + FRQ"
        else:
            return f"📁 {qfile}: 2wks FRQ + URP work"

    elif tier == 'Light':
        if call_num == 1:
            return f"📁 {qfile} : Check-in; focus Unit(s) {focus}"
        else:
            return f"📁 {qfile}: FRQ practice for Unit(s) {focus}"

    elif tier == 'Maintenance':
        return f"📁 {qfile}: Weekly MCQs + FRQ review"

    return f"📁 {qfile}"


def get_post_call_task(student, call_num, total_calls):
    """Determine what student should do after this call until next call/exam."""
    tier = student['tier']
    course = student['course']
    focus = student['focus_units']
    focus_list = get_focus_unit_list(focus)
    name = student['name']

    # Check if this is the last call
    is_last = (call_num == total_calls)
    next_qfile = get_question_file(name, call_num + 1) if not is_last else "N/A"

    if is_last:
        if 'Geography' in course:
            return "⭐ FINAL: All models + mixed MCQs + timed FRQs -> May 5"
        elif 'World' in course:
            return "⭐ FINAL: SAQ blitz + causal chains -> May 7"
        elif 'US History' in course:
            return "⭐ FINAL: SAQs + DBQ planning -> May 8"
        elif 'Government' in course:
            return "⭐ FINAL: SCOTUS + foundational docs -> May 11"
        return "Final exam preparation"

    num_focus = len(focus_list)

    if tier == 'Critical':
        if call_num == 1:
            if len(focus_list) > 1:
                return f"📁 {next_qfile}: Complete U{focus_list[0]}, start U{focus_list[1]}"
            else:
                return f"📁 {next_qfile}: Complete Unit {focus_list[0]}"
        next_idx = call_num - 1
        if focus_list and next_idx < len(focus_list):
            next_unit = focus_list[next_idx]
            return f"📁 {next_qfile}: Unit {next_unit} FRQ + Model"
        else:
            return f"📁 {next_qfile}: Review all; mixed practice"

    elif tier == 'Intensive':
        return f"📁 {next_qfile}: Next unit FRQ + daily practice"

    elif tier == 'Moderate':
        return f"📁 {next_qfile}: 2wks: 1-2 units + FRQs"

    elif tier == 'Light':
        return f"📁 {next_qfile}: Continue FRQ practice"

    elif tier == 'Maintenance':
        return "Continue weekly maintenance until exam"

    return "Continue with plan"


def main():
    plans_dir = Path('student_plans_v3')

    # Collect all student data
    students = {}
    for md_file in plans_dir.glob('*.md'):
        if md_file.name in ['MASTER_COACHING_SCHEDULE.md', 'TEMPLATE_Sydney_Barba.md']:
            continue

        data = parse_student_plan(md_file)
        if data and data['calls']:
            students[data['name']] = data

    # Build chronological list of all calls
    all_calls = []
    for name, student in students.items():
        for call in student['calls']:
            # Parse date for sorting
            date_str = call['date']
            # Handle dates like "Thu Mar 12"
            try:
                # Add year 2026 for parsing
                dt = datetime.strptime(f"{date_str} 2026", "%a %b %d %Y")
            except:
                try:
                    dt = datetime.strptime(f"{date_str} 2026", "%a %B %d %Y")
                except:
                    dt = datetime.now()

            all_calls.append({
                'datetime': dt,
                'date': call['date'],
                'time': call['time'],
                'student': name,
                'course': student['course'],
                'tier': student['tier'],
                'focus': student['focus_units'],
                'call_num': call['num'],
                'total_calls': len(student['calls']),
                'pre_task': get_pre_call_task(student, call['num']),
                'post_task': get_post_call_task(student, call['num'], len(student['calls']))
            })

    # Sort by date/time
    all_calls.sort(key=lambda x: (x['datetime'], x['time']))

    # Generate markdown output
    output = []
    output.append("# Coach Call Summary - March/April 2026")
    output.append("")
    output.append("**63 calls total** | **27 students** | **Call window: 0800-0930**")
    output.append("")
    output.append("---")
    output.append("")

    current_week = None

    for call in all_calls:
        # Week header
        week_start = call['datetime'].strftime("%b %d")
        week_of = f"Week of {call['datetime'].strftime('%b %d')}"

        # Determine week grouping (Mon-Sun)
        week_num = call['datetime'].isocalendar()[1]
        if week_num != current_week:
            current_week = week_num
            output.append(f"## Week of {call['datetime'].strftime('%b %d')}")
            output.append("")
            output.append("| Date | Time | Student | Course | Pre-Call Task | Post-Call Task |")
            output.append("|------|------|---------|--------|---------------|----------------|")

        output.append(f"| {call['date']} | {call['time']} | {call['student']} | {call['course']} | {call['pre_task']} | {call['post_task']} |")

    output.append("")
    output.append("---")
    output.append("")
    output.append("## Exam Dates")
    output.append("- **May 5:** AP Human Geography")
    output.append("- **May 7:** AP World History")
    output.append("- **May 8:** AP US History")
    output.append("- **May 11:** AP US Government")

    # Write output
    output_path = plans_dir / 'COACH_CALL_SUMMARY.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f"Generated {output_path}")
    print(f"Total calls: {len(all_calls)}")

    # Also print to console for verification
    print("\n" + "="*80)
    print('\n'.join(output))


if __name__ == '__main__':
    main()
