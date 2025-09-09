# 🧪 How to Test NPCL Voice Assistant Project

## 🚀 Quick Start Testing

### **Step 1: Basic Setup Test**
```bash
# 1. Check if virtual environment is active
python --version
# Should show Python 3.8+ and (.venv) in prompt

# 2. Test configuration
python -c "from config.settings import get_settings; print('✅ Config OK')"

# 3. Test API key
python check_quota.py
```

### **Step 2: Run the Main Application**
```bash
python src/main.py
```

**Expected Output:**
```
🤖 NPCL Voice Assistant - Choose Your Mode
🎆 Powered by Gemini 2.5 Flash
======================================================================
✅ System Information:
   Assistant: NPCL Voice Assistant
   AI Model: gemini-2.5-flash
   Voice: Puck
✅ Virtual environment: Active
✅ Configuration: .env file found
✅ Google API Key: Configured

🎯 Choose Your Assistant Mode:
1. 🎤 Voice Only - Real-time voice conversation
2. 💬 Chat Only - Text-based conversation
3. 🎭 Both - Voice + Chat combined
4. ❌ Exit
```

## 🎯 Testing Each Mode

### **Mode 1: Chat Only (Recommended First Test)**

**Choose option 2** - This works even with quota issues.

**Test Scenarios:**

#### **Scenario 1: Basic Greeting**
```
👤 You: Hi
🤖 Expected: Welcome to NPCL customer service message
```

#### **Scenario 2: Power Outage**
```
👤 You: I have power outage in my area
🤖 Expected: Helpful response about power issues, asks for details
```

#### **Scenario 3: Complaint Registration**
```
👤 You: I want to register a complaint
🤖 Expected: Offers to help register complaint, asks for details
```

#### **Scenario 4: Billing Query**
```
👤 You: I have a question about my bill
🤖 Expected: Offers billing assistance, asks for more details
```

#### **Scenario 5: Connection Issues**
```
👤 You: My meter is not working
🤖 Expected: Helps with connection/meter issues
```

### **Mode 2: Voice Only (If Quota Available)**

**Choose option 1** - Tests WebSocket Live API.

**Expected Behavior:**
- Should connect to Gemini Live API
- Should handle voice input/output
- May fall back to chat if quota exceeded

### **Mode 3: Both Modes**

**Choose option 3** - Tests combined functionality.

**Test Flow:**
1. Choose 'T' for text
2. Test chat functionality
3. Choose 'V' for voice (if available)
4. Choose 'Q' to quit

## 🔧 Component Testing

### **Test 1: Configuration System**
```bash
python -c "
from config.settings import get_settings
settings = get_settings()
print(f'Assistant: {settings.assistant_name}')
print(f'Model: {settings.gemini_model}')
print(f'API Key: {settings.google_api_key[:10]}...')
"
```

### **Test 2: Gemini Client**
```bash
python -c "
from src.voice_assistant.ai.gemini_client import GeminiClient
client = GeminiClient()
response = client.generate_response('Hello')
print(f'Response: {response}')
"
```

### **Test 3: Quota Status**
```bash
python check_quota.py
```

**Expected Output:**
```
🔍 Checking Google API Quota Status
========================================
1️⃣ Testing Basic Gemini API...
   ✅ Basic API works: 'Hello! How can I help you today?'

2️⃣ Testing Live API Access...
   ❌ Live API: Access denied (quota or permissions)

📊 Quota Status Summary:
   Basic Gemini API: ✅ Available
   Live API: ❌ Not Available
```

## 🧪 Automated Test Suite

### **Run All Tests**
```bash
python run_all_tests.py
```

### **Run Specific Test Categories**
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Audio tests (if available)
pytest tests/audio/ -v

# Configuration tests
pytest tests/test_config.py -v
```

## 🎭 NPCL-Specific Testing

### **Test NPCL Scenarios**

Create a test script to validate NPCL behavior:

```bash
python -c "
from src.main import NPCLAssistant
import asyncio

async def test_npcl():
    assistant = NPCLAssistant()
    
    # Test system instruction
    instruction = assistant.get_npcl_system_instruction()
    print('System Instruction:', instruction[:100] + '...')
    
    # Test quota check
    quota_ok = await assistant.check_api_quota()
    print(f'Quota Available: {quota_ok}')

