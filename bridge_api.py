"""
Agent Viz Bridge API
Connects OpenClaw to Unity/Web frontend via WebSocket

Handles:
- Subscribes to OpenClaw agent events
- Translates to Unity-friendly JSON format  
- Manages active agent registry
- Handles basic commands from Unity
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Set, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import websockets
from websockets.server import WebSocketServerProtocol
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentType(Enum):
    PERMANENT = "permanent"      # Core roles, always visible
    EPHEMERAL = "ephemeral"     # Temporary workers, fade when done


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Agent:
    id: str
    name: str
    role: str
    agent_type: AgentType
    status: AgentStatus
    color: str           # Hex color for visuals
    shape: str          # geometric shape name
    current_task: Optional[str] = None
    last_activity: Optional[str] = None
    message_preview: Optional[str] = None
    persona: Optional[str] = None
    expertise: Optional[list] = None


@dataclass  
class AgentEvent:
    event_type: str     # agent_spawned, agent_updated, agent_complete, agent_error
    timestamp: str
    agent: Agent
    details: Optional[str] = None


class AgentRegistry:
    """Tracks all active agents and their state"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.profiles = {}
        
    def load_profiles(self, profiles_path: str):
        """Load agent profiles from YAML file"""
        if os.path.exists(profiles_path):
            with open(profiles_path, 'r') as f:
                self.profiles = yaml.safe_load(f)
            logger.info(f"Loaded {len(self.profiles)} agent profiles")
        else:
            logger.warning(f"Profiles file not found: {profiles_path}")
    
    def register_from_profile(self, profile_key: str) -> Optional[Agent]:
        """Register an agent from a profile"""
        if profile_key not in self.profiles:
            return None
        
        p = self.profiles[profile_key]
        agent_type = AgentType(p.get('agent_type', 'permanent'))
        
        agent = Agent(
            id=p['id'] if 'id' in p else profile_key,
            name=p['name'],
            role=p['role'],
            agent_type=agent_type,
            status=AgentStatus.IDLE,
            color=p['color'],
            shape=p['shape'],
            persona=p.get('persona'),
            expertise=p.get('expertise', [])
        )
        self.agents[agent.id] = agent
        return agent
    
    def register(self, agent_id: str, name: str, role: str, agent_type: AgentType = AgentType.EPHEMERAL,
                 color: str = "#4A90D9", shape: str = "sphere") -> Agent:
        """Register a new agent"""
        agent = Agent(
            id=agent_id,
            name=name,
            role=role,
            agent_type=agent_type,
            status=AgentStatus.IDLE,
            color=color,
            shape=shape
        )
        self.agents[agent_id] = agent
        return agent
    
    def update(self, agent_id: str, **kwargs) -> Optional[Agent]:
        if agent_id not in self.agents:
            return None
        agent = self.agents[agent_id]
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        return agent
    
    def get(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)
    
    def list_all(self) -> list:
        return list(self.agents.values())
    
    def remove(self, agent_id: str) -> bool:
        return self.agents.pop(agent_id, None) is not None


