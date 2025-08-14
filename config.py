# Configuration file for Chemical CAS Search Application
# Update these values when you need to change file locations

# Google Drive Configuration for Chemical Databases
# To add a new database, just add a new entry with the required fields

GOOGLE_DRIVE_CONFIG = {
    'tscainv': {
        'file_id': '1Yw-PTNevU8HOjM7XMsehgqVGtgvJLCwG',  # Original working file ID
        'file_name': 'TSCAINV_012025.csv',
        'name': 'TSCA Inventory Database',
        'enabled': True,
        # Column mappings - tells the system which columns to use
        'cas_column': 'casregno',  # Primary CAS number column (without dashes)
        'name_column': 'ChemName',  # Chemical name column
        'flag_column': 'FLAG',      # Flag column
        'activity_column': 'ACTIVITY',  # Activity status column
        # Database-specific logic
        'database_type': 'tsca',  # For special handling
        'description': 'Toxic Substances Control Act Inventory'
    },
    
    'pmnacc': {
        'file_id': 'YOUR_PMNACC_FILE_ID_HERE',  # Replace with actual file ID
        'file_name': 'PMNACC_012025.csv',
        'name': 'PMNACC Database',
        'enabled': False,  # Currently disabled
        'cas_column': 'ACCNO',
        'name_column': 'GenericName',
        'flag_column': 'FLAG',
        'activity_column': 'ACTIVITY',
        'database_type': 'standard',
        'description': 'Premanufacture Notification Access'
    },
    
    'kecl': {
        'file_id': '18q22nCPMf2TsDDOOhHXLFLVxJ146fSYg',
        'file_name': 'KECL.csv',
        'name': 'KECL Database',
        'enabled': True,
        'cas_column': 'CAS No.',
        'name_column': 'Chemical Name',
        'flag_column': None,  # KECL doesn't have flags
        'activity_column': 'Value',  # Uses Value column (YES/NO)
        'database_type': 'kecl',  # For special KECL logic
        'description': 'Korea Existing Chemical List'
    },
    
    'piccs': {
        'file_id': '1Gr3Ez0s0P1auQWv6JvVkTBMFpgZ6zFg-',  # Replace with actual Google Drive file ID
        'file_name': 'PICCS_2017.csv',
        'name': 'PICCS 2017 Database',
        'enabled': True,
        'cas_column': 'CAS Number',
        'name_column': 'Chemical Name',
        'flag_column': None,  # PICCS doesn't have flags
        'activity_column': 'Value',  # Uses Value column (YES/NO)
        'database_type': 'piccs',  # For special PICCS logic
        'description': 'Philippines Inventory of Chemicals and Chemical Substances 2017'
    },
    
    'picannex': {
        'file_id': 'YOUR_PICANNEX_FILE_ID_HERE',  # Replace with actual Google Drive file ID
        'file_name': 'PICANNEX.csv',
        'name': 'PICANNEX Database',
        'enabled': True,
        'cas_column': 'CAS no.',
        'name_column': 'Substance name',
        'flag_column': 'Review Programme flag,New active substance flag,Annex I substance flag',  # Multiple flag columns
        'activity_column': 'Approval status',  # Primary status column
        'fallback_activity_column': 'Assessment status',  # Fallback status column
        'database_type': 'picannex',  # For special PICANNEX logic
        'description': 'EU Biocidal Products Regulation - PICANNEX Database'
    }
    
    # To add a new database, just copy this template and fill in the details:
    # 'new_database': {
    #     'file_id': 'YOUR_FILE_ID_HERE',
    #     'file_name': 'DATABASE_NAME.csv',
    #     'name': 'Human Readable Name',
    #     'enabled': True,
    #     'cas_column': 'CAS_COLUMN_NAME',
    #     'name_column': 'CHEMICAL_NAME_COLUMN',
    #     'flag_column': 'FLAG_COLUMN_NAME',  # or None if no flags
    #     'activity_column': 'ACTIVITY_COLUMN_NAME',
    #     'database_type': 'standard',  # or custom type for special logic
    #     'description': 'Brief description of the database'
    # }
}

# Flag definitions for databases that have flags
FLAG_DEFINITIONS = {
    'tscainv': {  # TSCA-specific flags
        '5E': 'Indicates a substance that is the subject of a TSCA section 5(e) order.',
        '5F': 'Indicates a substance that is the subject of a TSCA section 5(f) rule.',
        '12C': 'Indicates a substance that is prohibited to be exported from the United States under TSCA section 12(c).',
        'FRI': 'Indicates a polymeric substance containing no free-radical initiator in its Inventory name but is considered to cover the designated polymer made with any free-radical initiator regardless of the amount used.',
        'PE1': 'Indicates a polymer that has a number-average molecular weight of greater than or equal to 1,000 daltons and less than 10,000 daltons and that is exempt under the 1995 polymer exemption rule.',
        'PE2': 'Indicates a polymer that has a number-average molecular weight of greater than or equal to 10,000 daltons and that is exempt under the 1995 polymer exemption rule.',
        'PE3': 'Indicates a polymer that is a polyester and that is exempt under the 1995 polymer exemption rule.',
        'PMN': 'Indicates a commenced PMN substance.',
        'R': 'Indicates a substance that is the subject of a proposed or final TSCA section 6 risk management rule.',
        'S': 'Indicates a substance that is identified in a final Significant New Use Rule.',
        'SP': 'Indicates a substance that is identified in a proposed Significant New Use Rule.',
        'T': 'Indicates a substance that is the subject of a final TSCA section 4 test rule or order.',
        'TP': 'Indicates a substance that is the subject of a proposed TSCA section 4 test rule or order.',
        'XU': 'Indicates a substance exempt from reporting under the Chemical Data Reporting Rule.',
        'Y1': 'Indicates a polymer that has a number-average molecular weight greater than 1,000 and that was exempt under the 1984 polymer exemption rule.',
        'Y2': 'Indicates a polymer that is a polyester and that was exempt under the 1984 polymer exemption rule.'
    }
    # Add flag definitions for other databases here as needed
}

# Database categories for organization
DATABASE_CATEGORIES = {
    'US': ['tscainv', 'pmnacc'],
    'Asia': ['kecl', 'piccs'],
    'Europe': ['picannex'],  # PICANNEX is EU database
    'Global': []   # Future databases
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
    'pmnacc': 'PMNACC_012025.csv',
    'piccs': 'PICCS_2017.csv',
    'picannex': 'PICANNEX.csv'
} 