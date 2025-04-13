# runagent/api.py
"""
API interaction logic for RunAgent.
"""

import os
import requests
import logging
from typing import Dict, Any, Optional
import json

from .exceptions import ApiError, AuthenticationError

logger = logging.getLogger(__name__)

class ApiClient:
    """Base API client for interacting with the RunAgent service."""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        
        if not api_key:
            raise AuthenticationError("API key is required")
    
    def _get_headers(self, additional_headers=None):
        """Get the headers for an API request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if additional_headers:
            headers.update(additional_headers)
            
        return headers
    
    def request(self, method, endpoint, **kwargs):
        """Make an authenticated request to the API."""
        headers = self._get_headers(kwargs.pop("headers", {}))
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                **kwargs
            )
            
            response.raise_for_status()
            
            # If JSON response, parse it
            if response.headers.get("Content-Type", "").startswith("application/json"):
                return response.json()
            
            return response.text
            
        except requests.exceptions.HTTPError as e:
            # Try to parse error response
            error_msg = str(e)
            try:
                error_data = e.response.json()
                if "detail" in error_data:
                    error_msg = error_data["detail"]
            except:
                pass
            
            raise ApiError(
                f"API request failed: {error_msg}",
                status_code=e.response.status_code if hasattr(e, "response") else None,
                response=e.response if hasattr(e, "response") else None
            )
        except requests.exceptions.RequestException as e:
            raise ApiError(f"Request failed: {e}")
    
    def get(self, endpoint, **kwargs):
        """Make a GET request."""
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint, **kwargs):
        """Make a POST request."""
        return self.request("POST", endpoint, **kwargs)
    
    def put(self, endpoint, **kwargs):
        """Make a PUT request."""
        return self.request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint, **kwargs):
        """Make a DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)
        
    def upload_file(self, endpoint, file_path, file_param_name="file", additional_data=None):
        """Upload a file to the API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            # Content-Type will be set automatically by requests
        }
        
        with open(file_path, "rb") as f:
            files = {file_param_name: f}
            data = additional_data or {}
            
            logger.debug(f"Uploading file {file_path} to {url}")
            
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data
                )
                
                response.raise_for_status()
                
                # If JSON response, parse it
                if response.headers.get("Content-Type", "").startswith("application/json"):
                    return response.json()
                
                return response.text
                
            except requests.exceptions.HTTPError as e:
                # Try to parse error response
                error_msg = str(e)
                try:
                    error_data = e.response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                
                raise ApiError(
                    f"File upload failed: {error_msg}",
                    status_code=e.response.status_code if hasattr(e, "response") else None,
                    response=e.response if hasattr(e, "response") else None
                )
            except requests.exceptions.RequestException as e:
                raise ApiError(f"File upload request failed: {e}")
