from flask import Flask, request, jsonify, Response
import os
import zipfile
import tempfile
import shutil
import io
import json
from datetime import datetime
from werkzeug.exceptions import RequestEntityTooLarge

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

# Import your validation functions
from automation_for_app import (
    check_osc_duplicates, check_invalid_cable_refs,
    report_splice_counts_by_closure, process_shapefiles,
    check_gistool_id, check_cluster_overlaps, check_granularity_fields, 
    validate_non_virtual_closures, validate_feeder_primdistribution_locations,
    validate_cable_diameters
)

# Note: You'll need to create this module separately
from pdf_styles import get_pdf_styles

app = Flask(__name__)

# Reduced file size limit for serverless environment
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Vercel has limits)

def extract_zip_from_bytes(zip_data):
    """Extract zip file from bytes data and find the output directory"""
    # Create a temporary directory
    extract_dir = tempfile.mkdtemp()
    
    try:
        # Write zip data to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip.write(zip_data)
            temp_zip_path = temp_zip.name
        
        # Extract zip file
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Clean up temp zip file
        os.unlink(temp_zip_path)
        
        # Look for the output directory in the expected structure
        base_dir = None
        
        # 1. Check for MRO_* directories
        for name in os.listdir(extract_dir):
            if name.startswith('MRO_') and os.path.isdir(os.path.join(extract_dir, name)):
                base_dir = os.path.join(extract_dir, name)
                break
        
        # 2. If no MRO_* directory found, check for output directly
        if not base_dir:
            base_dir = extract_dir
        
        # 3. Look for output directory
        output_dir = os.path.join(base_dir, 'output')
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            return output_dir, extract_dir
        
        # 4. Fallback: check if any subdirectory contains OUT_Closures.shp
        for root, dirs, files in os.walk(base_dir):
            if 'OUT_Closures.shp' in files:
                return root, extract_dir
        
        return None, extract_dir
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        raise e

def validate_handler():
    """Main validation handler"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.endswith('.zip'):
            return jsonify({'error': 'File must be a ZIP archive'}), 400
        
        # Read file data into memory
        file_data = file.read()
        file_size = len(file_data)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'error': f'File too large ({file_size / (1024*1024):.1f}MB). Maximum size is 50MB for serverless deployment.'
            }), 413
        
        # Extract zip from memory
        workspace, extract_dir = extract_zip_from_bytes(file_data)
        
        if not workspace:
            # Generate directory tree for debugging
            tree = []
            for root, dirs, files in os.walk(extract_dir):
                level = root.replace(extract_dir, '').count(os.sep)
                indent = ' ' * 4 * level
                tree.append(f'{indent}{os.path.basename(root)}/')
                subindent = ' ' * 4 * (level + 1)
                for f in files:
                    tree.append(f'{subindent}{f}')
            
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            
            return jsonify({
                'error': f"Could not find output folder in ZIP structure. Directory structure:\n{chr(10).join(tree)}"
            }), 400
        
        # Get selected checks from form data
        checks_json = request.form.get('checks', '[]')
        try:
            selected_checks = json.loads(checks_json)
        except json.JSONDecodeError:
            selected_checks = []
        
        # If no checks selected, use all checks as default
        if not selected_checks:
            selected_checks = [
                "OSC Duplicates Check",
                "Cluster Overlap Check",
                "Cable Granularity Check",
                "Non-virtual Closure Validation",
                "Point Location Validation",
                "Cable Diameter Validation",
                "Cable Reference Validation",
                "Shapefile Processing",
                "GISTOOL_ID Validation",
                "Splice Count Report"
            ]
        
        # Mapping of check names to functions
        CHECK_FUNCTIONS = {
            "OSC Duplicates Check": check_osc_duplicates,
            "Cluster Overlap Check": check_cluster_overlaps,
            "Cable Granularity Check": check_granularity_fields,
            "Non-virtual Closure Validation": validate_non_virtual_closures,
            "Point Location Validation": validate_feeder_primdistribution_locations,
            "Cable Diameter Validation": validate_cable_diameters,
            "Cable Reference Validation": check_invalid_cable_refs,
            "Shapefile Processing": process_shapefiles,
            "GISTOOL_ID Validation": check_gistool_id,
            "Splice Count Report": report_splice_counts_by_closure
        }
        
        # Run only selected checks
        results = []
        for check_name in selected_checks:
            if check_name in CHECK_FUNCTIONS:
                try:
                    check_func = CHECK_FUNCTIONS[check_name]
                    status, message = check_func(workspace)
                    results.append([check_name, status, message])
                except Exception as e:
                    results.append([check_name, None, f"Error running check: {str(e)}"])
            else:
                results.append([check_name, None, "Check function not found"])
        
        # Cleanup temporary files
        shutil.rmtree(extract_dir, ignore_errors=True)
        
        return jsonify({
            'results': results,
            'filename': file.filename
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

def export_pdf_handler():
    """PDF export handler"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({'error': 'Invalid export request'}), 400
        
        # Get basic styles
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
            clean_message = message.replace('\n', '<br/>')
            elements.append(Paragraph(clean_message, styles['normal']))
            
            elements.append(Spacer(1, 12))
        
        # Generate PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Prepare response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_{data.get('filename', timestamp).replace('.zip', '')}.pdf"
        
        return Response(
            buffer.getvalue(),
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
        
    except Exception as e:
        return jsonify({'error': f'PDF export failed: {str(e)}'}), 500

def health_handler():
    """Health check handler"""
    return jsonify({'status': 'healthy'})

# Main handler function for Vercel
def handler(request):
    """Main serverless handler for Vercel"""
    with app.test_request_context(
        path=request.url.path,
        method=request.method,
        headers=request.headers,
        data=request.get_data(),
        query_string=request.url.query
    ):
        try:
            if request.method == 'POST' and request.url.path == '/api/validate':
                return validate_handler()
            elif request.method == 'POST' and request.url.path == '/api/export-pdf':
                return export_pdf_handler()
            elif request.method == 'GET' and request.url.path == '/api/health':
                return health_handler()
            else:
                return jsonify({'error': 'Endpoint not found'}), 404
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500