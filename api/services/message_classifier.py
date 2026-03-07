"""
Message classification service for memory stratification
Classifies messages into: CHAT | FACT | PREFERENCE | TASK_RESULT | SYSTEM
"""

import re
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio
from datetime import datetime

from ..providers.dispatcher_fixed import invoke_provider
from ..storage.models import MessageModel
from ..storage.database import get_db


class MessageType(Enum):
    """Message classification types"""
    CHAT = "chat"
    FACT = "fact"
    PREFERENCE = "preference"
    TASK_RESULT = "task_result"
    SYSTEM = "system"
    NOISE = "noise"


class MessageClassification:
    """Result of message classification"""
    
    def __init__(
        self,
        message_type: MessageType,
        confidence: float,
        keywords: List[str],
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message_type = message_type
        self.confidence = confidence
        self.keywords = keywords
        self.reasoning = reasoning
        self.metadata = metadata or {}


class MessageClassifier:
    """Service for classifying messages into memory types"""
    
    def __init__(self):
        # Rule-based patterns for initial classification
        self._fact_patterns = [
            r"(?i)\b(i am|i'm)\s+(.+?)\b",  # "I am a developer"
            r"(?i)\b(i have|i've)\s+(.+?)\b",  # "I have 5 years experience"
            r"(?i)\b(i work|working)\s+(.+?)\b",  # "I work at Google"
            r"(?i)\b(my name is|call me)\s+(.+?)\b",  # "My name is John"
            r"(?i)\b(i live|living)\s+(.+?)\b",  # "I live in NYC"
            r"(?i)\b(i studied|degree in)\s+(.+?)\b",  # "I studied computer science"
            r"(?i)\b(i know|familiar with)\s+(.+?)\b",  # "I know Python"
            r"(?i)\b(i use|using)\s+(.+?)\b",  # "I use React"
        ]
        
        self._preference_patterns = [
            r"(?i)\b(i prefer|i like|i love)\s+(.+?)\b",
            r"(?i)\b(i don't like|i dislike|i hate)\s+(.+?)\b",
            r"(?i)\b(i want|i need)\s+(.+?)\b",
            r"(?i)\b(i always|i never)\s+(.+?)\b",
            r"(?i)\b(best|worst|favorite|terrible|amazing)\s+(.+?)\b",
            r"(?i)\b(rather|instead of|over)\s+(.+?)\b",
            r"(?i)\b(should|must|have to|need to)\s+(.+?)\b",
            r"(?i)\b(avoid|don't want|never use)\s+(.+?)\b",
        ]
        
        self._task_result_patterns = [
            r"(?i)\b(done|completed|finished|created|built|implemented)\b",
            r"(?i)\b(successfully|completed|finished)\s+(.+?)\b",
            r"(?i)\b(here is|attached is|provided below)\b",
            r"(?i)\b(result|output|code|solution)\b",
            r"(?i)\b(check it out|see below|as requested)\b",
            r"(?i)\b(task|assignment|request)\s+(.+?)\b",
        ]
        
        self._system_patterns = [
            r"(?i)\b(system|assistant|bot|ai)\b",
            r"(?i)\b(memory|context|conversation)\b",
            r"(?i)\b(settings|configuration|setup)\b",
            r"(?i)\b(help|support|documentation)\b",
        ]
        
        self._noise_patterns = [
            r"(?i)\b(ok|okay|k)\b",  # Simple acknowledgements
            r"(?i)\b(yes|no|yeah|nah)\b",  # Simple responses
            r"(?i)\b(thanks|thank you|ty|thx)\b",  # Thanks without context
            r"(?i)\b(sure|alright|got it|cool)\b",  # Simple confirmations
            r"(?i)\b(lol|lmao|rofl|rotfl)\b",  # Laughter without context
            r"(?i)\b(what|why|how|when|where)\?$",  # Single word questions
            r"(?i)\b(hi|hello|hey|yo)\b",  # Greetings without context
            r"(?i)\b(bye|goodbye|see you|later)\b",  # Goodbyes
            r"(?i)\b(please|sorry|excuse me)\b",  # Politeness without substance
            r"^[a-zA-Z]{1,3}$",  # Very short messages (a, ok, ty, etc.)
            r"^[.!?]+$",  # Just punctuation
            r"^\s*$",  # Empty or whitespace only
        ]
    
    def classify_message(self, content: str, role: str) -> MessageClassification:
        """
        Classify a message using rule-based patterns and confidence scoring
        
        Args:
            content: Message content to classify
            role: Message role (user/assistant/system)
        
        Returns:
            MessageClassification with type and confidence
        """
        if not content or not content.strip():
            return MessageClassification(
                message_type=MessageType.CHAT,
                confidence=1.0,
                keywords=[],
                reasoning="Empty message classified as chat",
                metadata={"empty": True}
            )
        
        # Normalize content
        content_lower = content.lower().strip()
        
        # System messages are easy to identify
        if role == "system":
            return MessageClassification(
                message_type=MessageType.SYSTEM,
                confidence=1.0,
                keywords=["system"],
                reasoning="System role message",
                metadata={"role": "system"}
            )
        
        # Apply pattern matching
        fact_score, fact_keywords = self._score_patterns(content_lower, self._fact_patterns)
        preference_score, preference_keywords = self._score_patterns(content_lower, self._preference_patterns)
        task_score, task_keywords = self._score_patterns(content_lower, self._task_result_patterns)
        system_score, system_keywords = self._score_patterns(content_lower, self._system_patterns)
        noise_score, noise_keywords = self._score_patterns(content_lower, self._noise_patterns)
        
        # Determine classification
        scores = [
            (MessageType.FACT, fact_score, fact_keywords),
            (MessageType.PREFERENCE, preference_score, preference_keywords),
            (MessageType.TASK_RESULT, task_score, task_keywords),
            (MessageType.SYSTEM, system_score, system_keywords),
            (MessageType.NOISE, noise_score, noise_keywords),
        ]
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get best match
        best_type, best_score, best_keywords = scores[0]
        
        # If no patterns match strongly, classify as chat
        if best_score < 0.3:
            return MessageClassification(
                message_type=MessageType.CHAT,
                confidence=1.0 - best_score,
                keywords=[],
                reasoning="No strong pattern match, classified as chat",
                metadata={"pattern_score": best_score}
            )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(best_type, best_score, best_keywords, content)
        
        return MessageClassification(
            message_type=best_type,
            confidence=best_score,
            keywords=best_keywords,
            reasoning=reasoning,
            metadata={
                "pattern_score": best_score,
                "all_scores": {score[0].value: score[1] for score in scores}
            }
        )
    
    def _score_patterns(self, content: str, patterns: List[str]) -> tuple[float, List[str]]:
        """Score content against a list of regex patterns"""
        keywords = []
        matches = 0
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                matches += 1
                # Extract keywords from capture groups
                if match.groups():
                    for group in match.groups():
                        if group and len(group) > 2:  # Filter out short words
                            keywords.append(group.strip())
        
        # Normalize score (0.0 to 1.0)
        score = min(matches / len(patterns), 1.0)
        return score, keywords
    
    def _generate_reasoning(self, message_type: MessageType, score: float, keywords: List[str], content: str) -> str:
        """Generate human-readable reasoning for classification"""
        base_reasoning = f"Classified as {message_type.value} with confidence {score:.2f}"
        
        if keywords:
            keyword_str = ", ".join(keywords[:3])  # Show top 3 keywords
            return f"{base_reasoning}. Keywords: {keyword_str}"
        
        return base_reasoning
    
    async def classify_with_model(self, content: str, role: str) -> MessageClassification:
        """
        Use AI model to classify message (fallback for ambiguous cases)
        
        Args:
            content: Message content
            role: Message role
        
        Returns:
            MessageClassification from model
        """
        try:
            prompt = f"""Classify this message into one of these categories:
- CHAT: General conversation, questions, casual talk
- FACT: Statements about the user, their background, skills, or situation
- PREFERENCE: Likes, dislikes, wants, needs, opinions
- TASK_RESULT: Completed tasks, outputs, code, solutions
- SYSTEM: Technical, memory, context, or system-related

Message: "{content}"
Role: {role}

Respond with JSON:
{{
  "type": "CHAT|FACT|PREFERENCE|TASK_RESULT|SYSTEM",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}}"""

            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "gpt-3.5-turbo",
                "max_tokens": 200,
                "temperature": 0.1,
            }
            
            response = await invoke_provider(
                pid=None,
                model="gpt-3.5-turbo",
                payload=payload,
                timeout_ms=15000,
                stream=False,
            )
            
            if isinstance(response, dict) and response.get("ok"):
                result_text = response["result"]["text"]
                # Parse JSON response
                import json
                result = json.loads(result_text)
                
                return MessageClassification(
                    message_type=MessageType(result["type"]),
                    confidence=result["confidence"],
                    keywords=[],  # Model doesn't provide keywords
                    reasoning=result["reasoning"],
                    metadata={"model_classification": True}
                )
            
        except Exception as e:
            print(f"Model classification failed: {e}")
        
        # Fallback to rule-based classification
        return self.classify_message(content, role)
    
    async def classify_message_async(self, content: str, role: str, use_model: bool = False) -> MessageClassification:
        """
        Async message classification with optional model assistance
        
        Args:
            content: Message content
            role: Message role
            use_model: Whether to use AI model for classification
        
        Returns:
            MessageClassification result
        """
        # First pass: rule-based classification
        classification = self.classify_message(content, role)
        
        # If confidence is low and model assistance is requested, use AI
        if use_model and classification.confidence < 0.7:
            model_classification = await self.classify_with_model(content, role)
            
            # Use model result if it has higher confidence
            if model_classification.confidence > classification.confidence:
                return model_classification
        
        return classification


