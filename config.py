# Configuration file for Chemical CAS Search Application
# Update these values when you need to change file locations

# Google Drive Configuration
# IMPORTANT: Use Google Drive API "Replace" method to keep same file ID
GOOGLE_DRIVE_CONFIG = {
    'tscainv': {
        'file_id': '1Yw-PTNevU8HOjM7XMsehgqVGtgvJLCwG',  # Replace with actual file ID
        'file_name': 'TSCAINV_012025.csv',
        'name': 'TSCA Inventory Database',
        'enabled': True
    },
    'pmnacc': {
        'file_id': 'YOUR_PMNACC_FILE_ID_HERE',  # Replace with actual file ID
        'file_name': 'PMNACC_012025.csv',
        'name': 'PMNACC Database',
        'enabled': False
    }
}

# How to get Google Drive File ID:
# 1. Upload your CSV file to Google Drive
# 2. Right-click the file → "Get shareable link"
# 3. Copy the file ID from the URL:
#    https://drive.google.com/file/d/FILE_ID_HERE/view?usp=sharing
#    The FILE_ID_HERE part is what you need

# IMPORTANT: File Update Strategy
# When updating files, use Google Drive API "Replace" method:
# - Keeps the same file ID (no config changes needed)
# - Updates file content
# - Maintains same sharing links
# - No need to update file names or IDs

# Local file paths (fallback)
LOCAL_FILES = {
    'tscainv': 'TSCAINV_012025.csv',
    'pmnacc': 'PMNACC_012025.csv'
} 