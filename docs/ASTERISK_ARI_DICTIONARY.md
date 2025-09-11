# 📚 Asterisk ARI Voice Assistant - Complete Dictionary

## 🎯 **Overview**

This comprehensive dictionary covers all technical terms, concepts, and technologies used in the NPCL Asterisk ARI Voice Assistant project. Each term includes definition, context, and practical usage.

---

## 🔤 **A**

### **ARI (Asterisk REST Interface)**
- **Definition**: RESTful API for controlling Asterisk PBX programmatically
- **Use**: Enables external applications to control calls, channels, bridges, and media
- **Example**: `POST /ari/channels/{channelId}/answer` to answer a call

### **Asterisk**
- **Definition**: Open-source PBX (Private Branch Exchange) software
- **Use**: Handles telephony operations, call routing, and media processing
- **Context**: Core telephony platform for the voice assistant

### **Audio Codec**
- **Definition**: Algorithm for encoding/decoding audio data
- **Use**: Compresses audio for transmission over networks
- **Examples**: G.711 (ulaw/alaw), G.722, opus, slin16

### **Audio Format**
- **Definition**: Structure and encoding of audio data
- **Use**: Defines how audio is stored and transmitted
- **Project Use**: slin16 (16-bit signed linear PCM at 16kHz)

### **Async/Await**
- **Definition**: Python asynchronous programming pattern
- **Use**: Handles concurrent operations without blocking
- **Context**: Used in FastAPI for handling multiple calls simultaneously

---

## 🔤 **B**

### **Bridge**
- **Definition**: Asterisk component that connects multiple channels
- **Use**: Enables conference calls or call transfers
- **Example**: Connecting caller to voice assistant channel

### **Bidirectional Audio**
- **Definition**: Two-way audio streaming (send and receive)
- **Use**: Enables real-time conversation
- **Implementation**: WebSocket with external media

### **Buffer**
- **Definition**: Temporary storage for audio data
- **Use**: Smooths audio playback and prevents dropouts
- **Size**: Typically 320 samples (20ms) for real-time processing

---

## 🔤 **C**

### **Channel**
- **Definition**: Asterisk representation of a call leg or connection
- **Use**: Tracks call state, media, and properties
- **States**: Down, Reserved, OffHook, Dialing, Ring, Ringing, Up, Busy, etc.

### **Codec Negotiation**
- **Definition**: Process of agreeing on audio format between endpoints
- **Use**: Ensures compatible audio transmission
- **Example**: SIP endpoints negotiating G.711 or G.722

### **Conference Bridge**
- **Definition**: Multi-party audio mixing component
- **Use**: Enables multiple participants in single call
- **Context**: Can be used for group voice assistant sessions

### **Call Flow**
- **Definition**: Sequence of events during a phone call
- **Use**: Defines how calls are processed and routed
- **Example**: Incoming call → Answer → Voice Assistant → Hangup

---

## 🔤 **D**

### **Dialplan**
- **Definition**: Asterisk configuration defining call routing logic
- **Use**: Determines how incoming calls are handled
- **File**: `extensions.conf`
- **Example**: Extension 1000 routes to voice assistant

### **DTMF (Dual-Tone Multi-Frequency)**
- **Definition**: Touch-tone signals from phone keypads
- **Use**: Interactive voice response and menu navigation
- **Context**: Can be used for voice assistant commands

### **Docker**
- **Definition**: Containerization platform
- **Use**: Packages Asterisk with dependencies for easy deployment
- **File**: `docker-compose.yml`

---

## 🔤 **E**

### **External Media**
- **Definition**: Asterisk feature for streaming audio to external applications
- **Use**: Enables real-time audio processing by external systems
- **Protocol**: WebSocket with binary audio frames
- **Format**: Raw audio data (slin16)

### **Event-Driven Architecture**
- **Definition**: System design based on producing and consuming events
- **Use**: ARI sends events (StasisStart, ChannelTalkingStarted) to applications
- **Benefits**: Scalable, loosely coupled components

### **Endpoint**
- **Definition**: Communication device or software (phone, softphone)
- **Use**: Originates or terminates calls
- **Types**: SIP, PJSIP, IAX2, Local