class ClassificationPipeline:
    """Pipeline for processing message classification"""
    
    def __init__(self):
        self.classifier = MessageClassifier()
    
    async def process_message(
        self, 
        message_id: str, 
        content: str, 
        role: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a message through the classification pipeline
        
        Args:
            message_id: ID of the message
            content: Message content
            role: Message role
            conversation_id: Optional conversation ID
            user_id: Optional user ID
        
        Returns:
            Classification result with metadata
        """
        # Classify the message
        classification = await self.classifier.classify_message_async(
            content=content,
            role=role,
            use_model=True  # Use model for higher accuracy
        )
        
        # Build classification result
        result = {
            "message_id": message_id,
            "classification": {
                "type": classification.message_type.value,
                "confidence": classification.confidence,
                "keywords": classification.keywords,
                "reasoning": classification.reasoning,
            },
            "metadata": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat(),
                "classification_source": "model" if classification.metadata.get("model_classification") else "rule_based",
            },
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        }
        
        # Store classification metadata (optional - for analytics)
        await self._store_classification_metadata(result)
        
        return result
    
    async def _store_classification_metadata(self, result: Dict[str, Any]):
        """Store classification metadata for analytics (optional)"""
        try:
            # This could be stored in a separate table for analytics
            # For now, we'll just log it
            print(f"Classification: {result['classification']['type']} "
                  f"(confidence: {result['classification']['confidence']:.2f}) "
                  f"for message {result['message_id']}")
        except Exception as e:
            print(f"Failed to store classification metadata: {e}")


# Global classifier instance
message_classifier = MessageClassifier()
classification_pipeline = ClassificationPipeline()