"""
API Request and Response Models
Pydantic models for input validation and response structuring
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from datetime import timezone

class ChatRequest(BaseModel):
    """ Request model for chat interactions """
    message: str = Field(..., min_length=1, max_length=10000, description="The input message for the chat model")
    thread_id: str = Field(default="default", description="Optional thread ID for conversation context")

class ChatResponse(BaseModel):
    """ Response model for chat interactions """
    response: str = Field(..., description="The generated response from the chat model")
    thread_id: str = Field(default="default", description="The thread ID associated with the conversation")
    model_used: str = Field(..., description="The model that was used to generate the response")
    cached: bool = Field(default=False, description="Indicates if the response was served from cache")
    processing_time_ms: Optional[float] = Field(None, description="Time taken to process the request in milliseconds")
    timestamp: datetime = Field(default_factory= lambda: datetime.now(timezone.utc), description="The time when the response was generated")

class HealthResponse(BaseModel):
    """ Health status of the API """
    status: str = Field(default="healthy", description="Health status of the API")
    environment: str = Field(..., description="Current environment of the API (e.g., development, production)")
    version: str = Field(..., description="Version of the API")
    checks: dict = Field(default_factory=dict, description="Detailed health check results")

class MetricResponse(BaseModel):
    """ Metrics for monitoring API performance and usage """
    total_requests: int = Field(default=0, description="Total number of requests received")
    total_errors: int = Field(default=0, description="Total number of errors encountered")
    error_rate: float = Field(default=0.0, description="Error rate as a percentage")
    avg_latency_ms: float = Field(default=0.0, description="Average latency of requests in milliseconds")
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate as a percentage")
    total_input_tokens: int = Field(default=0, description="Total number of input tokens processed")
    total_output_tokens: int = Field(default=0, description="Total number of output tokens generated")

class ErrorResponse(BaseModel):
    """ Standardized error response model """
    error: str = Field(..., description="Error message describing what went wrong")
    details: Optional[str] = Field(None, description="Additional details about the error")
    request_id: Optional[str] = Field(None, description="Unique identifier for the request that caused the error")

    