"""Device Code Authentication Flow

Orchestrates the complete device code authentication flow including
user prompts, browser launch, polling, and error handling.
"""

import os
import time
import typing as t

import click
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

from runagent.cli.auth.device_client import DeviceCodeClient
from runagent.constants import DEVICE_CODE_EXPIRATION, DEVICE_CODE_POLL_INTERVAL
from runagent.sdk.rest_client import HttpException, ConnectionError as HttpConnectionError

console = Console()


class DeviceCodeAuthFlow:
    """Orchestrates device code authentication flow"""

    def __init__(self, base_url: str) -> None:
        """
        Initialize device code authentication flow.

        Args:
            base_url: Base URL for API endpoints
        """
        self.base_url = base_url
        self.client = DeviceCodeClient(base_url)

    def authenticate(self) -> t.Dict[str, t.Any]:
        """
        Execute complete device code authentication flow.

        Returns:
            Dictionary containing api_key and user_info on successful authentication

        Raises:
            TimeoutError: If device code expires
            PermissionError: If user cancels authentication
            ValueError: If unexpected response received
            HttpException: If HTTP request fails
        """
        try:
            # Step 1: Initiate device code flow
            device_flow_data = self.client.initiate_device_flow()
            device_code = device_flow_data["device_code"]
            user_code = device_flow_data["user_code"]
            verification_uri = device_flow_data["verification_uri"]
            expires_in = device_flow_data.get("expires_in", DEVICE_CODE_EXPIRATION)
            interval = device_flow_data.get("interval", DEVICE_CODE_POLL_INTERVAL)

            # Step 2: Display instructions to user
            self._display_instructions(user_code, verification_uri)

            # Step 3: Poll for completion
            api_key = self._poll_until_complete(device_code, interval, expires_in)
            
            # Step 4: Validate API key and extract user info (same as manual setup)
            user_info = self._validate_and_extract_user_info(api_key)

            return {
                "api_key": api_key,
                "user_info": user_info
            }

        except TimeoutError as e:
            console.print(
                Panel(
                    "[red]❌ Authentication window expired[/red]\n\n"
                    "[dim]Please run [white]runagent setup[/white] again to try again[/dim]",
                    title="[bold red]Expired[/bold red]",
                    border_style="red",
                )
            )
            raise click.ClickException(str(e))

        except PermissionError as e:
            console.print(
                Panel(
                    "[red]❌ Authentication cancelled[/red]\n\n"
                    "[dim]You cancelled the authentication in your browser.[/dim]",
                    title="[bold red]Cancelled[/bold red]",
                    border_style="red",
                )
            )
            raise click.ClickException(str(e))

        except (ValueError, KeyError) as e:
            console.print(
                Panel(
                    "[red]❌ Unexpected response from server[/red]\n\n"
                    "[dim]Please contact support if this persists.[/dim]",
                    title="[bold red]Error[/bold red]",
                    border_style="red",
                )
            )
            if os.getenv("DISABLE_TRY_CATCH"):
                console.print(f"[dim]Debug info: {str(e)}[/dim]")
            raise click.ClickException(str(e))

        except (HttpException, HttpConnectionError) as e:
            console.print(
                Panel(
                    "[red]❌ Connection error[/red]\n\n"
                    "[dim]Unable to connect to authentication service.\n"
                    "Please check your internet connection.[/dim]",
                    title="[bold red]Network Error[/bold red]",
                    border_style="red",
                )
            )
            if os.getenv("DISABLE_TRY_CATCH"):
                console.print(f"[dim]Debug info: {str(e)}[/dim]")
            raise click.ClickException(str(e))

    def _display_instructions(self, user_code: str, verification_uri: str) -> None:
        """
        Display authentication instructions to user.

        Args:
            user_code: User code to enter in browser
            verification_uri: URI for user to visit
        """
        console.print()

        # Create a nice panel with instructions
        instruction_text = (
            f"[bold white]Open your browser and visit:[/bold white]\n\n"
            f"[bold cyan]{verification_uri}[/bold cyan]\n\n"
            f"[bold white]Then enter this code:[/bold white]\n\n"
            f"[bold yellow]{user_code}[/bold yellow]"
        )

        console.print(
            Panel(
                instruction_text,
                title="[bold cyan]🔐 Authenticate via Browser[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        # Try to auto-open browser
        try:
            click.launch(verification_uri)
            console.print("[dim]✓ Browser opened automatically[/dim]\n")
        except Exception:
            console.print("[dim]💡 Copy the link above and open it in your browser\n[/dim]")

    def _poll_until_complete(
        self, device_code: str, interval: int, expires_in: int
    ) -> str:
        """
        Poll for device code completion.

        Args:
            device_code: Device code from initial flow
            interval: Polling interval in seconds
            expires_in: Expiration time in seconds

        Returns:
            API key on successful authentication

        Raises:
            TimeoutError: If device code expires
            PermissionError: If user cancels authentication
            ValueError: If unexpected status received
        """
        start_time = time.time()
        timeout = expires_in

        with Status(
            "[bold cyan]🔄 Waiting for browser authentication...[/bold cyan]",
            spinner="dots",
            console=console,
        ) as status:
            while True:
                elapsed = time.time() - start_time

                # Check timeout
                if elapsed > timeout:
                    raise TimeoutError("Device code has expired")

                # Poll for completion
                try:
                    response = self.client.poll_for_completion(device_code)
                    status_value = response.get("status")

                    if status_value == "completed":
                        api_key = response.get("api_key")
                        if not api_key:
                            raise ValueError("No API key in response")

                        console.print()
                        console.print(
                            Panel(
                                "[bold green]✅ Authentication successful![/bold green]\n\n"
                                "[dim]Credentials saved securely.[/dim]",
                                title="[bold green]Success[/bold green]",
                                border_style="green",
                            )
                        )
                        return api_key

                    elif status_value == "pending":
                        remaining = int(timeout - elapsed)
                        status.update(
                            f"[bold cyan]🔄 Waiting for browser authentication... ({remaining}s)[/bold cyan]"
                        )
                        time.sleep(interval)

                    elif status_value == "expired":
                        raise TimeoutError("Device code has expired")

                    elif status_value == "access_denied":
                        raise PermissionError("Authentication was cancelled")

                    else:
                        raise ValueError(f"Unexpected status: {status_value}")

                except (HttpException, HttpConnectionError):
                    # Check if we've exceeded timeout before retrying
                    if elapsed > timeout:
                        raise TimeoutError("Device code has expired")
                    # Otherwise, retry after interval
                    time.sleep(interval)

    def _validate_and_extract_user_info(self, api_key: str) -> t.Dict[str, t.Any]:
        """
        Validate API key and extract user information.
        Uses the same validation endpoint as manual setup.

        Args:
            api_key: API key to validate

        Returns:
            Dictionary containing user information

        Raises:
            ValueError: If validation fails or response format is invalid
        """
        try:
            from runagent.sdk.rest_client import HttpHandler

            # Create HTTP handler with the API key
            http_handler = HttpHandler(api_key=api_key, base_url=self.base_url)

            # Validate token using the same endpoint as manual setup
            response = http_handler.post(
                f"/api/v1/tokens/validate?token={api_key}",
                data={},
                handle_errors=True
            )

            token_data = response.json()

            # Check if token validation was successful
            if token_data.get("success") and token_data.get("data", {}).get("valid"):
                data = token_data.get("data", {})

                user_info = {
                    "email": data.get("user_email"),
                    "user_id": data.get("user_id"),
                    "tier": data.get("user_tier", "Free"),
                    "active_project_name": data.get("default_project_name"),
                    "active_project_id": data.get("default_project_id"),
                }

                return user_info
            else:
                error_msg = token_data.get("error", "Token validation failed")
                raise ValueError(error_msg)

        except (HttpException, HttpConnectionError) as e:
            console.print(
                Panel(
                    "[red]❌ Failed to validate credentials[/red]\n\n"
                    "[dim]Could not retrieve user information from server.[/dim]",
                    title="[bold red]Validation Error[/bold red]",
                    border_style="red",
                )
            )
            raise ValueError(f"Credential validation failed: {str(e)}")
