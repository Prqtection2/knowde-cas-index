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
    """Load CSV data files from Google Drive"""
    global pmnacc_data, tscainv_data
    
    try:
        print("Starting data load from Google Drive...")
        
        # Load TSCAINV from Google Drive
        tscainv_file_id = GOOGLE_DRIVE_FILES.get('tscainv', {}).get('file_id')
        if tscainv_file_id and tscainv_file_id != 'YOUR_TSCAINV_FILE_ID_HERE':
            print(f"Loading TSCAINV from Google Drive: {tscainv_file_id}")
            
            # Use direct file access URL - this bypasses Google Drive's download restrictions
            tscainv_url = f"https://drive.google.com/file/d/{tscainv_file_id}/view?usp=sharing"
            
            try:
                print(f"Fetching from: {tscainv_url}")
                
                # First, get the file info to check if it's accessible
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # Try the direct download URL
                download_url = f"https://drive.google.com/uc?export=download&id={tscainv_file_id}"
                response = requests.get(download_url, headers=headers, timeout=120)
                
                print(f"Response status: {response.status_code}")
                print(f"Content length: {len(response.content)}")
                
                if response.status_code == 200 and len(response.content) > 1000:
                    # Check if we got actual CSV data
                    content = response.text
                    if 'ID,CASRN,casregno' in content or content.startswith('ID,'):
                        tscainv_data = pd.read_csv(io.StringIO(content))
                        print(f"✓ Loaded TSCAINV from Google Drive: {len(tscainv_data)} records")
                    else:
                        print(f"✗ Response doesn't contain expected CSV headers. First 500 chars: {content[:500]}")
                        raise Exception("Invalid CSV format")
                else:
                    print(f"✗ Failed to get valid response. Status: {response.status_code}, Length: {len(response.content)}")
                    raise Exception(f"HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Failed to load from Google Drive: {e}")
                raise e
        else:
            print("No valid TSCAINV Google Drive file ID configured")
            tscainv_data = None
        
        # Load PMNACC data (disabled for now)
        pmnacc_data = None
        
        # Check if at least one database loaded
        if tscainv_data is None:
            print("✗ No databases loaded successfully")
            return False
        
        print("✓ Data loading completed")
        return True
        
    except Exception as e:
        print(f"✗ Critical error loading data: {e}")
        return False

def normalize_cas_number(cas_number):
    """Remove dashes and spaces from CAS number"""
    if pd.isna(cas_number):
        return ""
    return str(cas_number).replace('-', '').replace(' ', '')

