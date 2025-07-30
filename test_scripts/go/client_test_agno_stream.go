// Agno Assistant Streaming Example
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
	fmt.Println("=== Agno Assistant Streaming Example ===")

	// Create client for streaming entrypoint
	agentClient, err := client.New(
		"<agent_id>",  // agentID
		"agno_stream", // entrypoint tag
		true,          // local
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	// Run streaming
	fmt.Println("Starting agno assistant stream...")
	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
		"prompt": "I want to know about chocolate",
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
