# 🏗️ NPCL Voice Assistant - Architecture Documentation

## 🎯 System Overview

The NPCL Voice Assistant is a modern, scalable voice interaction system designed for power utility customer service. It combines real-time audio processing, AI-powered conversation, and telephony integration to provide seamless voice-based customer support.

## 🏛️ High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Phone Callers]
        B[Web Clients]
        C[Mobile Apps]
        D[API Clients]
    end
    
    subgraph "Gateway Layer"
        E[Asterisk PBX]
        F[Load Balancer]
        G[API Gateway]
    end
    
    subgraph "Application Layer"
        H[FastAPI Server]
        I[WebSocket Handler]
        J[Voice Assistant Core]
    end
    
    subgraph "Processing Layer"
        K[Audio Processor]
        L[AI Service Manager]
        M[Session Manager]
        N[Security Manager]
    end
    
    subgraph "AI Services"
        O[Gemini Client]
        P[Live API Client]
        Q[Speech Recognition]
        R[Text-to-Speech]
    end
    
    subgraph "Infrastructure"
        S[Redis Cache]
        T[PostgreSQL DB]
        U[File Storage]
        V[Monitoring]
    end
    
    A --> E
    B --> F
    C --> F
    D --> G
    
    E --> H
    F --> H
    G --> H
    
    H --> I
    H --> J
    
    J --> K
    J --> L
    J --> M
    J --> N
    
    K --> Q
    K --> R
    L --> O
    L --> P
    
    J --> S
    J --> T
    J --> U
    J --> V
```

## 🔧 Component Architecture

### Core Components

#### 1. Voice Assistant Core (`src/voice_assistant/core/`)

**Purpose**: Central orchestration and business logic

**Key Classes**:
- `VoiceAssistantCore`: Main orchestrator
- `SessionManager`: Manages conversation sessions
- `ConfigurationManager`: Handles settings and configuration
- `ErrorHandler`: Centralized error handling
- `SecurityManager`: Security and validation

**Responsibilities**:
- Coordinate between audio, AI, and telephony components
- Manage conversation state and context
- Handle security and validation
- Provide unified API interface

#### 2. Audio Processing (`src/voice_assistant/audio/`)

**Purpose**: Real-time audio processing and voice activity detection

**Key Classes**:
- `RealTimeAudioProcessor`: Main audio processing pipeline
- `VoiceActivityDetector`: Detects speech vs silence
- `AudioFormatConverter`: Handles format conversions
- `AudioBuffer`: Manages audio data buffering

**Responsibilities**:
- Process incoming audio streams
- Detect voice activity and speech boundaries
- Convert between audio formats
- Buffer audio for processing

```mermaid
graph LR
    A[Raw Audio] --> B[Format Converter]
    B --> C[Voice Activity Detector]
    C --> D[Audio Buffer]
    D --> E[Speech Recognition]
    
    F[AI Response] --> G[Text-to-Speech]
    G --> H[Audio Output]
```

#### 3. AI Services (`src/voice_assistant/ai/`)

**Purpose**: AI-powered conversation and language processing

**Key Classes**:
- `GeminiClient`: Standard Gemini API integration
- `GeminiLiveClient`: Real-time Live API integration
- `ConversationManager`: Manages conversation context
- `ResponseGenerator`: Generates contextual responses

**Responsibilities**:
- Process natural language input
- Generate intelligent responses
- Maintain conversation context
- Handle AI service failover

#### 4. Telephony Integration (`src/voice_assistant/telephony/`)

**Purpose**: Integration with Asterisk PBX and SIP protocols

**Key Classes**:
- `ARIHandler`: Asterisk REST Interface handler
- `CallManager`: Manages active calls
- `SIPHandler`: SIP protocol handling
- `MediaStreamer`: Handles media streaming

**Responsibilities**:
- Handle incoming calls
- Manage call state and media
- Stream audio to/from callers
- Integrate with PBX systems

## 🔄 Data Flow Architecture

### 1. Voice Interaction Flow

```mermaid
sequenceDiagram
    participant C as Caller
    participant A as Asterisk
    participant VA as Voice Assistant
    participant AI as AI Service
    participant TTS as Text-to-Speech
    
    C->>A: Incoming Call
    A->>VA: StasisStart Event
    VA->>VA: Create Session
    VA->>C: Play Greeting
    
    loop Conversation
        C->>A: Audio Stream
        A->>VA: Audio Data
        VA->>VA: Voice Activity Detection
        VA->>AI: Transcribed Text
        AI->>VA: Response Text
        VA->>TTS: Generate Audio
        TTS->>VA: Audio Response
        VA->>A: Play Audio
        A->>C: Audio Output
    end
    
    C->>A: Hangup
    A->>VA: StasisEnd Event
    VA->>VA: Cleanup Session
