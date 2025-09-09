#!/usr/bin/env python3
"""
Quick Test Script for NPCL Voice Assistant
Run this to quickly validate your setup
"""

import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_configuration():
    """Test basic configuration"""
    print("1️⃣ Testing Configuration...")
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        print(f"   ✅ Assistant Name: {settings.assistant_name}")
        print(f"   ✅ AI Model: {settings.gemini_model}")
        print(f"   ✅ API Key: {settings.google_api_key[:10]}...")
        return True
    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        return False

def test_gemini_client():
    """Test Gemini client"""
    print("\n2️⃣ Testing Gemini Client...")
    try:
        from voice_assistant.ai.gemini_client import GeminiClient
        
        client = GeminiClient()
        print("   ✅ Client initialized")
        
        # Test basic response
        start_time = time.time()
        response = client.generate_response("Hello")
        end_time = time.time()
        
        print(f"   ✅ Response received in {end_time - start_time:.2f}s")
        print(f"   📝 Response: '{response[:50]}...'")
        return True
    except Exception as e:
        print(f"   ❌ Gemini client failed: {e}")
        return False

def test_npcl_behavior():
    """Test NPCL-specific behavior"""
    print("\n3️⃣ Testing NPCL Behavior...")
    try:
        from voice_assistant.ai.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        # NPCL system instruction
        npcl_prompt = """You are a customer service assistant for NPCL (Noida Power Corporation Limited), a power utility company.

Your role:
- Help customers with power connection inquiries
- Handle complaint registration and status updates
- Provide professional customer service
- Use polite Indian English communication style

Communication style:
- Be respectful and use "Sir" or "Madam"
- Use Indian English phrases naturally
- Speak clearly and be helpful
- Keep responses concise and professional

Sample complaint number format: 0000054321
Always be ready to help with power-related issues."""
        
        # Test NPCL scenarios
        test_cases = [
            ("Hello", "Should greet professionally"),
            ("I have power outage", "Should offer help with power issue"),
            ("I want to register complaint", "Should offer complaint registration"),
        ]
        
        for user_input, expected in test_cases:
            print(f"\n   🧪 Testing: '{user_input}'")
            print(f"   📋 Expected: {expected}")
            
            response = client.generate_response(user_input, npcl_prompt)
            print(f"   🤖 Response: '{response[:80]}...'")
            
            # Check if response seems appropriate
            response_lower = response.lower()
            if any(word in response_lower for word in ['npcl', 'power', 'help', 'assist', 'sir', 'madam']):
                print("   ✅ Response seems NPCL-appropriate")
            else:
                print("   ⚠️  Response may not be NPCL-specific")
        
        return True
    except Exception as e:
        print(f"   ❌ NPCL behavior test failed: {e}")
        return False

def test_quota_status():
    """Test API quota status"""
    print("\n4️⃣ Testing API Quota...")
    try:
        import google.generativeai as genai
        from config.settings import get_settings
        
        settings = get_settings()
        genai.configure(api_key=settings.google_api_key)
        
        # Try a simple request
        model = genai.GenerativeModel(settings.gemini_model)
        response = model.generate_content("test")
        
        print("   ✅ Basic API quota available")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "quota" in error_str or "exceeded" in error_str:
            print("   ❌ API quota exceeded")
            print("   💡 You can still use chat mode with fallback responses")
        else:
            print(f"   ❌ API error: {e}")
        return False

def test_main_application():
    """Test if main application can start"""
    print("\n5️⃣ Testing Main Application Import...")
    try:
        from main import NPCLAssistant
        
        assistant = NPCLAssistant()
        print("   ✅ NPCLAssistant can be created")
        
        # Test system instruction
        instruction = assistant.get_npcl_system_instruction()
        if "NPCL" in instruction and "power" in instruction.lower():
            print("   ✅ NPCL system instruction looks good")
        else:
            print("   ⚠️  NPCL system instruction may need review")
        
        return True
    except Exception as e:
        print(f"   ❌ Main application test failed: {e}")
        return False

def main():
    """Run quick tests"""
    print("🧪 NPCL Voice Assistant - Quick Test")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Gemini Client", test_gemini_client),
        ("NPCL Behavior", test_npcl_behavior),
        ("API Quota", test_quota_status),
        ("Main Application", test_main_application),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your NPCL Voice Assistant is ready!")
        print("\n🚀 Next steps:")
        print("   1. Run: python src/main.py")
        print("   2. Choose option 2 (Chat Only)")
        print("   3. Test with: 'Hi' or 'I have power outage'")
    elif passed >= total * 0.8:
        print("\n✅ Most tests passed! Your assistant should work.")
        print("\n💡 Recommendations:")
        print("   - Use chat mode (option 2) for best results")
        print("   - Check failed tests above for any issues")
    else:
        print("\n⚠️  Several tests failed. Please check the issues above.")
        print("\n🔧 Common fixes:")
        print("   1. Check your .env file has GOOGLE_API_KEY")
        print("   2. Ensure virtual environment is active")
        print("   3. Run: pip install -r requirements.txt")
    
    return 0 if passed >= total * 0.8 else 1

if __name__ == "__main__":
    sys.exit(main())