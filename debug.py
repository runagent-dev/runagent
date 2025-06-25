#!/usr/bin/env python3
"""
Debug script to identify why agent 732e45b2 is failing
"""

import importlib.util
import os
import sys
import traceback
from pathlib import Path


def debug_agent(agent_id="d6594457"):
    """Debug the specific agent to find the exact error"""

    print(f"🔍 Debugging agent: {agent_id}")
    print("=" * 50)

    # 1. Check agent directory
    agent_dir = Path(f"deployments/{agent_id}")
    print(f"📁 Agent directory: {agent_dir}")
    print(f"📁 Directory exists: {agent_dir.exists()}")

    if not agent_dir.exists():
        print("❌ Agent directory not found!")
        return

    # 2. List files
    print(f"📄 Files in directory:")
    for item in agent_dir.iterdir():
        size = item.stat().st_size if item.is_file() else "DIR"
        print(f"   - {item.name} ({size} bytes)")

    # 3. Check main.py exists
    main_file = agent_dir / "main.py"
    print(f"\n📄 main.py exists: {main_file.exists()}")

    if not main_file.exists():
        print("❌ main.py not found!")
        return

    # 4. Check main.py content
    print(f"\n📄 main.py content (first 500 chars):")
    try:
        content = main_file.read_text()
        print(content[:500] + ("..." if len(content) > 500 else ""))
        print(f"\n📄 File size: {len(content)} characters")
        print(f"📄 Has 'def run(': {'def run(' in content}")
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return

    # 5. Check requirements.txt
    req_file = agent_dir / "requirements.txt"
    print(f"\n📋 requirements.txt exists: {req_file.exists()}")
    if req_file.exists():
        try:
            reqs = req_file.read_text()
            print(f"📋 Requirements:\n{reqs}")
        except Exception as e:
            print(f"❌ Error reading requirements.txt: {e}")

    # 6. Check .env file
    env_file = agent_dir / ".env"
    print(f"\n🔐 .env file exists: {env_file.exists()}")
    if env_file.exists():
        try:
            env_content = env_file.read_text()
            # Don't print actual keys, just show structure
            lines = env_content.strip().split("\n")
            print(f"🔐 .env has {len(lines)} lines")
            for line in lines:
                if "=" in line:
                    key = line.split("=")[0]
                    print(f"   - {key}=***")
        except Exception as e:
            print(f"❌ Error reading .env: {e}")

    # 7. Try to import main.py
    print(f"\n🔄 Attempting to import main.py...")

    # Save original path
    original_path = sys.path.copy()

    try:
        # Add agent directory to Python path
        sys.path.insert(0, str(agent_dir))

        # Try to import
        spec = importlib.util.spec_from_file_location("main", main_file)
        if spec is None:
            print("❌ Could not create module spec")
            return

        print("✅ Module spec created successfully")

        main_module = importlib.util.module_from_spec(spec)
        print("✅ Module object created successfully")

        # Try to execute the module
        print("🔄 Executing module...")
        spec.loader.exec_module(main_module)
        print("✅ Module executed successfully")

        # Check for run function
        if hasattr(main_module, "run"):
            print("✅ 'run' function found")
            print(f"✅ 'run' is callable: {callable(main_module.run)}")

            # Try to call the run function
            print("\n🔄 Testing run function with sample input...")
            test_input = {
                "messages": [{"role": "user", "content": "Hello test"}],
                "config": {},
            }

            try:
                result = main_module.run(test_input)
                print("✅ Run function executed successfully!")
                print(f"📤 Result type: {type(result)}")
                print(f"📤 Result: {result}")

                # Check result format
                if isinstance(result, dict):
                    print("✅ Result is a dictionary")
                    if "success" in result:
                        print(f"✅ Has 'success' key: {result['success']}")
                    if "result" in result:
                        print(f"✅ Has 'result' key: {type(result['result'])}")
                    if "errors" in result:
                        print(f"⚠️ Has 'errors' key: {result['errors']}")
                else:
                    print(f"⚠️ Result is not a dictionary: {type(result)}")

            except Exception as e:
                print(f"❌ Error calling run function: {e}")
                print(f"📋 Traceback:\n{traceback.format_exc()}")
        else:
            print("❌ 'run' function not found!")
            print(
                f"📋 Available attributes: {[attr for attr in dir(main_module) if not attr.startswith('_')]}"
            )

    except Exception as e:
        print(f"❌ Error during import: {e}")
        print(f"📋 Traceback:\n{traceback.format_exc()}")

    finally:
        # Restore original Python path
        sys.path = original_path
        print(f"\n🔄 Python path restored")

    # 8. Check environment variables
    print(f"\n🔐 Environment variables check:")
    important_env_vars = ["OPENAI_API_KEY", "PYTHONPATH"]
    for var in important_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"   - {var}: {'***' if 'KEY' in var else value}")
        else:
            print(f"   - {var}: Not set")

    # 9. Check Python environment
    print(f"\n🐍 Python environment:")
    print(f"   - Python version: {sys.version}")
    print(f"   - Python executable: {sys.executable}")
    print(f"   - Current working directory: {os.getcwd()}")

    # 10. Check installed packages relevant to the agent
    print(f"\n📦 Checking installed packages:")
    packages_to_check = ["langchain", "langchain_openai", "openai", "python-dotenv"]

    for package in packages_to_check:
        try:
            __import__(package)
            print(f"   ✅ {package}: Installed")
        except ImportError:
            print(f"   ❌ {package}: Not installed")
        except Exception as e:
            print(f"   ⚠️ {package}: Error - {e}")

    print("\n" + "=" * 50)
    print("🔍 Debug complete!")