---

## 🔤 **F**

### **FastAPI**
- **Definition**: Modern Python web framework for building APIs
- **Use**: Handles ARI events and provides REST endpoints
- **Features**: Automatic documentation, async support, type hints

### **Frame**
- **Definition**: Unit of audio data transmission
- **Use**: Contains audio samples for specific time duration
- **Size**: Typically 20ms (320 samples at 16kHz)

### **Function Calling**
- **Definition**: AI capability to execute specific functions based on user input
- **Use**: Enables voice assistant to perform actions (create tickets, check status)
- **Context**: Gemini AI can call predefined functions

---

## 🔤 **G**

### **Gemini**
- **Definition**: Google's large language model family
- **Use**: Powers intelligent conversation in voice assistant
- **Models**: gemini-1.5-flash (text), gemini-2.0-flash-exp (voice)

### **G.711**
- **Definition**: ITU-T audio codec standard
- **Variants**: μ-law (North America), A-law (Europe)
- **Use**: Common telephony codec with good quality

### **Gateway**
- **Definition**: Device connecting different network types
- **Use**: Connects VoIP to PSTN (traditional phone networks)
- **Example**: SIP trunk provider gateway

---

## 🔤 **H**

### **HTTP/HTTPS**
- **Definition**: Web communication protocols
- **Use**: ARI REST API communication
- **Security**: HTTPS recommended for production deployments

### **Hangup**
- **Definition**: Termination of a phone call
- **Use**: Ends call session and releases resources
- **Events**: ChannelHangupRequest, StasisEnd

### **Health Check**
- **Definition**: System monitoring endpoint
- **Use**: Verifies service availability and status
- **Endpoint**: `/health` in FastAPI application

---

## 🔤 **I**

### **IVR (Interactive Voice Response)**
- **Definition**: Automated phone system with voice prompts
- **Use**: Guides callers through menu options
- **Context**: Voice assistant can replace traditional IVR

### **Interruption Handling**
- **Definition**: Managing mid-conversation user input
- **Use**: Allows natural conversation flow
- **Implementation**: Voice Activity Detection with real-time processing

### **Integration Testing**
- **Definition**: Testing component interactions
- **Use**: Verifies Asterisk-to-application communication
- **Tools**: pytest with async support

---

## 🔤 **J**

### **JSON**
- **Definition**: JavaScript Object Notation data format
- **Use**: ARI event and response format
- **Example**: `{"type": "StasisStart", "channel": {...}}`

### **Jitter**
- **Definition**: Variation in packet arrival times
- **Use**: Can affect audio quality in VoIP calls
- **Mitigation**: Jitter buffers smooth audio playback

---

## 🔤 **K**

### **Keep-Alive**
- **Definition**: Mechanism to maintain connection
- **Use**: Prevents WebSocket timeouts
- **Implementation**: Periodic ping/pong messages

---

## 🔤 **L**

### **Latency**
- **Definition**: Delay between input and output
- **Use**: Critical for real-time voice conversation
- **Target**: <200ms for natural conversation

### **Live API**
- **Definition**: Real-time AI conversation interface
- **Use**: Direct voice-to-voice AI interaction
- **Provider**: Google Gemini Live API

### **Load Balancing**
- **Definition**: Distributing requests across multiple servers
- **Use**: Scales voice assistant for high call volumes
- **Methods**: Round-robin, least connections, weighted

---

## 🔤 **M**

### **Media**
- **Definition**: Audio/video content in telecommunications
- **Use**: Voice data transmitted during calls
- **Formats**: Raw audio, RTP packets, WebSocket frames

### **Microphone**
- **Definition**: Audio input device
- **Use**: Captures user voice for speech recognition
- **Configuration**: Sample rate, channels, bit depth

### **Mixing**
- **Definition**: Combining multiple audio streams
- **Use**: Conference calls, background music
- **Component**: Asterisk mixing bridge

---

## 🔤 **N**

### **NAT (Network Address Translation)**
- **Definition**: IP address mapping technique
- **Use**: Enables private networks to access internet
- **Challenge**: Can complicate VoIP connectivity

