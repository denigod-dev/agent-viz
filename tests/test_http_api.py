"""
Tests for Bridge API HTTP endpoints
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge_api import BridgeAPI, AgentType, AgentStatus


class MockRequest:
    """Mock aiohttp Request object for testing"""
    def __init__(self, json_data=None, invalid_json=False):
        self._json_data = json_data
        self._invalid_json = invalid_json
    
    async def json(self):
        if self._invalid_json:
            raise json.JSONDecodeError("Invalid JSON", "", 0)
        return self._json_data


class TestHTTPEndpoints:
    """Test cases for HTTP endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        request = MockRequest()
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_health(request))
        loop.close()
        
        assert resp.status == 200
        data = json.loads(resp.text)
        assert data['status'] == 'ok'
        assert 'agents' in data
        assert 'ws_clients' in data
    
    def test_list_agents_endpoint(self):
        """Test list agents endpoint"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        request = MockRequest()
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_list_agents(request))
        loop.close()
        
        assert resp.status == 200
        data = json.loads(resp.text)
        assert 'agents' in data
        # Should have permanent agents
        assert len(data['agents']) >= 5
    
    def test_post_event_spawns_agent(self):
        """Test posting an event creates a new agent"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        
        request = MockRequest(json_data={
            'event_type': 'agent_spawned',
            'agent': {
                'id': 'test-agent-1',
                'name': 'Test Agent',
                'role': 'testing',
                'status': 'idle'
            }
        })
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        
        assert resp.status == 200
        data = json.loads(resp.text)
        assert data['status'] == 'ok'
        assert data['agent_id'] == 'test-agent-1'
        
        # Verify agent was registered
        agent = bridge.registry.get('test-agent-1')
        assert agent is not None
        assert agent.name == 'Test Agent'
    
    def test_post_event_updates_agent(self):
        """Test posting an event updates an existing agent"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        
        # First spawn an agent
        bridge.registry.register(
            agent_id='test-agent-2',
            name='Test Agent 2',
            role='testing',
            agent_type=AgentType.EPHEMERAL
        )
        
        # Now update it
        request = MockRequest(json_data={
            'event_type': 'agent_updated',
            'agent': {
                'id': 'test-agent-2',
                'name': 'Test Agent 2',
                'role': 'testing',
                'status': 'working',
                'current_task': 'Processing test'
            }
        })
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        
        assert resp.status == 200
        
        # Verify agent was updated
        agent = bridge.registry.get('test-agent-2')
        assert agent is not None
        assert agent.status == AgentStatus.WORKING
        assert agent.current_task == 'Processing test'
    
    def test_post_event_complete(self):
        """Test agent completion event"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        
        # First register an agent
        bridge.registry.register(
            agent_id='test-agent-3',
            name='Test Agent 3',
            role='testing',
            agent_type=AgentType.EPHEMERAL
        )
        
        request = MockRequest(json_data={
            'event_type': 'agent_complete',
            'agent': {
                'id': 'test-agent-3',
                'name': 'Test Agent 3',
                'role': 'testing',
                'status': 'complete'
            },
            'details': 'Task finished successfully'
        })
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        
        assert resp.status == 200
        
        # Verify agent status updated
        agent = bridge.registry.get('test-agent-3')
        assert agent.status == AgentStatus.COMPLETE
    
    def test_post_event_missing_fields(self):
        """Test posting event with missing fields returns error"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        
        import asyncio
        
        # Missing event_type
        request = MockRequest(json_data={'agent': {'id': 'test'}})
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        assert resp.status == 400
        
        # Missing agent
        request = MockRequest(json_data={'event_type': 'agent_spawned'})
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        assert resp.status == 400
    
    def test_post_event_with_provider_info(self):
        """Test posting event with provider and model info"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        
        request = MockRequest(json_data={
            'event_type': 'agent_spawned',
            'agent': {
                'id': 'openclaw-task-1',
                'name': 'OpenClaw Task',
                'role': 'coding',
                'status': 'working',
                'provider': 'openclaw',
                'model': 'minimax-m2.7:cloud'
            }
        })
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        
        assert resp.status == 200
        
        agent = bridge.registry.get('openclaw-task-1')
        assert agent.provider == 'openclaw'
        assert agent.model == 'minimax-m2.7:cloud'
    
    def test_post_event_invalid_json(self):
        """Test posting invalid JSON returns error"""
        bridge = BridgeAPI(ws_port=18765, http_port=18766)
        
        request = MockRequest(invalid_json=True)
        
        import asyncio
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(bridge.http_handle_event(request))
        loop.close()
        
        assert resp.status == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
