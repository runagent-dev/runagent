import click
import inquirer
from runagent.client import RunAgentClient


@click.command()
@click.option('--api-key', required=True, help='Your API key')
@click.option('--base-url', help='API base URL')
@click.option('--force', is_flag=True, help='Force reconfiguration')
def setup(api_key, base_url, force):
    """Setup RunAgent authentication"""
    client = RunAgentClient(cli_mode=True)  # Enable interactive mode
    client.setup(api_key=api_key, base_url=base_url, force=force)


@click.command()
@click.option('--yes', is_flag=True, help='Skip confirmation')
def teardown(yes):
    """Remove RunAgent configuration"""
    client = RunAgentClient(cli_mode=True)  # Enable interactive mode
    client.teardown(confirm=yes)


@click.command()
@click.option('--folder', help='Project folder name')
@click.option('--framework', default=None, help='Framework to use (langchain, langgraph, llamaindex). Defaults to langchain if not specified')
@click.option('--template', default=None, help='Template variant (basic, advanced). Defaults to basic if not specified')
@click.option('--non-interactive', is_flag=True, help='Skip interactive prompts and use defaults (langchain/basic)')
def init(folder, framework, template, non_interactive):
    """Initialize a new RunAgent project
    
    Examples:
      runagent init                                    # Interactive mode
      runagent init --non-interactive                  # Use defaults (langchain/basic)  
      runagent init --framework langgraph             # Specify framework, prompt for template
      runagent init --framework langchain --template advanced  # Specify both (no prompts)
    """
    
    # Determine if we should use CLI mode
    # CLI mode is disabled if --non-interactive is used OR if both framework and template are provided
    use_cli_mode = not non_interactive and not (framework and template)
    
    client = RunAgentClient(cli_mode=use_cli_mode)
    
    # Call the init method
    success = client.init(
        framework=framework, 
        template=template, 
        folder=folder
    )
    
    if not success:
        raise click.ClickException("Project initialization failed")


@click.command()
@click.option('--list', 'action_list', is_flag=True, help='List all available templates')
@click.option('--info', 'action_info', is_flag=True, help='Get detailed information about a specific template')
@click.option('--framework', help='Framework name (required for --info)')
@click.option('--template', help='Template name (required for --info)')
@click.option('--filter-framework', help='Filter templates by framework when listing')
@click.option('--format', type=click.Choice(['table', 'json', 'yaml']), default='table', help='Output format')
def template(action_list, action_info, framework, template, filter_framework, format):
    """Manage project templates - list available templates or get detailed information"""
    
    if not action_list and not action_info:
        click.echo("❌ Please specify either --list or --info")
        click.echo("Usage examples:")
        click.echo("  runagent template --list")
        click.echo("  runagent template --info --framework langchain --template basic")
        raise click.ClickException("No action specified")
    
    if action_list and action_info:
        click.echo("❌ Please specify only one action: --list or --info")
        raise click.ClickException("Multiple actions specified")
    
    client = RunAgentClient(cli_mode=True)
    
    if action_list:
        _handle_list_templates(client, filter_framework, format)
    elif action_info:
        _handle_template_info(client, framework, template)


def _handle_list_templates(client, filter_framework, format):
    """Handle the --list action"""
    try:
        available_templates = client.list_templates()
        
        if not available_templates:
            click.echo("❌ No templates available")
            return
        
        # Apply framework filter if specified
        if filter_framework:
            if filter_framework not in available_templates:
                click.echo(f"❌ Framework '{filter_framework}' not found")
                click.echo(f"Available frameworks: {', '.join(available_templates.keys())}")
                return
            available_templates = {filter_framework: available_templates[filter_framework]}
        
        # Output in different formats
        if format == 'json':
            import json
            click.echo(json.dumps(available_templates, indent=2))
        elif format == 'yaml':
            try:
                import yaml
                click.echo(yaml.dump(available_templates, default_flow_style=False))
            except ImportError:
                click.echo("❌ PyYAML not installed. Using JSON format instead.")
                import json
                click.echo(json.dumps(available_templates, indent=2))
        else:  # table format (default)
            click.secho("📋 Available Templates:", fg='cyan', bold=True)
            
            for framework_name, templates in available_templates.items():
                click.secho(f"\n🎯 {framework_name}:", fg='blue', bold=True)
                for tmpl in templates:
                    click.echo(f"  - {tmpl}")
            
            click.echo(f"\n💡 Use 'runagent template --info --framework <framework> --template <template>' for details")
            
    except Exception as e:
        click.echo(f"❌ Error listing templates: {str(e)}")


