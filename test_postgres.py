#!/usr/bin/env python3
"""
Test script to verify PostgreSQL connection and create tables
"""

import os
import sys

# Set up environment
os.environ['DATABASE_URL'] = 'postgresql://contract_user:contract_password@localhost:5432/contract_intelligence'

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    print("✓ SQLAlchemy imported successfully")
    
    # Import models
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.config import Base, settings
    from src.models.documents import Document, ExtractionResult
    print("✓ Models imported successfully")
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    print(f"✓ Engine created: {settings.DATABASE_URL}")
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✓ PostgreSQL connected: {version[:50]}...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created!")
    
    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✓ Tables created: {', '.join(tables)}")
    
    # Test inserting a record
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Check if test record exists
    test_doc = session.query(Document).filter_by(filename="test.pdf").first()
    if not test_doc:
        test_doc = Document(
            filename="test.pdf",
            file_size=1024,
            status="test"
        )
        session.add(test_doc)
        session.commit()
        print(f"✓ Test document created: {test_doc.id}")
    else:
        print(f"✓ Test document already exists: {test_doc.id}")
    
    # Count records
    doc_count = session.query(Document).count()
    print(f"✓ Total documents in database: {doc_count}")
    
    session.close()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED! PostgreSQL is working correctly!")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
