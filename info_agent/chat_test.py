"""
Info Agent Chat Test Interface
Text-only testing interface for rapid development and testing
"""

import os
import sys
import asyncio
import json
from typing import Dict, Any
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Pipecat imports
from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    TextFrame,
    EndFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

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
   
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            # Convert text to transcription frame
            transcription = TranscriptionFrame(
                text=frame.text,
                user_id="test_user",
                timestamp=asyncio.get_event_loop().time()
            )
            await self.push_frame(transcription, direction)
        else:
            await self.push_frame(frame, direction)


class TextOutputProcessor(FrameProcessor):
   
    
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket
        self.current_response = ""
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # Capture LLM text output
        from pipecat.frames.frames import LLMTextFrame, LLMFullResponseEndFrame
        
        if isinstance(frame, LLMTextFrame):
            # Accumulate response text
            self.current_response += frame.text
            
            # Stream to browser
            try:
                await self.websocket.send_json({
                    "type": "assistant_delta",
                    "text": frame.text
                })
            except Exception as e:
                logger.error(f"Error sending delta: {e}")
        
        elif isinstance(frame, LLMFullResponseEndFrame):
            # Response complete
            logger.info(f"🤖 Assistant: {self.current_response}")
            
            try:
                await self.websocket.send_json({
                    "type": "assistant_complete",
                    "text": self.current_response
                })
            except Exception as e:
                logger.error(f"Error sending completion: {e}")
            
            # Reset for next response
            self.current_response = ""
        
        await self.push_frame(frame, direction)


class TextTransportSimulator:
  
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.text_input = TextInputProcessor()
        self.text_output = None
    
    def input(self):
        return self.text_input
    
    def output(self):
        if not self.text_output:
            self.text_output = TextOutputProcessor(self.websocket)
        return self.text_output
    
    def event_handler(self, event_name: str):
        """Decorator for event handlers"""
        def decorator(func):
            return func
        return decorator


