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
    plex_collection: Any, 
    jellyfin_collection_id: str, 
    jellyfin_client: Any,
    force_sync: bool = False,
    sync_tag: str = "JellytoolsCollectionSynced"
) -> bool:
    """
    Sync images from a Plex collection to a Jellyfin collection.

    Args:
        plex_collection: Plex collection object
        jellyfin_collection_id: Jellyfin collection ID
        jellyfin_client: Jellyfin client instance
        force_sync: Whether to force sync even if already tagged
        sync_tag: Tag to mark synced collections

    Returns:
        bool: True if any images were synced, False otherwise
    """
    images_synced = False
    
    # Check if collection is already synced (unless force_sync is True)
    if not force_sync:
        # Get collection details to check for the sync tag
        try:
            collection_info = jellyfin_client._get(f"/Users/{jellyfin_client.user_id}/Items/{jellyfin_collection_id}")
            item_tags = [tag.get("Name", "") for tag in collection_info.get("TagItems", [])]
            
            if sync_tag in item_tags:
                logger.debug(f"Collection '{plex_collection.title}' already synced, skipping")
                return False
        except Exception as e:
            # If we can't get collection details, just proceed with the sync
            logger.debug(f"Error checking sync status of collection '{plex_collection.title}': {e}")
    
    # If force_sync, remove the tag if it exists
    if force_sync:
        remove_jellyfin_tag(jellyfin_client, jellyfin_collection_id, sync_tag)
    
    # Skip if image already exists, to avoid duplicate uploads
    if check_image_exists(jellyfin_client, jellyfin_collection_id, "Primary"):
        logger.debug(f"Primary image already exists for collection '{plex_collection.title}', skipping")
        return False
        
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
                
                # Tag the collection as synced
                tag_jellyfin_item(jellyfin_client, jellyfin_collection_id, sync_tag)
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


def tag_jellyfin_item(jellyfin_client: Any, item_id: str, tag: str) -> bool:
    """
    Add a tag to a Jellyfin item.
    
    Args:
        jellyfin_client: Jellyfin client instance
        item_id: Jellyfin item ID
        tag: Tag to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First get the current item details to see existing tags
        item_info = jellyfin_client._get(f"/Users/{jellyfin_client.user_id}/Items/{item_id}")
        
        # Get current tags
        current_tags = item_info.get("TagItems", [])
        current_tag_names = [tag_item.get("Name") for tag_item in current_tags]
        
        # Check if tag already exists
        if tag in current_tag_names:
            return True  # Tag already exists
            
        # Add the new tag
        url = f"/Items/{item_id}/Tags"
        result = jellyfin_client._post(url, data={"Tags": [tag]})
        logger.debug(f"Added tag '{tag}' to item {item_id}")
        return True
    except Exception as e:
        logger.debug(f"Error adding tag '{tag}' to item {item_id}: {e}")
        return False

def remove_jellyfin_tag(jellyfin_client: Any, item_id: str, tag: str) -> bool:
    """
    Remove a tag from a Jellyfin item.
    
    Args:
        jellyfin_client: Jellyfin client instance
        item_id: Jellyfin item ID
        tag: Tag to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First check if the item has the tag
        item_info = jellyfin_client._get(f"/Users/{jellyfin_client.user_id}/Items/{item_id}")
        
        # Get current tags
        current_tags = item_info.get("TagItems", [])
        current_tag_names = [tag_item.get("Name") for tag_item in current_tags]
        
        # Check if tag exists
        if tag not in current_tag_names:
            return True  # Tag doesn't exist, nothing to do
            
        # Remove the tag
        url = f"/Items/{item_id}/Tags/{tag}"
        result = jellyfin_client._delete(url)
        logger.debug(f"Removed tag '{tag}' from item {item_id}")
        return True
    except Exception as e:
        logger.debug(f"Error removing tag '{tag}' from item {item_id}: {e}")
        return False

