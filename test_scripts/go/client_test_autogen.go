package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
	// Create client
	agentClient, err := client.New(
		"<agent_id>",     // agentID
		"autogen_invoke", // entrypointTag
		true,             // local
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	// Run the agent
	result, err := agentClient.Run(ctx, map[string]interface{}{
		"task": "what is autogen",
	})
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", result)
}
