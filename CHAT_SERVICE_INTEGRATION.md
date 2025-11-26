# Chat Service Integration Guide
## WebSocket Chat API for Dashboard Integration

This guide shows how to integrate the Pipecat Chat Service into your Node.js dashboard.

---

## 📋 Overview

The Chat Service provides a **VAPI-like API** for integrating the Info Agent into external applications:

- **REST API**: Create/manage chat sessions
- **WebSocket**: Real-time bidirectional communication
- **Session Persistence**: Maintains conversation context
- **Streaming Responses**: AI responses stream word-by-word

---

## 🚀 Deployment

### Deploy with Docker Compose

```bash
# Build and deploy
docker-compose build
docker-compose up -d chat-service

# Verify deployment
curl http://your-azure-vm:8002/health

# Check logs
docker-compose logs -f chat-service
```

### Environment Variables

Add to your `.env` file:

```bash
# Chat Service Configuration
CHAT_SERVICE_PORT=8002
CHAT_SERVICE_HOST=0.0.0.0

# Required API Keys (already configured)
OPENAI_API_KEY=your_key_here
```

---

## 📡 API Reference

### Base URL

```
Production: http://your-azure-vm-ip:8002
Local Dev: http://localhost:8002
```

### Endpoints

#### 1. Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "pipecat-chat-service",
  "agent": "Info Agent - Cerba Lombardia",
  "version": "1.0.0",
  "active_sessions": 5,
  "timestamp": "2025-11-26T10:30:00Z"
}
```

---

#### 2. Create Session
```
POST /api/create-session
```

**Request Body** (optional):
```json
{
  "user_id": "user_12345",
  "metadata": {
    "source": "dashboard",
    "user_name": "John Doe"
  }
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "websocket_url": "ws://your-azure-vm:8002/ws/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-26T10:30:00Z",
  "status": "ready"
}
```

---

#### 3. Get Session Info
```
GET /api/session/{session_id}/info
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-26T10:30:00Z",
  "message_count": 12,
  "user_id": "user_12345",
  "status": "active"
}
```

---

#### 4. Delete Session
```
DELETE /api/session/{session_id}
```

**Response:**
```json
{
  "status": "deleted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted_at": "2025-11-26T10:35:00Z"
}
```

---

#### 5. WebSocket Chat
```
WS /ws/{session_id}
```

**Message Format (Client → Server):**
```json
{
  "message": "What are your blood test hours?"
}
```

**Response Formats (Server → Client):**

**Status Update:**
```json
{
  "type": "status",
  "status": "connected|typing|ready",
  "session_id": "...",
  "timestamp": "2025-11-26T10:30:00Z"
}
```

**Function Called (Real-time):**
```json
{
  "type": "function_called",
  "function_name": "knowledge_base_lombardia",
  "timestamp": "2025-11-26T10:30:00.500Z"
}
```
*Sent in real-time when the AI calls a function (e.g., knowledge base query, price check, booking API)*

**Streaming Chunk:**
```json
{
  "type": "chunk",
  "content": "We are open ",
  "timestamp": "2025-11-26T10:30:01Z"
}
```

**Complete Response:**
```json
{
  "type": "complete",
  "full_response": "We are open Monday-Friday 7am-10am for blood tests.",
  "timestamp": "2025-11-26T10:30:03Z"
}
```

**Error:**
```json
{
  "type": "error",
  "error": "Failed to process message"
}
```

---

## 💻 Node.js Integration

### Option 1: Full Client Library (Recommended)

Create `lib/pipecat-chat-client.js`:

```javascript
const axios = require('axios');
const WebSocket = require('ws');
const EventEmitter = require('events');

class PipecatChatClient extends EventEmitter {
  constructor(baseUrl) {
    super();
    this.baseUrl = baseUrl; // e.g., 'http://your-azure-vm:8002'
    this.sessionId = null;
    this.ws = null;
    this.isConnected = false;
  }

  /**
   * Create a new chat session
   * @param {string} userId - Optional user identifier
   * @param {object} metadata - Optional metadata
   * @returns {Promise<string>} Session ID
   */
  async createSession(userId = null, metadata = {}) {
    try {
      const response = await axios.post(`${this.baseUrl}/api/create-session`, {
        user_id: userId,
        metadata: metadata
      });

      this.sessionId = response.data.session_id;
      console.log('✅ Session created:', this.sessionId);

      return this.sessionId;
    } catch (error) {
      console.error('❌ Failed to create session:', error.message);
      throw error;
    }
  }

