//! CLI output utilities for consistent formatting

use colored::{ColoredString, Colorize};
use indicatif::{ProgressBar, ProgressStyle};
use std::io::{self, Write};

/// CLI output helper for consistent formatting and colors
pub struct CliOutput {
    colored: bool,
}

impl CliOutput {
    /// Create a new CLI output helper
    pub fn new(colored: bool) -> Self {
        Self { colored }
    }

    /// Print an info message with blue icon
    pub fn info(&self, message: &str) {
        self.print_with_icon("ℹ", message, |s| if self.colored { s.bright_blue() } else { s.normal() });
    }

    /// Print a success message with green checkmark
    pub fn success(&self, message: &str) {
        self.print_with_icon("✅", message, |s| if self.colored { s.bright_green() } else { s.normal() });
    }

    /// Print a warning message with yellow exclamation
    pub fn warning(&self, message: &str) {
        self.print_with_icon("⚠️", message, |s| if self.colored { s.bright_yellow() } else { s.normal() });
    }

    /// Print an error message with red X
    pub fn error(&self, message: &str) {
        self.print_with_icon("❌", message, |s| if self.colored { s.bright_red() } else { s.normal() });
    }

    /// Print a debug message with gray text
    pub fn debug(&self, message: &str) {
        if self.colored {
            eprintln!("{} {}", "🔧".dimmed(), message.dimmed());
        } else {
            eprintln!("DEBUG: {}", message);
        }
    }

    /// Print a step message with numbered step
    pub fn step(&self, step: usize, message: &str) {
        let step_str = format!("{}.", step);
        if self.colored {
            println!("{} {}", step_str.bright_cyan().bold(), message);
        } else {
            println!("{} {}", step_str, message);
        }
    }

    /// Print a configuration item
    pub fn config_item(&self, key: &str, value: &str) {
        if self.colored {
            println!("   {}: {}", key.dimmed(), value.bright_white());
        } else {
            println!("   {}: {}", key, value);
        }
    }

    /// Print a table header
    pub fn table_header(&self, headers: &[&str]) {
        let header_line = headers.join(" | ");
        if self.colored {
            println!("{}", header_line.bold().underline());
        } else {
            println!("{}", header_line);
            println!("{}", "-".repeat(header_line.len()));
        }
    }

    /// Print a table row
    pub fn table_row(&self, values: &[&str]) {
        println!("{}", values.join(" | "));
    }

    /// Print a command suggestion
    pub fn suggest_command(&self, command: &str) {
        if self.colored {
            println!("💡 Try: {}", command.bright_cyan());
        } else {
            println!("Suggestion: {}", command);
        }
    }

    /// Print a URL link
    pub fn link(&self, text: &str, url: &str) {
        if self.colored {
            println!("{}: {}", text, url.bright_blue().underline());
        } else {
            println!("{}: {}", text, url);
        }
    }

    /// Create a progress bar
    pub fn progress_bar(&self, total: u64, message: &str) -> ProgressBar {
        let pb = ProgressBar::new(total);
        if self.colored {
            pb.set_style(
                ProgressStyle::default_bar()
                    .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} {msg}")
                    .unwrap()
                    .progress_chars("█▉▊▋▌▍▎▏  ")
            );
        } else {
            pb.set_style(
                ProgressStyle::default_bar()
                    .template("[{elapsed_precise}] [{bar:40}] {pos}/{len} {msg}")
                    .unwrap()
                    .progress_chars("##-")
            );
        }
        pb.set_message(message.to_string());
        pb
    }

    /// Print a separator line
    pub fn separator(&self) {
        if self.colored {
            println!("{}", "─".repeat(50).dimmed());
        } else {
            println!("{}", "-".repeat(50));
        }
    }

    /// Print agent information in a formatted block
    pub fn agent_info(&self, agent_id: &str, framework: &str, status: &str, host: &str, port: u16) {
        self.separator();
        self.config_item("Agent ID", &self.colorize_value(agent_id, "magenta"));
        self.config_item("Framework", &self.colorize_value(framework, "green"));
        self.config_item("Status", &self.colorize_status(status));
        self.config_item("Address", &self.colorize_value(&format!("{}:{}", host, port), "blue"));
        self.separator();
    }

    /// Print capacity information
    pub fn capacity_info(&self, current: usize, max: usize, is_full: bool) {
        let status_color = if is_full { "red" } else { "green" };
        let status_text = if is_full { "FULL" } else { "Available" };
        
        self.config_item("Capacity", &format!("{}/{}", 
            self.colorize_value(&current.to_string(), "cyan"),
            self.colorize_value(&max.to_string(), "cyan")
        ));
        self.config_item("Status", &self.colorize_value(status_text, status_color));
    }

    /// Ask for user confirmation
    pub fn confirm(&self, message: &str) -> io::Result<bool> {
        print!("{} {} [y/N]: ", 
            if self.colored { "❓".to_string() } else { "?".to_string() },
            message
        );
        io::stdout().flush()?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        
        Ok(input.trim().to_lowercase().starts_with('y'))
    }

    /// Print a list of items with bullets
    pub fn list_items(&self, items: &[&str]) {
        for item in items {
            if self.colored {
                println!("  • {}", item);
            } else {
                println!("  - {}", item);
            }
        }
    }

    /// Print next steps section
    pub fn next_steps(&self, steps: &[&str]) {
        self.info("📝 Next steps:");
        for (i, step) in steps.iter().enumerate() {
            self.step(i + 1, step);
        }
    }

    // Helper methods
    
    fn print_with_icon<F>(&self, icon: &str, message: &str, color_fn: F) 
    where 
        F: Fn(ColoredString) -> ColoredString
    {
        if self.colored {
            println!("{} {}", icon, color_fn(message.into()));
        } else {
            println!("{}", message);
        }
    }

    fn colorize_value(&self, value: &str, color: &str) -> String {
        if !self.colored {
            return value.to_string();
        }

        match color {
            "red" => value.bright_red().to_string(),
            "green" => value.bright_green().to_string(),
            "blue" => value.bright_blue().to_string(),
            "yellow" => value.bright_yellow().to_string(),
            "magenta" => value.bright_magenta().to_string(),
            "cyan" => value.bright_cyan().to_string(),
            _ => value.to_string(),
        }
    }

    fn colorize_status(&self, status: &str) -> String {
        if !self.colored {
            return status.to_string();
        }

        match status.to_lowercase().as_str() {
            "deployed" | "running" | "active" | "healthy" => status.bright_green().to_string(),
            "error" | "failed" | "unhealthy" => status.bright_red().to_string(),
            "pending" | "starting" | "loading" => status.bright_yellow().to_string(),
            "stopped" | "inactive" => status.dimmed().to_string(),
            _ => status.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_output_creation() {
        let output = CliOutput::new(true);
        assert!(output.colored);

        let output = CliOutput::new(false);
        assert!(!output.colored);
    }

    #[test]
    fn test_colorize_value() {
        let output = CliOutput::new(true);
        let colored = output.colorize_value("test", "red");
        // Can't easily test color codes, but ensure it doesn't panic
        assert!(!colored.is_empty());

        let output = CliOutput::new(false);
        let plain = output.colorize_value("test", "red");
        assert_eq!(plain, "test");
    }

    #[test]
    fn test_colorize_status() {
        let output = CliOutput::new(false);
        assert_eq!(output.colorize_status("deployed"), "deployed");
        assert_eq!(output.colorize_status("error"), "error");
    }
}