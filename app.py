import os
import pandas as pd
import requests
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import json
from config import GOOGLE_DRIVE_CONFIG, FLAG_DEFINITIONS

app = Flask(__name__)

# Global data storage - will be populated dynamically
database_data = {}
database_metadata = {}

def normalize_cas_number(cas_number):
    """Normalize CAS number by removing dashes and spaces"""
    if pd.isna(cas_number):
        return ""
    return str(cas_number).replace('-', '').replace(' ', '').strip()

def load_database(database_key, config):
    """Generic function to load any database from Google Drive"""
    try:
        print(f"Loading {config['name']} from Google Drive...")
        
        # Construct Google Drive download URL
        file_id = config['file_id']
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"{config['name']} Response Status: {response.status_code}")
        print(f"{config['name']} Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"{config['name']} Content Length: {len(response.content)}")
        
        if response.status_code == 200:
            try:
                from io import StringIO
                csv_content = StringIO(response.text)
                data = pd.read_csv(csv_content)
                print(f"{config['name']} data loaded successfully. Shape: {data.shape}")
                print(f"{config['name']} columns: {list(data.columns)}")
                
                # Store the data and metadata
                database_data[database_key] = data
                database_metadata[database_key] = {
                    'name': config['name'],
                    'shape': data.shape,
                    'columns': list(data.columns),
                    'enabled': config['enabled']
                }
                
                return True
            except Exception as csv_error:
                print(f"CSV parsing error for {config['name']}: {csv_error}")
                print(f"First 500 chars of response: {response.text[:500]}")
                return False
        else:
            print(f"Failed to load {config['name']} from Google Drive. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error loading {config['name']}: {e}")
        return False

def load_all_databases():
    """Load all enabled databases from config"""
    print("Starting data loading process...")
    
    success_count = 0
    total_enabled = sum(1 for config in GOOGLE_DRIVE_CONFIG.values() if config['enabled'])
    
    for database_key, config in GOOGLE_DRIVE_CONFIG.items():
        if config['enabled']:
            if load_database(database_key, config):
                success_count += 1
            else:
                print(f"✗ Failed to load {config['name']}")
        else:
            print(f"{config['name']} disabled in config")
    
    print("Data loading process completed.")
    
    if success_count == total_enabled:
        print("✓ All databases loaded successfully")
        return True
    elif success_count > 0:
        print(f"⚠ {success_count}/{total_enabled} databases loaded successfully")
        return True
    else:
        print("✗ Failed to load any databases - application may not work properly")
        return False

def get_flag_description(flag, database_key):
    """Get description for a flag or list of flags"""
    if pd.isna(flag) or not flag or flag == 'N/A':
        return "No flag information available"
    
    # Get flag definitions for this database
    db_flags = FLAG_DEFINITIONS.get(database_key, {})
    
    # Split flags if multiple (e.g., "PMN; S; 5E")
    flags = [f.strip() for f in str(flag).split(';')]
    
    descriptions = []
    for f in flags:
        if f in db_flags:
            descriptions.append(f"{f}: {db_flags[f]}")
        else:
            descriptions.append(f"{f}: Flag description not available")
    
    return "; ".join(descriptions)

def search_database(database_key, normalized_cas):
    """Generic function to search any database for a CAS number"""
    if database_key not in database_data:
        return []
    
    data = database_data[database_key]
    config = GOOGLE_DRIVE_CONFIG[database_key]
    results = []
    
    # Get the CAS column name from config
    cas_column = config.get('cas_column', 'CAS No.')  # Default fallback
    
    # Search in the CAS column
    matches = data[data[cas_column].apply(lambda x: normalize_cas_number(x) == normalized_cas)]
    
    if not matches.empty:
        for _, row in matches.iterrows():
            # Build result based on database configuration
            result = {
                'database': config['name'],
                'cas_number': str(row.get(cas_column, normalized_cas)),
                'chemical_name': str(row.get(config.get('name_column', 'Chemical Name'), 'Unknown')),
                'flag': str(row.get(config.get('flag_column', 'FLAG'), 'N/A')),
                'activity': str(row.get(config.get('activity_column', 'ACTIVITY'), 'Unknown'))
            }
            
            # Apply database-specific logic
            if database_key == 'kecl':
                # KECL specific logic: YES/NO -> ACTIVE/INACTIVE
                value = str(row.get('Value', '')).upper()
                if value == 'YES':
                    result['activity'] = 'ACTIVE'
                elif value == 'NO':
                    result['activity'] = 'INACTIVE'
                result['flag'] = 'N/A'  # KECL doesn't have flags
            elif database_key == 'tscainv':
                # TSCA specific logic: handle nan flags
                if pd.isna(result['flag']) or result['flag'] == 'nan':
                    result['flag'] = 'N/A'
            
            # Add flag description if available
            if result['flag'] != 'N/A':
                result['flagDescription'] = get_flag_description(result['flag'], database_key)
            
            results.append(result)
    else:
        # Handle "not found" cases based on database type
        if database_key == 'kecl':
            # KECL: not found = INACTIVE
            results.append({
                'database': config['name'],
                'chemical_name': 'Not listed in KECL',
                'flag': 'N/A',
                'activity': 'INACTIVE',
                'cas_number': normalized_cas
            })
    
    return results

def search_cas_number(normalized_cas):
    """Search for CAS number across all loaded databases"""
    all_results = []
    
    for database_key in database_data.keys():
        if GOOGLE_DRIVE_CONFIG[database_key]['enabled']:
            results = search_database(database_key, normalized_cas)
            all_results.extend(results)
    
    return all_results

# Load data when app starts
if load_all_databases():
    print("✓ Data loaded successfully")
else:
    print("✗ Failed to load data - application may not work properly")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update-panel')
def update_panel():
    return render_template('update_panel.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'data_loaded': len(database_data) > 0,
        'databases_loaded': list(database_data.keys()),
        'total_databases': len([k for k, v in GOOGLE_DRIVE_CONFIG.items() if v['enabled']])
    })

