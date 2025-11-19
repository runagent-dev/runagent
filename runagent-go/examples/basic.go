package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent/runagent-go/runagent"
)

func main() {
	fmt.Println("=== Example 1: Non-Streaming ===")

	client, err := runagent.NewRunAgentClient(runagent.Config{
		AgentID:       "841debad-7433-46ae-a0ec-0540d0df7314",
		EntrypointTag: "minimal",
		Host:          "localhost",
		Port:          8450,
		Local:         runagent.Bool(true),
	})
	if err != nil {
		log.Fatalf("failed to create client: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	solutionResult, err := client.Run(ctx,
		runagent.Kw("role", "user"),
		runagent.Kw("message", "Analyze the benefits of remote work for software teams"),
	)
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", solutionResult)
}
