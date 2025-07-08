let agent_id = "7d8bf036-199d-4ced-8d9d-aad39d8c96a9"; // Your actual agent ID

let client = RunAgentClient::new(agent_id, "generic", true).await?;

let response = client.run(&[
    ("message", json!("Hello from Rust SDK!")),
]).await?;

println!("Response: {}", response);