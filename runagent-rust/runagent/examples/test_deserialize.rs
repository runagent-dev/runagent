use runagent::utils::serializer::CoreSerializer;
use serde_json::json;

fn main() {
    let serializer = CoreSerializer::new(10.0).unwrap();
    
    // Test the exact structure we're getting
    let test_response = json!({
        "payload": "\"Hello, world!\"",
        "type": "string"
    });
    
    println!("Input: {}", test_response);
    let result = serializer.deserialize_object(test_response).unwrap();
    println!("Result: {}", result);
    println!("Result is string: {}", result.is_string());
}
