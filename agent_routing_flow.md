# Unified Agent Routing Flow - Step by Step

## Complete Flow Diagram

```mermaid
flowchart TD
    Start([📞 Incoming Call from Talkdesk]) --> Router

    Router[🎯 Initial Router Node<br/>Greeting: Hello, I'm Ualà<br/>How can I help you today?]

    Router -->|User mentions<br/>booking/appointment| BookingFlow
    Router -->|User asks<br/>info question| InfoFlow

    %% INFO AGENT FLOW
    subgraph InfoAgent[" 🟠 INFO AGENT FLOW "]
        InfoFlow[📋 Info Agent Greeting<br/>Functions available:<br/>- query_knowledge_base<br/>- get_pricing<br/>- get_exams<br/>- get_clinic_info<br/>- transfer_to_booking_agent ⚡]

        InfoFlow --> InfoAnswer[💬 Answer Info Questions<br/>Knowledge base, pricing,<br/>exams, clinic hours]

        InfoAnswer --> InfoDecision{User wants to?}

        InfoDecision -->|Book appointment| TransferToBooking[✅ Transfer to Booking Agent<br/>Available ANYTIME ⚡]
        InfoDecision -->|More questions| InfoAnswer
        InfoDecision -->|Talk to human| TransferToHuman[👤 Transfer to Human Operator]

        TransferToBooking -.->|Route call| BookingFlow
    end

    %% BOOKING AGENT FLOW
    subgraph BookingAgent[" 🟢 BOOKING AGENT FLOW "]
        BookingFlow[🏥 Start Booking Flow<br/>🔒 NO TRANSFER during booking]

        BookingFlow --> Step1[1️⃣ Search Health Service<br/>User describes service needed]
        Step1 --> Step2[2️⃣ Select Health Center<br/>Choose location]
        Step2 --> Step3[3️⃣ Collect Patient Details<br/>Name, phone, DOB, fiscal code]
        Step3 --> Step4[4️⃣ Select Date/Time<br/>Choose appointment slot]
        Step4 --> Step5[5️⃣ Confirm Booking<br/>Review all details]

        Step5 --> Completion[✅ Booking Completion Node<br/>Your booking is confirmed!<br/>New function available:<br/>ask_info_question ⚡]

        Completion --> PostBookingDecision{User wants to?}

        PostBookingDecision -->|Ask info question| TransferToInfo[📋 Transfer to Info Agent<br/>Only AFTER completion]
        PostBookingDecision -->|End call| EndCall[👋 End Call - Goodbye]

        TransferToInfo -.->|Route call| InfoAnswer
    end

    TransferToHuman --> HumanEnd([🎧 Human Operator Takes Over])
    EndCall --> CallEnd([📴 Call Ends])

    style Router fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style InfoFlow fill:#FFE082,stroke:#F57C00,stroke-width:2px
    style InfoAnswer fill:#FFCC80,stroke:#F57C00,stroke-width:2px
    style TransferToBooking fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style BookingFlow fill:#81C784,stroke:#2E7D32,stroke-width:2px,color:#fff
    style Step1 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style Step2 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style Step3 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style Step4 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style Step5 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style Completion fill:#66BB6A,stroke:#1B5E20,stroke-width:3px,color:#fff
    style TransferToInfo fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style InfoAgent fill:#FFF3E0,stroke:#FF9800,stroke-width:3px
    style BookingAgent fill:#E8F5E9,stroke:#4CAF50,stroke-width:3px
```

---

## Step-by-Step Explanation

### 🎬 **PHASE 1: Call Start & Initial Routing**

```mermaid
sequenceDiagram
    participant Caller
    participant Router as Initial Router Node
    participant System

    Caller->>Router: 📞 Call connects
    Router->>Caller: 🎤 "Hello, I'm Ualà. How can I help you today?"
    Caller->>Router: 💬 User responds
    Router->>System: 🤔 Analyze intent (booking vs info)

    alt User wants booking
        System->>Router: Route to Booking Agent
        Note over Router: Goes to BOOKING FLOW
    else User wants info
        System->>Router: Route to Info Agent
        Note over Router: Goes to INFO FLOW
    end
```

