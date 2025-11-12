import json
import os
from datetime import datetime
from typing import List, Dict

class ConversationManager:
    def __init__(self, max_history=10):
        self.max_history = max_history
        self.conversation_history: List[Dict] = []
        
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.conversation_history.append(message)
        
        # Keep only the last max_history messages
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_conversation_context(self) -> List[Dict]:
        """Get formatted conversation history for API"""
        return [{"role": msg["role"], "content": msg["content"]} 
                for msg in self.conversation_history]
    
    def get_full_conversation(self) -> List[Dict]:
        """Get complete conversation history with timestamps"""
        return self.conversation_history.copy()
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
    
    def save_conversation(self, filename: str = "conversation_history.json"):
        """Save conversation to file"""
        with open(filename, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
    
    def load_conversation(self, filename: str = "conversation_history.json"):
        """Load conversation from file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                self.conversation_history = json.load(f)