# NPCL Asterisk ARI Voice Assistant - File Descriptions

This document provides 25-word descriptions for each file in the NPCL Asterisk ARI Voice Assistant project, explaining their purpose and functionality.

## 📁 Root Directory Files

### Core Application Files
- **`src/main.py`** - Main entry point for NPCL Asterisk ARI Voice Assistant. Provides multiple interaction modes including chat, voice, and combined modes with Gemini AI integration.
- **`src/run_realtime_server.py`** - FastAPI server for handling Asterisk ARI events with Gemini Live API integration. Provides HTTP endpoints for ARI events and WebSocket support.
- **`run_ari_server.py`** - Legacy ARI server launcher script. Starts the FastAPI server for handling Asterisk REST Interface events and external media WebSocket connections.
- **`run_all_tests.py`** - Comprehensive test runner script with dependency checking, auto-installation, and multiple test execution modes including unit, integration, performance, and end-to-end testing.

### Configuration Files
- **`.env.example`** - Environment variables template file containing all required configuration settings for API keys, Asterisk connection, and audio processing parameters.
- **`requirements.txt`** - Python package dependencies for production deployment including FastAPI, Gemini AI, audio processing, telephony, and WebSocket communication libraries.
- **`requirements-test.txt`** - Testing dependencies including pytest, coverage tools, mocking libraries, and performance testing frameworks for comprehensive test suite execution.
- **`pytest.ini`** - Pytest configuration file defining test discovery patterns, markers, async support, output formatting, and timeout settings for test execution.
- **`docker-compose.yml`** - Docker Compose configuration for Asterisk PBX container with volume mounts, network settings, and environment variables for development deployment.
- **`docker-compose.production.yml`** - Production Docker Compose setup with optimized Asterisk configuration, security settings, monitoring, and scalability features for enterprise deployment.
- **`Dockerfile`** - Docker container definition for the voice assistant application with Python runtime, dependencies, and optimized configuration for containerized deployment.

### Documentation Files
- **`README.md`** - Comprehensive project documentation including installation instructions, configuration guide, usage examples, and troubleshooting information for NPCL voice assistant.
- **`PROJECT_SUMMARY.md`** - High-level project overview describing architecture, features, technology stack, and integration capabilities of the NPCL Asterisk ARI voice assistant.
- **`AGENTS.md`** - Documentation for AI agent configurations, behavior patterns, conversation flows, and customization options for different voice assistant personalities.
- **`qodo.md`** - Qodo AI integration documentation explaining code analysis, quality metrics, automated testing, and continuous improvement features for development workflow.

## 📁 Source Code (`src/`)

### Main Application Files
- **`src/ari_handler.py`** - Basic Asterisk REST Interface event handler for processing telephony events, managing call states, and coordinating with voice assistant components.
- **`src/audio_logger.py`** - Audio event logging system for tracking voice interactions, call quality metrics, and debugging audio processing issues in telephony applications.
- **`src/audio_processor.py`** - Core audio processing engine for real-time voice data handling, format conversion, noise reduction, and audio quality optimization.
- **`src/llm_agent.py`** - Large Language Model agent interface for Gemini AI integration, conversation management, and intelligent response generation for voice interactions.
- **`src/models.py`** - Pydantic data models and schemas for API requests, responses, configuration validation, and data serialization throughout the voice assistant application.
- **`src/tts.py`** - Text-to-Speech engine implementation using Google TTS services for converting AI responses to natural-sounding voice output for telephony calls.
- **`src/voice_assistant_cli.py`** - Command-line interface for voice assistant testing, configuration management, and standalone operation without telephony integration for development purposes.

## 📁 Configuration (`config/`)

- **`config/settings.py`** - Centralized configuration management using Pydantic for environment variables, API keys, audio settings, telephony parameters, and application behavior control.
- **`config/__init__.py`** - Configuration package initialization file exposing settings classes and utility functions for application-wide configuration access and validation.

## 📁 Voice Assistant Core (`src/voice_assistant/`)

### Main Package Files
- **`src/voice_assistant/__init__.py`** - Voice assistant package initialization with version information, core imports, and package-level configuration for modular component access.
- **`src/voice_assistant/enterprise_integration.py`** - Enterprise system integration features including CRM connectivity, database synchronization, and external API integration for business applications.

