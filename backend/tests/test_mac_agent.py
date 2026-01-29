# File: backend/tests/test_mac_agent.py
# Purpose: Test Mac Agent unified interface
# Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/test_mac_agent.py

import pytest
from pathlib import Path

from agent.mac_agent import (
    MacAgent,
    create_mac_agent,
    create_cli_agent,
    quick_run,
)
from agent.prompts import BASE_SYSTEM_PROMPT, CLI_SYSTEM_PROMPT


class TestMacAgent:
    """测试 MacAgent 类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        agent = MacAgent()
        
        assert agent.client is not None
        assert agent.registry is not None
        assert agent.agent is not None
        assert agent.system_prompt == BASE_SYSTEM_PROMPT
    
    def test_init_with_custom_prompt(self):
        """测试自定义提示词初始化"""
        custom_prompt = "这是自定义提示词"
        agent = MacAgent(system_prompt=custom_prompt)
        
        assert agent.system_prompt == custom_prompt
    
    def test_init_with_allowed_paths(self):
        """测试带路径限制的初始化"""
        paths = ["/Users/test/Documents", "/Users/test/Downloads"]
        agent = MacAgent(allowed_paths=paths)
        
        # 系统提示词应该包含路径信息
        assert "/Users/test/Documents" in agent.system_prompt
        assert "/Users/test/Downloads" in agent.system_prompt
    
    def test_get_tools_info(self):
        """测试获取工具信息"""
        agent = MacAgent()
        tools = agent.get_tools_info()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # 检查工具格式
        first_tool = tools[0]
        assert "type" in first_tool
        assert "function" in first_tool
        assert "name" in first_tool["function"]
        assert "description" in first_tool["function"]
    
    def test_get_tools_count(self):
        """测试获取工具数量"""
        agent = MacAgent()
        count = agent.get_tools_count()
        
        assert isinstance(count, int)
        assert count == 53  # 当前工具总数
    
    def test_update_system_prompt(self):
        """测试更新系统提示词"""
        agent = MacAgent()
        original_prompt = agent.system_prompt
        
        new_prompt = "新的系统提示词"
        agent.update_system_prompt(new_prompt)
        
        assert agent.system_prompt == new_prompt
        assert agent.system_prompt != original_prompt
    
    def test_add_allowed_paths(self):
        """测试添加允许路径"""
        agent = MacAgent()
        paths = ["/Users/test/Documents"]
        
        agent.add_allowed_paths(paths)
        
        assert "/Users/test/Documents" in agent.system_prompt


class TestFactoryFunctions:
    """测试工厂函数"""
    
    def test_create_mac_agent(self):
        """测试创建 Mac Agent"""
        agent = create_mac_agent()
        
        assert isinstance(agent, MacAgent)
        assert agent.get_tools_count() > 0
    
    def test_create_mac_agent_with_model(self):
        """测试指定模型创建"""
        agent = create_mac_agent(model="gpt-4o-mini")
        
        assert agent.config.model == "gpt-4o-mini"
    
    def test_create_mac_agent_with_paths(self):
        """测试带路径创建"""
        paths = ["/Users/test"]
        agent = create_mac_agent(allowed_paths=paths)
        
        assert "/Users/test" in agent.system_prompt
    
    def test_create_cli_agent(self):
        """测试创建 CLI Agent"""
        agent = create_cli_agent()
        
        assert isinstance(agent, MacAgent)
        assert agent.system_prompt == CLI_SYSTEM_PROMPT


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    @pytest.mark.skip(reason="需要实际的 API 调用")
    def test_quick_run(self):
        """测试快速运行"""
        result = quick_run("echo test")
        
        assert isinstance(result, str)
        assert len(result) > 0


class TestPrompts:
    """测试提示词模块"""
    
    def test_base_system_prompt(self):
        """测试基础系统提示词"""
        from agent.prompts import BASE_SYSTEM_PROMPT
        
        assert isinstance(BASE_SYSTEM_PROMPT, str)
        assert len(BASE_SYSTEM_PROMPT) > 0
        assert "macOS" in BASE_SYSTEM_PROMPT
    
    def test_cli_system_prompt(self):
        """测试 CLI 系统提示词"""
        from agent.prompts import CLI_SYSTEM_PROMPT
        
        assert isinstance(CLI_SYSTEM_PROMPT, str)
        assert len(CLI_SYSTEM_PROMPT) > 0
    
    def test_build_system_prompt_with_paths(self):
        """测试构建带路径的提示词"""
        from agent.prompts import build_system_prompt_with_paths
        
        paths = ["/Users/test/Documents", "/Users/test/Downloads"]
        prompt = build_system_prompt_with_paths(paths)
        
        assert "/Users/test/Documents" in prompt
        assert "/Users/test/Downloads" in prompt
    
    def test_build_extra_system_prompt(self):
        """测试构建额外提示词"""
        from agent.prompts import build_extra_system_prompt
        
        # 测试附件上下文
        prompt = build_extra_system_prompt(attachment_context="文件内容...")
        assert "附件内容" in prompt
        assert "文件内容..." in prompt
        
        # 测试记忆上下文
        prompt = build_extra_system_prompt(memory_context="历史对话...")
        assert "对话历史摘要" in prompt
        assert "历史对话..." in prompt
        
        # 测试自定义指令
        prompt = build_extra_system_prompt(custom_instructions="请简洁回答")
        assert "用户自定义指令" in prompt
        assert "请简洁回答" in prompt
        
        # 测试组合
        prompt = build_extra_system_prompt(
            attachment_context="文件内容",
            memory_context="历史对话",
            custom_instructions="自定义指令"
        )
        assert "附件内容" in prompt
        assert "对话历史摘要" in prompt
        assert "用户自定义指令" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
