package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
	agentClient, err := client.New(
		"<agent_id>", // agentID
		"generic",    // entrypoint tag
		true,         // local
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	result, err := agentClient.Run(ctx, map[string]interface{}{
		"query":         "My phone battery is dead",
		"num_solutions": 4,
	})
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", result)
}
