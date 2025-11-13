import os
from dotenv import load_dotenv
from openrouter_client import OpenRouterClient
from voice_handler import VoiceHandler
import json

class VoiceAssistant:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("Please set OPENROUTER_API_KEY in your .env file")
        
        # Initialize components
        self.openrouter_client = OpenRouterClient(api_key)
        self.voice_handler = VoiceHandler()
        
        # Conversation settings
        self.is_listening = True
        
        print("Voice Assistant initialized!")
        print("Say 'hello' to start, 'goodbye' to exit, or 'clear' to reset conversation.")
    
    def run(self):
        """Main assistant loop"""
        # Initial greeting
        greeting = "Hello! I'm your voice assistant. How can I help you today?"
        print(f"Assistant: {greeting}")
        self.voice_handler.speak(greeting)
        
        while self.is_listening:
            try:
                # Listen for user input
                user_input = self.voice_handler.listen(timeout=10, phrase_time_limit=15)
                
                if not user_input:
                    continue
                
                # Check for exit command
                if any(phrase in user_input for phrase in ['goodbye', 'exit', 'quit', 'stop']):
                    farewell = "Goodbye! It was nice talking with you."
                    print(f"Assistant: {farewell}")
                    self.voice_handler.speak(farewell)
                    self.is_listening = False
                    break
                
                # Check for clear command
                if 'clear' in user_input or 'reset' in user_input:
                    self.openrouter_client.clear_conversation()
                    response = "Conversation history cleared. What would you like to talk about?"
                    print(f"Assistant: {response}")
                    self.voice_handler.speak(response)
                    continue
                
                # Check for history command
                if 'history' in user_input or 'show conversation' in user_input:
                    history = self.openrouter_client.get_conversation_history()
                    print("\n=== Conversation History ===")
                    for msg in history:
                        role = msg['role'].capitalize()
                        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                        print(f"{role}: {content}")
                    print("============================\n")
                    response = "I've printed our conversation history to the console."
                    self.voice_handler.speak(response)
                    continue
                
                # Generate response
                print(f"User: {user_input}")
                response = self.openrouter_client.generate_response(user_input)
                print(f"Assistant: {response}")
                
                # Speak the response
                self.voice_handler.speak(response)
                
            except KeyboardInterrupt:
                print("\nAssistant interrupted by user.")
                self.is_listening = False
                break
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                print(error_msg)
                self.voice_handler.speak("Sorry, I encountered an error. Please try again.")
        
        # Save conversation before exiting
        self.openrouter_client.conversation_manager.save_conversation()
        print("Conversation saved to conversation_history.json")

if __name__ == "__main__":
    try:
        assistant = VoiceAssistant()
        assistant.run()
    except Exception as e:
        print(f"Failed to start voice assistant: {e}")