**Example Scenarios:**
- User says: *"I need to book an X-ray"* → **Booking Flow**
- User says: *"What are your opening hours?"* → **Info Flow**
- User says: *"How much does a blood test cost?"* → **Info Flow**

---

### 🟠 **PHASE 2: Info Agent Flow** (Stateless - Can Transfer Anytime)

```mermaid
flowchart TD
    A[📋 Info Agent Activated] --> B[💬 User asks question]
    B --> C{What type of question?}

    C -->|Pricing| D[💰 Get pricing info]
    C -->|Exams| E[🔬 Get exam requirements]
    C -->|Clinic hours| F[🏥 Get clinic info]
    C -->|General question| G[📚 Query knowledge base]

    D --> H[🎤 Agent responds with answer]
    E --> H
    F --> H
    G --> H

    H --> I{User wants to?}

    I -->|Book appointment| J[✅ Transfer to Booking Agent<br/>⚡ Available ANYTIME]
    I -->|Ask more| B
    I -->|Talk to human| K[👤 Transfer to Human]

    J -.->|Routes to| L[🟢 Booking Agent Flow]

    style A fill:#FFE082,stroke:#F57C00,stroke-width:2px
    style H fill:#FFCC80,stroke:#F57C00,stroke-width:2px
    style J fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style L fill:#81C784,stroke:#2E7D32,stroke-width:2px,color:#fff
```

**Key Rule:**
> ✅ **Info agent can transfer to booking ANYTIME**
> Why? Info queries are stateless - no booking in progress to protect

**Example Conversation:**
```
Agent: "Hello, I'm Ualà. How can I help?"
User: "What are your opening hours?"
Agent: [Provides info] "We're open 8am-6pm. Anything else?"
User: "I'd like to book an appointment"
Agent: ✅ [Transfers to booking agent] "Great, let me help you book..."
```

---

### 🟢 **PHASE 3: Booking Agent Flow** (Protected - No Transfers)

```mermaid
flowchart TD
    Start[🏥 Booking Agent Activated] --> Lock[🔒 Set booking_in_progress = True<br/>Transfer functions DISABLED]

    Lock --> S1[1️⃣ STEP 1: Search Service<br/>User: I need ankle X-ray<br/>Agent: Searching...]

    S1 --> S2[2️⃣ STEP 2: Select Center<br/>Agent: Found 3 centers<br/>User: I'll take the first one]

    S2 --> S3[3️⃣ STEP 3: Patient Details<br/>Agent: What's your name?<br/>Agent: Phone number?<br/>Agent: Date of birth?]

    S3 --> S4[4️⃣ STEP 4: Date/Time Selection<br/>Agent: When would you like?<br/>User: Tomorrow at 2pm]

    S4 --> S5[5️⃣ STEP 5: Confirm Booking<br/>Agent: Let me confirm...<br/>Service: Ankle X-ray<br/>Center: Milan<br/>Date: Tomorrow 2pm<br/>Correct?]

    S5 --> Complete[✅ BOOKING COMPLETE<br/>Set booking_completed = True<br/>Transfer functions ENABLED]

    Complete --> Decision{User wants to?}

    Decision -->|Ask question| InfoTransfer[📋 Transfer to Info Agent<br/>⚡ NOW AVAILABLE]
    Decision -->|End call| End[👋 Goodbye]

    InfoTransfer -.->|Routes to| InfoAgent[🟠 Info Agent Flow]

    style Lock fill:#FFEB3B,stroke:#F57C00,stroke-width:3px
    style S1 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style S2 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style S3 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style S4 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style S5 fill:#A5D6A7,stroke:#2E7D32,stroke-width:2px
    style Complete fill:#66BB6A,stroke:#1B5E20,stroke-width:3px,color:#fff
    style InfoTransfer fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff
```

