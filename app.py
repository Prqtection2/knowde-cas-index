from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import re
from werkzeug.utils import secure_filename
import io
import tempfile
from datetime import datetime
import requests

# Import configuration
try:
    from config import GOOGLE_DRIVE_CONFIG, LOCAL_FILES
except ImportError:
    # Fallback configuration if config.py doesn't exist
    GOOGLE_DRIVE_CONFIG = {
        'tscainv': {
            'file_id': 'YOUR_TSCAINV_FILE_ID_HERE',
            'file_name': 'TSCAINV_012025.csv',
            'file_pattern': 'TSCAINV_*.csv',
            'folder_name': 'Chemical_Databases',
            'name': 'TSCA Inventory Database',
            'last_updated': '2025-01-23 18:30:00',
            'enabled': True
        },
        'pmnacc': {
            'file_id': 'YOUR_PMNACC_FILE_ID_HERE',
            'file_name': 'PMNACC_012025.csv',
            'file_pattern': 'PMNACC_*.csv',
            'folder_name': 'Chemical_Databases',
            'name': 'PMNACC Database',
            'last_updated': '2025-01-23 18:30:00',
            'enabled': False
        }
    }
    LOCAL_FILES = {
        'tscainv': 'TSCAINV_012025.csv',
        'pmnacc': 'PMNACC_012025.csv'
    }

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global variables to store the loaded data
pmnacc_data = None
tscainv_data = None

# Use configuration from config.py
GOOGLE_DRIVE_FILES = GOOGLE_DRIVE_CONFIG

def load_data():
    """Load CSV data files into memory"""
    global pmnacc_data, tscainv_data
    
    try:
        # Try to load from Google Drive first
        tscainv_file_id = GOOGLE_DRIVE_FILES.get('tscainv', {}).get('file_id')
        
        if tscainv_file_id and tscainv_file_id != 'YOUR_TSCAINV_FILE_ID_HERE':
            # Try to load from Google Drive
            try:
                tscainv_url = f"https://drive.google.com/uc?export=download&id={tscainv_file_id}"
                tscainv_data = pd.read_csv(tscainv_url)
                print(f"Loaded TSCAINV data from Google Drive: {len(tscainv_data)} records")
            except Exception as e:
                print(f"Failed to load TSCAINV from Google Drive: {e}")
                # Fallback to local file
                tscainv_data = pd.read_csv('TSCAINV_012025.csv')
                print(f"Loaded TSCAINV data from local file: {len(tscainv_data)} records")
        else:
            # Load from local files
            tscainv_data = pd.read_csv('TSCAINV_012025.csv')
            print(f"Loaded TSCAINV data from local file: {len(tscainv_data)} records")
        
        # Load PMNACC data (local only for now)
        try:
            pmnacc_data = pd.read_csv('PMNACC_012025.csv')
            print(f"Loaded PMNACC data: {len(pmnacc_data)} records")
        except Exception as e:
            print(f"Warning: Could not load PMNACC data: {e}")
            pmnacc_data = None
        
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

def normalize_cas_number(cas_number):
    """Remove dashes and spaces from CAS number"""
    if pd.isna(cas_number):
        return ""
    return str(cas_number).replace('-', '').replace(' ', '')

def search_cas_number(normalized_cas, database='all'):
    """Search for CAS number in specified database(s)"""
    results = []
    
    # Search in PMNACC data
    if database in ['pmnacc', 'all'] and pmnacc_data is not None:
        pmnacc_match = pmnacc_data[
            pmnacc_data['ACCNO'].apply(lambda x: normalize_cas_number(x) == normalized_cas)
        ]
        
        if not pmnacc_match.empty:
            for _, row in pmnacc_match.iterrows():
                results.append({
                    'source': 'PMNACC',
                    'casNumber': row['ACCNO'],
                    'chemicalName': row['GenericName'],
                    'flag': row['FLAG'],
                    'activity': row['ACTIVITY']
                })
    
    # Search in TSCAINV data
    if database in ['tscainv', 'all'] and tscainv_data is not None:
        tscainv_match = tscainv_data[
            (tscainv_data['casregno'].apply(lambda x: normalize_cas_number(x) == normalized_cas)) |
            (tscainv_data['CASRN'].apply(lambda x: normalize_cas_number(x) == normalized_cas))
        ]
        
        if not tscainv_match.empty:
            for _, row in tscainv_match.iterrows():
                results.append({
                    'source': 'TSCAINV',
                    'casNumber': row['CASRN'] if pd.notna(row['CASRN']) else row['casregno'],
                    'chemicalName': row['ChemName'],
                    'flag': row['FLAG'],
                    'activity': row['ACTIVITY']
                })
    
    return results

def extract_cas_numbers_from_file(file_content, filename):
    """Extract CAS numbers from uploaded file"""
    cas_numbers = set()
    
    try:
        if filename.lower().endswith('.csv'):
            # Parse CSV file
            df = pd.read_csv(io.StringIO(file_content))
            
            # Look for columns that might contain CAS numbers
            for column in df.columns:
                for value in df[column].dropna():
                    normalized = normalize_cas_number(value)
                    if re.match(r'^\d{5,10}$', normalized):  # Basic CAS number validation
                        cas_numbers.add(normalized)
        else:
            # Parse text file (one CAS number per line)
            lines = file_content.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    normalized = normalize_cas_number(line)
                    if re.match(r'^\d{5,10}$', normalized):
                        cas_numbers.add(normalized)
    
    except Exception as e:
        print(f"Error processing file: {e}")
        return []
    
    return list(cas_numbers)

