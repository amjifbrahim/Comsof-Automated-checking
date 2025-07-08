import os
import zipfile
import tempfile
import shutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from automation_for_app import (
    check_osc_duplicates, check_invalid_cable_refs,
    report_splice_counts_by_closure, process_shapefiles,
    check_gistool_id, check_cluster_overlaps, check_granularity_fields, 
    validate_non_virtual_closures, validate_feeder_primdistribution_locations,
    validate_cable_diameters
)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

def extract_zip(zip_path, extract_to):
    """Extract zip file and find the output directory"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Look for the output directory in the expected structure
    base_dir = None
    
    # 1. Check for MRO_* directories
    for name in os.listdir(extract_to):
        if name.startswith('MRO_') and os.path.isdir(os.path.join(extract_to, name)):
            base_dir = os.path.join(extract_to, name)
            break
    
    # 2. If no MRO_* directory found, check for output directly
    if not base_dir:
        base_dir = extract_to
    
    # 3. Look for output directory
    output_dir = os.path.join(base_dir, 'output')
    if os.path.exists(output_dir) and os.path.isdir(output_dir):
        return output_dir
    
    # 4. Fallback: check if any subdirectory contains OUT_Closures.shp
    for root, dirs, files in os.walk(base_dir):
        if 'OUT_Closures.shp' in files:
            return root
    
    return None

@app.route('/')
def serve_frontend():
    """Serve the React app (you'll need to build and place it in a 'build' folder)"""
    return send_from_directory('build', 'index.html')

@app.route('/validate', methods=['POST'])
def validate():
    """API endpoint for validation"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.endswith('.zip'):
            return jsonify({'error': 'File must be a ZIP archive'}), 400
        
        # Save uploaded file
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(zip_path)
        
        # Create temp directory for extraction
        extract_dir = tempfile.mkdtemp()
        workspace = extract_zip(zip_path, extract_dir)
        
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
            try:
                os.remove(zip_path)
                shutil.rmtree(extract_dir)
            except:
                pass
            
            return jsonify({
                'error': f"Could not find output folder in ZIP structure. Directory structure:\\n{'\\n'.join(tree)}"
            }), 400
        
        # Run validation checks
        results = []
        checks = [
            ("OSC Duplicates Check", check_osc_duplicates),
            ("Cluster Overlap Check", check_cluster_overlaps),
            ("Cable Granularity Check", check_granularity_fields),
            ("Non-virtual Closure Validation", validate_non_virtual_closures),
            ("Point Location Validation", validate_feeder_primdistribution_locations),
            ("Cable Diameter Validation", validate_cable_diameters),
            ("Cable Reference Validation", check_invalid_cable_refs),
            ("Shapefile Processing", process_shapefiles),
            ("GISTOOL_ID Validation", check_gistool_id),
            ("Splice Count Report", report_splice_counts_by_closure)
        ]
        
        for name, func in checks:
            try:
                result = func(workspace)
                results.append([name, result[0], result[1]])
            except Exception as e:
                results.append([name, None, f"Error running check: {str(e)}"])
        
        # Cleanup temporary files
        try:
            os.remove(zip_path)
            shutil.rmtree(extract_dir)
        except Exception as e:
            app.logger.error(f"Cleanup error: {e}")
        
        return jsonify({
            'results': results,
            'filename': file.filename
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

# Serve static files for React app
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from React build"""
    return send_from_directory('build', path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)