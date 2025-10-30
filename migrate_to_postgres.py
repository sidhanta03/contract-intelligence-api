#!/usr/bin/env python3
"""
SQLite to PostgreSQL Data Migration Script

This script migrates data from SQLite to PostgreSQL database.
It handles all edge cases including:
- Empty databases
- Large datasets with batch processing
- Data type conversions
- Foreign key constraints
- Error handling and rollback
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.documents import Document, ExtractionResult
from src.config import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database URLs
SQLITE_URL = "sqlite:///./contracts.db"
POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://contract_user:contract_password@localhost:5432/contract_intelligence"
)

# Batch size for processing large datasets
BATCH_SIZE = 100


def check_sqlite_exists():
    """Check if SQLite database file exists"""
    db_file = SQLITE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_file):
        logger.warning(f"SQLite database not found at {db_file}")
        return False
    return True


def create_engines():
    """Create database engines"""
    try:
        sqlite_engine = create_engine(
            SQLITE_URL,
            connect_args={"check_same_thread": False}
        )
        postgres_engine = create_engine(
            POSTGRES_URL,
            pool_pre_ping=True
        )
        return sqlite_engine, postgres_engine
    except Exception as e:
        logger.error(f"Failed to create database engines: {e}")
        raise


def test_connections(sqlite_engine, postgres_engine):
    """Test database connections"""
    try:
        # Test SQLite
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ SQLite connection successful")
        
        # Test PostgreSQL
        with postgres_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ PostgreSQL connection successful")
        
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def get_table_counts(engine):
    """Get row counts for all tables"""
    counts = {}
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        counts['documents'] = session.query(Document).count()
        counts['extraction_results'] = session.query(ExtractionResult).count()
    except Exception as e:
        logger.warning(f"Could not get table counts: {e}")
        counts = {'documents': 0, 'extraction_results': 0}
    finally:
        session.close()
    
    return counts


def migrate_documents(sqlite_session, postgres_session):
    """Migrate documents table"""
    logger.info("Migrating documents...")
    
    try:
        # Get total count
        total = sqlite_session.query(Document).count()
        if total == 0:
            logger.info("No documents to migrate")
            return 0
        
        logger.info(f"Found {total} documents to migrate")
        
        migrated = 0
        offset = 0
        
        while offset < total:
            # Fetch batch from SQLite
            documents = sqlite_session.query(Document).limit(BATCH_SIZE).offset(offset).all()
            
            for doc in documents:
                # Create new document instance for PostgreSQL
                new_doc = Document(
                    id=doc.id,
                    filename=doc.filename,
                    file_size=doc.file_size,
                    uploaded_at=doc.uploaded_at,
                    status=doc.status,
                    extracted_text=doc.extracted_text,
                    document_metadata=doc.document_metadata
                )
                
                # Check if already exists
                existing = postgres_session.query(Document).filter_by(id=doc.id).first()
                if existing:
                    logger.debug(f"Document {doc.id} already exists, skipping")
                    continue
                
                postgres_session.add(new_doc)
                migrated += 1
            
            # Commit batch
            postgres_session.commit()
            offset += BATCH_SIZE
            logger.info(f"Migrated {min(offset, total)}/{total} documents")
        
        logger.info(f"✓ Successfully migrated {migrated} documents")
        return migrated
        
    except Exception as e:
        logger.error(f"Error migrating documents: {e}")
        postgres_session.rollback()
        raise


def migrate_extraction_results(sqlite_session, postgres_session):
    """Migrate extraction_results table"""
    logger.info("Migrating extraction results...")
    
    try:
        # Get total count
        total = sqlite_session.query(ExtractionResult).count()
        if total == 0:
            logger.info("No extraction results to migrate")
            return 0
        
        logger.info(f"Found {total} extraction results to migrate")
        
        migrated = 0
        offset = 0
        
        while offset < total:
            # Fetch batch from SQLite
            results = sqlite_session.query(ExtractionResult).limit(BATCH_SIZE).offset(offset).all()
            
            for result in results:
                # Create new extraction result instance for PostgreSQL
                new_result = ExtractionResult(
                    id=result.id,
                    document_id=result.document_id,
                    parties=result.parties,
                    effective_date=result.effective_date,
                    term=result.term,
                    governing_law=result.governing_law,
                    payment_terms=result.payment_terms,
                    termination=result.termination,
                    auto_renewal=result.auto_renewal,
                    confidentiality=result.confidentiality,
                    indemnity=result.indemnity,
                    liability_cap=result.liability_cap,
                    signatories=result.signatories,
                    confidence_score=result.confidence_score,
                    created_at=result.created_at
                )
                
                # Check if already exists
                existing = postgres_session.query(ExtractionResult).filter_by(id=result.id).first()
                if existing:
                    logger.debug(f"Extraction result {result.id} already exists, skipping")
                    continue
                
                postgres_session.add(new_result)
                migrated += 1
            
            # Commit batch
            postgres_session.commit()
            offset += BATCH_SIZE
            logger.info(f"Migrated {min(offset, total)}/{total} extraction results")
        
        logger.info(f"✓ Successfully migrated {migrated} extraction results")
        return migrated
        
    except Exception as e:
        logger.error(f"Error migrating extraction results: {e}")
        postgres_session.rollback()
        raise


def verify_migration(sqlite_session, postgres_session):
    """Verify migration by comparing counts"""
    logger.info("Verifying migration...")
    
    sqlite_counts = get_table_counts(sqlite_session.bind)
    postgres_counts = get_table_counts(postgres_session.bind)
    
    logger.info("\nMigration Summary:")
    logger.info("=" * 60)
    logger.info(f"{'Table':<30} {'SQLite':<15} {'PostgreSQL':<15}")
    logger.info("=" * 60)
    
    all_match = True
    for table in ['documents', 'extraction_results']:
        sqlite_count = sqlite_counts.get(table, 0)
        postgres_count = postgres_counts.get(table, 0)
        match = "✓" if sqlite_count == postgres_count else "✗"
        logger.info(f"{table:<30} {sqlite_count:<15} {postgres_count:<15} {match}")
        if sqlite_count != postgres_count:
            all_match = False
    
    logger.info("=" * 60)
    
    if all_match:
        logger.info("✓ Migration verified successfully - all counts match!")
    else:
        logger.warning("⚠ Migration verification failed - counts do not match")
    
    return all_match


def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("SQLite to PostgreSQL Migration Script")
    logger.info("=" * 60)
    
    # Check if SQLite database exists
    if not check_sqlite_exists():
        logger.info("No SQLite database found. Starting fresh with PostgreSQL.")
        logger.info("Creating PostgreSQL tables...")
        
        try:
            postgres_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
            Base.metadata.create_all(bind=postgres_engine)
            logger.info("✓ PostgreSQL tables created successfully")
            return 0
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")
            return 1
    
    try:
        # Create database engines
        logger.info("Creating database connections...")
        sqlite_engine, postgres_engine = create_engines()
        
        # Test connections
        if not test_connections(sqlite_engine, postgres_engine):
            logger.error("Connection tests failed. Aborting migration.")
            return 1
        
        # Create PostgreSQL tables
        logger.info("Creating PostgreSQL tables...")
        Base.metadata.create_all(bind=postgres_engine)
        logger.info("✓ PostgreSQL tables ready")
        
        # Create sessions
        SQLiteSession = sessionmaker(bind=sqlite_engine)
        PostgresSession = sessionmaker(bind=postgres_engine)
        
        sqlite_session = SQLiteSession()
        postgres_session = PostgresSession()
        
        # Get initial counts
        logger.info("\nInitial database state:")
        sqlite_counts = get_table_counts(sqlite_engine)
        logger.info(f"SQLite - Documents: {sqlite_counts['documents']}, "
                   f"Extraction Results: {sqlite_counts['extraction_results']}")
        
        postgres_counts = get_table_counts(postgres_engine)
        logger.info(f"PostgreSQL - Documents: {postgres_counts['documents']}, "
                   f"Extraction Results: {postgres_counts['extraction_results']}")
        
        # Perform migration
        logger.info("\nStarting data migration...")
        start_time = datetime.now()
        
        try:
            # Migrate documents first (parent table)
            docs_migrated = migrate_documents(sqlite_session, postgres_session)
            
            # Migrate extraction results (child table)
            results_migrated = migrate_extraction_results(sqlite_session, postgres_session)
            
            # Verify migration
            verification_passed = verify_migration(sqlite_session, postgres_session)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"\n✓ Migration completed in {duration:.2f} seconds")
            logger.info(f"Total records migrated: {docs_migrated + results_migrated}")
            
            if verification_passed:
                logger.info("\n✓✓✓ Migration completed successfully! ✓✓✓")
                return 0
            else:
                logger.warning("\n⚠ Migration completed with warnings - please verify manually")
                return 1
                
        except Exception as e:
            logger.error(f"\n✗ Migration failed: {e}")
            return 1
        finally:
            sqlite_session.close()
            postgres_session.close()
            
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
