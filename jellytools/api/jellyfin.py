"""
Jellyfin API client wrapper for interacting with Jellyfin servers.
This is a compatibility layer over jellyfin_apiclient_python.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any

from jellyfin_apiclient_python import JellyfinClient as ThirdPartyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JellyfinClient:
    """Client for interacting with the Jellyfin API."""

    def __init__(self, url: str, api_key: str = None, username: str = None, password: str = None):
        """
        Initialize the Jellyfin client.

        Args:
            url (str): Base URL of the Jellyfin server
            api_key (str, optional): API key for authentication
            username (str, optional): Username for authentication
            password (str, optional): Password for authentication
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self.authentication_successful = False
        
        # Generate a unique device ID
        self.device_id = str(uuid.uuid4())
        
        # Initialize the third-party client
        self.client = ThirdPartyClient()
        
        # Configure the client
        self.client.config.app(
            name="jellytools",
            version="1.0.0",
            device_name="python-script",
            device_id=self.device_id
        )
        
        # Set SSL verification based on URL
        self.client.config.data["auth.ssl"] = self.url.startswith("https")
        
        # Authenticate using the best method available
        self._authenticate()
        
        if not self.authentication_successful:
            raise ValueError("Failed to authenticate with Jellyfin. Check credentials and server URL.")
    
    def _authenticate(self):
        """Try multiple authentication methods until one succeeds."""
        # First try with API key if provided
        if self.api_key:
            try:
                self._authenticate_with_api_key()
                return
            except Exception as e:
                logger.warning(f"API key authentication failed: {str(e)}")
                
                # If API key authentication failed but we have username/password,
                # don't give up yet - we'll try that next
                if not (self.username and self.password):
                    logger.error("API key authentication failed and no username/password provided")
                    raise
        
        # Try username/password auth if provided
        if self.username and self.password:
            try:
                self._authenticate_with_credentials()
                return
            except Exception as e:
                logger.error(f"Username/password authentication failed: {str(e)}")
                raise
        
        # If we got here with no credentials, raise an error
        if not self.api_key and not (self.username and self.password):
            raise ValueError("Either api_key or both username and password must be provided")
            
    def _authenticate_with_api_key(self):
        """Authenticate using API key."""
        try:
            # Connect to the server address first
            result = self.client.auth.connect_to_address(self.url)
            if not result or 'State' not in result:
                raise ValueError(f"Failed to connect to server: {self.url}")
            
            # Set token directly in all required places
            self.client.config.data["auth.token"] = self.api_key
            
            # Find server ID from the connection result
            if result.get('Servers') and len(result.get('Servers', [])) > 0:
                server_id = result['Servers'][0].get('Id')
                self.client.auth.server_id = server_id
                
                # Set server token
                for server in self.client.auth.credentials.get_credentials().get('Servers', []):
                    if server.get('Id') == server_id:
                        server['AccessToken'] = self.api_key
                        self.client.auth.credentials.set_credentials(self.client.auth.credentials.get_credentials())
                        break
            
            # We need to get user_id for future calls
            self.client.auth.config.data["auth.server"] = self.url
            
            # Start the HTTP session
            self.client.http.start_session()
            
            # Try a direct request to test the token
            import requests
            headers = {"X-Emby-Token": self.api_key}
            test_response = requests.get(f"{self.url}/users", headers=headers)
            
            if test_response.status_code != 200:
                raise ValueError(f"API key authentication failed: HTTP {test_response.status_code}")
            
            users = test_response.json()
            if not users or not isinstance(users, list) or len(users) == 0:
                raise ValueError("Failed to retrieve Jellyfin users using API key")
            
            self.user_id = users[0]["Id"]
            self.client.config.data["auth.user_id"] = self.user_id
            
            # Finally, set the user info on the client
            self.client.logged_in = True
            self.authentication_successful = True
            
            logger.info(f"Connected to Jellyfin as user ID: {self.user_id} using API key")
        except Exception as e:
            logger.error(f"API key authentication error: {str(e)}")
            raise
    
    def _authenticate_with_credentials(self):
        """Authenticate using username and password."""
        try:
            # Bypass the complex auth flow of the library and use a direct request
            # This is more reliable and gives us more control over the process
            import requests
            import json
            
            # Set up the auth endpoint
            auth_url = f"{self.url}/Users/AuthenticateByName"
            
            # Create auth data
            auth_data = {
                "Username": self.username,
                "Pw": self.password
            }
            
            # Set required headers
            headers = {
                "Content-Type": "application/json",
                "X-Emby-Authorization": f'MediaBrowser Client="jellytools", Device="python-script", DeviceId="{self.device_id}", Version="1.0.0"'
            }
            
            # Make the direct request
            auth_response = requests.post(auth_url, headers=headers, json=auth_data)
            
            if auth_response.status_code != 200:
                raise ValueError(f"Failed to authenticate: HTTP {auth_response.status_code} - {auth_response.text}")
            
            # Parse the response
            result = auth_response.json()
            
            if not result or "AccessToken" not in result or "User" not in result:
                raise ValueError(f"Invalid authentication response: {json.dumps(result)}")
            
            # Store user_id and token for future use
            self.user_id = result["User"]["Id"]
            self.api_key = result["AccessToken"]
            
            # Initialize the client with our successful auth
            self.client.http.start_session()
            self.client.logged_in = True
            
            # Ensure auth configuration is properly set
            self.client.config.data["auth.server"] = self.url
            self.client.config.data["auth.user_id"] = self.user_id
            self.client.config.data["auth.token"] = self.api_key
            
            # Set the server ID for future API calls
            if 'ServerId' in result:
                self.client.auth.server_id = result['ServerId']
            
            # Mark authentication as successful
            self.authentication_successful = True
            
            logger.info(f"Connected to Jellyfin as user {self.username} (ID: {self.user_id})")
            
        except Exception as e:
            logger.error(f"Username/password authentication error: {str(e)}")
            raise
    
    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the Jellyfin API."""
        path = path.lstrip("/")
        try:
            # Use direct requests approach instead of the client
            import requests
            
            # Build the full URL - replace any placeholders
            full_url = f"{self.url}/{path}"
            if hasattr(self, 'user_id') and self.user_id:
                full_url = full_url.replace("{UserId}", self.user_id)
            
            # Set up headers with authentication
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["X-Emby-Token"] = self.api_key
            
            # Make the direct request 
            response = requests.get(full_url, headers=headers, params=params)
            
            if response.status_code >= 400:
                logger.error(f"GET {path} failed with status {response.status_code}: {response.text}")
                return {}
            
            # Return empty dict for empty responses
            if not response.content:
                return {}
            
            # Parse JSON responses
            if response.headers.get("Content-Type", "").startswith("application/json"):
                return response.json()
            
            # Return raw content for other responses
            return {"content": response.content}
            
        except Exception as e:
            logger.error(f"Request error (GET {path}): {e}")
            return {}
    
    def _post(self, path: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """Make a POST request to the Jellyfin API."""
        path = path.lstrip("/")
        try:
            # Use direct requests approach instead of the client
            import requests
            
            # Build the full URL - replace any placeholders
            full_url = f"{self.url}/{path}"
            if hasattr(self, 'user_id') and self.user_id:
                full_url = full_url.replace("{UserId}", self.user_id)
            
            # Set up headers with authentication
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["X-Emby-Token"] = self.api_key
            
            # Make the direct request
            response = requests.post(full_url, headers=headers, params=params, json=data if data else None)
            
            if response.status_code >= 400:
                logger.error(f"POST {path} failed with status {response.status_code}: {response.text}")
                return {}
            
            # Return empty dict for empty responses
            if not response.content:
                return {}
            
            # Parse JSON responses
            if response.headers.get("Content-Type", "").startswith("application/json"):
                return response.json()
                
            # Return raw content for other responses
            return {"content": response.content}
            
        except Exception as e:
            logger.error(f"Request error (POST {path}): {e}")
            return {}
    
    def _delete(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a DELETE request to the Jellyfin API."""
        path = path.lstrip("/")
        try:
            # Use direct requests approach instead of the client
            import requests
            
            # Build the full URL - replace any placeholders
            full_url = f"{self.url}/{path}"
            if hasattr(self, 'user_id') and self.user_id:
                full_url = full_url.replace("{UserId}", self.user_id)
            
            # Set up headers with authentication
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["X-Emby-Token"] = self.api_key
            
            # Make the direct request
            response = requests.delete(full_url, headers=headers, params=params)
            
            if response.status_code >= 400:
                logger.error(f"DELETE {path} failed with status {response.status_code}: {response.text}")
                return {}
            
            # Return empty dict for empty responses
            if not response.content:
                return {}
            
            # Parse JSON responses
            if response.headers.get("Content-Type", "").startswith("application/json"):
                return response.json()
                
            # Return raw content for other responses
            return {"content": response.content}
            
        except Exception as e:
            logger.error(f"Request error (DELETE {path}): {e}")
            return {}

    def _request(self, verb: str, path: str, params: Optional[Dict] = None,
                data: Optional[Dict] = None, headers: Optional[Dict] = None,
                binary_data: Optional[bytes] = None, raw_response: bool = False):
        """
        Legacy compatibility method for making HTTP requests to the Jellyfin API.
        """
        import requests
        
        # Build the full URL
        full_url = f"{self.url}/{path.lstrip('/')}"
        if hasattr(self, 'user_id') and self.user_id:
            full_url = full_url.replace("{UserId}", self.user_id)
            
        # Set up default headers
        request_headers = {
            "Content-Type": "application/json"
        }
        
        # Add authentication token
        if self.api_key:
            request_headers["X-Emby-Token"] = self.api_key
            
        # Merge with any custom headers
        if headers:
            request_headers.update(headers)
            
        try:
            if verb.lower() == "get":
                response = requests.get(full_url, headers=request_headers, params=params)
            elif verb.lower() == "post":
                if binary_data:
                    response = requests.post(full_url, headers=request_headers, params=params, data=binary_data)
                elif data:
                    response = requests.post(full_url, headers=request_headers, params=params, json=data)
                else:
                    response = requests.post(full_url, headers=request_headers, params=params)
            elif verb.lower() == "delete":
                response = requests.delete(full_url, headers=request_headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {verb}")
                
            # Check for errors
            response.raise_for_status()
            
            # Return the raw response if requested
            if raw_response:
                return response
                
            # Otherwise parse the content appropriately
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json() if response.content else {}
                
            # Return raw content for non-JSON responses
            return response.content
            
        except Exception as e:
            logger.error(f"Request error ({verb.upper()} {path}): {e}")
            if raw_response:
                return None
            return {}

    def items_list(
        self,
        parentId: Optional[str] = None,
        limit: Optional[int] = None,
        recursive: bool = False,
        include_fields: bool = False,
    ) -> Dict:
        """
        Get a list of items from Jellyfin.

        Args:
            parentId (str): ID of the parent folder
            limit (int): Maximum number of items to return
            recursive (bool): Whether to include items in subfolders
            include_fields (bool): Whether to include additional fields

        Returns:
            dict: JSON response with items
        """
        params = {}
        if parentId:
            params["parentId"] = parentId
        if limit:
            params["limit"] = limit
        if recursive:
            params["recursive"] = "true"

        # Request provider IDs and other fields to avoid additional API calls
        if include_fields:
            params["fields"] = "ProviderIds,Path"

        try:
            return self._get("/Items", params)
        except Exception as e:
            logger.error(f"Error listing items: {e}")
            return {"Items": []}

    def item(self, item_id: str) -> Dict:
        """
        Get details for a specific item.

        Args:
            item_id (str): Item ID

        Returns:
            dict: Item details
        """
        try:
            return self.client.jellyfin.get_item(item_id)
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            return {}





    def libraries_list(self) -> Dict:
        """
        Get all libraries (also known as views) in the Jellyfin server.

        Returns:
            dict: List of libraries with their details
        """
        # Use the third-party client's media_folders method
        try:
            return self.client.jellyfin.media_folders()
        except Exception as e:
            logger.error(f"Error listing libraries: {e}")
            return {"Items": []}

    @staticmethod
    def get_content_type(file_path: str) -> str:
        """
        Get content type based on file extension.

        Args:
            file_path (str): Path to the file

        Returns:
            str: Content type
        """
        ext = file_path.split(".")[-1].lower()
        return {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }.get(ext, "application/octet-stream")

    def download_image(
        self, item_id: str, image_type: str = "Primary"
    ) -> Optional[Dict[str, Any]]:
        """
        Download an image for a specific item.

        Args:
            item_id (str): ID of the item
            image_type (str): Type of image (Primary, Backdrop, etc.)

        Returns:
            Optional[Dict[str, Any]]: Dictionary with image data and extension, or None if not found
        """
        # We need to use the raw HTTP client to get the image data
        try:
            # Fall back to direct HTTP request if the client method doesn't work
            url = f"{self.url}/Items/{item_id}/Images/{image_type}"
            headers = {}
            
            # Add authentication token if available
            if self.api_key:
                headers["X-Emby-Token"] = self.api_key
            
            # Make a direct HTTP request using requests
            import requests
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.debug(f"Image not found for item {item_id}, type {image_type}, status: {response.status_code}")
                return None
            
            # Determine the image extension from content type
            content_type = response.headers.get("content-type", "")
            extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
                content_type, "jpg"
            )
            
            return {"image_data": response.content, "extension": extension}
        except Exception as e:
            logger.error(f"Error downloading image for item {item_id}: {e}")
            return None

            
    
