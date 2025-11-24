# AI Journalist Agent - News Article Generator

Generate high-quality, NYT-worthy articles on any topic using AI agents with web research capabilities.


## Setup

### 1. Agent Setup

```bash
cd agents
pip install -r requirements.txt
```

Set environment variables:
```bash
export OPENAI_API_KEY="your-openai-key"
export SERPER_API_KEY="your-serper-key"
```

### 2. Deploy Agent with RunAgent Local

```bash
cd agents
runagent serve .
```

After deployment, you'll get an `agent_id`. Update this in:
- `backend/app.py` (both client instances)
- `test_dart/lib/main.dart`

### 2.1 Local vs Cloud Runs

- **Local:** Keep the `local` flag in `test_dart/lib/main.dart` (or your Dart sample) and make sure `host`/`port` point to your `runagent serve` process (defaults: `127.0.0.1:8451`).
- **Cloud:** Comment out the `local` override, then authenticate once per shell:

```bash
export RUNAGENT_API_KEY="your-runagent-api-key"
```

Use the cloud agent ID returned from the dashboard when you deploy remotely.

### 3. Backend Setup (Optional - for HTTP testing)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 4. Dart SDK Test

```bash
cd test_dart
dart pub get
dart run lib/main.dart
```

## Agent Functions

### Non-Streaming
**Entrypoint:** `article_create`
```dart
final result = await client.run({'topic': 'AI developments'});
```

### Streaming
**Entrypoint:** `article_stream`
```dart
await for (final chunk in client.runStream({'topic': 'AI developments'})) {
  print(chunk);
}
```

## Features

- **AI-Powered Research**: Automatically searches web for relevant sources
- **Content Extraction**: Reads and analyzes articles from top sources
- **High-Quality Output**: NYT-worthy articles with proper attribution
- **Streaming Support**: Real-time article generation
- **Dart SDK Compatible**: Works with RunAgent Dart SDK

## Configuration

After running `runagent serve .`, a `runagent.config.json` will be automatically generated with your agent architecture and entrypoints.

## Testing

**Dart SDK (Recommended):**
```bash
cd test_dart
dart run lib/main.dart
```

**Backend API:**
```bash
# Non-streaming
curl -X POST http://localhost:5001/api/article \
  -H "Content-Type: application/json" \
  -d '{"topic": "Latest in quantum computing"}'

# Streaming
curl -X POST http://localhost:5001/api/article/stream \
  -H "Content-Type: application/json" \
  -d '{"topic": "Climate change solutions"}'
```

## Notes

- The agent requires OpenAI API key and Serper API key
- Articles are typically 15+ paragraphs with proper citations
- Processing time varies based on topic complexity (usually 1-3 minutes)
- Streaming provides real-time updates as the article is written