package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/client"
)

func main() {
	fmt.Println("=== Minimal Streaming Example ===")

	// Create client for streaming entrypoint
	agentClient, err := client.NewWithAddress(
		"841debad-7433-46ae-a0ec-0540d0df7314", // agentID
		"minimal_stream",                       // streaming entrypoint tag
		true,                                   // local
		"localhost",                            // host
		8450,                                   // port
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	// Run streaming
	fmt.Println("Starting stream...")
	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
		"role":    "user",
		"message": "Analyze the benefits of remote work for software teams",
	})
	if err != nil {
		log.Fatalf("Failed to start stream: %v", err)
	}
	defer stream.Close()

	// Read from stream
	for {
		data, hasMore, err := stream.Next(ctx)
		if err != nil {
			log.Printf("Stream error: %v", err)
			break
		}

		if !hasMore {
			fmt.Println("Stream completed")
			break
		}

		fmt.Printf("Received: %v\n", data)
	}
}