def search_cas_number(normalized_cas):
    """Search for CAS number in specified database(s)"""
    results = []
    
    print(f"Searching for normalized CAS: '{normalized_cas}'")
    print(f"TSCAINV data loaded: {tscainv_data is not None}")
    if tscainv_data is not None:
        print(f"TSCAINV data shape: {tscainv_data.shape}")
        print(f"TSCAINV columns: {list(tscainv_data.columns)}")
    
    # Search in PMNACC data
    if pmnacc_data is not None:
        print(f"PMNACC data available: {len(pmnacc_data)} records")
        # Check a few sample CAS numbers for debugging
        sample_cas = pmnacc_data['ACCNO'].head(5).tolist()
        print(f"Sample PMNACC CAS numbers: {sample_cas}")
        
        pmnacc_match = pmnacc_data[
            pmnacc_data['ACCNO'].apply(lambda x: normalize_cas_number(x) == normalized_cas)
        ]
        
        print(f"PMNACC matches found: {len(pmnacc_match)}")
        
        if not pmnacc_match.empty:
            for _, row in pmnacc_match.iterrows():
                results.append({
                    'source': 'PMNACC',
                    'casNumber': str(row['ACCNO']) if pd.notna(row['ACCNO']) else '',
                    'chemicalName': str(row['GenericName']) if pd.notna(row['GenericName']) else '',
                    'flag': str(row['FLAG']) if pd.notna(row['FLAG']) else '',
                    'flagDescription': get_flag_description(row['FLAG']),
                    'activity': str(row['ACTIVITY']) if pd.notna(row['ACTIVITY']) else ''
                })
    
    # Search in TSCAINV data
    if tscainv_data is not None:
        print(f"TSCAINV data available: {len(tscainv_data)} records")
        
        # Convert casregno to string for comparison and handle NaN values
        tscainv_data['casregno_str'] = tscainv_data['casregno'].fillna('').astype(str)
        tscainv_data['CASRN_str'] = tscainv_data['CASRN'].fillna('').astype(str)
        
        # Check if the exact CAS number exists in the data
        exact_match_casregno = tscainv_data[tscainv_data['casregno_str'] == normalized_cas]
        exact_match_CASRN = tscainv_data[tscainv_data['CASRN_str'] == normalized_cas]
        
        print(f"Exact matches in casregno: {len(exact_match_casregno)}")
        print(f"Exact matches in CASRN: {len(exact_match_CASRN)}")
        
        # Check a few sample CAS numbers for debugging
        sample_cas = tscainv_data['casregno_str'].head(10).tolist()
        print(f"Sample TSCAINV casregno: {sample_cas}")
        sample_casrn = tscainv_data['CASRN_str'].head(10).tolist()
        print(f"Sample TSCAINV CASRN: {sample_casrn}")
        
        # Try normalized search
        tscainv_match = tscainv_data[
            (tscainv_data['casregno_str'].apply(lambda x: normalize_cas_number(x) == normalized_cas)) |
            (tscainv_data['CASRN_str'].apply(lambda x: normalize_cas_number(x) == normalized_cas))
        ]
        
        print(f"TSCAINV normalized matches found: {len(tscainv_match)}")
        
        if not tscainv_match.empty:
            for _, row in tscainv_match.iterrows():
                results.append({
                    'source': 'TSCAINV',
                    'casNumber': str(row['CASRN']) if pd.notna(row['CASRN']) else str(row['casregno']) if pd.notna(row['casregno']) else '',
                    'chemicalName': str(row['ChemName']) if pd.notna(row['ChemName']) else '',
                    'flag': str(row['FLAG']) if pd.notna(row['FLAG']) else '',
                    'flagDescription': get_flag_description(row['FLAG']),
                    'activity': str(row['ACTIVITY']) if pd.notna(row['ACTIVITY']) else ''
                })
    else:
        print("TSCAINV data is None - not loaded properly")
    
    print(f"Total results found: {len(results)}")
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
        database = data.get('database', 'all')
        
        if not cas_number:
            return jsonify({'error': 'Please provide a CAS number'}), 400
        
        normalized_cas = normalize_cas_number(cas_number)
        results = search_cas_number(normalized_cas)
        
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
            results = search_cas_number(cas)
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
                'pmnacc': pmnacc_data is not None
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
        'tscainv_count': int(len(tscainv_data)) if tscainv_data is not None else 0,
        'pmnacc_count': int(len(pmnacc_data)) if pmnacc_data is not None else 0,
        'google_drive_config': {
            'tscainv_file_id': GOOGLE_DRIVE_FILES.get('tscainv', {}).get('file_id'),
            'tscainv_enabled': GOOGLE_DRIVE_FILES.get('tscainv', {}).get('enabled'),
            'pmnacc_file_id': GOOGLE_DRIVE_FILES.get('pmnacc', {}).get('file_id'),
            'pmnacc_enabled': GOOGLE_DRIVE_FILES.get('pmnacc', {}).get('enabled')
        },
        'file_system': {
            'current_directory': os.getcwd(),
            'files_in_directory': os.listdir('.'),
            'tscainv_exists': os.path.exists('TSCAINV_012025.csv'),
            'pmnacc_exists': os.path.exists('PMNACC_012025.csv')
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
            'pmnacc_loaded': pmnacc_data is not None
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