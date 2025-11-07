"""
CLI commands that use the restructured SDK internally.
"""
import os
import json
import uuid

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from runagent import RunAgent
from runagent.sdk.exceptions import (  # RunAgentError,; ConnectionError
    AuthenticationError,
    TemplateError,
    ValidationError,
)
from runagent.client.client import RunAgentClient
from runagent.sdk.server.local_server import LocalServer
from runagent.utils.agent import detect_framework
from runagent.utils.animation import show_subtle_robotic_runner, show_quick_runner
from runagent.utils.config import Config
from runagent.sdk.deployment.middleware_sync import get_middleware_sync
from runagent.cli.utils import add_framework_options, get_selected_framework
from runagent.utils.enums.framework import Framework
console = Console()


def format_error_message(error_info):
    """Format error information from API responses"""
    if isinstance(error_info, dict) and "message" in error_info:
        # New format with ErrorDetail object
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code", "UNKNOWN_ERROR")
        return f"[{error_code}] {error_message}"
    else:
        # Fallback to old format for backward compatibility
        return str(error_info) if error_info else "Unknown error"


# ============================================================================
# Config Command Group
# ============================================================================

@click.group()
def db():
    """Database management and monitoring commands"""
    pass

@db.command()
@click.option("--cleanup-days", type=int, help="Clean up records older than N days")
@click.option("--agent-id", help="Show detailed info for specific agent")
def status(cleanup_days, agent_id):
    """Show local database status and statistics (ENHANCED with invocation stats)"""
    try:
        sdk = RunAgent()

        if agent_id:
            # Show agent-specific details including invocations
            result = sdk.get_agent_info(agent_id, local=True)
            if result.get("success"):
                agent_data = result["agent_info"]
                console.print(f"\n[bold]Agent Details: {agent_id}[/bold]")
                console.print(f"Framework: [green]{agent_data.get('framework')}[/green]")
                console.print(f"Status: [yellow]{agent_data.get('status')}[/yellow]")
                console.print(f"Path: [blue]{agent_data.get('deployment_path')}[/blue]")
                
                # Show agent-specific invocation stats
                agent_inv_stats = sdk.db_service.get_invocation_stats(agent_id=agent_id)
                console.print(f"\n[bold]Invocation Statistics for {agent_id}[/bold]")
                console.print(f"Total: [cyan]{agent_inv_stats.get('total_invocations', 0)}[/cyan]")
                console.print(f"Success Rate: [blue]{agent_inv_stats.get('success_rate', 0)}%[/blue]")
                
            return

        # Show general database stats
        stats = sdk.db_service.get_database_stats()

        console.print("\n[bold]Local Database Status[/bold]")

        total_agents = stats.get("total_agents", 0)
        console.print(f"Total Agents: [cyan]{total_agents}[/cyan]")
        console.print(f"Total Agent Runs: [cyan]{stats.get('total_runs', 0)}[/cyan]")
        console.print(
            f"Database Size: [yellow]{stats.get('database_size_mb', 0)} MB[/yellow]"
        )

        # NEW: Show invocation statistics
        overall_stats = sdk.db_service.get_invocation_stats()
        
        console.print(f"\n[bold]Invocation Statistics[/bold]")
        console.print(f"Total Invocations: [cyan]{overall_stats.get('total_invocations', 0)}[/cyan]")
        console.print(f"Completed: [green]{overall_stats.get('completed_invocations', 0)}[/green]")
        console.print(f"Failed: [red]{overall_stats.get('failed_invocations', 0)}[/red]")
        console.print(f"Pending: [yellow]{overall_stats.get('pending_invocations', 0)}[/yellow]")
        console.print(f"Success Rate: [blue]{overall_stats.get('success_rate', 0)}%[/blue]")
        
        if overall_stats.get('avg_execution_time_ms'):
            avg_time = overall_stats['avg_execution_time_ms']
            if avg_time < 1000:
                time_display = f"{avg_time:.1f}ms"
            else:
                time_display = f"{avg_time/1000:.2f}s"
            console.print(f"Average Execution Time: [cyan]{time_display}[/cyan]")

        # Show agent status breakdown
        status_counts = stats.get("agent_status_counts", {})
        if status_counts:
            console.print("\n[bold]Agent Status Breakdown:[/bold]")
            for status, count in status_counts.items():
                console.print(f"  [cyan]{status}[/cyan]: {count}")

        # List agents in table format
        agents = sdk.db_service.list_agents()

        if agents:
            console.print(f"\n[bold]Deployed Agents:[/bold]")
            
            # Create table for better formatting
            table = Table(title=f"Local Agents ({len(agents)} total)")
            table.add_column("Status", width=10)
            table.add_column("Files", width=6)
            table.add_column("Agent ID", style="magenta", width=36)
            table.add_column("Framework", style="green", width=12)
            table.add_column("Host:Port", style="blue", width=15)
            table.add_column("Runs", style="cyan", width=6)
            table.add_column("Status", style="yellow", width=10)
            
            for agent in agents:
                status_text = (
                    "[green]deployed[/green]"
                    if agent["status"] == "deployed"
                    else "[red]error[/red]" if agent["status"] == "error" else "[yellow]other[/yellow]"
                )
                exists_text = "[green]exists[/green]" if agent.get("exists") else "[red]missing[/red]"
                
                table.add_row(
                    status_text,
                    exists_text,
                    agent['agent_id'],
                    agent['framework'],
                    f"{agent.get('host', 'N/A')}:{agent.get('port', 'N/A')}",
                    str(agent.get('run_count', 0)),
                    agent['status']
                )
            
            console.print(table)

        # Show recent invocations
        recent_invocations = sdk.db_service.list_invocations(limit=5)
        if recent_invocations:
            console.print(f"\n[bold]Recent Invocations:[/bold]")
            for inv in recent_invocations:
                status_color = "green" if inv['status'] == "completed" else "red" if inv['status'] == "failed" else "yellow"
                console.print(f"   • {inv['invocation_id'][:12]}... [{status_color}]{inv['status']}[/{status_color}] ({inv.get('entrypoint_tag', 'N/A')})")

        console.print(f"\n[bold]Database Commands:[/bold]")
        console.print(f"   • [cyan]runagent db invocations[/cyan] - Show all invocations")
        console.print(f"   • [cyan]runagent db invocation <id>[/cyan] - Show specific invocation")
        console.print(f"   • [cyan]runagent db cleanup[/cyan] - Clean up old records")
        console.print(f"   • [cyan]runagent db status --agent-id <id>[/cyan] - Agent-specific info")
        console.print(f"   • [cyan]runagent db status --agent-id <id>[/cyan] - Agent-specific info")

        # Cleanup if requested (keep existing logic)
        if cleanup_days:
            console.print(f"\n[cyan]Cleaning up records older than {cleanup_days} days...[/cyan]")
            cleanup_result = sdk.cleanup_local_database(cleanup_days)
            if cleanup_result.get("success"):
                console.print(f"✅ [green]{cleanup_result.get('message')}[/green]")
            else:
                console.print(f"❌ [red]{cleanup_result.get('error')}[/red]")

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Database status error:[/red] {e}")
        raise click.ClickException("Failed to get database status")