def install_missing_dependencies():
    """Install missing dependencies for the agent"""
    print("📦 Installing missing dependencies...")

    import subprocess

    requirements = [
        "langchain==0.1.0",
        "langchain-openai==0.0.5",
        "openai==1.12.0",
        "python-dotenv==1.0.0",
    ]

    for req in requirements:
        try:
            print(f"   Installing {req}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", req, "--quiet"]
            )
            print(f"   ✅ {req} installed")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {req}: {e}")


def fix_env_file(agent_id="732e45b2"):
    """Create or fix .env file for the agent"""
    agent_dir = Path(f"deployments/{agent_id}")
    env_file = agent_dir / ".env"

    print(f"🔐 Fixing .env file for agent {agent_id}")

    # Create a basic .env file with placeholder
    env_content = """# RunAgent Environment Variables
OPENAI_API_KEY=your-openai-api-key-here

# Note: Replace 'your-openai-api-key-here' with your actual OpenAI API key
# You can get one from: https://platform.openai.com/api-keys
"""

    try:
        with open(env_file, "w") as f:
            f.write(env_content)
        print(f"✅ Created .env file at {env_file}")
        print("⚠️ Remember to add your actual OpenAI API key!")
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")


def quick_fix_all(agent_id="732e45b2"):
    """Apply all quick fixes"""
    print("🔧 Applying quick fixes...")
    print("=" * 50)

    # 1. Install dependencies
    install_missing_dependencies()

    # 2. Fix .env file
    fix_env_file(agent_id)

    # 3. Set temporary API key for testing
    os.environ["OPENAI_API_KEY"] = "test-key-for-debugging"
    print("🔐 Set temporary OPENAI_API_KEY for testing")

    print("=" * 50)
    print("✅ Quick fixes applied!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Debug RunAgent local agent")
    parser.add_argument("--agent-id", default="732e45b2", help="Agent ID to debug")
    parser.add_argument("--fix", action="store_true", help="Apply quick fixes")
    parser.add_argument(
        "--install-deps", action="store_true", help="Install missing dependencies"
    )
    parser.add_argument("--fix-env", action="store_true", help="Fix .env file")

    args = parser.parse_args()

    if args.fix:
        quick_fix_all(args.agent_id)
        print("\n" + "=" * 50)

    if args.install_deps:
        install_missing_dependencies()

    if args.fix_env:
        fix_env_file(args.agent_id)

    # Always run debug
    debug_agent(args.agent_id)
