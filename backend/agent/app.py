# File: backend/agent/app.py
# Purpose: Provide a CLI entrypoint for the backend agent runtime.
import sys

from agent.mac_agent import create_cli_agent


def main() -> int:
    """
    CLI entrypoint for Mac Agent.
    
    Usage:
        python -m agent.app "查看系统信息"
        echo "列出当前目录" | python -m agent.app
    """
    # Get user input from args or stdin
    if len(sys.argv) < 2:
        user_input = sys.stdin.read().strip()
    else:
        user_input = " ".join(sys.argv[1:]).strip()
    
    if not user_input:
        print("Error: No input provided", file=sys.stderr)
        print("Usage: python -m agent.app '<your question>'", file=sys.stderr)
        return 1
    
    # Create CLI agent and run
    agent = create_cli_agent()
    output = agent.run(user_input)
    sys.stdout.write(output)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
