"""
Main entry point for the Real-time Gemini Voice Assistant with Asterisk ARI.
This is the production-ready implementation with full Gemini Live API integration.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings, get_logging_settings
from src.voice_assistant.utils.logger import setup_logging
from src.voice_assistant.telephony.realtime_ari_handler import RealTimeARIHandler, RealTimeARIConfig


class GeminiVoiceAssistantApp:
    """Main application class for the Gemini Voice Assistant"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logging_settings = get_logging_settings()
        
        # Setup logging
        setup_logging(
            level=self.logging_settings.log_level,
            log_file=self.logging_settings.log_file
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize ARI handler
        self.ari_config = RealTimeARIConfig(
            ari_base_url=self.settings.ari_base_url,
            ari_username=self.settings.ari_username,
            ari_password=self.settings.ari_password,
            stasis_app=self.settings.stasis_app,
            external_media_host=self.settings.external_media_host,
            external_media_port=self.settings.external_media_port,
            auto_answer=self.settings.auto_answer_calls,
            enable_recording=self.settings.enable_call_recording,
            max_call_duration=self.settings.max_call_duration,
            audio_format=self.settings.audio_format,
            sample_rate=self.settings.audio_sample_rate
        )
        
        self.ari_handler = RealTimeARIHandler(self.ari_config)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        self.logger.info("Gemini Voice Assistant Application initialized")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the application"""
        try:
            self.logger.info("🚀 Starting Gemini Voice Assistant with Real-time ARI...")
            
            # Print startup information
            self.print_startup_info()
            
            # Start the ARI handler
            if await self.ari_handler.start():
                self.logger.info("✅ Gemini Voice Assistant started successfully!")
                self.print_status_info()
                
                # Keep the application running
                await self.run_forever()
            else:
                self.logger.error("❌ Failed to start Gemini Voice Assistant")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error starting application: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the application gracefully"""
        try:
            self.logger.info("🛑 Shutting down Gemini Voice Assistant...")
            
            # Stop the ARI handler
            await self.ari_handler.stop()
            
            self.logger.info("✅ Gemini Voice Assistant shutdown complete")
            
            # Exit the application
            sys.exit(0)
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
            sys.exit(1)
    
    async def run_forever(self):
        """Keep the application running"""
        try:
            while self.ari_handler.is_running:
                await asyncio.sleep(1)
                
                # Optional: Print periodic status updates
                if self.settings.enable_performance_logging:
                    await self.log_periodic_status()
                    
        except asyncio.CancelledError:
            self.logger.info("Application run loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in run loop: {e}")
            await self.shutdown()
    
    async def log_periodic_status(self):
        """Log periodic status information"""
        # This could be enhanced to log every N seconds
        pass
    
    def print_startup_info(self):
        """Print startup information"""
        print("\\n" + "="*80)
        print("🤖 GEMINI VOICE ASSISTANT - REAL-TIME ARI INTEGRATION")
        print("="*80)
        print(f"✅ Assistant Name: {self.settings.assistant_name}")
        print(f"✅ Gemini Live Model: {self.settings.gemini_live_model}")
        print(f"✅ Gemini Voice: {self.settings.gemini_voice}")
        print(f"✅ Audio Format: {self.settings.audio_format}")
        print(f"✅ Sample Rate: {self.settings.audio_sample_rate} Hz")
        print(f"✅ Stasis App: {self.settings.stasis_app}")
        print(f"✅ External Media: {self.settings.external_media_host}:{self.settings.external_media_port}")
        print(f"✅ ARI Endpoint: {self.settings.ari_base_url}")
        print(f"✅ Auto Answer: {self.settings.auto_answer_calls}")
        print(f"✅ Interruption Handling: {self.settings.enable_interruption_handling}")
        print("="*80)
    
    def print_status_info(self):
        """Print status information"""
        print("\\n📊 SYSTEM STATUS:")
        print("-" * 40)
        print("🟢 Gemini Live API: Connected")
        print("🟢 External Media Server: Running")
        print("🟢 Session Manager: Active")
        print("🟢 ARI Handler: Listening")
        print("-" * 40)
        print("\\n📞 READY FOR CALLS!")
        print("Call extension 1000 to start a conversation with Gemini")
        print("Call extension 1001 for external media testing")
        print("Call extension 1002 for basic audio testing")
        print("\\n💡 Press Ctrl+C to stop the assistant")
        print("="*80 + "\\n")


async def main():
    """Main entry point"""
    app = GeminiVoiceAssistantApp()
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 Application interrupted by user")
    except Exception as e:
        print(f"\\n❌ Fatal error: {e}")
        sys.exit(1)