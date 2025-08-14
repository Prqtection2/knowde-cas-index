# 🚀 Adding New Databases - Super Easy!

## ✨ **To Add a New Database (3 Steps):**

### 1. **Upload CSV to Google Drive**

- Upload your CSV file to Google Drive
- Get the file ID from the sharing link
- Make sure it's publicly accessible

### 2. **Add One Entry to `config.py`**

```python
'new_database': {
    'file_id': 'YOUR_FILE_ID_HERE',
    'file_name': 'DATABASE_NAME.csv',
    'name': 'Human Readable Name',
    'enabled': True,
    'cas_column': 'CAS_COLUMN_NAME',
    'name_column': 'CHEMICAL_NAME_COLUMN',
    'flag_column': 'FLAG_COLUMN_NAME',  # or None if no flags
    'activity_column': 'ACTIVITY_COLUMN_NAME',
    'database_type': 'standard',  # or custom type for special logic
    'description': 'Brief description of the database'
}
```

### 3. **Optionally Add Flag Definitions**

```python
FLAG_DEFINITIONS = {
    'new_database': {
        'FLAG1': 'Description of what FLAG1 means',
        'FLAG2': 'Description of what FLAG2 means',
        # ... more flags
    }
}
```

## 🎯 **That's It!**

- **Frontend automatically updates** - shows new database checkbox
- **Search automatically works** - finds chemicals in new database
- **Upload automatically works** - processes new database
- **Update panel automatically shows** - new database status

## 📊 **Example: Adding EU Database**

```python
'eu_reach': {
    'file_id': '1ABC123DEF456GHI789',
    'file_name': 'EU_REACH_2025.csv',
    'name': 'EU REACH Database',
    'enabled': True,
    'cas_column': 'CAS_Number',
    'name_column': 'Chemical_Name',
    'flag_column': 'Regulatory_Status',
    'activity_column': 'Authorization_Status',
    'database_type': 'eu_reach',
    'description': 'European Union REACH Regulation Database'
}
```

## 🔧 **Special Logic (Optional)**

If your database needs special handling (like KECL's YES/NO → ACTIVE/INACTIVE), just add a condition in the `search_database` function:

```python
elif database_key == 'eu_reach':
    # EU REACH specific logic
    if result['activity'] == 'AUTHORIZED':
        result['activity'] = 'ACTIVE'
    elif result['activity'] == 'RESTRICTED':
        result['activity'] = 'RESTRICTED'
```

## 📈 **Scale to 50+ Databases**

- **No code changes needed** for standard databases
- **Automatic UI generation** for all databases
- **Efficient memory usage** - only loads enabled databases
- **Easy maintenance** - all config in one place

## 🚨 **Important Notes**

- **File IDs must be unique** for each database
- **CSV format should be consistent** (CAS numbers, chemical names, etc.)
- **Column names must match** what you specify in config
- **Test with small files first** before uploading large databases
