import pyttsx3
import speech_recognition as sr
import threading
import queue
import time

class VoiceHandler:
    def __init__(self):
        # Text-to-Speech setup
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        
        # Speech-to-Text setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise
        print("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("Microphone calibrated!")
        
        # Queue for speech synthesis
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        
        # Start speech synthesis thread
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()
    
    def setup_tts(self):
        """Configure TTS settings for natural speech"""
        voices = self.tts_engine.getProperty('voices')
        if voices:
            # Use the first available voice (you can customize this)
            self.tts_engine.setProperty('voice', voices[5].id)
        
        # Set speech rate and volume
        self.tts_engine.setProperty('rate', 170)  # Words per minute
        self.tts_engine.setProperty('volume', 0.8)  # Volume level 0-1
    
    def speak(self, text: str):
        """Add text to speech queue"""
        self.speech_queue.put(text)
    
    def _speech_worker(self):
        """Background worker for speech synthesis"""
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                self.is_speaking = True
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self.is_speaking = False
                time.sleep(0.1)  # Small pause between speeches
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech synthesis error: {e}")
                self.is_speaking = False
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        """Listen for user speech and convert to text"""
        try:
            with self.microphone as source:
                print("Listening...")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
            
            print("Processing speech...")
            text = self.recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text.lower()
            
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand what you said.")
            return ""
        except sr.RequestError as e:
            print(f"Error with speech recognition service: {e}")
            return ""
    
    def stop_speaking(self):
        """Stop current speech"""
        self.tts_engine.stop()
        self.is_speaking = False