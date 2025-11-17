# Unified Agent Integration - Changes Summary

**Date:** 2025-01-17
**Status:** ✅ Completed - Ready for Testing

---

## 🎯 What Was Changed

### **CHANGE 1: Info Agent Booking Transfer Function**

**File:** `info_agent/flows/nodes/greeting.py`

**Added:**
1. **Import statement** (line 32):
   ```python
   from flows.handlers.agent_routing_handlers import transfer_from_info_to_booking_handler
   ```

2. **New function in task_messages** (line 70):
   ```
   - transfer_to_booking_agent: Transfer to booking agent when user wants to book appointment
   ```

3. **New TOOL 7: Transfer to Booking Agent** (lines 185-199):
   ```python
   FlowsFunctionSchema(
       name="transfer_to_booking_agent",
       handler=transfer_from_info_to_booking_handler,
       description="Transfer to booking agent when user wants to book an appointment or medical service...",
       properties={
           "user_request": {
               "type": "string",
               "description": "What the user wants to book (e.g., 'blood test', 'cardiology visit', 'X-ray')"
           }
       },
       required=["user_request"]
   )
   ```

4. **Updated TOOL 8 description** (line 207):
   - Changed from TOOL 7 to TOOL 8
   - Updated description to clarify: "For booking appointments, use transfer_to_booking_agent instead"

**What this means:**
- ✅ Users can now say "I want to book" while in info agent
- ✅ LLM will automatically call `transfer_to_booking_agent` function
- ✅ User gets seamlessly transferred to booking flow
- ✅ No more dead-end when users want to book after getting information

---

### **CHANGE 2: Docker Compose Cleanup**

**File:** `docker-compose.yml`

**Removed:**
1. **Separate `info-agent` container** (lines 143-175) - DELETED ❌
   - Was running on port 8081
   - Had separate command to run `info_agent.main:app`
   - No longer needed - info agent is now integrated into main agent

2. **`dashboard-frontend` container** (lines 177-206) - DELETED ❌
   - Next.js frontend on port 8082
   - Will be moved to separate repository (as per your request)

**Kept:**
- ✅ `nginx-lb` - Load balancer (port 8000)
- ✅ `pipecat-agent-1` - Unified agent instance 1
- ✅ `pipecat-agent-2` - Unified agent instance 2
- ✅ `pipecat-agent-3` - Unified agent instance 3

**What this means:**
- ✅ Only ONE agent image (`rudyimhtpdev/voicebooking_piemo1:latest`)
- ✅ All 3 instances run the unified agent (booking + info)
- ✅ Clean, simple deployment structure
- ✅ No port conflicts

---

### **CHANGE 3: Dockerfile Analysis - NO CHANGES NEEDED**

**File:** `Dockerfile` (main one in root directory)

**Confirmed:**
- ✅ Line 58: `COPY info_agent/ ./info_agent/` - Already includes info_agent folder
- ✅ Line 76: `CMD ["python", "-m", "uvicorn", "bot:app", ...]` - Correct entry point
- ✅ Port 8000 - Correct
- ✅ All dependencies installed (gcc, ffmpeg, NLTK, PyTorch, etc.)

**Files to DELETE (no longer needed):**
- `info_agent/Dockerfile.dev` - Was only for isolated info agent testing
- `info_agent/docker-compose.dev.yml` - Was only for local dev
- `Dockerfile.frontend` - Dashboard goes to separate repo

---

## 🔄 How Agent Routing Now Works

### **Complete Flow:**

```
📞 Incoming Call (Talkdesk)
    ↓
🌐 Nginx Load Balancer (port 8000)
    ↓
🤖 Unified Agent (pipecat-agent-1/2/3)
    ↓
🎯 Router Node: "Ciao, sono Ualà. Come posso aiutarti?"
    ↓
    ├─→ User says: "Quanto costa?"
    │   → route_to_info → INFO AGENT FLOW
    │   → User can ask questions
    │   → User says: "Vorrei prenotare"
    │   → transfer_to_booking_agent (NEW!) ✅
    │   → BOOKING AGENT FLOW
    │
    └─→ User says: "Vorrei prenotare una visita"
        → route_to_booking → BOOKING AGENT FLOW
        → Complete booking (5 steps)
        → Booking confirmed ✅
        → User says: "Che documenti devo portare?"
        → ask_info_question → INFO AGENT FLOW
        → Info agent answers
        → Call ends 👋
```

---

## 📋 Testing Checklist

### **Before Deployment - Test Locally:**