# FastAPI app
app = FastAPI(
    title="Info Agent Chat Test",
    description="Text-only testing interface for Info Agent",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active sessions
active_sessions: Dict[str, Any] = {}


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
            let isAssistantSpeaking = false;
            
            function connect() {
                const sessionId = 'test-' + Date.now();
                ws = new WebSocket(`ws://localhost:8082/ws?session_id=${sessionId}`);
                
                ws.onopen = () => {
                    console.log('Connected to Info Agent');
                    document.getElementById('statusText').textContent = 'Connected';
                    document.getElementById('messageInput').disabled = false;
                    document.getElementById('sendButton').disabled = false;
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'assistant_start') {
                        isAssistantSpeaking = true;
                        showTypingIndicator();
                    } 
                    else if (data.type === 'assistant_delta') {
                        hideTypingIndicator();
                        appendToLastAssistantMessage(data.text);
                    } 
                    else if (data.type === 'assistant_complete') {
                        hideTypingIndicator();
                        isAssistantSpeaking = false;
                    }
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    document.getElementById('statusText').textContent = 'Error';
                };
                
                ws.onclose = () => {
                    console.log('Disconnected');
                    document.getElementById('statusText').textContent = 'Disconnected';
                    document.getElementById('messageInput').disabled = true;
                    document.getElementById('sendButton').disabled = true;
                    
                    // Reconnect after 2 seconds
                    setTimeout(connect, 2000);
                };
            }
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                const text = input.value.trim();
                
                if (text && ws && ws.readyState === WebSocket.OPEN) {
                    // Add user message to chat
                    addMessage('user', text);
                    
                    // Send to server
                    ws.send(JSON.stringify({
                        type: 'user_message',
                        text: text
                    }));
                    
                    // Clear input
                    input.value = '';
                    
                    // Show typing indicator
                    showTypingIndicator();
                }
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
                
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            let currentAssistantMessage = null;
            
            function appendToLastAssistantMessage(text) {
                const messagesDiv = document.getElementById('messages');
                
                // If we have a current message element, append to it
                if (currentAssistantMessage && isAssistantSpeaking) {
                    const bubble = currentAssistantMessage.querySelector('.message-bubble');
                    bubble.textContent += text;
                } else {
                    // Create new assistant message
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message assistant';
                    
                    const icon = document.createElement('div');
                    icon.className = 'message-icon';
                    icon.textContent = '🏥';
                    
                    const bubble = document.createElement('div');
                    bubble.className = 'message-bubble';
                    bubble.textContent = text;
                    
                    messageDiv.appendChild(icon);
                    messageDiv.appendChild(bubble);
                    messagesDiv.appendChild(messageDiv);
                    
                    currentAssistantMessage = messageDiv;
                }
                
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            function showTypingIndicator() {
                let indicator = document.getElementById('typingIndicator');
                if (!indicator) {
                    const messagesDiv = document.getElementById('messages');
                    
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message assistant';
                    messageDiv.id = 'typingIndicator';
                    
                    const icon = document.createElement('div');
                    icon.className = 'message-icon';
                    icon.textContent = '🏥';
                    
                    const indicator = document.createElement('div');
                    indicator.className = 'typing-indicator active';
                    indicator.innerHTML = '<span></span><span></span><span></span>';
                    
                    messageDiv.appendChild(icon);
                    messageDiv.appendChild(indicator);
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            }
            
            function hideTypingIndicator() {
                const indicator = document.getElementById('typingIndicator');
                if (indicator) {
                    indicator.remove();
                }
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat testing"""
    await websocket.accept()
    
    # Extract session ID
    query_params = dict(websocket.query_params)
    session_id = query_params.get("session_id", "test-session")
    
    logger.info(f"💬 Chat test session started: {session_id}")
    
    task = None
    
    try:
    
        llm = create_llm_service()
        context_aggregator = create_context_aggregator(llm)
        
        # Create text transport simulator
        transport = TextTransportSimulator(websocket)
        
       
        pipeline = Pipeline([
            transport.input(),           # Text input
            context_aggregator.user(),   # User context
            llm,                         # LLM processing
            transport.output(),          # Text output
            context_aggregator.assistant()
        ])
        
        logger.info("Text-only Pipeline structure:")
        logger.info("  1. TextInputProcessor (text → transcription)")
        logger.info("  2. Context Aggregator (User)")
        logger.info("  3. OpenAI LLM (with flows)")
        logger.info("  4. TextOutputProcessor (LLM → browser)")
        logger.info("  5. Context Aggregator (Assistant)")
        
        # Create task
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=False,  # Not needed for text
            )
        )
        
        # Create flow manager
        flow_manager = create_flow_manager(task, llm, context_aggregator, transport)
        flow_manager.state["session_id"] = session_id
        
        # Store session
        active_sessions[session_id] = {
            "websocket": websocket,
            "started_at": asyncio.get_event_loop().time()
        }
        
        # Initialize flow with greeting
        await initialize_flow_manager(flow_manager, "greeting")
        logger.success(f"✅ Flow initialized for chat test: {session_id}")
        
        # Handle incoming messages
        async def handle_messages():
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message["type"] == "user_message":
                        text = message["text"]
                        logger.info(f"👤 User: {text}")
                        
                        # Push text frame into pipeline
                        await transport.text_input.push_frame(TextFrame(text=text))
                        
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {session_id}")
            except Exception as e:
                logger.error(f"Message handling error: {e}")
        
        # Run message handler and pipeline concurrently
        runner = PipelineRunner()
        
        await asyncio.gather(
            handle_messages(),
            runner.run(task)
        )
        
    except Exception as e:
        logger.error(f"❌ Chat test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        if task:
            await task.cancel()
        
        logger.info(f"Chat test session ended: {session_id}")


if __name__ == "__main__":
    import uvicorn
    
    port = 8082  # Different port from main.py (8081)
    
    logger.info("🚀 Starting Info Agent Chat Test Interface")
    logger.info(f"📝 Text-only testing - No STT/TTS costs")
    logger.info(f"🌐 Open http://localhost:{port} in your browser")
    
    uvicorn.run(
        "info_agent.chat_test:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )