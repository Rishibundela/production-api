"""
Production-Ready FastAPI + LangGraph Application

Wires together:
- FastAPI for API endpoints
- SlowAPI for rate limiting
- LangGraph for agent orchestration with retry and fallback
- LangSmith for tracing and monitoring
- Security pipeline for input validation
- Response caching for performance optimization
- Structured logging and metrics collection for observability
- Health checks and error handling for robustness
"""
import time
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langsmith import traceable
from dotenv import load_dotenv

from app.config import get_settings
from app.models import (
    ChatRequest, ChatResponse,
    HealthResponse, MetricResponse, ErrorResponse
)
from app.security import SecurityPipeline
from app.cache import ResponseCache
from app.monitoring import get_logger, MetricsCollector, RequestTimer
from app.agent import ProductionAgent

load_dotenv()



# === Global Components ===

security: SecurityPipeline | None = None
cache: ResponseCache | None = None
metrics: MetricsCollector | None = None
agent: ProductionAgent | None = None

logger = get_logger()

# === Lifespan (startup/shutdown) ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """

    """
    global security, cache, metrics, agent

    settings = get_settings()

    logger.info("Starting production API...", extra={"extra_data": {
        "environment": settings.APP_ENV, 
        "version": settings.APP_VERSION,
        "primary_model": settings.PRIMARY_MODEL,
        "tracing_enabled": settings.LANGCHAIN_TRACING_V2,
        "rate_limits": settings.RATE_LIMIT,
        }})

    # Initialize components
    security = SecurityPipeline()
    cache = ResponseCache(ttl_seconds=settings.CACHE_TTL_SECONDS)
    metrics = MetricsCollector()
    agent = ProductionAgent()

    logger.info("Application startup complete. Components initialized.")

    yield #  Application is running here
    # Shutdown
    logger.info("Application shutting down...", extra={"extra_data": metrics.get_summary()}) 


# === Rate Limiter setup ===
limiter = Limiter(key_func=get_remote_address, default_limits=[get_settings().RATE_LIMIT])

# === FastAPI Application ===
app = FastAPI(
    title=get_settings().APP_NAME,
    version=get_settings().APP_VERSION,
    description="A production-ready FastAPI application with LangGraph orchestration, security pipeline, caching, and observability.",
    lifespan=lifespan,
)

app.state.limiter = limiter

# === Exception Handlers ===

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("Rate limit exceeded", extra={"extra_data": {"client": get_remote_address(request)}})
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

# ====================================
# ENDPOINTS AND BUSINESS LOGIC BELOW
# ====================================

@app.post("/chat", response_model=ChatResponse, responses={400: {"model": ErrorResponse}})
@limiter.limit(get_settings().RATE_LIMIT)
@traceable(name="chat_endpoint")
async def chat_endpoint(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint

    Flow:
    1. Security check (injection detection, PII masking)
    2. Cache lookup
    3. LangGraph agent invoke (if cache miss)
    4. Output validation
    5. Cache store
    6. Metrics recording
    7. Return response
    """

    with RequestTimer() as timer:
        security_notes = []

        # ---- Step 1: Security Check ----
        input_result = security.check_input(body.message)

        is_allowed = input_result["safe"]
        sanitized_input = input_result["processed_input"]
        notes = input_result["security_notes"]
        security_notes.extend(notes)

        if not is_allowed:
            logger.warning("Request blocked by security", extra={"extra_data": {
                "input": body.message,
                "reasons": security_notes,
                "thread_id": body.thread_id,  
            }})
            metrics.record_request(latency=0.0, error=True)
            raise HTTPException(
                status_code=400, 
                detail="Your message was blocked by our security filters. Please modify your input and try again."
            )
        
        # ---- Step 2: Cache Lookup ----
        cached_response = cache.get(sanitized_input)
        if cached_response:
            logger.info("Cache hit", extra={"extra_data": {
                "input": sanitized_input,
                "thread_id": body.thread_id,  
            }})
            metrics.record_request(latency=0.0, cache_hit=True)
            return ChatResponse(
                response=cached_response,
                thread_id=body.thread_id,
                model_used="cache",
                cached=True,
                processing_time_ms=0.0,
            )

        # ---- Step 3: LangGraph Agent Invoke ----
        try:
            agent_response = agent.invoke(sanitized_input)
        except Exception as e:
            logger.error("Agent invocation failed", extra={"extra_data": {
                "input": sanitized_input,
                "error": str(e),
                "thread_id": body.thread_id,  
            }})
            metrics.record_request(latency=timer.elapsed_ms / 1000.0, error=True)
            raise HTTPException(
                status_code=500, 
                detail="An error occurred while processing your request. Please try again later."
            )
        
        response_text = agent_response.get("response", "Sorry, I couldn't generate a response.")
        model_used = agent_response.get("model_used", "unknown")

        # ---- Step 4: Output Validation ----
        output_results= security.check_output(response_text)
        validated_response = output_results["output"]
        security_notes.extend(output_results["security_notes"])

        # ---- Step 5: Cache Store ----
        cache.set(sanitized_input, validated_response)

    # ---- Step 6: Metrics Recording ----
    input_tokens = int(len(sanitized_input.split())* 1.3)  # Rough estimate of input tokens
    output_tokens = int(len(validated_response.split())* 1.3)  # Rough estimate of output tokens
    
    metrics.record_request(
        latency=timer.elapsed_ms / 1000.0, 
        tokens_input=input_tokens, 
        tokens_output=output_tokens, 
        cache_hit=False
    )

    if security_notes:
        logger.info("Security notes for request", extra={"extra_data": {
            "thread_id": body.thread_id,
            "notes": security_notes,
        }})

    # ---- Step 7: Return Response ----
    return ChatResponse(
        response=validated_response,
        thread_id=body.thread_id,
        model_used=model_used,
        cached=False,
        processing_time_ms=round(timer.elapsed_ms, 2),
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to report API status."""
    settings = get_settings()

    checks = {
        "agent": "ok" if agent else "not initialized",
        "cache": "ok" if cache else "not initialized",
        "security": "ok" if security else "not initialized",
    }

    all_healhy = all(status == "ok" for status in checks.values())
    
    return HealthResponse(
        status="healthy" if all_healhy else "degraded",
        environment=settings.APP_ENV,
        version=settings.APP_VERSION,
        checks=checks,
    )

@app.get("/metrics", response_model=MetricResponse)
async def get_metrics():
    """Endpoint to retrieve current metrics summary."""
    summary = metrics.get_summary()
    return MetricResponse(**summary)

@app.get("/cache/stats")
async def cache_stats():
    """Endpoint to retrieve cache statistics."""
    stats = cache.stats
    return JSONResponse(content=stats)

@app.get("/test-limit")
@limiter.limit("3/minute")
async def test_limit(request: Request):
    return {"status": "ok"}
