# Queue a run
curl -s -X POST http://localhost:8000/run/tests -H 'Content-Type: application/json' -d '{"story_id":"story_demo_001"}' | jq .

# View queue snapshot
curl -s 'http://localhost:8000/run/queue?limit=50' | jq .

# View one queue item
curl -s http://localhost:8000/run/queue/<queue_id> | jq .

# Cancel pending queue item
curl -s -X DELETE http://localhost:8000/run/queue/<queue_id> | jq .
