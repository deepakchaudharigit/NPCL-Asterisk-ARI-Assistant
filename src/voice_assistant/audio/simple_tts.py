#!/usr/bin/env python3
"""
Simple TTS fallback that works reliably on Windows without external dependencies.
This is a backup solution when both Google TTS and pyttsx3 fail.
"""

import subprocess
import sys
import os
import re
from typing import Optional


def clean_text_for_windows_tts(text: str, language_code: str = "en-IN") -> str:
    """Clean text specifically for Windows SAPI TTS"""
    
    # Basic cleaning
    cleaned_text = text
    
    # Remove problematic characters
    replacements = {
        '/': ' ',
        '\n': ' ',
        '\t': ' ',
        '।': '.',
        '॥': '.',
        '?': '.',
        '!': '.',
        '"': '',
        "'": '',
        '(': '',
        ')': '',
        '[': '',
        ']': '',
        '{': '',
        '}': '',
        '*': '',
        '#': '',
        '@': '',
        '$': '',
        '%': '',
        '^': '',
        '&': ' and ',
        '+': ' plus ',
        '=': ' equals ',
        '<': '',
        '>': '',
        '|': '',
        '\\': '',
        '~': '',
        '`': '',
    }
    
    # Apply replacements
    for old, new in replacements.items():
        cleaned_text = cleaned_text.replace(old, new)
    
    # For Hindi, convert to phonetic English
    if language_code == "hi-IN":
        # Convert Hindi text to phonetic English for better pronunciation
        hindi_to_phonetic = {
            'नमस्ते': 'namaste',
            'सर': 'sir',
            'मैडम': 'madam',
            'एनपीसीएल': 'N P C L',
            'नोएडा': 'noida',
            'पावर': 'power',
            'कॉर्पोरेशन': 'corporation',
            'लिमिटेड': 'limited',
            'ग्राहक': 'customer',
            'सेवा': 'service',
            'में': 'mein',
            'आपका': 'aapka',
            'स्वागत': 'swagat',
            'है': 'hai',
            'मैं': 'main',
            'आपकी': 'aapki',
            'कैसे': 'kaise',
            'मदद': 'madad',
            'कर': 'kar',
            'सकता': 'sakta',
            'सकती': 'sakti',
            'हूं': 'hun',
            'कृपया': 'kripaya',
            'मुझे': 'mujhe',
            'अपना': 'apna',
            'कनेक्शन': 'connection',
            'विवरण': 'vivaran',
            'या': 'ya',
            'शिकायत': 'complaint',
            'संख्या': 'number',
            'बताएं': 'batayen',
            'बिजली': 'electricity',
            'समस्या': 'problem',
            'का': 'ka',
            'सामना': 'samna',
            'कर': 'kar',
            'रहे': 'rahe',
            'हैं': 'hain',
            'दुःख': 'dukh',
            'क्षेत्र': 'area',
            'नहीं': 'nahin',
            'पूरा': 'pura',
            'पता': 'address',
            'और': 'aur',
            'नंबर': 'number',
            'ताकि': 'taki',
            'दर्ज': 'register',
            'सकूं': 'sakun',
            'जल्द': 'jald',
            'से': 'se',
            'समाधान': 'solution'
        }
        
        # Apply phonetic conversion
        for hindi, phonetic in hindi_to_phonetic.items():
            cleaned_text = cleaned_text.replace(hindi, phonetic)
    
    # Clean up multiple spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text


def speak_with_windows_sapi(text: str, language_code: str = "en-IN") -> bool:
    """Use Windows SAPI for TTS (most reliable on Windows)"""
    try:
        # Clean text
        cleaned_text = clean_text_for_windows_tts(text, language_code)
        
        if not cleaned_text or len(cleaned_text.strip()) < 2:
            return False
        
        print("🔊 Speaking (Windows SAPI)...")
        print(f"Text: {cleaned_text[:100]}..." if len(cleaned_text) > 100 else f"Text: {cleaned_text}")
        
        # Use PowerShell to call Windows SAPI\n        powershell_command = f'''\nAdd-Type -AssemblyName System.Speech\n$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer\n$speak.Rate = -2\n$speak.Volume = 100\n$speak.Speak(\"{cleaned_text}\")\n'''\n        \n        # Execute PowerShell command\n        result = subprocess.run(\n            [\"powershell\", \"-Command\", powershell_command],\n            capture_output=True,\n            text=True,\n            timeout=30\n        )\n        \n        if result.returncode == 0:\n            print(\"✅ Speech completed (Windows SAPI)\")\n            print()\n            return True\n        else:\n            print(f\"⚠️  Windows SAPI failed: {result.stderr}\")\n            return False\n            \n    except subprocess.TimeoutExpired:\n        print(\"⚠️  Windows SAPI timeout\")\n        return False\n    except Exception as e:\n        print(f\"⚠️  Windows SAPI error: {e}\")\n        return False\n\n\ndef speak_text_simple(text: str, language_code: str = \"en-IN\") -> bool:\n    \"\"\"Simple TTS that works on Windows without external dependencies\"\"\"\n    \n    # Skip empty text\n    if not text or len(text.strip()) < 2:\n        print(\"⚠️  Text too short for TTS\")\n        return False\n    \n    # Try Windows SAPI first (most reliable on Windows)\n    if sys.platform == \"win32\":\n        success = speak_with_windows_sapi(text, language_code)\n        if success:\n            return True\n    \n    # If Windows SAPI fails, try basic pyttsx3\n    try:\n        import pyttsx3\n        \n        cleaned_text = clean_text_for_windows_tts(text, language_code)\n        \n        engine = pyttsx3.init()\n        engine.setProperty('rate', 100)\n        engine.setProperty('volume', 1.0)\n        \n        print(\"🔊 Speaking (Basic TTS)...\")\n        print(f\"Text: {cleaned_text[:100]}...\" if len(cleaned_text) > 100 else f\"Text: {cleaned_text}\")\n        \n        engine.say(cleaned_text)\n        engine.runAndWait()\n        \n        try:\n            engine.stop()\n            del engine\n        except:\n            pass\n        \n        print(\"✅ Speech completed (Basic TTS)\")\n        print()\n        return True\n        \n    except Exception as e:\n        print(f\"⚠️  All TTS methods failed: {e}\")\n        print(\"💡 Text will be displayed only (no speech)\")\n        return False