# Contract Intelligence API - Setup Script
# This script automates the database migration process

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Contract Intelligence API Setup" -ForegroundColor Cyan
Write-Host "SQLite to PostgreSQL Migration" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (-not (Test-Command "docker")) {
    Write-Host "✗ Docker not found. Please install Docker first." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker found" -ForegroundColor Green

if (-not (Test-Command "docker-compose")) {
    Write-Host "✗ Docker Compose not found. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker Compose found" -ForegroundColor Green

if (-not (Test-Command "python")) {
    Write-Host "✗ Python not found. Please install Python 3.11+ first." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python found" -ForegroundColor Green

Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠ .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env file. Please update with your credentials." -ForegroundColor Green
    Write-Host ""
    Write-Host "Opening .env file for editing..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    notepad .env
    Write-Host ""
    $continue = Read-Host "Have you updated the .env file? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Please update .env file and run this script again." -ForegroundColor Yellow
        exit 0
    }
}

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install Python dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Start PostgreSQL
Write-Host "Starting PostgreSQL database..." -ForegroundColor Yellow
docker-compose up -d db

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PostgreSQL container started" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to start PostgreSQL" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check database health
$retries = 0
$maxRetries = 30
$healthy = $false

while ($retries -lt $maxRetries -and -not $healthy) {
    $result = docker-compose exec -T db pg_isready -U contract_user 2>&1
    if ($LASTEXITCODE -eq 0) {
        $healthy = $true
        Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
    } else {
        $retries++
        Write-Host "Waiting... (attempt $retries/$maxRetries)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $healthy) {
    Write-Host "✗ PostgreSQL failed to start properly" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs db" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Ask about migration
$migrate = Read-Host "Do you have existing SQLite data to migrate? (y/n)"

if ($migrate -eq "y") {
    Write-Host ""
    Write-Host "Running data migration from SQLite to PostgreSQL..." -ForegroundColor Yellow
    python migrate_to_postgres.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Data migration completed successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "✗ Data migration failed" -ForegroundColor Red
        Write-Host "You can run the migration manually with: python migrate_to_postgres.py" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Creating database schema with Alembic..." -ForegroundColor Yellow
    alembic upgrade head
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Database schema created" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to create database schema" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start the application:" -ForegroundColor White
Write-Host "   docker-compose up --build" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Or run locally:" -ForegroundColor White
Write-Host "   uvicorn src.main:app --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Access the API:" -ForegroundColor White
Write-Host "   http://localhost:8000" -ForegroundColor Cyan
Write-Host "   http://localhost:8000/docs (API documentation)" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. View logs:" -ForegroundColor White
Write-Host "   docker-compose logs -f" -ForegroundColor Cyan
Write-Host ""

$start = Read-Host "Would you like to start the application now? (y/n)"

if ($start -eq "y") {
    Write-Host ""
    Write-Host "Starting the application..." -ForegroundColor Yellow
    docker-compose up --build
}