asyncio.run(test_npcl())
"
```

### **Manual NPCL Test Cases**

**Test Case 1: Customer Greeting**
```
Input: "Hello"
Expected: Professional NPCL greeting with offer to help
```

**Test Case 2: Power Outage Report**
```
Input: "There is no electricity in my area since morning"
Expected: Acknowledges power issue, asks for location/details
```

**Test Case 3: Complaint Number Inquiry**
```
Input: "What is the status of my complaint 0000054321"
Expected: Provides status update for the complaint number
```

**Test Case 4: New Complaint Registration**
```
Input: "I want to file a new complaint about voltage fluctuation"
Expected: Offers to register new complaint, asks for details
```

**Test Case 5: Billing Question**
```
Input: "My electricity bill is very high this month"
Expected: Offers billing assistance, asks for more information
```

## 🔍 Troubleshooting Tests

### **Test 1: API Key Issues**
```bash
# Test with invalid API key
GOOGLE_API_KEY="invalid" python src/main.py
# Should show configuration error
```

### **Test 2: Network Issues**
```bash
# Test without internet (disconnect network)
python src/main.py
# Should show connection errors but graceful fallbacks
```

### **Test 3: Quota Exceeded**
```bash
# If you have quota issues, test fallback responses
python src/main.py
# Choose option 2, should use fallback responses
```

## 📊 Performance Testing

### **Test Response Times**
```bash
python -c "
import time
from src.voice_assistant.ai.gemini_client import GeminiClient

client = GeminiClient()
start = time.time()
response = client.generate_response('Hello')
end = time.time()
print(f'Response time: {end - start:.2f} seconds')
print(f'Response: {response}')
"
```

### **Test Memory Usage**
```bash
# Monitor memory during operation
python -c "
import psutil
import os
from src.voice_assistant.ai.gemini_client import GeminiClient

process = psutil.Process(os.getpid())
print(f'Initial memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')

client = GeminiClient()
print(f'After client init: {process.memory_info().rss / 1024 / 1024:.1f} MB')

for i in range(5):
    response = client.generate_response(f'Test message {i}')
    print(f'After response {i}: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## 🎯 Success Criteria

### **✅ Basic Functionality**
- [ ] Application starts without errors
- [ ] Configuration loads correctly
- [ ] API key is validated
- [ ] Mode selection works

### **✅ Chat Mode**
- [ ] Responds to greetings appropriately
- [ ] Handles NPCL-specific queries
- [ ] Uses professional customer service tone
- [ ] Provides helpful fallback responses
- [ ] Maintains conversation context

### **✅ Voice Mode (If Available)**
- [ ] Connects to Live API
- [ ] Handles voice input/output
- [ ] Falls back gracefully if quota exceeded

### **✅ Error Handling**
- [ ] Graceful handling of API quota issues
- [ ] Appropriate fallback responses
- [ ] Clear error messages for users
- [ ] No application crashes

### **✅ NPCL Behavior**
- [ ] Professional customer service responses
- [ ] Power utility company context
- [ ] Indian English communication style
- [ ] Helpful responses for power-related queries

## 🚀 Quick Test Commands

```bash
# Full system test
python src/main.py

# Quick API test
python check_quota.py

# Configuration test
python -c "from config.settings import get_settings; print('✅ OK')"

# Unit tests
pytest tests/ -v

# Performance test
python -c "from src.voice_assistant.ai.gemini_client import GeminiClient; print(GeminiClient().generate_response('Hello'))"
```

## 📝 Test Results Template

```
NPCL Voice Assistant Test Results
================================

Date: ___________
Tester: _________

Basic Setup:
[ ] Virtual environment active
[ ] Configuration loads
[ ] API key valid
[ ] Dependencies installed

Chat Mode:
[ ] Starts successfully
[ ] Responds to greetings
[ ] Handles power queries
[ ] Professional tone
[ ] Fallback responses work

Voice Mode:
[ ] Connects to Live API
[ ] Voice input works
[ ] Voice output works
[ ] Graceful fallback

Error Handling:
[ ] Quota exceeded handled
[ ] Network issues handled
[ ] Invalid input handled
[ ] Graceful error messages

NPCL Behavior:
[ ] Customer service tone
[ ] Power utility context
[ ] Indian English style
[ ] Helpful responses

Overall Rating: ___/10
Comments: ________________
```

## 🎉 Ready to Test!

**Start with this simple test:**

```bash
python src/main.py
# Choose option 2 (Chat Only)
# Type: "Hi"
# Should get NPCL customer service response
```

**If that works, your project is ready!** 🚀