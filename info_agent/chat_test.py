"""
Info Agent Chat Test Interface
Text-only testing interface for rapid development and testing
Based on booking agent's working chat_test.py structure
"""

import os
import sys
import asyncio
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path for booking agent imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Pipecat imports
from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionFrame,
    LLMMessagesFrame,
    LLMFullResponseEndFrame,
    EndFrame,
    StartFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

# Import flow management
from info_agent.flows.manager import create_flow_manager, initialize_flow_manager
from info_agent.config.settings import info_settings

# Reuse components from booking agent
from pipeline.components import (
    create_llm_service,
    create_context_aggregator
)

load_dotenv(override=True)


class TextInputProcessor(FrameProcessor):
    """
    Processor that converts incoming text messages to TextFrame
    and adds them to the conversation context
    """

    def __init__(self):
        super().__init__()
        logger.info("💬 TextInputProcessor initialized")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames"""
        # CRITICAL: Call super() first to properly initialize the processor
        await super().process_frame(frame, direction)

        # Push all frames downstream
        await self.push_frame(frame, direction)


class TextOutputProcessor(FrameProcessor):
    """
    Processor that captures LLM text output and sends to WebSocket
    """

    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket
        self._buffer = ""
        logger.info("💬 TextOutputProcessor initialized")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process outgoing frames and send text to WebSocket"""
        # CRITICAL: Call super() first to properly initialize the processor
        await super().process_frame(frame, direction)

        # ONLY capture text going DOWNSTREAM (from LLM to output)
        # NOT upstream text (user input)
        if isinstance(frame, TextFrame) and direction == FrameDirection.DOWNSTREAM:
            text = frame.text
            self._buffer += text

            # Send partial response to WebSocket for streaming effect
            try:
                await self.websocket.send_json({
                    "type": "assistant_message_chunk",
                    "text": text
                })
                logger.debug(f"📤 Sent text chunk to browser: {text[:50]}...")
            except Exception as e:
                logger.error(f"❌ Failed to send text chunk: {e}")

        # When LLM finishes, send complete message
        elif isinstance(frame, (LLMFullResponseEndFrame, EndFrame)) and self._buffer:
            try:
                await self.websocket.send_json({
                    "type": "assistant_message_complete",
                    "text": self._buffer
                })
                logger.info(f"✅ Complete message sent: {self._buffer[:100]}...")
                self._buffer = ""
            except Exception as e:
                logger.error(f"❌ Failed to send complete message: {e}")

        await self.push_frame(frame, direction)