### AI Integration (`src/voice_assistant/ai/`)
- **`src/voice_assistant/ai/function_calling.py`** - Function calling framework for Gemini AI to execute specific actions, access external APIs, and perform structured tasks during conversations.
- **`src/voice_assistant/ai/gemini_client.py`** - Standard Gemini AI client for text-based conversations, response generation, and basic AI interaction without real-time voice capabilities.
- **`src/voice_assistant/ai/gemini_live_client.py`** - Real-time Gemini Live API client for bidirectional voice conversations, streaming audio processing, and low-latency AI interaction for telephony.
- **`src/voice_assistant/ai/npcl_prompts.py`** - NPCL-specific conversation prompts, customer service templates, and domain knowledge for power utility company interactions and complaint handling.
- **`src/voice_assistant/ai/websocket_gemini_client.py`** - WebSocket-based Gemini client for persistent connections, real-time communication, and efficient message handling for continuous voice assistant operation.

### Audio Processing (`src/voice_assistant/audio/`)
- **`src/voice_assistant/audio/advanced_audio_processor.py`** - Advanced audio processing with noise reduction, echo cancellation, audio enhancement, and quality optimization for professional telephony applications.
- **`src/voice_assistant/audio/audio_player.py`** - Audio playback engine for TTS output, sound effects, hold music, and voice prompts with volume control and format support.
- **`src/voice_assistant/audio/audio_utils.py`** - Audio utility functions for format conversion, sample rate adjustment, audio validation, and common audio processing operations.
- **`src/voice_assistant/audio/improved_vad.py`** - Enhanced Voice Activity Detection with machine learning algorithms, noise robustness, and accurate speech/silence discrimination for telephony.
- **`src/voice_assistant/audio/microphone_stream.py`** - Real-time microphone input streaming for voice capture, audio buffering, and continuous audio processing in voice assistant applications.
- **`src/voice_assistant/audio/realtime_audio_processor.py`** - Real-time audio processing engine with low-latency voice handling, format conversion, and streaming capabilities for live telephony conversations.
- **`src/voice_assistant/audio/speech_recognition.py`** - Speech-to-text engine using Google Speech Recognition for converting voice input to text with language support and accuracy optimization.
- **`src/voice_assistant/audio/speech_recognition_fallback.py`** - Fallback speech recognition system with offline capabilities, alternative providers, and error recovery for robust voice processing.
- **`src/voice_assistant/audio/text_to_speech.py`** - Text-to-speech conversion engine with voice selection, speed control, and audio format optimization for natural voice output.

### Core Components (`src/voice_assistant/core/`)
- **`src/voice_assistant/core/assistant.py`** - Main voice assistant orchestrator coordinating AI, audio, telephony components for complete conversation management and user interaction.
- **`src/voice_assistant/core/constants.py`** - Application constants including audio formats, timeout values, configuration defaults, and system-wide parameters for consistent behavior.
- **`src/voice_assistant/core/error_handling.py`** - Centralized error handling system with custom exceptions, error recovery strategies, and logging for robust application operation.
- **`src/voice_assistant/core/modern_assistant.py`** - Modern voice assistant implementation with latest AI features, real-time processing, and enhanced conversation capabilities for advanced interactions.
- **`src/voice_assistant/core/performance.py`** - Performance monitoring and optimization tools for tracking response times, resource usage, and system efficiency in voice assistant operations.
- **`src/voice_assistant/core/security.py`** - Security framework with authentication, authorization, input validation, and protection against common vulnerabilities in voice assistant applications.
- **`src/voice_assistant/core/session_manager.py`** - Session management system for tracking user conversations, call states, context preservation, and multi-user support in telephony applications.

### Telephony Integration (`src/voice_assistant/telephony/`)
- **`src/voice_assistant/telephony/advanced_ari_handler.py`** - Advanced Asterisk REST Interface handler with complex call routing, conference management, and enterprise telephony features.
- **`src/voice_assistant/telephony/ari_handler.py`** - Standard ARI event handler for basic call management, channel operations, and telephony event processing in Asterisk integration.
- **`src/voice_assistant/telephony/external_media_handler.py`** - External media WebSocket handler for bidirectional audio streaming between Asterisk and voice assistant with real-time processing.
- **`src/voice_assistant/telephony/realtime_ari_handler.py`** - Real-time ARI handler optimized for low-latency voice processing, immediate event response, and seamless telephony integration.
- **`src/voice_assistant/telephony/rtp_streaming_handler.py`** - RTP audio streaming handler for direct media processing, codec management, and high-quality audio transmission in telephony systems.
- **`src/voice_assistant/telephony/simple_ari_handler.py`** - Simplified ARI handler for basic telephony operations, call answering, and minimal feature set for lightweight voice assistant deployment.

