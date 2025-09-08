@echo off
curl -X POST http://localhost:8000/ari/events ^
  -H "Content-Type: application/json" ^
  -d "{\"type\":\"StasisStart\",\"channel\":{\"id\":\"test-chan-001\"}}"
pause
