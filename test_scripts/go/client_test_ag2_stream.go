// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// )

// func main() {
// 	fmt.Println("=== AG2 Invoke Streaming Example ===")

// 	// Create client for streaming entrypoint
// 	agentClient, err := client.NewWithAddress(
// 		"6d9a6fb8-a58c-49de-92ef-cd64d53da932", // agentID
// 		"ag2_stream",                           // entrypoint tag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8451,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Run streaming
// 	fmt.Println("Starting AG2 invoke stream...")
// 	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
// 		"message":   "The capital of bd is dhaka",
// 		"max_turns": 4,
// 	})
// 	if err != nil {
// 		log.Fatalf("Failed to start stream: %v", err)
// 	}
// 	defer stream.Close()

// 	// Read from stream
// 	for {
// 		data, hasMore, err := stream.Next(ctx)
// 		if err != nil {
// 			log.Printf("Stream error: %v", err)
// 			break
// 		}

// 		if !hasMore {
// 			fmt.Println("Stream completed")
// 			break
// 		}

// 		fmt.Printf("Received: %v\n", data)
// 	}
// }
