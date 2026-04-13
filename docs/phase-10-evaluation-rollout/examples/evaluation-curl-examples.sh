curl -s "http://localhost:8000/evaluation/story/story_demo_001?run_limit=100" | jq .
curl -s "http://localhost:8000/evaluation/global?run_limit=300" | jq .
curl -s "http://localhost:8000/evaluation/rollout/story_demo_001?run_limit=100" | jq .
