from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
from engine import TranslationEngine

app = Flask(__name__)
CORS(app)

# Create ONE instance of our engine
translator_ai = TranslationEngine()
translator_ai.start_worker() # Start the background thread immediately

@app.route('/transcribe', methods=['POST'])
def handle_transcribe():
    # 1. Get the data safely
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    audio_b64 = data.get('audio_b64')
    # Use fallback values to prevent KeyError crashes
    chunk_id = data.get('chunk_id', str(int(time.time()))) 
    tenant_id = data.get('tenant_id', '0000')
    target_lang = data.get('target_lang', 'hi')

    if not audio_b64:
        return jsonify({"status": "error", "message": "Missing audio data"}), 400

    # 2. Hand off the work to the engine stack
    translator_ai.audio_stack.put((tenant_id, chunk_id, audio_b64))

    # 3. Wait for the engine to finish (Increased for Neural Inference)
    # 100 * 0.1 = 10 seconds total max wait to account for CPU-only environments
    max_retries = 100  
    transcript = ""
    
    for _ in range(max_retries):
        time.sleep(0.1)  # Check every 100ms
        
        # Check the engine's results dictionary
        results_for_tenant = translator_ai.results.get(tenant_id, {})
        transcript = results_for_tenant.get(chunk_id, "")
        
        if transcript:
            # Clean up memory immediately after retrieval
            if chunk_id in results_for_tenant:
                del results_for_tenant[chunk_id]
            break

    # 4. Use the engine's translation tool if transcription was successful
    translated_text = ""
    if transcript:
        translated_text = translator_ai.translate_text(transcript, target_lang)

    # Return the final results
    return jsonify({
        "status": "success",
        "transcript": transcript,
        "translation": translated_text,
        "chunk_id": chunk_id
    }), 200

if __name__ == '__main__':
    # Running on 8888 to keep it distinct from default Flask 5000
    app.run(host='0.0.0.0', port=8888, debug=True)