### Tools and Utilities (`src/voice_assistant/tools/`)
- **`src/voice_assistant/tools/weather_tool.py`** - Weather information tool for function calling, providing location-based weather data and forecasts during voice assistant conversations.

### Utility Functions (`src/voice_assistant/utils/`)
- **`src/voice_assistant/utils/exceptions.py`** - Custom exception classes for voice assistant specific errors, telephony failures, and AI processing issues with detailed error information.
- **`src/voice_assistant/utils/logger.py`** - Logging system with structured logging, log rotation, and configurable output for debugging and monitoring voice assistant operations.
- **`src/voice_assistant/utils/optimized_logger.py`** - High-performance logging system optimized for real-time applications with minimal latency impact and efficient log processing.
- **`src/voice_assistant/utils/performance_monitor.py`** - Performance monitoring tools for tracking system metrics, response times, and resource utilization in voice assistant applications.
- **`src/voice_assistant/utils/simple_indicators.py`** - Simple status indicators and progress displays for command-line interfaces and basic user feedback in voice assistant operations.
- **`src/voice_assistant/utils/ui_indicators.py`** - User interface indicators for visual feedback, status displays, and progress tracking in voice assistant applications.

### Security Components (`src/voice_assistant/security/`)
- **`src/voice_assistant/security/audit_logger.py`** - Security audit logging system for tracking access attempts, security events, and compliance monitoring in voice assistant applications.
- **`src/voice_assistant/security/auth_manager.py`** - Authentication and authorization manager for user verification, access control, and security policy enforcement in voice assistant systems.
- **`src/voice_assistant/security/encryption.py`** - Encryption utilities for data protection, secure communication, and privacy preservation in voice assistant data handling.
- **`src/voice_assistant/security/input_validator.py`** - Input validation system for sanitizing user input, preventing injection attacks, and ensuring data integrity in voice assistant interactions.
- **`src/voice_assistant/security/rate_limiter.py`** - Rate limiting system for preventing abuse, controlling API usage, and maintaining service quality in voice assistant applications.
- **`src/voice_assistant/security/security_manager.py`** - Centralized security management coordinating authentication, authorization, encryption, and security policies for comprehensive protection.

### Observability (`src/voice_assistant/observability/`)
- **`src/voice_assistant/observability/dashboard.py`** - Monitoring dashboard for real-time system metrics, performance visualization, and operational insights for voice assistant management.
- **`src/voice_assistant/observability/logger.py`** - Observability-focused logging with structured data, metrics collection, and integration with monitoring systems for operational visibility.
- **`src/voice_assistant/observability/metrics_collector.py`** - Metrics collection system for gathering performance data, usage statistics, and system health information for monitoring and analysis.
- **`src/voice_assistant/observability/monitoring.py`** - System monitoring framework with alerting, health checks, and automated monitoring for voice assistant infrastructure management.
- **`src/voice_assistant/observability/tracer.py`** - Distributed tracing system for tracking requests across components, performance analysis, and debugging complex voice assistant interactions.

### Scalability (`src/voice_assistant/scalability/`)
- **`src/voice_assistant/scalability/auto_scaler.py`** - Automatic scaling system for dynamic resource allocation, load-based scaling, and capacity management in voice assistant deployments.
- **`src/voice_assistant/scalability/cluster_manager.py`** - Cluster management for distributed voice assistant deployment, node coordination, and high-availability configuration for enterprise systems.
- **`src/voice_assistant/scalability/database_cluster.py`** - Database clustering solution for distributed data storage, replication, and high-availability database management in voice assistant systems.
- **`src/voice_assistant/scalability/load_balancer.py`** - Load balancing system for distributing voice assistant requests across multiple instances, ensuring optimal performance and availability.
- **`src/voice_assistant/scalability/service_discovery.py`** - Service discovery mechanism for dynamic service registration, health monitoring, and automatic failover in distributed voice assistant architectures.

