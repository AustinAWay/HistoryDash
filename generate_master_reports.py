#!/usr/bin/env python3
"""Generate beautiful PDF reports from master coaching plans with charts and infographics."""

import io
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart

# Paths
PROJECT_DIR = Path(r"C:\Users\Adam Work\PycharmProjects\coaching_coach")
OUTPUT_DIR = PROJECT_DIR / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

# Color scheme
COLORS = {
    'primary': colors.HexColor('#2563eb'),
    'primary_dark': colors.HexColor('#1d4ed8'),
    'success': colors.HexColor('#16a34a'),
    'warning': colors.HexColor('#ea580c'),
    'danger': colors.HexColor('#dc2626'),
    'info': colors.HexColor('#0891b2'),
    'gray': colors.HexColor('#6b7280'),
    'light_gray': colors.HexColor('#f3f4f6'),
    'dark': colors.HexColor('#1f2937'),
    'white': colors.HexColor('#ffffff'),
    'yellow': colors.HexColor('#eab308'),
}

# Matplotlib colors (hex strings)
MPL_COLORS = {
    'primary': '#2563eb',
    'success': '#16a34a',
    'warning': '#ea580c',
    'danger': '#dc2626',
    'info': '#0891b2',
    'gray': '#6b7280',
    'yellow': '#eab308',
}

