# Voice Assistant with Gemini 2.5 Flash

A professional voice assistant system powered by Google's Gemini 2.5 Flash model, featuring both standalone voice interaction and telephony integration through Asterisk ARI.

## 🚀 Features

- **🤖 AI-Powered Conversations**: Uses Gemini 2.5 Flash for intelligent responses
- **🎤 Speech Recognition**: Google Speech Recognition for accurate voice input
- **🗣️ Text-to-Speech**: Google TTS with standard voice for clear audio output
- **📞 Telephony Integration**: Asterisk ARI support for phone-based interactions
- **🔧 Professional Architecture**: Modular, maintainable, and extensible design
- **📊 Comprehensive Logging**: Detailed logging and error handling
- **⚡ Real-time Processing**: Fast response times with efficient audio processing

## 📁 Project Structure

```
voice_assistant_ari_llm/
├── src/                           # Source code
│   ├── voice_assistant/           # Main package
│   │   ├── core/                  # Core assistant logic
│   │   ├── ai/                    # AI integration (Gemini)
│   │   ├── audio/                 # Audio processing
│   │   ├── telephony/             # ARI integration
│   │   └── utils/                 # Utilities
│   └── main.py                    # Main entry point
├── config/                        # Configuration
├── tests/                         # Test suite
├── docs/                          # Documentation
├── scripts/                       # Utility scripts
├── asterisk-config/               # Asterisk configuration
├── sounds/                        # Audio files
├── requirements.txt               # Dependencies
└── .env                          # Environment variables
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Google API key for Gemini
- Microphone and speakers
- (Optional) Asterisk PBX for telephony features

### Setup

1. **Clone and navigate to the project**:
   ```bash
   cd voice_assistant_ari_llm
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\\Scripts\\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Google API key
   ```

5. **Run the assistant**:
   ```bash
   python src/main.py
   ```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Required
GOOGLE_API_KEY=your-google-api-key-here

# AI Settings
GEMINI_MODEL=gemini-2.5-flash
MAX_TOKENS=150
TEMPERATURE=0.7

# Voice Settings
ASSISTANT_NAME=ARI
VOICE_LANGUAGE=en
LISTEN_TIMEOUT=20.0
PHRASE_TIME_LIMIT=15.0

# Telephony (optional)
ARI_BASE_URL=http://localhost:8088/ari
ARI_USERNAME=asterisk
ARI_PASSWORD=1234
```

### Getting Google API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

## 🎯 Usage

### Standalone Voice Assistant

```bash
python src/main.py
```

The assistant will:
1. Test all components (microphone, AI, TTS)
2. Play a welcome message
3. Listen for your voice input
4. Process with Gemini 2.5 Flash
5. Respond with synthesized speech

### Voice Commands

- **Normal conversation**: Just speak naturally
- **Exit commands**: "quit", "exit", "goodbye", "bye"
- **Interruption**: Press Ctrl+C to force quit

### Telephony Integration

For phone-based interactions:

1. Set up Asterisk PBX with ARI enabled
2. Configure the telephony settings in `.env`
3. Run the ARI handler:
   ```bash
   uvicorn src.voice_assistant.telephony.ari_handler:create_ari_app --host 0.0.0.0 --port 8000
   ```

## 🔧 Development

### Project Architecture

- **Modular Design**: Separate modules for AI, audio, telephony
- **Configuration Management**: Centralized settings with Pydantic
- **Error Handling**: Comprehensive exception handling and fallbacks
- **Logging**: Structured logging throughout the application
- **Type Hints**: Full type annotation for better code quality

### Key Components

1. **VoiceAssistant**: Main orchestrator class
2. **GeminiClient**: AI integration with Gemini 2.5 Flash
3. **SpeechRecognizer**: Google Speech Recognition wrapper
4. **TextToSpeech**: Google TTS integration
5. **ARIHandler**: Asterisk telephony integration

### Adding Features

The modular architecture makes it easy to extend:

- Add new AI providers in `src/voice_assistant/ai/`
- Extend audio processing in `src/voice_assistant/audio/`
- Add telephony features in `src/voice_assistant/telephony/`

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/voice_assistant
```

## 📊 Monitoring

The assistant provides comprehensive logging and statistics:

- Real-time state changes
- Conversation metrics
- Error tracking
- Performance monitoring

## 🔒 Security

- API keys stored in environment variables
- No sensitive data in logs
- Secure telephony authentication
- Input validation and sanitization

## 🚨 Troubleshooting

### Common Issues

1. **Microphone not detected**:
   - Check microphone permissions
   - Try different microphone devices
   - Install PyAudio: `pip install pyaudio`

2. **Google API errors**:
   - Verify API key is correct
   - Check API quotas and billing
   - Ensure internet connection

3. **Audio playback issues**:
   - Check speaker/headphone connections
   - Verify audio drivers
   - Try different audio output devices

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python src/main.py
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:
- Check the documentation in `docs/`
- Review the troubleshooting section
- Open an issue on GitHub