def _handle_template_info(client, framework, template):
    """Handle the --info action"""
    if not framework or not template:
        click.echo("❌ Both --framework and --template are required for --info")
        click.echo("Usage: runagent template --info --framework <framework> --template <template>")
        raise click.ClickException("Missing required parameters")
    
    try:
        from runagent.constants import TEMPLATE_REPO_URL, TEMPLATE_BRANCH, TEMPLATE_PREPATH
        from runagent.client.template_downloader import TemplateDownloader
        
        downloader = TemplateDownloader(TEMPLATE_REPO_URL, TEMPLATE_BRANCH)
        info = downloader.get_template_info(TEMPLATE_PREPATH, framework, template)
        
        if info:
            click.secho(f"📋 Template Information: {framework}/{template}", fg='cyan', bold=True)
            click.echo(f"Framework: {info['framework']}")
            click.echo(f"Template: {info['template']}")
            
            if 'metadata' in info:
                metadata = info['metadata']
                if 'description' in metadata:
                    click.echo(f"Description: {metadata['description']}")
                if 'requirements' in metadata:
                    click.echo(f"Requirements: {', '.join(metadata['requirements'])}")
                if 'version' in metadata:
                    click.echo(f"Version: {metadata['version']}")
                if 'author' in metadata:
                    click.echo(f"Author: {metadata['author']}")
            
            click.echo(f"\n📁 Structure:")
            click.echo(f"Files: {', '.join(info['files'])}")
            if info['directories']:
                click.echo(f"Directories: {', '.join(info['directories'])}")
            
            if 'readme' in info:
                click.echo(f"\n📖 README:")
                click.echo("-" * 50)
                click.echo(info['readme'])
                click.echo("-" * 50)
            
            click.echo(f"\n🚀 To use this template:")
            click.echo(f"runagent init --framework {framework} --template {template}")
            
        else:
            click.echo(f"❌ Template '{framework}/{template}' not found")
            
            # Suggest available templates for the framework
            try:
                available_templates = client.list_templates()
                if framework in available_templates:
                    click.echo(f"Available templates for {framework}: {', '.join(available_templates[framework])}")
                else:
                    click.echo(f"Available frameworks: {', '.join(available_templates.keys())}")
            except:
                pass
            
    except Exception as e:
        click.echo(f"❌ Error getting template info: {str(e)}")


# Add these new commands to your existing runagent/cli/commands.py file

import click
import json
from pathlib import Path
from rich.console import Console

console = Console()

