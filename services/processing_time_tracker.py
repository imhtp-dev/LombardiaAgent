"""
Processing Time Tracker for Healthcare Booking Agent
Monitors response time and injects "processing" message if agent takes too long to respond
"""

import asyncio
import time
from loguru import logger
from typing import Optional
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import (
    Frame,
    TTSSpeakFrame,
    UserStoppedSpeakingFrame,
    UserStartedSpeakingFrame,
    TranscriptionFrame
)
from config.settings import settings


class ProcessingTimeTracker(FrameProcessor):
    """
    Tracks processing time from when user stops speaking to when TTS response starts.
    If processing takes longer than threshold, injects a "please wait" message.
    """

    def __init__(self, threshold_seconds: float = 3.0):
        """
        Initialize the processing time tracker

        Args:
            threshold_seconds: Seconds to wait before injecting processing message (default: 3.0)
        """
        super().__init__()
        self._threshold = threshold_seconds
        self._processing_start_time: Optional[float] = None
        self._warning_spoken = False
        self._timer_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        logger.info(f"🕐 ProcessingTimeTracker initialized with {threshold_seconds}s threshold")

    async def process_frame(self, frame: Frame, direction):
        """
        Process frames flowing through the pipeline and monitor timing
        """
        await super().process_frame(frame, direction)

        # User stopped speaking - start monitoring processing time
        if isinstance(frame, UserStoppedSpeakingFrame):
            await self._start_timer()

        # User started speaking again - cancel monitoring (user interrupted)
        elif isinstance(frame, UserStartedSpeakingFrame):
            await self._cancel_timer()

        # TTS is about to speak - processing complete, stop monitoring
        elif isinstance(frame, TTSSpeakFrame):
            await self._stop_timer()

        # Pass frame through to next processor
        await self.push_frame(frame, direction)

    async def _start_timer(self):
        """Start monitoring processing time when user stops speaking"""
        async with self._lock:
            # Cancel any existing timer
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
                try:
                    await self._timer_task
                except asyncio.CancelledError:
                    pass

            # Reset state
            self._processing_start_time = time.time()
            self._warning_spoken = False

            # Start background timer task
            self._timer_task = asyncio.create_task(self._check_processing_time())

            logger.debug("⏱️ Processing timer started")

    async def _stop_timer(self):
        """Stop monitoring when TTS starts (response is ready)"""
        async with self._lock:
            if self._processing_start_time:
                elapsed = time.time() - self._processing_start_time
                logger.debug(f"⏱️ Processing completed in {elapsed:.2f}s")

            # Cancel timer task
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
                try:
                    await self._timer_task
                except asyncio.CancelledError:
                    pass

            # Reset state
            self._processing_start_time = None
            self._warning_spoken = False
            self._timer_task = None

    async def _cancel_timer(self):
        """Cancel monitoring when user interrupts"""
        async with self._lock:
            logger.debug("⏱️ Processing timer cancelled (user interrupted)")

            # Cancel timer task
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
                try:
                    await self._timer_task
                except asyncio.CancelledError:
                    pass

            # Reset state
            self._processing_start_time = None
            self._warning_spoken = False
            self._timer_task = None

    async def _check_processing_time(self):
        """
        Background task that checks elapsed time every 0.5 seconds.
        Injects processing message if threshold is exceeded.
        """
        try:
            while True:
                await asyncio.sleep(0.5)  # Check twice per second

                # Check if we should inject warning message
                if self._processing_start_time and not self._warning_spoken:
                    elapsed = time.time() - self._processing_start_time

                    if elapsed > self._threshold:
                        await self._inject_processing_message()
                        break  # Exit loop after speaking once

        except asyncio.CancelledError:
            # Timer was cancelled (normal flow)
            pass
        except Exception as e:
            logger.error(f"❌ Error in processing time checker: {e}")

    async def _inject_processing_message(self):
        """Inject 'please wait' message into TTS pipeline"""
        async with self._lock:
            if self._warning_spoken:
                return  # Already spoken, don't repeat

            elapsed = time.time() - self._processing_start_time if self._processing_start_time else 0
            logger.info(f"🔔 Processing exceeded {self._threshold}s threshold (elapsed: {elapsed:.2f}s) - injecting message")

            # Get language-specific message
            language_instruction = settings.language_config
            message = "Attendi qualche secondo che sto cercando" if "Italian" in language_instruction else "Please wait a few seconds while I search"

            # Inject TTS message into pipeline
            await self.push_frame(TTSSpeakFrame(message))

            # Mark as spoken to prevent repeats
            self._warning_spoken = True

            logger.success(f"✅ Processing message injected: '{message}'")

    async def cleanup(self):
        """Cleanup when processor is destroyed"""
        # Cancel any running timer
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

        await super().cleanup()


def create_processing_time_tracker(threshold_seconds: float = 3.0) -> ProcessingTimeTracker:
    """
    Create a ProcessingTimeTracker for healthcare booking agent

    Args:
        threshold_seconds: Seconds to wait before injecting message (default: 3.0 seconds)

    Returns:
        ProcessingTimeTracker: Configured processor
    """
    logger.info(f"🕐 Creating ProcessingTimeTracker with {threshold_seconds}s threshold")

    return ProcessingTimeTracker(threshold_seconds=threshold_seconds)
