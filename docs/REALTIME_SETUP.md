# 🚀 Real-time Gemini Voice Assistant with Asterisk ARI

This document provides comprehensive setup and usage instructions for the real-time Gemini Voice Assistant integration with Asterisk ARI.

## 🎯 Overview

The Real-time Gemini Voice Assistant implements a complete conversational AI system that integrates Google's Gemini Live API with Asterisk PBX using the Asterisk REST Interface (ARI). This enables real-time, low-latency voice conversations with AI through phone calls.

### Key Features

- **Real-time Conversation**: Direct integration with Gemini Live API for natural voice interactions
- **Bidirectional Audio Streaming**: Uses Asterisk's `externalMedia` for low-latency audio processing
- **Voice Activity Detection**: Intelligent detection of speech start/stop for interruption handling
- **Session Management**: Complete conversation state management and metrics
- **slin16 Audio Format**: Optimized for Asterisk with 16-bit signed linear PCM at 16kHz
- **Interruption Handling**: Users can interrupt the AI mid-response for natural conversation flow
- **Professional Architecture**: Modular, scalable design with comprehensive error handling

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Phone Call    │───▶│   Asterisk PBX   │───▶│  ARI Handler    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  externalMedia   │───▶│ Audio Processor │
                       │   (WebSocket)    │    └─────────────────┘
                       └──────────────────┘             │
                                                        ▼
                                               ┌─────────────────┐
                                               │ Gemini Live API │
                                               │   (WebSocket)   │
                                               └─────────────────┘
```

## 📋 Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Asterisk**: 16.0 or higher with ARI enabled
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Network**: Stable internet connection for Gemini Live API

### Required Accounts

- **Google AI Studio Account**: For Gemini API access
  - Visit: https://aistudio.google.com/
  - Create API key with Gemini access

## 🛠️ Installation

### Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd voice_assistant_ari_llm

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run Setup Script

```bash
# Run the automated setup
python scripts/setup_realtime.py

# This will:
# - Check environment requirements
# - Validate configuration
# - Create required directories
# - Check dependencies
# - Test connections
# - Generate startup scripts
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env  # or your preferred editor
```

#### Required Configuration

```bash
# Google AI Configuration (REQUIRED)
GOOGLE_API_KEY=your-google-api-key-here

# AI Model Settings
GEMINI_LIVE_MODEL=gemini-2.0-flash-exp
GEMINI_VOICE=Puck

# Real-time Audio Settings
AUDIO_FORMAT=slin16
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SIZE=320

# Asterisk ARI Configuration
ARI_BASE_URL=http://localhost:8088/ari
ARI_USERNAME=asterisk
ARI_PASSWORD=1234
STASIS_APP=gemini-voice-assistant

