import speech_recognition as sr
import openai
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define the path to save TTS output
ASTERISK_SOUNDS_DIR = os.path.abspath(os.path.join(os.getcwd(), "sounds", "en"))
RESPONSE_FILENAME = "response_tts.wav"
RESPONSE_FILEPATH = os.path.join(ASTERISK_SOUNDS_DIR, RESPONSE_FILENAME)
os.makedirs(ASTERISK_SOUNDS_DIR, exist_ok=True)

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Listening...")
        audio = recognizer.listen(source)
    try:
        query = recognizer.recognize_google(audio)
        print(f"🧠 You said: {query}")
        return query.lower().strip()
    except Exception as e:
        print("❌ Speech Recognition failed:", e)
        return None

def ask_ai(text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": text}]
    )
    reply = response.choices[0].message["content"]
    print("🤖 Assistant:", reply)
    return reply

def speak(text):
    tts = gTTS(text=text, lang='en')
    tts.save(RESPONSE_FILEPATH)
    audio = AudioSegment.from_file(RESPONSE_FILEPATH)
    play(audio)
    print(f"✅ TTS saved to: {RESPONSE_FILEPATH}")

if __name__ == "__main__":
    paused = False
    print("🟢 Voice assistant is now running. Say 'pause' to hold, 'resume' to continue, or 'quit' to exit.")

    while True:
        if paused:
            print("⏸️ Assistant paused. Say 'resume' to continue...")
            command = listen()
            if command and command in ["resume"]:
                paused = False
                print("▶️ Resumed.")
            elif command in ["quit", "exit", "stop"]:
                print("👋 Goodbye!")
                break
            continue

        query = listen()
        if not query:
            continue

        if query in ["quit", "exit", "stop"]:
            print("👋 Exiting assistant.")
            break
        elif query in ["pause", "hold on"]:
            paused = True
            print("⏸️ Paused.")
            continue

        reply = ask_ai(query)
        speak(reply)
