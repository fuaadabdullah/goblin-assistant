"""
Mock provider that returns realistic AI responses for testing and development.
"""

from typing import AsyncGenerator, Dict, Any, Union, List
import asyncio
import random
from .base import BaseProvider


class MockProvider(BaseProvider):
    """Mock AI provider that generates realistic responses for testing."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "mock-gpt", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Generate a mock AI response."""
        
        # Simulate processing time
        processing_time = random.uniform(0.5, 2.0)
        await asyncio.sleep(processing_time)
        
        # Generate contextually appropriate responses based on the prompt
        response = self._generate_response(prompt, model)
        
        if stream:
            # Return streaming response
            async def gen():
                words = response.split()
                for i, word in enumerate(words):
                    await asyncio.sleep(0.1)  # Simulate streaming delay
                    yield {
                        "text": word + (" " if i < len(words) - 1 else ""),
                        "raw": {"delta": {"content": word + (" " if i < len(words) - 1 else "")}}
                    }
            
            return {"ok": True, "stream": gen(), "latency_ms": int(processing_time * 1000)}
        else:
            return {
                "ok": True,
                "result": {"text": response, "raw": {"model": model, "provider": "mock"}},
                "latency_ms": int(processing_time * 1000),
                "provider": "mock",
                "model": model
            }

    def _generate_response(self, prompt: str, model: str) -> str:
        """Generate a contextually appropriate response."""
        prompt_lower = prompt.lower()
        
        # AI/Technology related responses
        if any(word in prompt_lower for word in ["ai", "artificial intelligence", "machine learning", "neural network"]):
            return f"""I can explain AI concepts! Artificial Intelligence refers to computer systems designed to perform tasks that typically require human intelligence. Key aspects include:

**Machine Learning**: Systems that learn from data patterns
**Deep Learning**: Neural networks with multiple layers  
**Natural Language Processing**: Understanding human language
**Computer Vision**: Interpreting visual information

Current AI models like those I'm based on use transformer architectures with billions of parameters trained on vast datasets. They're particularly good at language tasks, code generation, and reasoning.

Is there a specific aspect of AI you'd like me to elaborate on?"""

        # Programming/Coding responses
        elif any(word in prompt_lower for word in ["code", "programming", "python", "javascript", "function", "bug", "debug"]):
            return f"""I can help with programming! As an AI assistant, I'm designed to understand code, debug issues, and suggest improvements.

**Programming Best Practices**:
- Write clean, readable code with good variable names
- Use proper error handling and validation
- Follow consistent formatting and style guides
- Write tests for your functions
- Document complex logic with comments

**Common Debugging Steps**:
1. Check error messages carefully
2. Use print statements or debugger
3. Test components individually  
4. Review recent changes
5. Check dependencies and versions

What specific programming challenge are you working on?"""

        # Questions about the system/chat
        elif any(word in prompt_lower for word in ["system", "how do you work", "what are you", "who are you"]):
            return f"""I'm an AI assistant designed to help with various tasks through conversation. I can assist with:

- Answering questions and providing explanations
- Helping with programming and technical problems
- Brainstorming ideas and creative tasks
- Writing, editing, and communication
- Analysis and research tasks

I process messages through natural language understanding and generate helpful responses based on my training. While I'm currently operating in a mock/test mode, I'm fully functional for testing the chat interface and demonstrating conversation capabilities.

What would you like to discuss?"""

        # Greeting responses
        elif any(word in prompt_lower for word in ["hello", "hi", "hey", "greetings"]):
            return f"""Hello! I'm an AI assistant ready to help you with various tasks. Whether you need answers to questions, help with programming, creative brainstorming, or just want to have an engaging conversation, I'm here to assist.

What can I help you with today?"""

        # Help/Assistance requests
        elif any(word in prompt_lower for word in ["help", "assist", "support", "explain", "how to"]):
            return f"""I'd be happy to help! I'm designed to assist with a wide range of topics and tasks.

**Areas I can help with**:
- Technical questions and problem-solving
- Programming and development guidance
- Writing and communication assistance
- Research and analysis
- Creative tasks and brainstorming
- Learning and education support

To get the best help, please describe your specific question or task, and I'll provide a detailed response tailored to your needs.

What would you like assistance with?"""

        # General conversation starter
        elif len(prompt.strip()) < 50:
            return f"""That's an interesting point! I'd love to hear more about your thoughts on this topic. Could you elaborate on what specific aspect interests you most?

I'm here to engage in thoughtful conversation and provide helpful insights. What would you like to explore further?"""

        # Default comprehensive response
        else:
            return f"""Thank you for your message about: "{prompt[:100]}{'...' if len(prompt) > 100 else ''}"

I appreciate the detailed question. Based on the content, I can see this covers several interesting areas. Let me address the key points:

**Main Points**:
- This appears to be a thoughtful question covering important concepts
- The topic involves multiple dimensions worth exploring
- A comprehensive response would cover various perspectives

**Key Insights**:
- Consider different approaches to this challenge
- Look at both practical and theoretical aspects
- Think about potential solutions and trade-offs

**Next Steps**:
- Break down complex parts into smaller questions
- Consider what specific information would be most helpful
- Think about practical applications or next steps

Is there a particular aspect of this topic you'd like me to focus on? I can provide more detailed information on specific areas that interest you most."""

    async def embed(self, texts: Union[str, List[str]], model: str = "mock-embed", **kwargs) -> Union[List[float], List[List[float]]]:
        """Generate mock embeddings."""
        # Return random vectors for testing
        dim = 384  # Common embedding dimension
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        embeddings = []
        for _ in texts:
            # Generate random vector
            embedding = [random.uniform(-1, 1) for _ in range(dim)]
            embeddings.append(embedding)
        
        return embeddings[0] if is_single else embeddings