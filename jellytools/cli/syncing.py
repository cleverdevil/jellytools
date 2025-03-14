"""
Syncing functionality for Plex to Jellyfin collections and artwork.
"""

import time
import logging
import requests
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple, Set

from jellytools.core.server import ServerManager
from jellytools.core.config import get_config

# Configure logging
logger = logging.getLogger(__name__)


def get_plex_collections(
    server_manager: ServerManager,
) -> Tuple[Dict[str, Set[str]], Dict[str, Any]]:
    """
    Gather all Plex collections and their media with IMDB IDs.

    Args:
        server_manager: Server manager instance with Plex connection

    Returns:
        tuple: (collections mapping, collection objects)
            - dict: Mapping of collection names to sets of IMDB IDs
            - dict: Mapping of collection names to Plex collection objects (for images)
    """
    collections = defaultdict(set)
    collection_objects = {}
    media_to_imdb = {}

    # Get Plex client
    plex = server_manager.get_plex_client()
    if not plex:
        logger.error("Plex server not configured or connection failed")
        return {}, {}

    config = get_config()

    # Get all media items and their IMDB IDs
    logger.info(
        f"Scanning Plex libraries {config.PLEX_LIBRARIES} for media and their IMDB IDs..."
    )
    for library in plex.library.sections():
        if library.title in config.PLEX_LIBRARIES:
            logger.info(f"Processing library: {library.title} (type: {library.type})")
            for media in library.all():
                imdb_id = None
                for guid in media.guids:
                    if guid.id.startswith("imdb"):
                        imdb_id = guid.id.replace("imdb://", "")
                        media_to_imdb[media] = imdb_id
                        break

                if not imdb_id:
                    logger.warning(
                        f"No IMDB ID found for {library.type}: {media.title}"
                    )

    # Process all collections
    logger.info("Processing Plex collections...")
    for library in plex.library.sections():
        if library.title in config.PLEX_LIBRARIES:
            logger.info(f"Processing collections in library: {library.title}")
            for collection in library.collections():
                collection_objects[collection.title] = collection
                for media in collection.items():
                    if media in media_to_imdb:  # Only include media with IMDB IDs
                        collections[collection.title].add(media_to_imdb[media])

    # Remove empty collections
    collections = {name: imdb_ids for name, imdb_ids in collections.items() if imdb_ids}

    logger.info(f"Found {len(collections)} collections across all libraries")
    return collections, collection_objects


def get_jellyfin_media(server_manager: ServerManager) -> Dict[str, Any]:
    """
    Pre-fetch all media in Jellyfin from the configured libraries and map them by IMDB ID.

    Args:
        server_manager: Server manager instance with Jellyfin connection

    Returns:
        dict: Mapping of IMDB IDs to Jellyfin media objects
    """
    jellyfin = server_manager.get_jellyfin_client()
    if not jellyfin:
        logger.error("Jellyfin server not configured or connection failed")
        return {}

    config = get_config()
    jf_media = {}

    # Process each library type configured in PLEX_LIBRARIES
    for library_name in config.PLEX_LIBRARIES:
        logger.info(f"Fetching Jellyfin {library_name} library...")
        items = jellyfin.items_list()
        library_items = [
            item for item in items["Items"] if item["Name"] == library_name
        ]

        if not library_items:
            logger.warning(f"No '{library_name}' library found in Jellyfin")
            continue

        library_id = library_items[0]["Id"]

        # Loop through the items in the Jellyfin library
        # Use recursive parameter to get all items at once with all fields
        library_contents = jellyfin.items_list(
            parentId=library_id, recursive=True, include_fields=True
        )

        # Process each item, looking for IMDB IDs directly in the item data
        logger.info(f"Mapping Jellyfin {library_name} by IMDB ID...")
        item_count = 0
        items_with_imdb = 0

        for item in library_contents.get("Items", []):
            # Skip folders, collections, and other non-media items
            item_type = item.get("Type", "")
            if item_type in ["Folder", "CollectionFolder", "UserView", "BoxSet"]:
                continue

            item_count += 1
            if item_count % 100 == 0:
                logger.info(f"Processed {item_count} items in {library_name}...")

            # Extract IMDB ID directly from the item data
            provider_ids = item.get("ProviderIds", {})
            for provider, provider_id in provider_ids.items():
                if provider.lower() == "imdb":
                    jf_media[provider_id] = item
                    items_with_imdb += 1
                    break

        logger.info(
            f"Found {item_count} items in {library_name}, of which {items_with_imdb} have IMDB IDs"
        )

    logger.info(
        f"Total: Found {len(jf_media)} media items with IMDB IDs across all Jellyfin libraries"
    )
    return jf_media


