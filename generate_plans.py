import pandas as pd
import os
import re

def clean_text(text):
    """Fix encoding issues from Excel data"""
    if not isinstance(text, str):
        return text
    # Fix corrupted em-dashes (shows as �_x0080__x0093_ or similar)
    text = re.sub(r'�_x[0-9a-fA-F]{4}__x[0-9a-fA-F]{4}_', '-', text)
    text = re.sub(r'_x[0-9a-fA-F]{4}_', '', text)
    text = text.replace('�', '-')
    # Replace various dash-like characters with standard hyphen
    text = text.replace('\u2013', '-')  # en-dash
    text = text.replace('\u2014', '-')  # em-dash
    # Replace any non-ASCII characters between number and number/letter with hyphen (for date ranges)
    text = re.sub(r'(\d)[^\x00-\x7F]+(\d)', r'\1-\2', text)
    text = re.sub(r'(\d)[^\x00-\x7F]+([A-Za-z])', r'\1-\2', text)
    # Remove any remaining non-ASCII characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    # Clean up any double dashes
    text = re.sub(r'-+', '-', text)
    return text

# Load unit-level data
unit_df = pd.read_excel('AP Progress Tracker - Session 4 - AY 25-26.xlsx', sheet_name='unit_level')

# Student call schedules (date, time)
call_schedules = {
    'Gus Castillo': [('Thu Mar 12', '08:00'), ('Thu Mar 19', '08:00'), ('Thu Mar 26', '08:00'),
                     ('Thu Apr 02', '08:00'), ('Thu Apr 09', '08:00'), ('Thu Apr 16', '08:00'), ('Thu Apr 30', '08:00')],
    'Branson Pfiester': [('Thu Mar 12', '08:35'), ('Thu Mar 19', '08:35'), ('Thu Mar 26', '08:35'),
                          ('Thu Apr 02', '08:35'), ('Thu Apr 16', '08:35'), ('Thu Apr 30', '08:35')],
    'Emma Cotner': [('Thu Mar 12', '09:05'), ('Thu Mar 19', '09:05'), ('Thu Mar 26', '09:05'),
                    ('Thu Apr 02', '09:05'), ('Thu Apr 16', '09:05'), ('Thu Apr 30', '09:05')],
    'Saeed Tarawneh': [('Fri Mar 13', '08:00'), ('Fri Mar 20', '08:00'), ('Fri Mar 27', '08:00'),
                       ('Fri Apr 03', '08:00'), ('Fri Apr 17', '08:00'), ('Fri May 01', '08:00')],
    'Boris Dudarev': [('Wed Mar 11', '08:35'), ('Wed Mar 25', '08:00'), ('Wed Apr 08', '09:05'), ('Wed Apr 29', '08:00')],
    'Sydney Barba': [('Wed Mar 11', '09:05'), ('Wed Mar 25', '08:35'), ('Tue Apr 07', '08:00'), ('Wed Apr 29', '08:35')],
    'Zayen Szpitalak': [('Wed Mar 18', '09:05'), ('Wed Apr 01', '08:00'), ('Wed Apr 15', '08:00'), ('Wed Apr 29', '09:05')],
    'Stella Cole': [('Tue Mar 17', '08:00'), ('Wed Apr 01', '08:35'), ('Wed Apr 15', '08:35'), ('Tue Apr 28', '08:00')],
    'Aheli Shah': [('Fri Mar 13', '08:35'), ('Thu Apr 09', '08:35')],
    'Ella Dietz': [('Fri Mar 13', '09:05'), ('Thu Apr 09', '09:05')],
    'Jackson Price': [('Wed Mar 11', '08:00'), ('Fri Apr 10', '08:00')],
    'Adrienne Laswell': [('Fri Mar 20', '08:35')],
    'Austin Lin': [('Fri Mar 20', '09:05')],
    'Erika Rigby': [('Wed Mar 18', '08:00')],
    'Grady Swanson': [('Wed Mar 18', '08:35')],
    'Jessica Owenby': [('Fri Mar 27', '08:35')],
    'Cruce Saunders IV': [('Fri Mar 27', '09:05')],
    'Kavin Lingham': [('Fri Apr 03', '08:35')],
    'Stella Grams': [('Fri Apr 03', '09:05')],
    'Ali Romman': [('Fri Apr 10', '08:35')],
    'Benny Valles': [('Fri Apr 10', '09:05')],
    'Jacob Kuchinsky': [('Wed Apr 08', '08:00')],
    'Luca Sanchez': [('Wed Apr 08', '08:35')],
    'Vera Li': [('Fri Apr 17', '08:35')],
    'Emily Smith': [('Fri Apr 17', '09:05')],
    'Paty Margain-Junco': [('Fri May 01', '08:35')],
    'Michael Cai': [('Fri May 01', '09:05')]
}

