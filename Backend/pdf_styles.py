# pdf_styles.py
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

def get_pdf_styles():
    """Returns a dictionary of basic paragraph styles that work reliably"""
    return {
        'title': ParagraphStyle(
            'Title',
            fontName='Helvetica-Bold',
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=12,
            textColor=colors.black
        ),
        'filename': ParagraphStyle(
            'Filename',
            fontName='Helvetica',
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            textColor=colors.black
        ),
        'date': ParagraphStyle(
            'Date',
            fontName='Helvetica',
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=24,
            textColor=colors.black
        ),
        'section': ParagraphStyle(
            'Section',
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.black
        ),
        'result_title': ParagraphStyle(
            'ResultTitle',
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceAfter=3,
            textColor=colors.black
        ),
        'normal': ParagraphStyle(
            'Normal',
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.black
        )
    }