//! Core serialization logic for the RunAgent SDK

use crate::types::{RunAgentError, RunAgentResult, SafeMessage};
use serde_json::Value;
use std::collections::HashMap;

/// Core serializer for handling object serialization and deserialization
#[derive(Clone)]
pub struct CoreSerializer {
    max_size_bytes: usize,
}

impl CoreSerializer {
    /// Create a new CoreSerializer with specified size limit
    pub fn new(max_size_mb: f64) -> RunAgentResult<Self> {
        Ok(Self {
            max_size_bytes: (max_size_mb * 1024.0 * 1024.0) as usize,
        })
    }

    /// Serialize an object to JSON string
    pub fn serialize_object(&self, obj: Value) -> RunAgentResult<String> {
        let serialized_data = self.try_serialize_strategies(obj)?;
        let json_str = serde_json::to_string(&serialized_data)?;

        if !self.check_size_limit(&json_str) {
            tracing::warn!("Serialized object exceeds size limit: {} bytes", json_str.len());
        }

        Ok(json_str)
    }

    /// Prepare value for deserialization
    /// 
    /// If the value is a JSON string, parses it first.
    /// Otherwise returns the value as-is.
    /// This handles cases where responses come as JSON strings.
    pub fn prepare_for_deserialization(&self, value: Value) -> Value {
        if let Some(str_val) = value.as_str() {
            // Try to parse as JSON first
            match serde_json::from_str::<Value>(str_val) {
                Ok(parsed) => parsed,
                Err(_) => value, // Not JSON, return as-is
            }
        } else {
            value // Already parsed
        }
    }

    /// Deserialize JSON response to object
    /// 
    /// Handles multiple response formats:
    /// 1. `{type, payload}` structure - extracts and deserializes payload
    /// 2. String payload - parses JSON string
    /// 3. Direct value - reconstructs nested JSON
    /// 
    /// Handles multiple response formats including `{type, payload}` structures.
    pub fn deserialize_object(&self, json_resp: Value) -> RunAgentResult<Value> {
        // Handle {type, payload} structure
        if let Value::Object(ref map) = json_resp {
            if map.contains_key("type") && map.contains_key("payload") {
                let payload_val = map.get("payload").unwrap();
                
                // If payload is a string, try to parse it as JSON
                if let Some(payload_str) = payload_val.as_str() {
                    // The payload is a JSON-encoded string, parse it to get the actual value
                    // Example: payload_str = "\"Hello\"" -> parsed = "Hello"
                    match serde_json::from_str::<Value>(payload_str) {
                        Ok(parsed) => {
                            // Parse succeeded - return the parsed value
                            return Ok(parsed);
                        }
                        Err(_) => {
                            // Parse failed - return the string as-is
                            return Ok(Value::String(payload_str.to_string()));
                        }
                    }
                }
                
                // Payload is not a string - reconstruct it directly
                return self.reconstruct_nested_json(payload_val.clone());
            }
            
            // Handle {content} structure (legacy format)
            if let Some(content) = map.get("content") {
                return self.reconstruct_nested_json(content.clone());
            }
        }
        
        // If it's a string, try to parse it first
        if let Some(str_val) = json_resp.as_str() {
            match serde_json::from_str::<Value>(str_val) {
                Ok(parsed) => return self.reconstruct_nested_json(parsed),
                Err(_) => return Ok(Value::String(str_val.to_string())),
            }
        }
        
        // Default: reconstruct nested JSON
        self.reconstruct_nested_json(json_resp)
    }

    /// Serialize SafeMessage to JSON string
    pub fn serialize_message(&self, message: &SafeMessage) -> RunAgentResult<String> {
        let message_dict = message.to_dict();
        
        // Deep serialize the data field to handle nested objects
        let mut serialized_dict = message_dict;
        if let Some(data) = serialized_dict.get("data") {
            serialized_dict.insert("data".to_string(), self.deep_serialize_value(data.clone())?);
        }
        
        if let Some(metadata) = serialized_dict.get("metadata") {
            serialized_dict.insert("metadata".to_string(), self.deep_serialize_value(metadata.clone())?);
        }

        let json_str = serde_json::to_string(&serialized_dict)?;

        if !self.check_size_limit(&json_str) {
            tracing::warn!("Serialized message exceeds size limit: {} bytes", json_str.len());
        }

        Ok(json_str)
    }