@click.command()
@click.option('--folder', required=True, help='Folder containing agent files to deploy locally')
@click.option('--framework', help='Framework type (auto-detected if not specified)')
@click.option('--replace', help='Agent ID to replace (for capacity management)')
def deploy_local(folder, framework, replace):
    """Deploy agent locally for testing (max 5 agents)"""
    try:
        from runagent.client.local_client import LocalClient
        
        if not Path(folder).exists():
            raise click.ClickException(f"Folder not found: {folder}")
        
        # Detect framework if not provided
        if not framework:
            framework = _detect_framework(folder)
        
        local_client = LocalClient()
        
        # Check capacity if not replacing
        if not replace:
            capacity_info = local_client.get_capacity_info()
            if capacity_info.get('is_full'):
                console.print(f"\n⚠️ [yellow]Database at full capacity ({capacity_info.get('current_count')}/5 agents)[/yellow]")
                console.print("💡 Available options:")
                
                agents = capacity_info.get('agents', [])
                for i, agent in enumerate(agents):
                    console.print(f"   {i+1}. Replace: [cyan]{agent['agent_id']}[/cyan] (deployed: {agent['deployed_at']})")
                
                oldest_agent = capacity_info.get('oldest_agent')
                if oldest_agent:
                    console.print(f"\n💡 Suggested command:")
                    console.print(f"   [cyan]runagent deploy-local --folder {folder} --replace {oldest_agent['agent_id']}[/cyan]")
                
                raise click.ClickException("Database at capacity. Use --replace to replace an existing agent.")
        
        result = local_client.deploy_agent(
            folder_path=folder,
            metadata={'framework': framework},
            replace_agent_id=replace
        )
        
        if result.get('success'):
            click.echo(f"\n✅ {result.get('message', 'Deployment successful')}")
            click.echo(f"🆔 Agent ID: {result.get('agent_id')}")
            
            if replace:
                click.echo(f"🔄 Replaced agent: {replace}")
        else:
            error_code = result.get('error_code')
            if error_code == 'DATABASE_FULL':
                capacity_info = result.get('capacity_info', {})
                oldest_agent = capacity_info.get('oldest_agent', {}).get('agent_id')
                suggestion = result.get('suggestion', '')
                
                console.print(f"\n💡 [yellow]Suggestion:[/yellow] {suggestion}")
                raise click.ClickException(result.get('error'))
            else:
                raise click.ClickException(result.get('error'))
            
    except Exception as e:
        raise click.ClickException(str(e))


@click.command()
@click.option('--folder', required=True, help='Folder containing agent files to upload')
@click.option('--framework', help='Framework type (auto-detected if not specified)')
def upload(folder, framework):
    """Upload agent to remote server"""
    try:
        from runagent.client.rest_client import RestClient
        
        if not Path(folder).exists():
            raise click.ClickException(f"Folder not found: {folder}")
        
        # Detect framework if not provided
        if not framework:
            framework = _detect_framework(folder)
        
        rest_client = RestClient()
        result = rest_client.upload_agent(
            folder_path=folder,
            metadata={'framework': framework}
        )
        
        if result.get('success'):
            click.echo(f"\n✅ {result.get('message')}")
            click.echo(f"🆔 Agent ID: {result.get('agent_id')}")
        else:
            raise click.ClickException(f"Upload failed: {result.get('error')}")
            
    except Exception as e:
        raise click.ClickException(str(e))


@click.command()
@click.option('--id', 'agent_id', required=True, help='Agent ID to start')
@click.option('--config', help='JSON configuration for deployment')
def start(agent_id, config):
    """Start an uploaded agent on remote server"""
    try:
        from runagent.client.rest_client import RestClient
        
        # Parse config if provided
        config_dict = {}
        if config:
            try:
                config_dict = json.loads(config)
            except json.JSONDecodeError:
                raise click.ClickException("Invalid JSON in config parameter")
        
        rest_client = RestClient()
        result = rest_client.start_agent(agent_id, config_dict)
        
        if result.get('success'):
            click.echo(f"\n✅ Agent started successfully!")
            click.echo(f"🌐 Endpoint: {result.get('endpoint')}")
        else:
            raise click.ClickException(f"Start failed: {result.get('error')}")
            
    except Exception as e:
        raise click.ClickException(str(e))


