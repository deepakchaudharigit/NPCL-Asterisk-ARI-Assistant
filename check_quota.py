#!/usr/bin/env python3
"""
Google API Quota Checker
Check your current API usage and quota status
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_quota_status():
    """Check Google API quota status"""
    try:
        from config.settings import get_settings
        import google.generativeai as genai
        
        settings = get_settings()
        
        print("🔍 Checking Google API Quota Status")
        print("=" * 40)
        
        # Configure API
        genai.configure(api_key=settings.google_api_key)
        
        # Test basic API
        print("1️⃣ Testing Basic Gemini API...")
        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content("Hello")
            print(f"   ✅ Basic API works: '{response.text[:50]}...'")
            basic_api_ok = True
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "exceeded" in error_str:
                print(f"   ❌ Quota exceeded: {e}")
                basic_api_ok = False
            else:
                print(f"   ❌ API error: {e}")
                basic_api_ok = False
        
        # Test Live API (if basic works)
        print("\n2️⃣ Testing Live API Access...")
        if basic_api_ok:
            try:
                import websockets
                import asyncio
                import json
                
                async def test_live_api():
                    ws_url = f"{settings.gemini_live_api_endpoint}?key={settings.google_api_key}"
                    
                    try:
                        ws = await websockets.connect(ws_url)
                        
                        setup_message = {
                            "setup": {
                                "model": f"models/{settings.gemini_live_model}",
                                "generationConfig": {
                                    "responseModalities": ["AUDIO"],
                                    "speechConfig": {
                                        "voiceConfig": {
                                            "prebuiltVoiceConfig": {"voiceName": settings.gemini_voice}
                                        }
                                    }
                                }
                            }
                        }
                        
                        await ws.send(json.dumps(setup_message))
                        
                        # Wait for response
                        response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        await ws.close()
                        
                        print("   ✅ Live API access confirmed")
                        return True
                        
                    except websockets.exceptions.InvalidStatusCode as e:
                        if e.status_code == 403:
                            print("   ❌ Live API: Access denied (quota or permissions)")
                        elif e.status_code == 429:
                            print("   ❌ Live API: Rate limited")
                        else:
                            print(f"   ❌ Live API: HTTP {e.status_code}")
                        return False
                    except Exception as e:
                        error_str = str(e).lower()
                        if "quota" in error_str or "exceeded" in error_str:
                            print(f"   ❌ Live API quota exceeded: {e}")
                        else:
                            print(f"   ❌ Live API error: {e}")
                        return False
                
                live_api_ok = asyncio.run(test_live_api())
                
            except Exception as e:
                print(f"   ❌ Live API test failed: {e}")
                live_api_ok = False
        else:
            print("   ⏭️  Skipped (basic API failed)")
            live_api_ok = False
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 Quota Status Summary:")
        print(f"   Basic Gemini API: {'✅ Available' if basic_api_ok else '❌ Quota Exceeded'}")
        print(f"   Live API: {'✅ Available' if live_api_ok else '❌ Not Available'}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        
        if not basic_api_ok:
            print("❌ CRITICAL: Basic API quota exceeded")
            print("   Solutions:")
            print("   1. Wait for quota reset (usually monthly)")
            print("   2. Upgrade your Google AI Studio plan")
            print("   3. Check billing settings at https://aistudio.google.com/")
            print("   4. Use a different API key if available")
            
        elif basic_api_ok and not live_api_ok:
            print("⚠️  Live API not available (normal for most users)")
            print("   Solutions:")
            print("   1. Use chat mode only (works with basic API)")
            print("   2. Request Live API access from Google")
            print("   3. Wait for Live API public release")
            
        else:
            print("🎉 All APIs available!")
            print("   You can use all modes: Voice, Chat, and Both")
        
        return basic_api_ok, live_api_ok
        
    except Exception as e:
        print(f"❌ Quota check failed: {e}")
        return False, False

def main():
    """Main quota checker"""
    print("🔍 Google API Quota Checker")
    print("Checking your current API access...")
    print()
    
    basic_ok, live_ok = check_quota_status()
    
    print("\n🚀 What you can do now:")
    
    if basic_ok:
        print("✅ Run chat mode: python src/main_with_options.py (choose option 2)")
        if live_ok:
            print("✅ Run voice mode: python src/main_with_options.py (choose option 1)")
            print("✅ Run both modes: python src/main_with_options.py (choose option 3)")
        else:
            print("⚠️  Voice mode unavailable (Live API quota/access issue)")
    else:
        print("❌ All modes unavailable (basic API quota exceeded)")
        print("💡 Fix quota issues first, then try again")
    
    return 0 if basic_ok else 1

if __name__ == "__main__":
    sys.exit(main())