@db.command()
@click.option("--agent-id", help="Filter by specific agent ID")
@click.option("--status", type=click.Choice(["pending", "completed", "failed"]), help="Filter by status")
@click.option("--limit", type=int, default=20, help="Maximum number of invocations to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def invocations(agent_id, status, limit, output_format):
    """Show agent invocation history and statistics"""
    try:
        sdk = RunAgent()
        
        # Get invocations
        invocations_list = sdk.db_service.list_invocations(
            agent_id=agent_id,
            status=status,
            limit=limit
        )
        
        if output_format == "json":
            console.print(json.dumps(invocations_list, indent=2))
            return
        
        if not invocations_list:
            console.print("[yellow]No invocations found[/yellow]")
            if agent_id:
                console.print(f"   • Agent ID: {agent_id}")
            if status:
                console.print(f"   • Status: {status}")
            return
        
        # Show statistics first
        if agent_id:
            stats = sdk.db_service.get_invocation_stats(agent_id=agent_id)
        else:
            stats = sdk.db_service.get_invocation_stats()
        
        console.print(f"\n[bold]Invocation Statistics[/bold]")
        if agent_id:
            console.print(f"   Agent ID: [magenta]{agent_id}[/magenta]")
        console.print(f"   Total: [cyan]{stats.get('total_invocations', 0)}[/cyan]")
        console.print(f"   Completed: [green]{stats.get('completed_invocations', 0)}[/green]")
        console.print(f"   Failed: [red]{stats.get('failed_invocations', 0)}[/red]")
        console.print(f"   Pending: [yellow]{stats.get('pending_invocations', 0)}[/yellow]")
        console.print(f"   Success Rate: [blue]{stats.get('success_rate', 0)}%[/blue]")
        if stats.get('avg_execution_time_ms'):
            console.print(f"   Avg Execution Time: [cyan]{stats.get('avg_execution_time_ms', 0):.1f}ms[/cyan]")
        
        # Show invocations table
        console.print(f"\n[bold]Recent Invocations (showing {len(invocations_list)} of {limit} max)[/bold]")
        
        table = Table(title="Agent Invocations")
        table.add_column("Invocation", style="dim", width=12)
        table.add_column("Agent", style="magenta", width=12)
        table.add_column("Entrypoint", style="green", width=12)
        table.add_column("Status", width=10)
        table.add_column("Duration", style="cyan", width=10)
        table.add_column("Started", style="dim", width=16)
        table.add_column("SDK", style="yellow", width=10)
        
        for inv in invocations_list:
            # Status with color
            status_text = inv['status']
            if status_text == "completed":
                status_display = f"[green]{status_text}[/green]"
            elif status_text == "failed":
                status_display = f"[red]{status_text}[/red]"
            else:
                status_display = f"[yellow]{status_text}[/yellow]"
            
            # Duration calculation
            duration_display = "N/A"
            if inv.get('execution_time_ms'):
                if inv['execution_time_ms'] < 1000:
                    duration_display = f"{inv['execution_time_ms']:.0f}ms"
                else:
                    duration_display = f"{inv['execution_time_ms']/1000:.1f}s"
            
            # Format timestamp
            started_display = "N/A"
            if inv.get('request_timestamp'):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(inv['request_timestamp'].replace('Z', '+00:00'))
                    started_display = dt.strftime('%m-%d %H:%M:%S')
                except:
                    started_display = inv['request_timestamp'][:16]
            
            table.add_row(
                inv['invocation_id'][:8] + "...",
                inv['agent_id'][:8] + "...",
                inv.get('entrypoint_tag', 'N/A')[:12],
                status_display,
                duration_display,
                started_display,
                inv.get('sdk_type', 'unknown')[:10]
            )
        
        console.print(table)
        
        # Show usage tips
        console.print(f"\n💡 [dim]Usage tips:[/dim]")
        console.print(f"   • View specific invocation: [cyan]runagent db invocation <invocation_id>[/cyan]")
        console.print(f"   • Filter by agent: [cyan]runagent db invocations --agent-id <agent_id>[/cyan]")
        console.print(f"   • Filter by status: [cyan]runagent db invocations --status completed[/cyan]")
        console.print(f"   • JSON output: [cyan]runagent db invocations --format json[/cyan]")
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error getting invocations:[/red] {e}")
        raise click.ClickException("Failed to get invocations")


@db.command()
@click.argument("invocation_id")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def invocation(invocation_id, output_format):
    """Show detailed information about a specific invocation"""
    try:
        sdk = RunAgent()
        
        invocation = sdk.db_service.get_invocation(invocation_id)
        
        if not invocation:
            console.print(f"❌ [red]Invocation {invocation_id} not found[/red]")
            
            # Show available invocations
            console.print("\n💡 Recent invocations:")
            recent = sdk.db_service.list_invocations(limit=5)
            for inv in recent:
                console.print(f"   • {inv['invocation_id']} ({inv['status']})")
            
            raise click.ClickException("Invocation not found")
        
        if output_format == "json":
            console.print(json.dumps(invocation, indent=2))
            return
        
        # Display detailed information
        console.print(f"\n🔍 [bold]Invocation Details[/bold]")
        console.print(f"   Invocation ID: [bold magenta]{invocation['invocation_id']}[/bold magenta]")
        console.print(f"   Agent ID: [bold cyan]{invocation['agent_id']}[/bold cyan]")
        console.print(f"   Entrypoint: [green]{invocation.get('entrypoint_tag', 'N/A')}[/green]")
        console.print(f"   SDK Type: [yellow]{invocation.get('sdk_type', 'unknown')}[/yellow]")
        
        # Status with color
        status = invocation['status']
        if status == "completed":
            status_display = f"[green]{status}[/green]"
        elif status == "failed":
            status_display = f"[red]{status}[/red]"
        else:
            status_display = f"[yellow]{status}[/yellow]"
        console.print(f"   Status: {status_display}")
        
        # Timing information
        console.print(f"\n⏱️ [bold]Timing Information[/bold]")
        if invocation.get('request_timestamp'):
            console.print(f"   Started: [cyan]{invocation['request_timestamp']}[/cyan]")
        if invocation.get('response_timestamp'):
            console.print(f"   Completed: [cyan]{invocation['response_timestamp']}[/cyan]")
        if invocation.get('execution_time_ms'):
            exec_time = invocation['execution_time_ms']
            if exec_time < 1000:
                time_display = f"{exec_time:.1f}ms"
            else:
                time_display = f"{exec_time/1000:.2f}s"
            console.print(f"   Duration: [green]{time_display}[/green]")
        
        # Input data
        console.print(f"\n📥 [bold]Input Data[/bold]")
        if invocation.get('input_data'):
            input_str = json.dumps(invocation['input_data'], indent=2)
            if len(input_str) > 500:
                console.print(f"   [dim]{input_str[:500]}...\n   (truncated - use --format json for full data)[/dim]")
            else:
                console.print(f"   [dim]{input_str}[/dim]")
        else:
            console.print("   [dim]No input data[/dim]")
        
        # Output data or error
        if invocation['status'] == 'failed' and invocation.get('error_detail'):
            console.print(f"\n❌ [bold red]Error Details[/bold red]")
            console.print(f"   [red]{invocation['error_detail']}[/red]")
        elif invocation.get('output_data'):
            console.print(f"\n📤 [bold]Output Data[/bold]")
            output_str = json.dumps(invocation['output_data'], indent=2)
            if len(output_str) > 500:
                console.print(f"   [dim]{output_str[:500]}...\n   (truncated - use --format json for full data)[/dim]")
            else:
                console.print(f"   [dim]{output_str}[/dim]")
        
        # Client info
        if invocation.get('client_info'):
            console.print(f"\n🔧 [bold]Client Information[/bold]")
            client_str = json.dumps(invocation['client_info'], indent=2)
            console.print(f"   [dim]{client_str}[/dim]")
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error getting invocation details:[/red] {e}")
        raise click.ClickException("Failed to get invocation details")


@db.command()
@click.option("--days", type=int, default=30, help="Clean up invocations older than N days")
@click.option("--agent-runs", is_flag=True, help="Also clean up old agent_runs records")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def cleanup(days, agent_runs, yes):
    """Clean up old database records"""
    try:
        sdk = RunAgent()
        
        # Get count of records to be cleaned
        all_invocations = sdk.db_service.list_invocations(limit=1000)
        
        # Filter by date (simple approximation for preview)
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_invocations_count = len([
            inv for inv in all_invocations 
            if inv.get('request_timestamp') and 
            datetime.fromisoformat(inv['request_timestamp'].replace('Z', '+00:00')) < cutoff_date
        ])
        
        console.print(f"🧹 [yellow]Cleanup Preview (older than {days} days):[/yellow]")
        console.print(f"   • Invocations: {old_invocations_count} records")
        
        if agent_runs:
            console.print(f"   • Agent runs: Will be cleaned too")
        
        if old_invocations_count == 0:
            console.print(f"✅ [green]No records found older than {days} days[/green]")
            return
        
        if not yes:
            if not click.confirm(f"⚠️ This will permanently delete {old_invocations_count} invocation records. Continue?"):
                console.print("Cleanup cancelled.")
                return
        
        # Perform cleanup
        deleted_invocations = sdk.db_service.cleanup_old_invocations(days_old=days)
        
        console.print(f"✅ [green]Cleaned up {deleted_invocations} old invocation records[/green]")
        
        if agent_runs:
            deleted_runs = sdk.cleanup_local_database(days)
            if deleted_runs.get("success"):
                console.print(f"✅ [green]Also cleaned up old agent runs[/green]")
        
        # Show updated stats
        stats = sdk.db_service.get_invocation_stats()
        console.print(f"📊 Remaining invocations: [cyan]{stats.get('total_invocations', 0)}[/cyan]")
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error cleaning up records:[/red] {e}")
        raise click.ClickException("Cleanup failed")


# local-sync command removed - sync settings now managed via 'runagent config'
# Use: runagent config > Select "🔄 Sync Settings"


# Add this simplified logs command to the db group in runagent/cli/commands.py

@db.command()
@click.option("--agent-id", help="Filter by specific agent ID")
@click.option("--limit", type=int, default=100, help="Maximum number of logs to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def logs(agent_id, limit, output_format):
    """Show all agent logs (no filtering)"""
    try:
        sdk = RunAgent()
        
        if agent_id:
            # Show logs for specific agent
            logs = sdk.db_service.get_agent_logs(agent_id=agent_id, limit=limit)
            
            if not logs:
                console.print("📭 [yellow]No logs found[/yellow]")
                console.print(f"   • Agent ID: {agent_id}")
                return
            
            if output_format == "json":
                console.print(json.dumps(logs, indent=2))
                return
            
            console.print(f"\n📋 [bold]Agent Logs: {agent_id}[/bold]")
            
            table = Table(title=f"All Agent Logs (showing {len(logs)} entries)")
            table.add_column("Time", style="dim", width=16)
            table.add_column("Level", width=8)
            table.add_column("Message", style="white", width=80)
            table.add_column("Execution", style="cyan", width=12)
            
            for log in logs:
                # Format timestamp
                time_str = "N/A"
                if log.get('created_at'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(log['created_at'])
                        time_str = dt.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = log['created_at'][:16]
                
                # Color code log levels
                level = log.get('log_level', 'INFO')
                if level == 'ERROR' or level == 'CRITICAL':
                    level_display = f"[red]{level}[/red]"
                elif level == 'WARNING':
                    level_display = f"[yellow]{level}[/yellow]"
                elif level == 'DEBUG':
                    level_display = f"[dim]{level}[/dim]"
                else:
                    level_display = f"[green]{level}[/green]"
                
                # Don't truncate messages - show full log
                message = log.get('message', '')
                
                # Show execution ID if available
                exec_id = log.get('execution_id', '')
                exec_display = exec_id[:8] + "..." if exec_id else ""
                
                table.add_row(time_str, level_display, message, exec_display)
            
            console.print(table)
            
        else:
            # Show log summary for all agents
            agents = sdk.db_service.list_agents()
            
            if not agents:
                console.print("📭 [yellow]No agents found[/yellow]")
                return
            
            console.print(f"\n📊 [bold]Agent Log Summary[/bold]")
            
            table = Table(title="Log Counts by Agent")
            table.add_column("Agent ID", style="magenta", width=36)
            table.add_column("Framework", style="green", width=12)
            table.add_column("Total Logs", style="cyan", width=10)
            table.add_column("Errors", style="red", width=8)
            table.add_column("Last Log", style="dim", width=16)
            
            for agent in agents[:10]:  # Show first 10 agents
                agent_logs = sdk.db_service.get_agent_logs(agent['agent_id'], limit=1000)
                error_logs = [log for log in agent_logs if log.get('log_level') in ['ERROR', 'CRITICAL']]
                
                last_log_time = "Never"
                if agent_logs:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(agent_logs[0]['created_at'])
                        last_log_time = dt.strftime('%m-%d %H:%M')
                    except:
                        last_log_time = "Recent"
                
                table.add_row(
                    agent['agent_id'],
                    agent['framework'],
                    str(len(agent_logs)),
                    str(len(error_logs)),
                    last_log_time
                )
            
            console.print(table)
        
        console.print(f"\n💡 [bold]Usage tips:[/bold]")
        console.print(f"   • View agent logs: [cyan]runagent db logs --agent-id <agent_id>[/cyan]")
        console.print(f"   • JSON output: [cyan]runagent db logs --agent-id <agent_id> --format json[/cyan]")
        console.print(f"   • More logs: [cyan]runagent db logs --agent-id <agent_id> --limit 500[/cyan]")

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error getting logs:[/red] {e}")
        raise click.ClickException("Failed to get logs")


@db.command()
@click.option("--days", type=int, default=7, help="Clean up logs older than N days")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def cleanup_logs(days, yes):
    """Clean up old agent logs"""
    try:
        sdk = RunAgent()
        
        if not yes:
            if not click.confirm(f"⚠️ This will delete logs older than {days} days for ALL agents. Continue?"):
                console.print("Cleanup cancelled.")
                return
        
        deleted_count = sdk.db_service.cleanup_old_logs(days_old=days)
        console.print(f"✅ [green]Cleaned up {deleted_count} old log entries[/green]")
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error cleaning up logs:[/red] {e}")
        raise click.ClickException("Log cleanup failed")