@click.command()
@click.option('--folder', help='Folder containing agent files (for upload + start)')
@click.option('--id', 'agent_id', help='Agent ID (for start only)')
@click.option('--local', is_flag=True, help='Deploy locally instead of remote server')
@click.option('--framework', help='Framework type (auto-detected if not specified)')
@click.option('--config', help='JSON configuration for deployment')
def deploy(folder, agent_id, local, framework, config):
    """Deploy agent (upload + start) or deploy locally"""
    try:
        if local:
            # Local deployment
            if not folder:
                raise click.ClickException("--folder is required for local deployment")
            
            if not Path(folder).exists():
                raise click.ClickException(f"Folder not found: {folder}")
            
            # Detect framework if not provided
            if not framework:
                framework = _detect_framework(folder)
            
            from runagent.client.local_client import LocalClient
            local_client = LocalClient()
            result = local_client.deploy_agent(
                folder_path=folder,
                metadata={'framework': framework}
            )
            
            if result.get('success'):
                click.echo(f"\n✅ {result.get('message')}")
                click.echo(f"🆔 Agent ID: {result.get('agent_id')}")
            else:
                raise click.ClickException(f"Local deployment failed: {result.get('error')}")
        
        else:
            # Remote deployment
            from runagent.client.rest_client import RestClient
            rest_client = RestClient()
            
            if folder:
                # Upload + Start
                if not Path(folder).exists():
                    raise click.ClickException(f"Folder not found: {folder}")
                
                # Detect framework if not provided
                if not framework:
                    framework = _detect_framework(folder)
                
                # Parse config if provided
                config_dict = {}
                if config:
                    try:
                        config_dict = json.loads(config)
                    except json.JSONDecodeError:
                        raise click.ClickException("Invalid JSON in config parameter")
                
                result = rest_client.deploy_agent(
                    folder_path=folder,
                    metadata={'framework': framework}
                )
                
                if result.get('success'):
                    click.echo(f"\n✅ {result.get('message')}")
                    click.echo(f"🆔 Agent ID: {result.get('agent_id')}")
                    click.echo(f"🌐 Endpoint: {result.get('endpoint')}")
                else:
                    raise click.ClickException(f"Deployment failed: {result.get('error')}")
            
            elif agent_id:
                # Start existing agent
                config_dict = {}
                if config:
                    try:
                        config_dict = json.loads(config)
                    except json.JSONDecodeError:
                        raise click.ClickException("Invalid JSON in config parameter")
                
                result = rest_client.start_agent(agent_id, config_dict)
                
                if result.get('success'):
                    click.echo(f"\n✅ Agent started successfully!")
                    click.echo(f"🌐 Endpoint: {result.get('endpoint')}")
                else:
                    raise click.ClickException(f"Start failed: {result.get('error')}")
            
            else:
                raise click.ClickException("Either --folder (for upload+start) or --id (for start only) is required")
            
    except Exception as e:
        raise click.ClickException(str(e))


@click.command()
@click.option('--port', default=8450, help='Port to run the local server on')
@click.option('--host', default='127.0.0.1', help='Host to bind the server to')
@click.option('--debug', is_flag=True, help='Run server in debug mode')
def serve(port, host, debug):
    """Start local FastAPI server for testing deployed agents"""
    try:
        from runagent.server.local_server import LocalServer
        
        console.print("⚡ Starting FastAPI server...")
        server = LocalServer(port=port, host=host)
        server.start(debug=debug)
        
    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
    except Exception as e:
        raise click.ClickException(str(e))


@click.command()
@click.option('--id', 'agent_id', required=True, help='Agent ID to run')
@click.option('--input', 'input_file', help='Path to input JSON file')
@click.option('--message', '-m', help='Simple message to send to the agent')
@click.option('--local', is_flag=True, help='Run agent locally')
@click.option('--timeout', default=300, help='Maximum wait time in seconds')
def run(agent_id, input_file, message, local, timeout):
    """Run a deployed agent"""
    try:
        # Prepare input data
        input_data = {}
        
        if input_file:
            if not Path(input_file).exists():
                raise click.ClickException(f"Input file not found: {input_file}")
            
            with open(input_file, 'r') as f:
                try:
                    input_data = json.load(f)
                except json.JSONDecodeError:
                    raise click.ClickException(f"Invalid JSON in input file: {input_file}")
        
        elif message:
            input_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            }
        else:
            # Interactive mode
            click.echo("Enter your message (press Enter twice to submit):")
            lines = []
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
            
            message_text = '\n'.join(lines)
            input_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": message_text
                    }
                ]
            }
        
        if local:
            # Run locally
            from runagent.client.local_client import LocalClient
            
            console.print(f"🏠 Running agent locally: [cyan]{agent_id}[/cyan]")
            
            local_client = LocalClient()
            result = local_client.run_agent(agent_id, input_data)
            
        else:
            # Run remotely
            import requests
            import time
            
            # Get deployment info
            deployments_dir = Path.cwd() / ".deployments"
            info_file = deployments_dir / f"{agent_id}.json"
            
            if not info_file.exists():
                raise click.ClickException(f"No deployment info found for agent {agent_id}")
            
            with open(info_file, 'r') as f:
                deployment_info = json.load(f)
            
            endpoint = deployment_info.get('endpoint')
            if not endpoint:
                raise click.ClickException(f"No endpoint found for agent {agent_id}")
            
            console.print(f"🌐 Running agent remotely: [cyan]{agent_id}[/cyan]")
            console.print(f"📡 Endpoint: [blue]{endpoint}[/blue]")
            
            start_time = time.time()
            response = requests.post(endpoint, json=input_data, timeout=timeout)
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
            else:
                raise click.ClickException(f"Agent execution failed: HTTP {response.status_code}")
        
        # Display result
        if result.get('success'):
            console.print("\n✅ [bold green]Agent execution completed![/bold green]")
            
            if 'result' in result and result['result']:
                agent_result = result['result']
                content = agent_result.get('content', '')
                
                console.print(f"\n📄 [bold]Result:[/bold]")
                console.print(content)
                
                # Show metadata if available
                if 'metadata' in agent_result:
                    metadata = agent_result['metadata']
                    console.print(f"\n📊 [bold]Metadata:[/bold]")
                    for key, value in metadata.items():
                        console.print(f"  • {key}: {value}")
            
            if not local:
                console.print(f"\n⏱️ Total time: {execution_time:.2f}s")
        else:
            error_msg = result.get('error', 'Unknown error')
            raise click.ClickException(f"Agent execution failed: {error_msg}")
            
    except Exception as e:
        raise click.ClickException(str(e))