class TextTransportSimulator(FrameProcessor):
    """
    Simulates a transport layer for text-only communication
    Acts as both input and output processor
    """

    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket
        self._running = True
        self._started = False
        self._message_queue = asyncio.Queue()
        logger.info("🔌 TextTransportSimulator initialized")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames in both directions"""
        # CRITICAL: Call super() first to properly initialize the processor
        await super().process_frame(frame, direction)

        # Mark as started when we receive StartFrame
        if isinstance(frame, StartFrame):
            self._started = True
            logger.info("✅ TextTransportSimulator received StartFrame - ready to process messages")

            # Start processing queued messages
            asyncio.create_task(self._process_message_queue())

        # Push frame downstream
        await self.push_frame(frame, direction)

    async def _process_message_queue(self):
        """Process messages from the queue after pipeline has started"""
        while self._running:
            try:
                text = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                if text:
                    logger.info(f"📥 Processing queued message: {text}")

                    # Use TranscriptionFrame (like STT does) instead of TextFrame
                    # This way the context aggregator knows it's user input
                    transcription_frame = TranscriptionFrame(text=text, user_id="user", timestamp=0)
                    await self.push_frame(transcription_frame)

                    # Also notify that user "started speaking" and "stopped speaking"
                    # This helps with conversation flow timing
                    await self.push_frame(UserStartedSpeakingFrame())
                    await self.push_frame(UserStoppedSpeakingFrame())

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Error processing message from queue: {e}")

    async def receive_text_message(self, text: str):
        """
        Receive text message from WebSocket and queue it for processing
        """
        logger.info(f"📨 Queueing user message: {text}")
        await self._message_queue.put(text)

    def stop(self):
        """Stop the transport"""
        self._running = False


# FastAPI app
app = FastAPI(
    title="Info Agent - Text Chat Testing",
    description="Text-only chat interface for Info Agent rapid testing",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active sessions
active_sessions: Dict[str, Any] = {}

# Global config for start node
global_start_node = "greeting"  # Info agent starts with greeting


@app.get("/")
async def get_chat_ui():
    """Serve chat test UI"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Info Agent Chat Test</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: rgba(255,255,255,0.95);
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                color: #333;
                font-size: 24px;
                margin-bottom: 5px;
            }
            
            .header p {
                color: #666;
                font-size: 14px;
            }
            
            .status-bar {
                background: rgba(255,255,255,0.9);
                padding: 10px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
            }
            
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #22c55e;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .chat-container {
                flex: 1;
                background: rgba(255,255,255,0.95);
                margin: 20px;
                border-radius: 10px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            
            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
            }
            
            .message {
                margin-bottom: 16px;
                display: flex;
                gap: 12px;
            }
            
            .message.user {
                flex-direction: row-reverse;
            }
            
            .message-bubble {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 18px;
                word-wrap: break-word;
            }
            
            .user .message-bubble {
                background: #667eea;
                color: white;
                border-bottom-right-radius: 4px;
            }
            
            .assistant .message-bubble {
                background: #f1f3f5;
                color: #333;
                border-bottom-left-radius: 4px;
            }
            
            .message-icon {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                flex-shrink: 0;
            }
            
            .user .message-icon {
                background: #667eea;
            }
            
            .assistant .message-icon {
                background: #764ba2;
            }
            
            .input-area {
                padding: 20px;
                background: white;
                border-top: 1px solid #e5e7eb;
            }
            
            .input-container {
                display: flex;
                gap: 10px;
            }
            
            #messageInput {
                flex: 1;
                padding: 12px 16px;
                border: 2px solid #e5e7eb;
                border-radius: 24px;
                font-size: 14px;
                outline: none;
                transition: border-color 0.3s;
            }
            
            #messageInput:focus {
                border-color: #667eea;
            }
            
            #sendButton {
                padding: 12px 24px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 24px;
                cursor: pointer;
                font-weight: 600;
                transition: background 0.3s;
            }
            
            #sendButton:hover {
                background: #5568d3;
            }
            
            #sendButton:disabled {
                background: #cbd5e1;
                cursor: not-allowed;
            }
            
            .typing-indicator {
                display: none;
                padding: 12px 16px;
                background: #f1f3f5;
                border-radius: 18px;
                border-bottom-left-radius: 4px;
                max-width: 70px;
            }
            
            .typing-indicator.active {
                display: block;
            }
            
            .typing-indicator span {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #94a3b8;
                margin: 0 2px;
                animation: typing 1.4s infinite;
            }
            
            .typing-indicator span:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .typing-indicator span:nth-child(3) {
                animation-delay: 0.4s;
            }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 Info Agent - Ualà</h1>
            <p>Medical Information Assistant - Text Testing Interface</p>
        </div>
        
        <div class="status-bar">
            <div class="status-indicator">
                <span class="status-dot"></span>
                <span id="statusText">Connecting...</span>
            </div>
            <div>
                <span>Sessions: <strong id="sessionCount">0</strong></span>
            </div>
        </div>
        
        <div class="chat-container">
            <div class="messages" id="messages">
                <!-- Messages will appear here -->
            </div>
            
            <div class="input-area">
                <div class="input-container">
                    <input 
                        type="text" 
                        id="messageInput" 
                        placeholder="Scrivi il tuo messaggio..." 
                        disabled
                    >
                    <button id="sendButton" disabled>Invia</button>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let isConnected = false;
            let currentAssistantMessage = '';

            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;

                console.log('Connecting to:', wsUrl);
                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    console.log('WebSocket connected');
                    isConnected = true;
                    document.getElementById('statusText').textContent = 'Connected';
                    document.getElementById('messageInput').disabled = false;
                    document.getElementById('sendButton').disabled = false;
                    document.getElementById('messageInput').focus();
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('Received:', data);

                    if (data.type === 'system_ready') {
                        addSystemMessage(`✅ Info Agent ready`);
                    }
                    else if (data.type === 'assistant_message_chunk') {
                        // Streaming chunks from LLM - accumulate
                        currentAssistantMessage += data.text;
                        updateAssistantMessage(currentAssistantMessage);
                    }
                    else if (data.type === 'assistant_message_complete') {
                        // Complete message - finalize and reset
                        finalizeAssistantMessage(currentAssistantMessage);
                        currentAssistantMessage = '';
                    }
                    else if (data.type === 'assistant_message') {
                        // Single complete message (fallback)
                        currentAssistantMessage = '';
                        addMessage('assistant', data.text);
                    }
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    document.getElementById('statusText').textContent = 'Error';
                };

                ws.onclose = () => {
                    console.log('Disconnected');
                    isConnected = false;
                    document.getElementById('statusText').textContent = 'Disconnected';
                    document.getElementById('messageInput').disabled = true;
                    document.getElementById('sendButton').disabled = true;
                };
            }
            
            function sendMessage() {
                const text = document.getElementById('messageInput').value.trim();

                if (!text || !isConnected) return;

                addMessage('user', text);

                ws.send(JSON.stringify({
                    type: 'user_message',
                    text: text
                }));

                document.getElementById('messageInput').value = '';
                showTypingIndicator();
            }
            
            function addMessage(role, text) {
                const messagesDiv = document.getElementById('messages');

                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;

                const icon = document.createElement('div');
                icon.className = 'message-icon';
                icon.textContent = role === 'user' ? '👤' : '🏥';

                const bubble = document.createElement('div');
                bubble.className = 'message-bubble';
                bubble.textContent = text;

                messageDiv.appendChild(icon);
                messageDiv.appendChild(bubble);

                // Remove typing indicator if exists
                const typingIndicator = document.querySelector('.typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }

                messagesDiv.appendChild(messageDiv);
                scrollToBottom();
            }

            function updateAssistantMessage(text) {
                let messageDiv = document.querySelector('.message.assistant.streaming');

                if (!messageDiv) {
                    // Remove ALL typing indicators
                    const typingIndicators = document.querySelectorAll('.message.assistant');
                    typingIndicators.forEach(indicator => {
                        if (indicator.querySelector('.typing-indicator')) {
                            indicator.remove();
                        }
                    });

                    // Create new streaming message
                    messageDiv = document.createElement('div');
                    messageDiv.className = 'message assistant streaming';

                    const icon = document.createElement('div');
                    icon.className = 'message-icon';
                    icon.textContent = '🏥';

                    const bubble = document.createElement('div');
                    bubble.className = 'message-bubble';

                    messageDiv.appendChild(icon);
                    messageDiv.appendChild(bubble);

                    document.getElementById('messages').appendChild(messageDiv);
                }

                const bubble = messageDiv.querySelector('.message-bubble');
                bubble.textContent = text;
                scrollToBottom();
            }

            function finalizeAssistantMessage(text) {
                // Remove ALL streaming classes to ensure clean state
                const allStreamingMessages = document.querySelectorAll('.message.assistant.streaming');
                allStreamingMessages.forEach(msg => {
                    msg.classList.remove('streaming');
                });

                // Reset the current message buffer
                currentAssistantMessage = '';

                // Ensure we scroll to bottom
                scrollToBottom();
            }

            function showTypingIndicator() {
                const indicator = document.createElement('div');
                indicator.className = 'message assistant';
                indicator.innerHTML = `
                    <div class="message-icon">🏥</div>
                    <div class="typing-indicator active">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                `;
                document.getElementById('messages').appendChild(indicator);
                scrollToBottom();
            }

            function addSystemMessage(text) {
                const messageDiv = document.createElement('div');
                messageDiv.style.textAlign = 'center';
                messageDiv.style.color = '#666';
                messageDiv.style.fontSize = '12px';
                messageDiv.style.margin = '15px 0';
                messageDiv.style.fontStyle = 'italic';
                messageDiv.textContent = text;
                document.getElementById('messages').appendChild(messageDiv);
                scrollToBottom();
            }

            function scrollToBottom() {
                const container = document.getElementById('messages');
                container.scrollTop = container.scrollHeight;
            }
            
            // Event listeners
            document.getElementById('sendButton').addEventListener('click', sendMessage);
            
            document.getElementById('messageInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            
            // Connect on load
            connect();
        </script>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "info-agent-text-chat",
        "version": "1.0.0",
        "active_sessions": len(active_sessions),
        "mode": "text-only",
        "start_node": global_start_node
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Text-only WebSocket endpoint for chat testing
    """
    global global_start_node

    await websocket.accept()

    import uuid
    session_id = f"info-chat-{uuid.uuid4().hex[:8]}"

    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"New Info Agent Text Chat Session")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Start Node: {global_start_node}")
    logger.info(f"Mode: Text-only (No STT/TTS)")
    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Variables for pipeline
    runner = None
    task = None
    text_transport = None
    text_output = None

    try:
        # Check required API keys (only LLM needed for text mode)
        if not os.getenv("OPENAI_API_KEY"):
            raise Exception("OPENAI_API_KEY not found - required for LLM")

        # CREATE SERVICES (NO STT/TTS FOR TEXT MODE!)
        logger.info("Initializing services for TEXT mode...")
        llm = create_llm_service()
        context_aggregator = create_context_aggregator(llm)
        logger.info("✅ LLM and context aggregator initialized (no STT/TTS)")

        # CREATE TEXT TRANSPORT SIMULATOR
        text_transport = TextTransportSimulator(websocket)
        text_output = TextOutputProcessor(websocket)

        # CREATE PIPELINE (TEXT-ONLY - NO STT/TTS!)
        pipeline = Pipeline([
            text_transport,              # Text input from WebSocket
            context_aggregator.user(),   # Add user message to context
            llm,                         # LLM with flows
            text_output,                 # Capture and send text output
            context_aggregator.assistant()  # Add assistant response to context
        ])

        logger.info("Text Chat Pipeline structure:")
        logger.info("  1. TextTransportSimulator (WebSocket text input)")
        logger.info("  2. Context Aggregator (User)")
        logger.info("  3. OpenAI LLM (with flows)")
        logger.info("  4. TextOutputProcessor (WebSocket text output)")
        logger.info("  5. Context Aggregator (Assistant)")
        logger.info("✅ NO STT/TTS - Pure text mode for fast testing!")

        # Create pipeline task
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=False,  # Not needed for text
                enable_transcriptions=False,  # No audio transcription
            ),
            cancel_on_idle_timeout=False  # MUST be direct parameter
        )

        # CREATE FLOW MANAGER
        flow_manager = create_flow_manager(task, llm, context_aggregator, None)
        flow_manager.state["session_id"] = session_id

        # Store session
        active_sessions[session_id] = {
            "websocket": websocket,
            "connected_at": asyncio.get_event_loop().time(),
            "mode": "text-only",
            "flow_manager": flow_manager,
            "text_transport": text_transport
        }

        # Initialize flow manager
        try:
            await initialize_flow_manager(flow_manager, global_start_node)
            logger.success(f"✅ Flow initialized with {global_start_node} node")

            # Notify client that system is ready
            await websocket.send_json({
                "type": "system_ready",
                "start_node": global_start_node
            })
        except Exception as e:
            logger.error(f"Error during flow initialization: {e}")

        # START PIPELINE
        runner = PipelineRunner()
        logger.info(f"🚀 Text Chat Pipeline started for session: {session_id}")

        # Run pipeline in background
        pipeline_task = asyncio.create_task(runner.run(task))

        # Handle incoming WebSocket messages
        try:
            while True:
                # Receive message from WebSocket
                message = await websocket.receive_json()

                if message.get("type") == "user_message":
                    user_text = message.get("text", "").strip()
                    if user_text:
                        logger.info(f"💬 User: {user_text}")

                        # Send to pipeline
                        await text_transport.receive_text_message(user_text)

        except WebSocketDisconnect:
            logger.info(f"🔌 Text chat client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error in message loop: {e}")
        finally:
            # Cancel pipeline
            if pipeline_task:
                pipeline_task.cancel()
                try:
                    await pipeline_task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"❌ Error in Text Chat WebSocket handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if session_id in active_sessions:
            del active_sessions[session_id]

        # Cancel task
        if task:
            await task.cancel()

        logger.info(f"Text Chat Session ended: {session_id}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Text-Based Chat Testing for Info Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chat_test.py                         # Start with greeting (default)
  python chat_test.py --start-node greeting   # Explicit greeting start
  python chat_test.py --port 8082             # Use custom port
        """
    )

    parser.add_argument(
        "--start-node",
        default="greeting",
        choices=["greeting"],
        help="Starting flow node (default: greeting)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8082,
        help="Port to run the server on (default: 8082)"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )

    return parser.parse_args()


def main():
    """Main function"""
    global global_start_node

    args = parse_arguments()
    global_start_node = args.start_node

    # Check required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ Missing OPENAI_API_KEY environment variable")
        sys.exit(1)

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🚀 INFO AGENT - TEXT CHAT TESTING MODE")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"📍 Start Node: {args.start_node}")
    logger.info(f"🌐 Server: http://{args.host}:{args.port}")
    logger.info(f"💬 Mode: Text-only (No STT/TTS)")
    logger.info(f"⚡ Benefits: Instant testing, lower costs, better debugging")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("📖 INSTRUCTIONS:")
    logger.info(f"   1. Open http://localhost:{args.port} in your browser")
    logger.info("   2. Start typing to test your Info Agent flows")
    logger.info("   3. All your existing flows work exactly the same")
    logger.info("   4. Press Ctrl+C to stop the server")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Text chat testing server stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)