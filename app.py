from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import re
import json
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
        },
        'kecl': {
            'file_id': 'YOUR_KECL_FILE_ID_HERE',
            'file_name': 'KECL.csv',
            'enabled': True
        }
    }
    LOCAL_FILES = {
        'tscainv': 'TSCAINV_012025.csv',
        'pmnacc': 'PMNACC_012025.csv'
    }

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global variables to store the data
pmnacc_data = None
tscainv_data = None
kecl_data = None

# Use configuration from config.py
GOOGLE_DRIVE_FILES = GOOGLE_DRIVE_CONFIG

# Flag definitions for TSCA database
FLAG_DEFINITIONS = {
    '5E': 'Indicates a substance that is the subject of a TSCA section 5(e) order.',
    '5F': 'Indicates a substance that is the subject of a TSCA section 5(f) rule.',
    '12C': 'Indicates a substance that is prohibited to be exported from the United States under TSCA section 12(c).',
    'FRI': 'Indicates a polymeric substance containing no free-radical initiator in its Inventory name but is considered to cover the designated polymer made with any free-radical initiator regardless of the amount used.',
    'PE1': 'Indicates a polymer that has a number-average molecular weight of greater than or equal to 1,000 daltons and less than 10,000 daltons and that is exempt under the 1995 polymer exemption rule. The polymer\'s oligomer content must be less than 10 percent by weight below 500 daltons and less than 25 percent by weight below 1,000 daltons.',
    'PE2': 'Indicates a polymer that has a number-average molecular weight of greater than or equal to 10,000 daltons and that is exempt under the 1995 polymer exemption rule. The polymer\'s oligomer content must be less than 2 percent by weight below 500 daltons and less than 5 percent by weight below 1,000 daltons.',
    'PE3': 'Indicates a polymer that is a polyester and that is exempt under the 1995 polymer exemption rule. The polyester is made only from monomers and reactants included in a specified list that comprises one of the eligibility criteria for the 1995 polymer exemption rule.',
    'PMN': 'Indicates a commenced PMN substance.',
    'R': 'Indicates a substance that is the subject of a proposed or final TSCA section 6 risk management rule.',
    'S': 'Indicates a substance that is identified in a final Significant New Use Rule.',
    'SP': 'Indicates a substance that is identified in a proposed Significant New Use Rule.',
    'T': 'Indicates a substance that is the subject of a final TSCA section 4 test rule or order.',
    'TP': 'Indicates a substance that is the subject of a proposed TSCA section 4 test rule or order.',
    'XU': 'Indicates a substance exempt from reporting under the Chemical Data Reporting Rule, (40 CFR 711).',
    'Y1': 'Indicates a polymer that has a number-average molecular weight greater than 1,000 and that was exempt under the 1984 polymer exemption rule.',
    'Y2': 'Indicates a polymer that is a polyester and that was exempt under the 1984 polymer exemption rule. The polyester is made only from reactants included in a specified list of low-concern reactants that comprises one of the eligibility criteria for the 1984 polymer exemption rule.'
}

def get_flag_description(flag):
    """Get description for a flag or list of flags"""
    if pd.isna(flag) or not flag:
        return "No flag information available"
    
    # Split flags if multiple (e.g., "PMN; S; 5E")
    flags = [f.strip() for f in str(flag).split(';')]
    
    descriptions = []
    for f in flags:
        if f in FLAG_DEFINITIONS:
            descriptions.append(f"{f}: {FLAG_DEFINITIONS[f]}")
        else:
            descriptions.append(f"{f}: Flag description not available")
    
    return "; ".join(descriptions)