@app.route('/api/search', methods=['POST'])
def search():
    """Search for CAS number across selected databases"""
    try:
        data = request.get_json()
        cas_number = data.get('casNumber', '').strip()
        databases = data.get('databases', [])
        
        if not cas_number:
            return jsonify({'error': 'CAS number is required'}), 400
        
        # Normalize CAS number
        normalized_cas = normalize_cas_number(cas_number)
        
        # Search across all databases if none specified
        if not databases or 'all' in databases:
            results = search_cas_number(normalized_cas)
        else:
            # Filter by selected databases
            results = []
            for database_key in databases:
                if database_key in database_data and GOOGLE_DRIVE_CONFIG[database_key]['enabled']:
                    db_results = search_database(database_key, normalized_cas)
                    results.extend(db_results)
        
        if not results:
            return jsonify({'error': f'No results found for CAS number: {cas_number}'}), 404
        
        return jsonify({'results': results})
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    """Handle file upload for batch processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        databases = json.loads(request.form.get('databases', '[]'))
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        all_results = []
        
        # Process each line
        for line in lines:
            line = line.strip()
            if line:
                # Try to extract CAS number from the line
                # Look for common CAS patterns
                import re
                cas_match = re.search(r'\b\d{1,7}-\d{2}-\d\b', line)
                if cas_match:
                    cas_number = cas_match.group()
                else:
                    # Try to find numbers that might be CAS numbers
                    numbers = re.findall(r'\b\d{5,10}\b', line)
                    if numbers:
                        cas_number = numbers[0]
                    else:
                        continue
                
                # Search for this CAS number
                normalized_cas = normalize_cas_number(cas_number)
                if normalized_cas:
                    if not databases or 'all' in databases:
                        results = search_cas_number(normalized_cas)
                    else:
                        results = []
                        for database_key in databases:
                            if database_key in database_data and GOOGLE_DRIVE_CONFIG[database_key]['enabled']:
                                db_results = search_database(database_key, normalized_cas)
                                results.extend(db_results)
                    
                    all_results.extend(results)
        
        if not all_results:
            return jsonify({'error': 'No results found in uploaded file'}), 404
        
        return jsonify({'results': all_results})
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': 'File upload failed'}), 500

@app.route('/api/database-info')
def database_info():
    """Get information about all databases"""
    try:
        info = {}
        for database_key, config in GOOGLE_DRIVE_CONFIG.items():
            if database_key in database_data:
                data = database_data[database_key]
                info[database_key] = {
                    'name': config['name'],
                    'enabled': config['enabled'],
                    'loaded': True,
                    'record_count': len(data),
                    'columns': list(data.columns),
                    'last_updated': '2025-01-01',  # Mock data for now
                    'file_size': 'N/A'  # Mock data for now
                }
            else:
                info[database_key] = {
                    'name': config['name'],
                    'enabled': config['enabled'],
                    'loaded': False,
                    'record_count': 0,
                    'columns': [],
                    'last_updated': 'N/A',
                    'file_size': 'N/A'
                }
        
        return jsonify(info)
        
    except Exception as e:
        print(f"Database info error: {e}")
        return jsonify({'error': 'Failed to get database information'}), 500

@app.route('/api/debug/<cas_number>')
def debug_search(cas_number):
    """Debug endpoint to see what's happening with a specific CAS number"""
    try:
        normalized_cas = normalize_cas_number(cas_number)
        debug_info = {
            'original_cas': cas_number,
            'normalized_cas': normalized_cas,
            'databases_loaded': list(database_data.keys()),
            'search_results': search_cas_number(normalized_cas)
        }
        
        # Add database-specific debug info
        for database_key, data in database_data.items():
            config = GOOGLE_DRIVE_CONFIG[database_key]
            cas_column = config.get('cas_column', 'CAS No.')
            
            # Check for exact matches
            exact_matches = data[data[cas_column] == cas_number]
            debug_info[f'{database_key}_exact_matches'] = len(exact_matches)
            
            # Check for normalized matches
            normalized_matches = data[data[cas_column].apply(lambda x: normalize_cas_number(x) == normalized_cas)]
            debug_info[f'{database_key}_normalized_matches'] = len(normalized_matches)
            
            # Show sample data
            if not normalized_matches.empty:
                sample = normalized_matches.iloc[0]
                debug_info[f'{database_key}_sample'] = {
                    'cas': str(sample.get(cas_column, 'N/A')),
                    'name': str(sample.get(config.get('name_column', 'Chemical Name'), 'N/A')),
                    'flag': str(sample.get(config.get('flag_column', 'FLAG'), 'N/A')),
                    'activity': str(sample.get(config.get('activity_column', 'ACTIVITY'), 'N/A'))
                }
        
        return jsonify(debug_info)
        
    except Exception as e:
        print(f"Debug error: {e}")
        return jsonify({'error': 'Debug failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False) 