```

### 2. WebSocket Real-time Flow

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant AudioProcessor
    participant AI
    
    Client->>WebSocket: Connect
    WebSocket->>WebSocket: Create Session
    
    loop Real-time Interaction
        Client->>WebSocket: Audio Chunk
        WebSocket->>AudioProcessor: Process Audio
        AudioProcessor->>AudioProcessor: VAD Analysis
        
        alt Speech Detected
            AudioProcessor->>AI: Transcribe & Process
            AI->>AudioProcessor: Response
            AudioProcessor->>WebSocket: Audio Response
            WebSocket->>Client: Audio Output
        else Silence
            AudioProcessor->>WebSocket: Silence Event
        end
    end
```

## 🗄️ Data Architecture

### Database Schema

```sql
-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    status VARCHAR(50),
    mode VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB
);

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    message_type VARCHAR(50),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

-- Audio recordings table
CREATE TABLE audio_recordings (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    file_path VARCHAR(500),
    duration_seconds INTEGER,
    format VARCHAR(50),
    created_at TIMESTAMP
);

-- Performance metrics table
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY,
    component VARCHAR(100),
    metric_name VARCHAR(100),
    metric_value DECIMAL,
    timestamp TIMESTAMP,
    metadata JSONB
);
```

### Cache Architecture

```mermaid
graph TB
    subgraph "Redis Cache Layers"
        A[Session Cache<br/>TTL: 30min]
        B[AI Response Cache<br/>TTL: 5min]
        C[Audio Buffer Cache<br/>TTL: 1min]
        D[Configuration Cache<br/>TTL: 1hour]
    end
    
    subgraph "Application"
        E[Session Manager]
        F[AI Service]
        G[Audio Processor]
        H[Config Manager]
    end
    
    E --> A
    F --> B
    G --> C
    H --> D
```

## 🔒 Security Architecture

### Security Layers

```mermaid
graph TB
    subgraph "Network Security"
        A[Load Balancer<br/>SSL Termination]
        B[Firewall<br/>Port Filtering]
        C[VPN<br/>Secure Access]
    end
    
    subgraph "Application Security"
        D[API Gateway<br/>Authentication]
        E[Rate Limiting<br/>DDoS Protection]
        F[Input Validation<br/>Sanitization]
    end
    
    subgraph "Data Security"
        G[Encryption at Rest<br/>Database]
        H[Encryption in Transit<br/>TLS/SSL]
        I[Key Management<br/>Secrets]
    end
    
    A --> D
    B --> E
    C --> F
    D --> G
    E --> H
    F --> I
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant Auth
    participant Service
    
    Client->>Gateway: Request + API Key
    Gateway->>Auth: Validate Key
    Auth->>Gateway: Validation Result
    
    alt Valid Key
        Gateway->>Service: Forward Request
        Service->>Gateway: Response
        Gateway->>Client: Response
    else Invalid Key
        Gateway->>Client: 401 Unauthorized
    end
```

## 📊 Monitoring Architecture

### Observability Stack

```mermaid
graph TB
    subgraph "Application"
        A[Voice Assistant]
        B[Metrics Collector]
        C[Log Aggregator]
    end
    
    subgraph "Monitoring Stack"
        D[Prometheus<br/>Metrics Storage]
        E[Grafana<br/>Visualization]
        F[AlertManager<br/>Alerting]
    end
    
    subgraph "Logging Stack"
        G[Elasticsearch<br/>Log Storage]
        H[Kibana<br/>Log Analysis]
        I[Logstash<br/>Log Processing]
    end
    
    A --> B
    A --> C
    B --> D
    C --> I
    D --> E
    D --> F
    I --> G
    G --> H
```

### Key Metrics

| Category | Metrics | Purpose |
|----------|---------|---------|
| **Performance** | Response time, Throughput, Error rate | Monitor system performance |
| **Audio** | Processing latency, VAD accuracy, Audio quality | Monitor audio pipeline |
| **AI** | API response time, Token usage, Model accuracy | Monitor AI services |
| **Telephony** | Call volume, Call duration, Connection quality | Monitor telephony |
| **System** | CPU usage, Memory usage, Disk I/O | Monitor infrastructure |

## 🚀 Deployment Architecture

