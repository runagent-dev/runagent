// AutoGen Streaming Example
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
	fmt.Println("=== AutoGen Streaming Example ===")

	// Create client for streaming entrypoint
	agentClient, err := client.New(
		"<agent_id>",           // agentID
		"autogen_token_stream", // entrypoint tag (changed from autogen_invoke to autogen_stream)
		true,                   // local
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	// Run streaming
	fmt.Println("Starting AutoGen streaming conversation...")
	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
		"task": "What is autogen and how does it work?",
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

		// Handle different types of streaming data
		if dataMap, ok := data.(map[string]interface{}); ok {
			switch dataMap["type"] {
			case "status":
				fmt.Printf("Status: %v\n", dataMap["message"])
			case "message":
				fmt.Printf("Turn %v - %s: %v\n",
					dataMap["turn"],
					dataMap["sender"],
					dataMap["content"])
			case "summary":
				fmt.Printf("Summary - Total turns: %v\n", dataMap["total_turns"])
				fmt.Printf("Final result: %v\n", dataMap["final_result"])
			case "error":
				fmt.Printf("Error: %v\n", dataMap["message"])
			case "complete":
				fmt.Println("Conversation completed successfully")
			default:
				fmt.Printf("Received: %v\n", data)
			}
		} else {
			fmt.Printf("Received: %v\n", data)
		}
	}
}
