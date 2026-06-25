-- Activate pgvector: convert TEXT embedding columns to vector(1536) and add HNSW indexes
-- Safe to run on empty tables; no existing rows need casting.

-- Confirm pgvector is active (no-op if already installed)
CREATE EXTENSION IF NOT EXISTS vector;

-- Convert TEXT columns to proper vector(1536) type
ALTER TABLE public.embeddings
  ALTER COLUMN embedding TYPE vector(1536) USING NULL;

ALTER TABLE public.conversation_summaries
  ALTER COLUMN summary_embedding TYPE vector(1536) USING NULL;

ALTER TABLE public.memory_facts
  ALTER COLUMN fact_embedding TYPE vector(1536) USING NULL;

-- HNSW indexes for approximate nearest-neighbor similarity search
-- HNSW preferred over IVFFLAT: builds on empty tables, higher recall, no list-count tuning
CREATE INDEX IF NOT EXISTS embeddings_embedding_hnsw_idx
  ON public.embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS conversation_summaries_embedding_hnsw_idx
  ON public.conversation_summaries USING hnsw (summary_embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS memory_facts_embedding_hnsw_idx
  ON public.memory_facts USING hnsw (fact_embedding vector_cosine_ops);
