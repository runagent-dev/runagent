# File: runagent/agent_builder/conversation_memory.py

from typing import List, Dict, Any
from datetime import datetime


class ConversationMemory:
    """Manages conversation memory for the agent builder session"""
    
    def __init__(self, max_messages: int = 10):
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages
        self.session_start = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to conversation memory"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.messages.append(message)
        
        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in memory"""
        return self.messages.copy()
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for context"""
        if not self.messages:
            return ""
        
        summary_parts = []
        for msg in self.messages:
            role = msg['role']
            content = msg['content'][:200]  # Truncate long messages
            summary_parts.append(f"{role}: {content}")
        
        return "\n".join(summary_parts)
    
    def clear(self):
        """Clear conversation memory"""
        self.messages = []
        self.session_start = datetime.now()
    
    def get_session_duration(self) -> float:
        """Get session duration in minutes"""
        duration = datetime.now() - self.session_start
        return duration.total_seconds() / 60