"""
Gemini 2.5 Flash client for voice assistant
"""

import logging
import time
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Gemini 2.5 Flash model"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google API key (if not provided, will use from settings)
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.google_api_key
        
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model with more permissive safety settings for voice assistant
        self.model = genai.GenerativeModel(
            model_name=self.settings.gemini_model,
            generation_config=genai.types.GenerationConfig(
                temperature=self.settings.temperature,
                max_output_tokens=self.settings.max_tokens,
                top_p=0.8,
                top_k=40
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
        )
        
        self.conversation_history: List[Dict[str, str]] = []
        self.consecutive_failures = 0
        
        logger.info(f"Gemini client initialized with model: {self.settings.gemini_model}")
    
    def generate_response(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a response using Gemini 2.5 Flash
        
        Args:
            user_input: User's input text
            system_prompt: Optional system prompt to set context
            
        Returns:
            Generated response text
        """
        try:
            # Add delay if there were previous failures to avoid rate limits
            if self.consecutive_failures > 0:
                delay = min(2 ** self.consecutive_failures, 10)  # Exponential backoff, max 10s
                logger.info(f"Adding {delay}s delay due to previous failures")
                time.sleep(delay)
            
            # Prepare the prompt
            if system_prompt:
                prompt = f"{system_prompt}\n\nUser: {user_input}\nAssistant:"
            else:
                prompt = self._build_conversation_prompt(user_input)
            
            logger.debug(f"Sending prompt to Gemini: {prompt[:100]}...")
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Check if we got a valid response
            if hasattr(response, 'text') and response.text:
                response_text = response.text.strip()
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": response_text})
                
                # Keep only last 10 exchanges to manage context length
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                self.consecutive_failures = 0  # Reset failure counter
                logger.info("Successfully generated response from Gemini")
                return response_text
            
            # Check if response was blocked by safety filters
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    logger.warning(f"Gemini response blocked by safety filter: {candidate.finish_reason}")
                    # Return a polite response about content filtering
                    return "I apologize, but I can't provide a response to that particular request. Could you try rephrasing your question?"
            
            # If we get here, something unexpected happened
            raise Exception("No usable response from Gemini")
                
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Gemini API error (attempt {self.consecutive_failures}): {e}")
            
            # Return fallback response
            return self._get_fallback_response(user_input)
    
    def _build_conversation_prompt(self, user_input: str) -> str:
        """Build conversation prompt with history"""
        system_prompt = self._get_default_system_prompt()
        
        prompt_parts = [system_prompt]
        
        # Add conversation history
        for exchange in self.conversation_history[-10:]:  # Last 5 exchanges
            if exchange["role"] == "user":
                prompt_parts.append(f"User: {exchange['content']}")
            else:
                prompt_parts.append(f"Assistant: {exchange['content']}")
        
        # Add current user input
        prompt_parts.append(f"User: {user_input}")
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for the assistant"""
        return f"""You are {self.settings.assistant_name}, a helpful and friendly voice assistant.

Your characteristics:
- Conversational and engaging personality
- Keep responses concise (1-3 sentences) since this is voice conversation
- Be natural, helpful, and show personality
- Provide accurate and helpful information
- Ask clarifying questions when needed
- Be professional but warm and approachable

Guidelines:
- This is a voice conversation, so keep responses brief and clear
- Speak naturally as if talking to a friend
- If you don't know something, admit it honestly
- Offer to help with related topics when appropriate
- Be encouraging and positive in your responses

Remember: You're having a voice conversation, so prioritize clarity and brevity."""
    
    def _get_fallback_response(self, user_input: str) -> str:
        """Generate fallback response when API fails"""
        user_lower = user_input.lower()
        
        # Context-aware fallback responses
        if any(word in user_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return f"Hello! I'm {self.settings.assistant_name}, your voice assistant. How can I help you today?"
        
        elif any(word in user_lower for word in ['help', 'assist', 'support']):
            return "I'm here to help! I can answer questions, provide information, or just have a conversation. What would you like to know?"
        
        elif any(word in user_lower for word in ['weather', 'temperature', 'forecast']):
            return "I'd love to help with weather information! For current conditions, I recommend checking a reliable weather service or app."
        
        elif any(word in user_lower for word in ['time', 'date', 'day']):
            return "For the current time and date, please check your device's clock. Is there something specific about time or scheduling I can help with?"
        
        elif any(word in user_lower for word in ['thank', 'thanks']):
            return "You're very welcome! I'm happy to help. Is there anything else you'd like to know?"
        
        else:
            fallback_responses = [
                "I'm having a brief connection issue with my AI service, but I'm still here! Could you try rephrasing your question?",
                "My AI brain is taking a quick break, but I'm listening! Feel free to ask something else or try again.",
                "I'm experiencing some technical difficulties right now. Could you try asking your question in a different way?",
                "Sorry, I'm having trouble accessing my full capabilities at the moment. What else would you like to talk about?"
            ]
            return fallback_responses[self.consecutive_failures % len(fallback_responses)]
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history.clear()
        self.consecutive_failures = 0
        logger.info("Conversation history reset")
    
    def test_connection(self) -> bool:
        """Test connection to Gemini API"""
        try:
            # Use a safe, simple test prompt
            test_prompt = "Hello, please respond with a simple greeting."
            response = self.model.generate_content(test_prompt)
            
            # Check if we got any response
            if hasattr(response, 'text') and response.text:
                logger.info("Gemini API connection test successful")
                return True
            elif hasattr(response, 'candidates') and response.candidates:
                # Check if response was blocked by safety filters
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    logger.warning(f"Gemini response blocked by safety filter: {candidate.finish_reason}")
                    # Still consider this a successful connection, just blocked content
                    return True
            
            logger.warning("Gemini API responded but with no usable content")
            return True  # Connection works, just content issue
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            # For connection test, we'll be more lenient
            if "Invalid operation" in str(e) or "finish_reason" in str(e):
                logger.info("Gemini API is accessible (content was filtered)")
                return True
            return False