# Rerank Role Documentation

## Overview

The rerank role enables hybrid Continue setup with advanced document reranking capabilities. This role integrates multiple reranking providers to improve retrieval quality in RAG (Retrieval-Augmented Generation) applications.

## Supported Providers

### Voyage AI
- **Provider**: `voyageai`
- **Models**: `rerank-1`, `rerank-lite-1`
- **Features**: High-performance reranking with semantic understanding
- **API Key**: Required from Voyage AI dashboard

### Cohere
- **Provider**: `cohere`
- **Models**: `rerank-english-v2.0`, `rerank-multilingual-v2.0`
- **Features**: Multilingual support, fast inference
- **API Key**: Required from Cohere dashboard

### LLM-based Reranking
- **Provider**: `llm`
- **Models**: Any compatible LLM (GPT-4, Claude, etc.)
- **Features**: Uses LLM for relevance scoring
- **API Key**: Depends on chosen LLM provider

### TEI (Text Embeddings Inference)
- **Provider**: `tei`
- **Models**: Local TEI server models
- **Features**: Local inference, privacy-focused
- **Setup**: Requires running TEI server locally

## Configuration

### Basic Setup

```yaml
rerank:
  provider: voyageai  # voyageai, cohere, llm, or tei
  model: rerank-1
  api_key: ${VOYAGE_API_KEY}
  top_k: 10
```

### Advanced Configuration

```yaml
rerank:
  provider: voyageai
  model: rerank-1
  api_key: ${VOYAGE_API_KEY}
  top_k: 10
  score_threshold: 0.7
  batch_size: 32
  timeout: 30
```

### Multiple Providers (Fallback)

```yaml
rerank:
  - provider: voyageai
    model: rerank-1
    api_key: ${VOYAGE_API_KEY}
    priority: 1
  - provider: cohere
    model: rerank-english-v2.0
    api_key: ${COHERE_API_KEY}
    priority: 2
  - provider: llm
    model: gpt-4
    api_key: ${OPENAI_API_KEY}
    priority: 3
```

## Usage Examples

### Basic Reranking

```python
from rerank import Reranker

reranker = Reranker(config=rerank_config)
documents = ["doc1", "doc2", "doc3"]
query = "What is machine learning?"

ranked_docs = reranker.rerank(query, documents)
```

### Hybrid Search with Reranking

```python
# First retrieve candidates
candidates = vector_search(query, top_k=100)

# Then rerank for better relevance
reranked = reranker.rerank(query, candidates, top_k=10)
```

## Performance Considerations

- **Batch Processing**: Use batch_size parameter for multiple queries
- **Caching**: Implement result caching for repeated queries
- **Async Support**: Use async methods for non-blocking operations
- **Rate Limiting**: Respect API rate limits for cloud providers

## Monitoring

Monitor reranking performance with these metrics:
- Response time per query
- Reranking accuracy vs baseline
- API usage and costs
- Error rates and fallback usage

## Troubleshooting

### Common Issues

1. **API Key Errors**: Verify API keys are set correctly
2. **Timeout Errors**: Increase timeout or reduce batch size
3. **Low Scores**: Adjust score_threshold or try different models
4. **Rate Limits**: Implement exponential backoff

### Debug Mode

Enable debug logging:

```yaml
rerank:
  debug: true
  log_level: DEBUG
```

## Integration with Continue

This rerank role integrates seamlessly with Continue's hybrid search:

```yaml
continue:
  rerank:
    enabled: true
    provider: voyageai
    model: rerank-1
```

## Best Practices

1. **Choose Right Model**: Voyage AI for general use, Cohere for multilingual
2. **Set Appropriate top_k**: Balance between quality and speed
3. **Use Fallbacks**: Configure multiple providers for reliability
4. **Monitor Costs**: Track API usage for cloud providers
5. **Test Locally**: Use TEI for development and testing