## 📁 Asterisk Configuration (`asterisk-config/`)

- **`asterisk-config/ari.conf`** - Asterisk REST Interface configuration defining user credentials, permissions, and API access settings for voice assistant integration.
- **`asterisk-config/extensions.conf`** - Asterisk dialplan configuration with call routing rules, voice assistant extensions, and telephony logic for NPCL customer service.
- **`asterisk-config/http.conf`** - HTTP server configuration for Asterisk web interface, REST API access, and WebSocket connections for external media streaming.
- **`asterisk-config/module.conf`** - Asterisk module loading configuration specifying required modules for ARI, external media, and voice assistant functionality.
- **`asterisk-config/modules.conf`** - Alternative module configuration file for Asterisk component loading, feature enablement, and telephony capability management.
- **`asterisk-config/sip.conf`** - SIP protocol configuration for voice over IP settings, endpoint definitions, and telephony connectivity for voice assistant calls.

## 📁 Scripts (`scripts/`)

- **`scripts/run_assistant.py`** - Voice assistant launcher script with configuration validation, dependency checking, and multiple startup modes for development and production.
- **`scripts/setup.py`** - Installation and setup script for voice assistant deployment, dependency installation, and environment configuration for new installations.
- **`scripts/setup_realtime.py`** - Real-time system setup script for configuring low-latency audio processing, WebSocket connections, and optimized voice assistant performance.

## 📁 Test Suite (`tests/`)

### Test Organization
The test suite contains over 360 comprehensive tests organized into multiple categories:

- **`tests/unit/`** - Unit tests for individual components including ARI handlers, audio processors, AI clients, and configuration validation.
- **`tests/integration/`** - Integration tests for component interactions, audio pipelines, and end-to-end system functionality.
- **`tests/performance/`** - Performance tests for latency measurement, throughput testing, and system optimization validation.
- **`tests/e2e/`** - End-to-end tests for complete call workflows, user scenarios, and system integration validation.
- **`tests/audio/`** - Audio-specific tests for voice activity detection, audio quality, and processing accuracy.
- **`tests/mocks/`** - Mock objects and test doubles for external services, APIs, and hardware components.
- **`tests/fixtures/`** - Test data fixtures, audio samples, and configuration templates for consistent testing.
- **`tests/utils/`** - Test utilities, helpers, and common functions for test execution and validation.

### Key Test Files
- **`tests/conftest.py`** - Pytest configuration with fixtures, test setup, and shared testing utilities for comprehensive test execution.
- **`tests/test_all_features.py`** - Comprehensive feature validation tests covering all voice assistant capabilities and integration points.
- **`tests/run_tests.py`** - Test execution script with category selection, coverage reporting, and automated test running capabilities.

## 📁 Additional Directories

### Docker Configuration (`docker/`)
- Contains Docker-related files for containerized deployment, development environments, and production orchestration.

### Documentation (`docs/`)
- Comprehensive documentation including API references, user guides, deployment instructions, and troubleshooting information.

### Kubernetes (`kubernetes/`)
- Kubernetes deployment manifests for container orchestration, scaling, and cloud deployment of voice assistant services.

### Monitoring (`monitoring/`)
- Monitoring and observability configuration including Prometheus, Grafana, and alerting setup for production deployments.

### Sounds (`sounds/`)
- Audio files including voice prompts, hold music, system sounds, and temporary audio storage for voice assistant operations.

---

## 🏗️ Architecture Overview

This NPCL Asterisk ARI Voice Assistant project implements a comprehensive telephony-integrated AI voice assistant with the following key components:

1. **Asterisk PBX Integration** - Full ARI support for call handling, external media streaming, and telephony operations
2. **Gemini AI Integration** - Real-time voice processing with Google's Gemini 1.5 Flash model
3. **Audio Processing Pipeline** - Professional-grade audio handling with VAD, noise reduction, and format conversion
4. **Session Management** - Complete conversation tracking and state management
5. **Security Framework** - Enterprise-grade security with authentication, encryption, and audit logging
6. **Scalability Features** - Distributed deployment, load balancing, and auto-scaling capabilities
7. **Observability** - Comprehensive monitoring, metrics, and tracing for operational excellence

The system is designed for production deployment in enterprise environments with high availability, security, and performance requirements.