# Student tiers and courses
student_info = {
    'Gus Castillo': ('Critical', 'AP Human Geography', 'May 5'),
    'Branson Pfiester': ('Intensive', 'AP Human Geography', 'May 5'),
    'Emma Cotner': ('Intensive', 'AP World History', 'May 7'),
    'Saeed Tarawneh': ('Intensive', 'AP World History', 'May 7'),
    'Boris Dudarev': ('Moderate', 'AP Human Geography', 'May 5'),
    'Sydney Barba': ('Moderate', 'AP Human Geography', 'May 5'),
    'Zayen Szpitalak': ('Moderate', 'AP Human Geography', 'May 5'),
    'Stella Cole': ('Moderate', 'AP World History', 'May 7'),
    'Aheli Shah': ('Light', 'AP Human Geography', 'May 5'),
    'Ella Dietz': ('Light', 'AP World History', 'May 7'),
    'Jackson Price': ('Light', 'AP World History', 'May 7'),
    'Adrienne Laswell': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Austin Lin': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Erika Rigby': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Grady Swanson': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Jessica Owenby': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Cruce Saunders IV': ('Maintenance', 'AP US History', 'May 8'),
    'Kavin Lingham': ('Maintenance', 'AP World History', 'May 7'),
    'Stella Grams': ('Maintenance', 'AP World History', 'May 7'),
    'Ali Romman': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Benny Valles': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Jacob Kuchinsky': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Luca Sanchez': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Vera Li': ('Maintenance', 'AP Human Geography', 'May 5'),
    'Emily Smith': ('Maintenance', 'AP US Government', 'May 11'),
    'Paty Margain-Junco': ('Maintenance', 'AP US History', 'May 8'),
    'Michael Cai': ('Maintenance', 'AP World History', 'May 7')
}

def get_rag(accuracy, status):
    if status == 'NOT_STARTED':
        return 'RED'
    if pd.isna(accuracy):
        return 'AMBER'
    if accuracy <= 50:
        return 'RED'
    if accuracy <= 74:
        return 'AMBER'
    return 'GREEN'

def get_unit_data(student, course_pattern):
    student_data = unit_df[unit_df['student'] == student]
    course_data = student_data[student_data['course'].str.contains(course_pattern, case=False, na=False)]
    units = course_data[course_data['unit'].str.startswith('Unit ', na=False)].copy()

    results = []
    for _, row in units.iterrows():
        unit_name = row['unit']
        # Clean encoding issues and extract short name
        unit_name = clean_text(unit_name)
        short_name = unit_name.replace('Unit ', '').split(':')[-1].strip()[:30]
        short_name = clean_text(short_name)
        unit_num = int(row['unit_num']) if pd.notna(row['unit_num']) else 0

        accuracy = row['combined_accuracy']
        status = row['unit_status']
        rag = get_rag(accuracy, status)

        acc_str = f"{int(accuracy)}%" if pd.notna(accuracy) else "N/A"

        results.append({
            'num': unit_num,
            'name': short_name,
            'accuracy': acc_str,
            'status': status,
            'rag': rag
        })

    return sorted(results, key=lambda x: x['num'])

