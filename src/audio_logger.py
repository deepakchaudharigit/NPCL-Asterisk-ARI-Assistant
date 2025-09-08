import os
from gtts import gTTS
from pydub import AudioSegment
from datetime import datetime

def save_conversation_audio(question: str, answer: str, save_dir: str = "./sounds/en"):
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    q_base = os.path.join(save_dir, f"user_{timestamp}")
    a_base = os.path.join(save_dir, f"bot_{timestamp}")

    # Save question
    q_tts = gTTS(question)
    q_tts.save(f"{q_base}.mp3")
    AudioSegment.from_mp3(f"{q_base}.mp3").export(f"{q_base}.wav", format="wav")
    os.remove(f"{q_base}.mp3")

    # Save answer
    a_tts = gTTS(answer)
    a_tts.save(f"{a_base}.mp3")
    AudioSegment.from_mp3(f"{a_base}.mp3").export(f"{a_base}.wav", format="wav")
    os.remove(f"{a_base}.mp3")

    return f"{q_base}.wav", f"{a_base}.wav"