1. **Test Info → Booking Transfer (CRITICAL NEW FEATURE):**
   ```bash
   python chat_test.py
   ```
   - Say: "What are your opening hours?" (goes to info agent)
   - Say: "I want to book a blood test" (should transfer to booking agent)
   - ✅ Expected: Transfer works, booking flow starts

2. **Test Router → Info:**
   ```bash
   python chat_test.py
   ```
   - Say: "How much does a cardiology visit cost?"
   - ✅ Expected: Routes to info agent, answers question

3. **Test Router → Booking:**
   ```bash
   python chat_test.py
   ```
   - Say: "I need to book an X-ray"
   - ✅ Expected: Routes directly to booking agent

4. **Test Booking → Info (After Completion):**
   ```bash
   python chat_test.py --start-node booking
   ```
   - Complete a full booking flow
   - After confirmation, say: "What documents do I need?"
   - ✅ Expected: Transfers to info agent, answers question

---

## 🚀 Deployment Instructions

### **Step 1: Local Testing**
```bash
# Test with text chat (fastest)
python chat_test.py

# Test with voice (Daily rooms)
python test.py
```

### **Step 2: Build & Push Docker Image**
```bash
# Build the unified agent image
docker build -t rudyimhtpdev/voicebooking_piemo1:latest .

# Push to Docker registry
docker push rudyimhtpdev/voicebooking_piemo1:latest
```

### **Step 3: Deploy to Azure VM**
```bash
# SSH into Azure VM
ssh -i voilavoicebookingvm_key.pem azureuser@<your-vm-ip>

# Navigate to project directory
cd /path/to/project

# Pull latest image
docker-compose pull

# Stop old containers
docker-compose down

# Start unified agent
docker-compose up -d

# Verify all 3 agents are running
docker-compose ps

# Check logs
docker-compose logs -f pipecat-agent-1
docker-compose logs -f pipecat-agent-2
docker-compose logs -f pipecat-agent-3

# Cleanup old images
docker image prune -f
```

### **Step 4: Verify Deployment**
```bash
# Health check
curl http://localhost:8000/health

# Check Nginx
curl http://localhost:8000/

# View logs
docker-compose logs --tail=100 pipecat-agent-1
```

---

## 🗂️ Files to Clean Up (Optional)

**Can be deleted after testing (no longer needed):**
- `info_agent/Dockerfile.dev`
- `info_agent/docker-compose.dev.yml`
- `info_agent/chat_test.py` (duplicate of main chat_test.py)
- `info_agent/test_*.py` (old test files)
- `Dockerfile.frontend` (dashboard goes to separate repo)
- `info_frontend/` folder (dashboard goes to separate repo)

**Keep for now:**
- `talkdeskbridge/` folder (you'll move to separate repo later)
- `info_agent/main.py` (if it's used for dashboard API)

---

## 📞 Talkdesk Bridge - Separate Repository Plan

**When you're ready to separate the bridge:**

1. Create new repository: `talkdesk-bridge`
2. Move `talkdeskbridge/bridge_conn.py` there
3. Deploy separately (different Docker container)
4. Update Talkdesk webhook to point to bridge
5. Bridge forwards to unified agent at port 8000

---

## ✅ Summary of Benefits

**Before (Separate Containers):**
- ❌ 3 booking agents + 1 info agent = 4 containers
- ❌ Users couldn't transfer from info to booking
- ❌ Confusing deployment structure
- ❌ Port conflicts (8000, 8081)

**After (Unified Agent):**
- ✅ 3 unified agents (booking + info) = 3 containers
- ✅ Seamless info ↔ booking transfers
- ✅ Clean, simple deployment
- ✅ Single port (8000)
- ✅ Better resource utilization
- ✅ Easier maintenance

---

## 🐛 Troubleshooting

### Issue: Transfer from info to booking not working
**Solution:** Check logs for import errors:
```bash
docker-compose logs -f pipecat-agent-1 | grep transfer
```

### Issue: Bot doesn't respond after transfer
**Solution:** Verify handler returns NodeConfig:
```bash
# Check that transfer_from_info_to_booking_handler exists
docker exec pipecat-agent-1 python -c "from flows.handlers.agent_routing_handlers import transfer_from_info_to_booking_handler; print('✅ Import OK')"
```

### Issue: Container not starting
**Solution:** Check environment variables:
```bash
docker-compose config
docker-compose logs pipecat-agent-1
```

---

**Implementation Date:** 2025-01-17
**Status:** ✅ Ready for Testing & Deployment
**Next Steps:** Test locally → Build image → Deploy to Azure
