import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file_path: str) -> str:
    try:
        with open(file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(model="whisper-1", file=audio_file)
            return response.get("text", "")
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return "Sorry, I couldn't understand the audio."
