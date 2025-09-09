# 🤖 Voice Assistant with Gemini 2.5 Flash & Real-time Live API

A professional voice assistant system powered by Google's Gemini 2.5 Flash model, featuring both standalone voice interaction and **real-time telephony integration** with Asterisk ARI and Gemini Live API.

## ✨ What's New in Version 2.0

- **🔄 Migrated from OpenAI to Gemini 2.5 Flash**: More efficient and cost-effective AI responses
- **🎆 NEW: Real-time Gemini Live API Integration**: Direct voice-to-voice conversation with ultra-low latency
- **📡 NEW: Asterisk ARI with externalMedia**: Bidirectional audio streaming for telephony integration
- **🎤 NEW: Voice Activity Detection**: Intelligent interruption handling for natural conversations
- **🔊 NEW: slin16 Audio Format**: Optimized for Asterisk with 16-bit signed linear PCM at 16kHz
- **🏢 Professional Architecture**: Complete restructure with modular design
- **📦 Package Structure**: Proper Python package with clear separation of concerns
- **🔧 Enhanced Configuration**: Pydantic-based settings management
- **📈 Better Logging**: Comprehensive logging and error handling
- **🧪 Test Coverage**: Unit tests and testing framework
- **📚 Documentation**: Complete documentation and setup guides

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and add your Google API key

