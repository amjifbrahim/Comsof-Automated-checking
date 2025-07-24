import os
import sys
import io
import json
from datetime import datetime
import base64

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

# Import PDF styles (you'll need to create this)
try:
    from pdf_styles import get_pdf_styles
except ImportError:
    # Fallback if pdf_styles module doesn't exist
    def get_pdf_styles():
        styles = getSampleStyleSheet()
        return {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER
            ),
            'heading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12
            ),
            'section': ParagraphStyle(
                'CustomSection',
                parent=styles['Heading3'],
                fontSize=12,
                spaceAfter=12
            ),
            'normal': styles['Normal'],
            'result_title': ParagraphStyle(
                'ResultTitle',
                parent=styles['Normal'],
                fontSize=11,
                spaceBefore=6,
                spaceAfter=6,
                textColor=colors.darkblue
            )
        }

def handler(request):
    """Serverless handler for PDF export"""
    
    # Only allow POST requests
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'}),
            'headers': {'Content-Type': 'application/json'}
        }
    
    try:
        # Parse JSON request body
        body = request.get_data()
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        
        data = json.loads(body)
        
        if not data or 'results' not in data:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid export request'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Get PDF styles
        styles = get_pdf_styles()
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Title and metadata
        elements.append(Paragraph("Comsof Validation Report", styles['title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"File: {data.get('filename', 'Unknown')}", styles['normal']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['normal']))
        elements.append(Spacer(1, 24))
        
        # Add section showing which checks were run
        elements.append(Paragraph("Checks Performed:", styles['heading2']))
        checks_run = [result[0] for result in data['results']]
        checks_text = ", ".join(checks_run)
        elements.append(Paragraph(checks_text, styles['normal']))
        elements.append(Spacer(1, 24))
        
        # Add detailed results
        elements.append(Paragraph("Detailed Results", styles['section']))
        
        for i, (name, status, message) in enumerate(data['results']):
            # Add result header
            status_text = "Passed" if status is False else "Failed" if status is True else "Error"
            elements.append(Paragraph(f"{i+1}. {name} - {status_text}", styles['result_title']))
            
            # Clean and format message
            clean_message = str(message).replace('\n', '<br/>')
            # Escape any HTML-like characters that aren't intentional
            clean_message = clean_message.replace('<', '&lt;').replace('>', '&gt;').replace('<br/>', '<br/>')
            elements.append(Paragraph(clean_message, styles['normal']))
            
            elements.append(Spacer(1, 12))
        
        # Generate PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Prepare response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_{data.get('filename', timestamp).replace('.zip', '')}.pdf"
        
        # Encode PDF as base64 for serverless response
        pdf_content = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'pdf': pdf_base64,
                'filename': filename
            }),
            'headers': {'Content-Type': 'application/json'}
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'PDF export failed: {str(e)}'}),
            'headers': {'Content-Type': 'application/json'}
        }