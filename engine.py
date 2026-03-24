import time
import os
import base64
import whisper
import torch
from queue import Queue
from threading import Thread
from deep_translator import GoogleTranslator

# 1. Global Hardware Auto-Detect
device = "cuda" if torch.cuda.is_available() else "cpu"
if torch.backends.mps.is_available(): 
    device = "mps" 

class TranslationEngine:
    def __init__(self):
        print(f"🚀 Loading Whisper-Tiny on {device} for Max Speed...")
        # Use the auto-detected device here
        self.model = whisper.load_model("tiny", device=device)
        self.audio_stack = Queue()
        self.results = {}
        print(f"✅ Engine Ready on {device}!")

    def start_worker(self):
        t = Thread(target=self._process_audio, daemon=True)
        t.start()

    def _process_audio(self):
        while True:
            # Getting data from the queue
            item = self.audio_stack.get()
            if item is None: break
            
            tenant_id, chunk_id, audio_b64 = item
            temp_filename = f"temp_{chunk_id}.webm"
            
            try:
                # 1. Decode and Save Temp File
                with open(temp_filename, "wb") as f:
                    f.write(base64.b64decode(audio_b64))

                # 2. Transcribe (Optimized)
                # fp16=False is essential for CPU stability
                result = self.model.transcribe(temp_filename, fp16=False, language='en')
                transcript = result.get("text", "").strip()

                # 3. Store Result
                if tenant_id not in self.results:
                    self.results[tenant_id] = {}
                self.results[tenant_id][chunk_id] = transcript

            except Exception as e:
                print(f"❌ Engine Error: {e}")
            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
            
            self.audio_stack.task_done()

    def translate_text(self, text, target_lang):
        try:
            return GoogleTranslator(source='auto', target=target_lang).translate(text)
        except Exception as e:
            return f"Error: {e}"