  /**
   * Connect to WebSocket for real-time chat
   * @returns {Promise<void>}
   */
  connect() {
    return new Promise((resolve, reject) => {
      if (!this.sessionId) {
        reject(new Error('No session ID. Call createSession() first.'));
        return;
      }

      const wsUrl = this.baseUrl.replace('http', 'ws') + `/ws/${this.sessionId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.on('open', () => {
        this.isConnected = true;
        console.log('✅ WebSocket connected');
        this.emit('connected');
        resolve();
      });

      this.ws.on('message', (data) => {
        try {
          const message = JSON.parse(data);
          this.handleMessage(message);
        } catch (error) {
          console.error('❌ Failed to parse message:', error);
        }
      });

      this.ws.on('close', () => {
        this.isConnected = false;
        console.log('🔌 WebSocket disconnected');
        this.emit('disconnected');
      });

      this.ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error);
        this.emit('error', error);
        reject(error);
      });
    });
  }

  /**
   * Handle incoming messages from server
   */
  handleMessage(message) {
    switch (message.type) {
      case 'status':
        if (message.status === 'typing') {
          this.emit('typing');
        } else if (message.status === 'ready') {
          this.emit('ready');
        }
        break;

      case 'function_called':
        // AI called a function (e.g., knowledge base, price check)
        this.emit('function_called', {
          function_name: message.function_name,
          timestamp: message.timestamp
        });
        break;

      case 'chunk':
        // Real-time streaming chunk
        this.emit('chunk', message.content);
        break;

      case 'complete':
        // Full response received
        this.emit('message', message.full_response);
        break;

      case 'error':
        this.emit('error', new Error(message.error));
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  /**
   * Send a message to the AI
   * @param {string} text - Message text
   */
  sendMessage(text) {
    if (!this.isConnected) {
      throw new Error('WebSocket not connected');
    }

    this.ws.send(JSON.stringify({ message: text }));
  }

  /**
   * Get session information
   * @returns {Promise<object>}
   */
  async getSessionInfo() {
    if (!this.sessionId) {
      throw new Error('No active session');
    }

    const response = await axios.get(`${this.baseUrl}/api/session/${this.sessionId}/info`);
    return response.data;
  }

  /**
   * Close session and cleanup
   */
  async disconnect() {
    if (this.ws) {
      this.ws.close();
    }

    if (this.sessionId) {
      try {
        await axios.delete(`${this.baseUrl}/api/session/${this.sessionId}`);
        console.log('✅ Session deleted');
      } catch (error) {
        console.error('⚠️ Failed to delete session:', error.message);
      }
    }

    this.sessionId = null;
    this.isConnected = false;
  }
}

module.exports = PipecatChatClient;
```

---

### Usage Example

```javascript
const PipecatChatClient = require('./lib/pipecat-chat-client');

// Initialize client
const chatClient = new PipecatChatClient('http://your-azure-vm:8002');

// Event handlers
chatClient.on('connected', () => {
  console.log('🟢 Connected to chat service');
});

chatClient.on('typing', () => {
  console.log('⌨️ AI is typing...');
});

chatClient.on('function_called', (data) => {
  console.log(`🔧 Function called: ${data.function_name}`);
});

chatClient.on('chunk', (text) => {
  // Display text chunk in real-time (streaming effect)
  process.stdout.write(text);
});

chatClient.on('message', (fullMessage) => {
  console.log('\n✅ Complete message:', fullMessage);
});

chatClient.on('error', (error) => {
  console.error('❌ Error:', error.message);
});

chatClient.on('disconnected', () => {
  console.log('🔌 Disconnected from chat service');
});

// Main flow
async function startChat() {
  try {
    // 1. Create session
    await chatClient.createSession('user_12345', {
      source: 'dashboard',
      user_name: 'John Doe'
    });

    // 2. Connect WebSocket
    await chatClient.connect();

    // 3. Send messages
    chatClient.sendMessage('What are your blood test hours?');

    // Wait for response...
    setTimeout(() => {
      chatClient.sendMessage('What about Saturday?');
    }, 5000);

    // 4. Cleanup after 30 seconds
    setTimeout(async () => {
      await chatClient.disconnect();
    }, 30000);

  } catch (error) {
    console.error('❌ Failed to start chat:', error);
  }
}

startChat();
```

---

## 🎨 React/Next.js Integration

### React Hook

Create `hooks/usePipecatChat.js`:

```javascript
import { useState, useEffect, useCallback, useRef } from 'react';
import PipecatChatClient from '@/lib/pipecat-chat-client';

export function usePipecatChat(baseUrl) {
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState([]);
  const [currentChunk, setCurrentChunk] = useState('');
  const [functionCalls, setFunctionCalls] = useState([]);
  const clientRef = useRef(null);

  useEffect(() => {
    // Initialize client
    clientRef.current = new PipecatChatClient(baseUrl);

    // Event handlers
    clientRef.current.on('connected', () => {
      setIsConnected(true);
    });

    clientRef.current.on('typing', () => {
      setIsTyping(true);
    });

    clientRef.current.on('function_called', (data) => {
      // Track function calls for analytics/display
      setFunctionCalls((prev) => [...prev, {
        function_name: data.function_name,
        timestamp: data.timestamp
      }]);
    });

    clientRef.current.on('chunk', (text) => {
      setCurrentChunk((prev) => prev + text);
    });

    clientRef.current.on('message', (fullMessage) => {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: fullMessage,
        timestamp: new Date().toISOString()
      }]);
      setCurrentChunk('');
      setIsTyping(false);
    });

    clientRef.current.on('disconnected', () => {
      setIsConnected(false);
    });

    // Cleanup
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
      }
    };
  }, [baseUrl]);

  const connect = useCallback(async (userId, metadata) => {
    try {
      await clientRef.current.createSession(userId, metadata);
      await clientRef.current.connect();
    } catch (error) {
      console.error('Failed to connect:', error);
      throw error;
    }
  }, []);

  const sendMessage = useCallback((text) => {
    if (!isConnected) {
      throw new Error('Not connected');
    }

    // Add user message to UI
    setMessages((prev) => [...prev, {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    }]);

    // Send to AI
    clientRef.current.sendMessage(text);
  }, [isConnected]);

  const disconnect = useCallback(async () => {
    if (clientRef.current) {
      await clientRef.current.disconnect();
    }
  }, []);

  return {
    isConnected,
    isTyping,
    messages,
    currentChunk,
    functionCalls,
    connect,
    sendMessage,
    disconnect
  };
}
```

---

### React Component

```jsx
'use client';

import { useState } from 'react';
import { usePipecatChat } from '@/hooks/usePipecatChat';

export default function ChatWidget() {
  const [input, setInput] = useState('');
  const {
    isConnected,
    isTyping,
    messages,
    currentChunk,
    functionCalls,
    connect,
    sendMessage,
    disconnect
  } = usePipecatChat('http://your-azure-vm:8002');

  const handleConnect = async () => {
    try {
      await connect('user_12345', { source: 'dashboard' });
    } catch (error) {
      alert('Failed to connect: ' + error.message);
    }
  };

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="chat-widget">
      {!isConnected ? (
        <button onClick={handleConnect}>Connect to Chat</button>
      ) : (
        <>
          <div className="messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <strong>{msg.role === 'user' ? 'You' : 'AI'}:</strong>
                <p>{msg.content}</p>
              </div>
            ))}

            {/* Show streaming chunk in real-time */}
            {currentChunk && (
              <div className="message assistant streaming">
                <strong>AI:</strong>
                <p>{currentChunk}</p>
              </div>
            )}

            {isTyping && !currentChunk && (
              <div className="typing-indicator">AI is typing...</div>
            )}
          </div>

          <div className="input-area">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type your message..."
            />
            <button onClick={handleSend}>Send</button>
          </div>

          {/* Display function calls for analytics/debugging */}
          {functionCalls.length > 0 && (
            <div className="function-calls-indicator">
              🔧 Functions called: {functionCalls.map(f => f.function_name).join(', ')}
            </div>
          )}

          <button onClick={disconnect}>Disconnect</button>
        </>
      )}
    </div>
  );
}
```

---

## 🔐 Production Considerations

### 1. CORS Configuration

Update `chat_service.py` for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-dashboard-domain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Authentication

Add authentication to protect the API:

```javascript
// In your Node.js backend
const jwt = require('jsonwebtoken');

async function createAuthenticatedSession(userId) {
  // Create session with JWT
  const token = jwt.sign({ userId }, process.env.JWT_SECRET);

  const response = await axios.post('http://your-azure-vm:8002/api/create-session', {
    user_id: userId,
    metadata: { token }
  }, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  return response.data;
}
```

### 3. Rate Limiting

Consider adding rate limiting to prevent abuse.

### 4. Session Cleanup

Sessions persist until explicitly deleted. Implement cleanup:

```javascript
// Cleanup sessions after 1 hour of inactivity
setInterval(async () => {
  const inactiveSessions = getInactiveSessions(); // Your logic
  for (const sessionId of inactiveSessions) {
    await axios.delete(`http://your-azure-vm:8002/api/session/${sessionId}`);
  }
}, 60 * 60 * 1000); // Every hour
```

---

## 🧪 Testing

### Test Locally

```bash
# Start chat service
python chat_service.py

# In another terminal, test with curl
curl -X POST http://localhost:8002/api/create-session

# Test WebSocket with wscat
npm install -g wscat
wscat -c ws://localhost:8002/ws/YOUR_SESSION_ID
> {"message": "What are your hours?"}
```

### Test in Production

```bash
curl -X POST http://your-azure-vm:8002/api/create-session
```

---

## 📊 Monitoring

### Check Active Sessions

```bash
curl http://your-azure-vm:8002/health
```

### View Logs

```bash
docker-compose logs -f chat-service
```

---

## 🆘 Troubleshooting

### Issue: "Session not found"
**Solution**: Create a session before connecting to WebSocket

### Issue: WebSocket connection fails
**Solution**: Check firewall rules on Azure VM (port 8002 must be open)

### Issue: CORS errors
**Solution**: Update `allow_origins` in `chat_service.py`

### Issue: Messages not streaming
**Solution**: Ensure your client handles "chunk" type messages

---

## 📞 Support

For issues or questions, check logs:
```bash
docker-compose logs -f chat-service
```

---

**Ready to integrate!** 🚀

Your chat service will be available at:
- **REST API**: `http://your-azure-vm:8002/api/*`
- **WebSocket**: `ws://your-azure-vm:8002/ws/{session_id}`
- **Health**: `http://your-azure-vm:8002/health`
