"""
Tests for Gemini client
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from voice_assistant.ai.gemini_client import GeminiClient


class TestGeminiClient:
    """Test cases for GeminiClient"""
    
    @patch('voice_assistant.ai.gemini_client.genai.configure')
    @patch('voice_assistant.ai.gemini_client.genai.GenerativeModel')
    def test_init(self, mock_model, mock_configure):
        """Test client initialization"""
        with patch('voice_assistant.ai.gemini_client.get_settings') as mock_settings:
            mock_settings.return_value.google_api_key = "test-key"
            mock_settings.return_value.gemini_model = "gemini-2.5-flash"
            mock_settings.return_value.temperature = 0.7
            mock_settings.return_value.max_tokens = 150
            
            client = GeminiClient()
            
            mock_configure.assert_called_once_with(api_key="test-key")
            assert client.api_key == "test-key"
    
    def test_init_no_api_key(self):
        """Test initialization without API key"""
        with patch('voice_assistant.ai.gemini_client.get_settings') as mock_settings:
            mock_settings.return_value.google_api_key = None
            
            with pytest.raises(ValueError, match="Google API key is required"):
                GeminiClient()
    
    @patch('voice_assistant.ai.gemini_client.genai.configure')
    @patch('voice_assistant.ai.gemini_client.genai.GenerativeModel')
    def test_generate_response(self, mock_model_class, mock_configure):
        """Test response generation"""
        with patch('voice_assistant.ai.gemini_client.get_settings') as mock_settings:
            mock_settings.return_value.google_api_key = "test-key"
            mock_settings.return_value.gemini_model = "gemini-2.5-flash"
            mock_settings.return_value.temperature = 0.7
            mock_settings.return_value.max_tokens = 150
            
            # Mock the model and response
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = "Test response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            client = GeminiClient()
            response = client.generate_response("Hello")
            
            assert response == "Test response"
            assert len(client.conversation_history) == 2  # User + assistant
    
    @patch('voice_assistant.ai.gemini_client.genai.configure')
    @patch('voice_assistant.ai.gemini_client.genai.GenerativeModel')
    def test_fallback_response(self, mock_model_class, mock_configure):
        """Test fallback response on API failure"""
        with patch('voice_assistant.ai.gemini_client.get_settings') as mock_settings:
            mock_settings.return_value.google_api_key = "test-key"
            mock_settings.return_value.gemini_model = "gemini-2.5-flash"
            mock_settings.return_value.temperature = 0.7
            mock_settings.return_value.max_tokens = 150
            mock_settings.return_value.assistant_name = "ARI"
            
            # Mock the model to raise an exception
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model
            
            client = GeminiClient()
            response = client.generate_response("Hello")
            
            # Should return fallback response
            assert "ARI" in response or "Hello" in response
            assert client.consecutive_failures == 1