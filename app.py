import os
import zipfile
import tempfile
import shutil
from flask import Flask, render_template, request, send_file, after_this_request
from automation_for_app import check_osc_duplicates, process_shapefiles, check_gistool_id, check_invalid_cable_refs, report_splice_counts_by_closure
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', error="No file uploaded")
            
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error="No file selected")
            
        if not file.filename.endswith('.zip'):
            return render_template('index.html', error="File must be a ZIP archive")
        
        try:
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
                
                return render_template(
                    'index.html', 
                    error=f"Could not find output folder in ZIP structure. Directory structure:<pre>{'\n'.join(tree)}</pre>"
                )
            
            # Run validation checks
            results = []
            checks = [
                ("OSC Duplicates Check", check_osc_duplicates),
                ("Cable Reference Validation", check_invalid_cable_refs),
                ("Shapefile Processing", process_shapefiles),
                ("GISTOOL_ID Validation", check_gistool_id),
                ("Splice Count Report", report_splice_counts_by_closure)  # New report
            ]
            
            for name, func in checks:
                result = func(workspace)
                results.append((name, result[0], result[1]))
            
            # Cleanup temporary files
            @after_this_request
            def cleanup(response):
                try:
                    os.remove(zip_path)
                    shutil.rmtree(extract_dir)
                except Exception as e:
                    app.logger.error(f"Cleanup error: {e}")
                return response
            
            return render_template('index.html', results=results, filename=file.filename)
            
        except Exception as e:
            return render_template('index.html', error=f"Processing error: {str(e)}")
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)