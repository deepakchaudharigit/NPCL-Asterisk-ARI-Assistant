"""
FastAPI server for handling Asterisk ARI events with Gemini Live API integration.
This server provides HTTP endpoints for ARI events and WebSocket support for external media.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import get_settings, get_logging_settings
from src.voice_assistant.utils.logger import setup_logging
from src.voice_assistant.telephony.realtime_ari_handler import create_realtime_ari_app


def create_app() -> FastAPI:
    """Create the main FastAPI application"""
    
    # Setup logging
    logging_settings = get_logging_settings()
    setup_logging(
        level=logging_settings.log_level,
        log_file=logging_settings.log_file
    )
    
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # Create the main app
    app = FastAPI(
        title="Gemini Voice Assistant - Real-time ARI Server",
        description="Real-time conversational AI with Asterisk ARI and Gemini Live API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Create and mount the ARI handler app
    ari_app = create_realtime_ari_app()
    app.mount("/ari", ari_app)
    
    @app.get("/")
    async def root():
        """Root endpoint with system information"""
        return {
            "service": "Gemini Voice Assistant - Real-time ARI Server",
            "version": "2.0.0",
            "status": "running",
            "features": [
                "Real-time Gemini Live API integration",
                "Bidirectional audio streaming with externalMedia",
                "Voice Activity Detection",
                "Session management",
                "Interruption handling",
                "slin16 audio format support"
            ],
            "endpoints": {
                "ari_events": "/ari/events",
                "status": "/ari/status",
                "calls": "/ari/calls",
                "health": "/ari/health",
                "docs": "/docs"
            },
            "configuration": {
                "assistant_name": settings.assistant_name,
                "gemini_model": settings.gemini_live_model,
                "gemini_voice": settings.gemini_voice,
                "audio_format": settings.audio_format,
                "sample_rate": settings.audio_sample_rate,
                "external_media_port": settings.external_media_port,
                "stasis_app": settings.stasis_app
            }
        }
    
    @app.get("/info")
    async def system_info():
        """Detailed system information"""
        return {
            "system": {
                "name": "Gemini Voice Assistant",
                "version": "2.0.0",
                "type": "Real-time ARI Integration"
            },
            "ai": {
                "provider": "Google Gemini",
                "model": settings.gemini_live_model,
                "voice": settings.gemini_voice,
                "features": ["Real-time STT", "Real-time TTS", "Conversation AI"]
            },
            "telephony": {
                "platform": "Asterisk",
                "interface": "ARI (Asterisk REST Interface)",
                "audio_streaming": "externalMedia WebSocket",
                "format": settings.audio_format,
                "sample_rate": f"{settings.audio_sample_rate} Hz",
                "channels": settings.audio_channels
            },
            "capabilities": {
                "real_time_conversation": True,
                "voice_activity_detection": True,
                "interruption_handling": settings.enable_interruption_handling,
                "session_management": True,
                "call_recording": settings.enable_call_recording,
                "auto_answer": settings.auto_answer_calls
            }
        }
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__
            }
        )
    
    logger.info("FastAPI application created successfully")
    return app


def main():
    """Main entry point for the server"""
    settings = get_settings()
    
    print("\\n" + "="*80)
    print("🚀 STARTING GEMINI VOICE ASSISTANT - REAL-TIME ARI SERVER")
    print("="*80)
    print(f"🤖 Assistant: {settings.assistant_name}")
    print(f"🧠 AI Model: {settings.gemini_live_model}")
    print(f"🎤 Voice: {settings.gemini_voice}")
    print(f"🔊 Audio: {settings.audio_format} @ {settings.audio_sample_rate}Hz")
    print(f"📞 Stasis App: {settings.stasis_app}")
    print(f"🌐 External Media: {settings.external_media_host}:{settings.external_media_port}")
    print("="*80)
    
    # Run the server
    uvicorn.run(
        "src.run_realtime_server:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower() if hasattr(settings, 'log_level') else "info",
        reload=False,  # Set to True for development
        access_log=True
    )


if __name__ == "__main__":
    main()