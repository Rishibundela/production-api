FROM python:3.12-slim

WORKDIR /app

# Creatte a non-root user to run the application for better security
RUN useradd --create-home appauser && chown appauser:appauser /app

# install uv (fast python package manager)
RUN pip install uv

# Copy dependency files first (Docker will cache this layer if dependencies don't change)
COPY --chown=appauser:appauser pyproject.toml . 
COPY --chown=appauser:appauser uv.lock* .

# Switch to non-root user before installing dependencies (so .venv is owned by appauser)
USER appauser

# Install dependencies (production only)
RUN uv sync --frozen --no-dev

# Copy applcation code
COPY --chown=appauser:appauser app/ app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]