def check_image_exists(jellyfin_client: Any, item_id: str, image_type: str) -> bool:
    """
    Check if an image of the specified type already exists for an item.
    
    Args:
        jellyfin_client: Jellyfin client instance
        item_id: Jellyfin item ID
        image_type: Image type (Primary, Backdrop, etc.)
        
    Returns:
        bool: True if image exists, False otherwise
    """
    try:
        response = jellyfin_client._request(
            verb="get", 
            path=f"/Items/{item_id}/Images/{image_type}", 
            raw_response=True
        )
        
        # If a valid response with 200 status, the image exists
        return response.status_code == 200 and len(response.content) > 0
    except Exception as e:
        # If we get a 404 or other error, the image doesn't exist
        return False

def sync_media_images(
    plex_media_map: Dict[str, Any],
    jellyfin_media_map: Dict[str, Any],
    jellyfin_client: Any,
    image_types: List[str] = ["thumb", "art", "banner"],
    force_sync: bool = False,
    sync_tag: str = "JellytoolsArtworkSynced"
) -> int:
    """
    Sync images from Plex media items to Jellyfin media items.

    Args:
        plex_media_map: Mapping of IMDB IDs to Plex media objects
        jellyfin_media_map: Mapping of IMDB IDs to Jellyfin media objects
        jellyfin_client: Jellyfin client instance
        image_types: Types of images to sync (default: ["thumb", "art", "banner"])
        force_sync: Whether to force sync for all items (default: False)
        sync_tag: Tag to use for marking synced items (default: "JellytoolsArtworkSynced")

    Returns:
        int: Number of items with synced images
    """
    synced_count = 0
    common_imdb_ids = set(plex_media_map.keys()) & set(jellyfin_media_map.keys())
    total_items = len(common_imdb_ids)

    # Define mapping from Plex image types to Jellyfin image types
    image_type_mapping = {
        "thumb": "Primary",  # Poster/thumbnail
        "art": "Backdrop",   # Background art
        "banner": "Banner",  # Banner image
    }

    logger.info(f"Syncing {', '.join(image_types)} images for {total_items} media items...")
    
    if force_sync:
        logger.info("Force sync enabled: checking all items regardless of sync status")
    else:
        logger.info("Incremental sync: only checking items not previously synced")

    # Process in batches to show progress
    processed = 0
    items_with_images = 0
    total_images_synced = 0
    skipped_items = 0
    
    for imdb_id in common_imdb_ids:
        processed += 1
        item_synced = False

        plex_obj = plex_media_map[imdb_id]
        jellyfin_obj = jellyfin_media_map[imdb_id]
        jellyfin_id = jellyfin_obj["Id"]
        
        # Check if this item has already been synced (unless force_sync is True)
        if not force_sync:
            # Check for the sync tag in Jellyfin
            item_tags = [tag.get("Name", "") for tag in jellyfin_obj.get("TagItems", [])]
            if sync_tag in item_tags:
                skipped_items += 1
                if processed % 100 == 0:
                    logger.debug(f"Skipped {skipped_items} previously synced items so far")
                continue
        elif force_sync:
            # If force_sync, remove the sync tag if it exists
            remove_jellyfin_tag(jellyfin_client, jellyfin_id, sync_tag)
        
        # Try to sync each image type
        for plex_type in image_types:
            if plex_type not in image_type_mapping:
                logger.warning(f"Unknown image type: {plex_type}, skipping")
                continue
                
            jellyfin_type = image_type_mapping[plex_type]
            
            # Skip if image already exists, to avoid duplicate uploads
            if check_image_exists(jellyfin_client, jellyfin_id, jellyfin_type):
                logger.debug(f"{jellyfin_type} image already exists for {plex_obj.title}, skipping")
                continue
            
            try:
                image_data, extension = get_plex_image_data(plex_obj, plex_type)
                if image_data and jellyfin_client.upload_image(
                    jellyfin_id, jellyfin_type, image_data, extension
                ):
                    total_images_synced += 1
                    item_synced = True
                    logger.debug(f"Synced {plex_type} → {jellyfin_type} for {plex_obj.title}")
            except Exception as e:
                logger.debug(f"Error syncing {plex_type} image for {plex_obj.title}: {e}")
        
        # If at least one image was synced, tag the item
        if item_synced:
            items_with_images += 1
            tag_jellyfin_item(jellyfin_client, jellyfin_id, sync_tag)

        # Show progress periodically
        if processed % 20 == 0 or processed == total_items:
            logger.info(
                f"Processed {processed}/{total_items} items, "
                f"synced {total_images_synced} images for {items_with_images} items, "
                f"skipped {skipped_items} previously synced items"
            )

    logger.info(f"Total: {total_images_synced} images synced for {items_with_images} items")
    logger.info(f"Skipped {skipped_items} previously synced items")
    return items_with_images


