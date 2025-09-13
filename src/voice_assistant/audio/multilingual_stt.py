"""
Enhanced Speech-to-Text with multi-language support for NPCL Voice Assistant
Supports all Indian regional languages plus Bhojpuri and English
"""

import logging
import speech_recognition as sr
from typing import Optional, Tuple, Dict, List
from ..i18n.language_manager import LanguageManager, SupportedLanguage

logger = logging.getLogger(__name__)

class MultilingualSTT:
    """Enhanced Speech-to-Text with multi-language support"""
    
    def __init__(self, language_manager: LanguageManager):
        self.language_manager = language_manager
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # Language codes for speech recognition
        self.stt_language_codes = {
            SupportedLanguage.ENGLISH: "en-IN",
            SupportedLanguage.HINDI: "hi-IN",
            SupportedLanguage.BENGALI: "bn-IN",
            SupportedLanguage.TELUGU: "te-IN",
            SupportedLanguage.MARATHI: "mr-IN",
            SupportedLanguage.TAMIL: "ta-IN",
            SupportedLanguage.GUJARATI: "gu-IN",
            SupportedLanguage.URDU: "ur-IN",
            SupportedLanguage.KANNADA: "kn-IN",
            SupportedLanguage.ODIA: "or-IN",
            SupportedLanguage.MALAYALAM: "ml-IN",
            SupportedLanguage.BHOJPURI: "hi-IN",
        }
        
        # Initialize microphone
        self._initialize_microphone()
        
        # Recognition statistics
        self.stats = {
            "total_attempts": 0,
            "successful_recognitions": 0,
            "failed_recognitions": 0,
            "language_detections": 0,
            "by_language": {}
        }
        
        logger.info(f"MultilingualSTT initialized with {len(self.stt_language_codes)} languages")
    
    def _initialize_microphone(self):
        """Initialize and calibrate microphone"""
        try:
            self.microphone = sr.Microphone()
            self._calibrate_microphone()
            logger.info("Microphone initialized and calibrated successfully")
        except Exception as e:
            logger.error(f"Failed to initialize microphone: {e}")
            self.microphone = None
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        if not self.microphone:
            return
        
        try:
            with self.microphone as source:
                logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
            # Optimize recognition settings
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            
            logger.info("Microphone calibration completed")
        except Exception as e:
            logger.error(f"Microphone calibration failed: {e}")
    
    def listen_for_speech(self, language: Optional[SupportedLanguage] = None, 
                         timeout: float = 15.0, phrase_time_limit: float = 15.0) -> Tuple[bool, str, str]:
        """Listen for speech in specified language"""
        if not self.microphone:
            error_msg = "Microphone not available"
            logger.error(error_msg)
            return False, "", error_msg
        
        if language is None:
            language = self.language_manager.current_language
        
        if not language.voice_support:
            error_msg = f"Voice recognition not supported for {language.english_name}"
            logger.warning(error_msg)
            return False, "", error_msg
        
        self.stats["total_attempts"] += 1
        
        try:
            # Get language code for speech recognition
            lang_code = self.stt_language_codes.get(language, "en-IN")
            
            logger.info(f"Listening for speech in {language.english_name} ({lang_code})...")
            
            with self.microphone as source:
                # Listen for audio
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
            
            logger.info("Processing speech...")
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(
                audio, 
                language=lang_code
            )
            
            # Update statistics
            self.stats["successful_recognitions"] += 1
            lang_stats = self.stats["by_language"].get(language.code, {"success": 0, "failed": 0})
            lang_stats["success"] += 1
            self.stats["by_language"][language.code] = lang_stats
            
            logger.info(f"Recognized text in {language.english_name}: {text}")
            return True, text, ""
            
        except sr.WaitTimeoutError:
            error_msg = f"No speech detected within {timeout} seconds"
            logger.debug(error_msg)
            self._update_failed_stats(language)
            return False, "", error_msg
            
        except sr.UnknownValueError:
            error_msg = f"Could not understand speech in {language.english_name}"
            logger.warning(error_msg)
            self._update_failed_stats(language)
            return False, "", error_msg
            
        except sr.RequestError as e:
            error_msg = f"Speech recognition service error: {e}"
            logger.error(error_msg)
            self._update_failed_stats(language)
            return False, "", error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during speech recognition: {e}"
            logger.error(error_msg)
            self._update_failed_stats(language)
            return False, "", error_msg
    
    def _update_failed_stats(self, language: SupportedLanguage):
        """Update failure statistics"""
        self.stats["failed_recognitions"] += 1
        lang_stats = self.stats["by_language"].get(language.code, {"success": 0, "failed": 0})
        lang_stats["failed"] += 1
        self.stats["by_language"][language.code] = lang_stats
    
    def detect_language_from_speech(self, timeout: float = 10.0, 
                                   candidate_languages: Optional[List[SupportedLanguage]] = None) -> Optional[SupportedLanguage]:
        """Detect language from speech audio"""
        if not self.microphone:
            logger.error("Microphone not available for language detection")
            return None
        
        if candidate_languages is None:
            candidate_languages = [lang for lang in SupportedLanguage if lang.voice_support]
        
        try:
            logger.info("Listening for language detection...")
            
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5.0)
            
            best_confidence = 0.0
            detected_language = None
            
            logger.info(f"Testing {len(candidate_languages)} languages for detection...")
            
            for language in candidate_languages:
                try:
                    lang_code = self.stt_language_codes.get(language, "en-IN")
                    
                    # Try to recognize with this language
                    text = self.recognizer.recognize_google(audio, language=lang_code)
                    
                    # Simple confidence scoring based on text length and language patterns
                    confidence = self._calculate_language_confidence(text, language)
                    
                    logger.debug(f"Language {language.english_name}: confidence={confidence:.2f}, text='{text[:30]}...'")
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        detected_language = language
                        
                except (sr.UnknownValueError, sr.RequestError):
                    continue  # Try next language
            
            if detected_language:
                self.stats["language_detections"] += 1
                logger.info(f"Detected language: {detected_language.english_name} (confidence: {best_confidence:.2f})")
            else:
                logger.warning("Could not detect language from speech")
            
            return detected_language
            
        except sr.WaitTimeoutError:
            logger.warning("Timeout during language detection")
            return None
        except Exception as e:
            logger.error(f"Error during language detection: {e}")
            return None
    
    def _calculate_language_confidence(self, text: str, language: SupportedLanguage) -> float:
        """Calculate confidence score for language detection"""
        if not text:
            return 0.0
        
        # Base confidence from text length (longer text = more confident)
        length_confidence = min(len(text) / 50.0, 1.0)
        
        # Script-based confidence boost
        script_confidence = 0.0
        
        if language.script == "devanagari" and any('\\u0900' <= char <= '\\u097F' for char in text):
            script_confidence = 0.5
        elif language.script == "bengali" and any('\\u0980' <= char <= '\\u09FF' for char in text):
            script_confidence = 0.5
        elif language.script == "telugu" and any('\\u0C00' <= char <= '\\u0C7F' for char in text):
            script_confidence = 0.5
        elif language.script == "tamil" and any('\\u0B80' <= char <= '\\u0BFF' for char in text):
            script_confidence = 0.5
        elif language.script == "gujarati" and any('\\u0A80' <= char <= '\\u0AFF' for char in text):
            script_confidence = 0.5
        elif language.script == "arabic" and any('\\u0600' <= char <= '\\u06FF' for char in text):
            script_confidence = 0.5
        elif language.script == "kannada" and any('\\u0C80' <= char <= '\\u0CFF' for char in text):
            script_confidence = 0.5
        elif language.script == "odia" and any('\\u0B00' <= char <= '\\u0B7F' for char in text):
            script_confidence = 0.5
        elif language.script == "malayalam" and any('\\u0D00' <= char <= '\\u0D7F' for char in text):
            script_confidence = 0.5
        elif language.script == "devanagari" and any('\\u0900' <= char <= '\\u097F' for char in text):
            script_confidence = 0.5
        elif language.script == "latin" and all(ord(char) < 256 for char in text):
            script_confidence = 0.3  # Lower confidence for Latin script as it's common
        
        # Language-specific word patterns
        word_confidence = self._check_language_patterns(text, language)
        
        # Combine confidences
        total_confidence = (length_confidence * 0.3 + script_confidence * 0.5 + word_confidence * 0.2)
        
        return min(total_confidence, 1.0)
    
    def _check_language_patterns(self, text: str, language: SupportedLanguage) -> float:
        """Check for language-specific word patterns"""
        text_lower = text.lower()
        
        # Common words for each language
        patterns = {
            SupportedLanguage.HINDI: ['है', 'हैं', 'का', 'की', 'के', 'में', 'से', 'को', 'और', 'यह', 'वह'],
            SupportedLanguage.BENGALI: ['আছে', 'আছেন', 'এর', 'এই', 'সেই', 'এবং', 'কিন্তু', 'যে', 'যা'],
            SupportedLanguage.TELUGU: ['ఉంది', 'ఉన్నాయి', 'అని', 'ఈ', 'ఆ', 'మరియు', 'కానీ', 'ఎందుకంటే'],
            SupportedLanguage.MARATHI: ['आहे', 'आहेत', 'चा', 'ची', 'चे', 'मध्ये', 'आणि', 'पण', 'हे', 'ते'],
            SupportedLanguage.TAMIL: ['உள்ளது', 'உள்ளன', 'இந்த', 'அந்த', 'மற்றும்', 'ஆனால்', 'ஏனெனில்'],
            SupportedLanguage.GUJARATI: ['છે', 'છો', 'ના', 'નું', 'માં', 'અને', 'પણ', 'આ', 'તે'],
            SupportedLanguage.URDU: ['ہے', 'ہیں', 'کا', 'کی', 'کے', 'میں', 'سے', 'کو', 'اور', 'یہ'],
            SupportedLanguage.KANNADA: ['ಇದೆ', 'ಇವೆ', 'ಈ', 'ಆ', 'ಮತ್ತು', 'ಆದರೆ', 'ಏಕೆಂದರೆ'],
            SupportedLanguage.ODIA: ['ଅଛି', 'ଅଛନ୍ତି', 'ଏହି', 'ସେହି', 'ଏବଂ', 'କିନ୍ତୁ', 'କାରଣ'],
            SupportedLanguage.MALAYALAM: ['ഉണ്ട്', 'ഉണ്ടായിരുന്നു', 'ഇത്', 'അത്', 'ഒപ്പം', 'എന്നാൽ'],
            SupportedLanguage.BHOJPURI: ['बा', 'बानी', 'बाटे', 'करेला', 'होखे', 'रहल', 'जाला', 'रउआ', 'हमार'],
            SupportedLanguage.ENGLISH: ['is', 'are', 'the', 'and', 'or', 'but', 'this', 'that', 'with']
        }
        
        language_words = patterns.get(language, [])
        if not language_words:
            return 0.0
        
        # Count matches
        matches = sum(1 for word in language_words if word in text_lower)
        
        # Return confidence based on match ratio
        return min(matches / len(language_words), 1.0)
    
    def is_microphone_available(self) -> bool:
        """Check if microphone is available"""
        if not self.microphone:
            return False
        
        try:
            with self.microphone as source:
                pass  # Just try to access the microphone
            return True
        except Exception as e:
            logger.error(f"Microphone not available: {e}")
            return False
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages for STT"""
        supported = []
        for language in SupportedLanguage:
            if language.voice_support and language in self.stt_language_codes:
                supported.append({
                    "code": language.code,
                    "iso_code": language.iso_code,
                    "name": language.english_name,
                    "native_name": language.native_name,
                    "direction": language.direction,
                    "script": language.script,
                    "flag": language.flag,
                    "stt_code": self.stt_language_codes[language]
                })
        return supported
    
    def test_language_recognition(self, language: SupportedLanguage, timeout: float = 10.0) -> bool:
        """Test speech recognition for a specific language"""
        logger.info(f"Testing speech recognition for {language.english_name}")
        
        # Get test phrase
        test_phrase = self.language_manager.get_translation("voice_test", "voice_prompts", language)
        
        print(f"Please say: '{test_phrase}' in {language.english_name}")
        
        success, recognized_text, error = self.listen_for_speech(language, timeout, timeout)
        
        if success:
            logger.info(f"Recognition test successful: '{recognized_text}'")
            return True
        else:
            logger.warning(f"Recognition test failed: {error}")
            return False
    
    def get_recognition_statistics(self) -> Dict[str, any]:
        """Get speech recognition statistics"""
        total_attempts = self.stats["total_attempts"]
        success_rate = (self.stats["successful_recognitions"] / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            "total_attempts": total_attempts,
            "successful_recognitions": self.stats["successful_recognitions"],
            "failed_recognitions": self.stats["failed_recognitions"],
            "success_rate": round(success_rate, 2),
            "language_detections": self.stats["language_detections"],
            "by_language": self.stats["by_language"],
            "microphone_available": self.is_microphone_available(),
            "supported_languages": len(self.stt_language_codes)
        }
    
    def reset_statistics(self):
        """Reset recognition statistics"""
        self.stats = {
            "total_attempts": 0,
            "successful_recognitions": 0,
            "failed_recognitions": 0,
            "language_detections": 0,
            "by_language": {}
        }
        logger.info("Recognition statistics reset")
    
    def recalibrate_microphone(self):
        """Recalibrate microphone"""
        if self.microphone:
            self._calibrate_microphone()
            logger.info("Microphone recalibrated")
        else:
            logger.warning("Cannot recalibrate: microphone not available")