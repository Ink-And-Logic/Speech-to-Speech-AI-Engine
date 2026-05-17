import time
import os
import base64
import whisper
import torch
import threading
from queue import Queue
from threading import Thread, Lock
from deep_translator import GoogleTranslator

# 1. Global Hardware Auto-Detect
device = "cuda" if torch.cuda.is_available() else "cpu"
if torch.backends.mps.is_available(): 
    device = "mps" 

class TranslationEngine:
    def __init__(self):
        print(f"🚀 Loading Whisper-Tiny on {device} for Max Speed...")
        # Use the auto-detected device
        self.model = whisper.load_model("tiny", device=device)
        self.audio_stack = Queue()
        self.results = {}
        self.results_lock = Lock() # Pro Move: Thread safety for the results dict
        print(f"✅ Engine Ready on {device}!")

    def start_worker(self):
        t = Thread(target=self._process_audio, daemon=True)
        t.start()

    def _process_audio(self):
        while True:
            item = self.audio_stack.get()
            if item is None: break
            
            tenant_id, chunk_id, audio_b64 = item
            # Create a unique temp file in a dedicated temp folder if possible
            temp_filename = f"audio_chunk_{chunk_id}.webm"
            
            try:
                # 1. Decode and Save Temp File
                with open(temp_filename, "wb") as f:
                    f.write(base64.b64decode(audio_b64))

                # 2. Transcribe (Optimized for Stability)
                # fp16=False is essential for CPU; CUDA can handle True but False is safer for cross-platform
                result = self.model.transcribe(temp_filename, fp16=(device == "cuda"), language='en')
                transcript = result.get("text", "").strip()

                # 3. Store Result with Thread Lock
                with self.results_lock:
                    if tenant_id not in self.results:
                        self.results[tenant_id] = {}
                    self.results[tenant_id][chunk_id] = transcript

            except Exception as e:
                print(f"❌ Engine Error during transcription: {e}")
            finally:
                # Ensure the file is deleted immediately to save disk space
                if os.path.exists(temp_filename):
                    try:
                        os.remove(temp_filename)
                    except Exception as e:
                        print(f"⚠️ Could not delete {temp_filename}: {e}")
            
            self.audio_stack.task_done()

    def translate_text(self, text, target_lang):
        if not text:
            return ""
        try:
            # Optimized translation call
            return GoogleTranslator(source='auto', target=target_lang).translate(text)
        except Exception as e:
            print(f"❌ Translation Error: {e}")
            return text # Return original text if translation fails
