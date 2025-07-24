from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors

def get_pdf_styles():
    """Return custom PDF styles for the validation report"""
    
    # Get base styles
    base_styles = getSampleStyleSheet()
    
    # Create custom styles dictionary
    styles = {
        'title': ParagraphStyle(
            'CustomTitle',
            parent=base_styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            spaceBefore=0,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        ),
        
        'heading2': ParagraphStyle(
            'CustomHeading2',
            parent=base_styles['Heading2'],
            fontSize=16,
            spaceAfter=18,
            spaceBefore=12,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        ),
        
        'section': ParagraphStyle(
            'CustomSection',
            parent=base_styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkred,
            fontName='Helvetica-Bold'
        ),
        
        'normal': ParagraphStyle(
            'CustomNormal',
            parent=base_styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            spaceBefore=3,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ),
        
        'result_title': ParagraphStyle(
            'ResultTitle',
            parent=base_styles['Normal'],
            fontSize=12,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.darkgreen,
            fontName='Helvetica-Bold',
            leftIndent=0
        ),
        
        'passed': ParagraphStyle(
            'PassedResult',
            parent=base_styles['Normal'],
            fontSize=10,
            spaceBefore=4,
            spaceAfter=6,
            textColor=colors.darkgreen,
            fontName='Helvetica',
            leftIndent=20
        ),
        
        'failed': ParagraphStyle(
            'FailedResult',
            parent=base_styles['Normal'],
            fontSize=10,
            spaceBefore=4,
            spaceAfter=6,
            textColor=colors.darkred,
            fontName='Helvetica',
            leftIndent=20
        ),
        
        'error': ParagraphStyle(
            'ErrorResult',
            parent=base_styles['Normal'],
            fontSize=10,
            spaceBefore=4,
            spaceAfter=6,
            textColor=colors.red,
            fontName='Helvetica',
            leftIndent=20
        ),
        
        'metadata': ParagraphStyle(
            'Metadata',
            parent=base_styles['Normal'],
            fontSize=10,
            spaceAfter=3,
            spaceBefore=1,
            textColor=colors.grey,
            fontName='Helvetica',
            alignment=TA_LEFT
        ),
        
        'summary': ParagraphStyle(
            'Summary',
            parent=base_styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            spaceBefore=4,
            textColor=colors.black,
            fontName='Helvetica',
            alignment=TA_JUSTIFY,
            leftIndent=10,
            rightIndent=10
        )
    }
    
    return styles

def get_status_style(status, styles):
    """Return appropriate style based on check status"""
    if status is False:  # Passed
        return styles['passed']
    elif status is True:  # Failed
        return styles['failed']
    else:  # Error/None
        return styles['error']

def format_check_message(message, max_length=500):
    """Format and truncate check messages for PDF display"""
    if not message:
        return "No message provided"
    
    # Convert to string and clean up
    message = str(message)
    
    # Replace problematic characters
    message = message.replace('\r\n', '\n').replace('\r', '\n')
    
    # Truncate if too long
    if len(message) > max_length:
        message = message[:max_length] + "... (truncated)"
    
    # Escape HTML-like characters but preserve line breaks
    message = message.replace('&', '&amp;')
    message = message.replace('<', '&lt;')
    message = message.replace('>', '&gt;')
    message = message.replace('\n', '<br/>')
    
    return message