@click.command()
@click.option('--cleanup-days', type=int, help='Clean up run records older than N days')
@click.option('--agent-id', help='Show detailed info for specific agent')
@click.option('--capacity', is_flag=True, help='Show detailed capacity information')
def db_status(cleanup_days, agent_id, capacity):
    """Show local database status and statistics"""
    try:
        from runagent.client.local_client import LocalClient
        
        local_client = LocalClient()
        
        if capacity:
            # Show detailed capacity info
            capacity_info = local_client.get_capacity_info()
            
            console.print(f"\n📊 [bold]Database Capacity Information[/bold]")
            console.print(f"Current: {capacity_info.get('current_count', 0)}/5 agents")
            console.print(f"Remaining slots: {capacity_info.get('remaining_slots', 0)}")
            console.print(f"Status: {'🔴 FULL' if capacity_info.get('is_full') else '🟢 Available'}")
            
            agents = capacity_info.get('agents', [])
            if agents:
                console.print(f"\n📋 [bold]Deployed Agents (by age):[/bold]")
                for i, agent in enumerate(agents):
                    status_icon = "🟢" if agent['status'] == 'deployed' else "🔴" if agent['status'] == 'error' else "🟡"
                    age_label = "oldest" if i == 0 else "newest" if i == len(agents)-1 else ""
                    console.print(f"  {i+1}. {status_icon} {agent['agent_id']} ({agent['framework']}) - {agent['deployed_at']} {age_label}")
            
            if capacity_info.get('is_full'):
                oldest = capacity_info.get('oldest_agent', {})
                console.print(f"\n💡 [yellow]To deploy new agent, replace oldest:[/yellow]")
                console.print(f"   [cyan]runagent deploy-local --folder <path> --replace {oldest.get('agent_id', '')}[/cyan]")
            
            return
        
        if agent_id:
            # Show specific agent info
            result = local_client.get_agent_info(agent_id)
            if result.get('success'):
                agent_info = result['agent_info']
                console.print(f"\n📊 [bold]Agent: {agent_id}[/bold]")
                console.print(f"Status: {agent_info['status']}")
                console.print(f"Framework: {agent_info['framework']}")
                console.print(f"Deployed: {agent_info['deployed_at']}")
                console.print(f"Source Path: {agent_info['folder_path']}")
                console.print(f"Deployment Path: {agent_info['deployment_path']}")
                console.print(f"Files Exist: {'✅' if agent_info.get('deployment_exists') else '❌'}")
                console.print(f"Source Exists: {'✅' if agent_info.get('source_exists') else '❌'}")
                
                stats = agent_info.get('stats', {})
                if stats:
                    console.print(f"\n📈 [bold]Statistics:[/bold]")
                    console.print(f"Total Runs: {stats.get('total_runs', 0)}")
                    console.print(f"Success Rate: {stats.get('success_rate', 0)}%")
                    console.print(f"Last Run: {stats.get('last_run', 'Never')}")
                    console.print(f"Avg Execution Time: {stats.get('avg_execution_time', 'N/A')}s")
                
                recent_runs = agent_info.get('recent_runs', [])
                if recent_runs:
                    console.print(f"\n📝 [bold]Recent Runs:[/bold]")
                    for run in recent_runs[:3]:
                        status = "✅" if run['success'] else "❌"
                        console.print(f"  {status} {run['started_at']} ({run.get('execution_time', 'N/A')}s)")
            else:
                console.print(f"❌ {result.get('error')}")
        else:
            # Show database stats
            stats = local_client.get_database_stats()
            capacity_info = local_client.get_capacity_info()
            
            if stats:
                console.print("\n📊 [bold]Local Database Status[/bold]")
                console.print(f"Capacity: {capacity_info.get('current_count', 0)}/5 agents ({'FULL' if capacity_info.get('is_full') else 'OK'})")
                console.print(f"Total Runs: {stats.get('total_runs', 0)}")
                console.print(f"Database Size: {stats.get('database_size_mb', 0)} MB")
                console.print(f"Database Path: {stats.get('database_path', 'Unknown')}")
                
                status_counts = stats.get('agent_status_counts', {})
                if status_counts:
                    console.print("\n📈 [bold]Agent Status Breakdown:[/bold]")
                    for status, count in status_counts.items():
                        console.print(f"  {status}: {count}")
                
                # List agents
                agents_result = local_client.list_local_agents()
                if agents_result.get('success'):
                    agents = agents_result.get('agents', [])
                    if agents:
                        console.print(f"\n📋 [bold]Deployed Agents:[/bold]")
                        for agent in agents:
                            status_icon = "🟢" if agent['status'] == 'deployed' else "🔴" if agent['status'] == 'error' else "🟡"
                            exists_icon = "📁" if agent.get('exists') else "❌"
                            console.print(f"  {status_icon} {exists_icon} {agent['agent_id']} ({agent['framework']}) - {agent['status']}")
                        
                        console.print(f"\n💡 Use --agent-id <id> for detailed info")
                        console.print(f"💡 Use --capacity for capacity management info")
        
        # Cleanup if requested
        if cleanup_days:
            console.print(f"\n🧹 Cleaning up run records older than {cleanup_days} days...")
            cleanup_result = local_client.cleanup_old_runs(cleanup_days)
            if cleanup_result.get('success'):
                console.print(f"✅ {cleanup_result.get('message')}")
            else:
                console.print(f"❌ {cleanup_result.get('error')}")
        
    except Exception as e:
        raise click.ClickException(str(e))


def _detect_framework(folder_path: str) -> str:
    """Detect framework from agent files"""
    folder = Path(folder_path)
    
    # Check main.py for framework imports
    main_file = folder / 'main.py'
    agent_file = folder / 'agent.py'
    
    framework_keywords = {
        'langgraph': ['langgraph', 'StateGraph', 'Graph'],
        'langchain': ['langchain', 'ConversationChain', 'AgentExecutor'],
        'llamaindex': ['llama_index', 'VectorStoreIndex', 'QueryEngine']
    }
    
    for file_to_check in [main_file, agent_file]:
        if file_to_check.exists():
            try:
                content = file_to_check.read_text().lower()
                
                for framework, keywords in framework_keywords.items():
                    if any(keyword.lower() in content for keyword in keywords):
                        return framework
            except:
                continue
    
    # Check requirements.txt
    req_file = folder / 'requirements.txt'
    if req_file.exists():
        try:
            content = req_file.read_text().lower()
            
            for framework, keywords in framework_keywords.items():
                if any(keyword.lower() in content for keyword in keywords):
                    return framework
        except:
            pass
    
    return 'unknown'

