# Agent Viz Interface Control Document (ICD)

**Version:** 0.1  
**Date:** 2026-04-01  
**Status:** Draft

---

## 1. Overview

This document defines the interface between the immersive agent visualization frontend (Unity/Web) and the AI agent backend(s). The goal is an AI-agnostic visualization layer that can connect to OpenClaw, Claude, Codex, or other agentic systems.

```
┌─────────────────────────────────────────────────────────┐
│                    Unity / Web 3D                       │
│                                                         │
│   Agents as geometric shapes with thought bubbles        │
│   Voice + mouse/kbd interaction                         │
│   VR + desktop support                                  │
└───────────────────────┬─────────────────────────────────┘
                        │ WebSocket
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Bridge API                            │
│                                                         │
│   Normalizes events across AI providers                 │
│   Maintains agent registry                             │
│   Handles command routing                              │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│    OpenClaw     │         │  Claude/Codex   │
│    (now)        │         │  (future)       │
└─────────────────┘         └─────────────────┘
```

---

## 2. Design Principles

### 2.1 Visual Design
- **Agent shapes:** Abstract / robot-like, NOT humanoid
- **Color palette:** Distinct per role, tasteful — not garish
- **Role distinction:** Visually clear who does what
- **States:** Idle, thinking, working, complete, error

### 2.2 Agent Types
| Type | Behavior |
|------|----------|
| **Permanent** | Always visible, core roles (e.g., main assistant, coder, researcher) |
| **Ephemeral** | Spawned on demand, fade when task complete, temporary workers |

### 2.3 Interaction Modes
- **VR:** Voice commands (primary), hand/gaze tracking
- **Desktop:** Keyboard/mouse (primary), voice as fallback

---

## 3. Architecture

### 3.1 Components

| Component | Responsibility | Tech |
|-----------|---------------|------|
| Frontend | 3D visualization, user interaction | Unity or Three.js (web) |
| Bridge API | Event normalization, agent registry, command routing | Python asyncio |
| OpenClaw Adapter | Connects Bridge to OpenClaw sessions/cron | Python |
| Claude/Codex Adapter | (Future) Connects Bridge to Claude/Codex | TBD |

### 3.2 Data Flow

1. **Agent events flow forward:**
   ```
   OpenClaw → OpenClaw Adapter → Bridge API → WebSocket → Unity/Web
   ```

2. **Commands flow backward:**
   ```
   Unity/Web → WebSocket → Bridge API → Adapter → AI Backend
   ```

---

## 4. WebSocket API

**Endpoint:** `ws://host:port`  
**Default port:** 8765

### 4.1 Client → Server Messages

#### `init` (Server → Client)
Sent to new client upon connection. Contains current state of all agents.

```json
{
  "type": "init",
  "data": {
    "agents": [ /* array of Agent objects */ ]
  }
}
```

#### `agent_event` (Server → Client)
Broadcast whenever an agent spawns, updates, completes, or errors.

```json
{
  "type": "agent_event",
  "data": {
    "event_type": "agent_spawned | agent_updated | agent_complete | agent_error",
    "timestamp": "2026-04-01T12:00:00Z",
    "agent": { /* Agent object */ },
    "details": "optional string"
  }
}
```

#### `command_ack` (Server → Client)
Acknowledges a command was received.

```json
{
  "type": "command_ack",
  "data": {
    "command": "spawn | message | cancel | ...",
    "target": "agent_id or null",
    "status": "received | executing | complete | error",
    "result": "optional result data"
  }
}
```

#### `pong` (Server → Client)
Response to client ping.

```json
{
  "type": "pong"
}
```

### 4.2 Client → Server Messages

#### `ping`
Keepalive.

```json
{ "type": "ping" }
```

#### `command`
Send a command to an agent or the system.

```json
{
  "type": "command",
  "command": "spawn | message | cancel | query",
  "target": "agent_id or null",
  "payload": {
    "message": "optional text",
    "agent_type": "ephemeral",
    "role": "optional role hint"
  }
}
```

#### `subscribe_agent`
Subscribe to detailed updates for a specific agent.

