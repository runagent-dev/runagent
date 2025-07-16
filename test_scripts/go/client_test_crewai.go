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
		"331fa66f-1089-43f0-8912-cc1b4c22ab01",
		"research_crew",
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
		"topic": "global warming",
	})
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", result)
}