def clean_jellyfin_collections(server_manager: ServerManager) -> None:
    """
    Remove all existing collections from Jellyfin.

    Args:
        server_manager: Server manager instance with Jellyfin connection
    """
    jellyfin = server_manager.get_jellyfin_client()
    if not jellyfin:
        logger.error("Jellyfin server not configured or connection failed")
        return

    logger.info("Removing existing Jellyfin collections...")
    existing_collections = jellyfin.collections_list()
    removed_count = 0

    for collection in existing_collections.get("Items", []):
        logger.info(f"Removing collection: {collection['Name']}")
        try:
            jellyfin.remove_collection(collection["Id"])
            removed_count += 1
        except Exception as e:
            logger.error(f"Error removing collection {collection['Name']}: {e}")

    logger.info(f"Removed {removed_count} collections from Jellyfin")


def get_plex_image_data(
    plex_obj: Any, image_type: str = "thumb"
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Get image data from a Plex object.

    Args:
        plex_obj: Plex object (movie, show, collection, etc.)
        image_type: Type of image ("thumb", "art", "poster", etc.)

    Returns:
        tuple: (image_data, extension) or (None, None) if image doesn't exist
    """
    config = get_config()

    try:
        image_url = None

        # Get the appropriate image URL
        if image_type == "thumb" or image_type == "poster":
            if hasattr(plex_obj, "thumb") and plex_obj.thumb:
                image_url = plex_obj.thumb
        elif image_type == "art":
            if hasattr(plex_obj, "art") and plex_obj.art:
                image_url = plex_obj.art
        elif image_type == "banner":
            if hasattr(plex_obj, "banner") and plex_obj.banner:
                image_url = plex_obj.banner

        if not image_url:
            return None, None

        # Construct full URL with token
        full_url = f"{config.PLEX_URL}{image_url}?X-Plex-Token={config.PLEX_TOKEN}"

        # Get the image data
        response = requests.get(full_url)
        response.raise_for_status()

        # Determine image extension from content type
        content_type = response.headers.get("Content-Type", "")
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(
            content_type, "jpg"
        )

        return response.content, extension
    except Exception as e:
        logger.error(
            f"Error getting image for {plex_obj.title if hasattr(plex_obj, 'title') else 'unknown item'}: {e}"
        )
        return None, None


def sync_collection_images(
    plex_collection: Any, jellyfin_collection_id: str, jellyfin_client: Any
) -> bool:
    """
    Sync images from a Plex collection to a Jellyfin collection.

    Args:
        plex_collection: Plex collection object
        jellyfin_collection_id: Jellyfin collection ID
        jellyfin_client: Jellyfin client instance

    Returns:
        bool: True if any images were synced, False otherwise
    """
    images_synced = False

    # Try to sync the poster image (thumb in Plex)
    try:
        image_data, extension = get_plex_image_data(plex_collection, "thumb")
        if image_data:
            logger.info(
                f"Uploading poster image for collection '{plex_collection.title}'..."
            )
            if jellyfin_client.upload_image(
                jellyfin_collection_id, "Primary", image_data, extension
            ):
                images_synced = True
                logger.info(
                    f"Successfully uploaded poster image for collection '{plex_collection.title}'"
                )
    except Exception as e:
        logger.error(
            f"Error syncing image for collection '{plex_collection.title}': {e}"
        )

    return images_synced


def build_plex_media_map(server_manager: ServerManager) -> Dict[str, Any]:
    """
    Build a mapping of IMDB IDs to Plex media objects.

    Args:
        server_manager: Server manager instance with Plex connection

    Returns:
        dict: Mapping of IMDB IDs to Plex media objects
    """
    plex = server_manager.get_plex_client()
    if not plex:
        logger.error("Plex server not configured or connection failed")
        return {}

    config = get_config()
    plex_media_map = {}

    for library in plex.library.sections():
        if library.title in config.PLEX_LIBRARIES:
            for media in library.all():
                imdb_id = None
                for guid in media.guids:
                    if guid.id.startswith("imdb"):
                        imdb_id = guid.id.replace("imdb://", "")
                        plex_media_map[imdb_id] = media
                        break

    return plex_media_map


def sync_media_images(
    plex_media_map: Dict[str, Any],
    jellyfin_media_map: Dict[str, Any],
    jellyfin_client: Any,
) -> int:
    """
    Sync images from Plex media items to Jellyfin media items.

    Args:
        plex_media_map: Mapping of IMDB IDs to Plex media objects
        jellyfin_media_map: Mapping of IMDB IDs to Jellyfin media objects
        jellyfin_client: Jellyfin client instance

    Returns:
        int: Number of items with synced images
    """
    synced_count = 0
    common_imdb_ids = set(plex_media_map.keys()) & set(jellyfin_media_map.keys())
    total_items = len(common_imdb_ids)

    logger.info(f"Syncing images for {total_items} media items...")

    # Process in batches to show progress
    processed = 0
    for imdb_id in common_imdb_ids:
        processed += 1

        plex_obj = plex_media_map[imdb_id]
        jellyfin_id = jellyfin_media_map[imdb_id]["Id"]

        # Just try to sync the primary/poster image
        try:
            image_data, extension = get_plex_image_data(plex_obj, "thumb")
            if image_data and jellyfin_client.upload_image(
                jellyfin_id, "Primary", image_data, extension
            ):
                synced_count += 1
        except Exception as e:
            logger.error(f"Error syncing image for {plex_obj.title}: {e}")

        # Show progress periodically
        if processed % 20 == 0 or processed == total_items:
            logger.info(
                f"Processed {processed}/{total_items} items, synced images for {synced_count} items"
            )

    return synced_count


def sync_collections(server_manager: ServerManager) -> Dict[str, int]:
    """
    Main function to synchronize collections from Plex to Jellyfin.

    Args:
        server_manager: Server manager instance with connections to both servers

    Returns:
        dict: Summary statistics of the synchronization
    """
    logger.info("\n=== Starting Plex to Jellyfin Collection Synchronization ===\n")
    start_time = time.time()

    # Get Jellyfin client
    jellyfin_client = server_manager.get_jellyfin_client()
    if not jellyfin_client:
        logger.error("Jellyfin server not configured or connection failed")
        return {
            "collections_created": 0,
            "collections_failed": 0,
            "collections_with_images": 0,
            "media_with_images": 0,
            "elapsed_time": 0,
        }

    # Step 1: Get Plex collections data
    logger.info("\n--- Gathering Plex Data ---")
    plex_collections, plex_collection_objects = get_plex_collections(server_manager)

    if not plex_collections:
        logger.error("No Plex collections found or Plex server not configured")
        return {
            "collections_created": 0,
            "collections_failed": 0,
            "collections_with_images": 0,
            "media_with_images": 0,
            "elapsed_time": time.time() - start_time,
        }

    # Step 2: Get Jellyfin media data
    logger.info("\n--- Gathering Jellyfin Data ---")
    jellyfin_media = get_jellyfin_media(server_manager)

    # Step 3: Clean existing Jellyfin collections
    logger.info("\n--- Cleaning Jellyfin Collections ---")
    clean_jellyfin_collections(server_manager)

    # Step 4: Create new collections in Jellyfin
    logger.info("\n--- Creating Jellyfin Collections ---")
    collections_created = 0
    collections_failed = 0
    collections_with_images = 0

    for collection_name, imdb_ids in plex_collections.items():
        # Convert IMDB IDs to Jellyfin media IDs
        jellyfin_item_ids = []
        for imdb_id in imdb_ids:
            if imdb_id in jellyfin_media:
                jellyfin_item_ids.append(jellyfin_media[imdb_id]["Id"])

        if not jellyfin_item_ids:
            logger.info(
                f"Skipping collection '{collection_name}' - no matching items in Jellyfin"
            )
            continue

        logger.info(
            f"Creating collection '{collection_name}' with {len(jellyfin_item_ids)} items"
        )
        try:
            result = jellyfin_client.create_collection(
                collection_name, jellyfin_item_ids
            )
            collections_created += 1

            # Sync collection images if enabled
            if "Id" in result:
                plex_collection = plex_collection_objects[collection_name]
                if sync_collection_images(
                    plex_collection, result["Id"], jellyfin_client
                ):
                    collections_with_images += 1

        except Exception as e:
            logger.error(f"Error creating collection '{collection_name}': {e}")
            collections_failed += 1

    # Step 5: Sync media images
    media_with_images = 0

    # Check if sync_collection_images has been monkey-patched by the skip_images flag
    if not hasattr(sync_collection_images, "__patched_to_skip__"):
        logger.info("\n--- Syncing Media Images ---")
        plex_media_map = build_plex_media_map(server_manager)
        media_with_images = sync_media_images(
            plex_media_map, jellyfin_media, jellyfin_client
        )
    else:
        logger.info("\n--- Skipping Media Image Sync ---")
        logger.info("Image syncing has been disabled with --skip-images flag")

    # Summary
    elapsed_time = time.time() - start_time
    logger.info(f"\n=== Synchronization Complete ===")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
    logger.info(f"Collections created: {collections_created}")
    logger.info(f"Collections failed: {collections_failed}")
    logger.info(f"Collections with images: {collections_with_images}")
    logger.info(f"Media items with images: {media_with_images}")

    return {
        "collections_created": collections_created,
        "collections_failed": collections_failed,
        "collections_with_images": collections_with_images,
        "media_with_images": media_with_images,
        "elapsed_time": elapsed_time,
    }

