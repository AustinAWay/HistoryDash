#!/usr/bin/env python3
"""Convert main planning markdown files to PDF."""

import re
from pathlib import Path
from fpdf import FPDF

PROJECT_DIR = Path(r"C:\Users\Adam Work\PycharmProjects\coaching_coach")
OUTPUT_DIR = PROJECT_DIR / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

MAIN_DOCS = [
    "COACHING_PLAN.md",
    "INTERVENTION_TRACKING.md",
    "PERSONALIZED_LEARNING_PLANS_V2.md",
]


def sanitize_text(text):
    """Replace special Unicode characters with ASCII equivalents."""
    replacements = {
        '\u2192': '->', '\u2190': '<-', '\u2713': '[x]', '\u2717': '[ ]',
        '\u2022': '*', '\u2014': '--', '\u2013': '-', '\u201c': '"',
        '\u201d': '"', '\u2018': "'", '\u2019': "'", '\u2026': '...',
        '\u00a0': ' ', '\u2605': '*', '\u2606': '*', '\u25cf': '*', '\u25cb': 'o',
        '\u2260': '!=', '\u2248': '~',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('ascii', 'replace').decode('ascii')


class MarkdownPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(12, 12, 12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
        self.set_text_color(0)

    def space_remaining(self):
        return self.h - self.get_y() - self.b_margin

    def write_title(self, title, level=1):
        self.set_x(self.l_margin)
        title = sanitize_text(title)
        min_space = {1: 50, 2: 45, 3: 40}
        if self.space_remaining() < min_space.get(level, 25):
            self.add_page()
        if level == 1:
            self.set_font('Helvetica', 'B', 14)
            self.multi_cell(0, 7, title)
            self.line(self.l_margin, self.get_y(), 198, self.get_y())
            self.ln(3)
        elif level == 2:
            self.ln(2)
            self.set_font('Helvetica', 'B', 11)
            self.multi_cell(0, 5, title)
            self.ln(2)
        elif level == 3:
            self.ln(1)
            self.set_font('Helvetica', 'B', 10)
            self.multi_cell(0, 5, title)
            self.ln(1)

    def write_paragraph(self, text):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', '', 8)
        self.multi_cell(0, 4, sanitize_text(text))
        self.ln(1)

    def write_bullet(self, text, checkbox=None):
        self.set_x(self.l_margin)
        text = sanitize_text(text)
        if checkbox is True:
            prefix = "[x] "
        elif checkbox is False:
            prefix = "[ ] "
        else:
            prefix = "- "
        self.set_font('Helvetica', '', 8)
        self.multi_cell(0, 4, prefix + text)

    def write_table(self, headers, rows):
        if not headers or not rows:
            return
        self.set_x(self.l_margin)
        headers = [sanitize_text(h)[:30] for h in headers]
        rows = [[sanitize_text(str(c))[:30] for c in row] for row in rows]
        num_cols = len(headers)
        col_width = (210 - self.l_margin - self.r_margin) / num_cols
        table_height = 5 + len(rows) * 4 + 4
        if self.space_remaining() < table_height:
            self.add_page()
        self.set_font('Helvetica', 'B', 7)
        self.set_fill_color(240, 240, 240)
        for h in headers:
            self.cell(col_width, 5, h, border=1, fill=True)
        self.ln()
        self.set_font('Helvetica', '', 7)
        for row in rows:
            self.set_x(self.l_margin)
            while len(row) < num_cols:
                row.append('')
            for c in row[:num_cols]:
                self.cell(col_width, 4, c, border=1)
            self.ln()
        self.ln(2)

    def write_code(self, code):
        self.set_x(self.l_margin)
        code = sanitize_text(code)
        self.set_font('Courier', '', 7)
        self.set_fill_color(244, 244, 244)
        for line in code.split('\n'):
            self.set_x(self.l_margin)
            self.cell(0, 3.5, line[:90], fill=True)
            self.ln()
        self.ln(1)

    def write_hr(self):
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), 198, self.get_y())
        self.ln(2)


def is_table_separator(line):
    line = line.strip()
    if not line.startswith('|'):
        return False
    parts = [p.strip() for p in line.split('|') if p.strip()]
    return all(re.match(r'^[-:]+$', p) for p in parts)


def parse_table(lines, start_idx):
    if start_idx + 1 >= len(lines):
        return None, None, start_idx + 1
    header_line = lines[start_idx].strip()
    sep_line = lines[start_idx + 1].strip() if start_idx + 1 < len(lines) else ""
    if not header_line.startswith('|') or not is_table_separator(sep_line):
        return None, None, start_idx + 1
    headers = [h.strip() for h in header_line.split('|') if h.strip()]
    rows = []
    i = start_idx + 2
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith('|') or not '|' in line[1:]:
            break
        row = [c.strip() for c in line.split('|') if c.strip()]
        if row:
            rows.append(row)
        i += 1
    return headers, rows, i


def convert_markdown_to_pdf(md_path: Path, pdf_path: Path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    pdf = MarkdownPDF()
    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code_block:
                pdf.write_code('\n'.join(code_lines))
                code_lines = []
            in_code_block = not in_code_block
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        if stripped.startswith('# ') and not stripped.startswith('##'):
            pdf.write_title(stripped[2:], level=1)
        elif stripped.startswith('## ') and not stripped.startswith('###'):
            pdf.write_title(stripped[3:], level=2)
        elif stripped.startswith('### '):
            pdf.write_title(stripped[4:], level=3)
        elif stripped == '---':
            pdf.write_hr()
        elif stripped.startswith('|') and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            headers, rows, new_i = parse_table(lines, i)
            if headers and rows:
                pdf.write_table(headers, rows)
            i = new_i
            continue
        elif stripped.startswith('- [ ]'):
            pdf.write_bullet(stripped[5:].strip(), checkbox=False)
        elif stripped.startswith('- [x]'):
            pdf.write_bullet(stripped[5:].strip(), checkbox=True)
        elif stripped.startswith('- '):
            pdf.write_bullet(stripped[2:])
        elif stripped.startswith('**') and stripped.endswith('**'):
            inner = stripped.strip('*')
            pdf.set_x(pdf.l_margin)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.multi_cell(0, 4, sanitize_text(inner))
            pdf.ln(1)
        elif stripped:
            pdf.write_paragraph(stripped)

        i += 1

    pdf.output(str(pdf_path))


def main():
    print("Converting main planning documents to PDF...")
    print()

    for md_name in MAIN_DOCS:
        md_path = PROJECT_DIR / md_name
        if not md_path.exists():
            print(f"  {md_name} - NOT FOUND, skipping")
            continue

        pdf_name = md_name.replace('.md', '.pdf')
        pdf_path = OUTPUT_DIR / pdf_name

        try:
            convert_markdown_to_pdf(md_path, pdf_path)
            print(f"  {md_name} -> {pdf_name} OK")
        except Exception as e:
            print(f"  {md_name} - ERROR: {str(e)[:50]}")

    print()
    print(f"Done! Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
