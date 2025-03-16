"""
Jellyfin API client for interacting with Jellyfin servers.
"""

import logging
import requests
import uuid
from base64 import b64encode
from typing import Dict, List, Optional, Any

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
            username (str, optional): Username for authentication (used if api_key not provided)
            password (str, optional): Password for authentication (used if api_key not provided)
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        # Generate a unique device ID instead of hardcoding
        self.device_id = str(uuid.uuid4())
        self.auth_header = f'MediaBrowser Client="jellytools", Device="python-script", DeviceId="{self.device_id}", Version="1.0.0"'
        
        # Set initial headers
        self._headers = {"Content-Type": "application/json"}
        
        # Authenticate based on what credentials were provided
        if api_key:
            # Use API key auth
            self._headers["X-Emby-Token"] = api_key
            
            # Get user ID
            users = self._get("/users")
            if not users:
                raise ValueError("Failed to retrieve Jellyfin users using API key")
            self.user_id = users[0]["Id"]
            
            logger.info(f"Connected to Jellyfin as user ID: {self.user_id} using API key")
            
        elif username and password:
            # Use username/password auth
            self._headers["Authorization"] = self.auth_header
            auth_data = {"username": username, "Pw": password}
            
            try:
                # Authenticate to get token
                auth_result = self._post("/Users/AuthenticateByName", data=auth_data)
                self.api_key = auth_result.get("AccessToken")
                self.user_id = auth_result.get("User").get("Id")
                
                # Update headers with token
                self._headers["X-Emby-Token"] = self.api_key
                
                logger.info(f"Connected to Jellyfin as user {username} (ID: {self.user_id})")
                
            except Exception as e:
                raise ValueError(f"Failed to authenticate with Jellyfin: {e}")
                
        else:
            raise ValueError("Either api_key or both username and password must be provided")

    def _request(
        self,
        verb: str,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        binary_data: Optional[bytes] = None,
        raw_response: bool = False,
    ):
        """
        Make an HTTP request to the Jellyfin API.

        Args:
            verb (str): HTTP method (get, post, delete)
            path (str): API endpoint path
            params (dict): Query parameters
            data (dict): Request body data for POST requests (JSON)
            headers (dict): Optional headers to override defaults
            binary_data (bytes): Raw binary data for POST requests
            raw_response (bool): Return raw response

        Returns:
            dict, bytes, or response object: JSON response from the API, raw bytes,
            or raw response object
        """
        # Make sure path starts with a slash
        if not path.startswith("/"):
            path = "/" + path

        # Build the full URL
        full_url = f"{self.url}{path}"
        params = params or {}

        # Use provided headers or default headers
        request_headers = headers or self._headers.copy()

        try:
            if verb.lower() == "get":
                r = requests.get(full_url, headers=request_headers, params=params)
            elif verb.lower() == "post":
                if binary_data:
                    r = requests.post(
                        full_url,
                        headers=request_headers,
                        params=params,
                        data=binary_data,
                    )
                elif data:
                    r = requests.post(
                        full_url, headers=request_headers, params=params, json=data
                    )
                else:
                    r = requests.post(full_url, headers=request_headers, params=params)
            elif verb.lower() == "delete":
                r = requests.delete(full_url, headers=request_headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {verb}")

            r.raise_for_status()

            if raw_response:
                return r

            # If the response is JSON, parse it; otherwise return raw content
            if "application/json" in r.headers.get("Content-Type", ""):
                return r.json() if r.content else {}
            return r.content

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error ({verb.upper()} {path}): {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    if "application/json" in e.response.headers.get("Content-Type", ""):
                        error_msg = e.response.json()
                        logger.error(f"Server response: {error_msg}")
                    else:
                        logger.error(f"Status code: {e.response.status_code}")
                        logger.error(f"Response text: {e.response.text[:200]}...")
                except Exception as parse_error:
                    logger.error(f"Failed to parse error response: {parse_error}")
                    logger.error(f"Status code: {e.response.status_code}")
                    logger.error(
                        f"Response text: {e.response.text[:200] if hasattr(e.response, 'text') else 'No text'}..."
                    )
            raise

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the Jellyfin API."""
        return self._request("get", path, params)

    def _post(
        self,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        binary_data: Optional[bytes] = None,
    ) -> Dict:
        """Make a POST request to the Jellyfin API."""
        return self._request("post", path, params, data, headers, binary_data)

    def _delete(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a DELETE request to the Jellyfin API."""
        return self._request("delete", path, params)

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
            return self._get(f"/Users/{self.user_id}/Items/{item_id}")
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            return {}

    def create_collection(self, name: str, ids: List[str]) -> Dict:
        """
        Create a new collection with the given items, handling large collections by creating
        them in chunks to avoid URL length limitations.

        Args:
            name (str): Collection name
            ids (list): List of item IDs to include

        Returns:
            dict: Collection details
        """
        if not ids:
            return {"Status": "No items to add to collection"}

        # First, create an empty collection
        logger.info(f"Creating collection '{name}'...")
        result = self._post("/Collections", {"Name": name, "Ids": ""})

        if not result or "Id" not in result:
            raise Exception(f"Failed to create collection: {result}")

        collection_id = result["Id"]

        # Then add items in chunks to avoid URL length limitations
        CHUNK_SIZE = 50  # Adjust based on your server's limitations
        total_chunks = (len(ids) + CHUNK_SIZE - 1) // CHUNK_SIZE

        for i in range(0, len(ids), CHUNK_SIZE):
            chunk = ids[i : i + CHUNK_SIZE]
            chunk_num = (i // CHUNK_SIZE) + 1
            logger.info(
                f"Adding chunk {chunk_num}/{total_chunks} ({len(chunk)} items) to collection '{name}'..."
            )

            try:
                # Add items to the collection
                self._post(
                    f"/Collections/{collection_id}/Items", {"Ids": ",".join(chunk)}
                )
            except Exception as e:
                logger.error(
                    f"Error adding chunk {chunk_num} to collection '{name}': {e}"
                )
                # Continue with next chunk even if this one fails

        return {
            "Status": f"Collection '{name}' created with {len(ids)} items in {total_chunks} chunks",
            "Id": collection_id,
        }

    def add_to_collection(self, collection_id: str, ids: List[str]) -> Dict:
        """
        Add items to an existing collection.

        Args:
            collection_id (str): Collection ID
            ids (list): List of item IDs to add

        Returns:
            dict: Response from the server
        """
        if not ids:
            return {"Status": "No items to add"}

        # Add items in chunks to avoid URL length limitations
        CHUNK_SIZE = 50  # Adjust based on your server's limitations
        total_chunks = (len(ids) + CHUNK_SIZE - 1) // CHUNK_SIZE

        for i in range(0, len(ids), CHUNK_SIZE):
            chunk = ids[i : i + CHUNK_SIZE]
            chunk_num = (i // CHUNK_SIZE) + 1
            logger.info(
                f"Adding chunk {chunk_num}/{total_chunks} ({len(chunk)} items) to collection..."
            )

            try:
                # Add items to the collection
                self._post(
                    f"/Collections/{collection_id}/Items", {"Ids": ",".join(chunk)}
                )
            except Exception as e:
                logger.error(f"Error adding chunk {chunk_num} to collection: {e}")
                # Continue with next chunk even if this one fails

        return {
            "Status": f"Added {len(ids)} items to collection in {total_chunks} chunks"
        }

    def remove_collection(self, collection_id: str) -> Dict:
        """
        Delete a collection.

        Args:
            collection_id (str): Collection ID

        Returns:
            dict: Response from the server
        """
        return self._delete(f"/Items/{collection_id}")

    def collections_list(self) -> Dict:
        """
        Get all collections.

        Returns:
            dict: List of collections
        """
        return self._get(
            f"/Users/{self.user_id}/Items",
            {"IncludeItemTypes": "BoxSet", "Recursive": "true"},
        )

    def libraries_list(self) -> Dict:
        """
        Get all libraries (also known as views) in the Jellyfin server.

        Returns:
            dict: List of libraries with their details
        """
        # Use the /Library/MediaFolders endpoint to get all media folders
        # This is more reliable than filtering the root items
        try:
            return self._get("/Library/MediaFolders")
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
        url = f"/Items/{item_id}/Images/{image_type}/0"
        try:
            response = self._request(verb="get", path=url, raw_response=True)

            if response.status_code != 200:
                logger.debug(f"Image not found for item {item_id}, type {image_type}")
                return None

            extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
                response.headers.get("content-type", ""), "jpg"
            )

            return {"image_data": response.content, "extension": extension}
        except Exception as e:
            logger.error(f"Error downloading image for item {item_id}: {e}")
            return None

    def upload_image(
        self, item_id: str, image_type: str, image_data: bytes, image_ext: str = "jpg"
    ) -> bool:
        """
        Upload an image to an item in Jellyfin using base64 encoding.

        Args:
            item_id (str): ID of the item
            image_type (str): Type of image ('Primary', 'Backdrop', etc.)
            image_data (bytes): Raw image data
            image_ext (str): Image extension to determine content type

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First check if the item exists and is accessible
            if not self.item_exists(item_id):
                logger.error(f"Cannot upload image to item {item_id} - it does not exist or is not accessible")
                return False
            
            # Determine content type based on extension
            content_type = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
            }.get(image_ext.lower(), "image/jpeg")

            # Base64 encode the image data
            encoded_data = b64encode(image_data)

            # Set up the URL and headers - try user-specific endpoint first
            url = f"/Items/{item_id}/Images/{image_type}/0"
            headers = {"X-Emby-Token": self.api_key, "Content-Type": content_type}

            # Make the request
            self._post(url, headers=headers, binary_data=encoded_data)
            logger.info(f"Successfully uploaded {image_type} image for item {item_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload image for item {item_id}: {e}")
            return False
            
    def item_exists(self, item_id: str) -> bool:
        """
        Check if an item exists and is accessible to the current user.
        
        Args:
            item_id (str): Jellyfin item ID
            
        Returns:
            bool: True if the item exists and is accessible, False otherwise
        """
        try:
            item_metadata = self._get(f"/Users/{self.user_id}/Items/{item_id}")
            return bool(item_metadata and "Id" in item_metadata)
        except Exception as e:
            logger.debug(f"Item {item_id} does not exist or is not accessible: {e}")
            return False
    
    def check_image_exists(self, item_id: str, image_type: str, detailed_logging: bool = False) -> bool:
        """
        Check if an image of the specified type already exists for an item.
        
        Args:
            item_id (str): Jellyfin item ID
            image_type (str): Image type (Primary, Backdrop, etc.)
            detailed_logging (bool): Whether to log detailed debug information
            
        Returns:
            bool: True if image exists, False otherwise
        """
        try:
            # First get the item details using the user-specific endpoint
            # This is safer than directly using /Items/{id}
            item_details = self._get(f"/Users/{self.user_id}/Items/{item_id}")
            item_name = item_details.get("Name", "Unknown")
            item_type = item_details.get("Type", "Unknown")
            
            # Use the metadata to check for images, which is more reliable
            # Check for primary image
            if image_type == "Primary" and "ImageTags" in item_details:
                has_primary = item_details.get("ImageTags", {}).get("Primary", False)
                if has_primary:
                    if detailed_logging:
                        logger.debug(f"Primary image exists for {item_type} '{item_name}' (ID: {item_id})")
                    return True
            
            # Check for backdrop image
            if image_type == "Backdrop" and "BackdropImageTags" in item_details:
                backdrop_tags = item_details.get("BackdropImageTags", [])
                if backdrop_tags and len(backdrop_tags) > 0:
                    if detailed_logging:
                        logger.debug(f"Backdrop image exists for {item_type} '{item_name}' (ID: {item_id})")
                    return True
                    
            # Check for banner image - many items don't support banner images
            if image_type == "Banner" and "ImageTags" in item_details:
                has_banner = item_details.get("ImageTags", {}).get("Banner", False)
                if has_banner:
                    if detailed_logging:
                        logger.debug(f"Banner image exists for {item_type} '{item_name}' (ID: {item_id})")
                    return True
                    
                # For items without Banner support, return True to avoid unnecessary requests
                if image_type == "Banner" and item_type in ["Movie", "Episode"]:
                    if detailed_logging:
                        logger.debug(f"Banner image not supported for {item_type} '{item_name}' (skipping)")
                    return True
            
            # If no image found for the given type and content type supports it, return False
            if detailed_logging:
                logger.debug(f"No {image_type} image found for {item_type} '{item_name}' (ID: {item_id})")
            return False
                
        except Exception as e:
            logger.warning(f"Error checking if image exists for item {item_id}: {e}")
            # If we can't check, assume it doesn't exist
            return False
