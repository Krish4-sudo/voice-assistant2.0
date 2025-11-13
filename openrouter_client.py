import os
from openai import OpenAI
from conversation_manager import ConversationManager

class OpenRouterClient:
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.conversation_manager = ConversationManager(max_history=10)
        
        # Initialize with system prompt
        self.system_prompt = """You are a helpful, friendly, and human-like voice assistant. 
        Your responses should be natural, conversational, and suitable for speech synthesis.
        Keep responses concise but engaging. Use natural pauses and conversational fillers when appropriate.
        Be empathetic and adapt to the user's tone and mood."""
        
        # Add initial system message
        self.conversation_manager.add_message("system", self.system_prompt)
    
    def generate_response_stream(self, user_input: str, model: str = "anthropic/claude-3.5-sonnet"):
        """Generate response using OpenRouter API with streaming - yields chunks in real-time"""
        
        # Add user message to history
        self.conversation_manager.add_message("user", user_input)
        
        try:
            # Get conversation context including system message
            messages = self.conversation_manager.get_conversation_context()
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=100,
                stream=True,
                temperature=0.7,
                top_p=0.9,
            )
            
            full_response = ""
            
            # Iterate through the stream and yield each chunk
            for chunk in response:
                # Check if chunk has choices and delta
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # Extract content if it exists
                    if hasattr(delta, 'content') and delta.content is not None:
                        content = delta.content
                        full_response += content
                        yield content  # Yield immediately for real-time TTS
            
            # Add complete response to history
            if full_response:
                self.conversation_manager.add_message("assistant", full_response)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            self.conversation_manager.add_message("assistant", error_msg)
            yield error_msg
    
    def generate_response(self, user_input: str, model: str = "anthropic/claude-3.5-sonnet") -> str:
        """Generate complete response (non-streaming) - waits for full response"""
        
        # Add user message to history
        self.conversation_manager.add_message("user", user_input)
        
        try:
            # Get conversation context including system message
            messages = self.conversation_manager.get_conversation_context()
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=100,
                stream=False,  # Non-streaming
                temperature=0.7,
                top_p=0.9,
            )
            
            assistant_response = response.choices[0].message.content.strip()
            
            # Add assistant response to history
            self.conversation_manager.add_message("assistant", assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"
            self.conversation_manager.add_message("assistant", error_msg)
            return error_msg
    
    def get_conversation_history(self):
        """Get the complete conversation history"""
        return self.conversation_manager.get_full_conversation()
    
    def clear_conversation(self):
        """Clear conversation history (keeping system prompt)"""
        self.conversation_manager.clear_history()
        # Re-add system prompt
        self.conversation_manager.add_message("system", self.system_prompt)