def get_course_type(course):
    if 'Human Geography' in course:
        return 'APHG'
    elif 'World History' in course:
        return 'World'
    elif 'US History' in course:
        return 'APUSH'
    elif 'Government' in course:
        return 'Gov'
    return 'Other'

# Course-specific plan sections
def get_plan_section(tier, course_type):
    """Generate plan section based on tier AND course type"""

    if course_type == 'APHG':
        # AP Human Geography - emphasize model drawing
        if tier == 'Critical':
            return """## Your Plan

You have weekly calls. Each week:

**Daily Practice (10-15 min):**
- [ ] Draw 2 models from memory (see list below)
- [ ] Check against reference, correct errors, redraw

**Days 1-3: Build knowledge**
- [ ] Complete Edmentum lessons for focus unit
- [ ] 15 MCQs from this unit

**Days 4-5: Lock it in**
- [ ] Complete URP (Ultimate Review Packet) for this unit
- [ ] FRQ Planning Exercise 1 (8 min) - outline only
- [ ] FRQ Planning Exercise 2 (8 min) - outline only

**Days 6-7: Apply it**
- [ ] FRQ Full Write (15 min timed)
- [ ] Self-score against rubric
- [ ] 15 MCQs mixed review
- [ ] Coaching call

---

## Models to Draw From Memory

Practice drawing these until you can reproduce them perfectly:

1. **Demographic Transition Model (DTM)** - 5 stages, birth/death rates, population growth
2. **Epidemiological Transition Model** - disease types by stage
3. **Burgess Concentric Zone Model** - urban land use rings
4. **Hoyt Sector Model** - wedge-shaped zones
5. **Harris-Ullman Multiple Nuclei Model** - multiple centers
6. **Von Thunen Model** - agricultural land use rings
7. **Rostow's Stages of Growth** - economic development stages

**How to practice:** Draw from memory -> Check -> Correct -> Redraw

---

"""
        elif tier == 'Intensive':
            return """## Your Plan

You have 6 calls over 8 weeks. Each week:

**Daily Practice (10-15 min):**
- [ ] Draw 2 models from memory (see list below)
- [ ] Check against reference, correct errors, redraw

**Days 1-3: Build knowledge**
- [ ] Complete Edmentum lessons for focus unit
- [ ] 15 MCQs from this unit

**Days 4-5: Lock it in**
- [ ] Complete URP (Ultimate Review Packet) for this unit
- [ ] FRQ Planning Exercise (8 min) - outline only

**Days 6-7: Apply it**
- [ ] FRQ Full Write (15 min timed)
- [ ] Self-score against rubric
- [ ] 15 MCQs mixed review

---

## Models to Draw From Memory

Practice drawing these until you can reproduce them perfectly:

1. **Demographic Transition Model (DTM)** - 5 stages, birth/death rates
2. **Burgess Concentric Zone Model** - urban land use rings
3. **Hoyt Sector Model** - wedge-shaped zones
4. **Von Thunen Model** - agricultural land use rings
5. **Rostow's Stages of Growth** - economic development

**How to practice:** Draw from memory -> Check -> Correct -> Redraw

---

"""
        elif tier == 'Moderate':
            return """## Your Plan

You have 4 calls over 8 weeks (every other week). Between calls:

**Daily Practice (10 min):**
- [ ] Draw 2 models from memory
- [ ] Check and correct

**Week focus:**
- [ ] Complete Edmentum lessons for 1-2 units
- [ ] Complete URP for each unit
- [ ] 2 FRQ planning exercises per unit
- [ ] 1 FRQ full write per unit
- [ ] 20 MCQs mixed practice

---

## Models to Draw From Memory

1. Demographic Transition Model (DTM)
2. Burgess Concentric Zone Model
3. Hoyt Sector Model
4. Von Thunen Model
5. Rostow's Stages of Growth

---

"""
        elif tier == 'Light':
            return """## Your Plan

You have 2 check-in calls. Between calls:

**Daily Practice (10 min):**
- [ ] Draw 1-2 models from memory
- [ ] Review any you can't reproduce perfectly

**Weekly focus:**
- [ ] Complete any remaining Edmentum content
- [ ] Review weak units using URP
- [ ] 2-3 FRQ practice (planning + writes)
- [ ] 20 MCQs mixed practice

---

## Models to Draw From Memory

Make sure you can draw all key models without looking.

---

"""
        else:  # Maintenance
            return """## Your Plan

You're on track! Your 1 coaching call is a mid-point check-in.

**Weekly maintenance:**
- [ ] Draw 2 models from memory (stay sharp)
- [ ] 15-20 MCQs mixed practice
- [ ] 1-2 FRQ practice per week
- [ ] Review any AMBER units with URP

---

## Models to Draw From Memory

Keep practicing these so they stay fresh for exam day.

---

"""

    elif course_type in ['World', 'APUSH']:
        # AP World History / APUSH - SAQs as workhorse, distinguish FRQ types
        subject_name = "World History" if course_type == 'World' else "US History"

        if tier == 'Critical':
            return f"""## Your Plan

You have weekly calls. Each week:

**Daily Practice - SAQs are your workhorse:**
- [ ] Complete 3-5 SAQs daily (5 min each)
- [ ] Self-check: Did I answer what was asked? Did I explain WHY, not just WHAT?

**Daily Practice - Narrative Retrieval (10 min):**
- [ ] Write one causal chain from memory (e.g., "Causes of [event]" or "Effects of [event]")
- [ ] Check against notes, identify gaps

**Days 1-3: Build knowledge**
- [ ] Complete Edmentum lessons for focus unit
- [ ] 15 MCQs from this unit

**Days 4-5: Lock it in**
- [ ] Complete URP (Ultimate Review Packet) for this unit
- [ ] DBQ Planning Exercise (10 min) - thesis + document groupings only
- [ ] LEQ Planning Exercise (8 min) - thesis + argument structure only

**Days 6-7: Apply it**
- [ ] 3 more SAQs
- [ ] 15 MCQs mixed review
- [ ] Coaching call

**Full DBQ/LEQ:** Write one complete essay every 2-3 weeks (not weekly)

---

## The Three FRQ Types (Don't Mix Them Up!)

| Type | Time | How Often | What to Practice |
|------|------|-----------|------------------|
| **SAQ** | 3-5 min each | **DAILY (3-5)** | Quick retrieval + application |
| **DBQ Planning** | 8-10 min | 2-3x per week | Thesis + document groupings |
| **LEQ Planning** | 5-8 min | 1-2x per week | Thesis + argument structure |
| **Full DBQ/LEQ** | 35-40 min | Every 2-3 weeks | Integration (needs feedback) |

**Key insight:** These skills don't transfer. Practicing DBQs won't help your SAQs. Practice each separately.

---

## Narrative Retrieval - Causal Chains to Practice

Write these from memory, then check:
- Causes of major wars/conflicts
- Factors leading to revolutions
- Effects of trade/exchange networks
- Rise and decline of empires

---

"""
        elif tier == 'Intensive':
            return f"""## Your Plan

You have 6 calls over 8 weeks. Each week:

**Daily Practice - SAQs are your workhorse:**
- [ ] Complete 3-4 SAQs daily (5 min each)
- [ ] Self-check: Did I explain WHY, not just WHAT?

**Daily Practice - Narrative Retrieval (10 min):**
- [ ] Write one causal chain from memory
- [ ] Check against notes

**Days 1-3: Build knowledge**
- [ ] Complete Edmentum lessons for focus unit
- [ ] 15 MCQs from this unit

**Days 4-5: Lock it in**
- [ ] Complete URP for this unit
- [ ] DBQ Planning Exercise (10 min)

**Days 6-7: Apply it**
- [ ] 3 more SAQs
- [ ] 15 MCQs mixed review

**Full DBQ/LEQ:** Every 2-3 weeks

---

## The Three FRQ Types

| Type | How Often | Focus |
|------|-----------|-------|
| **SAQ** | **DAILY (3-4)** | Your workhorse |
| **DBQ/LEQ Planning** | 2-3x per week | Thesis + structure |
| **Full DBQ/LEQ** | Every 2-3 weeks | Needs feedback |

---

"""
        elif tier == 'Moderate':
            return """## Your Plan

You have 4 calls over 8 weeks. Between calls:

**Daily Practice:**
- [ ] 2-3 SAQs (your workhorse task)
- [ ] Write one causal chain from memory

**Week focus:**
- [ ] Complete Edmentum lessons for 1-2 units
- [ ] Complete URP for each unit
- [ ] 2 DBQ planning exercises per week
- [ ] 1 LEQ planning exercise per week
- [ ] 20 MCQs mixed practice

**Full DBQ/LEQ:** One every 2-3 weeks

---

## The Three FRQ Types

Practice each type separately - they don't transfer!

- **SAQ:** Daily (2-3) - quick retrieval + application
- **DBQ/LEQ Planning:** 2-3x per week - thesis + structure
- **Full Essay:** Every 2-3 weeks - needs feedback

---

"""
        elif tier == 'Light':
            return """## Your Plan

You have 2 check-in calls. Between calls:

**Daily Practice:**
- [ ] 2 SAQs
- [ ] Review weak periods with narrative retrieval

**Weekly focus:**
- [ ] Complete any remaining Edmentum content
- [ ] Review weak units using URP
- [ ] 1-2 DBQ planning exercises
- [ ] 20 MCQs mixed practice

---

## FRQ Types

- **SAQ:** Your daily practice
- **DBQ/LEQ Planning:** 1-2x per week
- **Full Essay:** Only if time permits

---

"""
        else:  # Maintenance
            return """## Your Plan

You're on track! Your 1 coaching call is a mid-point check-in.

**Weekly maintenance:**
- [ ] 2-3 SAQs daily (stay sharp)
- [ ] 15-20 MCQs mixed practice
- [ ] 1 DBQ planning exercise per week
- [ ] Review any AMBER periods with URP

---

## FRQ Types

Keep practicing SAQs - they're quick and keep your retrieval sharp.

---

"""

    elif course_type == 'Gov':
        # AP Government - different FRQ structure
        if tier == 'Maintenance':
            return """## Your Plan

You're on track! Your 1 coaching call is a mid-point check-in.

**Weekly maintenance:**
- [ ] Review required SCOTUS cases (flashcards)
- [ ] 15-20 MCQs mixed practice
- [ ] 1-2 FRQ practice per week (rotate types)
- [ ] Review foundational documents (Fed 10, Brutus 1, etc.)

---

## AP Gov FRQ Types

| Type | Time | Focus |
|------|------|-------|
| **Concept Application** | 20 min | Apply concept to scenario |
| **Quantitative Analysis** | 20 min | Interpret data/charts |
| **SCOTUS Comparison** | 20 min | Compare cases |
| **Argument Essay** | 40 min | Defend a claim |

---

"""
        else:
            return """## Your Plan

**Weekly focus:**
- [ ] Review required SCOTUS cases
- [ ] Complete Edmentum lessons
- [ ] 15-20 MCQs
- [ ] Practice each FRQ type

---

## AP Gov FRQ Types

| Type | Focus |
|------|-------|
| **Concept Application** | Apply concept to scenario |
| **Quantitative Analysis** | Interpret data |
| **SCOTUS Comparison** | Compare cases |
| **Argument Essay** | Defend a claim |

---

"""

    # Default fallback
    return """## Your Plan

**Weekly focus:**
- [ ] Complete Edmentum lessons
- [ ] Complete URP for each unit
- [ ] FRQ practice
- [ ] MCQ practice

---

"""

