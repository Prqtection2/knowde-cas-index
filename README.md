# Chemical CAS Number Search Application

A Flask web application for searching chemical information by CAS numbers. The application searches through two datasets:

- PMNACC (Premanufacture Notification Access)
- TSCAINV (TSCA Inventory)

## Features

- **Single CAS Number Search**: Enter a CAS number with or without dashes
- **Bulk File Upload**: Upload CSV or text files containing multiple CAS numbers
- **Modern UI**: Beautiful, responsive interface with Bootstrap 5
- **Real-time Search**: Fast search through large chemical databases
- **Country Selection**: Ready for multi-country support (currently US only)

## Local Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone or download the project files**

   ```bash
   # Make sure you have the following files in your project directory:
   # - app.py
   # - requirements.txt
   # - templates/index.html
   # - PMNACC_012025.csv
   # - TSCAINV_012025.csv
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**

   ```bash
   python app.py
   ```

4. **Access the application**
   - Open your browser and go to `http://localhost:5000`

## Deployment Options

### Option 1: Render (Recommended - Free Tier)

1. **Create a Render account**

   - Go to [render.com](https://render.com) and sign up

2. **Create a new Web Service**

   - Click "New +" → "Web Service"
   - Connect your GitHub repository or use "Deploy from existing repository"

3. **Configure the service**

   - **Name**: `chemical-cas-search` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

4. **Add environment variables** (if needed)

   - No environment variables required for basic functionality

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy your application

### Option 2: Railway

1. **Create a Railway account**

   - Go to [railway.app](https://railway.app) and sign up

2. **Deploy from GitHub**

   - Connect your GitHub repository
   - Railway will automatically detect it's a Python application

3. **Configure**
   - Railway will automatically install dependencies from `requirements.txt`
   - The `Procfile` will be used for the start command

### Option 3: Heroku

1. **Create a Heroku account**

   - Go to [heroku.com](https://heroku.com) and sign up

2. **Install Heroku CLI**

   ```bash
   # Download and install from https://devcenter.heroku.com/articles/heroku-cli
   ```

3. **Deploy**
   ```bash
   heroku create your-app-name
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

### Option 4: PythonAnywhere

1. **Create a PythonAnywhere account**

   - Go to [pythonanywhere.com](https://pythonanywhere.com) and sign up

2. **Upload files**

   - Upload all project files to your PythonAnywhere account

3. **Install dependencies**

   ```bash
   pip install --user -r requirements.txt
   ```

4. **Configure WSGI file**
   - Edit the WSGI configuration file to point to your Flask app

## File Structure

```
cas-db-project/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Deployment configuration
├── runtime.txt           # Python version specification
├── README.md             # This file
├── templates/
│   └── index.html        # Web interface template
├── PMNACC_012025.csv     # PMNACC chemical database
└── TSCAINV_012025.csv    # TSCA Inventory database
```

## API Endpoints

- `GET /` - Main web interface
- `POST /api/search` - Search for a single CAS number
- `POST /api/upload` - Upload file with multiple CAS numbers
- `GET /api/health` - Health check endpoint

## Usage

### Single Search

1. Enter a CAS number in the search box (e.g., "67-56-1" or "67561")
2. Click "Search" or press Enter
3. View the results showing chemical name, flags, and activity status

### Bulk Upload

1. Click "Upload File"
2. Choose a CSV or text file containing CAS numbers
3. The application will automatically extract CAS numbers and search for all matches
4. View results for all found chemicals

## Data Sources

- **PMNACC**: Premanufacture Notification Access database
- **TSCAINV**: TSCA (Toxic Substances Control Act) Inventory database

## Future Enhancements

- Add flag definitions and explanations
- Support for additional countries
- Export results to CSV/Excel
- Advanced filtering options
- Chemical structure visualization

## Troubleshooting

### Common Issues

1. **"Database is still loading" error**

   - Wait a few moments and refresh the page
   - Check that CSV files are in the correct location

2. **"No results found"**

   - Verify the CAS number format
   - Check that the chemical exists in the databases

3. **File upload issues**
   - Ensure file is CSV or text format
   - Check file size (max 16MB)
   - Verify CAS numbers are in the file

### Performance Notes

- Large CSV files may take time to load initially
- Search performance is optimized for the current dataset sizes
- Consider database indexing for larger datasets

## Support

For issues or questions, please check the troubleshooting section above or create an issue in the project repository.
