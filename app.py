from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import re
from werkzeug.utils import secure_filename
import io
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global variables to store the loaded data
pmnacc_data = None
tscainv_data = None

def load_data():
    """Load CSV data files into memory"""
    global pmnacc_data, tscainv_data
    
    try:
        # Load PMNACC data
        pmnacc_data = pd.read_csv('PMNACC_012025.csv')
        print(f"Loaded PMNACC data: {len(pmnacc_data)} records")
        
        # Load TSCAINV data
        tscainv_data = pd.read_csv('TSCAINV_012025.csv')
        print(f"Loaded TSCAINV data: {len(tscainv_data)} records")
        
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

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

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

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'data_loaded': pmnacc_data is not None and tscainv_data is not None})

if __name__ == '__main__':
    # Load data on startup
    if load_data():
        print("Data loaded successfully!")
    else:
        print("Warning: Failed to load data files")
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 