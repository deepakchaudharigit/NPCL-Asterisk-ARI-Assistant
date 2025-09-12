"""
Centralized dependency management for graceful handling of missing modules.
Provides consistent import handling and fallback mechanisms across the application.
"""

import logging
import importlib
import sys
from typing import Any, Dict, Optional, Type, Union, Callable
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a dependency"""
    name: str
    module_path: str
    fallback: Optional[Any] = None
    required: bool = False
    install_command: Optional[str] = None
    description: Optional[str] = None


class DependencyManager:
    """Centralized dependency management system"""
    
    def __init__(self):
        self._loaded_modules: Dict[str, Any] = {}
        self._failed_imports: Dict[str, Exception] = {}
        self._dependencies: Dict[str, DependencyInfo] = {}
        
        # Register core dependencies
        self._register_core_dependencies()
    
    def _register_core_dependencies(self):
        """Register core application dependencies"""
        dependencies = [
            DependencyInfo(
                name="websockets",
                module_path="websockets",
                required=True,
                install_command="pip install websockets",
                description="WebSocket communication for Gemini Live API"
            ),
            DependencyInfo(
                name="google_generativeai",
                module_path="google.generativeai",
                required=True,
                install_command="pip install google-generativeai",
                description="Google Gemini AI integration"
            ),
            DependencyInfo(
                name="speech_recognition",
                module_path="speech_recognition",
                required=False,
                install_command="pip install SpeechRecognition",
                description="Speech recognition capabilities"
            ),
            DependencyInfo(
                name="pyttsx3",
                module_path="pyttsx3",
                required=False,
                install_command="pip install pyttsx3",
                description="Text-to-speech functionality"
            ),
            DependencyInfo(
                name="numpy",
                module_path="numpy",
                required=True,
                install_command="pip install numpy",
                description="Audio processing and numerical operations"
            ),
            DependencyInfo(
                name="fastapi",
                module_path="fastapi",
                required=True,
                install_command="pip install fastapi",
                description="Web framework for API endpoints"
            ),
            DependencyInfo(
                name="uvicorn",
                module_path="uvicorn",
                required=True,
                install_command="pip install uvicorn",
                description="ASGI server for FastAPI"
            ),
            DependencyInfo(
                name="pydantic",
                module_path="pydantic",
                required=True,
                install_command="pip install pydantic",
                description="Data validation and serialization"
            ),
            DependencyInfo(
                name="requests",
                module_path="requests",
                required=True,
                install_command="pip install requests",
                description="HTTP client for API communication"
            ),
            DependencyInfo(
                name="psutil",
                module_path="psutil",
                required=False,
                install_command="pip install psutil",
                description="System monitoring and performance metrics"
            )
        ]
        
        for dep in dependencies:
            self._dependencies[dep.name] = dep
    
    def import_module(self, name: str, module_path: Optional[str] = None, 
                     fallback: Optional[Any] = None, required: bool = False) -> Any:
        """
        Import a module with graceful error handling
        
        Args:
            name: Dependency name for tracking
            module_path: Module import path (defaults to name)
            fallback: Fallback value if import fails
            required: Whether this is a required dependency
            
        Returns:
            Imported module or fallback value
            
        Raises:
            ImportError: If required dependency cannot be imported
        """
        if module_path is None:
            module_path = name
        
        # Check if already loaded
        if name in self._loaded_modules:
            return self._loaded_modules[name]
        
        # Check if previously failed
        if name in self._failed_imports and required:
            raise self._failed_imports[name]
        
        try:
            module = importlib.import_module(module_path)
            self._loaded_modules[name] = module
            logger.debug(f"Successfully imported {name} from {module_path}")
            return module
            
        except ImportError as e:
            self._failed_imports[name] = e
            
            # Get dependency info
            dep_info = self._dependencies.get(name)
            
            if required:
                error_msg = f"Required dependency '{name}' not found"
                if dep_info and dep_info.install_command:
                    error_msg += f". Install with: {dep_info.install_command}"
                logger.error(error_msg)
                raise ImportError(error_msg) from e
            else:
                logger.warning(f"Optional dependency '{name}' not available: {e}")
                if dep_info and dep_info.install_command:
                    logger.warning(f"Install with: {dep_info.install_command}")
                
                # Use fallback or None
                fallback_value = fallback if fallback is not None else dep_info.fallback if dep_info else None
                self._loaded_modules[name] = fallback_value
                return fallback_value
    
    def import_from_module(self, name: str, module_path: str, item: str,
                          fallback: Optional[Any] = None, required: bool = False) -> Any:
        """
        Import specific item from a module
        
        Args:
            name: Dependency name for tracking
            module_path: Module import path
            item: Specific item to import from module
            fallback: Fallback value if import fails
            required: Whether this is a required dependency
            
        Returns:
            Imported item or fallback value
        """
        cache_key = f"{name}.{item}"
        
        # Check if already loaded
        if cache_key in self._loaded_modules:
            return self._loaded_modules[cache_key]
        
        try:
            module = self.import_module(name, module_path, required=required)
            if module is None:
                if required:
                    raise ImportError(f"Cannot import {item} from {module_path}: module not available")
                self._loaded_modules[cache_key] = fallback
                return fallback
            
            imported_item = getattr(module, item)
            self._loaded_modules[cache_key] = imported_item
            logger.debug(f"Successfully imported {item} from {module_path}")
            return imported_item
            
        except (ImportError, AttributeError) as e:
            self._failed_imports[cache_key] = e
            
            if required:
                error_msg = f"Required item '{item}' not found in module '{module_path}'"
                logger.error(error_msg)
                raise ImportError(error_msg) from e
            else:
                logger.warning(f"Optional item '{item}' not available from {module_path}: {e}")
                self._loaded_modules[cache_key] = fallback
                return fallback
    
    def check_dependencies(self, required_only: bool = False) -> Dict[str, bool]:
        """
        Check status of all registered dependencies
        
        Args:
            required_only: Only check required dependencies
            
        Returns:
            Dictionary mapping dependency names to availability status
        """
        status = {}
        
        for name, dep_info in self._dependencies.items():
            if required_only and not dep_info.required:
                continue
            
            try:
                self.import_module(name, dep_info.module_path, required=False)
                status[name] = name in self._loaded_modules and self._loaded_modules[name] is not None
            except Exception:
                status[name] = False
        
        return status
    
    def get_missing_dependencies(self, required_only: bool = False) -> Dict[str, DependencyInfo]:
        """
        Get information about missing dependencies
        
        Args:
            required_only: Only check required dependencies
            
        Returns:
            Dictionary of missing dependencies with their info
        """
        missing = {}
        status = self.check_dependencies(required_only)
        
        for name, available in status.items():
            if not available:
                missing[name] = self._dependencies[name]
        
        return missing
    
    def validate_required_dependencies(self) -> bool:
        """
        Validate that all required dependencies are available
        
        Returns:
            True if all required dependencies are available
            
        Raises:
            ImportError: If any required dependency is missing
        """
        missing = self.get_missing_dependencies(required_only=True)
        
        if missing:
            error_lines = ["Missing required dependencies:"]
            for name, dep_info in missing.items():
                line = f"  - {name}: {dep_info.description or 'No description'}"
                if dep_info.install_command:
                    line += f" (Install: {dep_info.install_command})"
                error_lines.append(line)
            
            error_msg = "\n".join(error_lines)
            logger.error(error_msg)
            raise ImportError(error_msg)
        
        return True
    
    def get_dependency_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive dependency report
        
        Returns:
            Detailed report of all dependencies
        """
        status = self.check_dependencies()
        missing = self.get_missing_dependencies()
        
        return {
            "total_dependencies": len(self._dependencies),
            "available": sum(1 for available in status.values() if available),
            "missing": len(missing),
            "required_missing": len(self.get_missing_dependencies(required_only=True)),
            "status": status,
            "missing_details": {
                name: {
                    "description": dep_info.description,
                    "install_command": dep_info.install_command,
                    "required": dep_info.required
                }
                for name, dep_info in missing.items()
            },
            "failed_imports": {
                name: str(error) for name, error in self._failed_imports.items()
            }
        }