def get_google_drive_file_info(file_config):
    """Get file information from Google Drive using multiple strategies"""
    try:
        # Strategy 1: Try using file ID first
        if file_config.get('file_id') and file_config['file_id'] != 'YOUR_TSCAINV_FILE_ID_HERE':
            url = f"https://drive.google.com/uc?export=download&id={file_config['file_id']}"
            response = requests.head(url, allow_redirects=True)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'method': 'file_id',
                    'last_modified': response.headers.get('Last-Modified', 'Unknown'),
                    'size': response.headers.get('Content-Length', 'Unknown'),
                    'file_name': file_config.get('file_name', 'Unknown')
                }
        
        # Strategy 2: Try using file name pattern (for future implementation)
        # This would require Google Drive API authentication
        # For now, return a fallback response
        return {
            'success': True,
            'method': 'fallback',
            'last_modified': file_config.get('last_updated', 'Unknown'),
            'size': 'Unknown (requires API)',
            'file_name': file_config.get('file_name', 'Unknown'),
            'note': 'File ID not configured. Please update file_id in app.py'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'method': 'error'
        }

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/update-panel')
def update_panel():
    """Update panel page"""
    return render_template('update_panel.html', databases=GOOGLE_DRIVE_FILES)

@app.route('/api/search', methods=['POST'])
def search():
    """API endpoint for searching CAS numbers"""
    try:
        data = request.get_json()
        cas_number = data.get('casNumber', '').strip()
        database = data.get('database', 'all')
        
        if not cas_number:
            return jsonify({'error': 'Please provide a CAS number'}), 400
        
        normalized_cas = normalize_cas_number(cas_number)
        results = search_cas_number(normalized_cas, database)
        
        if not results:
            return jsonify({'error': f'No results found for CAS number: {cas_number}'}), 404
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API endpoint for uploading files with CAS numbers"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        database = request.form.get('database', 'all')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        file_content = file.read().decode('utf-8')
        filename = secure_filename(file.filename)
        
        # Extract CAS numbers from file
        cas_numbers = extract_cas_numbers_from_file(file_content, filename)
        
        if not cas_numbers:
            return jsonify({'error': 'No valid CAS numbers found in the uploaded file'}), 400
        
        # Search for all CAS numbers
        all_results = []
        for cas in cas_numbers:
            results = search_cas_number(cas, database)
            all_results.extend(results)
        
        if not all_results:
            return jsonify({'error': 'No matching chemicals found for the CAS numbers in the uploaded file'}), 404
        
        return jsonify({'results': all_results})
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/update-database', methods=['POST'])
def update_database():
    """API endpoint for updating database from Google Drive"""
    try:
        data = request.get_json()
        database_key = data.get('database')
        
        if database_key not in GOOGLE_DRIVE_FILES:
            return jsonify({'error': 'Invalid database specified'}), 400
        
        database_info = GOOGLE_DRIVE_FILES[database_key]
        
        if not database_info.get('enabled', True):
            return jsonify({'error': 'This database is currently disabled'}), 400
        
        # For now, simulate the update process
        # In the future, this will:
        # 1. Download new file from Google Drive
        # 2. Replace the existing file content (same file ID)
        # 3. Update the local database
        # 4. Reload the data
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Simulate update process
        update_status = {
            'success': True,
            'message': f'{database_info["name"]} update initiated',
            'timestamp': current_time,
            'details': {
                'method': 'Google Drive API Replace',
                'file_id': database_info.get('file_id', 'Not configured'),
                'status': 'Update will replace file content while keeping same file ID'
            }
        }
        
        return jsonify(update_status)
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/database-info')
def database_info():
    """API endpoint for getting database information"""
    try:
        info = {}
        for key, db_info in GOOGLE_DRIVE_FILES.items():
            if db_info.get('enabled', True):
                file_info = get_google_drive_file_info(db_info)
                info[key] = {
                    'name': db_info['name'],
                    'last_updated': db_info.get('last_updated', 'Unknown'),
                    'file_info': file_info,
                    'local_loaded': {
                        'tscainv': tscainv_data is not None,
                        'pmnacc': pmnacc_data is not None
                    }[key] if key in ['tscainv', 'pmnacc'] else False
                }
        
        return jsonify(info)
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    global pmnacc_data, tscainv_data
    
    status = {
        'status': 'healthy',
        'data_loaded': {
            'tscainv': tscainv_data is not None,
            'pmnacc': pmnacc_data is not None
        },
        'record_counts': {
            'tscainv': len(tscainv_data) if tscainv_data is not None else 0,
            'pmnacc': len(pmnacc_data) if pmnacc_data is not None else 0
        },
        'total_records': (len(tscainv_data) if tscainv_data is not None else 0) + 
                        (len(pmnacc_data) if pmnacc_data is not None else 0)
    }
    
    return jsonify(status)

if __name__ == '__main__':
    # Load data on startup
    if load_data():
        print("Data loaded successfully!")
    else:
        print("Warning: Failed to load data files")
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 