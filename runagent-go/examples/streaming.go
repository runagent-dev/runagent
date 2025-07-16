package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent/runagent-go/runagent"
)

func main() {
	fmt.Println("=== Streaming Agent Example ===")

	// Create client
	client := runagent.NewRunAgentClient(runagent.Config{
		AgentID:       "841debad-7433-46ae-a0ec-0540d0df7314",
		EntrypointTag: "minimal_stream",
		Host:          "localhost",
		Port:          8450,
		Local:         true,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	// Initialize
	if err := client.Initialize(ctx); err != nil {
		log.Fatalf("Failed to initialize: %v", err)
	}

	// Start streaming
	result, err := client.Run(ctx, map[string]interface{}{
		"role":    "user",
		"message": "Write a detailed analysis of remote work benefits for software development teams",
	})
	if err != nil {
		log.Fatalf("Failed to start streaming: %v", err)
	}

	stream := result.(*runagent.StreamIterator)
	defer stream.Close()

	fmt.Println("📡 Streaming response:")
	fmt.Println("----------------------------------------")

	// Process stream
	for {
		chunk, hasMore, err := stream.Next(ctx)
		if err != nil {
			log.Printf("Stream error: %v", err)
			break
		}
		if !hasMore {
			break
		}
		if chunk != nil {
			fmt.Print(chunk)
		}
	}

	fmt.Println("\n✅ Stream completed!")
}
