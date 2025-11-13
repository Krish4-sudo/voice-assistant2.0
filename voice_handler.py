import asyncio
import threading
import queue
import tempfile
import os
import subprocess
import signal
import speech_recognition as sr
import edge_tts

class VoiceHandler:
    def __init__(self):
        # Speech recognition setup
        self.recognizer = sr.Recognizer()
        # self.recognizer.pause_threshold = 1
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
        self.playback_process = None

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
            
            # Start ffplay as subprocess so we can kill it
            self.playback_process = subprocess.Popen(
                f"ffplay -nodisp -autoexit -loglevel quiet {output_path}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            
            # Wait for playback to finish, but check stop flag
            while self.playback_process.poll() is None:
                if self.stop_flag:
                    # Kill the process group
                    try:
                        os.killpg(os.getpgid(self.playback_process.pid), signal.SIGTERM)
                    except:
                        pass
                    break
                threading.Event().wait(0.1)
            
            # Cleanup
            try:
                os.remove(output_path)
            except:
                pass
                
        except Exception as e:
            print(f"TTS error: {e}")

    def _run_tts_worker(self):
        """Background thread for speaking text from the queue"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                if not text or text == "":
                    continue
                    
                self.is_speaking = True
                self.stop_flag = False
                print(f"Speaking: {text}")
                loop.run_until_complete(self._speak_async(text))
                self.is_speaking = False
                self.stop_flag = False
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Worker error: {e}")
                self.is_speaking = False
                self.stop_flag = False

    def speak(self, text: str):
        """Queue text to be spoken"""
        if not text or text.strip() == "":
            return
        self.speech_queue.put(text.strip())

    def speak_stream(self, stream_generator, min_chunk_size: int = 30):
        """
        Handle streaming response from model
        Buffers chunks before sending to TTS for natural speech
        
        Usage:
            voice_handler.speak_stream(model_stream_generator)
        """
        buffer = ""
        
        try:
            for chunk in stream_generator:
                if not chunk or self.stop_flag:
                    break
                
                buffer += chunk
                
                # Send to TTS when buffer reaches minimum size or ends with sentence
                if len(buffer) >= min_chunk_size or buffer.endswith(('.', '!', '?', '\n')):
                    if buffer.strip():
                        self.speak(buffer.strip())
                    buffer = ""
            
            # Send remaining buffer
            if buffer.strip():
                self.speak(buffer.strip())
                
        except Exception as e:
            print(f"Stream processing error: {e}")

    # -----------------------
    #  Speech Recognition
    # -----------------------
    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        """Listen and recognize speech using Google API"""
        try:
            # Stop any ongoing speech immediately
            if self.is_speaking:
                self.stop_flag = True
                print("(Agent interrupted)")
                # Wait for audio to actually stop
                threading.Event().wait(0.5)
            
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
        finally:
            # Reset stop flag after listening is done
            self.stop_flag = False

    def stop(self):
        """Stop the background threads"""
        self.stop_flag = True
        self.is_speaking = False
        
        # Kill playback process if running
        if self.playback_process and self.playback_process.poll() is None:
            try:
                os.killpg(os.getpgid(self.playback_process.pid), signal.SIGTERM)
            except:
                pass