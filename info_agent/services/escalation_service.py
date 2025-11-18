"""
Escalation Service for transferring calls to human operators
Calls the bridge escalation API which handles WebSocket closure and Talkdesk transfer
"""
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Bridge escalation endpoint
ESCALATION_API_URL = "https://bridgeapitvchc-ptnbridge-eyfbgsbsdwepfgb3.francecentral-01.azurewebsites.net/escalation"


async def call_escalation_api(
    summary: str,
    sentiment: str,
    action: str,
    duration: str,
    service: str
) -> bool:
    """
    Call bridge escalation API to transfer call to human operator

    The bridge will:
    1. Close Pipecat WebSocket automatically
    2. Send transfer message to Talkdesk with provided data

    Args:
        summary: Call summary (max 250 chars)
        sentiment: positive|neutral|negative
        action: transfer
        duration: Duration in seconds (as string)
        service: Service code 1-5 (as string)

    Returns:
        bool: True if escalation API call succeeded, False otherwise

    Note: WebSocket closes automatically regardless of return value
    """
    try:
        # Prepare payload for bridge escalation endpoint
        payload = {
            "summary": summary[:250],  # Ensure max 250 chars
            "sentiment": sentiment,
            "action": action,
            "duration": duration,
            "service": service
        }

        logger.info(f"Calling escalation API: {ESCALATION_API_URL}")
        logger.info(f"Escalation data: summary_len={len(summary)}, sentiment={sentiment}, "
                   f"action={action}, duration={duration}s, service={service}")

        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                ESCALATION_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                status = response.status
                response_text = await response.text()

                if status == 200:
                    logger.info(f"✅ Escalation API success: {response_text}")
                    return True
                else:
                    logger.error(f"❌ Escalation API failed: status={status}, response={response_text}")
                    return False

    except aiohttp.ClientError as e:
        logger.error(f"❌ Escalation API network error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Escalation API unexpected error: {e}")
        return False
