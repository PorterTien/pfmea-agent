# PFMEA Analysis Tool - Auto Setup & Start Script (Windows PowerShell)
# This script automatically configures and starts the entire application

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Header {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $args" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Header "PFMEA Analysis Tool - Auto Setup & Start"

# Check for clear-db flag
$ClearDB = $false
if ($args -contains "--clear-db" -or $args -contains "-c") {
    $ClearDB = $true
}

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check Python
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Success "Python found: $pythonVersion"
    
    # Check Python version (3.11+)
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
    if ($versionMatch) {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            Write-Error "Python 3.11+ is required. Found: $major.$minor"
            exit 1
        }
    }
} catch {
    Write-Error "Python 3 is not installed. Please install Python 3.11+ first."
    Write-Info "Download from: https://www.python.org/downloads/"
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version
    if ($LASTEXITCODE -ne 0) {
        throw "Node.js not found"
    }
    Write-Success "Node.js found: $nodeVersion"
    
    $versionMatch = $nodeVersion -match "v(\d+)"
    if ($versionMatch) {
        $major = [int]$matches[1]
        if ($major -lt 18) {
            Write-Error "Node.js 18+ is required. Found: v$major"
            exit 1
        }
    }
} catch {
    Write-Error "Node.js is not installed. Please install Node.js 18+ first."
    Write-Info "Download from: https://nodejs.org/"
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version
    Write-Success "npm found: v$npmVersion"
} catch {
    Write-Error "npm is not installed."
    exit 1
}

# Check Ollama
$OllamaAvailable = $false
try {
    $ollamaCheck = ollama --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Ollama found"
        $OllamaAvailable = $true
        
        # Check if Ollama is running
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            Write-Success "Ollama server is running"
        } catch {
            Write-Warning "Ollama server is not running. Please start Ollama manually."
            Write-Info "On Windows, Ollama usually runs as a service. Check if it's running in Task Manager."
        }
        
        # Check if model is available
        if ($OllamaAvailable) {
            $models = ollama list 2>&1 | Select-String "llama3.2:3b"
            if (-not $models) {
                Write-Warning "No LLM model found. Pulling llama3.2:3b (this may take a while)..."
                ollama pull llama3.2:3b
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Model pulled successfully"
                } else {
                    Write-Warning "Failed to pull model. You can pull manually with: ollama pull llama3.2:3b"
                }
            } else {
                Write-Success "LLM model available: llama3.2:3b"
            }
        }
    }
} catch {
    Write-Warning "Ollama is not installed or not in PATH."
    Write-Warning "Please install Ollama from https://ollama.ai"
    Write-Warning "The application will start but LLM features won't work."
}

# Setup Backend
Write-Header "Setting up Backend"

Set-Location backend

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Info "Creating Python virtual environment..."
    python -m venv venv
    Write-Success "Virtual environment created"
}

# Activate virtual environment
$venvActivate = Join-Path $PWD "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Error "Failed to activate virtual environment"
    exit 1
}

# Install/upgrade dependencies
Write-Info "Installing Python dependencies..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
Write-Success "Backend dependencies installed"

# Create uploads directory
if (-not (Test-Path "uploads")) {
    New-Item -ItemType Directory -Path "uploads" | Out-Null
}
Write-Success "Backend ready"

Set-Location ..

# Setup Frontend
Write-Header "Setting up Frontend"

Set-Location frontend

# Install dependencies if node_modules doesn't exist
if (-not (Test-Path "node_modules")) {
    Write-Info "Installing Node.js dependencies (this may take a minute)..."
    npm install
    Write-Success "Frontend dependencies installed"
} else {
    Write-Success "Frontend dependencies already installed"
}

Set-Location ..

# Clear database if requested
if ($ClearDB) {
    Write-Warning "Clearing database..."
    Set-Location backend
    
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
        
        if (Test-Path "pfmea.db") {
            $clearScript = @"
import os
import sys
sys.path.insert(0, os.getcwd())

from app.models.database import engine, Base
from app.models.analysis import Analysis, PFMEAResult

# Drop all tables
print("Dropping existing tables...")
Base.metadata.drop_all(bind=engine, checkfirst=True)

# Recreate tables
print("Recreating tables...")
Base.metadata.create_all(bind=engine)

print("✓ Database cleared and reinitialized")
"@
            $clearScript | python
            Write-Success "Database cleared"
        } else {
            Write-Info "No database file found, will be created on first run."
        }
    } else {
        Write-Error "Virtual environment not found. Cannot clear database."
    }
    Set-Location ..
} elseif (Test-Path "backend\pfmea.db") {
    Write-Info "Database exists. Use --clear-db flag to clear it on startup."
}