# Global dependency manager instance
_dependency_manager = None


def get_dependency_manager() -> DependencyManager:
    """Get the global dependency manager instance"""
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = DependencyManager()
    return _dependency_manager


def safe_import(name: str, module_path: Optional[str] = None, 
               fallback: Optional[Any] = None, required: bool = False) -> Any:
    """
    Convenience function for safe module importing
    
    Args:
        name: Dependency name
        module_path: Module import path
        fallback: Fallback value if import fails
        required: Whether this is a required dependency
        
    Returns:
        Imported module or fallback value
    """
    return get_dependency_manager().import_module(name, module_path, fallback, required)


def safe_import_from(name: str, module_path: str, item: str,
                    fallback: Optional[Any] = None, required: bool = False) -> Any:
    """
    Convenience function for safe item importing from module
    
    Args:
        name: Dependency name
        module_path: Module import path
        item: Item to import from module
        fallback: Fallback value if import fails
        required: Whether this is a required dependency
        
    Returns:
        Imported item or fallback value
    """
    return get_dependency_manager().import_from_module(name, module_path, item, fallback, required)


def require_dependencies(*dependency_names: str):
    """
    Decorator to ensure required dependencies are available
    
    Args:
        dependency_names: Names of required dependencies
        
    Raises:
        ImportError: If any required dependency is missing
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            dm = get_dependency_manager()
            
            # Check each required dependency
            for dep_name in dependency_names:
                if dep_name in dm._dependencies:
                    dep_info = dm._dependencies[dep_name]
                    dm.import_module(dep_name, dep_info.module_path, required=True)
                else:
                    # Unknown dependency - try to import by name
                    dm.import_module(dep_name, dep_name, required=True)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def optional_feature(dependency_name: str, fallback_return: Any = None):
    """
    Decorator to mark a function as requiring an optional dependency
    
    Args:
        dependency_name: Name of the optional dependency
        fallback_return: Value to return if dependency is not available
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            dm = get_dependency_manager()
            
            # Check if dependency is available
            if dependency_name in dm._dependencies:
                dep_info = dm._dependencies[dependency_name]
                module = dm.import_module(dependency_name, dep_info.module_path, required=False)
            else:
                module = dm.import_module(dependency_name, dependency_name, required=False)
            
            if module is None:
                logger.warning(f"Feature '{func.__name__}' not available: missing dependency '{dependency_name}'")
                return fallback_return
            
            return func(*args, **kwargs)
        return wrapper
    return decorator