#!/usr/bin/env python3
"""
NPCL Voice Assistant - Main Entry Point
Unified version with fallback for import issues
"""

import sys
import os
import asyncio
import json
import base64
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("🤖 NPCL Voice Assistant")
    print("🎆 Powered by Gemini 2.5 Flash")
    print("=" * 70)

def check_api_key():
    """Check if API key is configured"""
    try:
        env_file = Path('.env')
        if not env_file.exists():
            print("❌ .env file not found")
            return False, None
        
        with open(env_file, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.strip().startswith('GOOGLE_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    if api_key and api_key != 'your-google-api-key-here':
                        print("✅ Google API Key: Configured")
                        return True, api_key
            
        print("❌ Google API Key: Not configured properly")
        return False, None
    except Exception as e:
        print(f"❌ Error checking API key: {e}")
        return False, None

def print_system_status():
    """Print system status"""
    print("🔍 System Check:")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment: Active")
    else:
        print("⚠️  Virtual environment: Not detected")
    
    # Check API key
    api_key_valid, api_key = check_api_key()
    return api_key_valid, api_key

def print_mode_options():
    """Print mode selection options"""
    print("\n🎯 Choose Your Assistant Mode:")
    print("1. 💬 Chat Mode - Text-based conversation")
    print("2. 🎤 Voice Mode - Real-time voice conversation (Advanced)")
    print("3. 🎭 Combined Mode - Voice + Chat (Advanced)")
    print("4. ❌ Exit")
    print()

def get_user_choice():
    """Get user's mode choice"""
    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return 4
        except Exception:
            print("❌ Invalid input. Please enter a number.")

def get_npcl_system_instruction():
    """Get NPCL system instruction"""
    return """You are a customer service assistant for NPCL (Noida Power Corporation Limited), a power utility company.

Your role:
- Help customers with power connection inquiries
- Handle complaint registration and status updates
- Provide professional customer service
- Use polite Indian English communication style

When customers contact you:
1. Greet them professionally
2. Ask for their connection details or complaint number
3. Provide helpful information about their power service
4. Register new complaints if needed
5. Give status updates on existing complaints

Communication style:
- Be respectful and use "Sir" or "Madam"
- Use Indian English phrases naturally
- Speak clearly and be helpful
- Keep responses concise and professional

Sample complaint number format: 0000054321
Always be ready to help with power-related issues."""

def start_simple_chat_mode(api_key):
    """Start simple chat mode using direct Gemini API"""
    print("\n💬 Starting Chat Mode...")
    print("Type your messages below. Type 'quit' to exit.")
    print("-" * 50)
    
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # NPCL system prompt
        system_prompt = get_npcl_system_instruction()
        
        # Initial greeting
        initial_response = model.generate_content(system_prompt + "\n\nUser: Hello, I need help with my power connection\nAssistant:")
        print(f"🤖 NPCL Assistant: {initial_response.text}")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print("👋 Thank you for contacting NPCL. Have a great day!")
                    break
                
                if not user_input:
                    continue
                
                # Get AI response
                prompt = f"{system_prompt}\n\nUser: {user_input}\nAssistant:"
                response = model.generate_content(prompt)
                print(f"🤖 NPCL Assistant: {response.text}")
                
            except KeyboardInterrupt:
                print("\n👋 Chat session ended.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Failed to initialize chat: {e}")
        print("\n💡 Make sure you have:")
        print("1. Valid Google API key in .env file")
        print("2. Internet connection")
        print("3. google-generativeai package installed")

# Advanced mode classes and functions (with import protection)
class NPCLAssistant:
    """NPCL Assistant with multiple modes"""
    
    def __init__(self):
        try:
            from voice_assistant.utils.logger import setup_logger
            from config.settings import get_settings
            
            self.settings = get_settings()
            self.logger = setup_logger()
        except ImportError as e:
            print(f"⚠️  Advanced features unavailable due to import error: {e}")
            print("🔄 Falling back to simple mode...")
            raise
        
        self.ws = None
        self.running = False
        self.setup_complete = False
        self.is_listening = False
        self.is_speaking = False
        self.audio_chunks_received = 0
        
        # NPCL specific data
        self.names = ["dheeraj", "nidhi", "nikunj"]
        self.complaint_number = "0000054321"
        self.session_active = False
        
    def get_npcl_system_instruction(self):
        """Get NPCL system instruction"""
        return get_npcl_system_instruction()

    async def start_voice_mode(self):
        """Start voice-only mode with WebSocket"""
        print("\n🎤 Starting Voice Mode...")
        print("🔊 Make sure your microphone and speakers are working!")
        print("💡 Say 'quit' or press Ctrl+C to exit voice mode")
        print("-" * 50)
        
        try:
            # Check quota first
            if not await self.check_api_quota():
                print("❌ API quota exceeded. Falling back to chat mode.")
                await self.start_chat_mode()
                return
                
            await self.start_websocket_connection()
            
        except Exception as e:
            self.logger.error(f"Voice mode error: {e}")
            error_msg = str(e)
            
            if "Unsupported language code" in error_msg:
                print("❌ Voice mode failed: Unsupported language configuration")
                print("💡 The Gemini Live API has limited language support")
            elif "Live API not available" in error_msg:
                print("❌ Voice mode failed: Gemini Live API not available")
                print("💡 Live API is in limited preview - not available for all users")
            else:
                print(f"❌ Voice mode failed: {e}")
            
            print("🔄 Falling back to chat mode...")
            await self.start_chat_mode()

    async def start_chat_mode(self):
        """Start chat-only mode"""
        print("\n💬 Starting Advanced Chat Mode...")
        print("Type your messages below. Type 'quit' to exit.")
        print("-" * 50)
        
        try:
            from voice_assistant.ai.gemini_client import GeminiClient
            
            # Initialize chat client
            client = GeminiClient()
            
            # Send initial NPCL greeting with system instruction
            system_prompt = self.get_npcl_system_instruction()
            initial_response = client.generate_response("Hello, I need help with my power connection", system_prompt)
            print(f"🤖 NPCL Assistant: {initial_response}")
            
            while True:
                try:
                    user_input = input("\n👤 You: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                        print("👋 Thank you for contacting NPCL. Have a great day!")
                        break
                    
                    if not user_input:
                        continue
                    
                    # Get AI response with NPCL context
                    response = client.generate_response(user_input, system_prompt)
                    print(f"🤖 NPCL Assistant: {response}")
                    
                except KeyboardInterrupt:
                    print("\n👋 Chat session ended.")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Chat mode error: {e}")
            print(f"❌ Advanced chat mode failed: {e}")
            print("🔄 Falling back to simple chat mode...")
            # Fall back to simple chat
            api_key_valid, api_key = check_api_key()
            if api_key_valid:
                start_simple_chat_mode(api_key)

    async def start_both_mode(self):
        """Start combined voice + chat mode"""
        print("\n🎭 Starting Combined Mode...")
        print("🎤 Voice commands will be processed in real-time")
        print("💬 You can also type messages")
        print("Press 'v' for voice, 't' for text, 'q' to quit")
        
        try:
            # Check quota first
            voice_available = await self.check_api_quota()
            
            if voice_available:
                print("✅ Voice mode available")
            else:
                print("⚠️  Voice mode unavailable (quota exceeded), text only")
            
            from voice_assistant.ai.gemini_client import GeminiClient
            client = GeminiClient()
            
            # Send initial greeting with NPCL context
            system_prompt = self.get_npcl_system_instruction()
            initial_response = client.generate_response("Hello, I need help with my power connection", system_prompt)
            print(f"🤖 NPCL Assistant: {initial_response}")
            
            while True:
                try:
                    mode_choice = input("\n[V]oice, [T]ext, or [Q]uit: ").strip().lower()
                    
                    if mode_choice in ['q', 'quit', 'exit']:
                        print("👋 Thank you for contacting NPCL!")
                        break
                    elif mode_choice in ['v', 'voice'] and voice_available:
                        print("🎤 Speak now... (implementing voice capture)")
                        # Here you would implement voice capture
                        print("⚠️  Voice capture not implemented in this demo")
                    elif mode_choice in ['t', 'text']:
                        user_input = input("👤 Type your message: ").strip()
                        if user_input:
                            response = client.generate_response(user_input, system_prompt)
                            print(f"🤖 NPCL Assistant: {response}")
                    else:
                        print("❌ Invalid choice or voice unavailable")
                        
                except KeyboardInterrupt:
                    print("\n👋 Session ended.")
                    break
                    
        except Exception as e:
            self.logger.error(f"Combined mode error: {e}")
            print(f"❌ Combined mode failed: {e}")

    async def check_api_quota(self):
        """Check if API quota is available"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.settings.google_api_key)
            model = genai.GenerativeModel(self.settings.gemini_model)
            
            # Try a simple request
            response = model.generate_content("test")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "exceeded" in error_str:
                return False
            return True

    async def start_websocket_connection(self):
        """Start WebSocket connection for voice mode"""
        try:
            import websockets
            
            ws_url = f"{self.settings.gemini_live_api_endpoint}?key={self.settings.google_api_key}"
            
            self.ws = await websockets.connect(ws_url)
            print("🔗 Connecting to Gemini Live API...")
            
            # Setup message
            setup_message = {
                "setup": {
                    "model": f"models/{self.settings.gemini_live_model}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "temperature": 0.2,
                        "maxOutputTokens": 256,
                        "speechConfig": {
                            "languageCode": "en-US",
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": self.settings.gemini_voice}
                            },
                        },
                    },
                    "system_instruction": {"parts": [{"text": self.get_npcl_system_instruction()}]},
                }
            }
            
            await self.ws.send(json.dumps(setup_message))
            print("⚙️  Configuring voice settings...")
            
            # Handle messages with timeout and graceful exit
            try:
                # Create a task for message handling
                message_task = asyncio.create_task(self.handle_websocket_messages())
                
                # Create a task for user input handling
                input_task = asyncio.create_task(self.handle_user_input())
                
                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [message_task, input_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
            except KeyboardInterrupt:
                print("\n👋 Voice session ended")
                if self.ws:
                    await self.ws.close()
            except asyncio.CancelledError:
                print("\n👋 Voice session cancelled")
                if self.ws:
                    await self.ws.close()
            
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                raise Exception("API quota exceeded or Live API not available")
            else:
                raise Exception(f"WebSocket connection failed: {e}")
        except websockets.exceptions.ConnectionClosedError as e:
            if "Unsupported language code" in str(e):
                raise Exception(f"Unsupported language code 'en-US' for model {self.settings.gemini_live_model}")
            else:
                raise Exception(f"WebSocket connection closed: {e}")
        except Exception as e:
            if "Unsupported language code" in str(e):
                raise Exception(f"Unsupported language code for Gemini Live API: {e}")
            else:
                raise Exception(f"WebSocket error: {e}")

    async def handle_websocket_messages(self):
        """Handle WebSocket messages"""
        try:
            # Show initial status
            print("\n🔄 Initializing voice conversation...")
            conversation_started = False
            
            async for message in self.ws:
                response = json.loads(message)
                
                if "setupComplete" in response:
                    print("\r✅ Voice connection established")
                    print("🎤 Ready to start conversation...")
                    self.setup_complete = True
                    self.is_listening = True
                    await self.send_trigger_message()
                    conversation_started = True
                    
                elif response.get("serverContent"):
                    await self.handle_server_content(response["serverContent"])
                    
                # Add a small delay to prevent overwhelming the terminal
                await asyncio.sleep(0.01)
                
                # Keep the conversation alive
                if conversation_started and self.setup_complete:
                    # Continue processing messages until user interrupts
                    continue
                    
        except KeyboardInterrupt:
            print("\n👋 Voice session ended by user")
            if self.ws:
                await self.ws.close()
        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 Connection closed by server")
        except Exception as e:
            if "Unsupported language code" in str(e):
                self.logger.error(f"Language code not supported: {e}")
                raise Exception(f"Unsupported language code for Gemini Live API")
            else:
                self.logger.error(f"WebSocket message error: {e}")
                print(f"\n❌ Voice session error: {e}")

    async def send_trigger_message(self):
        """Send trigger message to start conversation"""
        trigger_message = {
            "clientContent": {
                "turns": [{"role": "user", "parts": [{"text": "Hello, I am calling NPCL customer service. Please greet me and ask how you can help with my power connection."}]}],
                "turnComplete": True,
            }
        }
        await self.ws.send(json.dumps(trigger_message))
        print("\r🤖 Starting NPCL conversation...", end="", flush=True)
        
    async def send_keep_alive(self):
        """Send keep-alive message to maintain session"""
        try:
            # Mark session as active
            self.session_active = True
            
            # In a real implementation, this would:
            # - Monitor microphone for voice input
            # - Send audio data when user speaks
            # - Handle voice activity detection
            # - Process "quit" voice commands
            
            # For now, just maintain the connection
            self.logger.debug("Voice session is active and ready for input")
            
        except Exception as e:
            self.logger.debug(f"Keep-alive error: {e}")

    async def handle_server_content(self, server_content):
        """Handle server content"""
        if server_content.get("modelTurn"):
            model_turn = server_content["modelTurn"]
            
            if model_turn.get("parts"):
                # Check if this is the start of a response
                if not self.is_speaking:
                    print("\r🤖 NPCL Assistant is responding...", end="", flush=True)
                    self.is_speaking = True
                    self.is_listening = False
                    self.audio_chunks_received = 0
                
                for part in model_turn["parts"]:
                    if part.get("inlineData") and "audio/pcm" in part["inlineData"].get("mimeType", ""):
                        await self.handle_audio_response(part["inlineData"])
                    elif part.get("text"):
                        # If there's text content, show it
                        text_content = part["text"]
                        if text_content.strip():
                            print(f"\n🤖 NPCL Assistant: {text_content}")
                        
            # Check if turn is complete
            if model_turn.get("turnComplete", False):
                if self.is_speaking:
                    print("\n🎤 Listening... (speak now or say 'quit' to exit)")
                    print("💡 Voice conversation is active - speak to continue")
                    print("🎙️  In a real implementation, your microphone would be active now")
                    self.is_speaking = False
                    self.is_listening = True
                    
                    # Keep the session alive by sending a keep-alive message
                    await self.send_keep_alive()

    async def handle_audio_response(self, inline_data):
        """Handle audio response"""
        pcm_chunk = base64.b64decode(inline_data["data"])
        self.audio_chunks_received += 1
        
        # Only log occasionally to avoid spam (and only in debug mode)
        if self.audio_chunks_received % 20 == 1:  # Log every 20th chunk
            self.logger.debug(f"Processing audio chunk {self.audio_chunks_received} ({len(pcm_chunk)} bytes)")
            
        # Show a simple progress indicator for audio processing
        if self.audio_chunks_received % 5 == 0:  # Update every 5 chunks
            dots = "..." if (self.audio_chunks_received // 5) % 3 == 0 else "." * ((self.audio_chunks_received // 5) % 3 + 1)
            print(f"\r🤖 NPCL Assistant is responding{dots}", end="", flush=True)
        
        # Simulate audio playback
        if self.audio_chunks_received == 1:
            print("\n🔊 Playing welcome message...")
        
        # Here you would play the audio
        # For now, we simulate audio playback
        # In a real implementation, you would:
        # - Convert PCM to playable format (WAV, MP3, etc.)
        # - Use audio library (pygame, pyaudio, etc.) to play through speakers
        # - Handle audio buffering and synchronization
        # - Manage audio device selection
        
        # Simulate audio processing delay
        await asyncio.sleep(0.01)
        
    async def handle_user_input(self):
        """Handle user input during voice session"""
        try:
            print("\n💡 Voice session active. Press Enter to continue or type 'quit' to exit.")
            
            while True:
                # Use asyncio to handle input without blocking
                try:
                    # Simulate waiting for user input
                    await asyncio.sleep(1)
                    
                    # In a real implementation, you would:
                    # - Capture microphone input
                    # - Process voice commands
                    # - Send audio data to Gemini Live API
                    # - Handle voice activity detection
                    
                    # For now, just keep the session alive
                    if not self.session_active:
                        self.session_active = True
                        print("\n🎤 Voice session is now active - speak to interact")
                        print("💡 In a real implementation, your voice would be captured here")
                        print("🔄 Session will continue until you press Ctrl+C")
                        
                        # Simulate a long-running voice session
                        await asyncio.sleep(30)  # Keep session alive for 30 seconds
                        
                        if self.session_active:
                            print("\n⏰ Voice session timeout - returning to menu")
                            break
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"User input error: {e}")
                    break
                    
        except KeyboardInterrupt:
            print("\n👋 Voice session ended by user")
        except Exception as e:
            self.logger.error(f"Input handling error: {e}")

def main():
    """Main application entry point"""
    print_banner()
    
    # Check system status
    api_key_valid, api_key = print_system_status()
    
    if not api_key_valid:
        print("\n❌ System check failed. Please fix the issues above.")
        print("\n💡 Quick fix:")
        print("1. Copy .env.example to .env")
        print("2. Get your Google API key from: https://aistudio.google.com/")
        print("3. Add your Google API key to .env file")
        return 1
    
    print("\n🎆 NPCL Features:")
    print("• Handles power connection inquiries")
    print("• Manages complaint numbers and status")
    print("• Indian English conversation style")
    print("• Real-time voice or text interaction")
    print("• Professional customer service experience")
    
    # Show mode options
    while True:
        print_mode_options()
        choice = get_user_choice()
        
        if choice == 4:  # Exit
            print("👋 Thank you for using NPCL Voice Assistant!")
            break
        
        try:
            if choice == 1:  # Chat Only (Simple mode first, advanced fallback)
                start_simple_chat_mode(api_key)
            elif choice in [2, 3]:  # Voice or Combined (Advanced modes)
                try:
                    # Try advanced mode
                    assistant = NPCLAssistant()
                    
                    if choice == 2:  # Voice Only
                        asyncio.run(assistant.start_voice_mode())
                    elif choice == 3:  # Both
                        asyncio.run(assistant.start_both_mode())
                        
                except ImportError:
                    print("⚠️  Advanced features not available. Using simple chat mode instead.")
                    start_simple_chat_mode(api_key)
                
        except KeyboardInterrupt:
            print("\n👋 Session interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔄 Falling back to simple chat mode...")
            start_simple_chat_mode(api_key)
        
        # Ask if user wants to try another mode
        try:
            again = input("\nWould you like to try another mode? (y/n): ").strip().lower()
            if again not in ['y', 'yes']:
                break
        except KeyboardInterrupt:
            break
    
    print("👋 Thank you for using NPCL Voice Assistant!")
    return 0

if __name__ == "__main__":
    sys.exit(main())