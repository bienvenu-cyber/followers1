"""
API for accessing statistics data from the Instagram auto signup system.
"""

import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.core.statistics_manager import get_statistics_manager


# Create FastAPI app
app = FastAPI(
    title="Instagram Auto Signup Statistics API",
    description="API for accessing real-time statistics from the Instagram auto signup system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/statistics/global")
async def get_global_statistics() -> Dict[str, Any]:
    """Get global statistics."""
    stats_manager = get_statistics_manager()
    return stats_manager.get_global_statistics()


@app.get("/api/statistics/services")
async def get_service_performance(service_type: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Get service performance statistics."""
    stats_manager = get_statistics_manager()
    return stats_manager.get_service_performance(service_type)


@app.get("/api/statistics/history/performance")
async def get_performance_history() -> Dict[str, List[Dict[str, Any]]]:
    """Get historical performance data."""
    stats_manager = get_statistics_manager()
    return stats_manager.get_performance_history()


@app.get("/api/statistics/history/cycles")
async def get_cycle_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Get history of recent cycles."""
    stats_manager = get_statistics_manager()
    return stats_manager.get_cycle_history(limit=limit)


@app.get("/api/statistics/current_cycle")
async def get_current_cycle() -> Dict[str, Any]:
    """Get current cycle statistics."""
    stats_manager = get_statistics_manager()
    stats = stats_manager.get_global_statistics()
    
    if 'current_cycle' not in stats:
        raise HTTPException(status_code=404, detail="No active cycle")
    
    return stats['current_cycle']


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()