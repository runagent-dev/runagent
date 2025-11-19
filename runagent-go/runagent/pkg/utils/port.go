package utils

import (
	"fmt"
	"net"

	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/constants"
)

// PortManager manages port allocation
type PortManager struct{}

// NewPortManager creates a new port manager
func NewPortManager() *PortManager {
	return &PortManager{}
}

// IsPortAvailable checks if a port is available
func (pm *PortManager) IsPortAvailable(host string, port int) bool {
	address := fmt.Sprintf("%s:%d", host, port)
	listener, err := net.Listen("tcp", address)
	if err != nil {
		return false
	}
	listener.Close()
	return true
}

// FindAvailablePort finds the next available port starting from the given port
func (pm *PortManager) FindAvailablePort(host string, startPort int) (int, error) {
	for port := startPort; port <= constants.DefaultPortEnd; port++ {
		if pm.IsPortAvailable(host, port) {
			return port, nil
		}
	}
	return 0, fmt.Errorf("no available ports found in range %d-%d", startPort, constants.DefaultPortEnd)
}

// AllocateUniqueAddress allocates a unique host:port combination
func (pm *PortManager) AllocateUniqueAddress(usedPorts []int) (string, int, error) {
	host := "127.0.0.1"

	for port := constants.DefaultPortStart; port <= constants.DefaultPortEnd; port++ {
		// Check if port is in used list
		used := false
		for _, usedPort := range usedPorts {
			if port == usedPort {
				used = true
				break
			}
		}

		if !used && pm.IsPortAvailable(host, port) {
			return host, port, nil
		}
	}

	return "", 0, fmt.Errorf("no available ports found for allocation")
}