**Key Rules:**
> 🔒 **NO transfers during booking steps 1-5**
> Why? Must protect booking flow integrity - user must complete or abandon
>
> ✅ **Transfer to Info ONLY after booking complete**
> Why? User may have follow-up questions about their appointment

**Example Conversation:**
```
Agent: "Let me help you book an appointment"
[STEPS 1-5: Service → Center → Details → Date → Confirm]
Agent: "Your booking is confirmed!"
User: "What should I bring to the appointment?"
Agent: ✅ [Can now transfer to info] "Let me get that info for you..."
```

---

### 📊 **State Management Throughout the Flow**

```mermaid
stateDiagram-v2
    [*] --> Router: Call starts

    Router --> InfoAgent: User wants info
    Router --> BookingAgent: User wants booking

    state InfoAgent {
        [*] --> InfoActive
        InfoActive: current_agent = "info"
        InfoActive: booking_in_progress = False
        InfoActive: can_transfer = True ✅

        InfoActive --> TransferToBooking: User wants to book
    }

    TransferToBooking --> BookingAgent: Route call

    state BookingAgent {
        [*] --> BookingActive
        BookingActive: current_agent = "booking"
        BookingActive: booking_in_progress = True 🔒
        BookingActive: can_transfer = False ❌

        BookingActive --> BookingComplete: Steps 1-5 finished

        BookingComplete: booking_completed = True
        BookingComplete: booking_in_progress = False
        BookingComplete: can_transfer = True ✅

        BookingComplete --> TransferToInfo: User has question
        BookingComplete --> [*]: User ends call
    }

    TransferToInfo --> InfoAgent: Route call

    InfoAgent --> [*]: User ends call
```

---

## 🎯 **Key Rules Summary**

### ✅ **Info Agent Rules**
| Can Do | Cannot Do |
|--------|-----------|
| ✅ Answer questions anytime | ❌ Book appointments (transfers to booking) |
| ✅ Transfer to booking ANYTIME | |
| ✅ Transfer to human operator | |
| ✅ Handle multiple questions | |

### ✅ **Booking Agent Rules**
| Can Do | Cannot Do |
|--------|-----------|
| ✅ Complete booking (steps 1-5) | ❌ Transfer to info during booking (steps 1-5) |
| ✅ After completion: transfer to info | ❌ Interrupt booking flow |
| ✅ After completion: end call | |

---

## 🔄 **Transfer Scenarios**

### Scenario 1: Info → Booking (Always Allowed ✅)
```
User asks: "What's the price?"
→ Info Agent answers
→ User says: "I want to book"
→ ✅ Transfer immediately to Booking Agent
```

### Scenario 2: Booking → Info (Blocked during booking 🔒)
```
Booking Agent: "What's your phone number?"
User: "Wait, what are your hours?"
→ ❌ NO transfer (booking in progress)
→ Agent: "I can help with that after we finish booking"
```

### Scenario 3: Booking → Info (Allowed after completion ✅)
```
Booking Agent: "Your booking is confirmed!"
User: "What documents do I need?"
→ ✅ Transfer to Info Agent
→ Info Agent provides document info
```

---

## 🧪 **Testing Checklist**

- [ ] Initial routing detects booking intent correctly
- [ ] Initial routing detects info intent correctly
- [ ] Info agent can transfer to booking anytime
- [ ] Booking agent CANNOT transfer during steps 1-5
- [ ] Booking agent CAN transfer after completion
- [ ] State preservation works across transfers
- [ ] User can return to info agent from booking completion

---

## 📁 **Files to Create/Modify**

### New Files:
1. `flows/nodes/router.py` - Initial routing node
2. `flows/handlers/agent_routing_handlers.py` - Routing logic

### Modified Files:
1. `info_agent/flows/nodes/greeting.py` - Add booking transfer
2. `flows/nodes/completion.py` - Add info transfer
3. `bot.py` - Use router as entry point
4. `flows/manager.py` - Add router start node

