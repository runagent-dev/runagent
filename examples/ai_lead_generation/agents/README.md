# 🎯 AI Lead Generation Agent - RunAgent

Automated lead generation from Quora using Firecrawl's Extract endpoint and Google Sheets integration. This RunAgent-powered agent finds and qualifies potential leads, extracting valuable information and organizing it into Google Sheets.

## Features

- **Intelligent Search**: Uses Firecrawl's search to find relevant Quora URLs
- **Smart Extraction**: Leverages Firecrawl's Extract endpoint to pull user information
- **Automated Processing**: Formats data into clean, structured format
- **Google Sheets Integration**: Automatically creates and populates sheets with lead data
- **RunAgent Compatible**: Deploy as a cloud API endpoint

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Composio

```bash
composio add googlesheets
```

Make sure the Google Sheets integration is active in your Composio dashboard.

### 3. Set Environment Variables

Update `runagent.config.json` with your API keys:
- `FIRECRAWL_API_KEY`: Get from [Firecrawl](https://www.firecrawl.dev/app/api-keys)
- `COMPOSIO_API_KEY`: Get from [Composio](https://composio.ai)
- `OPENAI_API_KEY`: Get from [OpenAI](https://platform.openai.com/api-keys)

## Usage

### Local Testing

```python
from main import generate_leads

result = generate_leads(
    search_query="AI customer support chatbots",
    num_links=3,
    firecrawl_api_key="your-key",
    composio_api_key="your-key",
    openai_api_key="your-key"
)

print(result)
```

### Deploy with RunAgent

```bash
# Test locally
runagent serve . --local

# Deploy to cloud
runagent deploy .
```

### Use the SDK

```python
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="your-deployed-agent-id",
    entrypoint_tag="generate_leads",
    local=False
)

result = client.run(
    search_query="AI video editing software",
    num_links=5
)

print(f"Google Sheet: {result['google_sheet_url']}")
print(f"Leads found: {result['leads_count']}")
```

## Parameters

- `search_query` (str): Description of leads to find (e.g., "AI customer support chatbots")
- `num_links` (int): Number of Quora URLs to process (1-10, default: 3)
- `firecrawl_api_key` (str): Your Firecrawl API key
- `composio_api_key` (str): Your Composio API key
- `openai_api_key` (str): Your OpenAI API key

## Response Format

```json
{
  "success": true,
  "search_query": "AI video editing software",
  "urls_processed": 3,
  "leads_count": 15,
  "google_sheet_url": "https://docs.google.com/spreadsheets/d/...",
  "leads_data": [...]
}
```

## How It Works

1. **Search**: Queries Quora for relevant discussions using Firecrawl search
2. **Extract**: Uses Firecrawl Extract to pull user profiles and interactions
3. **Format**: Structures data with username, bio, post type, timestamp, upvotes, and links
4. **Save**: Creates a new Google Sheet with all lead information

## Support

For issues or questions, refer to:
- [RunAgent Documentation](https://docs.runagent.dev)
- [Firecrawl Documentation](https://docs.firecrawl.dev)
- [Composio Documentation](https://docs.composio.dev)