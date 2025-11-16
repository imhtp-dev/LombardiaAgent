# Agent Routing System - Implementation Summary

## ✅ Implementation Complete

This document summarizes the unified agent routing system that routes calls between the **Booking Agent** and **Info Agent** based on user intent.

---

## 🎯 What Was Implemented

### 1. **Unified Router Node** ✅
**File**: `flows/nodes/router.py`

- **Purpose**: Initial greeting node that detects user intent
- **Functions**:
  - `route_to_booking`: Routes to booking agent when user wants to book
  - `route_to_info`: Routes to info agent when user has questions
- **Behavior**: Greets user with "Ciao, sono Ualà..." and listens for intent

### 2. **Agent Routing Handlers** ✅
**File**: `flows/handlers/agent_routing_handlers.py`

Four main routing handlers:
- `route_to_booking_handler`: Initial routing from router → booking
- `route_to_info_handler`: Initial routing from router → info
- `transfer_from_info_to_booking_handler`: Info → Booking transfer (ANYTIME)
- `transfer_from_booking_to_info_handler`: Booking → Info transfer (ONLY after completion)

### 3. **Info Agent Booking Transfer** ✅
**Files Modified**:
- `info_agent/flows/nodes/greeting.py`
- `info_agent/flows/handlers/transfer_handlers.py`

**Changes**:
- Added `transfer_to_booking_agent` function (always available)
- Split human transfer into separate function: `request_transfer_to_human`
- Info agent can now route to booking agent ANYTIME

### 4. **Booking Completion Info Transfer** ✅
**File Modified**: `flows/nodes/completion.py`

**Changes**:
- Added `ask_info_question` function to completion node
- Sets `booking_completed = True` flag
- Allows info questions ONLY after booking is complete
- Uses `transfer_from_booking_to_info_handler`

### 5. **Flow Manager Router Support** ✅
**File Modified**: `flows/manager.py`

**Changes**:
- Changed default start node from `"greeting"` to `"router"`
- Added router node initialization logic
- Maintains backward compatibility with direct node starts

### 6. **Entry Point Updates** ✅
**Files Modified**:
- `bot.py` - Default start_node changed to `"router"`
- `test.py` - Default start_node changed to `"router"`
- `chat_test.py` - Default global_start_node changed to `"router"`

---

## 🔄 Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Incoming Call (Talkdesk)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Router Node (bot.py - Default)                  │
│  "Ciao, sono Ualà. Come posso aiutarti oggi?"              │
│                                                               │
│  Functions:                                                   │
│  • route_to_booking (user wants to book)                     │
│  • route_to_info (user has questions)                        │
└───────────────────┬───────────────────┬─────────────────────┘
                    │                   │
        ┌───────────┘                   └───────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────────┐               ┌──────────────────────┐
│   INFO AGENT FLOW     │               │  BOOKING AGENT FLOW  │
│   🟠 Stateless        │               │  🟢 Stateful         │
├───────────────────────┤               ├──────────────────────┤
│ • Answer questions    │               │ 1. Search service    │
│ • Provide pricing     │               │ 2. Select center     │
│ • Clinic info         │               │ 3. Patient details   │
│ • Exam requirements   │               │ 4. Date/time         │
│                       │               │ 5. Confirm booking   │
│ Functions:            │               │                      │
│ ✓ transfer_to_booking │               │ 🔒 NO TRANSFERS     │
│   (ANYTIME)           │               │    DURING BOOKING    │
│ ✓ transfer_to_human   │               │                      │
└───────┬───────────────┘               └──────────┬───────────┘
        │                                          │
        │ User wants                               │ Booking
        │ to book                                  │ complete
        │                                          │
        └────────────────┐         ┌──────────────┘
                         │         │
                         ▼         ▼
            ┌────────────────────────────┐
            │  Completion Node           │
            │  ✅ Booking confirmed      │
            │                            │
            │  Functions:                │
            │  • ask_info_question       │
            │    (NOW AVAILABLE)         │
            │  • manage_booking          │
            │  • start_new_booking       │
            └────────────────────────────┘
```

---

## 📊 State Management

### Flow Manager State Variables

| State Variable | Purpose | Set By |
|---------------|---------|---------|
| `current_agent` | Track active agent ("router", "booking", "info") | Routing handlers |
| `booking_in_progress` | Protect booking flow from interruptions | Booking flow nodes |
| `booking_completed` | Allow info transfers after booking | Completion node |
| `can_transfer_to_info` | Flag for info transfer availability | Routing handlers |
| `can_transfer_to_booking` | Flag for booking transfer availability | Routing handlers |
| `came_from_agent` | Track routing history | Routing handlers |
| `initial_booking_request` | Store user's initial booking request | Router |
| `post_booking_question` | Store user's post-booking question | Completion |

---

## 🎛️ Transfer Rules

### ✅ Allowed Transfers

| From | To | When | Function |
|------|----|----|----------|
| Router | Booking | User wants to book | `route_to_booking` |
| Router | Info | User has questions | `route_to_info` |
| Info | Booking | **ANYTIME** | `transfer_to_booking_agent` |
| Booking | Info | **ONLY after completion** | `ask_info_question` |

### 🚫 Blocked Transfers

| From | To | When | Reason |
|------|----|----|---------|
| Booking | Info | During steps 1-5 | Protect booking integrity |

---

## 🧪 Testing Guide

### Test Scenarios

#### 1. **Initial Routing - Booking Intent**
```bash
python test.py
# User says: "Vorrei prenotare una visita"
# Expected: Routes to booking agent
```

#### 2. **Initial Routing - Info Intent**
```bash
python test.py
# User says: "Quanto costa un esame del sangue?"
# Expected: Routes to info agent
```

#### 3. **Info → Booking Transfer**
```bash
python test.py
# 1. User asks info question
# 2. Info agent responds
# 3. User says: "Vorrei prenotare"
# Expected: Transfers to booking agent ANYTIME
```

#### 4. **Booking → Info Transfer (Blocked)**
```bash
python test.py --start-node booking
# 1. During booking flow (e.g., entering patient details)
# 2. User asks: "Che ore siete aperti?"
# Expected: NO transfer function available (blocked)
```

#### 5. **Booking → Info Transfer (After Completion)**
```bash
python test.py --start-node booking
# 1. Complete full booking flow
# 2. Booking confirmed
# 3. User asks: "Quali documenti devo portare?"
# Expected: Transfers to info agent successfully
```

### Testing with Different Start Nodes

```bash
# Default: Unified router
python test.py

