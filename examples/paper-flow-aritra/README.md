# PaperFlow – ArXiv Paper Monitor (RunAgent Serverless)

PaperFlow is a RunAgent serverless-compatible agent that:

- Monitors **arXiv** for papers matching your research topics  
- Uses **OpenAI** to filter for **highly relevant** papers  
- Tracks already-seen papers in a **persistent cache**  
- Optionally sends you **email digests** of new relevant papers  
- Can be **scheduled** via RunAgent Pulse to run automatically (e.g. daily)

---

## What the agent does

- **Query arXiv** for each topic you provide (`topics`, `max_results`, `days_back`)
- For each paper:
  - Filter by **date range**  
  - Run an **LLM relevance check** (YES/NO only) via OpenAI (async/parallel)
  - Maintain a **cache** of relevant paper IDs in `paper_cache/relevant_papers.txt`
- **Email notifications**:
  - When new relevant papers are found (not previously in the cache)
  - Sends you a nicely formatted email (title, date, link per paper)

The agent returns a result dict like:

- `status`
- `total_processed`
- `total_relevant`
- `new_papers`
- `cached_hits`
- `llm_calls`
- `email_sent`
- `papers` (list of formatted strings)

---

## Local testing (without RunAgent serverless)

From this folder:

```bash
cd /home/azureuser/runagent/examples/paper-flow-aritra
pip install -r requirements.txt

# Make sure these env vars are set (e.g. via .env or shell)
export OPENAI_API_KEY=...
export USER_EMAIL=you@example.com
export SMTP_USERNAME=your_smtp_user
export SMTP_PASSWORD=your_smtp_password
```

Run the built-in test script:

```bash
python test_agent.py basic   # Basic functionality test
python test_agent.py sdk     # Test entrypoints (check_papers, check_papers_custom_topics)
python test_agent.py openai  # Test OpenAI connectivity
python test_agent.py email   # Test email config detection
python test_agent.py all     # Run the full test suite (interactive)
```

This verifies:

- OpenAI connectivity  
- Email configuration  
- Cache read/write  
- Async entrypoint `check_papers_async`

---

## Deploying to RunAgent Serverless

From the **runagent repo root**:

```bash
cd /home/azureuser/runagent
runagent deploy /home/azureuser/runagent/examples/paper-flow-aritra
```

This will:

- Build the agent bundle from `agent.py` + `runagent.config.json`
- Upload it to RunAgent Cloud
- Start a **micro VM** for this agent when executed

The deployed agent id is stored in:

- `.deployments/<agent_id>.json`
- `runagent.config.json` → `agent_id`

Make sure your `.env` / cloud env includes:

- `OPENAI_API_KEY`
- `USER_EMAIL`
- `SMTP_SERVER` / `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

### 📧 Gmail SMTP – App Password Setup

If you use **Gmail**, you **cannot** use your normal Gmail password for SMTP.  
You must create a **Gmail App Password**:

1. Open your Google Account: `https://myaccount.google.com`
2. Go to **Security → 2-Step Verification** and **enable 2FA** (if not already enabled)
3. After 2FA is enabled, go to **Security → 2-Step Verification → App passwords**
4. Click **App passwords** (usually at the bottom of the page)
5. In the dialog:
   - Select app: **Mail**
   - Select device: **Other**, type something like `"PaperFlow"`
   - Click **Generate**
6. Copy the **16-character** app password (looks like: `xxxx xxxx xxxx xxxx`)
7. Use this value as:
   - `SMTP_USERNAME` = your Gmail address (e.g. `you@gmail.com`)
   - `SMTP_PASSWORD` = the **16-character app password**

Do **not** commit these values to git. Prefer environment variables or a `.env` file mounted into the VM.

---

## Running via Python SDK (`client_test_paperflow.py`)

The agent exposes **only one serverless entrypoint**:  
- **`check_papers_async`** – async + parallel processing (fast, production mode)

Example async/parallel invocation (from `runagent/test_scripts/python/client_test_paperflow.py`):

```python
from runagent import RunAgentClient

client_async = RunAgentClient(
    agent_id="62f7a781-71bb-4d62-a68f-24dc4f2bfd0b",  # update to your agent_id
    entrypoint_tag="check_papers_async",              # async/parallel entrypoint
    local=False,
    user_id="prova4",
    persistent_memory=True
)

result = client_async.run(
    topics=["LLM finetuning"],
    max_results=20,
    days_back=100
)

print(f"Found {result['total_relevant']} relevant papers (async mode)")
print(f"Email sent: {result['email_sent']}")
```

Use `local=False` to hit the deployed serverless agent, and always use:

- **`entrypoint_tag="check_papers_async"`**

---

## (Optional) Local streaming experiments

The codebase still contains some streaming helpers and a `client_test_paperflow_stream.py` example, but in **serverless** the supported entrypoint is only `check_papers_async`.  
You can still experiment with streaming locally if you want, but for deployed usage stick to the async entrypoint.

---

## Scheduling with RunAgent Pulse (`test_paperflow.py`)

In `runagent-pulse/examples/test_paperflow.py` you’ll find examples of scheduling this agent with **RunAgent Pulse**:

- Configure:

```python
PULSE_SERVER_URL = "http://localhost:8000"   # or your Pulse server
AGENT_ID = "62f7a781-71bb-4d62-a68f-34dc4f2bfd0b"  # the deployed PaperFlow agent id

TOPICS = [
    "fine-tuning vision language models"
]
```

- Daily schedule:

```python
task = pulse.schedule_agent(
    agent_id=AGENT_ID,
    entrypoint_tag="check_papers_async",
    when="daily at 9am",
    params={
        "topics": TOPICS,
        "max_results": 20,
        "days_back": 7,
        "verbose": True,
    },
    executor_type="serverless",
    user_id="paperflow_daily",
    persistent_memory=True,
)
```

- Recurring schedule:

```python
task = pulse.schedule_agent(
    agent_id=AGENT_ID,
    entrypoint_tag="check_papers_async",
    when="in 3 minute",
    params={
        "topics": TOPICS,
        "max_results": 20,
        "days_back": 100,
        "verbose": True,
    },
    executor_type="serverless",
    user_id="paperflow_recurring",
    persistent_memory=True,
    repeat={
        "interval": "10m",  # e.g. every 10 minutes
        "times": 1,         # None = infinite
    },
)
```

This lets you:

- Run PaperFlow **daily** as a digest  
- Or run **recurring checks** (e.g. every few hours) for fresh arXiv papers

---

## Summary

- `agent.py` – core logic (arXiv queries, LLM filtering, caching, email)  
- `runagent.config.json` – RunAgent metadata, **async-only** entrypoint, agent id  
- `test_agent.py` – local testing harness (no serverless needed)  
- `client_test_paperflow.py` – Python SDK example (**async only**)  
- `runagent-pulse/examples/test_paperflow.py` – Pulse scheduling examples

Once deployed with `runagent deploy`, you can:

- Call the agent from Python or JS via the SDK using `check_papers_async`  
- Schedule periodic runs via Pulse for continuous paper monitoring


