# StartFrame Error Fix - Documentation

## The Error You Were Getting

```
ERROR | TextTransportSimulator#0 Trying to process StartFrame#0 but StartFrame not received yet
```

## Root Cause

When creating custom `FrameProcessor` classes in Pipecat, you **must** call `await super().process_frame(frame, direction)` **FIRST** in your `process_frame()` method.

This is because the parent class's `process_frame()` method handles critical initialization, including:
- Setting up internal queues (`__input_queue`)
- Marking the processor as "started" when it receives `StartFrame`
- Managing frame lifecycle

## What Was Wrong

**Before (BROKEN):**
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    # Custom logic first ❌ WRONG
    if isinstance(frame, StartFrame):
        self._started = True
        logger.info("✅ StartFrame received")

    await self.push_frame(frame, direction)
```

The processor tried to handle the frame before the parent class initialized it, causing the "StartFrame not received yet" error.

## What We Fixed

**After (CORRECT):**
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    # CRITICAL: Call super() first ✅ CORRECT
    await super().process_frame(frame, direction)

    # NOW you can do custom logic
    if isinstance(frame, StartFrame):
        self._started = True
        logger.info("✅ StartFrame received")

    await self.push_frame(frame, direction)
```

## Changes Made to chat_test.py

### 1. TextInputProcessor
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    await super().process_frame(frame, direction)  # ← Added this
    await self.push_frame(frame, direction)
```

### 2. TextOutputProcessor
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    await super().process_frame(frame, direction)  # ← Added this

    if isinstance(frame, TextFrame):
        # ... handle text output

    await self.push_frame(frame, direction)
```

### 3. TextTransportSimulator
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    await super().process_frame(frame, direction)  # ← Added this

    if isinstance(frame, StartFrame):
        self._started = True
        asyncio.create_task(self._process_message_queue())

    await self.push_frame(frame, direction)
```

## Pipecat Best Practices

According to Pipecat documentation:

### ✅ DO:
1. **Always call `super().__init__()`** in your `__init__()` method
2. **Always call `await super().process_frame(frame, direction)`** at the START of `process_frame()`
3. **Always push frames downstream** with `await self.push_frame(frame, direction)`

### ❌ DON'T:
1. Process frames before calling `super().process_frame()`
2. Skip pushing frames (this blocks the pipeline)
3. Forget to call parent constructors

## Why This Pattern Exists

Pipecat's `FrameProcessor` base class handles:
- **Internal queue management**: Creating `__input_queue` when `StartFrame` arrives
- **State tracking**: Marking processors as started/stopped
- **Frame routing**: Ensuring frames flow correctly through the pipeline
- **Error handling**: Proper cleanup and exception management

By calling `super().process_frame()` first, you ensure all this initialization happens before your custom logic runs.

## Testing

After the fix, your chat interface should now work correctly:

```bash
# Start the server
python chat_test.py

# Open browser: http://localhost:8081
# Type messages - should work without StartFrame errors!
```

## References

- Pipecat Docs: https://docs.pipecat.ai/guides/fundamentals/custom-frame-processor
- Related Issues:
  - https://github.com/pipecat-ai/pipecat/issues/2498 (RTVIProcessor StartFrame error)
  - https://github.com/pipecat-ai/pipecat/issues/2007 (Custom processor AttributeError)
  - https://github.com/pipecat-ai/pipecat/issues/1146 (ParallelPipeline initialization)

## Summary

The fix was simple but critical: **Always call `await super().process_frame(frame, direction)` at the beginning of your `process_frame()` method in custom FrameProcessors.**

This ensures proper initialization and prevents the "StartFrame not received yet" error.

---

**Your chat interface is now ready to use!** 🎉