# External Media Configuration
EXTERNAL_MEDIA_HOST=localhost
EXTERNAL_MEDIA_PORT=8090
```

### Step 4: Configure Asterisk

#### Copy Configuration Files

```bash
# Copy Asterisk configuration files
sudo cp asterisk-config/* /etc/asterisk/

# Or manually configure based on the examples
```

#### Key Asterisk Configuration

**extensions.conf**:
```ini
[gemini-voice-assistant]
exten => 1000,1,NoOp(Gemini Voice Assistant Call - Real-time)
same => n,Answer()
same => n,Set(TALK_DETECT(set)=4,160)
same => n,Stasis(gemini-voice-assistant,${CALLERID(num)},${EXTEN})
same => n,Hangup()
```

**ari.conf**:
```ini
[general]
enabled = yes
pretty = yes
allowed_origins = *

[asterisk]
type = user
read_only = no
password = 1234
```

**http.conf**:
```ini
[general]
enabled=yes
bindaddr=0.0.0.0
bindport=8088
```

#### Restart Asterisk

```bash
# Restart Asterisk to load new configuration
sudo systemctl restart asterisk

# Or reload configuration
sudo asterisk -rx "core reload"
```

## 🚀 Running the Application

### Method 1: Using Generated Scripts

```bash
# Linux/Mac
./start_realtime.sh

# Windows
start_realtime.bat
```

### Method 2: Manual Start

```bash
# Start the FastAPI server
python src/run_realtime_server.py

# Or start the standalone application
python src/main.py
```

### Method 3: Using uvicorn directly

```bash
# Start with uvicorn
uvicorn src.run_realtime_server:create_app --factory --host 0.0.0.0 --port 8000
```

## 📞 Testing the Integration

### Test Extensions

- **1000**: Main Gemini Voice Assistant (full real-time integration)
- **1001**: External Media Test (direct WebSocket audio)
- **1002**: Basic Audio Test (echo and playback)
- **1003**: Conference Test
- **1004**: Recording Test

### Testing Steps

1. **Start the Application**:
   ```bash
   ./start_realtime.sh
   ```

2. **Verify System Status**:
   - Visit: http://localhost:8000/status
   - Check all components are running

3. **Make Test Calls**:
   ```bash
   # Using Asterisk CLI
   asterisk -rx "originate Local/1000@gemini-voice-assistant extension 1000@gemini-voice-assistant"
   
   # Or use a SIP phone to call extension 1000
   ```

4. **Monitor Logs**:
   ```bash
   # Check application logs
   tail -f logs/voice_assistant.log
   
   # Check Asterisk logs
   sudo tail -f /var/log/asterisk/full
   ```

## 🔧 Configuration Options

### Audio Settings

```bash
# Audio format (slin16 recommended for Asterisk)
AUDIO_FORMAT=slin16

# Sample rate (16000 Hz optimal for Gemini Live)
AUDIO_SAMPLE_RATE=16000

# Chunk size (320 samples = 20ms at 16kHz)
AUDIO_CHUNK_SIZE=320

# Buffer size (1600 samples = 100ms buffer)
AUDIO_BUFFER_SIZE=1600
```

### Voice Activity Detection

```bash
# Energy threshold for speech detection
VAD_ENERGY_THRESHOLD=300

# Silence duration to detect speech end (seconds)
VAD_SILENCE_THRESHOLD=0.5

# Speech duration to detect speech start (seconds)
VAD_SPEECH_THRESHOLD=0.1
```

### Gemini Live API Settings

```bash
# Available models
GEMINI_LIVE_MODEL=gemini-2.0-flash-exp

# Available voices: Puck, Charon, Kore, Fenrir
GEMINI_VOICE=Puck

# Enable interruption handling
ENABLE_INTERRUPTION_HANDLING=true
```

### Performance Settings

```bash
# Maximum call duration (seconds)
MAX_CALL_DURATION=3600

# Auto-answer incoming calls
AUTO_ANSWER_CALLS=true

# Enable call recording
ENABLE_CALL_RECORDING=false

# Session cleanup interval (seconds)
SESSION_CLEANUP_INTERVAL=300
```

## 📊 Monitoring and Debugging

### API Endpoints

- **System Status**: `GET /status`
- **Active Calls**: `GET /calls`
- **Call Details**: `GET /calls/{channel_id}`
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs`

### Log Levels

```bash
# Set log level in .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Enable file logging
LOG_FILE=logs/voice_assistant.log
```

### Common Issues and Solutions

#### 1. Google API Key Issues

```bash
# Error: "Google API key is required"
# Solution: Verify GOOGLE_API_KEY in .env file

# Test API key
python -c "import google.generativeai as genai; genai.configure(api_key='your-key'); print('API key valid')"
```

#### 2. Asterisk Connection Issues

```bash
# Error: "Failed to connect to ARI"
# Solution: Check Asterisk ARI configuration

# Test ARI endpoint
curl -u asterisk:1234 http://localhost:8088/ari/asterisk/info
```

#### 3. External Media Connection Issues

```bash
# Error: "External media connection failed"
# Solution: Check WebSocket server and firewall

# Test WebSocket server
netstat -tlnp | grep 8090
```

#### 4. Audio Quality Issues

```bash
# Poor audio quality
# Solution: Verify audio format and sample rate

# Check audio settings
AUDIO_FORMAT=slin16
AUDIO_SAMPLE_RATE=16000
```

## 🔒 Security Considerations

### Production Deployment

1. **API Key Security**:
   ```bash
   # Use environment variables, not .env files in production
   export GOOGLE_API_KEY="your-secure-key"
   ```

2. **Network Security**:
   ```bash
   # Restrict ARI access
   # Configure firewall rules
   # Use HTTPS/WSS in production
   ```

3. **Authentication**:
   ```bash
   # Change default ARI credentials
   ARI_USERNAME=your-secure-username
   ARI_PASSWORD=your-secure-password
   ```

### CORS Configuration

```python
# In production, restrict CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## 📈 Performance Optimization

### System Tuning

1. **Audio Buffer Optimization**:
   ```bash
   # Adjust buffer sizes for your network latency
   AUDIO_CHUNK_SIZE=320    # 20ms chunks
   AUDIO_BUFFER_SIZE=1600  # 100ms buffer
   ```

2. **Session Management**:
   ```bash
   # Optimize cleanup intervals
   SESSION_CLEANUP_INTERVAL=300  # 5 minutes
   ```

3. **Logging Optimization**:
   ```bash
   # Reduce log level in production
   LOG_LEVEL=WARNING
   ENABLE_PERFORMANCE_LOGGING=false
   ```

### Scaling Considerations

- **Horizontal Scaling**: Deploy multiple instances behind a load balancer
- **Database Integration**: Add persistent session storage for large deployments
- **Caching**: Implement Redis for session caching
- **Monitoring**: Add Prometheus/Grafana for metrics

## 🧪 Development and Testing

### Development Mode

```bash
# Start with auto-reload
uvicorn src.run_realtime_server:create_app --factory --reload --host 0.0.0.0 --port 8000

# Enable debug logging
LOG_LEVEL=DEBUG
```

### Testing Framework

```bash
# Run tests
pytest tests/

# Run specific test categories
pytest tests/test_realtime/ -v
```

### Custom Extensions

The modular architecture allows easy extension:

```python
# Add custom event handlers
ari_handler.register_event_handler("custom_event", my_handler)

# Add custom audio processors
audio_processor.register_callback("audio_chunk", my_audio_handler)

# Add custom session handlers
session_manager.register_event_handler("session_created", my_session_handler)
```

## 📚 API Reference

### ARI Event Handling

The system handles these ARI events:

- `StasisStart`: Call enters the application
- `StasisEnd`: Call leaves the application
- `ChannelStateChange`: Channel state updates
- `ChannelHangupRequest`: Hangup requests

### WebSocket Protocols

#### External Media Protocol

```
ws://localhost:8090/external_media/{channel_id}
```

- **Format**: Binary audio data (slin16)
- **Direction**: Bidirectional
- **Sample Rate**: 16000 Hz
- **Channels**: 1 (mono)

#### Gemini Live API Protocol

- **Endpoint**: `wss://generativelanguage.googleapis.com/ws/...`
- **Format**: JSON messages with base64 audio
- **Events**: Setup, audio input/output, speech detection

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run code formatting
black src/
flake8 src/
```

### Code Style

- **Formatting**: Black
- **Linting**: Flake8
- **Type Hints**: Required for all functions
- **Documentation**: Docstrings for all classes and methods

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

For support and questions:

1. **Documentation**: Check this README and docs/
2. **Issues**: Create GitHub issues for bugs
3. **Discussions**: Use GitHub Discussions for questions
4. **Logs**: Always include relevant logs when reporting issues

---

**🎉 Enjoy your real-time AI voice assistant powered by Gemini Live API and Asterisk ARI!**