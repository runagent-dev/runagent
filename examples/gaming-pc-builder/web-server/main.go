package main

import (
	"context"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
	"github.com/runagent-dev/runagent-go/pkg/client"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for development
	},
}

type PCBuildRequest struct {
	UserQuery string `json:"user_query"`
}

type StreamData struct {
	Content   string `json:"content,omitempty"`
	Progress  string `json:"progress,omitempty"`
	Timestamp string `json:"timestamp,omitempty"`
	Type      string `json:"type"`
	Error     string `json:"error,omitempty"`
}

const htmlTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PC Builder AI Chat</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            overflow: hidden;
        }
        
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 30px rgba(0,0,0,0.2);
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .chat-header h1 {
            font-size: 1.8rem;
            margin-bottom: 5px;
        }
        
        .chat-header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .status-bar {
            background: #f8f9fa;
            padding: 10px 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }
        
        .status-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #28a745;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.disconnected {
            background: #dc3545;
            animation: none;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .clear-chat {
            background: none;
            border: 1px solid #dee2e6;
            padding: 4px 12px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 12px;
            color: #6c757d;
            transition: all 0.2s;
        }
        
        .clear-chat:hover {
            background: #f8f9fa;
            border-color: #adb5bd;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.4;
            position: relative;
            animation: fadeInUp 0.3s ease;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 6px;
        }
        
        .message.ai {
            align-self: flex-start;
            background: white;
            border: 1px solid #e9ecef;
            border-bottom-left-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .message.ai.streaming {
            border-left: 3px solid #007bff;
            background: #f8fbff;
        }
        
        .message.system {
            align-self: center;
            background: #e9ecef;
            color: #6c757d;
            font-size: 12px;
            padding: 8px 12px;
            border-radius: 12px;
            max-width: 60%;
            text-align: center;
        }
        
        .message.system.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .message.system.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .message-content {
            word-wrap: break-word;
        }
        
        .message-content h3 {
            color: #667eea;
            margin: 8px 0 6px 0;
            font-size: 1.1em;
        }
        
        .message-content h4 {
            color: #764ba2;
            margin: 6px 0 4px 0;
            font-size: 1em;
        }
        
        .message-content strong {
            color: #333;
        }
        
        .message-timestamp {
            font-size: 10px;
            opacity: 0.6;
            margin-top: 4px;
        }
        
        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 12px 16px;
            background: white;
            border-radius: 18px;
            border-bottom-left-radius: 6px;
            border: 1px solid #e9ecef;
            max-width: 80px;
            align-self: flex-start;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #adb5bd;
            animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.4;
            }
            30% {
                transform: translateY(-10px);
                opacity: 1;
            }
        }
        
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e9ecef;
        }
        
        .chat-input-form {
            display: flex;
            gap: 12px;
            align-items: flex-end;
        }
        
        .input-wrapper {
            flex: 1;
            position: relative;
        }
        
        .chat-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 20px;
            font-size: 14px;
            font-family: inherit;
            resize: none;
            max-height: 120px;
            min-height: 44px;
            transition: border-color 0.2s;
            background: #f8f9fa;
        }
        
        .chat-input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
        }
        
        .chat-input::placeholder {
            color: #adb5bd;
        }
        
        .send-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s, box-shadow 0.2s;
            font-size: 16px;
        }
        
        .send-button:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .send-button:disabled {
            background: #adb5bd;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .suggestions {
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .suggestion-chip {
            background: white;
            border: 1px solid #dee2e6;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            color: #6c757d;
        }
        
        .suggestion-chip:hover {
            background: #f8f9fa;
            border-color: #667eea;
            color: #667eea;
        }
        
        /* Scrollbar styling */
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 3px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .chat-container {
                height: 100vh;
            }
            
            .message {
                max-width: 90%;
            }
            
            .chat-header h1 {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>PC Builder AI</h1>
            <p>Your intelligent gaming PC build assistant</p>
        </div>
        
        <div class="status-bar">
            <div class="status-left">
                <div class="status-indicator disconnected" id="statusIndicator"></div>
                <span id="statusText">Disconnected</span>
            </div>
            <button class="clear-chat" onclick="clearChat()">Clear Chat</button>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message ai">
                <div class="message-content">
                    Hey! I am your PC Builder AI assistant. I can help you build the perfect gaming PC based on your needs, budget, and preferences.
                    <br><br>
                    Just tell me what you are looking for - like your budget, what games you want to play, target resolution, or any specific requirements!
                </div>
            </div>
            
            <div class="suggestions">
                <div class="suggestion-chip" onclick="sendSuggestion('Build me a 4K gaming PC under $3500')">4K Gaming Build</div>
                <div class="suggestion-chip" onclick="sendSuggestion('Budget gaming PC for 1080p under $1000')">Budget 1080p Build</div>
                <div class="suggestion-chip" onclick="sendSuggestion('High-end workstation for gaming and content creation')">Workstation Build</div>
                <div class="suggestion-chip" onclick="sendSuggestion('Upgrade recommendations for my current PC')">Upgrade Advice</div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <form class="chat-input-form" id="chatForm">
                <div class="input-wrapper">
                    <textarea 
                        class="chat-input" 
                        id="messageInput" 
                        placeholder="Ask me about building your dream gaming PC..."
                        rows="1"
                        required
                    ></textarea>
                </div>
                <button type="submit" class="send-button" id="sendButton">
                    →
                </button>
            </form>
        </div>
    </div>

    <script>
        let ws = null;
        let isProcessing = false;
        let currentStreamMessage = null;
        let accumulatedContent = '';
        
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const chatForm = document.getElementById('chatForm');
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
        
        // Handle form submission
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message && !isProcessing) {
                sendMessage(message);
            }
        });
        
        // Handle Enter key (but allow Shift+Enter for new lines)
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        function sendMessage(message) {
            // Add user message to chat
            addUserMessage(message);
            
            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Start processing
            startPCBuildAnalysis(message);
        }
        
        function sendSuggestion(suggestion) {
            sendMessage(suggestion);
        }
        
        function addUserMessage(message) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user';
            messageDiv.innerHTML = '<div class="message-content">' + escapeHtml(message) + '</div>';
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function addSystemMessage(message, type = '') {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message system ' + type;
            messageDiv.innerHTML = '<div class="message-content">' + escapeHtml(message) + '</div>';
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function showTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.id = 'typing-indicator';
            typingDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
            chatMessages.appendChild(typingDiv);
            scrollToBottom();
        }
        
        function hideTypingIndicator() {
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
        
        function startStreamingMessage() {
            hideTypingIndicator();
            
            currentStreamMessage = document.createElement('div');
            currentStreamMessage.className = 'message ai streaming';
            currentStreamMessage.innerHTML = '<div class="message-content" id="streaming-content"></div>';
            chatMessages.appendChild(currentStreamMessage);
            
            accumulatedContent = '';
            scrollToBottom();
        }
        
        function appendToStreamingMessage(content) {
            accumulatedContent += content;
            
            const contentDiv = document.getElementById('streaming-content');
            if (contentDiv) {
                let formattedContent = escapeHtml(accumulatedContent);
                
                // Basic markdown formatting
                formattedContent = formattedContent
                    .replace(/### (.*?)(\n|$)/g, '<h3>$1</h3>')
                    .replace(/#### (.*?)(\n|$)/g, '<h4>$1</h4>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n- /g, '<br>• ')
                    .replace(/\n\n/g, '<br><br>')
                    .replace(/\n/g, '<br>');
                
                contentDiv.innerHTML = formattedContent;
                scrollToBottom();
            }
        }
        
        function finishStreamingMessage() {
            if (currentStreamMessage) {
                currentStreamMessage.classList.remove('streaming');
                currentStreamMessage = null;
            }
        }
        
        function startPCBuildAnalysis(userQuery) {
            // Don't close existing connection if it's still open and working
            if (ws && ws.readyState === WebSocket.OPEN && !isProcessing) {
                // Reuse existing connection
                isProcessing = true;
                sendButton.disabled = true;
                
                showTypingIndicator();
                startStreamingMessage();
                
                const buildRequest = { user_query: userQuery };
                ws.send(JSON.stringify(buildRequest));
                return;
            }
            
            // Close old connection if exists
            if (ws) {
                ws.close();
            }
            
            isProcessing = true;
            sendButton.disabled = true;
            updateStatus('Connecting...', false);
            
            showTypingIndicator();
            
            ws = new WebSocket('ws://localhost:8080/ws');
            
            ws.onopen = function() {
                updateStatus('Connected', true);
                hideTypingIndicator();
                
                startStreamingMessage();
                
                const buildRequest = { user_query: userQuery };
                ws.send(JSON.stringify(buildRequest));
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleStreamData(data);
                } catch (e) {
                    console.error('Failed to parse message:', e);
                    addSystemMessage('Error parsing server response', 'error');
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                hideTypingIndicator();
                addSystemMessage('Connection error occurred', 'error');
                updateStatus('Error', false);
                isProcessing = false;
                sendButton.disabled = false;
            };
            
            ws.onclose = function() {
                updateStatus('Disconnected', false);
                isProcessing = false;
                sendButton.disabled = false;
                finishStreamingMessage();
            };
        }
        
        function handleStreamData(data) {
            if (data.error) {
                addSystemMessage(data.error, 'error');
                finishStreamingMessage();
                isProcessing = false;
                sendButton.disabled = false;
                return;
            }
            
            if (data.type === 'system') {
                addSystemMessage(data.content, 'success');
                finishStreamingMessage();
                isProcessing = false;
                sendButton.disabled = false;
                return;
            }
            
            if (data.content) {
                appendToStreamingMessage(data.content);
            }
        }
        
        function updateStatus(text, connected) {
            statusText.textContent = text;
            statusIndicator.className = 'status-indicator ' + (connected ? '' : 'disconnected');
        }
        
        function clearChat() {
            chatMessages.innerHTML = '' +
                '<div class="message ai">' +
                    '<div class="message-content">' +
                        'Hey! I am your PC Builder AI assistant. I can help you build the perfect gaming PC based on your needs, budget, and preferences.' +
                        '<br><br>' +
                        'Just tell me what you are looking for - like your budget, what games you want to play, target resolution, or any specific requirements!' +
                    '</div>' +
                '</div>' +
                
                '<div class="suggestions">' +
                    '<div class="suggestion-chip" onclick="sendSuggestion(\'Build me a 4K gaming PC under $3500\')">4K Gaming Build</div>' +
                    '<div class="suggestion-chip" onclick="sendSuggestion(\'Budget gaming PC for 1080p under $1000\')">Budget 1080p Build</div>' +
                    '<div class="suggestion-chip" onclick="sendSuggestion(\'High-end workstation for gaming and content creation\')">Workstation Build</div>' +
                    '<div class="suggestion-chip" onclick="sendSuggestion(\'Upgrade recommendations for my current PC\')">Upgrade Advice</div>' +
                '</div>';
            
            accumulatedContent = '';
            currentStreamMessage = null;
        }
        
        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>`

func main() {
	http.HandleFunc("/", handleHome)
	http.HandleFunc("/ws", handleWebSocket)

	fmt.Println("🎮 PC Builder AI Chat starting on http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func handleHome(w http.ResponseWriter, r *http.Request) {
	tmpl := template.Must(template.New("home").Parse(htmlTemplate))
	tmpl.Execute(w, nil)
}

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	log.Printf("New WebSocket connection established")

	// Handle multiple messages in a loop
	for {
		// Read the build request from client
		var buildRequest PCBuildRequest
		err = conn.ReadJSON(&buildRequest)
		if err != nil {
			log.Printf("Failed to read build request: %v", err)
			// Check if it's a normal close
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break // Exit the loop on any read error
		}

		log.Printf("Received build request: %s", buildRequest.UserQuery)

		// Create agent client
		agentClient, err := client.New(
			"adc86483-4aae-478e-af98-6adfcd3710a6", // Your agent ID
			"pc_builder_stream",                    // entrypoint tag
			true,                                   // local
		)
		if err != nil {
			log.Printf("Failed to create agent client: %v", err)
			conn.WriteJSON(StreamData{Type: "error", Error: "Failed to connect to PC Builder AI"})
			continue
		}

		// Create context with timeout
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)

		// Convert build request to map for agent
		requestMap := map[string]interface{}{
			"content": buildRequest.UserQuery,
			"role":    "user",
		}

		log.Printf("Sending to agent: %+v", requestMap)

		// Start streaming
		stream, err := agentClient.RunStream(ctx, requestMap)
		if err != nil {
			log.Printf("Failed to start stream: %v", err)
			conn.WriteJSON(StreamData{Type: "error", Error: "Failed to start PC build analysis"})
			cancel()
			agentClient.Close()
			continue
		}

		// Stream data to client
		completionSent := false
		streamError := false

		for {
			select {
			case <-ctx.Done():
				log.Printf("Request timeout for query: %s", buildRequest.UserQuery)
				conn.WriteJSON(StreamData{Type: "error", Error: "Request timeout"})
				streamError = true
			default:
				data, hasMore, err := stream.Next(ctx)
				if err != nil {
					log.Printf("Stream error: %v", err)
					conn.WriteJSON(StreamData{Type: "error", Error: "Stream error occurred"})
					streamError = true
					break
				}

				if !hasMore {
					// Only send completion message once
					if !completionSent && !streamError {
						conn.WriteJSON(StreamData{
							Type:      "system",
							Content:   "✅ PC build analysis completed!",
							Timestamp: time.Now().Format("15:04:05"),
						})
						completionSent = true
					}
					break
				}

				// Process stream data
				streamData := StreamData{
					Type:      "content",
					Timestamp: time.Now().Format("15:04:05"),
				}

				// Handle different data types
				switch v := data.(type) {
				case map[string]interface{}:
					if content, ok := v["content"].(string); ok && content != "" {
						streamData.Content = content
					}
					if progress, ok := v["progress"].(string); ok && progress != "" {
						streamData.Progress = progress
						streamData.Type = "progress"
					}
					if timestamp, ok := v["timestamp"].(string); ok && timestamp != "" {
						streamData.Timestamp = timestamp
					}
				case string:
					if v != "" {
						streamData.Content = v
					}
				default:
					if v != nil {
						streamData.Content = fmt.Sprintf("%v", v)
					}
				}

				// Only send if there's actual content
				if streamData.Content != "" || streamData.Progress != "" {
					if err := conn.WriteJSON(streamData); err != nil {
						log.Printf("Failed to send data to client: %v", err)
						streamError = true
						break
					}
				}
			}

			if streamError {
				break
			}
		}

		// Clean up after this request
		stream.Close()
		cancel()
		agentClient.Close()

		if streamError {
			break // Exit main loop on stream error
		}

		log.Printf("Completed processing request: %s", buildRequest.UserQuery)
	}

	log.Printf("WebSocket connection closed")
}
