from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
from engine import TranslationEngine # Importing your logic from Step 2

app = Flask(__name__)
CORS(app)

# Create ONE instance of our engine
translator_ai = TranslationEngine()
translator_ai.start_worker() # Start the background thread immediately

@app.route('/transcribe', methods=['POST'])
def handle_transcribe():
    # 1. Get the data
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    audio_b64 = data.get('audio_b64')
    # Use .get() with a fallback so it never crashes with a KeyError again
    chunk_id = data.get('chunk_id', str(int(time.time()))) 
    tenant_id = data.get('tenant_id', '0000')
    target_lang = data.get('target_lang', 'hi')

    if not audio_b64:
        return jsonify({"status": "error", "message": "Missing audio data"}), 400

    # 2. Hand off the work to the engine
    translator_ai.audio_stack.put((tenant_id, chunk_id, audio_b64))

    # 3. Wait for the engine to finish (Optimized Wait loop)
    max_retries = 50  # 50 * 0.1 = 5 seconds total max wait
    transcript = ""
    for _ in range(max_retries):
        time.sleep(0.1)  # Check every 100ms instead of every 1000ms!
        
        # Check the engine's results dictionary
        results_for_tenant = translator_ai.results.get(tenant_id, {})
        transcript = results_for_tenant.get(chunk_id, "")
        
        if transcript:
            # Clean up the results dictionary to save memory
            if chunk_id in results_for_tenant:
                del results_for_tenant[chunk_id]
            break

    # 4. Use the engine's translation tool
    translated_text = ""
    if transcript:
        translated_text = translator_ai.translate_text(transcript, target_lang)

    return jsonify({
        "status": "success",
        "transcript": transcript,
        "translation": translated_text,
        "chunk_id": chunk_id
    }), 200

if __name__ == '__main__':
    app.run(port=8888, debug=True)