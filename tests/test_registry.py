"""
Tests for Agent Registry
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge_api import AgentRegistry, Agent, AgentType, AgentStatus


class TestAgentRegistry:
    """Test cases for AgentRegistry"""
    
    def test_register_agent(self):
        """Test registering a basic agent"""
        registry = AgentRegistry()
        agent = registry.register(
            agent_id="test-1",
            name="Test Agent",
            role="testing",
            agent_type=AgentType.PERMANENT,
            color="#FF0000",
            shape="sphere"
        )
        
        assert agent is not None
        assert agent.id == "test-1"
        assert agent.name == "Test Agent"
        assert agent.role == "testing"
        assert agent.agent_type == AgentType.PERMANENT
        assert agent.color == "#FF0000"
        assert agent.shape == "sphere"
        assert agent.status == AgentStatus.IDLE
    
    def test_get_agent(self):
        """Test retrieving a registered agent"""
        registry = AgentRegistry()
        registry.register(
            agent_id="test-1",
            name="Test Agent",
            role="testing",
            agent_type=AgentType.PERMANENT
        )
        
        agent = registry.get("test-1")
        assert agent is not None
        assert agent.name == "Test Agent"
    
    def test_get_nonexistent_agent(self):
        """Test retrieving an agent that doesn't exist"""
        registry = AgentRegistry()
        agent = registry.get("nonexistent")
        assert agent is None
    
    def test_update_agent(self):
        """Test updating an agent's status"""
        registry = AgentRegistry()
        registry.register(
            agent_id="test-1",
            name="Test Agent",
            role="testing",
            agent_type=AgentType.PERMANENT
        )
        
        updated = registry.update("test-1", status=AgentStatus.WORKING, current_task="Testing...")
        assert updated is not None
        assert updated.status == AgentStatus.WORKING
        assert updated.current_task == "Testing..."
    
    def test_update_nonexistent_agent(self):
        """Test updating a nonexistent agent returns None"""
        registry = AgentRegistry()
        result = registry.update("nonexistent", status=AgentStatus.WORKING)
        assert result is None
    
    def test_remove_agent(self):
        """Test removing an agent"""
        registry = AgentRegistry()
        registry.register(
            agent_id="test-1",
            name="Test Agent",
            role="testing",
            agent_type=AgentType.EPHEMERAL
        )
        
        result = registry.remove("test-1")
        assert result is True
        assert registry.get("test-1") is None
    
    def test_remove_nonexistent_agent(self):
        """Test removing a nonexistent agent returns False"""
        registry = AgentRegistry()
        result = registry.remove("nonexistent")
        assert result is False
    
    def test_list_all_agents(self):
        """Test listing all registered agents"""
        registry = AgentRegistry()
        registry.register(agent_id="test-1", name="Agent 1", role="r1", agent_type=AgentType.PERMANENT)
        registry.register(agent_id="test-2", name="Agent 2", role="r2", agent_type=AgentType.EPHEMERAL)
        
        agents = registry.list_all()
        assert len(agents) == 2
    
    def test_multiple_agents_same_id(self):
        """Test that registering with same ID replaces existing"""
        registry = AgentRegistry()
        registry.register(agent_id="test-1", name="Agent 1", role="r1", agent_type=AgentType.PERMANENT, color="#FF0000")
        registry.register(agent_id="test-1", name="Agent 1 Updated", role="r1", agent_type=AgentType.PERMANENT, color="#00FF00")
        
        agents = registry.list_all()
        assert len(agents) == 1
        assert agents[0].color == "#00FF00"


class TestProfileLoading:
    """Test cases for loading agent profiles"""
    
    def test_load_profiles(self):
        """Test loading profiles from YAML file"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        
        registry.load_profiles(profiles_path)
        
        assert len(registry.profiles) > 0
        assert 'architect' in registry.profiles
        assert 'ops' in registry.profiles
        assert 'testing' in registry.profiles
        assert 'security' in registry.profiles
    
    def test_register_from_profile(self):
        """Test registering an agent from a profile"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        registry.load_profiles(profiles_path)
        
        agent = registry.register_from_profile('architect')
        
        assert agent is not None
        assert agent.name == "Architect"
        assert agent.role == "system_design"
        assert agent.agent_type == AgentType.PERMANENT
        assert agent.color == "#9B59B6"
        assert agent.shape == "octahedron"
        assert agent.expertise is not None
        assert len(agent.expertise) > 0
    
    def test_register_from_invalid_profile(self):
        """Test registering from nonexistent profile returns None"""
        registry = AgentRegistry()
        agent = registry.register_from_profile('nonexistent')
        assert agent is None


class TestAgentProfiles:
    """Test that profile content is correct"""
    
    def test_architect_profile(self):
        """Verify architect profile has expected fields"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        registry.load_profiles(profiles_path)
        
        arch = registry.profiles['architect']
        assert arch['name'] == "Architect"
        assert 'system_design' in arch['expertise']
        assert 'api_design' in arch['expertise']
        assert arch['shape'] == 'octahedron'
    
    def test_ops_profile(self):
        """Verify ops profile has expected fields"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        registry.load_profiles(profiles_path)
        
        ops = registry.profiles['ops']
        assert ops['name'] == "Ops"
        assert 'ci_cd' in ops['expertise']
        assert 'kubernetes' in ops['expertise']
        assert ops['shape'] == 'dodecahedron'
    
    def test_testing_profile(self):
        """Verify testing profile has expected fields"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        registry.load_profiles(profiles_path)
        
        testing = registry.profiles['testing']
        assert testing['name'] == "Testing"
        assert 'test_automation' in testing['expertise']
        assert 'unit_testing' in testing['expertise']
        assert testing['shape'] == 'icosahedron'
    
    def test_security_profile(self):
        """Verify security profile has expected fields"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        registry.load_profiles(profiles_path)
        
        security = registry.profiles['security']
        assert security['name'] == "Security"
        assert 'vulnerability_analysis' in security['expertise']
        assert 'secure_coding' in security['expertise']
        assert security['shape'] == 'tetrahedron'
    
    def test_all_profiles_permanent(self):
        """Verify all profiles are marked as permanent"""
        registry = AgentRegistry()
        profiles_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles', 'agent-profiles.yaml')
        registry.load_profiles(profiles_path)
        
        for key, profile in registry.profiles.items():
            assert profile['agent_type'] == 'permanent', f"Profile {key} should be permanent"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