    /// Deserialize JSON string to SafeMessage
    pub fn deserialize_message(&self, json_str: &str) -> RunAgentResult<SafeMessage> {
        let deserialized_data: Value = serde_json::from_str(json_str)?;
        
        let obj = deserialized_data.as_object()
            .ok_or_else(|| RunAgentError::validation("JSON must deserialize to an object"))?;

        // Reconstruct nested JSON structures in data and metadata
        let mut message_data = obj.clone();
        
        if let Some(data) = message_data.get("data") {
            message_data.insert("data".to_string(), self.reconstruct_nested_json(data.clone())?);
        }
        
        if let Some(metadata) = message_data.get("metadata") {
            message_data.insert("metadata".to_string(), self.reconstruct_nested_json(metadata.clone())?);
        }

        let safe_message: SafeMessage = serde_json::from_value(Value::Object(message_data.into()))?;
        Ok(safe_message)
    }

    /// Check if serialized data exceeds size limit
    pub fn check_size_limit(&self, json_str: &str) -> bool {
        json_str.len() <= self.max_size_bytes
    }

    /// Try multiple serialization strategies
    fn try_serialize_strategies(&self, obj: Value) -> RunAgentResult<HashMap<String, Value>> {
        // Strategy 1: Direct JSON serializable
        if self.is_json_serializable(&obj) {
            return Ok(self.create_response("direct", obj));
        }

        // Strategy 2: Convert to string representation
        let str_repr = self.value_to_string(&obj);
        Ok(self.create_response_with_metadata("string_repr", Value::String(str_repr), &obj))
    }

    /// Check if a value is directly JSON serializable
    fn is_json_serializable(&self, obj: &Value) -> bool {
        // JSON values are already serializable by definition
        match obj {
            Value::Null | Value::Bool(_) | Value::Number(_) | Value::String(_) => true,
            Value::Array(arr) => arr.iter().all(|item| self.is_json_serializable(item)),
            Value::Object(map) => map.values().all(|value| self.is_json_serializable(value)),
        }
    }

    /// Convert value to string representation
    fn value_to_string(&self, obj: &Value) -> String {
        match obj {
            Value::String(s) => s.clone(),
            _ => serde_json::to_string(obj).unwrap_or_else(|_| format!("<Unserializable {:?}>", obj)),
        }
    }

    /// Create a serialization response
    fn create_response(&self, strategy: &str, content: Value) -> HashMap<String, Value> {
        let mut response = HashMap::new();
        response.insert("content".to_string(), content);
        response.insert("strategy".to_string(), Value::String(strategy.to_string()));
        response
    }

    /// Create a serialization response with metadata
    fn create_response_with_metadata(&self, strategy: &str, content: Value, original: &Value) -> HashMap<String, Value> {
        let mut response = self.create_response(strategy, content);
        response.insert("type".to_string(), Value::String(self.get_value_type(original)));
        response.insert("metadata".to_string(), self.extract_metadata(original));
        response
    }

    /// Get value type as string
    fn get_value_type(&self, obj: &Value) -> String {
        match obj {
            Value::Null => "null".to_string(),
            Value::Bool(_) => "boolean".to_string(),
            Value::Number(_) => "number".to_string(),
            Value::String(_) => "string".to_string(),
            Value::Array(_) => "array".to_string(),
            Value::Object(_) => "object".to_string(),
        }
    }

    /// Extract metadata about the value
    fn extract_metadata(&self, obj: &Value) -> Value {
        let mut metadata = HashMap::new();
        
        let obj_str = serde_json::to_string(obj).unwrap_or_default();
        let obj_size = obj_str.len();
        
        metadata.insert("object_type".to_string(), Value::String(self.get_value_type(obj)));
        metadata.insert("object_size".to_string(), Value::Number(serde_json::Number::from(obj_size)));
        metadata.insert("is_null".to_string(), Value::Bool(obj.is_null()));
        metadata.insert("is_array".to_string(), Value::Bool(obj.is_array()));
        metadata.insert("is_object".to_string(), Value::Bool(obj.is_object()));

        Value::Object(metadata.into_iter().collect())
    }