# 4. Run the voice assistant
python src/main.py
```

## 📁 Professional Project Structure

```
voice_assistant_ari_llm/
├── src/                           # 🎯 Source code
│   ├── voice_assistant/           # 📦 Main package
│   │   ├── core/                  # 🧠 Core assistant logic
│   │   │   ├── assistant.py       # Main VoiceAssistant class
│   │   │   └── conversation.py    # Conversation management
│   │   ├── ai/                    # 🤖 AI integration
│   │   │   ├── gemini_client.py   # Gemini 2.5 Flash client
│   │   │   └── prompts.py         # System prompts
│   │   ├── audio/                 # 🎵 Audio processing
│   │   │   ├── speech_recognition.py  # Speech-to-text
│   │   │   ├── text_to_speech.py      # Text-to-speech
│   │   │   └── audio_utils.py         # Audio utilities
│   │   ├── telephony/             # 📞 Telephony integration
│   │   │   ├── ari_handler.py     # Asterisk ARI handler
│   │   │   └── call_manager.py    # Call management
│   │   └── utils/                 # 🛠️ Utilities
│   │       ├── logger.py          # Logging configuration
│   │       └── exceptions.py      # Custom exceptions
│   └── main.py                    # 🚀 Main entry point
├── config/                        # ⚙️ Configuration
│   ├── settings.py                # Pydantic settings
│   └── environment.py             # Environment management
├── tests/                         # 🧪 Test suite
│   ├── test_ai/                   # AI component tests
│   ├── test_audio/                # Audio component tests
│   └── test_core/                 # Core logic tests
├── docs/                          # 📚 Documentation
│   ├── README.md                  # Detailed documentation
│   ├── API.md                     # API reference
│   └── SETUP.md                   # Setup instructions
├── scripts/                       # 📜 Utility scripts
│   ├── run_assistant.py           # Simple run script
│   └── setup.py                   # Setup utilities
├── asterisk-config/               # 📞 Asterisk configuration
├── sounds/                        # 🔊 Audio files
├── requirements.txt               # 📋 Dependencies
├── .env.example                   # 📝 Environment template
└── README.md                      # 📖 This file
```

## 🎯 Key Features

### 🤖 AI-Powered with Gemini 2.5 Flash
- **Latest Model**: Uses Google's Gemini 2.5 Flash for intelligent responses
- **Cost Efficient**: More affordable than previous OpenAI integration
- **Fast Responses**: Optimized for real-time conversation
- **Fallback System**: Graceful handling of API failures

### 🎤 Professional Audio Processing
- **Speech Recognition**: Google Speech Recognition for accurate voice input
- **Text-to-Speech**: Google TTS with standard voice for clear output
- **Audio Utils**: Comprehensive audio processing utilities
- **Real-time Processing**: Low-latency audio handling

### 📞 Telephony Integration
- **Asterisk ARI**: Full integration with Asterisk PBX
- **Call Management**: Handle incoming/outgoing calls
- **Real-time Audio**: Process phone conversations in real-time
- **Multi-channel**: Support multiple concurrent calls

### 🏗️ Professional Architecture
- **Modular Design**: Clean separation of concerns
- **Type Safety**: Full type hints throughout
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logging with configurable levels
- **Testing**: Unit tests and testing framework

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Google API key (free tier available)
- Microphone and speakers
- (Optional) Asterisk PBX for telephony

### Detailed Setup

1. **Environment Setup**:
   ```bash
   # Ensure virtual environment is active
   .venv\Scripts\activate
   
   # Verify Python version
   python --version  # Should be 3.8+
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Get Google API Key**:
   - Visit [Google AI Studio](https://aistudio.google.com/)
   - Sign in and create a new API key
   - Copy the key for configuration

4. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set GOOGLE_API_KEY=your-key-here
   ```

5. **Test Installation**:
   ```bash
   python src/main.py
   ```

## 🎮 Usage

### 🎆 Real-time Telephony Integration (NEW!)

The flagship feature - real-time conversational AI through phone calls:

```bash
# Quick start with real-time integration
./start_realtime.sh

# Or manually
python src/run_realtime_server.py
```

**Real-time Features:**
- 📡 **Bidirectional Audio Streaming**: Direct WebSocket audio with Asterisk externalMedia
- 🎤 **Voice Activity Detection**: Intelligent speech start/stop detection
- ⚡ **Ultra-low Latency**: Direct Gemini Live API integration
- 🔄 **Interruption Handling**: Natural conversation flow with mid-response interruptions
- 🔊 **slin16 Format**: Optimized 16-bit signed linear PCM at 16kHz
- 📈 **Session Management**: Complete conversation state tracking

**Test Extensions:**
- **1000**: Main Gemini Voice Assistant (full real-time integration)
- **1001**: External Media Test (direct WebSocket audio)
- **1002**: Basic Audio Test (echo and playback)

### Standalone Voice Assistant

```bash
python src/main.py
```

**Features:**
- 🎤 Voice input with timeout handling
- 🧠 AI processing with Gemini 2.5 Flash
- 🗣️ Speech output with Google TTS
- 📊 Real-time status updates
- 📈 Session statistics

### Voice Commands
- **Normal conversation**: Speak naturally after "🎤 Listening"
- **Exit**: Say "quit", "exit", "goodbye", or "bye"
- **Force quit**: Press Ctrl+C

### Legacy Telephony Mode

For basic phone-based interactions:

```bash
# Start basic ARI handler
uvicorn src.voice_assistant.telephony.ari_handler:create_ari_app --host 0.0.0.0 --port 8000

# Configure Asterisk to send events to your handler
# See asterisk-config/ for configuration examples
```

## ⚙️ Configuration

### 🎆 Real-time Integration Setup

For the real-time Gemini Live API integration:

```bash
# Run automated setup
python scripts/setup_realtime.py

# This will:
# - Check environment requirements
# - Validate configuration
# - Create required directories
# - Test connections
# - Generate startup scripts
```

**Quick Setup:**
1. Copy `.env.example` to `.env`
2. Set your `GOOGLE_API_KEY`
3. Configure Asterisk (copy `asterisk-config/*`)
4. Run `./start_realtime.sh`

📚 **Detailed Setup Guide**: See [docs/REALTIME_SETUP.md](docs/REALTIME_SETUP.md)

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-google-api-key-here

# AI Settings
GEMINI_MODEL=gemini-2.5-flash
GEMINI_LIVE_MODEL=gemini-2.0-flash-exp
GEMINI_VOICE=Puck
MAX_TOKENS=150
TEMPERATURE=0.7

# Real-time Audio Settings
AUDIO_FORMAT=slin16
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=320
AUDIO_BUFFER_SIZE=1600

# Voice Activity Detection
VAD_ENERGY_THRESHOLD=300
VAD_SILENCE_THRESHOLD=0.5
VAD_SPEECH_THRESHOLD=0.1

# Assistant Settings
ASSISTANT_NAME=ARI
VOICE_LANGUAGE=en
LISTEN_TIMEOUT=20.0
PHRASE_TIME_LIMIT=15.0

# Audio Settings
VOICE_VOLUME=0.9

# Logging
LOG_LEVEL=INFO
# LOG_FILE=logs/assistant.log  # Optional file logging

# Asterisk ARI Configuration
ARI_BASE_URL=http://localhost:8088/ari
ARI_USERNAME=asterisk
ARI_PASSWORD=1234
STASIS_APP=gemini-voice-assistant

# External Media Configuration
EXTERNAL_MEDIA_HOST=localhost
EXTERNAL_MEDIA_PORT=8090

# Real-time Processing
ENABLE_INTERRUPTION_HANDLING=true
MAX_CALL_DURATION=3600
AUTO_ANSWER_CALLS=true
```

## 🔧 Development

### Architecture Overview

The system follows a clean, modular architecture:

1. **Core Layer**: Main assistant logic and conversation management
2. **AI Layer**: Gemini integration and response generation
3. **Audio Layer**: Speech recognition and text-to-speech
4. **Telephony Layer**: Asterisk ARI integration
5. **Utils Layer**: Logging, exceptions, and utilities
6. **Config Layer**: Settings and environment management

### Adding Features

The modular design makes it easy to extend:

```python
# Add new AI provider
from voice_assistant.ai.base_client import BaseAIClient

class NewAIClient(BaseAIClient):
    def generate_response(self, text: str) -> str:
        # Your implementation
        pass

# Add new audio processor
from voice_assistant.audio.base_processor import BaseAudioProcessor

class NewAudioProcessor(BaseAudioProcessor):
    def process_audio(self, audio_data: bytes) -> str:
        # Your implementation
        pass
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/voice_assistant --cov-report=html

# Run specific test file
pytest tests/test_gemini_client.py -v
```

## 📊 Monitoring & Logging

### 🎆 Real-time System Monitoring

The real-time integration provides comprehensive monitoring:

**API Endpoints:**
- **System Status**: `GET http://localhost:8000/status`
- **Active Calls**: `GET http://localhost:8000/calls`
- **Call Details**: `GET http://localhost:8000/calls/{channel_id}`
- **Health Check**: `GET http://localhost:8000/health`
- **API Documentation**: `GET http://localhost:8000/docs`

**Real-time Metrics:**
- **Audio Processing**: Latency, buffer sizes, packet counts
- **Session Management**: Active sessions, conversation turns, duration
- **Voice Activity**: Speech detection accuracy, interruption handling
- **Gemini Live API**: Connection status, response times, error rates
- **External Media**: WebSocket connections, audio quality metrics

### Traditional Monitoring

The assistant provides comprehensive monitoring:

- **Real-time Status**: State changes and processing updates
- **Conversation Metrics**: Success rates and response times
- **Error Tracking**: Detailed error logs and fallback handling
- **Performance Stats**: Session duration and interaction counts

Example output:
```
🤖 Voice Assistant with Gemini 2.5 Flash
============================================================
✅ System Information:
   Assistant Name: ARI
   AI Model: gemini-2.5-flash
   Voice Language: en
   Listen Timeout: 20.0s
✅ Virtual environment: Active
✅ Configuration: .env file found
✅ Google API Key: Configured

[💤 Ready - Waiting for input]
[🎤 Listening - Speak now]
👤 You: Hello, how are you?
[🧠 Processing - Thinking...]
[🗣️ Speaking - Response ready]
🤖 Assistant: Hello! I'm doing great, thank you for asking. I'm ARI, your voice assistant powered by Gemini 2.5 Flash. How can I help you today?
```

## 🚨 Troubleshooting

### Common Issues

1. **"Google API key is required"**:
   - Check `.env` file exists and contains `GOOGLE_API_KEY`
   - Verify API key is valid and has proper permissions

2. **Microphone not detected**:
   - Check microphone permissions in system settings
   - Try: `pip install pyaudio` for better microphone support
   - Test with different microphone devices

3. **Audio playback issues**:
   - Verify speakers/headphones are connected
   - Check system audio settings
   - Try different audio output devices

4. **Import errors**:
   - Ensure virtual environment is activated
   - Run: `pip install -r requirements.txt`
   - Check Python version (3.8+ required)

### Debug Mode

Enable detailed logging:
```bash
# Set in .env file
LOG_LEVEL=DEBUG

# Or set environment variable
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows
```

## 🆚 Migration from Previous Version

If upgrading from the old OpenAI-based version:

1. **Backup your data**: Save any important configurations
2. **Update dependencies**: `pip install -r requirements.txt`
3. **Update environment**: Replace `OPENAI_API_KEY` with `GOOGLE_API_KEY`
4. **Test functionality**: Run `python src/main.py` to verify

### Key Changes
- ❌ Removed: OpenAI dependency and API key
- ✅ Added: Google Generative AI (Gemini 2.5 Flash)
- 🔄 Updated: Professional project structure
- 📈 Improved: Error handling and logging
- 🧪 Added: Test suite and documentation

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with proper tests
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing-feature`
6. Open a Pull Request

## 📞 Support

- 📚 **Documentation**: Check `docs/README.md` for detailed guides
- 🐛 **Issues**: Report bugs on GitHub Issues
- 💡 **Features**: Request features on GitHub Discussions
- 📧 **Contact**: Open an issue for support questions

---

**🎉 Ready to start talking to your AI assistant!**

Run `python src/main.py` and start your conversation with Gemini 2.5 Flash! 🚀

