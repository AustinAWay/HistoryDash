# Coaching Coach

A coaching management system for AP exam preparation. Generates personalized learning plans, tracks interventions, manages coaching sessions, and communicates with students via Slack.

## Features

- **Dashboard** (`coaching_dashboard.py`): Main Streamlit dashboard for managing coaching sessions
- **Plan Generation** (`generate_plans.py`, `generate_master_reports.py`): Create personalized learning plans based on student assessment data
- **Intervention Tracking** (`generate_intervention_tracker.py`): Track student progress and trigger interventions
- **Question Generation** (`generate_questions.py`): Generate practice questions for students
- **Slack Integration** (`slack_coaching_bot.py`, `slack_bot_listener.py`): Send coaching messages and reminders via Slack
- **Google Calendar Integration** (`create_coaching_calendar.gs`): Google Apps Script for calendar management
- **PDF Export** (`convert_to_pdf.py`, `convert_main_docs.py`): Convert plans to PDF format

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy and configure credentials:
   ```bash
   cp dashboard_config.template.json dashboard_config.json
   # Edit dashboard_config.json with your API keys
   ```

3. Create your school calendar:
   ```bash
   cp calendar_date.template.csv calendar_date.csv
   # Edit with your school's calendar dates
   ```

4. Add your student data:
   - Create `student_plans/` directory for individual student plans
   - Import student assessment data (Excel files)

## Usage

Run the dashboard:
```bash
streamlit run coaching_dashboard.py
```

## Directory Structure

```
coaching_coach/
├── coaching_dashboard.py      # Main dashboard
├── generate_*.py              # Plan/report generators
├── slack_*.py                 # Slack bot integration
├── convert_*.py               # PDF conversion utilities
├── create_coaching_calendar.gs # Google Apps Script
├── requirements.txt           # Python dependencies
├── dashboard_config.json      # Your credentials (gitignored)
├── calendar_date.csv          # Your school calendar (gitignored)
├── student_plans/             # Student-specific plans (gitignored)
└── reports/                   # Generated reports (gitignored)
```

## Customization

This framework is designed to be adapted for any subject or school. Key files to customize:

1. **Calendar**: Update `calendar_date.csv` with your school's schedule
2. **Student Data**: Import your assessment data in Excel format
3. **Plan Templates**: Modify generators to match your curriculum
4. **Slack Messages**: Customize message templates in slack bot files