def sync_collections(
    server_manager: ServerManager,
    clean_collections: bool = True,
    sync_images: bool = True,
    sync_all_artwork: bool = True,
    force_sync: bool = False,
) -> Dict[str, int]:
    """
    Main function to synchronize collections and artwork from Plex to Jellyfin.

    Args:
        server_manager: Server manager instance with connections to both servers
        clean_collections: Whether to clean existing Jellyfin collections
        sync_images: Whether to sync images at all
        sync_all_artwork: Whether to sync all artwork types (not just primary images)
        force_sync: Whether to force sync even for previously synced items

    Returns:
        dict: Summary statistics of the synchronization
    """
    logger.info("\n=== Starting Plex to Jellyfin Synchronization ===\n")
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

    # Step 1: Get Plex collections data (only if we're syncing collections)
    collections_created = 0
    collections_failed = 0
    collections_with_images = 0
    plex_collections = {}
    plex_collection_objects = {}
    
    if clean_collections:
        logger.info("\n--- Gathering Plex Collections Data ---")
        plex_collections, plex_collection_objects = get_plex_collections(server_manager)

        if not plex_collections:
            logger.warning("No Plex collections found or Plex server not configured")
            # Continue for media artwork sync

    # Step 2: Get Jellyfin media data
    logger.info("\n--- Gathering Jellyfin Media Data ---")
    jellyfin_media = get_jellyfin_media(server_manager)

    # Step 3: Clean existing Jellyfin collections if requested
    if clean_collections:
        logger.info("\n--- Cleaning Jellyfin Collections ---")
        clean_jellyfin_collections(server_manager)

        # Step 4: Create new collections in Jellyfin
        if plex_collections:
            logger.info("\n--- Creating Jellyfin Collections ---")
            
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
                    if sync_images and "Id" in result:
                        plex_collection = plex_collection_objects[collection_name]
                        if sync_collection_images(
                            plex_collection, 
                            result["Id"], 
                            jellyfin_client,
                            force_sync=force_sync
                        ):
                            collections_with_images += 1

                except Exception as e:
                    logger.error(f"Error creating collection '{collection_name}': {e}")
                    collections_failed += 1

    # Step 5: Sync media images if not disabled
    media_with_images = 0

    if sync_images:
        logger.info("\n--- Syncing Media Artwork ---")
        
        # Check if sync_collection_images has been monkey-patched by the skip_images flag
        if hasattr(sync_collection_images, "__patched_to_skip__"):
            logger.info("Image syncing has been disabled with --skip-images flag")
        else:
            plex_media_map = build_plex_media_map(server_manager)
            
            # Determine which image types to sync
            image_types = ["thumb"]  # Default to just primary/poster images
            if sync_all_artwork:
                image_types = ["thumb", "art", "banner"]
                logger.info("Syncing all artwork types: Primary, Backdrop, and Banner images")
            else:
                logger.info("Syncing only Primary/Poster images")
                
            # Sync the images
            media_with_images = sync_media_images(
                plex_media_map, 
                jellyfin_media, 
                jellyfin_client,
                image_types,
                force_sync=force_sync
            )
    else:
        logger.info("\n--- Skipping Media Artwork Sync ---")

    # Summary
    elapsed_time = time.time() - start_time
    logger.info(f"\n=== Synchronization Complete ===")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
    
    if clean_collections:
        logger.info(f"Collections created: {collections_created}")
        logger.info(f"Collections failed: {collections_failed}")
        logger.info(f"Collections with images: {collections_with_images}")
    
    if sync_images:
        logger.info(f"Media items with images: {media_with_images}")

    return {
        "collections_created": collections_created,
        "collections_failed": collections_failed,
        "collections_with_images": collections_with_images,
        "media_with_images": media_with_images,
        "elapsed_time": elapsed_time,
    }

