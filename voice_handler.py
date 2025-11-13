import asyncio
import threading
import queue
import tempfile
import os
import speech_recognition as sr
import edge_tts

class VoiceHandler:
    def __init__(self):
        # Speech recognition setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise once
        print("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("Microphone calibrated!")

        # Queue for TTS
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.stop_flag = False

        # Start async TTS thread
        self.speech_thread = threading.Thread(target=self._run_tts_worker, daemon=True)
        self.speech_thread.start()

    # -----------------------
    #  Async TTS Handling
    # -----------------------
    async def _speak_async(self, text: str):
        """Speak text asynchronously using edge-tts"""
        try:
            communicate = edge_tts.Communicate(text, voice="en-US-JennyNeural", rate="+0%")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                output_path = tmp.name
            await communicate.save(output_path)
            os.system(f"ffplay -nodisp -autoexit -loglevel quiet {output_path}")
            os.remove(output_path)
        except Exception as e:
            print(f"TTS error: {e}")

    def _run_tts_worker(self):
        """Background thread for speaking text from the queue"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while not self.stop_flag:
            try:
                text = self.speech_queue.get(timeout=1)
                self.is_speaking = True
                loop.run_until_complete(self._speak_async(text))
                self.is_speaking = False
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Worker error: {e}")
                self.is_speaking = False

    def speak(self, text: str):
        """Queue text to be spoken"""
        if not text:
            return
        self.speech_queue.put(text)

    # -----------------------
    #  Speech Recognition
    # -----------------------
    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        """Listen and recognize speech using Google API"""
        try:
            with self.microphone as source:
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("Processing speech...")
            text = self.recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand that.")
            return ""
        except sr.RequestError as e:
            print(f"Speech recognition service error: {e}")
            return ""

    def stop(self):
        """Stop the background threads"""
        self.stop_flag = True
        self.is_speaking = False
