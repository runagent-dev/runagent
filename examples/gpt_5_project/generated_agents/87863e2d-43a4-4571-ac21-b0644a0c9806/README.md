# movie_recommender_llamaindex

A retrieval-augmented movie recommendation agent that uses LlamaIndex to combine user preferences with a movie knowledge base (plots, genres, cast, reviews) to produce personalized recommendations and explanations. It supports filtering, ranking, and returning relevant metadata and rationale for each suggestion.

## Framework
llamaindex

## Usage

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run with RunAgent
```bash
runagent serve .
```

### Test the agent
```bash
python3 agent_test.py <agent_id> localhost <port> "your test message"
```

## Input Fields
user_query, preferred_genres, preferred_actors_directors, release_year_range, minimum_rating, language, max_results, include_synopses, explain_reasons

## Entrypoints
main, recommend