# Student data
STUDENTS = [
    # Tier 1: At Risk
    {'name': 'Gus Castillo', 'subject': 'AP Human Geography', 'predicted': 1, 'target': 3, 'mcq': 48, 'frq': 29, 'completion': 58, 'tier': 1, 'hours': 3.0},
    {'name': 'Branson Pfiester', 'subject': 'AP Human Geography', 'predicted': 2, 'target': 4, 'mcq': 63, 'frq': 24, 'completion': 98, 'tier': 1, 'hours': 3.0, 'accommodation': 'Double Time'},
    {'name': 'Emma Cotner', 'subject': 'AP World History', 'predicted': 2, 'target': 3, 'mcq': 53, 'frq': 43, 'completion': 91, 'tier': 1, 'hours': 2.5},
    {'name': 'Saeed Tarawneh', 'subject': 'AP World History', 'predicted': 2, 'target': 3, 'mcq': 58, 'frq': 39, 'completion': 40, 'tier': 1, 'hours': 2.5},
    # Tier 2: Borderline
    {'name': 'Sydney Barba', 'subject': 'AP Human Geography', 'predicted': 3, 'target': 4, 'mcq': 65, 'frq': 17, 'completion': 49, 'tier': 2, 'hours': 2.0},
    {'name': 'Boris Dudarev', 'subject': 'AP Human Geography', 'predicted': 3, 'target': 4, 'mcq': 56, 'frq': 43, 'completion': 40, 'tier': 2, 'hours': 1.5, 'accommodation': 'Time +50%'},
    {'name': 'Zayen Szpitalak', 'subject': 'AP Human Geography', 'predicted': 3, 'target': 5, 'mcq': 68, 'frq': 43, 'completion': 57, 'tier': 2, 'hours': 1.5},
    {'name': 'Aheli Shah', 'subject': 'AP Human Geography', 'predicted': 3, 'target': 4, 'mcq': 58, 'frq': 48, 'completion': 100, 'tier': 2, 'hours': 1.0},
    {'name': 'Stella Cole', 'subject': 'AP World History', 'predicted': 3, 'target': 4, 'mcq': 62, 'frq': 60, 'completion': 30, 'tier': 2, 'hours': 1.5},
    {'name': 'Ella Dietz', 'subject': 'AP World History', 'predicted': 3, 'target': 5, 'mcq': 62, 'frq': 63, 'completion': 100, 'tier': 2, 'hours': 1.5},
    {'name': 'Jackson Price', 'subject': 'AP World History', 'predicted': 3, 'target': 4, 'mcq': 78, 'frq': 56, 'completion': 74, 'tier': 2, 'hours': 1.5},
    # Tier 3: Score 4
    {'name': 'Adrienne Laswell', 'subject': 'AP Human Geography', 'predicted': 4, 'target': 5, 'mcq': 77, 'frq': 62, 'completion': 85, 'tier': 3, 'hours': 0},
    {'name': 'Austin Lin', 'subject': 'AP Human Geography', 'predicted': 4, 'target': 5, 'mcq': 75, 'frq': 67, 'completion': 86, 'tier': 3, 'hours': 0},
    {'name': 'Cruce Saunders IV', 'subject': 'AP US History', 'predicted': 4, 'target': 5, 'mcq': 84, 'frq': 65, 'completion': 90, 'tier': 3, 'hours': 0, 'accommodation': 'Time +50%'},
    {'name': 'Erika Rigby', 'subject': 'AP Human Geography', 'predicted': 4, 'target': 4, 'mcq': 70, 'frq': 65, 'completion': 75, 'tier': 3, 'hours': 0},
    {'name': 'Grady Swanson', 'subject': 'AP Human Geography', 'predicted': 4, 'target': 5, 'mcq': 70, 'frq': 69, 'completion': 77, 'tier': 3, 'hours': 0},
    {'name': 'Jessica Owenby', 'subject': 'AP Human Geography', 'predicted': 4, 'target': 4, 'mcq': 68, 'frq': 66, 'completion': 73, 'tier': 3, 'hours': 0},
    {'name': 'Kavin Lingham', 'subject': 'AP World History', 'predicted': 4, 'target': 4, 'mcq': 70, 'frq': 65, 'completion': 90, 'tier': 3, 'hours': 0},
    {'name': 'Stella Grams', 'subject': 'AP World History', 'predicted': 4, 'target': 5, 'mcq': 65, 'frq': 71, 'completion': 96, 'tier': 3, 'hours': 0},
    # Tier 4: Score 5
    {'name': 'Evan Klein', 'subject': 'AP Computer Science A', 'predicted': 5, 'target': 5, 'mcq': 93, 'frq': 90, 'completion': 100, 'tier': 4, 'hours': 0},
    {'name': 'Ali Romman', 'subject': 'AP Human Geography', 'predicted': 5, 'target': 5, 'mcq': 68, 'frq': 86, 'completion': 85, 'tier': 4, 'hours': 0},
    {'name': 'Benny Valles', 'subject': 'AP Human Geography', 'predicted': 5, 'target': 5, 'mcq': 72, 'frq': 100, 'completion': 58, 'tier': 4, 'hours': 0},
    {'name': 'Emily Smith', 'subject': 'AP US Government', 'predicted': 5, 'target': 5, 'mcq': 87, 'frq': 100, 'completion': 98, 'tier': 4, 'hours': 0},
    {'name': 'Jacob Kuchinsky', 'subject': 'AP Human Geography', 'predicted': 5, 'target': 5, 'mcq': 75, 'frq': 78, 'completion': 100, 'tier': 4, 'hours': 0},
    {'name': 'Luca Sanchez', 'subject': 'AP Human Geography', 'predicted': 5, 'target': 5, 'mcq': 57, 'frq': 82, 'completion': 40, 'tier': 4, 'hours': 0},
    {'name': 'Michael Cai', 'subject': 'AP World History', 'predicted': 5, 'target': 5, 'mcq': 80, 'frq': 88, 'completion': 48, 'tier': 4, 'hours': 0},
    {'name': 'Paty Margain-Junco', 'subject': 'AP US History', 'predicted': 5, 'target': 5, 'mcq': 78, 'frq': 82, 'completion': 75, 'tier': 4, 'hours': 0},
    {'name': 'Vera Li', 'subject': 'AP Human Geography', 'predicted': 5, 'target': 5, 'mcq': 71, 'frq': 71, 'completion': 24, 'tier': 4, 'hours': 0},
]

