"""
Background tasks for semantic retrieval system
Handles conversation summarization and periodic maintenance tasks
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from ..storage.database import get_db
from ..storage.models import ConversationModel, MessageModel
from ..storage.conversations import conversation_store
from .retrieval_service import RetrievalService, retrieval_service as _retrieval_singleton
from .embedding_service import embedding_worker
from ..providers.dispatcher import invoke_provider

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for the semantic retrieval system"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Start all background tasks"""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting background task manager")
        
        # Start periodic conversation summarization
        self.tasks.append(asyncio.create_task(self._periodic_conversation_summarization()))
        
        # Start periodic cleanup of old embeddings
        self.tasks.append(asyncio.create_task(self._periodic_embedding_cleanup()))
        
        # Start periodic indexing optimization
        self.tasks.append(asyncio.create_task(self._periodic_index_optimization()))
        
    async def stop(self):
        """Stop all background tasks"""
        if not self.running:
            return
            
        self.running = False
        logger.info("Stopping background task manager")
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        self.tasks.clear()
    
    async def _periodic_conversation_summarization(self):
        """Periodically summarize conversations that need it"""
        
        while self.running:
            try:
                await self._summarize_stale_conversations()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic conversation summarization: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _periodic_embedding_cleanup(self):
        """Periodically clean up old embeddings"""
        
        while self.running:
            try:
                await self._cleanup_old_embeddings()
                await asyncio.sleep(86400)  # Run daily
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic embedding cleanup: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    async def _periodic_index_optimization(self):
        """Periodically optimize pgvector indexes"""
        
        while self.running:
            try:
                await self._optimize_vector_indexes()
                await asyncio.sleep(604800)  # Run weekly
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic index optimization: {e}")
                await asyncio.sleep(86400)  # Wait 1 day before retrying
    
    async def _summarize_stale_conversations(self):
        """Summarize conversations that haven't been summarized recently"""
        
        async with get_db() as session:
            # Find conversations that need summarization
            query = """
                SELECT c.conversation_id, c.user_id, c.updated_at,
                       COUNT(m.message_id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE c.updated_at < NOW() - INTERVAL '2 hours'
                AND NOT EXISTS (
                    SELECT 1 FROM conversation_summaries cs 
                    WHERE cs.conversation_id = c.conversation_id 
                    AND cs.updated_at > NOW() - INTERVAL '2 hours'
                )
                GROUP BY c.conversation_id, c.user_id, c.updated_at
                HAVING COUNT(m.message_id) >= 10  -- Only summarize conversations with 10+ messages
                ORDER BY c.updated_at ASC
                LIMIT 20  -- Process max 20 conversations per cycle
            """
            
            result = await session.execute(query)
            conversations = result.fetchall()
            
            for conv in conversations:
                try:
                    await self._summarize_conversation(
                        conv.conversation_id, 
                        conv.user_id,
                        max_messages=30
                    )
                except Exception as e:
                    logger.error(f"Failed to summarize conversation {conv.conversation_id}: {e}")
    
    async def _summarize_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        max_messages: int = 30
    ):
        """Summarize a specific conversation with memory stratification awareness"""
        
        try:
            # Get conversation messages
            conversation = await conversation_store.get_conversation(conversation_id)
            if not conversation or not conversation.messages:
                return
                
            # Take the most recent messages
            messages = conversation.messages[-max_messages:]
            
            # Analyze message types for better summarization
            message_analysis = self._analyze_message_types(messages)
            
            # Build enhanced summary prompt
            messages_text = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages
            ]
            
            summary_prompt = f"""Please create a working memory summary of this conversation in 200-300 words.

Conversation Analysis:
- Total messages: {len(messages)}
- Message types: {message_analysis['type_distribution']}
- Key facts extracted: {message_analysis['key_facts']}
- Key preferences: {message_analysis['key_preferences']}
- Tasks mentioned: {message_analysis['tasks']}

Focus on:
1. Main topics discussed and their significance
2. Key facts, preferences, or user traits revealed
3. Important decisions, outcomes, or agreements
4. Any tasks, follow-ups, or actionable items
5. Context that should be preserved for future conversations

Prioritize information that represents stable user characteristics, preferences, or important context over temporary chat content.

Conversation:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in messages_text])}

Working Memory Summary:"""

            # Generate summary with retry logic
            summary_text = await self._generate_summary_with_retry(summary_prompt)
            
            if summary_text:
                # Store summary with embedding
                retrieval_service = _retrieval_singleton
                success = await retrieval_service.embedding_service.store_conversation_summary(
                    conversation_id=conversation_id,
                    summary_text=summary_text
                )
                
                if success:
                    logger.info(f"Successfully created working memory summary for conversation {conversation_id}")
                else:
                    logger.error(f"Failed to store working memory summary for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error creating working memory summary for conversation {conversation_id}: {e}")
    
    def _analyze_message_types(self, messages: List) -> Dict[str, Any]:
        """Analyze message types to inform summarization"""
        
        type_counts = {}
        key_facts = []
        key_preferences = []
        tasks = []
        
        for msg in messages:
            # Extract classification from metadata if available
            metadata = getattr(msg, 'metadata', {}) or {}
            classification = metadata.get('classification', {})
            
            message_type = classification.get('type', 'chat')
            type_counts[message_type] = type_counts.get(message_type, 0) + 1
            
            # Extract key information based on type
            content = getattr(msg, 'content', '')
            
            if message_type == 'fact':
                key_facts.append(content[:100])  # Store first 100 chars
            elif message_type == 'preference':
                key_preferences.append(content[:100])
            elif message_type == 'task_result':
                tasks.append(content[:100])
        
        return {
            'type_distribution': type_counts,
            'key_facts': key_facts[:3],  # Top 3 facts
            'key_preferences': key_preferences[:3],  # Top 3 preferences
            'tasks': tasks[:3]  # Top 3 tasks
        }
    
    async def _generate_summary_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Generate summary with retry logic"""
        
        for attempt in range(max_retries):
            try:
                payload = {
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 400,
                    "temperature": 0.3,
                }
                
                provider_response = await invoke_provider(
                    pid=None,
                    model="gpt-3.5-turbo",
                    payload=payload,
                    timeout_ms=30000,
                    stream=False,
                )
                
                if isinstance(provider_response, dict) and provider_response.get("ok"):
                    return provider_response["result"]["text"]
                else:
                    logger.warning(f"Summary generation attempt {attempt + 1} failed: {provider_response}")
                    
            except Exception as e:
                logger.warning(f"Summary generation attempt {attempt + 1} error: {e}")
                
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        logger.error("All summary generation attempts failed")
        return None
    
    async def _cleanup_old_embeddings(self):
        """Clean up embeddings older than retention period"""
        
        async with get_db() as session:
            # Delete embeddings older than 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Note: In production, you'd want to be more selective about what to delete
            # For now, we'll just log what would be cleaned up
            query = """
                SELECT COUNT(*) as count
                FROM embeddings
                WHERE created_at < :cutoff_date
            """
            
            result = await session.execute(query, {"cutoff_date": cutoff_date})
            count = result.fetchone().count
            
            if count > 0:
                logger.info(f"Found {count} embeddings older than 90 days that could be cleaned up")
                
                # In production, you might want to move to archive instead of delete
                # For now, we'll just log it
                # await session.execute(
                #     "DELETE FROM embeddings WHERE created_at < :cutoff_date",
                #     {"cutoff_date": cutoff_date}
                # )
                # await session.commit()
    
    async def _optimize_vector_indexes(self):
        """Optimize pgvector indexes"""
        
        try:
            async with get_db() as session:
                # Recreate IVFFLAT indexes for better performance
                # This should only be done when the table has sufficient data
                
                index_queries = [
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'embeddings' 
                        AND indexname = 'embeddings_embedding_idx'
                    ) as index_exists
                    """,
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM embeddings LIMIT 1000) THEN
                            DROP INDEX IF EXISTS embeddings_embedding_idx;
                            CREATE INDEX embeddings_embedding_idx 
                            ON embeddings USING ivfflat (embedding vector_cosine_ops) 
                            WITH (lists = 100);
                        END IF;
                    END $$;
                    """,
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM conversation_summaries LIMIT 100) THEN
                            DROP INDEX IF EXISTS conversation_summaries_embedding_idx;
                            CREATE INDEX conversation_summaries_embedding_idx 
                            ON conversation_summaries USING ivfflat (summary_embedding vector_cosine_ops) 
                            WITH (lists = 10);
                        END IF;
                    END $$;
                    """,
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM memory_facts LIMIT 100) THEN
                            DROP INDEX IF EXISTS memory_facts_embedding_idx;
                            CREATE INDEX memory_facts_embedding_idx 
                            ON memory_facts USING ivfflat (fact_embedding vector_cosine_ops) 
                            WITH (lists = 10);
                        END IF;
                    END $$;
                    """
                ]
                
                for query in index_queries:
                    await session.execute(query)
                
                await session.commit()
                logger.info("Vector index optimization completed")
                
        except Exception as e:
            logger.error(f"Error optimizing vector indexes: {e}")


# Global background task manager instance
background_task_manager = BackgroundTaskManager()


class ConversationSummarizationService:
    """Service for on-demand conversation summarization"""
    
    def __init__(self):
        self.retrieval_service = _retrieval_singleton
    
    async def summarize_conversation(
        self, 
        conversation_id: str, 
        force_resummarize: bool = False,
        max_messages: int = 50
    ) -> Dict[str, Any]:
        """Summarize a conversation on demand"""
        
        try:
            # Check if summary already exists and is recent
            if not force_resummarize:
                async with get_db() as session:
                    result = await session.execute(
                        """
                        SELECT updated_at FROM conversation_summaries 
                        WHERE conversation_id = :conv_id 
                        AND updated_at > NOW() - INTERVAL '2 hours'
                        """,
                        {"conv_id": conversation_id}
                    )
                    existing = result.fetchone()
                    
                    if existing:
                        return {
                            "success": False,
                            "message": "Recent summary already exists",
                            "conversation_id": conversation_id
                        }
            
            # Get conversation details
            conversation = await conversation_store.get_conversation(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "message": "Conversation not found",
                    "conversation_id": conversation_id
                }
            
            user_id = conversation.user_id
            if not user_id:
                return {
                    "success": False,
                    "message": "Conversation has no user_id",
                    "conversation_id": conversation_id
                }
            
            # Generate and store summary
            await background_task_manager._summarize_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                max_messages=max_messages
            )
            
            return {
                "success": True,
                "message": "Conversation summarized successfully",
                "conversation_id": conversation_id,
                "summarized_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in summarize_conversation: {e}")
            return {
                "success": False,
                "message": f"Failed to summarize conversation: {str(e)}",
                "conversation_id": conversation_id
            }