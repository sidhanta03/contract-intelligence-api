# Contract Intelligence API 🚀

AI-powered contract analysis and clause extraction API with PostgreSQL database on Docker.

## 🌟 Features

- 📄 **Document Ingestion**: Upload and process contract documents
- 🔍 **Intelligent Extraction**: Extract key contract clauses using AI
- 💬 **Natural Language Queries**: Ask questions about your contracts
- 🐘 **PostgreSQL Database**: Robust, scalable database with connection pooling
- 🐳 **Docker Support**: Fully containerized application
- 🔄 **Database Migrations**: Alembic-based schema versioning
- 📊 **Health Monitoring**: Built-in health checks and logging
- 🔒 **Security**: Non-root containers, environment-based configuration

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```powershell
# Run the automated setup script
.\setup.ps1
```

The script will:
- ✅ Check prerequisites
- ✅ Install dependencies
- ✅ Start PostgreSQL
- ✅ Run migrations
- ✅ Optionally start the application

### Option 2: Manual Setup

1. **Clone and navigate to the project**
   ```powershell
   cd contract-intelligence-api
   ```

2. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```powershell
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start PostgreSQL**
   ```powershell
   docker-compose up -d db
   ```

5. **Run migrations**
   ```powershell
   # If migrating from SQLite
   python migrate_to_postgres.py
   
   # OR if starting fresh
   alembic upgrade head
   ```

6. **Start the application**
   ```powershell
   # With Docker
   docker-compose up --build
   
   # OR locally
   uvicorn src.main:app --reload
   ```

## 📋 Prerequisites

- **Docker** & **Docker Compose**
- **Python 3.11+**
- **PostgreSQL** (via Docker)

## 🏗️ Architecture

```
┌─────────────────┐
│   FastAPI App   │
│   (Port 8000)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Port 5432)   │
└─────────────────┘
```

## 📁 Project Structure

```
contract-intelligence-api/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration & settings
│   ├── db.py                # Database connection
│   ├── models/              # SQLAlchemy models
│   │   └── documents.py
│   ├── routers/             # API routes
│   │   ├── ingest.py
│   │   ├── extract.py
│   │   └── ask_route.py
│   └── utils/               # Utility functions
├── alembic/                 # Database migrations
├── init-scripts/            # PostgreSQL init scripts
├── docker-compose.yml       # Docker services
├── Dockerfile              # Application container
├── migrate_to_postgres.py  # Migration script
├── setup.ps1               # Automated setup
└── MIGRATION_GUIDE.md      # Detailed migration docs
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
# Database
POSTGRES_DB=contract_intelligence
POSTGRES_USER=contract_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_PORT=5432

# Application
APP_PORT=8000
DATABASE_URL=postgresql://contract_user:your_secure_password@localhost:5432/contract_intelligence

# API Keys
GEMINI_API_KEY=your_gemini_api_key
```

### Database Connection Pooling

Configure in `.env`:

```env
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

## 📊 API Endpoints

### Health Check
```http
GET /healthz
```

### Document Ingestion
```http
POST /api/ingest
```

### Clause Extraction
```http
POST /api/extract
```

### Ask Questions
```http
POST /api/ask
```

📖 **Full API Documentation**: http://localhost:8000/docs

## 🐳 Docker Commands

### Start Services
```powershell
docker-compose up -d
```

### View Logs
```powershell
docker-compose logs -f
```

### Stop Services
```powershell
docker-compose down
```

### Rebuild
```powershell
docker-compose up --build
```

### Database Access
```powershell
docker exec -it contract_intelligence_db psql -U contract_user -d contract_intelligence
```

## 🔄 Database Migrations

### Create Migration
```powershell
alembic revision --autogenerate -m "description"
```

### Apply Migrations
```powershell
alembic upgrade head
```

### Rollback
```powershell
alembic downgrade -1
```

### View History
```powershell
alembic history
```

## 🔍 Database Management

### Backup Database
```powershell
docker exec contract_intelligence_db pg_dump -U contract_user contract_intelligence > backup.sql
```

### Restore Database
```powershell
cat backup.sql | docker exec -i contract_intelligence_db psql -U contract_user -d contract_intelligence
```

### View Tables
```sql
-- Connect to database
docker exec -it contract_intelligence_db psql -U contract_user -d contract_intelligence

-- List tables
\dt

-- View table structure
\d documents
\d extraction_results
```

## 🚨 Troubleshooting

### Database Connection Issues

1. Check if PostgreSQL is running:
   ```powershell
   docker-compose ps
   ```

2. Check PostgreSQL logs:
   ```powershell
   docker-compose logs db
   ```

3. Test connection:
   ```powershell
   docker exec contract_intelligence_db pg_isready -U contract_user
   ```

### Port Conflicts

Change ports in `.env`:
```env
POSTGRES_PORT=5433
APP_PORT=8001
```

### Migration Issues

View detailed migration guide:
```powershell
cat MIGRATION_GUIDE.md
```

## 🔒 Security Features

- ✅ Non-root user in containers
- ✅ Environment-based secrets
- ✅ Connection pooling with health checks
- ✅ Docker network isolation
- ✅ Read-only filesystem support

## 📈 Performance Features

- ✅ Connection pooling (configurable)
- ✅ Batch processing for large datasets
- ✅ Database query optimization
- ✅ Multi-stage Docker builds
- ✅ Health check endpoints

## 🧪 Development

### Run Tests
```powershell
pytest
```

### Code Formatting
```powershell
black src/
```

### Linting
```powershell
flake8 src/
```

## 📚 Documentation

- [Migration Guide](MIGRATION_GUIDE.md) - Detailed migration documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues or questions:
1. Check the [Migration Guide](MIGRATION_GUIDE.md)
2. Review [Troubleshooting](#-troubleshooting) section
3. Check Docker logs: `docker-compose logs -f`

## 📊 Migration from SQLite

If you're migrating from an existing SQLite database:

1. **Backup your SQLite database**
   ```powershell
   cp contracts.db contracts.db.backup
   ```

2. **Run the migration script**
   ```powershell
   python migrate_to_postgres.py
   ```

3. **Verify the migration**
   ```powershell
   # The script will show a summary
   ```

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed instructions.

## 🎯 Roadmap

- [ ] Add authentication/authorization
- [ ] Implement caching layer
- [ ] Add more AI models support
- [ ] Enhanced search capabilities
- [ ] Batch processing improvements
- [ ] GraphQL API support

## 📞 Contact

For questions or support, please open an issue on GitHub.

---

Made with ❤️ using FastAPI, PostgreSQL, and Docker