### Container Architecture

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Voice Assistant Namespace"
            A[Voice Assistant Pods<br/>3 replicas]
            B[Redis Cache<br/>1 replica]
            C[PostgreSQL<br/>1 replica]
        end
        
        subgraph "Monitoring Namespace"
            D[Prometheus<br/>1 replica]
            E[Grafana<br/>1 replica]
            F[AlertManager<br/>1 replica]
        end
        
        subgraph "Telephony Namespace"
            G[Asterisk PBX<br/>2 replicas]
            H[SIP Proxy<br/>2 replicas]
        end
    end
    
    subgraph "External Services"
        I[Google AI APIs]
        J[Load Balancer]
        K[External Storage]
    end
    
    A --> B
    A --> C
    A --> I
    G --> A
    J --> A
    A --> K
```

### Scaling Strategy

```mermaid
graph LR
    subgraph "Horizontal Scaling"
        A[Load Balancer] --> B[Pod 1]
        A --> C[Pod 2]
        A --> D[Pod 3]
        A --> E[Pod N]
    end
    
    subgraph "Vertical Scaling"
        F[Resource Limits]
        G[CPU: 2 cores]
        H[Memory: 4GB]
        I[Storage: 10GB]
    end
    
    subgraph "Auto Scaling"
        J[HPA<br/>CPU > 70%]
        K[VPA<br/>Memory Optimization]
        L[Cluster Autoscaler<br/>Node Scaling]
    end
```

## 🔧 Configuration Architecture

### Configuration Hierarchy

```mermaid
graph TB
    A[Environment Variables] --> B[Configuration Manager]
    C[Config Files] --> B
    D[Database Settings] --> B
    E[Runtime Parameters] --> B
    
    B --> F[Application Config]
    B --> G[Audio Config]
    B --> H[AI Config]
    B --> I[Security Config]
    
    F --> J[Voice Assistant Core]
    G --> K[Audio Processor]
    H --> L[AI Services]
    I --> M[Security Manager]
```

### Configuration Sources Priority

1. **Environment Variables** (Highest priority)
2. **Command Line Arguments**
3. **Configuration Files** (.env, config.yaml)
4. **Database Configuration**
5. **Default Values** (Lowest priority)

## 🔄 Integration Patterns

### Event-Driven Architecture

```mermaid
graph TB
    subgraph "Event Sources"
        A[Telephony Events]
        B[Audio Events]
        C[AI Events]
        D[System Events]
    end
    
    subgraph "Event Bus"
        E[Event Router]
        F[Event Queue]
        G[Event Store]
    end
    
    subgraph "Event Handlers"
        H[Call Handler]
        I[Audio Handler]
        J[AI Handler]
        K[Monitoring Handler]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    
    E --> F
    F --> G
    
    F --> H
    F --> I
    F --> J
    F --> K
```

### Plugin Architecture

```mermaid
graph TB
    subgraph "Core System"
        A[Plugin Manager]
        B[Plugin Registry]
        C[Plugin Loader]
    end
    
    subgraph "Plugin Types"
        D[Audio Plugins<br/>Custom Processors]
        E[AI Plugins<br/>Custom Models]
        F[Telephony Plugins<br/>Custom Protocols]
        G[Integration Plugins<br/>External Systems]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    C --> G
```

## 📈 Performance Architecture

### Caching Strategy

```mermaid
graph TB
    subgraph "Cache Layers"
        A[L1: In-Memory<br/>Application Cache]
        B[L2: Redis<br/>Distributed Cache]
        C[L3: Database<br/>Persistent Storage]
    end
    
    subgraph "Cache Types"
        D[Session Cache<br/>User State]
        E[Response Cache<br/>AI Responses]
        F[Audio Cache<br/>Processed Audio]
        G[Config Cache<br/>Settings]
    end
    
    A --> D
    B --> E
    B --> F
    C --> G
```

### Load Balancing

```mermaid
graph TB
    A[External Load Balancer] --> B[Application Load Balancer]
    B --> C[Voice Assistant Instance 1]
    B --> D[Voice Assistant Instance 2]
    B --> E[Voice Assistant Instance 3]
    
    F[Session Affinity] --> B
    G[Health Checks] --> B
    H[Circuit Breaker] --> B
```

## 🔍 Quality Attributes

### Scalability
- **Horizontal**: Auto-scaling based on load
- **Vertical**: Resource optimization
- **Geographic**: Multi-region deployment

### Reliability
- **Availability**: 99.9% uptime target
- **Fault Tolerance**: Graceful degradation
- **Recovery**: Automatic failover

### Performance
- **Latency**: <500ms response time
- **Throughput**: 1000+ concurrent sessions
- **Efficiency**: Optimized resource usage

### Security
- **Authentication**: API key validation
- **Authorization**: Role-based access
- **Encryption**: End-to-end security

### Maintainability
- **Modularity**: Loosely coupled components
- **Testability**: Comprehensive test coverage
- **Observability**: Full monitoring and logging

---

*This architecture documentation is maintained by the NPCL Voice Assistant development team and is updated with each major release.*