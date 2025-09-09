#!/usr/bin/env python3
"""
NPCL Voice Assistant - Main Entry Point
Provides 3 modes: Voice Only, Chat Only, or Both
"""

import sys
import os
import asyncio
import json
import base64
import time
import websockets
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from voice_assistant.utils.logger import setup_logger
from config.settings import get_settings

def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("🤖 NPCL Voice Assistant - Choose Your Mode")
    print("🎆 Powered by Gemini 2.5 Flash")
    print("=" * 70)

def print_mode_options():
    """Print mode selection options"""
    print("\n🎯 Choose Your Assistant Mode:")
    print("1. 🎤 Voice Only - Real-time voice conversation")
    print("2. 💬 Chat Only - Text-based conversation")
    print("3. 🎭 Both - Voice + Chat combined")
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

class NPCLAssistant:
    """NPCL Assistant with multiple modes"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger()
        self.ws = None
        self.running = False
        self.setup_complete = False
        
        # NPCL specific data
        self.names = ["dheeraj", "nidhi", "nikunj"]
        self.complaint_number = "0000054321"
        
    def get_npcl_system_instruction(self):
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

    async def start_voice_mode(self):
        """Start voice-only mode with WebSocket"""
        print("\n🎤 Starting Voice Mode...")
        print("🔊 Make sure your microphone and speakers are working!")
        
        try:
            # Check quota first
            if not await self.check_api_quota():
                print("❌ API quota exceeded. Falling back to chat mode.")
                await self.start_chat_mode()
                return
                
            await self.start_websocket_connection()
            
        except Exception as e:
            self.logger.error(f"Voice mode error: {e}")
            print(f"❌ Voice mode failed: {e}")
            print("🔄 Falling back to chat mode...")
            await self.start_chat_mode()

    async def start_chat_mode(self):
        """Start chat-only mode"""
        print("\n💬 Starting Chat Mode...")
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
            print(f"❌ Chat mode failed: {e}")

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
        ws_url = f"{self.settings.gemini_live_api_endpoint}?key={self.settings.google_api_key}"
        
        try:
            self.ws = await websockets.connect(ws_url)
            self.logger.info("WebSocket connection established")
            
            # Setup message
            setup_message = {
                "setup": {
                    "model": f"models/{self.settings.gemini_live_model}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "temperature": 0.2,
                        "maxOutputTokens": 256,
                        "speechConfig": {
                            "languageCode": "en-IN",
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": self.settings.gemini_voice}
                            },
                        },
                    },
                    "system_instruction": {"parts": [{"text": self.get_npcl_system_instruction()}]},
                }
            }
            
            await self.ws.send(json.dumps(setup_message))
            self.logger.info("Setup message sent")
            
            # Handle messages
            await self.handle_websocket_messages()
            
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                raise Exception("API quota exceeded or Live API not available")
            else:
                raise Exception(f"WebSocket connection failed: {e}")
        except Exception as e:
            raise Exception(f"WebSocket error: {e}")

    async def handle_websocket_messages(self):
        """Handle WebSocket messages"""
        try:
            async for message in self.ws:
                response = json.loads(message)
                
                if "setupComplete" in response:
                    self.logger.info("Setup complete")
                    self.setup_complete = True
                    await self.send_trigger_message()
                    
                elif response.get("serverContent"):
                    await self.handle_server_content(response["serverContent"])
                    
        except Exception as e:
            self.logger.error(f"WebSocket message error: {e}")

    async def send_trigger_message(self):
        """Send trigger message to start conversation"""
        trigger_message = {
            "clientContent": {
                "turns": [{"role": "user", "parts": [{"text": "hello"}]}],
                "turnComplete": True,
            }
        }
        await self.ws.send(json.dumps(trigger_message))
        self.logger.info("Trigger message sent")

    async def handle_server_content(self, server_content):
        """Handle server content"""
        if server_content.get("modelTurn"):
            model_turn = server_content["modelTurn"]
            
            if model_turn.get("parts"):
                for part in model_turn["parts"]:
                    if part.get("inlineData") and "audio/pcm" in part["inlineData"].get("mimeType", ""):
                        await self.handle_audio_response(part["inlineData"])

    async def handle_audio_response(self, inline_data):
        """Handle audio response"""
        pcm_chunk = base64.b64decode(inline_data["data"])
        self.logger.info(f"Received audio chunk: {len(pcm_chunk)} bytes")
        
        # Here you would play the audio
        print("🔊 Playing audio response...")

def print_system_status():
    """Print system status"""
    try:
        settings = get_settings()
        
        print("✅ System Information:")
        print(f"   Assistant: NPCL Voice Assistant")
        print(f"   AI Model: {settings.gemini_model}")
        print(f"   Voice: {settings.gemini_voice}")
        
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("✅ Virtual environment: Active")
        else:
            print("⚠️  Virtual environment: Not detected")
        
        # Check .env file
        if Path(".env").exists():
            print("✅ Configuration: .env file found")
        else:
            print("❌ Configuration: .env file not found")
            return False
        
        # Check API key
        if settings.google_api_key and settings.google_api_key != "your-google-api-key-here":
            print("✅ Google API Key: Configured")
            return True
        else:
            print("❌ Google API Key: Not configured")
            return False
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    """Main application entry point"""
    print_banner()
    
    # Check system status
    if not print_system_status():
        print("\n❌ System check failed. Please fix the issues above.")
        print("\n💡 Quick fix:")
        print("1. Copy .env.example to .env")
        print("2. Add your Google API key to .env")
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
        
        # Create assistant instance
        assistant = NPCLAssistant()
        
        try:
            if choice == 1:  # Voice Only
                asyncio.run(assistant.start_voice_mode())
            elif choice == 2:  # Chat Only
                asyncio.run(assistant.start_chat_mode())
            elif choice == 3:  # Both
                asyncio.run(assistant.start_both_mode())
                
        except KeyboardInterrupt:
            print("\n👋 Session interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        
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