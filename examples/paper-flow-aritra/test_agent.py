"""
Test PaperFlow agent locally before deploying to RunAgent Serverless

This script tests the agent functionality without requiring full deployment.
"""
import os
import sys

# Add current directory to path to import agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import ArxivAgent, check_papers, check_papers_custom_topics


def test_basic_functionality():
    """Test basic paper search and filtering"""
    
    print("=" * 70)
    print("PaperFlow Local Test")
    print("=" * 70)
    
    # Create test agent
    agent = ArxivAgent(
        topics=[
            "neural networks",
            "transformers"
        ],
        max_results=5,
        days_back=7,
        verbose=True,
        cache_dir="test_cache"
    )
    
    print("\n🧪 Running test search...")
    result = agent.run()
    
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total processed: {result.get('total_processed', 0)}")
    print(f"Total relevant: {result.get('total_relevant', 0)}")
    print(f"New papers: {result.get('new_papers', 0)}")
    print(f"Cached hits: {result.get('cached_hits', 0)}")
    print(f"LLM calls: {result.get('llm_calls', 0)}")
    print(f"Email sent: {result.get('email_sent', False)}")
    
    if result.get('papers'):
        print(f"\n📄 Found {len(result['papers'])} relevant paper(s):")
        for i, paper in enumerate(result['papers'][:3], 1):  # Show first 3
            print(f"\n{i}. {paper[:200]}...")
    else:
        print("\n📄 No relevant papers found")
    
    if result.get('error'):
        print(f"\n⚠️  Error: {result['error']}")
    
    return result


def test_sdk_simulation():
    """Simulate SDK calls to test entrypoints"""
    
    print("\n" + "=" * 70)
    print("SDK Call Simulation Test")
    print("=" * 70)
    
    # Test 1: Default entrypoint
    print("\n🧪 Test 1: check_papers() entrypoint")
    try:
        result1 = check_papers(
            topics=["machine learning"],
            max_results=3,
            days_back=7,
            verbose=True
        )
        status = result1.get('status', 'unknown')
        total = result1.get('total_relevant', 0)
        print(f"✅ Result: {status}, Found {total} papers")
        if result1.get('error'):
            print(f"   ⚠️  Error: {result1['error']}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        result1 = None
    
    # Test 2: Custom topics entrypoint
    print("\n🧪 Test 2: check_papers_custom_topics() entrypoint")
    try:
        result2 = check_papers_custom_topics(
            topic1="quantum computing",
            topic2="neural networks",
            max_results=3,
            days_back=7
        )
        status = result2.get('status', 'unknown')
        total = result2.get('total_relevant', 0)
        print(f"✅ Result: {status}, Found {total} papers")
        if result2.get('error'):
            print(f"   ⚠️  Error: {result2['error']}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        result2 = None
    
    return result1, result2


def test_email_config():
    """Test email configuration"""
    
    print("\n" + "=" * 70)
    print("Email Configuration Test")
    print("=" * 70)
    
    user_email = os.getenv("USER_EMAIL", "")
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if user_email and smtp_username and smtp_password:
        print("✅ Email configuration found:")
        print(f"   User: {user_email}")
        print(f"   SMTP: {os.getenv('SMTP_SERVER', 'smtp.gmail.com')}")
        print(f"   Port: {os.getenv('SMTP_PORT', '587')}")
        print("\n⚠️  Note: Email will only be sent if new papers are found")
    else:
        print("❌ Email configuration incomplete:")
        print(f"   USER_EMAIL: {'✅ set' if user_email else '❌ not set'}")
        print(f"   SMTP_USERNAME: {'✅ set' if smtp_username else '❌ not set'}")
        print(f"   SMTP_PASSWORD: {'✅ set' if smtp_password else '❌ not set'}")
        print("\n💡 To enable email notifications:")
        print("   1. Set environment variables:")
        print("      export USER_EMAIL='your-email@example.com'")
        print("      export SMTP_USERNAME='your-email@gmail.com'")
        print("      export SMTP_PASSWORD='your-app-password'")
        print("   2. For Gmail, use an App Password (not your regular password)")


def test_openai():
    """Test OpenAI availability"""
    
    print("\n" + "=" * 70)
    print("OpenAI Configuration Test")
    print("=" * 70)
    
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    
    if openai_api_key:
        print("✅ OPENAI_API_KEY found")
        print(f"   Key length: {len(openai_api_key)} characters")
        print(f"   Key prefix: {openai_api_key[:10]}...")
        
        # Test API connection
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            
            print("\n🧪 Testing OpenAI API connection...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Say 'OK' if you can read this."}
                ],
                max_tokens=5
            )
            
            output = response.choices[0].message.content.strip()
            print(f"✅ OpenAI API working! Response: {output}")
            
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            print("   Check your API key and internet connection")
    else:
        print("❌ OPENAI_API_KEY not set")
        print("\n💡 To enable OpenAI:")
        print("   1. Get your API key from: https://platform.openai.com/api-keys")
        print("   2. Set environment variable:")
        print("      export OPENAI_API_KEY='sk-proj-your-key-here'")


