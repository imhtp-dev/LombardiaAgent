"""
OpenTelemetry and LangFuse Integration
Provides tracing capabilities for Pipecat healthcare agent
"""
import os
import asyncio
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode
from langfuse import Langfuse
from loguru import logger


def setup_tracing(
    service_name: str = "pipecat-healthcare-agent",
    enable_console: bool = False
) -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry tracing with LangFuse OTLP exporter

    Args:
        service_name: Name of the service for trace identification
        enable_console: Whether to also export traces to console (debugging)

    Returns:
        Configured tracer instance or None if tracing disabled
    """
    if not os.getenv("ENABLE_TRACING", "false").lower() == "true":
        logger.info("🔍 Tracing disabled (ENABLE_TRACING not set)")
        return None

    try:
        # Create resource with service name and metadata
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
            "service.version": os.getenv("VERSION", "1.0.0")
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter for LangFuse
        # OTLPSpanExporter automatically reads from environment variables:
        # - OTEL_EXPORTER_OTLP_TRACES_ENDPOINT (signal-specific)
        # - OTEL_EXPORTER_OTLP_TRACES_HEADERS (signal-specific)
        # - OTEL_EXPORTER_OTLP_TRACES_PROTOCOL (signal-specific)
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")

        if not otlp_endpoint:
            logger.error("❌ OTEL_EXPORTER_OTLP_TRACES_ENDPOINT not set")
            return None

        # Let exporter auto-read from env vars (no manual config needed)
        otlp_exporter = OTLPSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Optional: Console exporter for debugging
        if enable_console or os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true":
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("🔍 Console trace export enabled")

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        logger.success(f"✅ OpenTelemetry tracing initialized: {service_name}")
        logger.info(f"📊 Exporting to: {otlp_endpoint}")

        return trace.get_tracer(__name__)

    except Exception as e:
        logger.error(f"❌ Failed to initialize tracing: {e}")
        return None


def get_tracer() -> trace.Tracer:
    """Get the current tracer instance"""
    return trace.get_tracer(__name__)


def flush_traces():
    """
    Force flush all pending traces to Langfuse

    IMPORTANT: Call this before your application exits to ensure
    all traces are sent to Langfuse. BatchSpanProcessor queues spans
    and sends them asynchronously, so without flushing, traces may be lost.

    Usage:
        # At the end of your script or in cleanup
        from config.telemetry import flush_traces
        flush_traces()
    """
    try:
        provider = trace.get_tracer_provider()
        if hasattr(provider, 'force_flush'):
            logger.info("🔄 Flushing traces to Langfuse...")
            provider.force_flush()
            logger.success("✅ All traces flushed to Langfuse")
    except Exception as e:
        logger.error(f"❌ Failed to flush traces: {e}")


def get_current_trace_id() -> Optional[str]:
    """
    Get the current OpenTelemetry trace ID in hex format (for LangFuse queries)
    
    Returns:
        Trace ID as hex string (e.g., 'c04dca2bf957960bf2b4e9a7f8c8bb98') or None if no active trace
    """
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        # Convert trace ID (int) to 32-character hex string
        trace_id = format(current_span.get_span_context().trace_id, '032x')
        return trace_id
    return None


def get_langfuse_client() -> Langfuse:
    """Get initialized LangFuse client for API queries"""
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    )


async def get_conversation_tokens(trace_id: Optional[str] = None) -> dict:
    """
    Query LangFuse API to get total token usage for a conversation
    
    Args:
        trace_id: Optional OpenTelemetry trace ID (hex format).
                 If not provided, will try to get from current trace context.
    
    Returns:
        dict with keys: prompt_tokens, completion_tokens, total_tokens
    """
    try:
        # If trace_id not provided, try to get from current context
        if not trace_id:
            current_span = trace.get_current_span()
            if current_span and current_span.get_span_context().is_valid:
                # Convert trace ID to hex format (LangFuse expects this)
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                logger.info(f"🔍 Retrieved trace ID from context: {trace_id}")
            else:
                logger.warning("⚠️ No valid trace context found")
                return {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
        
        # Run synchronous LangFuse API call in thread pool
        loop = asyncio.get_event_loop()
        token_data = await loop.run_in_executor(
            None,
            _get_tokens_sync,
            trace_id
        )

        logger.success(f"✅ Retrieved tokens from LangFuse: {token_data['total_tokens']}")
        return token_data

    except Exception as e:
        logger.error(f"❌ Failed to get tokens from LangFuse: {e}")
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }


def _get_tokens_sync(trace_id: str) -> dict:
    """
    Synchronous helper to query LangFuse API
    (LangFuse SDK is synchronous, so we run in thread pool)

    Args:
        trace_id: OpenTelemetry trace ID in hex format (e.g., 'c04dca2bf957960bf2b4e9a7f8c8bb98')
    """
    try:
        client = get_langfuse_client()

        # Get trace by OpenTelemetry trace ID using SDK v3 API
        logger.info(f"🔍 Querying LangFuse with trace ID: {trace_id}")
        trace_data = client.api.trace.get(trace_id)

        # DEBUG: Print trace structure to understand what we have
        logger.info(f"📊 Trace data type: {type(trace_data)}")
        logger.info(f"📊 Trace attributes: {dir(trace_data)}")

        # Check if observations exist
        if hasattr(trace_data, 'observations'):
            logger.info(f"📊 Number of observations: {len(trace_data.observations)}")

            # Debug first observation structure
            if len(trace_data.observations) > 0:
                first_obs = trace_data.observations[0]
                logger.info(f"📊 First observation type: {first_obs.type}")
                logger.info(f"📊 First observation attributes: {dir(first_obs)}")

                # Check for direct token attributes
                if hasattr(first_obs, 'promptTokens'):
                    logger.info(f"📊 First observation promptTokens (direct): {first_obs.promptTokens}")
                if hasattr(first_obs, 'completionTokens'):
                    logger.info(f"📊 First observation completionTokens (direct): {first_obs.completionTokens}")
                if hasattr(first_obs, 'totalTokens'):
                    logger.info(f"📊 First observation totalTokens (direct): {first_obs.totalTokens}")

                # Check nested usage object
                if hasattr(first_obs, 'usage'):
                    logger.info(f"📊 First observation usage (nested): {first_obs.usage}")

        # Calculate total tokens across all LLM spans
        prompt_tokens = 0
        completion_tokens = 0

        # Navigate through observations to find LLM generations
        if hasattr(trace_data, 'observations'):
            for i, observation in enumerate(trace_data.observations):
                logger.debug(f"📊 Observation {i}: type={observation.type}")

                # CRITICAL: LangFuse uses uppercase "GENERATION" not lowercase "generation"
                if observation.type == "GENERATION":  # LLM calls
                    input_tokens = 0
                    output_tokens = 0

                    # Strategy 1: Try to get tokens from direct observation attributes first
                    # (LangFuse stores OTLP data as attributes on the observation object)
                    if hasattr(observation, 'promptTokens') and observation.promptTokens:
                        input_tokens = observation.promptTokens
                        logger.info(f"📊 Found promptTokens as direct attribute: {input_tokens}")

                    if hasattr(observation, 'completionTokens') and observation.completionTokens:
                        output_tokens = observation.completionTokens
                        logger.info(f"📊 Found completionTokens as direct attribute: {output_tokens}")

                    # Strategy 2: Fallback to nested usage object if attributes not found
                    if input_tokens == 0 or output_tokens == 0:
                        usage = observation.usage
                        if usage:
                            logger.info(f"📊 Checking nested usage object: {usage}")
                            # Try different field names in usage dict
                            if input_tokens == 0:
                                input_tokens = usage.get("input", 0) or usage.get("promptTokens", 0) or usage.get("input_tokens", 0)
                            if output_tokens == 0:
                                output_tokens = usage.get("output", 0) or usage.get("completionTokens", 0) or usage.get("output_tokens", 0)

                    if input_tokens > 0 or output_tokens > 0:
                        prompt_tokens += input_tokens
                        completion_tokens += output_tokens
                        logger.success(f"✅ Added tokens from observation {i}: input={input_tokens}, output={output_tokens}")
                    else:
                        logger.warning(f"⚠️ Observation {i} has no token data")

        total_tokens = prompt_tokens + completion_tokens
        logger.info(f"📊 Total tokens calculated: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

    except Exception as e:
        logger.error(f"❌ LangFuse API query error: {e}")
        import traceback
        logger.error(f"❌ Full error: {traceback.format_exc()}")
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
