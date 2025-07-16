package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
	agentClient, err := client.NewWithAddress(
		"841debad-7433-46ae-a0ec-0540d0df7314",
		"minimal",
		true,
		"localhost",
		8450,
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	result, err := agentClient.Run(ctx, map[string]interface{}{
		"role":    "user",
		"message": "Analyze the benefits of remote work for software teams",
	})
	if err != nil {
		log.Fatalf("Failed to run agent: %v", err)
	}

	fmt.Printf("Result: %v\n", result)
}