def test_cache_functionality():
    """Test cache read/write functionality"""
    
    print("\n" + "=" * 70)
    print("Cache Functionality Test")
    print("=" * 70)
    
    import tempfile
    import shutil
    
    # Create temporary cache directory
    test_cache_dir = tempfile.mkdtemp(prefix="test_paper_cache_")
    test_cache_file = os.path.join(test_cache_dir, "relevant_papers.txt")
    
    try:
        # Test 1: Load empty cache
        agent = ArxivAgent(
            topics=["test"],
            max_results=1,
            days_back=7,
            verbose=False,
            cache_dir=test_cache_dir
        )
        
        cached = agent.load_cached_papers()
        print(f"✅ Empty cache loaded: {len(cached)} papers")
        
        # Test 2: Save paper ID
        test_paper_id = "1234.5678"
        agent.save_paper_id(test_paper_id)
        print(f"✅ Paper ID saved: {test_paper_id}")
        
        # Test 3: Load cache with saved paper
        cached = agent.load_cached_papers()
        if test_paper_id in cached:
            print(f"✅ Paper ID found in cache: {test_paper_id}")
        else:
            print(f"❌ Paper ID not found in cache")
        
        # Cleanup
        shutil.rmtree(test_cache_dir)
        print("✅ Cache test completed successfully")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)


def run_all_tests():
    """Run all tests"""
    
    print("\n" + "🚀" * 35)
    print("PaperFlow Test Suite")
    print("🚀" * 35)
    
    # Test 1: OpenAI
    test_openai()
    
    # Test 2: Email config
    test_email_config()
    
    # Test 3: Cache functionality
    test_cache_functionality()
    
    # Test 4: SDK simulation
    test_sdk_simulation()
    
    # Test 5: Basic functionality
    # Note: This makes real API calls and LLM requests
    print("\n" + "=" * 70)
    print("Running full integration test (this may take a minute)...")
    print("=" * 70)
    print("⚠️  This will make real API calls to arXiv and OpenAI")
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        test_basic_functionality()
    else:
        print("Skipping full integration test")
    
    print("\n" + "✅" * 35)
    print("All tests complete!")
    print("✅" * 35)


if __name__ == "__main__":
    # Load .env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        print("Loading .env file...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        
        if test_name == "basic":
            test_basic_functionality()
        elif test_name == "sdk":
            test_sdk_simulation()
        elif test_name == "email":
            test_email_config()
        elif test_name == "openai":
            test_openai()
        elif test_name == "cache":
            test_cache_functionality()
        elif test_name == "all":
            run_all_tests()
        else:
            print("Available tests: basic, sdk, email, openai, cache, all")
            print("Usage: python test_agent.py [test_name]")
    else:
        run_all_tests()

