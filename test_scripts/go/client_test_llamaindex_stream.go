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
		"<agent_id>",  // agentID
		"math_stream", // entrypoint tag
		true,          // local
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	// Start streaming
	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
		"math_query": "What is 2 * 2?",
	})
	if err != nil {
		log.Fatalf("Failed to start stream: %v", err)
	}
	defer stream.Close()

	// Read stream
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
