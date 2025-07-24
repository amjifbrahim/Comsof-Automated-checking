import os
import sys
import zipfile
import tempfile
import shutil
import io
import json
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation_for_app import (
    check_osc_duplicates, check_invalid_cable_refs,
    report_splice_counts_by_closure, process_shapefiles,
    check_gistool_id, check_cluster_overlaps, check_granularity_fields, 
    validate_non_virtual_closures, validate_feeder_primdistribution_locations,
    validate_cable_diameters
)

from multipart_parser import parse_multipart_form

# Reduced file size limit for serverless environment
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

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

def handler(request):
    """Serverless handler for file validation"""
    
    # Only allow POST requests
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'}),
            'headers': {'Content-Type': 'application/json'}
        }
    
    try:
        # Parse multipart form data
        content_type = request.headers.get('content-type', '')
        if 'multipart/form-data' not in content_type:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid content type. Expected multipart/form-data'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Get request body
        body = request.get_data()
        
        # Parse multipart form data
        try:
            form_data = parse_multipart_form(body, content_type)
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Failed to parse form data: {str(e)}'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Extract file data
        if 'file' not in form_data:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No file uploaded'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        file_info = form_data['file']
        filename = file_info.get('filename', 'unknown.zip')
        file_data = file_info.get('data', b'')
        
        if not filename.endswith('.zip'):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'File must be a ZIP archive'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        file_size = len(file_data)
        if file_size > MAX_FILE_SIZE:
            return {
                'statusCode': 413,
                'body': json.dumps({
                    'error': f'File too large ({file_size / (1024*1024):.1f}MB). Maximum size is 50MB for serverless deployment.'
                }),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Extract checks data
        checks_data = form_data.get('checks', '[]')
        if isinstance(checks_data, bytes):
            checks_data = checks_data.decode('utf-8')
        
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
            
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f"Could not find output folder in ZIP structure. Directory structure:\n{chr(10).join(tree)}"
                }),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Parse selected checks
        try:
            selected_checks = json.loads(checks_data)
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
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'results': results,
                'filename': filename
            }),
            'headers': {'Content-Type': 'application/json'}
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Processing error: {str(e)}'}),
            'headers': {'Content-Type': 'application/json'}
        }