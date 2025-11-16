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

		// Uniform error detection across frame shapes - panic immediately on error frames
		if len(frame.Error) > 0 && string(frame.Error) != "null" {
			err := newExecutionError(0, enrichErrorPayload(parseFrameError(frame)))
			s.Close()
			panic(formatFriendlyError(err))
		}
		if strings.EqualFold(frame.Type, "error") {
			err := newExecutionError(0, enrichErrorPayload(parseFrameError(frame)))
			s.Close()
			panic(formatFriendlyError(err))
		}
		// Detect status strings that indicate failure - panic immediately
		if frame.Status != "" {
			status := strings.ToLower(frame.Status)
			if strings.Contains(status, "error") || strings.Contains(status, "fail") || strings.Contains(status, "failed") {
				err := newExecutionError(0, enrichErrorPayload(parseFrameError(frame)))
				s.Close()
				panic(formatFriendlyError(err))
			}
		}

		switch strings.ToLower(frame.Type) {
		case "status":
			status := strings.ToLower(frame.Status)
			switch status {
			case "stream_started":
				continue
			case "error", "stream_error", "failed", "stream_failed":
				err := newExecutionError(0, enrichErrorPayload(parseFrameError(frame)))
				s.Close()
				panic(formatFriendlyError(err))
			case "stream_completed":
				s.Close()
				return nil, false, nil
			default:
				continue
			}
		case "error":
			err := newExecutionError(0, enrichErrorPayload(parseFrameError(frame)))
			s.Close()
			panic(formatFriendlyError(err))
		case "data":
			payload, err := decodeStreamPayload(frame)
			if err != nil {
				s.Close()
				return nil, false, err
			}
			// If the payload itself encodes an error object, panic immediately
			if m, ok := payload.(map[string]interface{}); ok {
				// Some servers put error info inside the data envelope
				if rawErr, ok := m["error"]; ok && rawErr != nil {
					api := enrichErrorPayload(parseAPIError(rawErr))
					err := newExecutionError(0, api)
					s.Close()
					panic(formatFriendlyError(err))
				}
				if t, ok := m["type"].(string); ok && strings.EqualFold(t, "error") {
					// try to lift message/suggestion if present
					api := &apiErrorPayload{
						Type:    ErrorTypeServer,
						Message: fmt.Sprint(m["message"]),
						Code:    fmt.Sprint(m["code"]),
					}
					err := newExecutionError(0, enrichErrorPayload(api))
					s.Close()
					panic(formatFriendlyError(err))
				}
			}
			return payload, true, nil
		default:
			// Treat unknown types as data for forward compatibility.
			payload, err := decodeStreamPayload(frame)
			if err != nil {
				s.Close()
				return nil, false, err
			}
			// Also inspect unknown payloads for embedded errors - panic immediately
			if m, ok := payload.(map[string]interface{}); ok {
				if rawErr, ok := m["error"]; ok && rawErr != nil {
					api := enrichErrorPayload(parseAPIError(rawErr))
					err := newExecutionError(0, api)
					s.Close()
					panic(formatFriendlyError(err))
				}
				if t, ok := m["type"].(string); ok && strings.EqualFold(t, "error") {
					api := &apiErrorPayload{
						Type:    ErrorTypeServer,
						Message: fmt.Sprint(m["message"]),
						Code:    fmt.Sprint(m["code"]),
					}
					err := newExecutionError(0, enrichErrorPayload(api))
					s.Close()
					panic(formatFriendlyError(err))
				}
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

// NextOrPanic is a convenience wrapper that panics on error with a user-friendly message.
// Use this only in quickstarts or CLI-like apps where panicking is acceptable behavior.
func (s *StreamIterator) NextOrPanic(ctx context.Context) interface{} {
	chunk, more, err := s.Next(ctx)
	if err != nil {
		panic(formatFriendlyError(err))
	}
	if !more {
		panic("RunAgent stream: terminated unexpectedly before completion")
	}
	return chunk
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
		// payload-aware normalization
		decoded := decodeStructuredObject(v)
		return decoded, nil
	default:
		// If the payload is a stringified structured object, decode it
		if str, ok := v.(string); ok {
			decoded := decodeStructuredString(str)
			// If decoded is a map with payload, normalize it
			if m, isMap := decoded.(map[string]interface{}); isMap {
				n := decodeStructuredObject(m)
				return n, nil
			}
			return decoded, nil
		}
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
