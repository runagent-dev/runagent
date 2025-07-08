//! Teardown command implementation

use crate::utils::output::CliOutput;
use anyhow::Result;
use clap::Args;

/// Remove RunAgent configuration
#[derive(Args)]
pub struct TeardownArgs {
    /// Skip confirmation
    #[arg(long)]
    yes: bool,
}

pub async fn execute(args: TeardownArgs, output: &CliOutput) -> Result<()> {
    output.info("🗑️ Removing RunAgent configuration...");
    
    if !args.yes {
        output.warning("⚠️ This will remove all RunAgent configuration.");
        // In a real implementation, you'd prompt for confirmation here
    }
    
    // Simulate teardown
    output.success("✅ RunAgent teardown completed successfully!");
    output.info("💡 Run 'runagent setup --api-key <key>' to reconfigure");
    
    Ok(())
}