def load_data():
    """Load data from Google Drive or local files"""
    global pmnacc_data, tscainv_data, kecl_data
    
    print("Starting data loading process...")
    
    # Load TSCA Inventory data
    if GOOGLE_DRIVE_CONFIG['tscainv']['enabled']:
        print("Loading TSCA Inventory data from Google Drive...")
        try:
            file_id = GOOGLE_DRIVE_CONFIG['tscainv']['file_id']
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=30)
            print(f"TSCA Response Status: {response.status_code}")
            print(f"TSCA Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"TSCA Content Length: {len(response.content)}")
            
            if response.status_code == 200:
                try:
                    # Create a StringIO object from the content
                    from io import StringIO
                    csv_content = StringIO(response.text)
                    tscainv_data = pd.read_csv(csv_content)
                    print(f"TSCA Inventory data loaded successfully. Shape: {tscainv_data.shape}")
                    print(f"TSCA Inventory columns: {list(tscainv_data.columns)}")
                except Exception as csv_error:
                    print(f"CSV parsing error for TSCA: {csv_error}")
                    print(f"First 500 chars of response: {response.text[:500]}")
                    tscainv_data = None
            else:
                print(f"Failed to load TSCA Inventory from Google Drive. Status: {response.status_code}")
                tscainv_data = None
        except Exception as e:
            print(f"Error loading TSCA Inventory from Google Drive: {e}")
            tscainv_data = None
    else:
        print("TSCA Inventory disabled in config")
        tscainv_data = None
    
    # Load PMNACC data
    if GOOGLE_DRIVE_CONFIG['pmnacc']['enabled']:
        print("Loading PMNACC data from Google Drive...")
        try:
            file_id = GOOGLE_DRIVE_CONFIG['pmnacc']['file_id']
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200 and 'csv' in response.headers.get('content-type', '').lower():
                from io import StringIO
                csv_content = StringIO(response.text)
                pmnacc_data = pd.read_csv(csv_content)
                print(f"PMNACC data loaded successfully. Shape: {pmnacc_data.shape}")
                print(f"PMNACC columns: {list(pmnacc_data.columns)}")
            else:
                print(f"Failed to load PMNACC from Google Drive. Status: {response.status_code}")
                pmnacc_data = None
        except Exception as e:
            print(f"Error loading PMNACC from Google Drive: {e}")
            pmnacc_data = None
    else:
        print("PMNACC disabled in config")
        pmnacc_data = None
    
    # Load KECL data
    if GOOGLE_DRIVE_CONFIG['kecl']['enabled']:
        print("Loading KECL data from Google Drive...")
        try:
            file_id = GOOGLE_DRIVE_CONFIG['kecl']['file_id']
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=30)
            print(f"KECL Response Status: {response.status_code}")
            print(f"KECL Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"KECL Content Length: {len(response.content)}")
            
            if response.status_code == 200:
                try:
                    from io import StringIO
                    csv_content = StringIO(response.text)
                    kecl_data = pd.read_csv(csv_content)
                    print(f"KECL data loaded successfully. Shape: {kecl_data.shape}")
                    print(f"KECL columns: {list(kecl_data.columns)}")
                except Exception as csv_error:
                    print(f"CSV parsing error for KECL: {csv_error}")
                    print(f"First 500 chars of response: {response.text[:500]}")
                    kecl_data = None
            else:
                print(f"Failed to load KECL from Google Drive. Status: {response.status_code}")
                kecl_data = None
        except Exception as e:
            print(f"Error loading KECL from Google Drive: {e}")
            kecl_data = None
    else:
        print("KECL disabled in config")
        kecl_data = None
    
    print("Data loading process completed.")
    
    # Return True if at least one database loaded successfully
    return any([tscainv_data is not None, pmnacc_data is not None, kecl_data is not None])

def normalize_cas_number(cas_number):
    """Remove dashes and spaces from CAS number"""
    if pd.isna(cas_number):
        return ""
    return str(cas_number).replace('-', '').replace(' ', '')

def search_cas_number(normalized_cas):
    """Search for a CAS number across all enabled databases"""
    results = []
    
    # Search TSCA Inventory
    if tscainv_data is not None and GOOGLE_DRIVE_CONFIG['tscainv']['enabled']:
        try:
            # Search in both casregno and CASRN columns using normalized comparison
            tsca_match = tscainv_data[
                (tscainv_data['casregno'].apply(lambda x: normalize_cas_number(x) == normalized_cas)) |
                (tscainv_data['CASRN'].apply(lambda x: normalize_cas_number(x) == normalized_cas))
            ]
            
            if not tsca_match.empty:
                for _, row in tsca_match.iterrows():
                    results.append({
                        'database': 'TSCA Inventory',
                        'chemical_name': str(row['ChemName']),
                        'flag': str(row['FLAG']),
                        'activity': str(row['ACTIVITY']),
                        'cas_number': str(row['CASRN'])
                    })
        except Exception as e:
            print(f"Error searching TSCA data: {e}")
    
    # Search PMNACC
    if pmnacc_data is not None and GOOGLE_DRIVE_CONFIG['pmnacc']['enabled']:
        try:
            pmnacc_match = pmnacc_data[
                pmnacc_data['ACCNO'].apply(lambda x: normalize_cas_number(x) == normalized_cas)
            ]
            
            if not pmnacc_match.empty:
                for _, row in pmnacc_match.iterrows():
                    results.append({
                        'database': 'PMNACC',
                        'chemical_name': str(row['GenericName']),
                        'flag': str(row['FLAG']),
                        'activity': str(row['ACTIVITY']),
                        'cas_number': str(row['ACCNO'])
                    })
        except Exception as e:
            print(f"Error searching PMNACC data: {e}")
    
    # Search KECL
    if kecl_data is not None and GOOGLE_DRIVE_CONFIG['kecl']['enabled']:
        try:
            kecl_match = kecl_data[
                kecl_data['CAS No.'].apply(lambda x: normalize_cas_number(x) == normalized_cas)
            ]
            
            if not kecl_match.empty:
                for _, row in kecl_match.iterrows():
                    # Convert YES/NO to ACTIVE/INACTIVE
                    status = 'ACTIVE' if str(row['Value']).upper() == 'YES' else 'INACTIVE'
                    results.append({
                        'database': 'KECL (Korea)',
                        'chemical_name': str(row['Chemical Name']),
                        'flag': 'N/A',  # KECL doesn't have flags like TSCA
                        'activity': status,
                        'cas_number': str(row['CAS No.'])
                    })
            else:
                # Chemical not found in KECL list = INACTIVE
                results.append({
                    'database': 'KECL (Korea)',
                    'chemical_name': 'Not listed in KECL',
                    'flag': 'N/A',
                    'activity': 'INACTIVE',
                    'cas_number': normalized_cas  # Use the normalized CAS number since it wasn't found
                })
        except Exception as e:
            print(f"Error searching KECL data: {e}")
    
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

@app.route('/flag-definitions')
def flag_definitions():
    """Flag definitions page"""
    return render_template('flag_definitions.html', flag_definitions=FLAG_DEFINITIONS)

@app.route('/api/search', methods=['POST'])
def search():
    """API endpoint for searching CAS numbers"""
    try:
        data = request.get_json()
        cas_number = data.get('casNumber', '').strip()
        databases = data.get('databases', ['tscainv'])
        
        if not cas_number:
            return jsonify({'error': 'Please provide a CAS number'}), 400
        
        normalized_cas = normalize_cas_number(cas_number)
        results = search_cas_number(normalized_cas)
        
        # Filter results based on selected databases
        if databases and 'all' not in databases:
            # Map database keys to database names
            db_mapping = {
                'tscainv': 'TSCA Inventory',
                'kecl': 'KECL (Korea)',
                'pmnacc': 'PMNACC'
            }
            results = [r for r in results if any(r['database'] == db_mapping.get(db, db) for db in databases)]
        
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
        databases = request.form.get('databases', '["tscainv"]')
        try:
            databases = json.loads(databases)
        except:
            databases = ['tscainv']
        
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
            results = search_cas_number(cas)
            all_results.extend(results)
        
        # Filter results based on selected databases
        if databases and 'all' not in databases:
            # Map database keys to database names
            db_mapping = {
                'tscainv': 'TSCA Inventory',
                'kecl': 'KECL (Korea)',
                'pmnacc': 'PMNACC'
            }
            all_results = [r for r in all_results if any(r['database'] == db_mapping.get(db, db) for db in databases)]
        
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
        for key, db_info in GOOGLE_DRIVE_CONFIG.items():
            if db_info.get('enabled', True):
                # Mock file info for now
                file_info = {
                    'success': True,
                    'size': 9182919 if key == 'tscainv' else 2200000 if key == 'kecl' else 0,
                    'last_modified': '2025-01-23 18:30:00'
                }
                
                info[key] = {
                    'name': db_info.get('name', key.upper()),
                    'last_updated': '2025-01-23 18:30:00',
                    'file_info': file_info,
                    'local_loaded': {
                        'tscainv': tscainv_data is not None,
                        'pmnacc': pmnacc_data is not None,
                        'kecl': kecl_data is not None
                    }[key] if key in ['tscainv', 'pmnacc', 'kecl'] else False
                }
        
        return jsonify(info)
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    global pmnacc_data, tscainv_data, kecl_data
    
    status = {
        'status': 'healthy',
        'data_loaded': {
            'tscainv': tscainv_data is not None,
            'pmnacc': pmnacc_data is not None,
            'kecl': kecl_data is not None
        },
        'record_counts': {
            'tscainv': len(tscainv_data) if tscainv_data is not None else 0,
            'pmnacc': len(pmnacc_data) if pmnacc_data is not None else 0,
            'kecl': len(kecl_data) if kecl_data is not None else 0
        },
        'total_records': (len(tscainv_data) if tscainv_data is not None else 0) + 
                        (len(pmnacc_data) if pmnacc_data is not None else 0) +
                        (len(kecl_data) if kecl_data is not None else 0)
    }
    
    return jsonify(status)

@app.route('/api/debug/<cas_number>')
def debug_search(cas_number):
    """Debug endpoint to test CAS number search"""
    try:
        normalized_cas = normalize_cas_number(cas_number)
        
        debug_info = {
            'original_cas': cas_number,
            'normalized_cas': normalized_cas,
            'data_loaded': {
                'tscainv': tscainv_data is not None,
                'pmnacc': pmnacc_data is not None,
                'kecl': kecl_data is not None
            }
        }
        
        if tscainv_data is not None:
            debug_info['tscainv_info'] = {
                'total_records': len(tscainv_data),
                'sample_casregno': tscainv_data['casregno'].head(10).tolist(),
                'sample_casrn': tscainv_data['CASRN'].head(10).tolist(),
                'columns': list(tscainv_data.columns)
            }
            
            # Check for exact matches
            exact_matches = tscainv_data[
                (tscainv_data['casregno'] == normalized_cas) |
                (tscainv_data['CASRN'] == normalized_cas)
            ]
            debug_info['tscainv_exact_matches'] = len(exact_matches)
            
            # Check for normalized matches
            normalized_matches = tscainv_data[
                (tscainv_data['casregno'].apply(lambda x: normalize_cas_number(x) == normalized_cas)) |
                (tscainv_data['CASRN'].apply(lambda x: normalize_cas_number(x) == normalized_cas))
            ]
            debug_info['tscainv_normalized_matches'] = len(normalized_matches)
        
        if pmnacc_data is not None:
            debug_info['pmnacc_info'] = {
                'total_records': len(pmnacc_data),
                'sample_accno': pmnacc_data['ACCNO'].head(10).tolist(),
                'columns': list(pmnacc_data.columns)
            }
            
            # Check for exact matches
            exact_matches = pmnacc_data[pmnacc_data['ACCNO'] == normalized_cas]
            debug_info['pmnacc_exact_matches'] = len(exact_matches)
            
            # Check for normalized matches
            normalized_matches = pmnacc_data[
                pmnacc_data['ACCNO'].apply(lambda x: normalize_cas_number(x) == normalized_cas)
            ]
            debug_info['pmnacc_normalized_matches'] = len(normalized_matches)
        
        if kecl_data is not None:
            debug_info['kecl_info'] = {
                'total_records': len(kecl_data),
                'sample_cas_no': kecl_data['CAS No.'].head(10).tolist(),
                'columns': list(kecl_data.columns)
            }
            
            # Check for exact matches
            exact_matches = kecl_data[kecl_data['CAS No.'] == normalized_cas]
            debug_info['kecl_exact_matches'] = len(exact_matches)
            
            # Check for normalized matches
            normalized_matches = kecl_data[
                kecl_data['CAS No.'].apply(lambda x: normalize_cas_number(x) == normalized_cas)
            ]
            debug_info['kecl_normalized_matches'] = len(normalized_matches)
        
        return jsonify(debug_info)
    
    except Exception as e:
        return jsonify({'error': f'Debug error: {str(e)}'}), 500

@app.route('/api/test-data')
def test_data():
    """Test endpoint to check data loading"""
    import os
    
    result = {
        'tscainv_loaded': tscainv_data is not None,
        'pmnacc_loaded': pmnacc_data is not None,
        'kecl_loaded': kecl_data is not None,
        'tscainv_count': int(len(tscainv_data)) if tscainv_data is not None else 0,
        'pmnacc_count': int(len(pmnacc_data)) if pmnacc_data is not None else 0,
        'kecl_count': int(len(kecl_data)) if kecl_data is not None else 0,
        'google_drive_config': {
            'tscainv_file_id': GOOGLE_DRIVE_FILES.get('tscainv', {}).get('file_id'),
            'tscainv_enabled': GOOGLE_DRIVE_FILES.get('tscainv', {}).get('enabled'),
            'pmnacc_file_id': GOOGLE_DRIVE_FILES.get('pmnacc', {}).get('file_id'),
            'pmnacc_enabled': GOOGLE_DRIVE_FILES.get('pmnacc', {}).get('enabled'),
            'kecl_file_id': GOOGLE_DRIVE_FILES.get('kecl', {}).get('file_id'),
            'kecl_enabled': GOOGLE_DRIVE_FILES.get('kecl', {}).get('enabled')
        },
        'file_system': {
            'current_directory': os.getcwd(),
            'files_in_directory': os.listdir('.'),
            'tscainv_exists': os.path.exists('TSCAINV_012025.csv'),
            'pmnacc_exists': os.path.exists('PMNACC_012025.csv'),
            'kecl_exists': os.path.exists('KECL_012025.csv')
        }
    }
    
    if tscainv_data is not None:
        result['tscainv_sample'] = {
            'columns': list(tscainv_data.columns),
            'first_5_casregno': [str(x) for x in tscainv_data['casregno'].head(5).tolist()],
            'first_5_CASRN': [str(x) for x in tscainv_data['CASRN'].head(5).tolist()],
            'casregno_dtype': str(tscainv_data['casregno'].dtype),
            'CASRN_dtype': str(tscainv_data['CASRN'].dtype)
        }
        
        # Check if 110203 exists
        cas_110203 = tscainv_data[tscainv_data['casregno'] == 110203]
        result['cas_110203_exists'] = len(cas_110203) > 0
        if len(cas_110203) > 0:
            result['cas_110203_data'] = {
                'casregno': str(cas_110203.iloc[0]['casregno']) if pd.notna(cas_110203.iloc[0]['casregno']) else '',
                'CASRN': str(cas_110203.iloc[0]['CASRN']) if pd.notna(cas_110203.iloc[0]['CASRN']) else '',
                'ChemName': str(cas_110203.iloc[0]['ChemName']) if pd.notna(cas_110203.iloc[0]['ChemName']) else '',
                'ACTIVITY': str(cas_110203.iloc[0]['ACTIVITY']) if pd.notna(cas_110203.iloc[0]['ACTIVITY']) else ''
            }
    
    if pmnacc_data is not None:
        result['pmnacc_sample'] = {
            'columns': list(pmnacc_data.columns),
            'first_5_accno': [str(x) for x in pmnacc_data['ACCNO'].head(5).tolist()],
            'first_5_GenericName': [str(x) for x in pmnacc_data['GenericName'].head(5).tolist()],
            'ACCNO_dtype': str(pmnacc_data['ACCNO'].dtype),
            'GenericName_dtype': str(pmnacc_data['GenericName'].dtype)
        }
        
        # Check if 110203 exists
        pmnacc_110203 = pmnacc_data[pmnacc_data['ACCNO'] == 110203]
        result['pmnacc_110203_exists'] = len(pmnacc_110203) > 0
        if len(pmnacc_110203) > 0:
            result['pmnacc_110203_data'] = {
                'ACCNO': str(pmnacc_110203.iloc[0]['ACCNO']) if pd.notna(pmnacc_110203.iloc[0]['ACCNO']) else '',
                'GenericName': str(pmnacc_110203.iloc[0]['GenericName']) if pd.notna(pmnacc_110203.iloc[0]['GenericName']) else '',
                'FLAG': str(pmnacc_110203.iloc[0]['FLAG']) if pd.notna(pmnacc_110203.iloc[0]['FLAG']) else '',
                'ACTIVITY': str(pmnacc_110203.iloc[0]['ACTIVITY']) if pd.notna(pmnacc_110203.iloc[0]['ACTIVITY']) else ''
            }
    
    if kecl_data is not None:
        result['kecl_sample'] = {
            'columns': list(kecl_data.columns),
            'first_5_cas_no': [str(x) for x in kecl_data['CAS No.'].head(5).tolist()],
            'first_5_Chemical_Name': [str(x) for x in kecl_data['Chemical Name'].head(5).tolist()],
            'CAS_No_dtype': str(kecl_data['CAS No.'].dtype),
            'Chemical_Name_dtype': str(kecl_data['Chemical Name'].dtype)
        }
        
        # Check if 110203 exists
        kecl_110203 = kecl_data[kecl_data['CAS No.'] == 110203]
        result['kecl_110203_exists'] = len(kecl_110203) > 0
        if len(kecl_110203) > 0:
            result['kecl_110203_data'] = {
                'CAS_No': str(kecl_110203.iloc[0]['CAS No.']) if pd.notna(kecl_110203.iloc[0]['CAS No.']) else '',
                'Chemical_Name': str(kecl_110203.iloc[0]['Chemical Name']) if pd.notna(kecl_110203.iloc[0]['Chemical Name']) else '',
                'Value': str(kecl_110203.iloc[0]['Value']) if pd.notna(kecl_110203.iloc[0]['Value']) else '',
                'ACTIVITY': str(kecl_110203.iloc[0]['ACTIVITY']) if pd.notna(kecl_110203.iloc[0]['ACTIVITY']) else ''
            }
    
    return jsonify(result)

@app.route('/api/test-google-drive')
def test_google_drive():
    """Test Google Drive file access directly"""
    try:
        tscainv_file_id = GOOGLE_DRIVE_FILES.get('tscainv', {}).get('file_id')
        if not tscainv_file_id or tscainv_file_id == 'YOUR_TSCAINV_FILE_ID_HERE':
            return jsonify({'error': 'No valid file ID configured'})
        
        url = f"https://drive.google.com/uc?export=download&id={tscainv_file_id}"
        
        response = requests.get(url, timeout=30)
        
        result = {
            'file_id': tscainv_file_id,
            'url': url,
            'status_code': response.status_code,
            'content_length': len(response.content),
            'content_type': response.headers.get('content-type', 'unknown'),
            'first_200_chars': response.text[:200] if response.text else 'No content'
        }
        
        # Check if it looks like CSV data
        if response.status_code == 200:
            content = response.text
            if content.startswith('ID,CASRN,casregno') or ('ID' in content and 'CASRN' in content):
                result['is_csv'] = True
                result['csv_columns'] = content.split('\n')[0].split(',') if '\n' in content else []
            else:
                result['is_csv'] = False
        else:
            result['is_csv'] = False
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/test-cas/<cas_number>')
def test_cas_number(cas_number):
    """Test if a specific CAS number exists in the loaded data"""
    try:
        result = {
            'cas_number': cas_number,
            'normalized_cas': normalize_cas_number(cas_number),
            'tscainv_loaded': tscainv_data is not None,
            'pmnacc_loaded': pmnacc_data is not None,
            'kecl_loaded': kecl_data is not None
        }
        
        if tscainv_data is not None:
            # Convert to string and handle NaN
            tscainv_data['casregno_str'] = tscainv_data['casregno'].fillna('').astype(str)
            tscainv_data['CASRN_str'] = tscainv_data['CASRN'].fillna('').astype(str)
            
            normalized_cas = normalize_cas_number(cas_number)
            
            # Check exact matches
            exact_casregno = tscainv_data[tscainv_data['casregno_str'] == normalized_cas]
            exact_CASRN = tscainv_data[tscainv_data['CASRN_str'] == normalized_cas]
            
            result['tscainv'] = {
                'total_records': int(len(tscainv_data)),  # Convert to native Python int
                'exact_casregno_matches': int(len(exact_casregno)),
                'exact_CASRN_matches': int(len(exact_CASRN)),
                'sample_casregno': tscainv_data['casregno_str'].head(5).tolist(),
                'sample_CASRN': tscainv_data['CASRN_str'].head(5).tolist()
            }
            
            if len(exact_casregno) > 0:
                result['tscainv']['found_data'] = {
                    'casregno': str(exact_casregno.iloc[0]['casregno']) if pd.notna(exact_casregno.iloc[0]['casregno']) else '',
                    'CASRN': str(exact_casregno.iloc[0]['CASRN']) if pd.notna(exact_casregno.iloc[0]['CASRN']) else '',
                    'ChemName': str(exact_casregno.iloc[0]['ChemName']) if pd.notna(exact_casregno.iloc[0]['ChemName']) else '',
                    'ACTIVITY': str(exact_casregno.iloc[0]['ACTIVITY']) if pd.notna(exact_casregno.iloc[0]['ACTIVITY']) else ''
                }
        
        if pmnacc_data is not None:
            # Convert to string and handle NaN
            pmnacc_data['ACCNO_str'] = pmnacc_data['ACCNO'].fillna('').astype(str)
            
            normalized_cas = normalize_cas_number(cas_number)
            
            # Check exact matches
            exact_ACCNO = pmnacc_data[pmnacc_data['ACCNO_str'] == normalized_cas]
            
            result['pmnacc'] = {
                'total_records': int(len(pmnacc_data)),  # Convert to native Python int
                'exact_ACCNO_matches': int(len(exact_ACCNO)),
                'sample_ACCNO': pmnacc_data['ACCNO_str'].head(5).tolist()
            }
            
            if len(exact_ACCNO) > 0:
                result['pmnacc']['found_data'] = {
                    'ACCNO': str(exact_ACCNO.iloc[0]['ACCNO']) if pd.notna(exact_ACCNO.iloc[0]['ACCNO']) else '',
                    'GenericName': str(exact_ACCNO.iloc[0]['GenericName']) if pd.notna(exact_ACCNO.iloc[0]['GenericName']) else '',
                    'FLAG': str(exact_ACCNO.iloc[0]['FLAG']) if pd.notna(exact_ACCNO.iloc[0]['FLAG']) else '',
                    'ACTIVITY': str(exact_ACCNO.iloc[0]['ACTIVITY']) if pd.notna(exact_ACCNO.iloc[0]['ACTIVITY']) else ''
                }
        
        if kecl_data is not None:
            # Convert to string and handle NaN
            kecl_data['CAS_No_str'] = kecl_data['CAS No.'].fillna('').astype(str)
            
            normalized_cas = normalize_cas_number(cas_number)
            
            # Check exact matches
            exact_CAS_No = kecl_data[kecl_data['CAS_No_str'] == normalized_cas]
            
            result['kecl'] = {
                'total_records': int(len(kecl_data)),  # Convert to native Python int
                'exact_CAS_No_matches': int(len(exact_CAS_No)),
                'sample_CAS_No': kecl_data['CAS_No_str'].head(5).tolist()
            }
            
            if len(exact_CAS_No) > 0:
                result['kecl']['found_data'] = {
                    'CAS_No': str(exact_CAS_No.iloc[0]['CAS No.']) if pd.notna(exact_CAS_No.iloc[0]['CAS No.']) else '',
                    'Chemical_Name': str(exact_CAS_No.iloc[0]['Chemical Name']) if pd.notna(exact_CAS_No.iloc[0]['Chemical Name']) else '',
                    'Value': str(exact_CAS_No.iloc[0]['Value']) if pd.notna(exact_CAS_No.iloc[0]['Value']) else '',
                    'ACTIVITY': str(exact_CAS_No.iloc[0]['ACTIVITY']) if pd.notna(exact_CAS_No.iloc[0]['ACTIVITY']) else ''
                }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})

# Load data on startup (for both development and production)
print("Starting application and loading data...")
if load_data():
    print("✓ Data loaded successfully")
else:
    print("✗ Failed to load data - application may not work properly")

if __name__ == '__main__':
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 