### **NPCL (Noida Power Corporation Limited)**
- **Definition**: Power utility company
- **Use**: Target customer for voice assistant
- **Context**: Specialized prompts for power service inquiries

### **NLP (Natural Language Processing)**
- **Definition**: AI field for understanding human language
- **Use**: Enables intelligent conversation
- **Implementation**: Gemini AI model

---

## 🔤 **O**

### **Offline Mode**
- **Definition**: Operation without external AI services
- **Use**: Fallback when API quota exceeded
- **Features**: Predefined responses, local processing

### **Opus**
- **Definition**: Modern audio codec
- **Use**: High-quality, low-latency audio compression
- **Context**: Alternative to traditional telephony codecs

---

## 🔤 **P**

### **PBX (Private Branch Exchange)**
- **Definition**: Private telephone switching system
- **Use**: Manages internal and external calls for organization
- **Implementation**: Asterisk open-source PBX

### **PCM (Pulse Code Modulation)**
- **Definition**: Digital audio encoding method
- **Use**: Converts analog audio to digital
- **Format**: slin16 = 16-bit signed linear PCM

### **Playback**
- **Definition**: Playing audio files to caller
- **Use**: Voice prompts, music on hold
- **Formats**: WAV, GSM, various codecs

### **Pydantic**
- **Definition**: Python data validation library
- **Use**: Configuration management and API validation
- **Version**: v2 with enhanced features

---

## 🔤 **Q**

### **Queue**
- **Definition**: Call waiting system
- **Use**: Manages multiple incoming calls
- **Features**: Hold music, position announcements

### **Quota**
- **Definition**: API usage limit
- **Use**: Restricts number of AI requests
- **Management**: Automatic detection and offline fallback

---

## 🔤 **R**

### **REST (Representational State Transfer)**
- **Definition**: Web service architectural style
- **Use**: ARI provides RESTful API for Asterisk control
- **Methods**: GET, POST, PUT, DELETE

### **RTP (Real-time Transport Protocol)**
- **Definition**: Network protocol for media transmission
- **Use**: Carries audio/video over IP networks
- **Features**: Sequence numbering, timestamps

### **Recording**
- **Definition**: Capturing call audio for storage
- **Use**: Quality assurance, compliance
- **Formats**: WAV, MP3, various codecs

---

## 🔤 **S**

### **SIP (Session Initiation Protocol)**
- **Definition**: VoIP signaling protocol
- **Use**: Establishes, modifies, and terminates calls
- **Components**: User agents, proxy servers, registrars

### **Stasis**
- **Definition**: Asterisk application framework
- **Use**: Enables external control of call flow
- **Events**: StasisStart, StasisEnd, ChannelStateChange

### **Speech Recognition**
- **Definition**: Converting speech to text
- **Use**: Processes user voice input
- **Provider**: Google Speech Recognition API

### **slin16**
- **Definition**: 16-bit signed linear audio format
- **Use**: Uncompressed audio at 16kHz sample rate
- **Context**: Optimal for Asterisk and AI processing

---

## 🔤 **T**

### **TTS (Text-to-Speech)**
- **Definition**: Converting text to spoken audio
- **Use**: Voice assistant responses
- **Engine**: pyttsx3 with Windows optimization

### **Telephony**
- **Definition**: Technology for voice communication over distance
- **Use**: Core functionality of voice assistant
- **Types**: Traditional PSTN, VoIP, mobile

### **Timeout**
- **Definition**: Maximum wait time for operation
- **Use**: Prevents indefinite waiting
- **Example**: 15-second speech recognition timeout

---

## 🔤 **U**

### **UUID (Universally Unique Identifier)**
- **Definition**: 128-bit identifier
- **Use**: Unique channel and call identification
- **Format**: 8-4-4-4-12 hexadecimal digits

### **Uvicorn**
- **Definition**: ASGI server for Python web applications
- **Use**: Runs FastAPI application
- **Features**: High performance, async support

---

## 🔤 **V**

