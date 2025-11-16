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

	client, err := runagent.NewRunAgentClient(runagent.Config{
		AgentID:       "841debad-7433-46ae-a0ec-0540d0df7314",
		EntrypointTag: "minimal_stream",
		Host:          "localhost",
		Port:          8450,
		Local:         runagent.Bool(true),
	})
	if err != nil {
		log.Fatalf("failed to create client: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	stream, err := client.RunStream(ctx,
		runagent.Kw("role", "user"),
		runagent.Kw("message", "Write a detailed analysis of remote work benefits for software development teams"),
	)
	if err != nil {
		log.Fatalf("Failed to start streaming: %v", err)
	}
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
