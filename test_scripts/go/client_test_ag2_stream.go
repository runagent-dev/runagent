// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== Example 1: Non-Streaming ===")

// 	// Create client using the actual client package API
// 	// Using NewWithAddress since we have explicit host and port
// 	agentClient, err := client.NewWithAddress(
// 		"841debad-7433-46ae-a0ec-0540d0df7314", // agentID
// 		"minimal",                              // entrypointTag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8450,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Check if agent is healthy before running
// 	fmt.Println("Checking agent health...")
// 	healthy, err := agentClient.HealthCheck(ctx)
// 	if err != nil {
// 		log.Printf("Health check failed: %v", err)
// 		fmt.Println("This might mean:")
// 		fmt.Println("1. The agent server is not running")
// 		fmt.Println("2. The agent is not accessible at localhost:8450")
// 		fmt.Println("3. The agent is starting up and not ready yet")
// 		fmt.Println("\nTrying to proceed anyway...")
// 	} else if !healthy {
// 		log.Printf("Agent reported as unhealthy")
// 		fmt.Println("Trying to proceed anyway...")
// 	} else {
// 		fmt.Println("Agent is healthy ✓")
// 	}

// 	// Run the agent with the specified input
// 	fmt.Println("Attempting to run agent...")
// 	solutionResult, err := agentClient.Run(ctx, map[string]interface{}{
// 		"role":    "user",
// 		"message": "Analyze the benefits of remote work for software teams",
// 	})
// 	if err != nil {
// 		log.Printf("Failed to run agent: %v", err)
// 		fmt.Println("\nTroubleshooting steps:")
// 		fmt.Println("1. Make sure the agent server is running on localhost:8450")
// 		fmt.Println("2. Check if the agent ID '841debad-7433-46ae-a0ec-0540d0df7314' exists in the database")
// 		fmt.Println("3. Verify the entrypoint tag 'minimal' is correct")
// 		fmt.Println("4. Check the agent logs for any startup errors")

// 		// Try to get more info from the database
// 		fmt.Println("\nChecking database for agent info...")
// 		tryDatabaseCheck()
// 		return
// 	}

// 	fmt.Printf("Result: %v\n", solutionResult)

// 	// Optional: Get agent architecture info
// 	architecture, err := agentClient.GetAgentArchitecture(ctx)
// 	if err != nil {
// 		log.Printf("Failed to get architecture: %v", err)
// 	} else {
// 		fmt.Printf("Agent Architecture: %+v\n", architecture)
// 	}

// 	// Display client info
// 	fmt.Printf("Agent ID: %s\n", agentClient.AgentID())
// 	fmt.Printf("Entrypoint Tag: %s\n", agentClient.EntrypointTag())
// 	fmt.Printf("Is Local: %t\n", agentClient.IsLocal())
// }

// func tryDatabaseCheck() {
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Printf("Failed to initialize database: %v", err)
// 		return
// 	}
// 	defer dbService.Close()

// 	// Check if the agent exists in the database
// 	agent, err := dbService.GetAgent("841debad-7433-46ae-a0ec-0540d0df7314")
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 		return
// 	}

// 	if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 		fmt.Println("You may need to:")
// 		fmt.Println("1. Deploy the agent first")
// 		fmt.Println("2. Register the agent in the database")
// 		return
// 	}

// 	fmt.Printf("✓ Agent found in database: %s:%d (status: %s)\n", agent.Host, agent.Port, agent.Status)

// 	// List all agents for debugging
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	fmt.Printf("\nAll agents in database (%d):\n", len(agents))
// 	for _, a := range agents {
// 		fmt.Printf("  - %s (%s:%d) - %s\n", a.AgentID, a.Host, a.Port, a.Status)
// 	}
// }

// package main

// import (
// 	"encoding/json"
// 	"fmt"
// 	"log"

// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== RunAgent Database Info ===")

// 	// Initialize database service
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Fatalf("Failed to initialize database: %v", err)
// 	}
// 	defer dbService.Close()

