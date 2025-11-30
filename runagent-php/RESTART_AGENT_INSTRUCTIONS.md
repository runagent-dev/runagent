# How to See Agent Responses

## Current Situation

The agent is running and all infrastructure tests pass ✅, but it returns `INTERNAL_ERROR` when trying to execute because it doesn't have access to the OpenAI API key.

## Solution: Restart Agent with OpenAI Key

### Step 1: Stop the Current Agent

```bash
runagent stop --id 91e70681-def8-4600-8a30-d037c1b51870
```

### Step 2: Set OpenAI API Key in Environment

```bash
export OPENAI_API_KEY='YOUR_OPENAI_API_KEY_HERE'
```

### Step 3: Navigate to Agent Directory

```bash
cd /home/nihal/Desktop/github_repos/runagent/nice
```

### Step 4: Start the Agent

```bash
runagent start --id 91e70681-def8-4600-8a30-d037c1b51870
```

The agent will now have access to the OpenAI API key and will be able to execute LLM calls.

### Step 5: Test and See the Response

```bash
cd /home/nihal/Desktop/github_repos/runagent/runagent-php

# Run the verification script
OPENAI_API_KEY='YOUR_OPENAI_API_KEY_HERE' python3 verify_php_sdk_with_nice_agent.py
```

You should then see actual responses like:

```
TEST 2: Non-Streaming Execution (agno_print_response)
──────────────────────────────────────────────────────

  ✓ Client initialized for non-streaming
  ℹ Sending prompt: 'What is 2+2? Answer briefly.'

  Response received:
  ────────────────────────────────────────────────────
    2 + 2 equals 4.
  ────────────────────────────────────────────────────

  ✓ ✅ TEST 2 PASSED
```

## Quick Manual Test

Once the agent is restarted with the OpenAI key, you can also test manually:

```bash
curl -X POST \
  -H "Authorization: Bearer rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6" \
  -H "Content-Type: application/json" \
  -d '{"entrypoint_tag": "agno_print_response", "kwargs": {"prompt": "Tell me a joke"}}' \
  http://0.0.0.0:8333/api/v1/agents/91e70681-def8-4600-8a30-d037c1b51870/run
```

## What You'll See

With the OpenAI key properly configured, you'll see:

1. **Non-Streaming Response**: Complete answer from GPT-4o-mini
2. **Streaming Response**: Token-by-token response chunks
3. **No More INTERNAL_ERROR**: Successful execution

## Why This Happens

The agent process needs environment variables (like `OPENAI_API_KEY`) to be set **before** it starts. If you set the environment variable after the agent is already running, it won't have access to it. That's why a restart is necessary.
