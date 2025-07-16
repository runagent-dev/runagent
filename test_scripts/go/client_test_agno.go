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
		"0a0765df-96d4-4884-90b8-74a6c3632010",
		"agno_assistant",
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
		"prompt": "I want to know abour chocklate",
	})
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", result)
}
