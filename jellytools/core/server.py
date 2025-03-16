"""
Server manager for the library card generator.
"""
import os
import sys
import logging
import pathlib
from typing import Dict, Any, Optional

from plexapi.server import PlexServer
from jellytools.api.jellyfin import JellyfinClient
from jellytools.core.config import get_config

logger = logging.getLogger(__name__)


class ServerManager:
    """Manages connections to media servers (Plex, Jellyfin)"""

    def __init__(self):
        """Initialize the server manager and connect to configured servers."""
        self.servers = {}
        self._connect_to_servers()

    def _connect_to_servers(self):
        """Connect to all configured media servers."""
        config = get_config()

        if hasattr(config, "PLEX_URL") and hasattr(config, "PLEX_TOKEN"):
            logger.info(f"Connecting to Plex at {config.PLEX_URL}...")
            try:
                self.servers["plex"] = PlexServer(config.PLEX_URL, config.PLEX_TOKEN)
                logger.info("Successfully connected to Plex")
            except Exception as e:
                logger.error(f"Failed to connect to Plex: {e}")

        # Connect to Jellyfin - support both API key and username/password authentication
        if hasattr(config, "JELLYFIN_URL"):
            logger.info(f"Connecting to Jellyfin at {config.JELLYFIN_URL}...")
            try:
                # First try API key auth
                if hasattr(config, "JELLYFIN_API_KEY") and config.JELLYFIN_API_KEY:
                    self.servers["jellyfin"] = JellyfinClient(
                        url=config.JELLYFIN_URL, 
                        api_key=config.JELLYFIN_API_KEY
                    )
                # Otherwise try username/password auth
                elif hasattr(config, "JELLYFIN_USERNAME") and hasattr(config, "JELLYFIN_PASSWORD"):
                    self.servers["jellyfin"] = JellyfinClient(
                        url=config.JELLYFIN_URL, 
                        username=config.JELLYFIN_USERNAME,
                        password=config.JELLYFIN_PASSWORD
                    )
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

        if "plex" in self.servers:
            logger.info("Plex server connected and available for syncing")
        else:
            logger.info("Plex server not configured - syncing operations will be unavailable")


    def download_jellyfin_posters(self) -> Dict[str, Any]:
        """
        Download jellyfin primary posters.

        Returns:
            Dict[str, Any]: Dictionary of media items
        """
        config = get_config()

        if "jellyfin" not in self.servers:
            logger.warning("Jellyfin server not configured. Skipping poster download.")
            return {}

        jf_media = {}
        jellyfin = self.servers["jellyfin"]

        # Process each library type configured in JELLYFIN_LIBRARIES
        for library_name in config.JELLYFIN_LIBRARIES:
            logger.info(f"Fetching Jellyfin {library_name} library...")

            # Get all libraries using the dedicated method
            library_result = jellyfin.libraries_list()
            libraries = library_result.get("Items", [])

            # Find the library by name
            library_items = [lib for lib in libraries if lib.get("Name") == library_name]

            if not library_items:
                logger.warning(f"No '{library_name}' library found in Jellyfin")

                # Print available libraries for debugging
                available_libraries = [lib.get("Name", "Unknown") for lib in libraries]
                if available_libraries:
                    logger.info(f"Available libraries: {', '.join(available_libraries)}")
                else:
                    logger.warning("No libraries were found on the server")

                # Fall back to the old method as a backup
                logger.info("Trying alternative method to find the library...")
                items = jellyfin.items_list()
                for item in items.get("Items", []):
                    if item.get("Name") == library_name and item.get("Type") in ["CollectionFolder", "UserView", "Folder"]:
                        library_items = [item]
                        logger.info(f"Found library {library_name} using alternative method")
                        break

                if not library_items:
                    logger.warning(f"Still couldn't find library {library_name}. Skipping.")
                    continue

            library_id = library_items[0]["Id"]
            library_type = library_items[0].get("CollectionType", library_items[0].get("Type", "Unknown"))
            logger.info(f"Processing {library_name} (type: {library_type})")

            # Use recursive parameter to get all items at once with all fields
            library_contents = jellyfin.items_list(
                parentId=library_id, recursive=True, include_fields=True
            )

            # Create library directory
            poster_path = pathlib.Path("/".join((config.POSTER_DIRECTORY, library_name)))
            os.makedirs(poster_path, exist_ok=True)

            # List items for later use
            existing_files = os.listdir(poster_path)

            def poster_exists(item):
                return bool([fn for fn in existing_files if item["Id"] in fn])

            # Process each item, fetching the primary image and saving it to a
            # our target directory
            item_count = 0
            skipped_count = 0
            for item in library_contents.get("Items", []):
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
                    continue

                item_count += 1
                if item_count % 100 == 0:
                    logger.info(f"Processed {item_count} items in {library_name}...")

                # Download primary image
                try:
                    response = jellyfin.download_image(item["Id"])
                    if not response:
                        logger.info(f"No poster available for item {item['Id']} ({item.get('Name', 'Unknown')})")
                        continue
                except Exception as e:
                    logger.info(f"Unable to download poster for item {item['Id']} ({item.get('Name', 'Unknown')}): {e}")
                    continue

                # Determine poster file path
                filename = poster_path / ".".join((item["Id"], response["extension"]))

                # Write to output directory
                with open(filename, "wb") as f:
                    f.write(response["image_data"])

            logger.info(
                f"Downloaded {item_count} and skipped {skipped_count} posters from {library_name}."
            )

        logger.info(
            f"Total: Found {len(jf_media)} media items across all Jellyfin libraries"
        )
        return jf_media

    def get_jellyfin_client(self) -> Optional[JellyfinClient]:
        """
        Get the Jellyfin client if available.

        Returns:
            Optional[JellyfinClient]: Jellyfin client or None if not available
        """
        return self.servers.get("jellyfin")

    def get_plex_client(self) -> Optional[PlexServer]:
        """
        Get the Plex client if available.

        Returns:
            Optional[PlexServer]: Plex client or None if not available
        """
        return self.servers.get("plex")
