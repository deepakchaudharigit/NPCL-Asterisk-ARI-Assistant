"""
Function Calling System for Gemini Live API.
Provides infrastructure for tool calling and function execution.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Callable, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import inspect

from ..utils.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class FunctionParameter:
    """Function parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    enum_values: Optional[List[str]] = None
    default_value: Any = None


@dataclass
class FunctionDefinition:
    """Function definition for Gemini API"""
    name: str
    description: str
    parameters: List[FunctionParameter]
    behavior: str = "NON_BLOCKING"  # NON_BLOCKING or BLOCKING
    
    def to_gemini_format(self) -> Dict[str, Any]:
        """Convert to Gemini API function definition format"""
        properties = {}
        required_params = []
        
        for param in self.parameters:
            param_def = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum_values:
                param_def["enum"] = param.enum_values
            
            properties[param.name] = param_def
            
            if param.required:
                required_params.append(param.name)
        
        return {
            "name": self.name,
            "behavior": self.behavior,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_params
            }
        }


class BaseFunction(ABC):
    """Base class for callable functions"""
    
    @abstractmethod
    def get_definition(self) -> FunctionDefinition:
        """Get function definition"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the function"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and process parameters"""
        definition = self.get_definition()
        validated = {}
        
        for param in definition.parameters:
            if param.name in parameters:
                validated[param.name] = parameters[param.name]
            elif param.required and param.default_value is None:
                raise ValueError(f"Required parameter '{param.name}' is missing")
            elif param.default_value is not None:
                validated[param.name] = param.default_value
        
        return validated


class FunctionRegistry:
    """Registry for managing callable functions"""
    
    def __init__(self):
        self.functions: Dict[str, BaseFunction] = {}
        self.function_definitions: Dict[str, FunctionDefinition] = {}
        
        logger.info("Function Registry initialized")
    
    def register_function(self, function: BaseFunction):
        """Register a function"""
        definition = function.get_definition()
        self.functions[definition.name] = function
        self.function_definitions[definition.name] = definition
        
        logger.info(f"Registered function: {definition.name}")
    
    def unregister_function(self, function_name: str):
        """Unregister a function"""
        if function_name in self.functions:
            del self.functions[function_name]
            del self.function_definitions[function_name]
            logger.info(f"Unregistered function: {function_name}")
    
    def get_function(self, function_name: str) -> Optional[BaseFunction]:
        """Get a registered function"""
        return self.functions.get(function_name)
    
    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Get all function definitions in Gemini format"""
        return [definition.to_gemini_format() for definition in self.function_definitions.values()]
    
    def list_functions(self) -> List[str]:
        """List all registered function names"""
        return list(self.functions.keys())
    
    async def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function with parameters"""
        function = self.get_function(function_name)
        
        if not function:
            raise ValueError(f"Function '{function_name}' not found")
        
        try:
            # Validate parameters
            validated_params = function.validate_parameters(parameters)
            
            # Execute function
            result = await function.execute(**validated_params)
            
            logger.info(f"Function '{function_name}' executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error executing function '{function_name}': {e}")
            raise


class FunctionCallHandler:
    """Handles function calls from Gemini Live API"""
    
    def __init__(self, registry: FunctionRegistry):
        self.registry = registry
        self.pending_calls: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Function Call Handler initialized")
    
    async def handle_function_call(self, function_call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a function call from Gemini API.
        
        Args:
            function_call_data: Function call data from Gemini
            
        Returns:
            Function response in Gemini format
        """
        try:
            function_name = function_call_data.get("name")
            function_args = function_call_data.get("args", {})
            call_id = function_call_data.get("id", f"call_{int(asyncio.get_event_loop().time() * 1000)}")
            
            logger.info(f"Handling function call: {function_name} with args: {function_args}")
            
            # Track performance
            perf_id = performance_monitor.start_operation("function_call", call_id)
            
            # Store pending call
            self.pending_calls[call_id] = {
                "function_name": function_name,
                "args": function_args,
                "start_time": asyncio.get_event_loop().time()
            }
            
            # Execute function
            result = await self.registry.execute_function(function_name, function_args)
            
            # Remove from pending calls
            self.pending_calls.pop(call_id, None)
            
            # Format response for Gemini
            response = {
                "functionResponse": {
                    "name": function_name,
                    "response": {
                        "result": self._format_result(result)
                    }
                }
            }
            
            if "id" in function_call_data:
                response["functionResponse"]["id"] = function_call_data["id"]
            
            # End performance tracking
            performance_monitor.end_operation(perf_id, "function_call", True)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling function call: {e}")
            
            # End performance tracking with failure if perf_id exists
            try:
                performance_monitor.end_operation(perf_id, "function_call", False)
            except Exception:
                pass
            
            # Remove from pending calls
            call_id = function_call_data.get("id")
            if call_id:
                self.pending_calls.pop(call_id, None)
            
            # Return error response
            return {
                "functionResponse": {
                    "name": function_call_data.get("name", "unknown"),
                    "response": {
                        "error": str(e)
                    }
                }
            }
    
    def _format_result(self, result: Any) -> str:
        """Format function result for Gemini API"""
        if isinstance(result, dict):
            # Convert dict to readable string
            if "result" in result:
                return str(result["result"])
            else:
                # Format dict as readable text instead of JSON
                items = []
                for key, value in result.items():
                    items.append(f"{key}: {value}")
                return ", ".join(items)
        elif isinstance(result, (list, tuple)):
            return json.dumps(result)
        else:
            return str(result)
    
    def get_pending_calls(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending function calls"""
        return self.pending_calls.copy()
    
    def cancel_pending_call(self, call_id: str) -> bool:
        """Cancel a pending function call"""
        if call_id in self.pending_calls:
            del self.pending_calls[call_id]
            logger.info(f"Cancelled pending function call: {call_id}")
            return True
        return False


# Decorator for easy function registration
def gemini_function(name: str, description: str, parameters: List[FunctionParameter], 
                   behavior: str = "NON_BLOCKING"):
    """Decorator to create a Gemini function from a regular function"""
    
    def decorator(func: Callable):
        class DecoratedFunction(BaseFunction):
            def get_definition(self) -> FunctionDefinition:
                return FunctionDefinition(
                    name=name,
                    description=description,
                    parameters=parameters,
                    behavior=behavior
                )
            
            async def execute(self, **kwargs) -> Dict[str, Any]:
                if inspect.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)
                
                return {"result": result}
        
        return DecoratedFunction()
    
    return decorator


# Global registry instance
function_registry = FunctionRegistry()
function_call_handler = FunctionCallHandler(function_registry)