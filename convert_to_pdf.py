#!/usr/bin/env python3
"""Convert markdown student plans to PDFs using fpdf2."""

import os
import re
from pathlib import Path
from fpdf import FPDF


class MarkdownPDF(FPDF):
    """Custom PDF class for rendering markdown student plans."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def space_remaining(self):
        """Return vertical space remaining on current page."""
        return self.h - self.get_y() - self.b_margin

    def add_title(self, title):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, title, new_x='LMARGIN', new_y='NEXT')
        self.ln(2)

    def add_subtitle(self, text):
        # If less than 40mm left, start new page before this subtitle
        if self.space_remaining() < 40:
            self.add_page()
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 6, text, new_x='LMARGIN', new_y='NEXT')
        self.ln(1)

    def add_heading(self, text):
        # If less than 50mm left, start new page before this heading
        if self.space_remaining() < 50:
            self.add_page()
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 12)
        self.ln(3)
        self.cell(0, 8, text, new_x='LMARGIN', new_y='NEXT')
        self.ln(1)

    def add_paragraph(self, text):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', '', 10)
        self.multi_cell(0, 5, text)
        self.set_x(self.l_margin)
        self.ln(1)

    def add_bullet(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_x(self.l_margin + 5)
        width = self.w - self.l_margin - self.r_margin - 5
        self.multi_cell(width, 5, f"- {text}")
        self.set_x(self.l_margin)

    def add_checkbox(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_x(self.l_margin + 5)
        width = self.w - self.l_margin - self.r_margin - 5
        self.multi_cell(width, 5, f"[ ] {text}")
        self.set_x(self.l_margin)

    def add_table(self, headers, rows):
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 9)

        # Calculate column widths based on content
        page_width = self.w - 2 * self.l_margin
        num_cols = len(headers)

        # Default: distribute evenly but with min width
        if num_cols <= 3:
            col_widths = [page_width / num_cols] * num_cols
        else:
            # For unit status tables (Unit, Topic, Accuracy, RAG)
            # Give Topic more space, others less
            col_widths = []
            for i, header in enumerate(headers):
                h = header.lower()
                if 'topic' in h or 'focus' in h:
                    col_widths.append(page_width * 0.45)
                elif 'unit' in h or '#' in h:
                    col_widths.append(page_width * 0.08)
                elif 'accuracy' in h:
                    col_widths.append(page_width * 0.15)
                elif 'rag' in h:
                    col_widths.append(page_width * 0.12)
                elif 'date' in h:
                    col_widths.append(page_width * 0.20)
                elif 'time' in h:
                    col_widths.append(page_width * 0.15)
                else:
                    col_widths.append(page_width * 0.20)

            # Normalize to fit page
            total = sum(col_widths)
            col_widths = [w * page_width / total for w in col_widths]

        # Header row
        self.set_fill_color(230, 230, 230)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 6, header[:30], border=1, fill=True, align='C')
        self.ln()

        # Data rows
        self.set_font('Helvetica', '', 9)
        for row in rows:
            for i, cell in enumerate(row):
                cell_text = str(cell)[:35] if cell else ''
                width = col_widths[i] if i < len(col_widths) else col_widths[-1]
                self.cell(width, 5, cell_text, border=1, align='C')
            self.ln()
        self.ln(2)
        self.set_x(self.l_margin)


def parse_markdown(content):
    """Parse markdown content into structured elements."""
    elements = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # H1 title
        if line.startswith('# '):
            elements.append(('title', line[2:]))
            i += 1
            continue

        # H2 heading
        if line.startswith('## '):
            elements.append(('heading', line[3:]))
            i += 1
            continue

        # Bold subtitle (like **Exam: May 8**)
        if line.startswith('**') and line.endswith('**'):
            text = line[2:-2]
            elements.append(('subtitle', text))
            i += 1
            continue

        # Horizontal rule
        if line == '---':
            i += 1
            continue

        # Table
        if line.startswith('|'):
            headers = []
            rows = []

            # Parse header
            header_line = line
            header_parts = [p.strip() for p in header_line.split('|')[1:-1]]
            headers = header_parts
            i += 1

            # Skip separator line
            if i < len(lines) and lines[i].strip().startswith('|'):
                i += 1

            # Parse rows
            while i < len(lines) and lines[i].strip().startswith('|'):
                row_line = lines[i].strip()
                row_parts = [p.strip() for p in row_line.split('|')[1:-1]]
                rows.append(row_parts)
                i += 1

            elements.append(('table', (headers, rows)))
            continue

        # Checkbox item
        if line.startswith('- [ ]'):
            text = line[5:].strip()
            elements.append(('checkbox', text))
            i += 1
            continue

        # Bullet item
        if line.startswith('- '):
            text = line[2:].strip()
            elements.append(('bullet', text))
            i += 1
            continue

        # Numbered item
        if re.match(r'^\d+\.', line):
            text = re.sub(r'^\d+\.\s*', '', line)
            elements.append(('bullet', text))
            i += 1
            continue

        # Regular paragraph (clean up markdown formatting)
        text = line
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove italic
        elements.append(('paragraph', text))
        i += 1

    return elements


def convert_md_to_pdf(md_path, pdf_path):
    """Convert a markdown file to PDF."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    elements = parse_markdown(content)

    pdf = MarkdownPDF()
    pdf.add_page()

    for elem_type, elem_content in elements:
        try:
            if elem_type == 'title':
                pdf.add_title(elem_content)
            elif elem_type == 'subtitle':
                pdf.add_subtitle(elem_content)
            elif elem_type == 'heading':
                pdf.add_heading(elem_content)
            elif elem_type == 'paragraph':
                pdf.add_paragraph(elem_content)
            elif elem_type == 'bullet':
                # Clean bold markers and truncate long bullets
                clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', str(elem_content))
                pdf.add_bullet(clean_text)
            elif elem_type == 'checkbox':
                pdf.add_checkbox(elem_content)
            elif elem_type == 'table':
                headers, rows = elem_content
                pdf.add_table(headers, rows)
        except Exception as e:
            # Skip problematic elements but continue
            pass

    pdf.output(pdf_path)


def main():
    """Convert all markdown plans to PDFs."""
    plans_dir = Path('student_plans_v3')
    pdf_dir = plans_dir / 'pdf'
    pdf_dir.mkdir(exist_ok=True)

    md_files = list(plans_dir.glob('*.md'))

    print(f"Converting {len(md_files)} plans to PDF...")

    for md_file in md_files:
        pdf_file = pdf_dir / f"{md_file.stem}.pdf"
        try:
            convert_md_to_pdf(md_file, pdf_file)
            print(f"  Created: {pdf_file.name}")
        except Exception as e:
            print(f"  ERROR: {md_file.name} - {e}")

    print(f"\nDone! PDFs saved to {pdf_dir}")


if __name__ == '__main__':
    main()
