"""add document chunks table for RAG

Revision ID: 002
Revises: 001
Create Date: 2025-10-30 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('char_start', sa.Integer(), nullable=True),
        sa.Column('char_end', sa.Integer(), nullable=True),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('ix_document_chunks_id', 'document_chunks', ['id'])
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])
    
    # Update extraction_results to add foreign key if it doesn't exist
    # and change auto_renewal to boolean
    op.alter_column('extraction_results', 'auto_renewal',
                    existing_type=sa.String(),
                    type_=sa.Boolean(),
                    postgresql_using='auto_renewal::boolean',
                    nullable=True)
    
    # Add foreign key constraint to extraction_results if not exists
    try:
        op.create_foreign_key(
            'fk_extraction_results_document_id',
            'extraction_results', 'documents',
            ['document_id'], ['id'],
            ondelete='CASCADE'
        )
    except:
        pass  # Constraint might already exist
    
    # Change payment_terms and termination to TEXT for longer content
    op.alter_column('extraction_results', 'payment_terms',
                    existing_type=sa.String(),
                    type_=sa.Text(),
                    nullable=True)
    
    op.alter_column('extraction_results', 'termination',
                    existing_type=sa.String(),
                    type_=sa.Text(),
                    nullable=True)
    
    op.alter_column('extraction_results', 'confidentiality',
                    existing_type=sa.String(),
                    type_=sa.Text(),
                    nullable=True)
    
    op.alter_column('extraction_results', 'indemnity',
                    existing_type=sa.String(),
                    type_=sa.Text(),
                    nullable=True)


def downgrade():
    # Revert column type changes
    op.alter_column('extraction_results', 'indemnity',
                    existing_type=sa.Text(),
                    type_=sa.String(),
                    nullable=True)
    
    op.alter_column('extraction_results', 'confidentiality',
                    existing_type=sa.Text(),
                    type_=sa.String(),
                    nullable=True)
    
    op.alter_column('extraction_results', 'termination',
                    existing_type=sa.Text(),
                    type_=sa.String(),
                    nullable=True)
    
    op.alter_column('extraction_results', 'payment_terms',
                    existing_type=sa.Text(),
                    type_=sa.String(),
                    nullable=True)
    
    # Drop foreign key
    try:
        op.drop_constraint('fk_extraction_results_document_id', 'extraction_results', type_='foreignkey')
    except:
        pass
    
    # Revert auto_renewal type
    op.alter_column('extraction_results', 'auto_renewal',
                    existing_type=sa.Boolean(),
                    type_=sa.String(),
                    nullable=True)
    
    # Drop indexes
    op.drop_index('ix_document_chunks_document_id', 'document_chunks')
    op.drop_index('ix_document_chunks_id', 'document_chunks')
    
    # Drop table
    op.drop_table('document_chunks')