WEEKLY_SESSIONS = [
    {'week': 1, 'dates': 'Mar 9-13', 'sessions': 10, 'focus': 'Diagnostic + Content Start'},
    {'week': 2, 'dates': 'Mar 16-20', 'sessions': 6, 'focus': 'Content Acceleration'},
    {'week': 3, 'dates': 'Mar 23-27', 'sessions': 2, 'focus': 'Skills Building'},
    {'week': 4, 'dates': 'Mar 30 - Apr 3', 'sessions': 8, 'focus': 'Integration'},
    {'week': 5, 'dates': 'Apr 6-10', 'sessions': 2, 'focus': 'Pre-Test Prep'},
    {'week': 6, 'dates': 'Apr 13-17', 'sessions': 3, 'focus': 'Practice Test'},
    {'week': 7, 'dates': 'Apr 27 - May 1', 'sessions': 9, 'focus': 'Final Push'},
    {'week': 8, 'dates': 'May 4-6', 'sessions': 3, 'focus': 'Final Prep'},
]


def create_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'Title1',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=COLORS['primary'],
        spaceBefore=20,
        spaceAfter=10,
        borderColor=COLORS['primary'],
        borderWidth=2,
        borderPadding=5,
    ))

    styles.add(ParagraphStyle(
        'SubHeader',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=COLORS['dark'],
        spaceBefore=15,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLORS['dark'],
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLORS['gray'],
    ))

    styles.add(ParagraphStyle(
        'CenterText',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
    ))

    return styles