### **VAD (Voice Activity Detection)**
- **Definition**: Algorithm detecting speech presence
- **Use**: Optimizes processing and reduces noise
- **Implementation**: Energy threshold, silence detection

### **VoIP (Voice over Internet Protocol)**
- **Definition**: Voice communication over IP networks
- **Use**: Modern telephony technology
- **Protocols**: SIP, RTP, RTCP

### **Virtual Environment**
- **Definition**: Isolated Python environment
- **Use**: Manages project dependencies
- **Tool**: venv, virtualenv

---

## 🔤 **W**

### **WebSocket**
- **Definition**: Full-duplex communication protocol
- **Use**: Real-time bidirectional data exchange
- **Context**: External media streaming, Live API

### **Webhook**
- **Definition**: HTTP callback for event notification
- **Use**: ARI events trigger application responses
- **Method**: POST requests with event data

---

## 🔤 **X**

### **XML**
- **Definition**: Extensible Markup Language
- **Use**: Configuration files, data exchange
- **Context**: Some Asterisk configurations use XML

---

## 🔤 **Y**

### **YAML**
- **Definition**: Human-readable data serialization
- **Use**: Configuration files, Docker Compose
- **Example**: `docker-compose.yml`

---

## 🔤 **Z**

### **Zero-downtime Deployment**
- **Definition**: Updating system without service interruption
- **Use**: Production deployments
- **Methods**: Blue-green deployment, rolling updates

---

## 📊 **Common Acronyms Quick Reference**

| Acronym | Full Form | Context |
|---------|-----------|---------|
| **ARI** | Asterisk REST Interface | API for Asterisk control |
| **PBX** | Private Branch Exchange | Phone system |
| **SIP** | Session Initiation Protocol | VoIP signaling |
| **RTP** | Real-time Transport Protocol | Media transmission |
| **TTS** | Text-to-Speech | Voice synthesis |
| **STT** | Speech-to-Text | Voice recognition |
| **VAD** | Voice Activity Detection | Speech detection |
| **IVR** | Interactive Voice Response | Automated phone system |
| **DTMF** | Dual-Tone Multi-Frequency | Touch-tone signals |
| **NAT** | Network Address Translation | IP address mapping |
| **UUID** | Universally Unique Identifier | Unique identifiers |
| **PCM** | Pulse Code Modulation | Audio encoding |
| **API** | Application Programming Interface | Software interface |
| **REST** | Representational State Transfer | Web service style |
| **JSON** | JavaScript Object Notation | Data format |

---

## 🎯 **Usage Context in Project**

### **Core Technologies**
- **Asterisk + ARI**: Telephony platform and control interface
- **FastAPI**: Web framework for handling ARI events
- **Gemini AI**: Language model for intelligent responses
- **WebSocket**: Real-time audio streaming
- **Docker**: Containerized deployment

### **Audio Pipeline**
1. **Input**: Microphone → Speech Recognition → Text
2. **Processing**: Text → Gemini AI → Response Text
3. **Output**: Response Text → TTS → Audio → Speakers

### **Call Flow**
1. **Incoming Call**: SIP endpoint → Asterisk
2. **ARI Event**: StasisStart → FastAPI application
3. **Media Setup**: External media WebSocket
4. **Conversation**: Bidirectional audio + AI processing
5. **Cleanup**: Call end → Resource cleanup

---

## 📚 **Additional Resources**

### **Documentation Links**
- **Asterisk**: https://docs.asterisk.org/
- **ARI**: https://wiki.asterisk.org/wiki/display/AST/Asterisk+REST+Interface
- **FastAPI**: https://fastapi.tiangolo.com/
- **Gemini AI**: https://ai.google.dev/
- **SIP Protocol**: https://tools.ietf.org/html/rfc3261

### **Configuration Files**
- `extensions.conf` - Asterisk dialplan
- `ari.conf` - ARI user configuration
- `sip.conf` - SIP endpoint configuration
- `.env` - Environment variables
- `docker-compose.yml` - Container orchestration

---

*This dictionary serves as a comprehensive reference for understanding all technical terms and concepts used in the NPCL Asterisk ARI Voice Assistant project.*