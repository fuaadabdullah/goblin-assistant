"""Initial vector setup with pgvector extension

Revision ID: 001_initial_vector_setup
Revises: 
Create Date: 2025-12-30 23:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_vector_setup'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create pgvector extension and vector tables"""
    
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create embeddings table
    op.create_table(
        'embeddings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('embedding', postgresql.VECTOR(1536), nullable=True),  # OpenAI text-embedding-3-small
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create conversation_summaries table
    op.create_table(
        'conversation_summaries',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('summary_embedding', postgresql.VECTOR(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create memory_facts table
    op.create_table(
        'memory_facts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('fact_text', sa.Text(), nullable=False),
        sa.Column('fact_embedding', postgresql.VECTOR(1536), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_embeddings_user_conversation', 'embeddings', ['user_id', 'conversation_id'])
    op.create_index('idx_embeddings_source_type', 'embeddings', ['source_type'])
    op.create_index('idx_embeddings_created_at', 'embeddings', ['created_at'])
    op.create_index('idx_conversation_summaries_conversation_id', 'conversation_summaries', ['conversation_id'])
    op.create_index('idx_memory_facts_user_id', 'memory_facts', ['user_id'])
    op.create_index('idx_memory_facts_category', 'memory_facts', ['category'])
    
    # Create pgvector indexes for similarity search
    # IVFFLAT index for fast approximate search (needs to be created after table has data)
    # op.execute("CREATE INDEX embeddings_embedding_idx ON embeddings USING ivfflat (embedding vector_cosine_ops)")
    # op.execute("CREATE INDEX conversation_summaries_embedding_idx ON conversation_summaries USING ivfflat (summary_embedding vector_cosine_ops)")
    # op.execute("CREATE INDEX memory_facts_embedding_idx ON memory_facts USING ivfflat (fact_embedding vector_cosine_ops)")


def downgrade() -> None:
    """Drop vector tables and extension"""
    
    # Drop indexes
    op.drop_index('idx_memory_facts_category', table_name='memory_facts')
    op.drop_index('idx_memory_facts_user_id', table_name='memory_facts')
    op.drop_index('idx_conversation_summaries_conversation_id', table_name='conversation_summaries')
    op.drop_index('idx_embeddings_created_at', table_name='embeddings')
    op.drop_index('idx_embeddings_source_type', table_name='embeddings')
    op.drop_index('idx_embeddings_user_conversation', table_name='embeddings')
    
    # Drop tables
    op.drop_table('memory_facts')
    op.drop_table('conversation_summaries')
    op.drop_table('embeddings')
    
    # Note: Don't drop pgvector extension as it might be used by other extensions
    # op.execute("DROP EXTENSION IF EXISTS vector")