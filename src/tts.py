from gtts import gTTS
import os

# Use a relative folder for storing TTS audio (works on Windows)
ASTERISK_SOUNDS_DIR = os.path.abspath(os.path.join(os.getcwd(), "sounds", "en"))

def synthesize_speech(text: str) -> str:
    # Ensure the target folder exists
    os.makedirs(ASTERISK_SOUNDS_DIR, exist_ok=True)

    filename = "response_tts.wav"
    filepath = os.path.join(ASTERISK_SOUNDS_DIR, filename)

    # Generate the TTS audio
    tts = gTTS(text=text, lang='en')
    tts.save(filepath)

    print(f"✅ TTS saved to: {filepath}")
    return "en/response_tts"  # this is what ARI expects as 'sound:en/response_tts'
