#!/usr/bin/env python3
"""
File: backend/tests/run_chat_tests.py
Purpose: Enhanced test runner that saves complete chat conversations
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/run_chat_tests.py

【架构设计原则】【测试策略】【日志系统】
增强版测试运行器，记录完整的对话记录（用户输入、Agent响应、工具调用等）
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.tools.base import load_env
from tests.test_cases_config import get_all_test_cases
from agent.mac_agent import MacAgent


class ChatTestRunner:
    """
    对话测试运行器
    
    功能:
    1. 使用MacAgent进行对话测试
    2. 记录完整的对话流程（用户输入、Agent响应、工具调用）
    3. 保存为JSON和Markdown格式
    """
    
    def __init__(self):
        self.agent = MacAgent()
        self.conversations = []
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        
        # 创建对话记录目录
        self.chat_logs_dir = Path(__file__).parent / "chat_logs"
        self.chat_logs_dir.mkdir(exist_ok=True)
        
        # 生成时间戳
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def run_chat_test(
        self,
        user_input: str,
        description: str = "",
        max_tool_turns: int = 5
    ) -> Dict[str, Any]:
        """
        运行对话测试并记录完整流程
        
        Args:
            user_input: 用户输入
            description: 测试描述
            max_tool_turns: 最大工具调用轮数
        
        Returns:
            包含完整对话记录的字典
        """
        print(f"\n💬 用户输入: {user_input}")
        if description:
            print(f"📝 描述: {description}")
        
        # 记录对话
        conversation = {
            "user_input": user_input,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "events": [],
            "tool_calls": [],
            "agent_response": "",
            "success": True,
            "error": None
        }
        
        try:
            # 收集所有事件
            for event in self.agent.run_stream(user_input, max_tool_turns=max_tool_turns):
                event_copy = {
                    "type": event["type"],
                    "timestamp": datetime.now().isoformat()
                }
                
                if event["type"] == "content":
                    event_copy["content"] = event["content"]
                    conversation["agent_response"] += event["content"]
                    print(event["content"], end="", flush=True)
                
                elif event["type"] == "tool_start":
                    tool_call = {
                        "name": event["name"],
                        "args": event["args"],
                        "timestamp": datetime.now().isoformat()
                    }
                    conversation["tool_calls"].append(tool_call)
                    event_copy["tool_name"] = event["name"]
                    event_copy["tool_args"] = event["args"]
                    print(f"\n🔧 调用工具: {event['name']}")
                    print(f"   参数: {json.dumps(event['args'], ensure_ascii=False, indent=2)}")
                
                elif event["type"] == "tool_result":
                    # 更新最后一个工具调用的结果
                    if conversation["tool_calls"]:
                        conversation["tool_calls"][-1]["result"] = event.get("result", {})
                    event_copy["tool_result"] = event.get("result", {})
                    result_preview = str(event.get("result", {}))[:200]
                    print(f"\n✅ 工具结果: {result_preview}...")
                
                conversation["events"].append(event_copy)
            
            print("\n")  # 换行
            
        except Exception as e:
            conversation["success"] = False
            conversation["error"] = str(e)
            print(f"\n❌ 错误: {e}")
        
        self.conversations.append(conversation)
        return conversation
    
    def save_chat_logs_json(self):
        """保存JSON格式的对话记录"""
        json_file = self.chat_logs_dir / f"chat_logs_{self.timestamp}.json"
        
        summary = {
            "timestamp": self.timestamp,
            "total_conversations": len(self.conversations),
            "successful": sum(1 for c in self.conversations if c["success"]),
            "failed": sum(1 for c in self.conversations if not c["success"]),
            "conversations": self.conversations
        }
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ JSON对话记录已保存: {json_file}")
        return json_file
    
    def save_chat_logs_markdown(self):
        """保存Markdown格式的对话报告"""
        md_file = self.chat_logs_dir / f"chat_report_{self.timestamp}.md"
        
        successful = sum(1 for c in self.conversations if c["success"])
        failed = sum(1 for c in self.conversations if not c["success"])
        
        with open(md_file, "w", encoding="utf-8") as f:
            # 标题
            f.write(f"# Mac Agent 对话测试报告\n\n")
            f.write(f"> **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"> **对话总数**: {len(self.conversations)}\n")
            f.write(f"> **成功**: {successful} ✅\n")
            f.write(f"> **失败**: {failed} ❌\n\n")
            f.write("---\n\n")
            
            # 测试摘要
            f.write("## 📊 测试摘要\n\n")
            f.write(f"| 指标 | 数值 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 总对话数 | {len(self.conversations)} |\n")
            f.write(f"| 成功 | {successful} |\n")
            f.write(f"| 失败 | {failed} |\n")
            f.write(f"| 成功率 | {successful/len(self.conversations)*100:.1f}% |\n\n")
            f.write("---\n\n")
            
            # 详细对话记录
            f.write("## 💬 详细对话记录\n\n")
            
            for i, conv in enumerate(self.conversations, 1):
                status = "✅ 成功" if conv["success"] else "❌ 失败"
                f.write(f"### {i}. 对话 {i} - {status}\n\n")
                
                if conv["description"]:
                    f.write(f"**描述**: {conv['description']}\n\n")
                
                # 用户输入
                f.write(f"**👤 用户输入**:\n\n")
                f.write(f"```\n{conv['user_input']}\n```\n\n")
                
                # Agent响应
                if conv["agent_response"]:
                    f.write(f"**🤖 Agent响应**:\n\n")
                    f.write(f"```\n{conv['agent_response']}\n```\n\n")
                
                # 工具调用
                if conv["tool_calls"]:
                    f.write(f"**🔧 工具调用** ({len(conv['tool_calls'])} 个):\n\n")
                    for j, tool_call in enumerate(conv["tool_calls"], 1):
                        f.write(f"#### {j}. {tool_call['name']}\n\n")
                        f.write(f"**参数**:\n```json\n")
                        f.write(json.dumps(tool_call.get("args", {}), ensure_ascii=False, indent=2))
                        f.write("\n```\n\n")
                        
                        if "result" in tool_call:
                            f.write(f"**结果**:\n```json\n")
                            result_str = json.dumps(tool_call["result"], ensure_ascii=False, indent=2)
                            # 限制长度
                            if len(result_str) > 2000:
                                f.write(result_str[:2000] + "\n... (结果过长，已截断)")
                            else:
                                f.write(result_str)
                            f.write("\n```\n\n")
                
                # 错误信息
                if conv["error"]:
                    f.write(f"**❌ 错误信息**: {conv['error']}\n\n")
                
                # 时间戳
                f.write(f"**⏰ 时间**: {conv['timestamp']}\n\n")
                
                f.write("---\n\n")
        
        print(f"✅ Markdown对话报告已保存: {md_file}")
        return md_file
    
    def print_summary(self):
        """打印测试摘要"""
        successful = sum(1 for c in self.conversations if c["success"])
        failed = sum(1 for c in self.conversations if not c["success"])
        total_tools = sum(len(c["tool_calls"]) for c in self.conversations)
        
        print("\n" + "="*80)
        print("对话测试摘要")
        print("="*80)
        print(f"总对话数: {len(self.conversations)}")
        print(f"成功: {successful} ✅")
        print(f"失败: {failed} ❌")
        print(f"成功率: {successful/len(self.conversations)*100:.1f}%")
        print(f"工具调用总数: {total_tools}")
        print("="*80)
        
        if failed > 0:
            print("\n失败的对话:")
            for conv in self.conversations:
                if not conv["success"]:
                    print(f"  ❌ {conv['user_input'][:50]}...: {conv['error']}")


def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("Mac Agent 对话测试（完整记录版）")
    print("="*80)
    
    # 加载环境变量
    load_env()
    
    # 创建测试运行器
    runner = ChatTestRunner()
    
    # 准备测试问题（基于工具测试用例）
    print("\n📋 准备测试问题...")
    
    # 从工具测试用例中提取一些代表性的问题
    test_questions = [
        {
            "user_input": "查看系统信息",
            "description": "测试系统信息工具调用"
        },
        {
            "user_input": "列出当前目录的文件",
            "description": "测试文件列表工具调用"
        },
        {
            "user_input": "查看磁盘使用情况",
            "description": "测试磁盘使用工具调用"
        },
        {
            "user_input": "ping一下百度",
            "description": "测试网络工具调用"
        },
        {
            "user_input": "读取README.md文件的前100行",
            "description": "测试文件读取工具调用"
        },
    ]
    
    print(f"准备运行 {len(test_questions)} 个对话测试\n")
    print("="*80)
    
    # 运行对话测试
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"对话测试 {i}/{len(test_questions)}")
        print(f"{'='*80}")
        
        runner.run_chat_test(
            user_input=question["user_input"],
            description=question["description"],
            max_tool_turns=5
        )
    
    # 打印摘要
    runner.print_summary()
    
    # 保存结果
    json_file = runner.save_chat_logs_json()
    md_file = runner.save_chat_logs_markdown()
    
    print("\n" + "="*80)
    print("📄 对话记录已生成:")
    print(f"  - JSON: {json_file}")
    print(f"  - Markdown: {md_file}")
    print("="*80)
    
    print("\n💡 提示: 所有对话记录（包括用户输入、Agent响应、工具调用）都已保存")
    print("\n🎉 测试完成！")
    
    return 0 if sum(1 for c in runner.conversations if not c["success"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