# Direct to booking agent (skip router)
python test.py --start-node greeting

# Direct to info agent (testing only)
# Note: Need to manually route to info agent via router

# Fast text testing
python chat_test.py
```

---

## 📁 Files Created/Modified

### ✨ New Files
1. `flows/nodes/router.py` - Unified router node
2. `flows/handlers/agent_routing_handlers.py` - Routing logic
3. `agent_routing_flow.svg` - Visual SVG diagram
4. `agent_routing_flow.md` - Mermaid diagrams and documentation
5. `AGENT_ROUTING_IMPLEMENTATION.md` - This file

### 📝 Modified Files
1. `info_agent/flows/nodes/greeting.py` - Added booking transfer
2. `info_agent/flows/handlers/transfer_handlers.py` - Booking transfer handler
3. `flows/nodes/completion.py` - Added info transfer function
4. `flows/manager.py` - Router initialization support
5. `bot.py` - Default to router
6. `test.py` - Default to router
7. `chat_test.py` - Default to router

---

## 🚀 Deployment Steps

### 1. **Local Testing**
```bash
# Test with text interface (fastest)
python chat_test.py

# Test with voice (Daily rooms)
python test.py

# Test specific scenarios
python test.py --start-node booking
python test.py --start-node greeting
```

### 2. **Verify State Management**
Check logs for:
- ✅ State transitions logged correctly
- ✅ Transfer blocks working during booking
- ✅ Transfer allows after completion

### 3. **Production Deployment**
```bash
# Build Docker image
docker build -t rudyimhtpdev/voicebooking_piemo1:latest .

# Push to registry
docker push rudyimhtpdev/voicebooking_piemo1:latest

# On Azure VM
docker-compose pull
docker-compose up -d
docker image prune -f
```

### 4. **Verify Production**
```bash
# Check container is running
docker-compose ps

# Check logs
docker-compose logs --tail=100 pipecat-agent

# Test health endpoint
curl http://localhost:8000/health
```

---

## 🔧 Configuration

### WebSocket Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `start_node` | `router` | Starting node (router, greeting, booking, etc.) |
| `session_id` | auto-generated | Unique session identifier |
| `caller_phone` | empty | Caller phone from Talkdesk |
| `business_status` | `open` | Business status |

**Example**:
```
ws://localhost:8000/ws?start_node=router&caller_phone=+393491234567
```

---

## 🐛 Troubleshooting

### Issue: Router not responding
**Solution**: Check logs for router node initialization
```bash
docker-compose logs -f pipecat-agent | grep "router"
```

### Issue: Transfers not working
**Solution**: Check state management in logs
```bash
# Should see:
# ✅ current_agent = "info"
# ✅ can_transfer_to_booking = True
```

### Issue: Info transfer during booking not blocked
**Solution**: Verify `booking_in_progress` flag is set
```bash
# Should see:
# 🔒 booking_in_progress = True
# ❌ can_transfer_to_info = False
```

---

## 📚 Key Design Decisions

### 1. **Why Unified Entry Point?**
- Single WebSocket endpoint for Talkdesk
- Shared AI services (STT, TTS, LLM)
- Easier state management
- Better conversation continuity

### 2. **Why Block Transfers During Booking?**
- Prevents incomplete bookings
- Ensures data integrity
- User must complete or abandon booking
- Reduces confusion

### 3. **Why Allow Info Transfers Anytime?**
- Info queries are stateless
- Natural conversation flow
- User may decide to book after getting info
- No data integrity issues

### 4. **Why Post-Booking Info Available?**
- User may have follow-up questions
- Better user experience
- Natural end to conversation
- Reduces need for human transfer

---

## 🎓 Next Steps

### Recommended Enhancements
1. **Analytics**: Track routing patterns and transfer frequencies
2. **A/B Testing**: Test different router prompts
3. **Fallback Handling**: Improve error handling for failed transfers
4. **Context Preservation**: Enhance state passing between agents
5. **Multi-language**: Extend to English and other languages

### Future Features
1. **Intent Classification Model**: ML-based intent detection
2. **Smart Routing**: Based on time of day, queue length, etc.
3. **Agent Specialization**: More specialized agents (billing, emergencies, etc.)
4. **Warm Transfers**: Pass conversation summary to human operators

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs -f pipecat-agent`
2. Review state management in flow_manager.state
3. Test with chat_test.py for faster debugging
4. Verify all handlers return (result, NodeConfig) tuples

---

**Implementation Date**: 2025-01-12
**Version**: 1.0.0
**Status**: ✅ Complete and Ready for Testing