```json
{
  "type": "subscribe_agent",
  "agent_id": "agent-id"
}
```

---

## 5. Agent Schema

### 5.1 Agent Object

```json
{
  "id": "string (unique identifier)",
  "name": "string (display name, e.g., 'Bit', 'Coder')",
  "role": "string (e.g., 'assistant', 'coding', 'research')",
  "agent_type": "permanent | ephemeral",
  "status": "idle | thinking | working | complete | error",
  "color": "string (hex color, e.g., '#4A90D9')",
  "shape": "string (sphere | octahedron | icosahedron | tetrahedron | dodecahedron)",
  "current_task": "string or null",
  "message_preview": "string or null (truncated output/response)",
  "last_activity": "ISO timestamp or null",
  "created_at": "ISO timestamp",
  
  // Optional fields
  "tokens_used": "number (directionally relevant, not precise)",
  "provider": "string (e.g., 'openclaw', 'claude', 'codex')",
  "model": "string (model identifier)",
  "metadata": "object (provider-specific data)"
}
```

### 5.2 Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique across all agents |
| `name` | Yes | Human-readable name |
| `role` | Yes | Functional role |
| `agent_type` | Yes | permanent or ephemeral |
| `status` | Yes | Current state |
| `color` | Yes | Hex color for visualization |
| `shape` | Yes | Geometric shape identifier |
| `current_task` | No | What the agent is currently doing |
| `message_preview` | No | Truncated preview of output/thought |
| `last_activity` | No | Last meaningful action timestamp |
| `created_at` | Yes | When agent was spawned |
| `tokens_used` | No | Directional token consumption (optional, lightweight) |
| `provider` | No | Which backend (openclaw, claude, codex) |
| `model` | No | Model identifier |
| `metadata` | No | Provider-specific extra data |

### 5.3 Shape → Role Mapping

| Shape | Suggested Role |
|-------|---------------|
| `sphere` | General assistant, main agent |
| `octahedron` | Coding tasks |
| `icosahedron` | Research, search |
| `tetrahedron` | Alerts, notifications |
| `dodecahedron` | File operations, documents |

---

## 6. Commands

### 6.1 Supported Commands

| Command | Description | Payload |
|---------|-------------|---------|
| `spawn` | Create a new ephemeral agent | `{ agent_type, role, message }` |
| `message` | Send message to an agent | `{ target, message }` |
| `cancel` | Cancel an agent's current task | `{ target }` |
| `query` | Query agent state | `{ target }` |
| `list` | List all agents | none |
| `reset` | Reset/clear all ephemeral agents | none |

### 6.2 Command Response

Commands receive an acknowledgment immediately upon receipt, then a final response when complete.

---

## 7. Metrics

### 7.1 Required Metrics (Lightweight)

| Metric | Description | Implementation |
|--------|-------------|----------------|
| `session_duration` | How long frontend is connected | Bridge tracks WebSocket connections |
| `event_count` | Number of events broadcast | Counter in Bridge API |
| `command_count` | Commands received from client | Counter in Bridge API |
| `active_agents` | Gauge of current agent count | Updated on spawn/complete |

### 7.2 Agent Metrics (Lightweight)

| Metric | Description | Implementation |
|--------|-------------|----------------|
| `lifespan` | Ephemeral agent lifetime | timestamps in agent object |
| `token_direction` | Directional token usage | Optional field, cheap to track |

### 7.3 Optional Metrics (When Needed)

| Metric | Description |
|--------|-------------|
| Bridge latency | Event → UI delay |
| Token consumption per agent | Optional, only when cost-tracking needed |
| Error frequency by agent | Error events per agent |

---

## 8. OpenClaw Adapter

### 8.1 Integration Points

OpenClaw provides:
- `sessions_send()` — Send message to a session/sub-agent
- `sessions_spawn()` — Spawn isolated sub-agent
- `subagents()` — List/steer/kill sub-agents
- `cron` — Scheduled job execution

### 8.2 Event Capture Strategy

OpenClaw doesn't have native event streaming. Options:

| Approach | Pros | Cons |
|----------|------|------|
| **Polling** (simple) | Easy to implement | Delay, overhead |
| **Main session relay** (recommended) | Real-time, no polling | Uses main session context |
| **OpenClaw plugin** (complex) | Native | Requires OpenClaw changes |

**Recommended:** Main session relay — the main agent session receives events from sub-agents and relays them to the Bridge via a WebSocket client.

### 8.3 Adapter Interface

```python
class OpenClawAdapter:
    def __init__(self, bridge_ws_url: str):
        """Connect bridge WebSocket client to OpenClaw"""
        pass
    
    async def spawn_agent(self, role: str) -> str:
        """Spawn ephemeral agent, return agent_id"""
        pass
    
    async def send_message(self, agent_id: str, message: str):
        """Send message to agent"""
        pass
    
    async def cancel_agent(self, agent_id: str):
        """Cancel agent task"""
        pass
    
    async def relay_events(self):
        """Relay OpenClaw events to bridge"""
        pass
```

---

## 9. Unity/Web Frontend Notes

### 9.1 Web Prototype (Current)

- Built with Three.js for quick iteration
- Not VR-capable (requires Unity for true VR)
- Serves as reference implementation

### 9.2 Unity Requirements

- WebSocket client library (e.g., Native WebSocket or UnityWebSocket)
- XR interaction toolkit for VR support
- 3D UI system for thought bubbles

### 9.3 Visual States

| Status | Visual Indication |
|--------|-------------------|
| `idle` | Subtle glow, slow float |
| `thinking` | Faster pulse, brighter glow |
| `working` | Bright glow, active rotation |
| `complete` | Fade out (ephemeral) / return to idle (permanent) |
| `error` | Red tint, shake animation |

---

## 10. Future Backends

### 10.1 Claude Adapter (Future)

Requires:
- Anthropic API access
- Session/conversation management
- Claude's tool use events mapped to agent events

### 10.2 Codex Adapter (Future)

Requires:
- OpenAI Codex API access
- Task orchestration logic

### 10.3 Portability Checklist

- [ ] All provider-specific logic isolated in adapters
- [ ] Agent schema is provider-agnostic
- [ ] Bridge API is stateless (except registry)
- [ ] Frontend never calls provider APIs directly

---

## 11. Open Questions

- [ ] Voice input: Continuous transcription or push-to-talk?
- [ ] Deployment: Local only, or remote access for VR headset?
- [ ] Unity timeline: When to bring in Unity help?

---

## 12. File Structure

```
agent-viz/
├── bridge_api.py          # WebSocket server, agent registry
├── adapters/
│   └── openclaw_adapter.py # OpenClaw integration
├── frontend/
│   ├── index.html         # Web/Three.js prototype
│   └── (unity project)    # Future Unity build
├── SPEC.md                # This document
└── README.md              # Setup instructions
```

---

## Appendix A: Example Session

```
1. User launches Unity/Web frontend
2. Frontend connects to Bridge API (ws://localhost:8765)
3. Bridge sends "init" with current agents:
   { agents: [
     { id: "bit", name: "Bit", role: "assistant", agent_type: "permanent", ... },
     { id: "coder", name: "Coder", role: "coding", agent_type: "permanent", ... },
     { id: "researcher", name: "Researcher", role: "research", agent_type: "permanent", ... }
   ]}
4. User clicks "Coder" agent → thought bubble shows "Ready"
5. User sends command: { type: "command", command: "message", target: "coder", payload: { message: "Write a hello world in Python" } }
6. Bridge relays to OpenClaw → Coder agent starts working
7. OpenClaw adapter detects status change → Bridge broadcasts:
   { type: "agent_event", data: { event_type: "agent_updated", agent: { id: "coder-123", parent: "coder", status: "working", current_task: "Writing Python file..." } } }
8. Frontend updates Coder shape to "working" visual state
9. Task complete → Bridge broadcasts "agent_complete"
10. Frontend updates visuals, shows output in thought bubble
```

---

*Last updated: 2026-04-01*