# Create .env file if it doesn't exist
if (-not (Test-Path "backend\.env")) {
    Write-Info "Creating backend\.env file..."
    $envContent = @"
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Application
DEBUG=false

# File Upload
MAX_UPLOAD_SIZE_MB=50

# Database
DATABASE_URL=sqlite:///./pfmea.db

# CORS
ENABLE_CORS=true
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
"@
    $envContent | Out-File -FilePath "backend\.env" -Encoding utf8
    Write-Success "Configuration file created"
}

# Check and kill existing processes
Write-Header "Checking for Existing Processes"

function Kill-Port {
    param($Port, $Service)
    
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections) {
            $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            Write-Warning "Found existing $Service process(es) on port $Port (PIDs: $pids). Killing..."
            foreach ($pid in $pids) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Seconds 2
            Write-Success "Killed existing $Service process(es)"
        } else {
            Write-Success "Port $Port is free"
        }
    } catch {
        Write-Warning "Cannot check for existing processes on port $Port"
    }
}

function Kill-ProcessByName {
    param($Pattern, $Service)
    
    try {
        # Try to find processes by name pattern
        $processes = Get-Process | Where-Object { $_.ProcessName -like "*$Pattern*" } -ErrorAction SilentlyContinue
        if ($processes) {
            $pids = $processes | Select-Object -ExpandProperty Id -Unique
            Write-Warning "Found existing $Service process(es) matching '$Pattern' (PIDs: $pids). Killing..."
            foreach ($pid in $pids) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Seconds 1
            Write-Success "Killed existing $Service process(es)"
        }
    } catch {
        # Ignore errors
    }
}

# Kill existing processes
Write-Info "Checking for existing server processes..."
Kill-ProcessByName "uvicorn" "backend"
Kill-ProcessByName "vite" "frontend"
Kill-Port 8000 "backend"
Kill-Port 5173 "frontend"

# Start servers
Write-Header "Starting Servers"

# Function to cleanup on exit
function Cleanup {
    Write-Info "`nShutting down servers..."
    Kill-Port 8000 "backend"
    Kill-Port 5173 "frontend"
    Write-Success "Servers stopped"
    exit 0
}

# Register cleanup handler
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# Start backend
Write-Info "Starting backend server on http://localhost:8000"
Set-Location backend
$backendLog = Join-Path $ScriptDir "backend.log"
$pythonExe = Join-Path $PWD "venv\Scripts\python.exe"
Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog -WindowStyle Hidden -PassThru | Out-Null
Set-Location ..

# Wait for backend to be ready
Write-Info "Waiting for backend to start..."
Start-Sleep -Seconds 3
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Success "Backend server is running"
} catch {
    Write-Warning "Backend may still be starting. Check backend.log if issues occur."
}

# Start frontend
Write-Info "Starting frontend server on http://localhost:5173"
Set-Location frontend
$frontendLog = Join-Path $ScriptDir "frontend.log"
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendLog -WindowStyle Hidden -PassThru | Out-Null
Set-Location ..

# Wait a bit for frontend
Start-Sleep -Seconds 2

Write-Header "Application Started Successfully!"

Write-Host "✓ Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "✓ Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser and navigate to: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""

if (-not $OllamaAvailable) {
    Write-Host "⚠ Warning: Ollama is not available. LLM features will not work." -ForegroundColor Yellow
    Write-Host "   Install from: https://ollama.ai" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Yellow
Write-Host ""

Write-Info "Server logs:"
Write-Host "  Backend:  Get-Content backend.log -Wait -Tail 50" -ForegroundColor Cyan
Write-Host "  Frontend: Get-Content frontend.log -Wait -Tail 50" -ForegroundColor Cyan
Write-Host ""

# Keep script running
Write-Host "Servers are running in the background." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop all servers..." -ForegroundColor Yellow
Write-Host ""

# Wait for user interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    # User pressed Ctrl+C
    Cleanup
}