// 	// Get specific agent info
// 	agentID := "841debad-7433-46ae-a0ec-0540d0df7314"
// 	fmt.Printf("\n🔍 Looking for agent: %s\n", agentID)

// 	agent, err := dbService.GetAgent(agentID)
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 	} else if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 	} else {
// 		fmt.Println("✅ Agent found!")
// 		printAgentInfo(agent)
// 	}

// 	// List all agents
// 	fmt.Println("\n📋 All agents in database:")
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	if len(agents) == 0 {
// 		fmt.Println("No agents found in database")
// 	} else {
// 		fmt.Printf("Found %d agents:\n", len(agents))
// 		for i, a := range agents {
// 			fmt.Printf("\n--- Agent %d ---\n", i+1)
// 			printAgentInfo(a)
// 		}
// 	}

// 	// Get capacity information
// 	fmt.Println("\n💾 Database capacity info:")
// 	capacity, err := dbService.GetCapacityInfo()
// 	if err != nil {
// 		log.Printf("Failed to get capacity info: %v", err)
// 	} else {
// 		fmt.Printf("Current agents: %d\n", capacity.CurrentCount)
// 		fmt.Printf("Max capacity: %d\n", capacity.MaxCapacity)
// 		fmt.Printf("Available slots: %d\n", capacity.MaxCapacity-capacity.CurrentCount)
// 	}
// }

// func printAgentInfo(agent *db.Agent) {
// 	fmt.Printf("Agent ID: %s\n", agent.AgentID)
// 	fmt.Printf("Path: %s\n", agent.AgentPath)
// 	fmt.Printf("Host: %s\n", agent.Host)
// 	fmt.Printf("Port: %d\n", agent.Port)
// 	fmt.Printf("Framework: %s\n", agent.Framework)
// 	fmt.Printf("Status: %s\n", agent.Status)
// 	fmt.Printf("URL: http://%s:%d\n", agent.Host, agent.Port)

// 	// Pretty print as JSON for complete info
// 	agentJSON, err := json.MarshalIndent(agent, "", "  ")
// 	if err == nil {
// 		fmt.Printf("Full details:\n%s\n", string(agentJSON))
// 	}
// }

// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// )

// func main() {
// 	fmt.Println("=== Minimal Streaming Example ===")

// 	// Create client for streaming entrypoint
// 	agentClient, err := client.NewWithAddress(
// 		"841debad-7433-46ae-a0ec-0540d0df7314", // agentID
// 		"minimal_stream",                       // streaming entrypoint tag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8450,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Run streaming
// 	fmt.Println("Starting stream...")
// 	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
// 		"role":    "user",
// 		"message": "Analyze the benefits of remote work for software teams",
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

//***************Langgraph Example***************
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== Example 1: Non-Streaming ===")

// 	// Create client using the actual client package API
// 	// Using NewWithAddress since we have explicit host and port
// 	agentClient, err := client.NewWithAddress(
// 		"dba4bf28-01f4-4517-b0b2-e7fa92d75317", // agentID
// 		"generic",                              // entrypointTag
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

// 	// Check if agent is healthy before running
// 	fmt.Println("Checking agent health...")
// 	healthy, err := agentClient.HealthCheck(ctx)
// 	if err != nil {
// 		log.Printf("Health check failed: %v", err)
// 		fmt.Println("This might mean:")
// 		fmt.Println("1. The agent server is not running")
// 		fmt.Println("2. The agent is not accessible at localhost:8450")
// 		fmt.Println("3. The agent is starting up and not ready yet")
// 		fmt.Println("\nTrying to proceed anyway...")
// 	} else if !healthy {
// 		log.Printf("Agent reported as unhealthy")
// 		fmt.Println("Trying to proceed anyway...")
// 	} else {
// 		fmt.Println("Agent is healthy ✓")
// 	}

// 	// Run the agent with the specified input
// 	fmt.Println("Attempting to run agent...")
// 	solutionResult, err := agentClient.Run(ctx, map[string]interface{}{
// 		"query":         "My phone battery is dead",
// 		"num_solutions": 4,
// 	})
// 	if err != nil {
// 		log.Printf("Failed to run agent: %v", err)
// 		fmt.Println("\nTroubleshooting steps:")
// 		fmt.Println("1. Make sure the agent server is running on localhost:8450")
// 		fmt.Println("2. Check if the agent ID '841debad-7433-46ae-a0ec-0540d0df7314' exists in the database")
// 		fmt.Println("3. Verify the entrypoint tag 'minimal' is correct")
// 		fmt.Println("4. Check the agent logs for any startup errors")

// 		// Try to get more info from the database
// 		fmt.Println("\nChecking database for agent info...")
// 		tryDatabaseCheck()
// 		return
// 	}

// 	fmt.Printf("Result: %v\n", solutionResult)

// 	// Optional: Get agent architecture info
// 	architecture, err := agentClient.GetAgentArchitecture(ctx)
// 	if err != nil {
// 		log.Printf("Failed to get architecture: %v", err)
// 	} else {
// 		fmt.Printf("Agent Architecture: %+v\n", architecture)
// 	}

// 	// Display client info
// 	fmt.Printf("Agent ID: %s\n", agentClient.AgentID())
// 	fmt.Printf("Entrypoint Tag: %s\n", agentClient.EntrypointTag())
// 	fmt.Printf("Is Local: %t\n", agentClient.IsLocal())
// }

// func tryDatabaseCheck() {
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Printf("Failed to initialize database: %v", err)
// 		return
// 	}
// 	defer dbService.Close()

// 	// Check if the agent exists in the database
// 	agent, err := dbService.GetAgent("841debad-7433-46ae-a0ec-0540d0df7314")
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 		return
// 	}

// 	if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 		fmt.Println("You may need to:")
// 		fmt.Println("1. Deploy the agent first")
// 		fmt.Println("2. Register the agent in the database")
// 		return
// 	}

// 	fmt.Printf("✓ Agent found in database: %s:%d (status: %s)\n", agent.Host, agent.Port, agent.Status)

// 	// List all agents for debugging
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	fmt.Printf("\nAll agents in database (%d):\n", len(agents))
// 	for _, a := range agents {
// 		fmt.Printf("  - %s (%s:%d) - %s\n", a.AgentID, a.Host, a.Port, a.Status)
// 	}
// }

// ********* llamaindex math Example *********
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== Example 1: Non-Streaming ===")

// 	// Create client using the actual client package API
// 	// Using NewWithAddress since we have explicit host and port
// 	agentClient, err := client.NewWithAddress(
// 		"07b5ebc6-1669-41a6-b63d-2f892d6ae834", // agentID
// 		"math_run",                             // entrypointTag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8452,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Check if agent is healthy before running
// 	fmt.Println("Checking agent health...")
// 	healthy, err := agentClient.HealthCheck(ctx)
// 	if err != nil {
// 		log.Printf("Health check failed: %v", err)
// 		fmt.Println("This might mean:")
// 		fmt.Println("1. The agent server is not running")
// 		fmt.Println("2. The agent is not accessible at localhost:8450")
// 		fmt.Println("3. The agent is starting up and not ready yet")
// 		fmt.Println("\nTrying to proceed anyway...")
// 	} else if !healthy {
// 		log.Printf("Agent reported as unhealthy")
// 		fmt.Println("Trying to proceed anyway...")
// 	} else {
// 		fmt.Println("Agent is healthy ✓")
// 	}

// 	// Run the agent with the specified input
// 	fmt.Println("Attempting to run agent...")
// 	solutionResult, err := agentClient.Run(ctx, map[string]interface{}{
// 		"math_query": "What is 2 * 2?",
// 	})
// 	if err != nil {
// 		log.Printf("Failed to run agent: %v", err)
// 		fmt.Println("\nTroubleshooting steps:")
// 		fmt.Println("1. Make sure the agent server is running on localhost:8450")
// 		fmt.Println("2. Check if the agent ID '841debad-7433-46ae-a0ec-0540d0df7314' exists in the database")
// 		fmt.Println("3. Verify the entrypoint tag 'minimal' is correct")
// 		fmt.Println("4. Check the agent logs for any startup errors")

// 		// Try to get more info from the database
// 		fmt.Println("\nChecking database for agent info...")
// 		tryDatabaseCheck()
// 		return
// 	}

// 	fmt.Printf("Result: %v\n", solutionResult)

// 	// Optional: Get agent architecture info
// 	architecture, err := agentClient.GetAgentArchitecture(ctx)
// 	if err != nil {
// 		log.Printf("Failed to get architecture: %v", err)
// 	} else {
// 		fmt.Printf("Agent Architecture: %+v\n", architecture)
// 	}

// 	// Display client info
// 	fmt.Printf("Agent ID: %s\n", agentClient.AgentID())
// 	fmt.Printf("Entrypoint Tag: %s\n", agentClient.EntrypointTag())
// 	fmt.Printf("Is Local: %t\n", agentClient.IsLocal())
// }

// func tryDatabaseCheck() {
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Printf("Failed to initialize database: %v", err)
// 		return
// 	}
// 	defer dbService.Close()

// 	// Check if the agent exists in the database
// 	agent, err := dbService.GetAgent("841debad-7433-46ae-a0ec-0540d0df7314")
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 		return
// 	}

// 	if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 		fmt.Println("You may need to:")
// 		fmt.Println("1. Deploy the agent first")
// 		fmt.Println("2. Register the agent in the database")
// 		return
// 	}

// 	fmt.Printf("✓ Agent found in database: %s:%d (status: %s)\n", agent.Host, agent.Port, agent.Status)

// 	// List all agents for debugging
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	fmt.Printf("\nAll agents in database (%d):\n", len(agents))
// 	for _, a := range agents {
// 		fmt.Printf("  - %s (%s:%d) - %s\n", a.AgentID, a.Host, a.Port, a.Status)
// 	}
// }

// ********* Crewai research  Example *********
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== Example 1: Non-Streaming ===")

// 	// Create client using the actual client package API
// 	// Using NewWithAddress since we have explicit host and port
// 	agentClient, err := client.NewWithAddress(
// 		"331fa66f-1089-43f0-8912-cc1b4c22ab01", // agentID
// 		"research_crew",                        // entrypointTag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8453,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Check if agent is healthy before running
// 	fmt.Println("Checking agent health...")
// 	healthy, err := agentClient.HealthCheck(ctx)
// 	if err != nil {
// 		log.Printf("Health check failed: %v", err)
// 		fmt.Println("This might mean:")
// 		fmt.Println("1. The agent server is not running")
// 		fmt.Println("2. The agent is not accessible at localhost:8450")
// 		fmt.Println("3. The agent is starting up and not ready yet")
// 		fmt.Println("\nTrying to proceed anyway...")
// 	} else if !healthy {
// 		log.Printf("Agent reported as unhealthy")
// 		fmt.Println("Trying to proceed anyway...")
// 	} else {
// 		fmt.Println("Agent is healthy ✓")
// 	}

// 	// Run the agent with the specified input
// 	fmt.Println("Attempting to run agent...")
// 	solutionResult, err := agentClient.Run(ctx, map[string]interface{}{
// 		"topic": "global warming",
// 	})
// 	if err != nil {
// 		log.Printf("Failed to run agent: %v", err)
// 		fmt.Println("\nTroubleshooting steps:")
// 		fmt.Println("1. Make sure the agent server is running on localhost:8450")
// 		fmt.Println("2. Check if the agent ID '841debad-7433-46ae-a0ec-0540d0df7314' exists in the database")
// 		fmt.Println("3. Verify the entrypoint tag 'minimal' is correct")
// 		fmt.Println("4. Check the agent logs for any startup errors")

// 		// Try to get more info from the database
// 		fmt.Println("\nChecking database for agent info...")
// 		tryDatabaseCheck()
// 		return
// 	}

// 	fmt.Printf("Result: %v\n", solutionResult)

// 	// Optional: Get agent architecture info
// 	architecture, err := agentClient.GetAgentArchitecture(ctx)
// 	if err != nil {
// 		log.Printf("Failed to get architecture: %v", err)
// 	} else {
// 		fmt.Printf("Agent Architecture: %+v\n", architecture)
// 	}

// 	// Display client info
// 	fmt.Printf("Agent ID: %s\n", agentClient.AgentID())
// 	fmt.Printf("Entrypoint Tag: %s\n", agentClient.EntrypointTag())
// 	fmt.Printf("Is Local: %t\n", agentClient.IsLocal())
// }

// func tryDatabaseCheck() {
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Printf("Failed to initialize database: %v", err)
// 		return
// 	}
// 	defer dbService.Close()

// 	// Check if the agent exists in the database
// 	agent, err := dbService.GetAgent("841debad-7433-46ae-a0ec-0540d0df7314")
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 		return
// 	}

// 	if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 		fmt.Println("You may need to:")
// 		fmt.Println("1. Deploy the agent first")
// 		fmt.Println("2. Register the agent in the database")
// 		return
// 	}

// 	fmt.Printf("✓ Agent found in database: %s:%d (status: %s)\n", agent.Host, agent.Port, agent.Status)

// 	// List all agents for debugging
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	fmt.Printf("\nAll agents in database (%d):\n", len(agents))
// 	for _, a := range agents {
// 		fmt.Printf("  - %s (%s:%d) - %s\n", a.AgentID, a.Host, a.Port, a.Status)
// 	}
// }

// ********* Agno default  Example *********
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== Example 1: Non-Streaming ===")

// 	// Create client using the actual client package API
// 	// Using NewWithAddress since we have explicit host and port
// 	agentClient, err := client.NewWithAddress(
// 		"0a0765df-96d4-4884-90b8-74a6c3632010", // agentID
// 		"agno_assistant",                       // entrypointTag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8453,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Check if agent is healthy before running
// 	fmt.Println("Checking agent health...")
// 	healthy, err := agentClient.HealthCheck(ctx)
// 	if err != nil {
// 		log.Printf("Health check failed: %v", err)
// 		fmt.Println("This might mean:")
// 		fmt.Println("1. The agent server is not running")
// 		fmt.Println("2. The agent is not accessible at localhost:8450")
// 		fmt.Println("3. The agent is starting up and not ready yet")
// 		fmt.Println("\nTrying to proceed anyway...")
// 	} else if !healthy {
// 		log.Printf("Agent reported as unhealthy")
// 		fmt.Println("Trying to proceed anyway...")
// 	} else {
// 		fmt.Println("Agent is healthy ✓")
// 	}

// 	// Run the agent with the specified input
// 	fmt.Println("Attempting to run agent...")
// 	solutionResult, err := agentClient.Run(ctx, map[string]interface{}{
// 		"prompt": "I want to know abour chocklate",
// 	})
// 	if err != nil {
// 		log.Printf("Failed to run agent: %v", err)
// 		fmt.Println("\nTroubleshooting steps:")
// 		fmt.Println("1. Make sure the agent server is running on localhost:8450")
// 		fmt.Println("2. Check if the agent ID '841debad-7433-46ae-a0ec-0540d0df7314' exists in the database")
// 		fmt.Println("3. Verify the entrypoint tag 'minimal' is correct")
// 		fmt.Println("4. Check the agent logs for any startup errors")

// 		// Try to get more info from the database
// 		fmt.Println("\nChecking database for agent info...")
// 		tryDatabaseCheck()
// 		return
// 	}

// 	fmt.Printf("Result: %v\n", solutionResult)

// 	// Optional: Get agent architecture info
// 	architecture, err := agentClient.GetAgentArchitecture(ctx)
// 	if err != nil {
// 		log.Printf("Failed to get architecture: %v", err)
// 	} else {
// 		fmt.Printf("Agent Architecture: %+v\n", architecture)
// 	}

// 	// Display client info
// 	fmt.Printf("Agent ID: %s\n", agentClient.AgentID())
// 	fmt.Printf("Entrypoint Tag: %s\n", agentClient.EntrypointTag())
// 	fmt.Printf("Is Local: %t\n", agentClient.IsLocal())
// }

// func tryDatabaseCheck() {
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Printf("Failed to initialize database: %v", err)
// 		return
// 	}
// 	defer dbService.Close()

// 	// Check if the agent exists in the database
// 	agent, err := dbService.GetAgent("841debad-7433-46ae-a0ec-0540d0df7314")
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 		return
// 	}

// 	if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 		fmt.Println("You may need to:")
// 		fmt.Println("1. Deploy the agent first")
// 		fmt.Println("2. Register the agent in the database")
// 		return
// 	}

// 	fmt.Printf("✓ Agent found in database: %s:%d (status: %s)\n", agent.Host, agent.Port, agent.Status)

// 	// List all agents for debugging
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	fmt.Printf("\nAll agents in database (%d):\n", len(agents))
// 	for _, a := range agents {
// 		fmt.Printf("  - %s (%s:%d) - %s\n", a.AgentID, a.Host, a.Port, a.Status)
// 	}
// }

// ********* ag2 default  Example *********
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// 	"github.com/runagent-dev/runagent-go/pkg/db"
// )

// func main() {
// 	fmt.Println("=== Example 1: Non-Streaming ===")

// 	// Create client using the actual client package API
// 	// Using NewWithAddress since we have explicit host and port
// 	agentClient, err := client.NewWithAddress(
// 		"7c8c54d0-297b-4c63-86ae-38326a882067", // agentID
// 		"ag2_invoke",                           // entrypointTag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8453,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Check if agent is healthy before running
// 	fmt.Println("Checking agent health...")
// 	healthy, err := agentClient.HealthCheck(ctx)
// 	if err != nil {
// 		log.Printf("Health check failed: %v", err)
// 		fmt.Println("This might mean:")
// 		fmt.Println("1. The agent server is not running")
// 		fmt.Println("2. The agent is not accessible at localhost:8450")
// 		fmt.Println("3. The agent is starting up and not ready yet")
// 		fmt.Println("\nTrying to proceed anyway...")
// 	} else if !healthy {
// 		log.Printf("Agent reported as unhealthy")
// 		fmt.Println("Trying to proceed anyway...")
// 	} else {
// 		fmt.Println("Agent is healthy ✓")
// 	}

// 	// Run the agent with the specified input
// 	fmt.Println("Attempting to run agent...")
// 	solutionResult, err := agentClient.Run(ctx, map[string]interface{}{
// 		"message":   "The capital of bd is dhaka",
// 		"max_turns": 4,
// 	})
// 	if err != nil {
// 		log.Printf("Failed to run agent: %v", err)
// 		fmt.Println("\nTroubleshooting steps:")
// 		fmt.Println("1. Make sure the agent server is running on localhost:8450")
// 		fmt.Println("2. Check if the agent ID '841debad-7433-46ae-a0ec-0540d0df7314' exists in the database")
// 		fmt.Println("3. Verify the entrypoint tag 'minimal' is correct")
// 		fmt.Println("4. Check the agent logs for any startup errors")

// 		// Try to get more info from the database
// 		fmt.Println("\nChecking database for agent info...")
// 		tryDatabaseCheck()
// 		return
// 	}

// 	fmt.Printf("Result: %v\n", solutionResult)

// 	// Optional: Get agent architecture info
// 	architecture, err := agentClient.GetAgentArchitecture(ctx)
// 	if err != nil {
// 		log.Printf("Failed to get architecture: %v", err)
// 	} else {
// 		fmt.Printf("Agent Architecture: %+v\n", architecture)
// 	}

// 	// Display client info
// 	fmt.Printf("Agent ID: %s\n", agentClient.AgentID())
// 	fmt.Printf("Entrypoint Tag: %s\n", agentClient.EntrypointTag())
// 	fmt.Printf("Is Local: %t\n", agentClient.IsLocal())
// }

// func tryDatabaseCheck() {
// 	dbService, err := db.NewService("")
// 	if err != nil {
// 		log.Printf("Failed to initialize database: %v", err)
// 		return
// 	}
// 	defer dbService.Close()

// 	// Check if the agent exists in the database
// 	agent, err := dbService.GetAgent("841debad-7433-46ae-a0ec-0540d0df7314")
// 	if err != nil {
// 		log.Printf("Failed to get agent from database: %v", err)
// 		return
// 	}

// 	if agent == nil {
// 		fmt.Println("❌ Agent not found in database")
// 		fmt.Println("You may need to:")
// 		fmt.Println("1. Deploy the agent first")
// 		fmt.Println("2. Register the agent in the database")
// 		return
// 	}

// 	fmt.Printf("✓ Agent found in database: %s:%d (status: %s)\n", agent.Host, agent.Port, agent.Status)

// 	// List all agents for debugging
// 	agents, err := dbService.ListAgents()
// 	if err != nil {
// 		log.Printf("Failed to list agents: %v", err)
// 		return
// 	}

// 	fmt.Printf("\nAll agents in database (%d):\n", len(agents))
// 	for _, a := range agents {
// 		fmt.Printf("  - %s (%s:%d) - %s\n", a.AgentID, a.Host, a.Port, a.Status)
// 	}
// }

// ********* autogen default  Example *********
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// )

// func main() {
// 	// Create client
// 	agentClient, err := client.NewWithAddress(
// 		"f285ecb8-a2fc-4b9c-840d-1795386b84cd", // agentID
// 		"autogen_invoke",                       // entrypointTag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8453,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Run the agent
// 	result, err := agentClient.Run(ctx, map[string]interface{}{
// 		"task": "what is autogen",
// 	})
// 	if err != nil {
// 		log.Fatalf("Failed to run agent: %v", err)
// 	}

// 	fmt.Printf("Result: %v\n", result)
// }

// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// )

// func main() {
// 	fmt.Println("=== Math Agent Streaming Example ===")

// 	// Create client for streaming entrypoint
// 	agentClient, err := client.NewWithAddress(
// 		"07b5ebc6-1669-41a6-b63d-2f892d6ae834", // agentID
// 		"math_stream",                          // Keep original entrypoint tag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8452,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Run streaming
// 	fmt.Println("Starting math calculation stream...")
// 	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
// 		"math_query": "What is 2 * 2?",
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

// // Agno Assistant Streaming Example
// package main

// import (
// 	"context"
// 	"fmt"
// 	"log"
// 	"time"

// 	"github.com/runagent-dev/runagent-go/pkg/client"
// )

// func main() {
// 	fmt.Println("=== Agno Assistant Streaming Example ===")

// 	// Create client for streaming entrypoint
// 	agentClient, err := client.NewWithAddress(
// 		"47d63228-cc58-43d9-a512-d3583f8bf019", // agentID
// 		"agno_stream",                          // entrypoint tag
// 		true,                                   // local
// 		"localhost",                            // host
// 		8450,                                   // port
// 	)
// 	if err != nil {
// 		log.Fatalf("Failed to create client: %v", err)
// 	}
// 	defer agentClient.Close()

// 	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
// 	defer cancel()

// 	// Run streaming
// 	fmt.Println("Starting agno assistant stream...")
// 	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
// 		"prompt": "I want to know about chocolate",
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

package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
	fmt.Println("=== AG2 Invoke Streaming Example ===")

	// Create client for streaming entrypoint
	agentClient, err := client.NewWithAddress(
		"6d9a6fb8-a58c-49de-92ef-cd64d53da932", // agentID
		"ag2_stream",                           // entrypoint tag
		true,                                   // local
		"localhost",                            // host
		8451,                                   // port
	)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer agentClient.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	// Run streaming
	fmt.Println("Starting AG2 invoke stream...")
	stream, err := agentClient.RunStream(ctx, map[string]interface{}{
		"message":   "The capital of bd is dhaka",
		"max_turns": 4,
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