def create_score_distribution_chart():
    """Create bar chart showing student score distribution."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    scores = [s['predicted'] for s in STUDENTS]
    score_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for s in scores:
        score_counts[s] += 1

    colors_map = {1: MPL_COLORS['danger'], 2: MPL_COLORS['warning'], 3: MPL_COLORS['yellow'],
                  4: MPL_COLORS['info'], 5: MPL_COLORS['success']}
    bars = ax.bar(score_counts.keys(), score_counts.values(),
                  color=[colors_map[k] for k in score_counts.keys()],
                  edgecolor='white', linewidth=2)

    ax.set_xlabel('Predicted AP Score', fontsize=11, fontweight='bold')
    ax.set_ylabel('Number of Students', fontsize=11, fontweight='bold')
    ax.set_title('Student Score Distribution', fontsize=13, fontweight='bold', pad=12)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_ylim(0, max(score_counts.values()) + 2)

    for bar, count in zip(bars, score_counts.values()):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, str(count),
                   ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('white')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_tier_pie_chart():
    """Create pie chart showing tier distribution."""
    fig, ax = plt.subplots(figsize=(5, 5))

    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for s in STUDENTS:
        tier_counts[s['tier']] += 1

    labels = ['At Risk\n(Score 1-2)', 'Borderline\n(Score 3)', 'On Track\n(Score 4)', 'Excellent\n(Score 5)']
    sizes = [tier_counts[1], tier_counts[2], tier_counts[3], tier_counts[4]]
    chart_colors = [MPL_COLORS['danger'], MPL_COLORS['warning'], MPL_COLORS['info'], MPL_COLORS['success']]
    explode = (0.05, 0.02, 0, 0)

    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=chart_colors,
                                       autopct='%1.0f%%', shadow=False, startangle=90,
                                       textprops={'fontsize': 9})
    for autotext in autotexts:
        autotext.set_fontweight('bold')
        autotext.set_color('white')
        autotext.set_fontsize(10)

    ax.set_title('Student Tier Distribution', fontsize=13, fontweight='bold', pad=12)
    fig.patch.set_facecolor('white')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_mcq_frq_scatter():
    """Create scatter plot of MCQ vs FRQ performance."""
    fig, ax = plt.subplots(figsize=(7, 5))

    tier_colors = {1: MPL_COLORS['danger'], 2: MPL_COLORS['warning'],
                   3: MPL_COLORS['info'], 4: MPL_COLORS['success']}

    for s in STUDENTS:
        ax.scatter(s['mcq'], s['frq'], c=tier_colors[s['tier']], s=80, alpha=0.7,
                  edgecolors='white', linewidth=1.5)

    # Threshold lines
    ax.axhline(y=60, color=MPL_COLORS['gray'], linestyle='--', alpha=0.4)
    ax.axvline(x=60, color=MPL_COLORS['gray'], linestyle='--', alpha=0.4)

    # Quadrant labels
    ax.text(47, 90, 'FRQ Strong\nMCQ Weak', fontsize=8, color=MPL_COLORS['gray'], ha='center')
    ax.text(87, 90, 'Both Strong', fontsize=9, color=MPL_COLORS['success'], ha='center', fontweight='bold')
    ax.text(47, 22, 'Both Weak', fontsize=9, color=MPL_COLORS['danger'], ha='center', fontweight='bold')
    ax.text(87, 22, 'MCQ Strong\nFRQ Weak', fontsize=8, color=MPL_COLORS['gray'], ha='center')

    ax.set_xlabel('MCQ Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_ylabel('FRQ Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_title('MCQ vs FRQ Performance Analysis', fontsize=13, fontweight='bold', pad=12)
    ax.set_xlim(40, 100)
    ax.set_ylim(10, 105)

    legend_elements = [mpatches.Patch(facecolor=MPL_COLORS['danger'], label='Tier 1: At Risk'),
                       mpatches.Patch(facecolor=MPL_COLORS['warning'], label='Tier 2: Borderline'),
                       mpatches.Patch(facecolor=MPL_COLORS['info'], label='Tier 3: Score 4'),
                       mpatches.Patch(facecolor=MPL_COLORS['success'], label='Tier 4: Score 5')]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=8)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('white')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_coaching_hours_chart():
    """Create horizontal bar chart of coaching hours."""
    fig, ax = plt.subplots(figsize=(6, 4))

    students_needing = [s for s in STUDENTS if s['hours'] > 0]
    students_needing.sort(key=lambda x: x['hours'], reverse=True)

    names = [s['name'].split()[0] for s in students_needing]
    hours = [s['hours'] for s in students_needing]
    bar_colors = [MPL_COLORS['danger'] if s['tier'] == 1 else MPL_COLORS['warning'] for s in students_needing]

    bars = ax.barh(names, hours, color=bar_colors, edgecolor='white', linewidth=1.5)
    ax.set_xlabel('Coaching Hours', fontsize=11, fontweight='bold')
    ax.set_title('Coaching Time Allocation', fontsize=13, fontweight='bold', pad=12)
    ax.invert_yaxis()

    for bar, hour in zip(bars, hours):
        ax.text(bar.get_width() + 0.08, bar.get_y() + bar.get_height()/2,
               f'{hour}h', va='center', fontsize=9, fontweight='bold')

    ax.set_xlim(0, max(hours) + 0.6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('white')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_weekly_load_chart():
    """Create timeline chart of weekly sessions."""
    fig, ax = plt.subplots(figsize=(8, 3.5))

    weeks = [w['week'] for w in WEEKLY_SESSIONS]
    sessions = [w['sessions'] for w in WEEKLY_SESSIONS]

    bar_colors = [MPL_COLORS['primary'] if s <= 3 else MPL_COLORS['warning'] if s <= 6
                 else MPL_COLORS['danger'] for s in sessions]

    bars = ax.bar(weeks, sessions, color=bar_colors, edgecolor='white', linewidth=2)
    ax.set_xticks(weeks)
    ax.set_xticklabels([f"Wk {w}" for w in weeks])
    ax.set_ylabel('Sessions', fontsize=11, fontweight='bold')
    ax.set_title('Weekly Coaching Load', fontsize=13, fontweight='bold', pad=12)

    for bar, sess in zip(bars, sessions):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, str(sess),
               ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Spring break annotation
    ax.annotate('', xy=(6.5, 0.5), xytext=(6.5, 2),
               arrowprops=dict(arrowstyle='->', color=MPL_COLORS['success'], lw=2))
    ax.text(6.5, 2.5, 'Spring\nBreak', fontsize=8, color=MPL_COLORS['success'],
           ha='center', fontweight='bold')

    ax.set_ylim(0, max(sessions) + 2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('white')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_subject_distribution_chart():
    """Create pie chart of subject distribution."""
    fig, ax = plt.subplots(figsize=(5, 5))

    subjects = {}
    for s in STUDENTS:
        subj = s['subject'].replace('AP ', '')
        subjects[subj] = subjects.get(subj, 0) + 1

    chart_colors = [MPL_COLORS['primary'], MPL_COLORS['info'], MPL_COLORS['success'],
                   MPL_COLORS['warning'], '#8b5cf6']

    wedges, texts, autotexts = ax.pie(subjects.values(), labels=subjects.keys(),
                                       colors=chart_colors[:len(subjects)],
                                       autopct='%1.0f%%', shadow=False, startangle=90,
                                       textprops={'fontsize': 8})
    for autotext in autotexts:
        autotext.set_fontweight('bold')
        autotext.set_color('white')
        autotext.set_fontsize(9)

    ax.set_title('Students by Subject', fontsize=13, fontweight='bold', pad=12)
    fig.patch.set_facecolor('white')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_header_table(styles):
    """Create the header section."""
    data = [
        [Paragraph('<font color="white" size="24"><b>AP Coaching Master Plan</b></font>', styles['CenterText'])],
        [Paragraph('<font color="white" size="12">Social Science & Computer Science | Spring 2026</font>', styles['CenterText'])],
        [Paragraph(f'<font color="white" size="9">Generated {datetime.now().strftime("%B %d, %Y")}</font>', styles['CenterText'])],
    ]

    table = Table(data, colWidths=[180*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLORS['primary']),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 25),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 20),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    return table


def create_summary_cards(styles):
    """Create the executive summary cards."""
    tier1 = len([s for s in STUDENTS if s['tier'] == 1])
    tier2 = len([s for s in STUDENTS if s['tier'] == 2])
    total_hours = sum(s['hours'] for s in STUDENTS)

    card_data = [
        [
            Paragraph(f'<font size="24" color="#dc2626"><b>{tier1}</b></font><br/><font size="8" color="#6b7280">AT-RISK STUDENTS</font>', styles['CenterText']),
            Paragraph(f'<font size="24" color="#ea580c"><b>{tier2}</b></font><br/><font size="8" color="#6b7280">BORDERLINE STUDENTS</font>', styles['CenterText']),
            Paragraph(f'<font size="24" color="#2563eb"><b>{total_hours:.1f}</b></font><br/><font size="8" color="#6b7280">COACHING HOURS</font>', styles['CenterText']),
            Paragraph(f'<font size="24" color="#16a34a"><b>{len(STUDENTS)}</b></font><br/><font size="8" color="#6b7280">TOTAL STUDENTS</font>', styles['CenterText']),
        ]
    ]

    table = Table(card_data, colWidths=[44*mm, 44*mm, 44*mm, 44*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#fef2f2')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fffbeb')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#eff6ff')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#f0fdf4')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
    ]))
    return table


def create_key_dates_table(styles):
    """Create key dates section."""
    dates_data = [
        ['Key Dates', ''],
        ['Mar 9 - Apr 17', 'Session 4 (Intensive Coaching)'],
        ['Apr 13-17', 'Practice Test Week'],
        ['Apr 20-24', 'Spring Break (No School)'],
        ['May 5', 'AP Human Geography Exam'],
        ['May 7', 'AP World History Exam'],
        ['May 8', 'AP US History Exam'],
        ['May 12', 'AP Psychology Exam'],
    ]

    table = Table(dates_data, colWidths=[35*mm, 100*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), COLORS['light_gray']),
        ('TEXTCOLOR', (0, 1), (0, -1), COLORS['primary']),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
    ]))
    return table


def create_tier_table(tier, styles):
    """Create student table for a specific tier."""
    tier_students = [s for s in STUDENTS if s['tier'] == tier]

    if tier == 1:
        header_color = COLORS['danger']
        title = 'TIER 1: AT RISK (Score 1-2)'
        desc = 'Intensive intervention required - 2.5-3 hours coaching each'
    elif tier == 2:
        header_color = COLORS['warning']
        title = 'TIER 2: BORDERLINE (Score 3)'
        desc = 'Targeted coaching needed - 1-2 hours each'
    else:
        header_color = COLORS['info']
        title = 'TIER 3-4: ON TRACK (Score 4-5)'
        desc = 'Self-study maintenance plans'

    # Header row
    header = ['Student', 'Subject', 'Score', 'MCQ', 'FRQ', 'Completion', 'Hours']
    data = [header]

    for s in tier_students:
        score_text = f"{s['predicted']} -> {s['target']}"
        completion = f"{s['completion']}%"
        hours = f"{s['hours']}h" if s['hours'] > 0 else '-'
        data.append([
            s['name'],
            s['subject'].replace('AP ', ''),
            score_text,
            f"{s['mcq']}%",
            f"{s['frq']}%",
            completion,
            hours
        ])

    col_widths = [40*mm, 35*mm, 20*mm, 18*mm, 18*mm, 25*mm, 18*mm]
    table = Table(data, colWidths=col_widths)

    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['light_gray']),
    ]

    # Alternating row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_commands.append(('BACKGROUND', (0, i), (-1, i), COLORS['light_gray']))

    table.setStyle(TableStyle(style_commands))

    return [
        Paragraph(f'<b>{title}</b>', styles['SubHeader']),
        Paragraph(desc, styles['SmallText']),
        Spacer(1, 5*mm),
        table,
    ]


def create_weekly_table(styles):
    """Create weekly schedule table."""
    header = ['Week', 'Dates', 'Sessions', 'Focus']
    data = [header]

    for w in WEEKLY_SESSIONS:
        data.append([
            f"Week {w['week']}",
            w['dates'],
            str(w['sessions']),
            w['focus']
        ])

    table = Table(data, colWidths=[25*mm, 40*mm, 25*mm, 70*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['light_gray']),
    ]))

    for i in range(1, len(data)):
        if i % 2 == 0:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), COLORS['light_gray'])]))

    return table


def create_accommodations_table(styles):
    """Create accommodations reference table."""
    data = [
        ['Student', 'Accommodation', 'Notes'],
        ['Branson Pfiester', 'Double Time (+100%)', 'All practice must simulate this'],
        ['Boris Dudarev', 'Time +50%', 'Reduced practice volume; depth-first'],
        ['Cruce Saunders IV', 'Time +50%', 'Strong performance; accommodate exams'],
    ]

    table = Table(data, colWidths=[45*mm, 45*mm, 70*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['info']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (1, 1), (1, -1), colors.HexColor('#e0f2fe')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['light_gray']),
    ]))
    return table


def build_pdf():
    """Build the complete PDF report."""
    pdf_path = OUTPUT_DIR / "AP_Coaching_Master_Report.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=20*mm,
    )

    styles = create_styles()
    story = []

    # Header
    story.append(create_header_table(styles))
    story.append(Spacer(1, 10*mm))

    # Executive Summary
    story.append(Paragraph('<b>Executive Summary</b>', styles['SectionHeader']))
    story.append(Spacer(1, 5*mm))
    story.append(create_summary_cards(styles))
    story.append(Spacer(1, 8*mm))
    story.append(create_key_dates_table(styles))
    story.append(Spacer(1, 8*mm))

    # Charts - Row 1
    print("  Creating charts...")
    score_img = Image(create_score_distribution_chart(), width=85*mm, height=45*mm)
    tier_img = Image(create_tier_pie_chart(), width=65*mm, height=65*mm)

    chart_row1 = Table([[score_img, tier_img]], colWidths=[90*mm, 70*mm])
    chart_row1.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(chart_row1)

    # Page break
    story.append(PageBreak())

    # Performance Analysis
    story.append(Paragraph('<b>Performance Analysis</b>', styles['SectionHeader']))
    story.append(Spacer(1, 5*mm))

    scatter_img = Image(create_mcq_frq_scatter(), width=140*mm, height=100*mm)
    story.append(scatter_img)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        '<b>Key Finding:</b> Students in the bottom-left quadrant struggle with both MCQ and FRQ - '
        'these are our highest priority. Students in the bottom-right (strong MCQ, weak FRQ) need '
        'targeted writing support.',
        styles['Body']
    ))
    story.append(Spacer(1, 8*mm))

    # Charts - Row 2
    hours_img = Image(create_coaching_hours_chart(), width=80*mm, height=55*mm)
    subject_img = Image(create_subject_distribution_chart(), width=70*mm, height=70*mm)

    chart_row2 = Table([[hours_img, subject_img]], colWidths=[85*mm, 75*mm])
    chart_row2.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(chart_row2)

    # Page break
    story.append(PageBreak())

    # Weekly Schedule
    story.append(Paragraph('<b>Weekly Coaching Schedule</b>', styles['SectionHeader']))
    story.append(Spacer(1, 5*mm))

    weekly_img = Image(create_weekly_load_chart(), width=160*mm, height=70*mm)
    story.append(weekly_img)
    story.append(Spacer(1, 8*mm))
    story.append(create_weekly_table(styles))

    # Page break
    story.append(PageBreak())

    # Student Roster by Tier
    story.append(Paragraph('<b>Student Roster by Tier</b>', styles['SectionHeader']))
    story.append(Spacer(1, 5*mm))

    # Tier 1
    story.extend(create_tier_table(1, styles))
    story.append(Spacer(1, 10*mm))

    # Tier 2
    story.extend(create_tier_table(2, styles))

    # Page break
    story.append(PageBreak())

    # Tier 3-4 combined
    story.append(Paragraph('<b>On Track Students (Score 4-5)</b>', styles['SectionHeader']))
    story.append(Paragraph(
        'These students require minimal intervention. They should follow self-study maintenance plans.',
        styles['Body']
    ))
    story.append(Spacer(1, 5*mm))

    tier34_students = [s for s in STUDENTS if s['tier'] in [3, 4]]
    header = ['Student', 'Subject', 'Score', 'MCQ', 'FRQ', 'Completion', 'Tier']
    data = [header]

    for s in tier34_students:
        tier_label = 'Score 4' if s['tier'] == 3 else 'Score 5'
        data.append([
            s['name'],
            s['subject'].replace('AP ', ''),
            str(s['predicted']),
            f"{s['mcq']}%",
            f"{s['frq']}%",
            f"{s['completion']}%",
            tier_label
        ])

    col_widths = [40*mm, 35*mm, 18*mm, 18*mm, 18*mm, 25*mm, 20*mm]
    tier34_table = Table(data, colWidths=col_widths)

    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['success']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['light_gray']),
    ]

    for i in range(1, len(data)):
        if i % 2 == 0:
            style_commands.append(('BACKGROUND', (0, i), (-1, i), COLORS['light_gray']))

    tier34_table.setStyle(TableStyle(style_commands))
    story.append(tier34_table)

    # Accommodations
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph('<b>Accommodations Reference</b>', styles['SectionHeader']))
    story.append(Spacer(1, 5*mm))
    story.append(create_accommodations_table(styles))

    # Footer
    story.append(Spacer(1, 15*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=COLORS['light_gray']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f'<font size="8" color="#6b7280"><b>AP Coaching Plan</b> | Spring 2026 | Confidential | '
        f'Generated {datetime.now().strftime("%B %d, %Y at %H:%M")}</font>',
        styles['CenterText']
    ))

    # Build PDF
    print("  Building PDF...")
    doc.build(story)
    return pdf_path


def main():
    print("Generating AP Coaching Master Report...")
    print()

    pdf_path = build_pdf()

    print()
    print(f"Done! Report saved to: {pdf_path}")


if __name__ == "__main__":
    main()
