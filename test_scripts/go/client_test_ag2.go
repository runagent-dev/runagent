package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/client"
)

func main() {
	agentClient, err := client.NewWithAddress(
		"7c8c54d0-297b-4c63-86ae-38326a882067",
		"ag2_invoke",
		true,
		"localhost",
		8453,
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	result, err := agentClient.Run(ctx, map[string]interface{}{
		"message":   "The capital of bd is dhaka",
		"max_turns": 4,
	})
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", result)
}
