package runagent

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/gorilla/websocket"
)

// StreamIterator provides a blocking iterator over streaming responses.
type StreamIterator struct {
	conn   *websocket.Conn
	closed bool
}

func newStreamIterator(conn *websocket.Conn) *StreamIterator {
	return &StreamIterator{conn: conn}
}

// Next blocks until the next chunk is available. The boolean indicates whether more data is expected.
func (s *StreamIterator) Next(ctx context.Context) (interface{}, bool, error) {
	if s.closed {
		return nil, false, nil
	}

	for {
		select {
		case <-ctx.Done():
			s.Close()
			return nil, false, ctx.Err()
		default:
		}

		_, msg, err := s.conn.ReadMessage()
		if err != nil {
			s.Close()
			return nil, false, newError(
				ErrorTypeConnection,
				"failed to read stream message",
				withCause(err),
			)
		}

		var frame streamFrame
		if err := json.Unmarshal(msg, &frame); err != nil {
			s.Close()
			return nil, false, newError(ErrorTypeServer, "invalid stream message", withCause(err))
		}

		switch strings.ToLower(frame.Type) {
		case "status":
			status := strings.ToLower(frame.Status)
			switch status {
			case "stream_started":
				continue
			case "stream_completed":
				s.Close()
				return nil, false, nil
			default:
				continue
			}
		case "error":
			s.Close()
			return nil, false, newExecutionError(0, parseFrameError(frame))
		case "data":
			payload, err := decodeStreamPayload(frame)
			if err != nil {
				s.Close()
				return nil, false, err
			}
			return payload, true, nil
		default:
			// Treat unknown types as data for forward compatibility.
			payload, err := decodeStreamPayload(frame)
			if err != nil {
				s.Close()
				return nil, false, err
			}
			return payload, true, nil
		}
	}
}

// Close terminates the underlying WebSocket connection.
func (s *StreamIterator) Close() error {
	if s.closed {
		return nil
	}
	s.closed = true
	return s.conn.Close()
}

func decodeStreamPayload(frame streamFrame) (interface{}, error) {
	raw := frame.Content
	if len(raw) == 0 {
		raw = frame.Data
	}
	if len(raw) == 0 {
		return nil, nil
	}

	var payload interface{}
	if err := json.Unmarshal(raw, &payload); err != nil {
		// Fall back to raw string.
		return string(raw), nil
	}

	switch v := payload.(type) {
	case map[string]interface{}:
		// Some servers send { "type": "data", "data": { "content": ... } }
		if content, ok := v["content"]; ok {
			return content, nil
		}
		return v, nil
	default:
		return v, nil
	}
}

func parseFrameError(frame streamFrame) *apiErrorPayload {
	if len(frame.Error) == 0 {
		return &apiErrorPayload{
			Type:    ErrorTypeServer,
			Message: "stream failed",
		}
	}

	var payload interface{}
	if err := json.Unmarshal(frame.Error, &payload); err != nil {
		return &apiErrorPayload{
			Type:    ErrorTypeServer,
			Message: fmt.Sprintf("stream error: %s", string(frame.Error)),
		}
	}

	return parseAPIError(payload)
}
