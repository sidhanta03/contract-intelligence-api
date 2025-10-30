#!/bin/bash
# PostgreSQL initialization script
# This script runs when the PostgreSQL container is first created

set -e

echo "Initializing PostgreSQL database for Contract Intelligence API..."

# Configure pg_hba.conf to allow password authentication
echo "Configuring pg_hba.conf for development..."
cat > "$PGDATA/pg_hba.conf" <<-'PGHBA'
# TYPE  DATABASE        USER            ADDRESS                 METHOD
# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
# Allow connections from Docker networks
host    all             all             172.16.0.0/12           trust
# Allow connections from anywhere (development only!)
host    all             all             0.0.0.0/0               md5
# Allow replication connections from localhost
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
PGHBA

# Reload PostgreSQL configuration
pg_ctl reload -D "$PGDATA"

# Create extensions if needed
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable UUID extension (if needed in future)
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Enable pg_trgm for better text search (optional)
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    
    -- Create indexes for better performance (will be created by Alembic too)
    -- This is just a placeholder for additional setup
    
    SELECT 'Database initialized successfully!' as status;
EOSQL

echo "PostgreSQL initialization complete!"