def get_urp_section(course_type):
    """Get URP explanation section"""
    return """## What is the URP?

The **Ultimate Review Packet** is your unit summary resource. After completing Edmentum lessons, use the URP to:
- Review key terms and concepts
- Practice with additional examples
- Solidify your recall before moving to FRQs

---

"""

def get_frq_section(course_type):
    """Get FRQ guide section based on course type"""

    if course_type == 'APHG':
        return """## FRQ Practice Guide

APHG FRQs are structured: define, explain, give example.

**Planning exercises (2 per unit):**
1. Read the prompt
2. Identify: What concept/model does this need?
3. Outline your response structure
4. List specific examples
5. STOP - don't write it out

**Full writes (1 per unit):**
- 15 minutes timed
- Score yourself against the rubric

---

**Layer 1 first. Solid recall before FRQs. No shortcuts.**
"""

    elif course_type in ['World', 'APUSH']:
        return """## SAQ Self-Check

After each SAQ, ask yourself:
- [ ] Did I directly answer what was asked?
- [ ] Did I provide specific historical evidence?
- [ ] Did I explain WHY/HOW (causation), not just WHAT?

## DBQ Planning Self-Check

After each planning exercise:
- [ ] Does my thesis make a clear, defensible argument?
- [ ] Are documents grouped by theme (not just listed)?
- [ ] Did I identify documents for HIPP analysis?
- [ ] Did I list relevant outside evidence?

---

**Layer 1 first. Solid recall before FRQs. No shortcuts.**
"""

    elif course_type == 'Gov':
        return """## FRQ Practice Guide

**Concept Application:** Apply a concept to a real scenario
**Quantitative Analysis:** Interpret data accurately
**SCOTUS Comparison:** Know your required cases cold
**Argument Essay:** Clear thesis + evidence + reasoning

---

**Layer 1 first. Solid recall before FRQs. No shortcuts.**
"""

    return """## FRQ Practice Guide

**Planning exercises:**
1. Read the prompt
2. Identify what's being asked
3. Outline your response
4. STOP - don't write it out

**Full writes:**
- Timed practice
- Self-score against rubric

---

**Layer 1 first. Solid recall before FRQs. No shortcuts.**
"""

