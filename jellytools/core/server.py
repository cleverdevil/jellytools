"""
Server manager for the library card generator.
"""
import os
import sys
import logging
import pathlib
from typing import Dict, Any, Optional, List

from jellytools.api.jellyfin import JellyfinClient
from jellytools.core.config import get_config

logger = logging.getLogger(__name__)


class ServerManager:
    """Manages connection to the Jellyfin media server"""

    def __init__(self):
        """Initialize the server manager and connect to configured servers."""
        self.servers = {}
        self._connect_to_servers()

    def _connect_to_servers(self):
        """Connect to the Jellyfin media server."""
        config = get_config()

        # Connect to Jellyfin - support both API key and username/password authentication
        if hasattr(config, "JELLYFIN_URL"):
            logger.info(f"Connecting to Jellyfin at {config.JELLYFIN_URL}...")
            try:
                # Always provide both auth methods if available
                kwargs = {
                    "url": config.JELLYFIN_URL
                }
                
                # Add API key if available
                if hasattr(config, "JELLYFIN_API_KEY") and config.JELLYFIN_API_KEY:
                    kwargs["api_key"] = config.JELLYFIN_API_KEY
                
                # Add username/password if available
                if hasattr(config, "JELLYFIN_USERNAME") and hasattr(config, "JELLYFIN_PASSWORD"):
                    kwargs["username"] = config.JELLYFIN_USERNAME
                    kwargs["password"] = config.JELLYFIN_PASSWORD
                
                # Check if we have enough credentials to connect
                if "api_key" in kwargs or ("username" in kwargs and "password" in kwargs):
                    logger.info(f"Connecting to Jellyfin with {', '.join(k for k in kwargs.keys() if k != 'url')} auth...")
                    self.servers["jellyfin"] = JellyfinClient(**kwargs)
                else:
                    logger.error("No valid Jellyfin credentials found. Need either API_KEY or USERNAME+PASSWORD")
                    
                if "jellyfin" in self.servers:
                    logger.info("Successfully connected to Jellyfin")
            except Exception as e:
                logger.error(f"Failed to connect to Jellyfin: {e}")

        if len(self.servers) == 0:
            logger.info("Configuration contains no server information. Exiting.")
            sys.exit(0)

        # Log the available servers
        if "jellyfin" in self.servers:
            logger.info("Jellyfin server connected and available for operations")
        else:
            logger.warning("Jellyfin server not configured - some features may not work")

    def download_jellyfin_posters(self, libraries: List[str] = None) -> Dict[str, Any]:
        """
        Download jellyfin primary posters.

        Args:
            libraries (List[str], optional): List of library names to process.
                                           If None, all configured libraries will be processed.

        Returns:
            Dict[str, Any]: Dictionary with download statistics
                Format: {
                    'downloaded': {library_name: count, ...},
                    'skipped': {library_name: count, ...}
                }
        """
        config = get_config()

        if "jellyfin" not in self.servers:
            logger.warning("Jellyfin server not configured. Skipping poster download.")
            return {'downloaded': {}, 'skipped': {}}

        jellyfin = self.servers["jellyfin"]
        
        # Statistics to return
        stats = {
            'downloaded': {},
            'skipped': {}
        }
        
        # Use all configured libraries if none specified
        if libraries is None:
            libraries = config.JELLYFIN_LIBRARIES

        # Get all libraries from Jellyfin
        library_result = jellyfin.libraries_list()
        jellyfin_libraries = library_result.get("Items", [])
        
        # Map of library names to IDs for faster lookup
        library_map = {
            lib.get("Name"): lib.get("Id") 
            for lib in jellyfin_libraries 
            if lib.get("Name") and lib.get("Id")
        }
        
        # Fallback method if libraries not found
        if not library_map:
            logger.warning("No libraries found using standard method, trying alternative...")
            items = jellyfin.items_list()
            for item in items.get("Items", []):
                if item.get("Type") in ["CollectionFolder", "UserView", "Folder"] and item.get("Name"):
                    library_map[item.get("Name")] = item.get("Id")

        # Process each library
        for library_name in libraries:
            logger.info(f"Processing Jellyfin {library_name} library...")
            
            # Initialize stats for this library
            stats['downloaded'][library_name] = 0
            stats['skipped'][library_name] = 0

            # Find the library by name
            library_id = library_map.get(library_name)
            
            if not library_id:
                logger.warning(f"No '{library_name}' library found in Jellyfin")
                
                # Print available libraries for debugging
                available_libraries = list(library_map.keys())
                if available_libraries:
                    logger.info(f"Available libraries: {', '.join(available_libraries)}")
                else:
                    logger.warning("No libraries were found on the server")
                
                # Skip this library
                continue

            # Get library type for filtering
            library_type = None
            for lib in jellyfin_libraries:
                if lib.get("Id") == library_id:
                    library_type = lib.get("CollectionType", lib.get("Type", "Unknown"))
                    break
                    
            logger.info(f"Processing {library_name} (type: {library_type or 'Unknown'})")

            # Use recursive parameter to get all items at once with all fields
            library_contents = jellyfin.items_list(
                parentId=library_id, recursive=True, include_fields=True
            )

            # Create library directory
            poster_path = pathlib.Path(config.POSTER_DIRECTORY) / library_name
            poster_path.mkdir(parents=True, exist_ok=True)

            # List items for later use
            existing_files = list(poster_path.iterdir())

            def poster_exists(item):
                return bool([fn for fn in existing_files if item["Id"] in fn.name])

            # Process each item, fetching the primary image
            download_count = 0
            skipped_count = 0
            processed_count = 0
            
            for item in library_contents.get("Items", []):
                processed_count += 1
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} items in {library_name}...")
                
                # Special handling for different library types
                item_type = item.get("Type", "")

                # Regular libraries: Skip folders, collections, and other non-media items
                # For BoxSet/Collections libraries: Process BoxSet items and skip others
                if library_type != "boxsets" and item_type in [
                    "Folder", "CollectionFolder", "UserView", "BoxSet", "Season", "Episode"
                ]:
                    continue
                elif library_type == "boxsets" and item_type != "BoxSet":
                    # If we're in the Collections library, only process BoxSet items
                    continue

                # Skip already downloaded posters
                if poster_exists(item):
                    skipped_count += 1
                    stats['skipped'][library_name] += 1
                    continue

                # Download primary image
                try:
                    response = jellyfin.download_image(item["Id"])
                    if not response:
                        logger.debug(f"No poster available for item {item['Id']} ({item.get('Name', 'Unknown')})")
                        continue
                except Exception as e:
                    logger.debug(f"Unable to download poster for item {item['Id']} ({item.get('Name', 'Unknown')}): {e}")
                    continue

                # Determine poster file path
                filename = poster_path / f"{item['Id']}.{response['extension']}"

                # Write to output directory
                with open(filename, "wb") as f:
                    f.write(response["image_data"])
                    
                download_count += 1
                stats['downloaded'][library_name] += 1

            logger.info(
                f"Downloaded {download_count} and skipped {skipped_count} posters from {library_name}."
            )

        # Calculate totals for logging
        total_downloaded = sum(stats['downloaded'].values())
        total_skipped = sum(stats['skipped'].values())
        logger.info(
            f"Total: Downloaded {total_downloaded} new images, skipped {total_skipped} existing images"
        )
        
        return stats

    def get_jellyfin_client(self) -> Optional[JellyfinClient]:
        """
        Get the Jellyfin client if available.

        Returns:
            Optional[JellyfinClient]: Jellyfin client or None if not available
        """
        return self.servers.get("jellyfin")
