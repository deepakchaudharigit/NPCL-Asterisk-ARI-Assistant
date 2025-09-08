# ari_handler.py
from fastapi import APIRouter, Body
from src.llm_agent import get_llm_response
from src.tts import synthesize_speech
from src.audio_processor import transcribe_audio
import requests
import os
from dotenv import load_dotenv
from src.models import AriEvent
from src.audio_logger import save_conversation_audio

load_dotenv()

router = APIRouter()

# ARI settings
ARI_BASE_URL = os.getenv("ARI_BASE_URL", "http://localhost:8088/ari")
ARI_USERNAME = os.getenv("ARI_USERNAME", "asterisk")
ARI_PASSWORD = os.getenv("ARI_PASSWORD", "1234")

active_playbacks = {}

@router.post("/events")
async def handle_ari_event(event: AriEvent = Body(...)):
    event_type = event.type
    channel_id = event.channel.id if event.channel else ""

    if event_type == "StasisStart":
        print(f"📞 Call started: {channel_id}")
        respond_to_user(channel_id, first_time=True)

    elif event_type == "ChannelTalkingStarted":
        playback_id = active_playbacks.get(channel_id)
        if playback_id:
            print(f"🛑 Caller started talking. Stopping playback {playback_id}.")
            try:
                requests.delete(f"{ARI_BASE_URL}/playbacks/{playback_id}", auth=(ARI_USERNAME, ARI_PASSWORD))
            except Exception as e:
                print(f"❌ Error stopping playback: {e}")

    elif event_type == "ChannelTalkingStopped":
        print("🤖 Caller stopped. Starting recording...")
        start_recording(channel_id)
        print("📥 Waiting for recorded file before transcribing...")
        # Wait a moment to allow file to be finalized (depends on Asterisk setup)
        import time; time.sleep(2)
        respond_to_user(channel_id)

    return {"status": "event received"}


@router.get("/tts-test")
def tts_test():
    try:
        from gtts import gTTS
        tts = gTTS("TTS test successful")
        tts.save("./sounds/en/tts-test.wav")
        return {"status": "success", "file": "tts-test.wav"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def respond_to_user(channel_id: str, first_time=False):
    try:
        if first_time:
            user_input = "Who discovered gravity?"
        else:
            user_input = transcribe_audio("./sounds/caller_input.wav")

        print(f"🧠 User input: {user_input}")

        response_text = get_llm_response(user_input)
        print(f"🤖 LLM response: {response_text}")

        audio_file = synthesize_speech(response_text)
        print(f"🔊 TTS saved as: {audio_file}")

        save_conversation_audio(user_input, response_text)
        
        play_url = f"{ARI_BASE_URL}/channels/{channel_id}/play"
        payload = {"media": f"sound:{audio_file}"}
        print(f"📡 Sending playback to {play_url} with {payload}")

        response = requests.post(play_url, auth=(ARI_USERNAME, ARI_PASSWORD), json=payload)

        if response.status_code == 404:
            print(f"❌ Channel not found: {channel_id}. Ensure this is a real Asterisk channel ID.")
            return

        response.raise_for_status()
        playback_id = response.json().get("id")
        active_playbacks[channel_id] = playback_id
        print(f"✅ Playback started: {audio_file} (id: {playback_id})")

    except requests.exceptions.RequestException as req_err:
        print(f"❌ Playback HTTP error: {req_err}")
    except Exception as e:
        print(f"🔥 Error in respond_to_user(): {e}")


def start_recording(channel_id: str):
    record_url = f"{ARI_BASE_URL}/channels/{channel_id}/record"
    record_options = {
        "name": "caller_input",  # file saved as caller_input.wav
        "format": "wav",
        "maxDurationSeconds": 10,
        "beep": False,
        "terminateOn": "#"
    }
    try:
        response = requests.post(
            record_url,
            auth=(ARI_USERNAME, ARI_PASSWORD),
            params=record_options
        )
        response.raise_for_status()
        print(f"🎙️ Started recording on channel {channel_id}")
    except Exception as e:
        print(f"❌ Error starting recording: {e}")
