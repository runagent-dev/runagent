//! Port management utilities for allocating available ports

use crate::constants::{DEFAULT_PORT_START, DEFAULT_PORT_END};
use crate::types::{RunAgentError, RunAgentResult};
use std::net::{SocketAddr, TcpListener};

/// Port manager for finding and allocating available ports
pub struct PortManager;

impl PortManager {
    /// Check if a specific port is available on the given host
    pub fn is_port_available(host: &str, port: u16) -> bool {
        let addr = format!("{}:{}", host, port);
        
        if let Ok(socket_addr) = addr.parse::<SocketAddr>() {
            TcpListener::bind(socket_addr).is_ok()
        } else {
            false
        }
    }

    /// Find the next available port starting from a given port
    pub fn find_available_port(host: &str, start_port: u16) -> RunAgentResult<u16> {
        for port in start_port..=DEFAULT_PORT_END {
            if Self::is_port_available(host, port) {
                return Ok(port);
            }
        }
        
        Err(RunAgentError::connection(format!(
            "No available ports found in range {}-{}",
            start_port, DEFAULT_PORT_END
        )))
    }

    /// Allocate a unique host:port combination, avoiding used ports
    pub fn allocate_unique_address(used_ports: &[u16]) -> RunAgentResult<(String, u16)> {
        let host = "127.0.0.1".to_string();
        
        for port in DEFAULT_PORT_START..=DEFAULT_PORT_END {
            if !used_ports.contains(&port) && Self::is_port_available(&host, port) {
                return Ok((host, port));
            }
        }
        
        Err(RunAgentError::connection(
            "No available ports found for allocation".to_string()
        ))
    }

    /// Get a list of available ports in the default range
    pub fn get_available_ports(host: &str, count: usize) -> Vec<u16> {
        let mut available_ports = Vec::new();
        
        for port in DEFAULT_PORT_START..=DEFAULT_PORT_END {
            if Self::is_port_available(host, port) {
                available_ports.push(port);
                if available_ports.len() >= count {
                    break;
                }
            }
        }
        
        available_ports
    }

    /// Check if any port in a range is available
    pub fn has_available_ports(host: &str, start_port: u16, end_port: u16) -> bool {
        for port in start_port..=end_port {
            if Self::is_port_available(host, port) {
                return true;
            }
        }
        false
    }

    /// Get port usage statistics for a range
    pub fn get_port_usage_stats(host: &str) -> PortUsageStats {
        let mut available_count = 0;
        let mut used_count = 0;
        
        for port in DEFAULT_PORT_START..=DEFAULT_PORT_END {
            if Self::is_port_available(host, port) {
                available_count += 1;
            } else {
                used_count += 1;
            }
        }
        
        let total_ports = (DEFAULT_PORT_END - DEFAULT_PORT_START + 1) as usize;
        
        PortUsageStats {
            total_ports,
            available_count,
            used_count,
            usage_percentage: (used_count as f64 / total_ports as f64) * 100.0,
            start_port: DEFAULT_PORT_START,
            end_port: DEFAULT_PORT_END,
        }
    }
}

/// Port usage statistics
#[derive(Debug, Clone)]
pub struct PortUsageStats {
    /// Total number of ports in the range
    pub total_ports: usize,
    /// Number of available ports
    pub available_count: usize,
    /// Number of used ports
    pub used_count: usize,
    /// Percentage of ports that are used
    pub usage_percentage: f64,
    /// Start of the port range
    pub start_port: u16,
    /// End of the port range
    pub end_port: u16,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_port_available() {
        // Test with a likely available port
        assert!(PortManager::is_port_available("127.0.0.1", 0)); // Port 0 lets OS choose
        
        // Test with an invalid host
        assert!(!PortManager::is_port_available("invalid.host", 8080));
    }

    #[test]
    fn test_find_available_port() {
        let result = PortManager::find_available_port("127.0.0.1", DEFAULT_PORT_START);
        assert!(result.is_ok());
        
        if let Ok(port) = result {
            assert!(port >= DEFAULT_PORT_START);
            assert!(port <= DEFAULT_PORT_END);
        }
    }

    #[test]
    fn test_allocate_unique_address() {
        let used_ports = vec![8450, 8451, 8452]; // Some used ports
        let result = PortManager::allocate_unique_address(&used_ports);
        
        assert!(result.is_ok());
        
        if let Ok((host, port)) = result {
            assert_eq!(host, "127.0.0.1");
            assert!(!used_ports.contains(&port));
            assert!(port >= DEFAULT_PORT_START);
            assert!(port <= DEFAULT_PORT_END);
        }
    }

    #[test]
    fn test_get_available_ports() {
        let available_ports = PortManager::get_available_ports("127.0.0.1", 5);
        assert!(available_ports.len() <= 5);
        
        // All returned ports should be in the valid range
        for port in available_ports {
            assert!(port >= DEFAULT_PORT_START);
            assert!(port <= DEFAULT_PORT_END);
        }
    }

    #[test]
    fn test_has_available_ports() {
        let has_ports = PortManager::has_available_ports("127.0.0.1", DEFAULT_PORT_START, DEFAULT_PORT_END);
        assert!(has_ports); // Should have some available ports
        
        // Test with impossible range
        let no_ports = PortManager::has_available_ports("invalid.host", 1, 1);
        assert!(!no_ports);
    }

    #[test]
    fn test_get_port_usage_stats() {
        let stats = PortManager::get_port_usage_stats("127.0.0.1");
        
        assert_eq!(stats.start_port, DEFAULT_PORT_START);
        assert_eq!(stats.end_port, DEFAULT_PORT_END);
        assert_eq!(stats.total_ports, (DEFAULT_PORT_END - DEFAULT_PORT_START + 1) as usize);
        assert_eq!(stats.available_count + stats.used_count, stats.total_ports);
        assert!(stats.usage_percentage >= 0.0);
        assert!(stats.usage_percentage <= 100.0);
    }
}