class BridgeAPI:
    """Main bridge - manages WebSocket connections and OpenClaw integration"""
    
    def __init__(self, port: int = 8765, profiles_dir: str = None):
        self.port = port
        self.registry = AgentRegistry()
        self.clients: Set[WebSocketServerProtocol] = set()
        self.running = False
        
        # Load profiles
        if profiles_dir is None:
            profiles_dir = os.path.join(os.path.dirname(__file__), 'profiles')
        profiles_path = os.path.join(profiles_dir, 'Agent-profiles.yaml')
        self.registry.load_profiles(profiles_path)
        
        # Pre-register permanent agents
        self._register_permanent_agents()
    
    def _register_permanent_agents(self):
        """Register core/always-visible agents from profiles"""
        
        # Register specialized profiles
        profile_map = {
            'architect': 'architect',
            'ops': 'ops', 
            'testing': 'testing',
            'security': 'security'
        }
        
        for key, profile_key in profile_map.items():
            agent = self.registry.register_from_profile(profile_key)
            if agent:
                logger.info(f"Registered agent: {agent.name} ({agent.role})")
        
        # Also keep Bit as the main assistant
        bit = self.registry.register(
            agent_id="bit",
            name="Bit",
            role="assistant",
            agent_type=AgentType.PERMANENT,
            color="#4A90D9",
            shape="sphere"
        )
        logger.info(f"Registered agent: {bit.name} ({bit.role})")
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.clients:
            return
        data = json.dumps(message)
        await asyncio.gather(
            *[client.send(data) for client in self.clients],
            return_exceptions=True
        )
    
    async def broadcast_event(self, event: AgentEvent):
        """Broadcast an agent event to all clients"""
        await self.broadcast({
            "type": "agent_event",
            "data": asdict(event)
        })
    
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total: {len(self.clients)}")
        
        # Send current state to new client
        await websocket.send(json.dumps({
            "type": "init",
            "data": {
                "agents": [asdict(a) for a in self.registry.list_all()]
            }
        }))
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Remove a client connection"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.clients)}")
    
    async def handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming message from Unity/web client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
                
            elif msg_type == "command":
                await self._handle_command(data)
                
            elif msg_type == "subscribe_agent":
                agent_id = data.get("agent_id")
                logger.info(f"Client subscribed to agent: {agent_id}")
                
            elif msg_type == "message":
                # Send message to a specific agent
                await self._handle_agent_message(data)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_command(self, data: dict):
        """Handle commands from frontend"""
        command = data.get("command")
        target = data.get("target")
        
        logger.info(f"Command: {command} -> {target}")
        
        # Broadcast that we received the command
        await self.broadcast({
            "type": "command_ack",
            "data": {
                "command": command,
                "target": target,
                "status": "received"
            }
        })
        
        # Update agent status to show activity
        if target:
            agent = self.registry.get(target)
            if agent:
                agent.status = AgentStatus.THINKING
                agent.current_task = f"Handling: {command}"
                await self.broadcast_event(AgentEvent(
                    event_type="agent_updated",
                    timestamp=datetime.utcnow().isoformat(),
                    agent=agent
                ))
                
                # Simulate some work
                await asyncio.sleep(2)
                
                agent.status = AgentStatus.IDLE
                agent.current_task = None
                await self.broadcast_event(AgentEvent(
                    event_type="agent_complete",
                    timestamp=datetime.utcnow().isoformat(),
                    agent=agent,
                    details="Command acknowledged"
                ))
    
    async def _handle_agent_message(self, data: dict):
        """Handle message to a specific agent"""
        target = data.get("target")
        message = data.get("message", "")
        
        agent = self.registry.get(target)
        if not agent:
            logger.warning(f"Message to unknown agent: {target}")
            return
        
        agent.status = AgentStatus.THINKING
        agent.message_preview = message[:50] + "..." if len(message) > 50 else message
        await self.broadcast_event(AgentEvent(
            event_type="agent_updated",
            timestamp=datetime.utcnow().isoformat(),
            agent=agent
        ))
        
        # Simulate processing
        await asyncio.sleep(1)
        
        agent.status = AgentStatus.WORKING
        agent.current_task = "Processing..."
        await self.broadcast_event(AgentEvent(
            event_type="agent_updated",
            timestamp=datetime.utcnow().isoformat(),
            agent=agent
        ))
    
    async def simulate_activity(self):
        """Simulate some activity for demo purposes"""
        import random
        
        # Only simulate ephemeral agents
        ephemeral_roles = ['file-ops', 'web-search', 'data-analysis']
        
        while self.running:
            await asyncio.sleep(random.uniform(5, 12))
            
            agents = self.registry.list_all()
            ephemeral = [a for a in agents if a.agent_type == AgentType.EPHEMERAL]
            
            if not ephemeral:
                # Spawn a demo ephemeral agent
                colors = ['#FF8C42', '#FFD93D', '#6BCB77']
                shapes = ['dodecahedron', 'tetrahedron', 'icosahedron']
                idx = random.randint(0, 2)
                
                new_agent = self.registry.register(
                    agent_id=f"ephem-{datetime.utcnow().timestamp()}",
                    name=f"Worker-{random.randint(1, 99)}",
                    role=ephemeral_roles[idx],
                    agent_type=AgentType.EPHEMERAL,
                    color=colors[idx],
                    shape=shapes[idx]
                )
                
                await self.broadcast_event(AgentEvent(
                    event_type="agent_spawned",
                    timestamp=datetime.utcnow().isoformat(),
                    agent=new_agent
                ))
                
                await asyncio.sleep(3)
                
                # Remove ephemeral after a bit
                self.registry.remove(new_agent.id)
                await self.broadcast_event(AgentEvent(
                    event_type="agent_complete",
                    timestamp=datetime.utcnow().isoformat(),
                    agent=new_agent,
                    details="Task complete"
                ))
    
    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        
        # Start demo activity simulation
        asyncio.create_task(self.simulate_activity())
        
        async with websockets.serve(self._handle_connection, "0.0.0.0", self.port):
            logger.info(f"Bridge API running on ws://0.0.0.0:{self.port}")
            logger.info(f"Agents: {[a.name for a in self.registry.list_all()]}")
            await asyncio.Future()  # Run forever
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)


def main():
    bridge = BridgeAPI(port=8765)
    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        logger.info("Bridge shutting down")


if __name__ == "__main__":
    main()
