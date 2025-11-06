"""Device Code Authentication Client

Handles HTTP communication with device code authentication endpoints.
"""

import os
import secrets
import typing as t

from runagent.sdk.rest_client import HttpHandler


class DeviceCodeClient:
    """HTTP client for device code authentication flow"""

    def __init__(self, base_url: str) -> None:
        """
        Initialize device code client.

        Args:
            base_url: Base URL for API endpoints
        """
        self.base_url = base_url.rstrip("/")
        self.session_secret = secrets.token_urlsafe(32)
        # Use the existing HttpHandler from rest_client
        # No API key needed for device code flow
        self.http = HttpHandler(base_url=self.base_url)

    def initiate_device_flow(self) -> t.Dict[str, t.Any]:
        """
        Initiate device code authentication flow.

        Returns:
            Dictionary containing device_code, user_code, verification_uri,
            expires_in, and interval

        Raises:
            HttpException: If HTTP request fails
        """
        payload = {"session_secret": self.session_secret}

        # Make POST request to device initiate endpoint
        response = self.http.post(
            "/api/v1/auth/device/initiate",
            data=payload,
            handle_errors=True
        )
        return response.json()

    def poll_for_completion(self, device_code: str) -> t.Dict[str, t.Any]:
        """
        Poll for device code completion.

        Args:
            device_code: Device code from initial flow

        Returns:
            Dictionary containing status and api_key (if completed)

        Raises:
            HttpException: If HTTP request fails
        """
        headers = {"X-Session-Secret": self.session_secret}
        params = {"device_code": device_code}

        # Make GET request to device poll endpoint
        response = self.http.get(
            "/api/v1/auth/device/poll",
            params=params,
            headers=headers,
            handle_errors=True
        )
        return response.json()
