from flask import Flask, render_template, request, jsonify, send_file, session, url_for, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import threading
import queue
from datetime import datetime
import yaml
import json
import shutil
from pathlib import Path

from main import WSPOptimizer
from output_generators.dashboard_builder import DashboardBuilder

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create necessary directories
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, 'logs']:
    os.makedirs(folder, exist_ok=True)

# Job queue for async processing
job_queue = {}
job_status = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Check if all required files are present
        required_files = ['campaigns', 'keywords', 'search_terms', 'products']
        optional_files = ['keyword_targeting']
        
        for file_type in required_files:
            if file_type not in request.files:
                return jsonify({'error': f'Missing {file_type} file'}), 400
            
            file = request.files[file_type]
            if file.filename == '':
                return jsonify({'error': f'No {file_type} file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': f'Invalid file type for {file_type}'}), 400
        
        # Create unique job ID
        job_id = str(uuid.uuid4())
        job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        os.makedirs(job_folder, exist_ok=True)
        
        # Save uploaded files
        file_paths = {}
        for file_type in required_files:
            file = request.files[file_type]
            filename = secure_filename(file.filename)
            filepath = os.path.join(job_folder, f"{file_type}_{filename}")
            file.save(filepath)
            file_paths[file_type] = filepath
        
        # Handle optional files
        for file_type in optional_files:
            if file_type in request.files and request.files[file_type].filename != '':
                file = request.files[file_type]
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(job_folder, f"{file_type}_{filename}")
                    file.save(filepath)
                    file_paths[file_type] = filepath
        
        # Store job information
        job_queue[job_id] = file_paths
        job_status[job_id] = {
            'status': 'queued',
            'progress': 0,
            'message': 'Files uploaded successfully',
            'created_at': datetime.now().isoformat()
        }
        
        # Start optimization in background thread
        thread = threading.Thread(target=run_optimization, args=(job_id, file_paths))
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'Files uploaded successfully. Optimization started.',
            'status_url': url_for('get_job_status', job_id=job_id, _external=True)
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/status/<job_id>')
def get_job_status(job_id):
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job_status[job_id])


@app.route('/results/<job_id>')
def results(job_id):
    if job_id not in job_status:
        return render_template('error.html', message='Job not found'), 404
    
    if job_status[job_id]['status'] != 'completed':
        return render_template('processing.html', job_id=job_id)
    
    # Get results summary
    results_folder = os.path.join(app.config['RESULTS_FOLDER'], job_id)
    summary_file = os.path.join(results_folder, 'summary.json')
    
    if os.path.exists(summary_file):
        with open(summary_file, 'r') as f:
            summary = json.load(f)
    else:
        summary = {}
    
    # List available downloads
    downloads = []
    if os.path.exists(results_folder):
        for file in os.listdir(results_folder):
            if file.endswith(('.csv', '.xlsx', '.html')):
                downloads.append({
                    'filename': file,
                    'url': url_for('download_file', job_id=job_id, filename=file)
                })
    
    return render_template('results.html', 
                         job_id=job_id,
                         summary=summary,
                         downloads=downloads)


@app.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    try:
        file_path = os.path.join(app.config['RESULTS_FOLDER'], job_id, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard/<job_id>')
def dashboard(job_id):
    dashboard_path = os.path.join(app.config['RESULTS_FOLDER'], job_id, 'dashboard.html')
    if os.path.exists(dashboard_path):
        with open(dashboard_path, 'r') as f:
            return f.read()
    else:
        return render_template('error.html', message='Dashboard not found'), 404


def run_optimization(job_id, file_paths):
    try:
        # Update status
        job_status[job_id]['status'] = 'processing'
        job_status[job_id]['progress'] = 10
        job_status[job_id]['message'] = 'Starting optimization...'
        
        # Create results folder
        results_folder = os.path.join(app.config['RESULTS_FOLDER'], job_id)
        os.makedirs(results_folder, exist_ok=True)
        
        # Initialize optimizer
        optimizer = WSPOptimizer()
        
        # Update progress
        job_status[job_id]['progress'] = 20
        job_status[job_id]['message'] = 'Loading and validating data...'
        
        # Run optimization
        summary, recommendations = optimizer.run_full_optimization(file_paths)
        
        # Update progress
        job_status[job_id]['progress'] = 80
        job_status[job_id]['message'] = 'Generating reports...'
        
        # Save results
        save_results(job_id, summary, recommendations, results_folder)
        
        # Update status
        job_status[job_id]['status'] = 'completed'
        job_status[job_id]['progress'] = 100
        job_status[job_id]['message'] = 'Optimization completed successfully!'
        job_status[job_id]['completed_at'] = datetime.now().isoformat()
        job_status[job_id]['results_url'] = url_for('results', job_id=job_id, _external=True)
        
    except Exception as e:
        job_status[job_id]['status'] = 'failed'
        job_status[job_id]['message'] = f'Error: {str(e)}'
        job_status[job_id]['error'] = str(e)
    finally:
        # Clean up uploaded files
        upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)


def save_results(job_id, summary, recommendations, results_folder):
    # Save summary as JSON
    with open(os.path.join(results_folder, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Copy generated files to results folder
    bulk_upload_dir = 'reports/bulk_uploads'
    dashboard_dir = 'reports/dashboards'
    
    # Find and copy the most recent files
    if os.path.exists(bulk_upload_dir):
        files = sorted(os.listdir(bulk_upload_dir), key=lambda x: os.path.getmtime(os.path.join(bulk_upload_dir, x)))
        for file in files[-5:]:  # Copy last 5 files
            if file.endswith(('.csv', '.xlsx')):
                shutil.copy2(os.path.join(bulk_upload_dir, file), results_folder)
    
    # Generate dashboard
    dashboard_builder = DashboardBuilder(output_dir=results_folder)
    dashboard_file = dashboard_builder.create_executive_dashboard(summary, recommendations)
    
    # Rename dashboard to standard name
    if os.path.exists(dashboard_file):
        shutil.move(dashboard_file, os.path.join(results_folder, 'dashboard.html'))


@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)