    /// Deep serialize any value, handling nested structures
    fn deep_serialize_value(&self, value: Value) -> RunAgentResult<Value> {
        match value {
            Value::Object(map) => {
                let mut result = serde_json::Map::new();
                for (key, val) in map {
                    result.insert(key, self.deep_serialize_value(val)?);
                }
                Ok(Value::Object(result))
            }
            Value::Array(arr) => {
                let mut result = Vec::new();
                for item in arr {
                    result.push(self.deep_serialize_value(item)?);
                }
                Ok(Value::Array(result))
            }
            _ => Ok(value), // Primitive values are already serializable
        }
    }

    /// Reconstruct nested JSON structures
    fn reconstruct_nested_json(&self, data: Value) -> RunAgentResult<Value> {
        match data {
            Value::Object(ref map) => {
                if let (Some(strategy), Some(content)) = (
                    map.get("strategy").and_then(|s| s.as_str()),
                    map.get("content"),
                ) {
                    // This is a serialized object, reconstruct it
                    match strategy {
                        "direct" => Ok(content.clone()),
                        "string_repr" => Ok(content.clone()),
                        _ => Ok(data),
                    }
                } else {
                    // Regular object, recursively process
                    let mut result = serde_json::Map::new();
                    for (key, value) in map {
                        result.insert(key.clone(), self.reconstruct_nested_json(value.clone())?);
                    }
                    Ok(Value::Object(result))
                }
            }
            Value::Array(arr) => {
                let mut result = Vec::new();
                for item in arr {
                    result.push(self.reconstruct_nested_json(item)?);
                }
                Ok(Value::Array(result))
            }
            _ => Ok(data),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{MessageType, SafeMessage};

    #[test]
    fn test_serializer_creation() {
        let serializer = CoreSerializer::new(5.0).unwrap();
        assert_eq!(serializer.max_size_bytes, 5 * 1024 * 1024);
    }

    #[test]
    fn test_object_serialization() {
        let serializer = CoreSerializer::new(10.0).unwrap();
        let obj = serde_json::json!({"key": "value", "number": 42});
        
        let result = serializer.serialize_object(obj);
        assert!(result.is_ok());
    }

    #[test]
    fn test_message_serialization() {
        let serializer = CoreSerializer::new(10.0).unwrap();
        let message = SafeMessage::new(
            "test-id".to_string(),
            MessageType::Status,
            serde_json::json!({"status": "ok"}),
        );
        
        let result = serializer.serialize_message(&message);
        assert!(result.is_ok());
        
        let serialized = result.unwrap();
        let deserialized = serializer.deserialize_message(&serialized);
        assert!(deserialized.is_ok());
    }

    #[test]
    fn test_size_limit_check() {
        let serializer = CoreSerializer::new(0.001).unwrap(); // Very small limit
        let small_str = "test";
        let large_str = "a".repeat(2000);
        
        assert!(serializer.check_size_limit(small_str));
        assert!(!serializer.check_size_limit(&large_str));
    }

    #[test]
    fn test_json_serializable_check() {
        let serializer = CoreSerializer::new(10.0).unwrap();
        
        let simple_obj = serde_json::json!({"key": "value"});
        assert!(serializer.is_json_serializable(&simple_obj));
        
        let null_obj = Value::Null;
        assert!(serializer.is_json_serializable(&null_obj));
        
        let array_obj = serde_json::json!([1, 2, 3]);
        assert!(serializer.is_json_serializable(&array_obj));
    }

    #[test]
    fn test_nested_reconstruction() {
        let serializer = CoreSerializer::new(10.0).unwrap();
        
        let nested_data = serde_json::json!({
            "level1": {
                "level2": {
                    "value": "test"
                }
            }
        });
        
        let result = serializer.reconstruct_nested_json(nested_data.clone());
        assert!(result.is_ok());
        
        let reconstructed = result.unwrap();
        assert_eq!(reconstructed, nested_data);
    }
}