"""
Test cases for Function Calling System.
Tests function registration, execution, and Gemini API integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.voice_assistant.ai.function_calling import (
    FunctionParameter, FunctionDefinition, BaseFunction, FunctionRegistry,
    FunctionCallHandler, gemini_function, function_registry, function_call_handler
)


class TestFunctionParameter:
    """Test cases for FunctionParameter"""
    
    def test_initialization(self):
        """Test parameter initialization"""
        param = FunctionParameter(
            name="location",
            type="string",
            description="City name",
            required=True,
            enum_values=["Delhi", "Mumbai"],
            default_value="Delhi"
        )
        
        assert param.name == "location"
        assert param.type == "string"
        assert param.description == "City name"
        assert param.required == True
        assert param.enum_values == ["Delhi", "Mumbai"]
        assert param.default_value == "Delhi"
    
    def test_default_values(self):
        """Test parameter default values"""
        param = FunctionParameter(
            name="test",
            type="string",
            description="Test parameter"
        )
        
        assert param.required == True
        assert param.enum_values is None
        assert param.default_value is None


class TestFunctionDefinition:
    """Test cases for FunctionDefinition"""
    
    def test_initialization(self):
        """Test function definition initialization"""
        parameters = [
            FunctionParameter("location", "string", "City name", True),
            FunctionParameter("units", "string", "Temperature units", False, ["C", "F"], "C")
        ]
        
        definition = FunctionDefinition(
            name="get_weather",
            description="Get weather information",
            parameters=parameters,
            behavior="NON_BLOCKING"
        )
        
        assert definition.name == "get_weather"
        assert definition.description == "Get weather information"
        assert len(definition.parameters) == 2
        assert definition.behavior == "NON_BLOCKING"
    
    def test_to_gemini_format(self):
        """Test conversion to Gemini API format"""
        parameters = [
            FunctionParameter("location", "string", "City name", True),
            FunctionParameter("units", "string", "Temperature units", False, ["C", "F"], "C")
        ]
        
        definition = FunctionDefinition(
            name="get_weather",
            description="Get weather information",
            parameters=parameters
        )
        
        gemini_format = definition.to_gemini_format()
        
        # Check structure
        assert gemini_format["name"] == "get_weather"
        assert gemini_format["description"] == "Get weather information"
        assert gemini_format["behavior"] == "NON_BLOCKING"
        
        # Check parameters
        params = gemini_format["parameters"]
        assert params["type"] == "object"
        assert "location" in params["properties"]
        assert "units" in params["properties"]
        assert params["required"] == ["location"]
        
        # Check parameter details
        location_param = params["properties"]["location"]
        assert location_param["type"] == "string"
        assert location_param["description"] == "City name"
        
        units_param = params["properties"]["units"]
        assert units_param["enum"] == ["C", "F"]


class MockFunction(BaseFunction):
    """Mock function for testing"""
    
    def __init__(self, name="test_function", should_fail=False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0
        self.last_kwargs = None
    
    def get_definition(self) -> FunctionDefinition:
        return FunctionDefinition(
            name=self.name,
            description="Test function",
            parameters=[
                FunctionParameter("param1", "string", "Test parameter", True),
                FunctionParameter("param2", "integer", "Optional parameter", False, default_value=42)
            ]
        )
    
    async def execute(self, **kwargs) -> dict:
        self.call_count += 1
        self.last_kwargs = kwargs
        
        if self.should_fail:
            raise ValueError("Test function failure")
        
        return {"result": f"Success with {kwargs}"}


class TestBaseFunction:
    """Test cases for BaseFunction"""
    
    def test_validate_parameters_success(self):
        """Test successful parameter validation"""
        function = MockFunction()
        parameters = {"param1": "test_value", "param2": 100}
        
        validated = function.validate_parameters(parameters)
        
        assert validated["param1"] == "test_value"
        assert validated["param2"] == 100
    
    def test_validate_parameters_with_defaults(self):
        """Test parameter validation with default values"""
        function = MockFunction()
        parameters = {"param1": "test_value"}  # param2 missing but has default
        
        validated = function.validate_parameters(parameters)
        
        assert validated["param1"] == "test_value"
        assert validated["param2"] == 42  # Default value
    
    def test_validate_parameters_missing_required(self):
        """Test parameter validation with missing required parameter"""
        function = MockFunction()
        parameters = {"param2": 100}  # param1 missing and required
        
        with pytest.raises(ValueError, match="Required parameter 'param1' is missing"):
            function.validate_parameters(parameters)
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful function execution"""
        function = MockFunction()
        result = await function.execute(param1="test", param2=123)
        
        assert function.call_count == 1
        assert function.last_kwargs == {"param1": "test", "param2": 123}
        assert result["result"] == "Success with {'param1': 'test', 'param2': 123}"
    
    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test function execution failure"""
        function = MockFunction(should_fail=True)
        
        with pytest.raises(ValueError, match="Test function failure"):
            await function.execute(param1="test")


class TestFunctionRegistry:
    """Test cases for FunctionRegistry"""
    
    def setup_method(self):
        """Setup for each test"""
        self.registry = FunctionRegistry()
    
    def test_initialization(self):
        """Test registry initialization"""
        assert len(self.registry.functions) == 0
        assert len(self.registry.function_definitions) == 0
    
    def test_register_function(self):
        """Test function registration"""
        function = MockFunction("test_func")
        self.registry.register_function(function)
        
        assert "test_func" in self.registry.functions
        assert "test_func" in self.registry.function_definitions
        assert self.registry.get_function("test_func") == function
    
    def test_unregister_function(self):
        """Test function unregistration"""
        function = MockFunction("test_func")
        self.registry.register_function(function)
        
        # Verify registered
        assert "test_func" in self.registry.functions
        
        # Unregister
        self.registry.unregister_function("test_func")
        
        # Verify unregistered
        assert "test_func" not in self.registry.functions
        assert "test_func" not in self.registry.function_definitions
    
    def test_get_function_not_found(self):
        """Test getting non-existent function"""
        result = self.registry.get_function("nonexistent")
        assert result is None
    
    def test_get_all_definitions(self):
        """Test getting all function definitions"""
        function1 = MockFunction("func1")
        function2 = MockFunction("func2")
        
        self.registry.register_function(function1)
        self.registry.register_function(function2)
        
        definitions = self.registry.get_all_definitions()
        
        assert len(definitions) == 2
        assert all("name" in defn for defn in definitions)
        assert all("description" in defn for defn in definitions)
        assert all("parameters" in defn for defn in definitions)
    
    def test_list_functions(self):
        """Test listing function names"""
        function1 = MockFunction("func1")
        function2 = MockFunction("func2")
        
        self.registry.register_function(function1)
        self.registry.register_function(function2)
        
        function_names = self.registry.list_functions()
        
        assert len(function_names) == 2
        assert "func1" in function_names
        assert "func2" in function_names
    
    @pytest.mark.asyncio
    async def test_execute_function_success(self):
        """Test successful function execution through registry"""
        function = MockFunction("test_func")
        self.registry.register_function(function)
        
        result = await self.registry.execute_function("test_func", {"param1": "test"})
        
        assert function.call_count == 1
        assert result["result"] == "Success with {'param1': 'test', 'param2': 42}"
    
    @pytest.mark.asyncio
    async def test_execute_function_not_found(self):
        """Test executing non-existent function"""
        with pytest.raises(ValueError, match="Function 'nonexistent' not found"):
            await self.registry.execute_function("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_execute_function_validation_error(self):
        """Test function execution with validation error"""
        function = MockFunction("test_func")
        self.registry.register_function(function)
        
        with pytest.raises(ValueError, match="Required parameter 'param1' is missing"):
            await self.registry.execute_function("test_func", {"param2": 100})
    
    @pytest.mark.asyncio
    async def test_execute_function_execution_error(self):
        """Test function execution with execution error"""
        function = MockFunction("test_func", should_fail=True)
        self.registry.register_function(function)
        
        with pytest.raises(ValueError, match="Test function failure"):
            await self.registry.execute_function("test_func", {"param1": "test"})


class TestFunctionCallHandler:
    """Test cases for FunctionCallHandler"""
    
    def setup_method(self):
        """Setup for each test"""
        self.registry = FunctionRegistry()
        self.handler = FunctionCallHandler(self.registry)
    
    def test_initialization(self):
        """Test handler initialization"""
        assert self.handler.registry == self.registry
        assert len(self.handler.pending_calls) == 0
    
    @pytest.mark.asyncio
    async def test_handle_function_call_success(self):
        """Test successful function call handling"""
        function = MockFunction("test_func")
        self.registry.register_function(function)
        
        function_call_data = {
            "name": "test_func",
            "args": {"param1": "test_value"},
            "id": "call_123"
        }
        
        response = await self.handler.handle_function_call(function_call_data)
        
        # Check response structure
        assert "functionResponse" in response
        func_response = response["functionResponse"]
        assert func_response["name"] == "test_func"
        assert func_response["id"] == "call_123"
        assert "response" in func_response
        assert "result" in func_response["response"]
        
        # Check function was called
        assert function.call_count == 1
        
        # Check no pending calls
        assert len(self.handler.pending_calls) == 0
    
    @pytest.mark.asyncio
    async def test_handle_function_call_error(self):
        """Test function call handling with error"""
        function = MockFunction("test_func", should_fail=True)
        self.registry.register_function(function)
        
        function_call_data = {
            "name": "test_func",
            "args": {"param1": "test_value"}
        }
        
        response = await self.handler.handle_function_call(function_call_data)
        
        # Check error response
        assert "functionResponse" in response
        func_response = response["functionResponse"]
        assert func_response["name"] == "test_func"
        assert "error" in func_response["response"]
    
    @pytest.mark.asyncio
    async def test_handle_function_call_not_found(self):
        """Test handling call to non-existent function"""
        function_call_data = {
            "name": "nonexistent_func",
            "args": {}
        }
        
        response = await self.handler.handle_function_call(function_call_data)
        
        # Check error response
        assert "functionResponse" in response
        func_response = response["functionResponse"]
        assert func_response["name"] == "nonexistent_func"
        assert "error" in func_response["response"]
    
    def test_get_pending_calls(self):
        """Test getting pending calls"""
        # Initially empty
        pending = self.handler.get_pending_calls()
        assert len(pending) == 0
        
        # Add a pending call manually
        self.handler.pending_calls["call_123"] = {
            "function_name": "test_func",
            "args": {"param1": "test"},
            "start_time": 12345
        }
        
        pending = self.handler.get_pending_calls()
        assert len(pending) == 1
        assert "call_123" in pending
    
    def test_cancel_pending_call(self):
        """Test cancelling pending calls"""
        # Add a pending call
        self.handler.pending_calls["call_123"] = {
            "function_name": "test_func",
            "args": {"param1": "test"},
            "start_time": 12345
        }
        
        # Cancel it
        result = self.handler.cancel_pending_call("call_123")
        assert result == True
        assert len(self.handler.pending_calls) == 0
        
        # Try to cancel non-existent call
        result = self.handler.cancel_pending_call("nonexistent")
        assert result == False
    
    def test_format_result_dict(self):
        """Test result formatting for dictionary"""
        result = {"temperature": "25°C", "condition": "sunny"}
        formatted = self.handler._format_result(result)
        
        # Should be JSON string
        assert isinstance(formatted, str)
        assert "temperature" in formatted
        assert "25°C" in formatted
    
    def test_format_result_dict_with_result_key(self):
        """Test result formatting for dictionary with result key"""
        result = {"result": "Weather is sunny"}
        formatted = self.handler._format_result(result)
        
        assert formatted == "Weather is sunny"
    
    def test_format_result_list(self):
        """Test result formatting for list"""
        result = ["item1", "item2", "item3"]
        formatted = self.handler._format_result(result)
        
        assert isinstance(formatted, str)
        assert "item1" in formatted
    
    def test_format_result_string(self):
        """Test result formatting for string"""
        result = "Simple string result"
        formatted = self.handler._format_result(result)
        
        assert formatted == "Simple string result"


class TestGeminiFunctionDecorator:
    """Test cases for gemini_function decorator"""
    
    def test_decorator_basic(self):
        """Test basic decorator usage"""
        @gemini_function(
            name="test_decorated",
            description="Test decorated function",
            parameters=[
                FunctionParameter("input", "string", "Input parameter", True)
            ]
        )
        def test_func(input: str) -> str:
            return f"Processed: {input}"
        
        # Check it's a BaseFunction
        assert isinstance(test_func, BaseFunction)
        
        # Check definition
        definition = test_func.get_definition()
        assert definition.name == "test_decorated"
        assert definition.description == "Test decorated function"
        assert len(definition.parameters) == 1
    
    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator with async function"""
        @gemini_function(
            name="test_async",
            description="Test async function",
            parameters=[
                FunctionParameter("value", "integer", "Input value", True)
            ]
        )
        async def async_test_func(value: int) -> int:
            await asyncio.sleep(0.001)  # Simulate async work
            return value * 2
        
        # Execute function
        result = await async_test_func.execute(value=5)
        
        assert result["result"] == 10
    
    @pytest.mark.asyncio
    async def test_decorator_sync_function(self):
        """Test decorator with sync function"""
        @gemini_function(
            name="test_sync",
            description="Test sync function",
            parameters=[
                FunctionParameter("text", "string", "Input text", True)
            ]
        )
        def sync_test_func(text: str) -> str:
            return text.upper()
        
        # Execute function
        result = await sync_test_func.execute(text="hello")
        
        assert result["result"] == "HELLO"


class TestGlobalInstances:
    """Test cases for global instances"""
    
    def test_global_registry(self):
        """Test global function registry"""
        assert function_registry is not None
        assert isinstance(function_registry, FunctionRegistry)
    
    def test_global_handler(self):
        """Test global function call handler"""
        assert function_call_handler is not None
        assert isinstance(function_call_handler, FunctionCallHandler)
        assert function_call_handler.registry == function_registry


if __name__ == "__main__":
    pytest.main([__file__])