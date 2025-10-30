"""initial schema with UUID primary keys

Revision ID: 001
Revises: 
Create Date: 2025-10-30 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create documents table with String (UUID) primary key
    op.create_table(
        'documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('status', sa.String(), server_default='uploaded', nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('document_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_documents_id', 'documents', ['id'])
    op.create_index('ix_documents_filename', 'documents', ['filename'])
    op.create_index('ix_documents_status', 'documents', ['status'])
    
    # Create extraction_results table
    op.create_table(
        'extraction_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('parties', sa.JSON(), nullable=True),
        sa.Column('effective_date', sa.String(), nullable=True),
        sa.Column('term', sa.String(), nullable=True),
        sa.Column('governing_law', sa.String(), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('termination', sa.Text(), nullable=True),
        sa.Column('auto_renewal', sa.Boolean(), nullable=True),
        sa.Column('confidentiality', sa.Text(), nullable=True),
        sa.Column('indemnity', sa.Text(), nullable=True),
        sa.Column('liability_cap', sa.JSON(), nullable=True),
        sa.Column('signatories', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('ix_extraction_results_id', 'extraction_results', ['id'])
    op.create_index('ix_extraction_results_document_id', 'extraction_results', ['document_id'])


def downgrade():
    # Drop tables in reverse order (respect foreign key constraints)
    op.drop_index('ix_extraction_results_document_id', 'extraction_results')
    op.drop_index('ix_extraction_results_id', 'extraction_results')
    op.drop_table('extraction_results')
    
    op.drop_index('ix_documents_status', 'documents')
    op.drop_index('ix_documents_filename', 'documents')
    op.drop_index('ix_documents_id', 'documents')
    op.drop_table('documents')
