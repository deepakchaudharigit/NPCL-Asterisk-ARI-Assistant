"""
Distributed Tracing Implementation
Provides request tracing across microservices and components
"""

import time
import uuid
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from contextlib import asynccontextmanager
from enum import Enum
import logging
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

class SpanKind(Enum):
    """Types of spans"""
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"

class SpanStatus(Enum):
    """Span status"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class SpanContext:
    """Span context for distributed tracing"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'baggage': self.baggage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpanContext':
        """Create from dictionary"""
        return cls(
            trace_id=data['trace_id'],
            span_id=data['span_id'],
            parent_span_id=data.get('parent_span_id'),
            baggage=data.get('baggage', {})
        )

@dataclass
class Span:
    """Represents a single span in a trace"""
    context: SpanContext
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    kind: SpanKind = SpanKind.INTERNAL
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, status: SpanStatus = SpanStatus.OK):
        """Finish the span"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status
    
    def set_tag(self, key: str, value: Any):
        """Set a tag on the span"""
        self.tags[key] = value
    
    def log(self, message: str, level: str = "info", **kwargs):
        """Add a log entry to the span"""
        log_entry = {
            'timestamp': time.time(),
            'level': level,
            'message': message,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            'trace_id': self.context.trace_id,
            'span_id': self.context.span_id,
            'parent_span_id': self.context.parent_span_id,
            'operation_name': self.operation_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'status': self.status.value,
            'kind': self.kind.value,
            'tags': self.tags,
            'logs': self.logs
        }

class TraceContext:
    """Thread-local trace context"""
    
    def __init__(self):
        self._local = threading.local()
    
    def get_current_span(self) -> Optional[Span]:
        """Get current active span"""
        return getattr(self._local, 'current_span', None)
    
    def set_current_span(self, span: Optional[Span]):
        """Set current active span"""
        self._local.current_span = span
    
    def get_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        span = self.get_current_span()
        return span.context.trace_id if span else None

class DistributedTracer:
    """Distributed tracer implementation"""
    
    def __init__(self, service_name: str, 
                 export_interval: int = 10,
                 max_spans_per_trace: int = 1000):
        self.service_name = service_name
        self.export_interval = export_interval
        self.max_spans_per_trace = max_spans_per_trace
        
        # Span storage
        self.active_spans: Dict[str, Span] = {}
        self.completed_spans: List[Span] = []
        self.traces: Dict[str, List[Span]] = defaultdict(list)
        
        # Context management
        self.context = TraceContext()
        
        # Export configuration
        self.exporters: List[Callable[[List[Span]], None]] = []
        self.export_task = None
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'spans_created': 0,
            'spans_finished': 0,
            'traces_completed': 0,
            'export_errors': 0
        }
    
    def start_span(self, operation_name: str, 
                   parent_context: Optional[SpanContext] = None,
                   kind: SpanKind = SpanKind.INTERNAL,
                   tags: Dict[str, Any] = None) -> Span:
        """Start a new span"""
        
        # Generate IDs
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            # Check if there's a current span
            current_span = self.context.get_current_span()
            if current_span:
                trace_id = current_span.context.trace_id
                parent_span_id = current_span.context.span_id
            else:
                trace_id = self._generate_trace_id()
                parent_span_id = None
        
        span_id = self._generate_span_id()
        
        # Create span context
        span_context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        # Create span
        span = Span(
            context=span_context,
            operation_name=operation_name,
            start_time=time.time(),
            kind=kind,
            tags=tags or {}
        )
        
        # Add service tags
        span.set_tag('service.name', self.service_name)
        span.set_tag('span.kind', kind.value)
        
        # Store span
        with self._lock:
            self.active_spans[span_id] = span
            self.stats['spans_created'] += 1
        
        return span
    
    def finish_span(self, span: Span, status: SpanStatus = SpanStatus.OK):
        """Finish a span"""
        span.finish(status)
        
        with self._lock:
            # Remove from active spans
            self.active_spans.pop(span.context.span_id, None)
            
            # Add to completed spans
            self.completed_spans.append(span)
            self.traces[span.context.trace_id].append(span)
            
            # Update statistics
            self.stats['spans_finished'] += 1
            
            # Check if trace is complete
            if self._is_trace_complete(span.context.trace_id):
                self.stats['traces_completed'] += 1
    
    @asynccontextmanager
    async def trace(self, operation_name: str, 
                   parent_context: Optional[SpanContext] = None,
                   kind: SpanKind = SpanKind.INTERNAL,
                   tags: Dict[str, Any] = None):
        """Context manager for tracing operations"""
        span = self.start_span(operation_name, parent_context, kind, tags)
        
        # Set as current span
        previous_span = self.context.get_current_span()
        self.context.set_current_span(span)
        
        try:
            yield span
            self.finish_span(span, SpanStatus.OK)
        except Exception as e:
            span.set_tag('error', True)
            span.set_tag('error.message', str(e))
            span.log(f"Exception occurred: {e}", level="error")
            self.finish_span(span, SpanStatus.ERROR)
            raise
        finally:
            # Restore previous span
            self.context.set_current_span(previous_span)
    
    def inject_context(self, span_context: SpanContext) -> Dict[str, str]:
        """Inject span context into headers for propagation"""
        return {
            'X-Trace-Id': span_context.trace_id,
            'X-Span-Id': span_context.span_id,
            'X-Parent-Span-Id': span_context.parent_span_id or '',
            'X-Baggage': json.dumps(span_context.baggage) if span_context.baggage else ''
        }
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """Extract span context from headers"""
        trace_id = headers.get('X-Trace-Id')
        span_id = headers.get('X-Span-Id')
        
        if not trace_id or not span_id:
            return None
        
        parent_span_id = headers.get('X-Parent-Span-Id') or None
        baggage_str = headers.get('X-Baggage', '')
        
        baggage = {}
        if baggage_str:
            try:
                baggage = json.loads(baggage_str)
            except json.JSONDecodeError:
                pass
        
        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            baggage=baggage
        )
    
    def add_exporter(self, exporter: Callable[[List[Span]], None]):
        """Add a span exporter"""
        self.exporters.append(exporter)
    
    async def start_export_task(self):
        """Start background export task"""
        if self.export_task is None:
            self.export_task = asyncio.create_task(self._export_loop())
    
    async def stop_export_task(self):
        """Stop background export task"""
        if self.export_task:
            self.export_task.cancel()
            try:
                await self.export_task
            except asyncio.CancelledError:
                pass
            self.export_task = None
    
    async def _export_loop(self):
        """Background loop for exporting spans"""
        while True:
            try:
                await asyncio.sleep(self.export_interval)
                await self._export_spans()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Export error: {e}")
                self.stats['export_errors'] += 1
    
    async def _export_spans(self):
        """Export completed spans"""
        with self._lock:
            if not self.completed_spans:
                return
            
            spans_to_export = self.completed_spans.copy()
            self.completed_spans.clear()
        
        # Export to all configured exporters
        for exporter in self.exporters:
            try:
                exporter(spans_to_export)
            except Exception as e:
                logger.error(f"Exporter error: {e}")
                self.stats['export_errors'] += 1
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace"""
        return self.traces.get(trace_id, [])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tracer statistics"""
        with self._lock:
            return {
                **self.stats,
                'active_spans': len(self.active_spans),
                'completed_spans': len(self.completed_spans),
                'active_traces': len(self.traces),
                'exporters_count': len(self.exporters)
            }
    
    def _generate_trace_id(self) -> str:
        """Generate a new trace ID"""
        return uuid.uuid4().hex
    
    def _generate_span_id(self) -> str:
        """Generate a new span ID"""
        return uuid.uuid4().hex[:16]
    
    def _is_trace_complete(self, trace_id: str) -> bool:
        """Check if a trace is complete (no active spans)"""
        for span in self.active_spans.values():
            if span.context.trace_id == trace_id:
                return False
        return True

class JaegerExporter:
    """Jaeger exporter for spans"""
    
    def __init__(self, jaeger_endpoint: str = "http://localhost:14268/api/traces"):
        self.jaeger_endpoint = jaeger_endpoint
    
    def __call__(self, spans: List[Span]):
        """Export spans to Jaeger"""
        try:
            # Convert spans to Jaeger format
            jaeger_data = self._convert_to_jaeger_format(spans)
            
            # Send to Jaeger (would use HTTP client in production)
            logger.info(f"Exporting {len(spans)} spans to Jaeger")
            # In production: requests.post(self.jaeger_endpoint, json=jaeger_data)
            
        except Exception as e:
            logger.error(f"Jaeger export error: {e}")
    
    def _convert_to_jaeger_format(self, spans: List[Span]) -> Dict[str, Any]:
        """Convert spans to Jaeger format"""
        # Group spans by trace
        traces = defaultdict(list)
        for span in spans:
            traces[span.context.trace_id].append(span)
        
        jaeger_traces = []
        for trace_id, trace_spans in traces.items():
            jaeger_spans = []
            for span in trace_spans:
                jaeger_span = {
                    'traceID': span.context.trace_id,
                    'spanID': span.context.span_id,
                    'parentSpanID': span.context.parent_span_id,
                    'operationName': span.operation_name,
                    'startTime': int(span.start_time * 1000000),  # microseconds
                    'duration': int((span.duration or 0) * 1000000),
                    'tags': [{'key': k, 'value': v} for k, v in span.tags.items()],
                    'logs': span.logs
                }
                jaeger_spans.append(jaeger_span)
            
            jaeger_trace = {
                'traceID': trace_id,
                'spans': jaeger_spans
            }
            jaeger_traces.append(jaeger_trace)
        
        return {'data': jaeger_traces}

class ConsoleExporter:
    """Console exporter for development"""
    
    def __call__(self, spans: List[Span]):
        """Export spans to console"""
        for span in spans:
            logger.info(f"TRACE: {span.operation_name} "
                       f"[{span.context.trace_id[:8]}:{span.context.span_id[:8]}] "
                       f"duration={span.duration:.3f}s status={span.status.value}")

# Decorators for automatic tracing
def trace_function(operation_name: str = None, 
                  kind: SpanKind = SpanKind.INTERNAL,
                  tags: Dict[str, Any] = None):
    """Decorator for tracing functions"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            tracer = getattr(func, '_tracer', None)
            if not tracer:
                return await func(*args, **kwargs)
            
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            async with tracer.trace(op_name, kind=kind, tags=tags) as span:
                span.set_tag('function.name', func.__name__)
                span.set_tag('function.module', func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_tag('function.result_type', type(result).__name__)
                    return result
                except Exception as e:
                    span.set_tag('function.exception', str(e))
                    raise
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we can't use async context manager
            # This is a simplified version
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None

def get_tracer() -> Optional[DistributedTracer]:
    """Get global tracer instance"""
    return _global_tracer

def set_tracer(tracer: DistributedTracer):
    """Set global tracer instance"""
    global _global_tracer
    _global_tracer = tracer