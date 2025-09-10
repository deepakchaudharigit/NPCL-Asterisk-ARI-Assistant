"""
Dashboard Management for Observability
Provides web-based dashboards for monitoring and visualization
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

try:
    from aiohttp import web, web_runner
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    id: str
    title: str
    type: str  # chart, metric, table, log
    data_source: str
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height

@dataclass
class Dashboard:
    """Dashboard configuration"""
    id: str
    title: str
    description: str
    widgets: List[DashboardWidget]
    refresh_interval: int = 30  # seconds
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class DashboardManager:
    """Manages dashboards and provides web interface"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.dashboards: Dict[str, Dashboard] = {}
        self.data_sources: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.app = None
        self.runner = None
        
        # Create default dashboards
        self._create_default_dashboards()
    
    def register_data_source(self, name: str, source_func: Callable[[], Dict[str, Any]]):
        """Register a data source for dashboards"""
        self.data_sources[name] = source_func
        logger.info(f"Registered data source: {name}")
    
    def add_dashboard(self, dashboard: Dashboard):
        """Add a dashboard"""
        self.dashboards[dashboard.id] = dashboard
        logger.info(f"Added dashboard: {dashboard.title}")
    
    def remove_dashboard(self, dashboard_id: str):
        """Remove a dashboard"""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            logger.info(f"Removed dashboard: {dashboard_id}")
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID"""
        return self.dashboards.get(dashboard_id)
    
    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards"""
        return [
            {
                'id': dashboard.id,
                'title': dashboard.title,
                'description': dashboard.description,
                'widget_count': len(dashboard.widgets),
                'created_at': dashboard.created_at
            }
            for dashboard in self.dashboards.values()
        ]
    
    async def start_server(self):
        """Start dashboard web server"""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp not available, dashboard server cannot start")
            return
        
        try:
            self.app = web.Application()
            
            # API routes
            self.app.router.add_get('/api/dashboards', self._list_dashboards_handler)
            self.app.router.add_get('/api/dashboards/{dashboard_id}', self._get_dashboard_handler)
            self.app.router.add_get('/api/data/{source_name}', self._get_data_handler)
            self.app.router.add_get('/api/health', self._health_handler)
            
            # Static routes for dashboard UI
            self.app.router.add_get('/', self._index_handler)
            self.app.router.add_get('/dashboard/{dashboard_id}', self._dashboard_handler)
            
            # WebSocket for real-time updates
            self.app.router.add_get('/ws', self._websocket_handler)
            
            self.runner = web_runner.AppRunner(self.app)
            await self.runner.setup()
            
            site = web_runner.TCPSite(self.runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info(f"Dashboard server started on port {self.port}")
            logger.info(f"Access dashboards at: http://localhost:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start dashboard server: {e}")
    
    async def stop_server(self):
        """Stop dashboard web server"""
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
            logger.info("Dashboard server stopped")
    
    async def _list_dashboards_handler(self, request):
        """Handle dashboard list API"""
        return web.json_response(self.list_dashboards())
    
    async def _get_dashboard_handler(self, request):
        """Handle get dashboard API"""
        dashboard_id = request.match_info['dashboard_id']
        dashboard = self.get_dashboard(dashboard_id)
        
        if not dashboard:
            return web.json_response({'error': 'Dashboard not found'}, status=404)
        
        return web.json_response(asdict(dashboard))
    
    async def _get_data_handler(self, request):
        """Handle data source API"""
        source_name = request.match_info['source_name']
        
        if source_name not in self.data_sources:
            return web.json_response({'error': 'Data source not found'}, status=404)
        
        try:
            data_func = self.data_sources[source_name]
            if asyncio.iscoroutinefunction(data_func):
                data = await data_func()
            else:
                data = data_func()
            
            return web.json_response(data)
            
        except Exception as e:
            logger.error(f"Error getting data from {source_name}: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _health_handler(self, request):
        """Handle health check"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': time.time(),
            'dashboards_count': len(self.dashboards),
            'data_sources_count': len(self.data_sources)
        })
    
    async def _index_handler(self, request):
        """Handle index page"""
        html = self._generate_index_html()
        return web.Response(text=html, content_type='text/html')
    
    async def _dashboard_handler(self, request):
        """Handle dashboard page"""
        dashboard_id = request.match_info['dashboard_id']
        dashboard = self.get_dashboard(dashboard_id)
        
        if not dashboard:
            return web.Response(text="Dashboard not found", status=404)
        
        html = self._generate_dashboard_html(dashboard)
        return web.Response(text=html, content_type='text/html')
    
    async def _websocket_handler(self, request):
        """Handle WebSocket connections for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            # Send initial data
            await ws.send_str(json.dumps({
                'type': 'connected',
                'timestamp': time.time()
            }))
            
            # Keep connection alive and send updates
            while not ws.closed:
                # Send periodic updates
                for source_name, source_func in self.data_sources.items():
                    try:
                        if asyncio.iscoroutinefunction(source_func):
                            data = await source_func()
                        else:
                            data = source_func()
                        
                        await ws.send_str(json.dumps({
                            'type': 'data_update',
                            'source': source_name,
                            'data': data,
                            'timestamp': time.time()
                        }))
                        
                    except Exception as e:
                        logger.error(f"Error sending WebSocket update: {e}")
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        
        return ws
    
    def _generate_index_html(self) -> str:
        """Generate index HTML page"""
        dashboards_html = ""
        for dashboard in self.dashboards.values():
            dashboards_html += f"""
            <div class="dashboard-card">
                <h3><a href="/dashboard/{dashboard.id}">{dashboard.title}</a></h3>
                <p>{dashboard.description}</p>
                <small>{len(dashboard.widgets)} widgets</small>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>NPCL Voice Assistant - Dashboards</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .dashboard-card {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px; 
                }}
                .dashboard-card h3 {{ margin-top: 0; }}
                .dashboard-card a {{ text-decoration: none; color: #007bff; }}
                .dashboard-card a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>🤖 NPCL Voice Assistant - Monitoring Dashboards</h1>
            <p>Select a dashboard to view real-time monitoring data:</p>
            {dashboards_html}
            
            <h2>API Endpoints</h2>
            <ul>
                <li><a href="/api/dashboards">List Dashboards</a></li>
                <li><a href="/api/health">Health Check</a></li>
            </ul>
        </body>
        </html>
        """
    
    def _generate_dashboard_html(self, dashboard: Dashboard) -> str:
        """Generate dashboard HTML page"""
        widgets_html = ""
        
        for widget in dashboard.widgets:
            widget_html = f"""
            <div class="widget" id="widget-{widget.id}" 
                 style="grid-column: {widget.position['x']} / span {widget.position['width']};
                        grid-row: {widget.position['y']} / span {widget.position['height']};">
                <div class="widget-header">
                    <h3>{widget.title}</h3>
                    <span class="widget-type">{widget.type}</span>
                </div>
                <div class="widget-content" id="content-{widget.id}">
                    Loading...
                </div>
            </div>
            """
            widgets_html += widget_html
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{dashboard.title} - NPCL Voice Assistant</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f5f5f5; 
                }}
                .dashboard-header {{ 
                    background: white; 
                    padding: 20px; 
                    border-radius: 5px; 
                    margin-bottom: 20px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                }}
                .dashboard-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(12, 1fr); 
                    grid-template-rows: repeat(8, 150px); 
                    gap: 20px; 
                }}
                .widget {{ 
                    background: white; 
                    border-radius: 5px; 
                    padding: 15px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                }}
                .widget-header {{ 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    border-bottom: 1px solid #eee; 
                    padding-bottom: 10px; 
                    margin-bottom: 15px; 
                }}
                .widget-header h3 {{ margin: 0; }}
                .widget-type {{ 
                    background: #007bff; 
                    color: white; 
                    padding: 2px 8px; 
                    border-radius: 3px; 
                    font-size: 12px; 
                }}
                .widget-content {{ 
                    height: calc(100% - 60px); 
                    overflow: auto; 
                }}
                .metric-value {{ 
                    font-size: 2em; 
                    font-weight: bold; 
                    color: #007bff; 
                }}
                .metric-unit {{ 
                    font-size: 0.8em; 
                    color: #666; 
                }}
                .status-healthy {{ color: #28a745; }}
                .status-warning {{ color: #ffc107; }}
                .status-error {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>{dashboard.title}</h1>
                <p>{dashboard.description}</p>
                <small>Last updated: <span id="last-updated">Loading...</span></small>
            </div>
            
            <div class="dashboard-grid">
                {widgets_html}
            </div>
            
            <script>
                // WebSocket connection for real-time updates
                const ws = new WebSocket('ws://localhost:{self.port}/ws');
                
                ws.onmessage = function(event) {{
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'data_update') {{
                        updateWidgets(message.source, message.data);
                        document.getElementById('last-updated').textContent = 
                            new Date(message.timestamp * 1000).toLocaleString();
                    }}
                }};
                
                function updateWidgets(source, data) {{
                    // Update widgets based on data source
                    const widgets = {json.dumps([asdict(w) for w in dashboard.widgets])};
                    
                    widgets.forEach(widget => {{
                        if (widget.data_source === source) {{
                            updateWidget(widget, data);
                        }}
                    }});
                }}
                
                function updateWidget(widget, data) {{
                    const contentEl = document.getElementById('content-' + widget.id);
                    
                    if (widget.type === 'metric') {{
                        const value = getNestedValue(data, widget.config.metric_path);
                        const unit = widget.config.unit || '';
                        contentEl.innerHTML = `
                            <div class="metric-value">${{value}}</div>
                            <div class="metric-unit">${{unit}}</div>
                        `;
                    }} else if (widget.type === 'status') {{
                        const status = getNestedValue(data, widget.config.status_path);
                        const statusClass = 'status-' + status;
                        contentEl.innerHTML = `
                            <div class="${{statusClass}}">${{status.toUpperCase()}}</div>
                        `;
                    }} else if (widget.type === 'table') {{
                        const tableData = getNestedValue(data, widget.config.data_path);
                        contentEl.innerHTML = generateTable(tableData);
                    }}
                }}
                
                function getNestedValue(obj, path) {{
                    return path.split('.').reduce((o, p) => o && o[p], obj);
                }}
                
                function generateTable(data) {{
                    if (!Array.isArray(data)) return 'No data';
                    
                    if (data.length === 0) return 'No data';
                    
                    const headers = Object.keys(data[0]);
                    let html = '<table style="width: 100%; border-collapse: collapse;">';
                    
                    // Headers
                    html += '<tr>';
                    headers.forEach(header => {{
                        html += `<th style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa;">${{header}}</th>`;
                    }});
                    html += '</tr>';
                    
                    // Rows
                    data.forEach(row => {{
                        html += '<tr>';
                        headers.forEach(header => {{
                            html += `<td style="border: 1px solid #ddd; padding: 8px;">${{row[header] || ''}}</td>`;
                        }});
                        html += '</tr>';
                    }});
                    
                    html += '</table>';
                    return html;
                }}
                
                // Initial load
                setTimeout(() => {{
                    fetch('/api/data/system_metrics')
                        .then(response => response.json())
                        .then(data => updateWidgets('system_metrics', data));
                }}, 1000);
            </script>
        </body>
        </html>
        """
    
    def _create_default_dashboards(self):
        """Create default dashboards"""
        
        # System Overview Dashboard
        system_dashboard = Dashboard(
            id="system_overview",
            title="System Overview",
            description="Overall system health and performance metrics",
            widgets=[
                DashboardWidget(
                    id="cpu_usage",
                    title="CPU Usage",
                    type="metric",
                    data_source="system_metrics",
                    config={"metric_path": "cpu_percent", "unit": "%"},
                    position={"x": 1, "y": 1, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="memory_usage",
                    title="Memory Usage",
                    type="metric",
                    data_source="system_metrics",
                    config={"metric_path": "memory_percent", "unit": "%"},
                    position={"x": 4, "y": 1, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="disk_usage",
                    title="Disk Usage",
                    type="metric",
                    data_source="system_metrics",
                    config={"metric_path": "disk_percent", "unit": "%"},
                    position={"x": 7, "y": 1, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="system_status",
                    title="System Status",
                    type="status",
                    data_source="health_status",
                    config={"status_path": "status"},
                    position={"x": 10, "y": 1, "width": 3, "height": 2}
                )
            ]
        )
        
        # Voice Assistant Dashboard
        voice_dashboard = Dashboard(
            id="voice_assistant",
            title="Voice Assistant Metrics",
            description="Voice assistant specific metrics and performance",
            widgets=[
                DashboardWidget(
                    id="active_sessions",
                    title="Active Sessions",
                    type="metric",
                    data_source="voice_metrics",
                    config={"metric_path": "active_sessions", "unit": "sessions"},
                    position={"x": 1, "y": 1, "width": 4, "height": 2}
                ),
                DashboardWidget(
                    id="response_time",
                    title="Avg Response Time",
                    type="metric",
                    data_source="voice_metrics",
                    config={"metric_path": "avg_response_time", "unit": "ms"},
                    position={"x": 5, "y": 1, "width": 4, "height": 2}
                ),
                DashboardWidget(
                    id="error_rate",
                    title="Error Rate",
                    type="metric",
                    data_source="voice_metrics",
                    config={"metric_path": "error_rate", "unit": "%"},
                    position={"x": 9, "y": 1, "width": 4, "height": 2}
                )
            ]
        )
        
        self.add_dashboard(system_dashboard)
        self.add_dashboard(voice_dashboard)