# Create output directory
os.makedirs('student_plans_v3', exist_ok=True)

generated = 0

for student, (tier, course, exam_date) in student_info.items():
    if 'Human Geography' in course:
        pattern = 'Human Geography'
    elif 'World History' in course:
        pattern = 'World History'
    elif 'US History' in course:
        pattern = 'United States History'
    elif 'Government' in course:
        pattern = 'Government'
    else:
        pattern = course

    units = get_unit_data(student, pattern)
    calls = call_schedules.get(student, [])
    red_units = [u for u in units if u['rag'] == 'RED']
    course_type = get_course_type(course)

    filename = student.replace(' ', '_') + '.md'

    # Header
    content = f"# {student} | {course}\n"
    content += f"**Exam: {exam_date}** | **Tier: {tier}**\n\n"
    content += "---\n\n"

    # Unit Status
    content += "## Your Unit Status\n\n"
    content += "| Unit | Topic | Accuracy | RAG |\n"
    content += "|------|-------|----------|-----|\n"

    for u in units:
        content += f"| {u['num']} | {u['name']} | {u['accuracy']} | {u['rag']} |\n"

    content += "\n**RAG Key:** RED = needs work | AMBER = review | GREEN = solid\n\n"

    if red_units:
        red_list = ', '.join([str(u['num']) for u in red_units])
        content += f"**Your focus units:** {red_list}\n\n"

    content += "---\n\n"

    # Coaching Calls
    content += "## Your Coaching Calls\n\n"
    content += "| # | Date | Time |\n"
    content += "|---|------|------|\n"
    for i, (date, time) in enumerate(calls, 1):
        content += f"| {i} | {date} | {time} |\n"

    content += "\n---\n\n"

    # Plan section (course-type and tier specific)
    content += get_plan_section(tier, course_type)

    # URP section
    content += get_urp_section(course_type)

    # FRQ section (course-type specific)
    content += get_frq_section(course_type)

    filepath = f'student_plans_v3/{filename}'
    with open(filepath, 'w') as f:
        f.write(content)
    generated += 1

print(f'Generated {generated} student plans in student_plans_v3/')
