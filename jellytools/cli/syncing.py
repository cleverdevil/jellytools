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
from jellytools.core.utils import SyncDatabase

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


def get_jellyfin_media(server_manager: ServerManager) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Pre-fetch all media in Jellyfin from the configured libraries and map them by IMDB ID and title.

    Args:
        server_manager: Server manager instance with Jellyfin connection

    Returns:
        tuple: (
            dict: Mapping of IMDB IDs to Jellyfin media objects,
            dict: Mapping of normalized titles to Jellyfin media objects
        )
    """
    jellyfin = server_manager.get_jellyfin_client()
    if not jellyfin:
        logger.error("Jellyfin server not configured or connection failed")
        return {}, {}

    config = get_config()
    jf_media_imdb = {}
    jf_media_title = {}
    
    # Helper function to normalize titles for comparison
    def normalize_title(title):
        if not title:
            return ""
        # Remove special characters, lowercase, and remove spaces
        return ''.join(c.lower() for c in title if c.isalnum())

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

        # Process each item, mapping by both IMDB ID and title
        logger.info(f"Mapping Jellyfin {library_name} media...")
        item_count = 0
        items_with_imdb = 0
        items_with_title = 0

        for item in library_contents.get("Items", []):
            # Skip folders, collections, and other non-media items
            item_type = item.get("Type", "")
            if item_type in ["Folder", "CollectionFolder", "UserView", "BoxSet"]:
                continue

            item_count += 1
            if item_count % 100 == 0:
                logger.info(f"Processed {item_count} items in {library_name}...")

            # Extract IMDB ID first
            imdb_mapped = False
            provider_ids = item.get("ProviderIds", {})
            for provider, provider_id in provider_ids.items():
                if provider.lower() == "imdb":
                    jf_media_imdb[provider_id] = item
                    items_with_imdb += 1
                    imdb_mapped = True
                    break
            
            # Always map by title as well
            if "Name" in item:
                # For TV shows, include production year to avoid conflicts
                if item_type == "Series" and "ProductionYear" in item:
                    normalized_title = normalize_title(f"{item['Name']} {item['ProductionYear']}")
                else:
                    normalized_title = normalize_title(item["Name"])
                
                if normalized_title:
                    jf_media_title[normalized_title] = item
                    items_with_title += 1

        logger.info(
            f"Found {item_count} items in {library_name}: "
            f"{items_with_imdb} with IMDb IDs, {items_with_title} with titles"
        )

    logger.info(
        f"Total: Found {len(jf_media_imdb)} items with IMDb IDs and {len(jf_media_title)} with titles "
        f"across all Jellyfin libraries"
    )
    return jf_media_imdb, jf_media_title


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
    sync_db: SyncDatabase,
    force_sync: bool = False
) -> bool:
    """
    Sync images from a Plex collection to a Jellyfin collection.

    Args:
        plex_collection: Plex collection object
        jellyfin_collection_id: Jellyfin collection ID
        jellyfin_client: Jellyfin client instance
        sync_db: Database to track sync status
        force_sync: Whether to force sync even if already synced

    Returns:
        bool: True if any images were synced, False otherwise
    """
    images_synced = False
    collection_title = getattr(plex_collection, 'title', 'Unknown Collection')
    
    # Check if collection is already synced (unless force_sync is True)
    if not force_sync and sync_db.is_collection_synced(jellyfin_collection_id):
        logger.debug(f"Collection '{collection_title}' already synced according to database, skipping")
        return False
    
    # Check if collection still exists
    if not jellyfin_client.item_exists(jellyfin_collection_id):
        logger.warning(f"Collection {jellyfin_collection_id} no longer exists in Jellyfin, skipping")
        return False
    
    # Skip if image already exists, to avoid duplicate uploads
    if jellyfin_client.check_image_exists(jellyfin_collection_id, "Primary", detailed_logging=False):
        logger.debug(f"Primary image already exists for collection '{collection_title}', skipping")
        # Mark as synced in database even though we didn't upload anything
        sync_db.mark_collection_synced(jellyfin_collection_id, collection_title)
        return False
        
    # Try to sync the poster image (thumb in Plex)
    try:
        image_data, extension = get_plex_image_data(plex_collection, "thumb")
        if image_data:
            logger.info(f"Uploading poster image for collection '{collection_title}'...")
            if jellyfin_client.upload_image(
                jellyfin_collection_id, "Primary", image_data, extension
            ):
                images_synced = True
                logger.info(f"Successfully uploaded poster image for collection '{collection_title}'")
            else:
                logger.info(f"Failed to upload poster image for collection '{collection_title}'")
                
            # Mark the collection as synced in the database even if upload failed
            # This prevents repeated attempts at the same collection
            sync_db.mark_collection_synced(jellyfin_collection_id, collection_title)
    except Exception as e:
        logger.error(f"Error syncing image for collection '{collection_title}': {e}")
        # Still mark it as synced to avoid repeated failures
        sync_db.mark_collection_synced(jellyfin_collection_id, collection_title)

    return images_synced


def build_plex_media_map(server_manager: ServerManager) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Build mappings of IMDB IDs and titles to Plex media objects.

    Args:
        server_manager: Server manager instance with Plex connection

    Returns:
        tuple: (
            dict: Mapping of IMDB IDs to Plex media objects,
            dict: Mapping of normalized titles to Plex media objects
        )
    """
    plex = server_manager.get_plex_client()
    if not plex:
        logger.error("Plex server not configured or connection failed")
        return {}, {}

    config = get_config()
    plex_media_map_imdb = {}
    plex_media_map_title = {}
    
    # Helper function to normalize titles for comparison
    def normalize_title(title):
        if not title:
            return ""
        # Remove special characters, lowercase, and remove spaces
        return ''.join(c.lower() for c in title if c.isalnum())

    for library in plex.library.sections():
        if library.title in config.PLEX_LIBRARIES:
            for media in library.all():
                # Try to get IMDb ID first
                imdb_id = None
                for guid in media.guids:
                    if guid.id.startswith("imdb"):
                        imdb_id = guid.id.replace("imdb://", "")
                        plex_media_map_imdb[imdb_id] = media
                        break
                
                # Always create a title mapping as well
                if hasattr(media, 'title') and media.title:
                    # For TV shows, include year in title to avoid conflicts
                    if hasattr(media, 'TYPE') and media.TYPE == 'show' and hasattr(media, 'year') and media.year:
                        normalized_title = normalize_title(f"{media.title} {media.year}")
                    else:
                        normalized_title = normalize_title(media.title)
                    
                    if normalized_title:
                        plex_media_map_title[normalized_title] = media

    logger.info(f"Found {len(plex_media_map_imdb)} Plex items with IMDb IDs and {len(plex_media_map_title)} with titles")
    return plex_media_map_imdb, plex_media_map_title


# Database-based sync tracking functions

def get_sync_db(db_path: str = "jellytools_sync.db") -> SyncDatabase:
    """
    Get a SyncDatabase instance.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SyncDatabase: Database instance for tracking sync status
    """
    return SyncDatabase(db_path)

# This function has been moved to the JellyfinClient class
# Keeping the signature here for backwards compatibility, if needed
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
    return jellyfin_client.check_image_exists(item_id, image_type)

def sync_media_images(
    plex_media_maps: Tuple[Dict[str, Any], Dict[str, Any]],
    jellyfin_media_maps: Tuple[Dict[str, Any], Dict[str, Any]],
    jellyfin_client: Any,
    sync_db: SyncDatabase,
    image_types: List[str] = ["thumb", "art", "banner"],
    force_sync: bool = False
) -> int:
    """
    Sync images from Plex media items to Jellyfin media items.

    Args:
        plex_media_maps: Tuple containing (IMDB ID mapping, title mapping) for Plex objects
        jellyfin_media_maps: Tuple containing (IMDB ID mapping, title mapping) for Jellyfin objects
        jellyfin_client: Jellyfin client instance
        sync_db: Database to track sync status
        image_types: Types of images to sync (default: ["thumb", "art", "banner"])
        force_sync: Whether to force sync for all items (default: False)

    Returns:
        int: Number of items with synced images
    """
    # Unpack the mappings
    plex_media_map_imdb, plex_media_map_title = plex_media_maps
    jellyfin_media_map_imdb, jellyfin_media_map_title = jellyfin_media_maps
    
    # Create a combined set of media to sync (matched by either IMDb ID or title)
    media_to_sync = []  # List of tuples: (plex_obj, jellyfin_obj, jellyfin_id)
    
    # First add all IMDb matches
    imdb_matches = 0
    common_imdb_ids = set(plex_media_map_imdb.keys()) & set(jellyfin_media_map_imdb.keys())
    for imdb_id in common_imdb_ids:
        plex_obj = plex_media_map_imdb[imdb_id]
        jellyfin_obj = jellyfin_media_map_imdb[imdb_id]
        jellyfin_id = jellyfin_obj["Id"]
        media_to_sync.append((plex_obj, jellyfin_obj, jellyfin_id))
        imdb_matches += 1
    
    # Add title matches for items not already mapped by IMDb
    title_matches = 0
    plex_processed_by_imdb = set()
    jellyfin_processed_by_imdb = set()
    
    # Track which items were already processed via IMDb
    for imdb_id in common_imdb_ids:
        plex_obj = plex_media_map_imdb[imdb_id]
        jellyfin_obj = jellyfin_media_map_imdb[imdb_id]
        
        # Use title as the key if available
        if hasattr(plex_obj, 'title'):
            # Add both with and without year for maximum matching potential
            plex_processed_by_imdb.add(plex_obj.title.lower())
            if hasattr(plex_obj, 'year') and plex_obj.year:
                plex_processed_by_imdb.add(f"{plex_obj.title.lower()} {plex_obj.year}")
        
        jellyfin_processed_by_imdb.add(jellyfin_obj.get("Id"))
    
    # Now look for title matches that weren't already processed
    common_titles = set(plex_media_map_title.keys()) & set(jellyfin_media_map_title.keys())
    for title in common_titles:
        plex_obj = plex_media_map_title[title]
        jellyfin_obj = jellyfin_media_map_title[title]
        jellyfin_id = jellyfin_obj["Id"]
        
        # Skip if this Jellyfin ID was already processed via IMDb
        if jellyfin_id in jellyfin_processed_by_imdb:
            continue
            
        # Skip if this Plex title was already processed via IMDb
        if hasattr(plex_obj, 'title') and plex_obj.title.lower() in plex_processed_by_imdb:
            continue
        
        # This is a new match by title
        media_to_sync.append((plex_obj, jellyfin_obj, jellyfin_id))
        title_matches += 1
    
    total_items = len(media_to_sync)
    
    # Define mapping from Plex image types to Jellyfin image types
    image_type_mapping = {
        "thumb": "Primary",  # Poster/thumbnail
        "art": "Backdrop",   # Background art
        "banner": "Banner",  # Banner image
    }

    logger.info(f"Found {imdb_matches} matches by IMDb ID and {title_matches} additional matches by title")
    logger.info(f"Syncing {', '.join(image_types)} images for {total_items} total media items...")
    
    if force_sync:
        logger.info("Force sync enabled: checking all items regardless of sync status")
    else:
        logger.info("Incremental sync: only checking items not previously synced")

    # Process in batches to show progress
    processed = 0
    items_with_images = 0
    total_images_synced = 0
    skipped_items = 0
    
    for plex_obj, jellyfin_obj, jellyfin_id in media_to_sync:
        processed += 1
        item_synced = False
        item_name = getattr(plex_obj, 'title', 'Unknown')
        
        # Check if this item has already been synced (unless force_sync is True)
        if not force_sync and sync_db.is_media_synced(jellyfin_id, "artwork"):
            skipped_items += 1
            if processed % 100 == 0:
                logger.debug(f"Skipped {skipped_items} previously synced items so far")
            continue
            
        # Check if the item still exists in Jellyfin
        if not jellyfin_client.item_exists(jellyfin_id):
            logger.warning(f"Item {jellyfin_id} ({item_name}) no longer exists in Jellyfin, skipping")
            continue
        
        # Try to sync each image type
        for plex_type in image_types:
            if plex_type not in image_type_mapping:
                logger.warning(f"Unknown image type: {plex_type}, skipping")
                continue
                
            jellyfin_type = image_type_mapping[plex_type]
            
            # Skip "banner" type for movies and episodes - they don't typically support this
            jellyfin_obj_type = jellyfin_obj.get("Type", "")
            if jellyfin_type == "Banner" and jellyfin_obj_type in ["Movie", "Episode"]:
                logger.debug(f"Banner images not typically supported for {jellyfin_obj_type}s, skipping {item_name}")
                continue
            
            # Skip if image already exists, to avoid duplicate uploads
            if jellyfin_client.check_image_exists(jellyfin_id, jellyfin_type, detailed_logging=False):
                logger.debug(f"{jellyfin_type} image already exists for {item_name}, skipping")
                continue
            
            # Check if Plex has the image type before trying to upload
            has_plex_image = False
            if plex_type == "thumb" and hasattr(plex_obj, "thumb") and plex_obj.thumb:
                has_plex_image = True
            elif plex_type == "art" and hasattr(plex_obj, "art") and plex_obj.art:
                has_plex_image = True
            elif plex_type == "banner" and hasattr(plex_obj, "banner") and plex_obj.banner:
                has_plex_image = True
                
            if not has_plex_image:
                logger.debug(f"No {plex_type} image available in Plex for {item_name}, skipping")
                continue
            
            try:
                image_data, extension = get_plex_image_data(plex_obj, plex_type)
                if image_data and jellyfin_client.upload_image(
                    jellyfin_id, jellyfin_type, image_data, extension
                ):
                    total_images_synced += 1
                    item_synced = True
                    logger.debug(f"Synced {plex_type} → {jellyfin_type} for {item_name}")
            except Exception as e:
                logger.debug(f"Error syncing {plex_type} image for {item_name}: {e}")
        
        # If at least one image was synced, record it in the database
        if item_synced:
            items_with_images += 1
            # Record the sync in the database
            sync_db.mark_media_synced(jellyfin_id, item_name, "artwork")

        # Show progress periodically
        if processed % 20 == 0 or processed == total_items:
            logger.info(
                f"Processed {processed}/{total_items} items, "
                f"synced {total_images_synced} images for {items_with_images} items, "
                f"skipped {skipped_items} previously synced items"
            )

    logger.info(f"Total: {total_images_synced} images synced for {items_with_images} items")
    logger.info(f"Skipped {skipped_items} previously synced items")
    logger.info(f"Match breakdown: {imdb_matches} by IMDb ID, {title_matches} by title")
    return items_with_images


def sync_collections(
    server_manager: ServerManager,
    clean_collections: bool = True,
    sync_images: bool = True,
    sync_all_artwork: bool = True,
    force_sync: bool = False,
    db_path: str = "jellytools_sync.db"
) -> Dict[str, int]:
    """
    Main function to synchronize collections and artwork from Plex to Jellyfin.

    Args:
        server_manager: Server manager instance with connections to both servers
        clean_collections: Whether to clean existing Jellyfin collections
        sync_images: Whether to sync images at all
        sync_all_artwork: Whether to sync all artwork types (not just primary images)
        force_sync: Whether to force sync even for previously synced items
        db_path: Path to the SQLite database for tracking sync status

    Returns:
        dict: Summary statistics of the synchronization
    """
    logger.info("\n=== Starting Plex to Jellyfin Synchronization ===\n")
    start_time = time.time()

    # Get clients for both servers and load config
    jellyfin_client = server_manager.get_jellyfin_client()
    plex = server_manager.get_plex_client()
    config = get_config()
    
    # Initialize the sync database
    sync_db = SyncDatabase(db_path)
    
    # If force sync is requested, clear the relevant database entries
    if force_sync:
        logger.info("Force sync requested, clearing previous sync data")
        sync_db.reset_sync_data()
    
    if not jellyfin_client:
        logger.error("Jellyfin server not configured or connection failed")
        return {
            "collections_created": 0,
            "collections_failed": 0,
            "collections_with_images": 0,
            "media_with_images": 0,
            "elapsed_time": 0,
        }
        
    if not plex:
        logger.error("Plex server not configured or connection failed")
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
    jellyfin_media_imdb, jellyfin_media_title = get_jellyfin_media(server_manager)

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
                
                # First try to match by IMDb ID
                imdb_matches = 0
                for imdb_id in imdb_ids:
                    if imdb_id in jellyfin_media_imdb:
                        jellyfin_item_ids.append(jellyfin_media_imdb[imdb_id]["Id"])
                        imdb_matches += 1
                
                # For items that didn't match by IMDb ID, try matching by title
                if imdb_matches < len(imdb_ids):
                    # Get a mapping of titles to IMDb IDs for Plex items in this collection
                    plex_collection_titles = {}
                    title_matches = 0
                    
                    # Get all the Plex objects for this collection
                    plex_collection_items = []
                    for imdb_id in imdb_ids:
                        for library in plex.library.sections():
                            if library.title in config.PLEX_LIBRARIES:
                                for media in library.all():
                                    for guid in media.guids:
                                        if guid.id.startswith("imdb") and guid.id.replace("imdb://", "") == imdb_id:
                                            plex_collection_items.append(media)
                                            break
                    
                    # Normalize function for titles
                    def normalize_title(title):
                        if not title:
                            return ""
                        return ''.join(c.lower() for c in title if c.isalnum())
                    
                    # Now try to match remaining items by title
                    for plex_item in plex_collection_items:
                        # Skip if we already mapped this item by IMDb ID
                        imdb_mapped = False
                        for guid in plex_item.guids:
                            if guid.id.startswith("imdb"):
                                imdb_id = guid.id.replace("imdb://", "")
                                if imdb_id in jellyfin_media_imdb:
                                    imdb_mapped = True
                                    break
                        
                        if imdb_mapped:
                            continue
                            
                        # Try to find a match by title
                        if hasattr(plex_item, 'title') and plex_item.title:
                            # Try different title variations for matching
                            title_variations = [normalize_title(plex_item.title)]
                            
                            # Add year-based variations for shows
                            if hasattr(plex_item, 'TYPE') and plex_item.TYPE == 'show' and hasattr(plex_item, 'year') and plex_item.year:
                                title_variations.append(normalize_title(f"{plex_item.title} {plex_item.year}"))
                            
                            # Check each variation against the Jellyfin title map
                            for title_var in title_variations:
                                if title_var in jellyfin_media_title:
                                    jellyfin_id = jellyfin_media_title[title_var]["Id"]
                                    
                                    # Make sure we don't add duplicates
                                    if jellyfin_id not in jellyfin_item_ids:
                                        jellyfin_item_ids.append(jellyfin_id)
                                        title_matches += 1
                                        break
                
                if not jellyfin_item_ids:
                    logger.info(
                        f"Skipping collection '{collection_name}' - no matching items in Jellyfin"
                    )
                    continue
                    
                logger.info(
                    f"Collection '{collection_name}': {imdb_matches} items matched by IMDb ID, "
                    f"{len(jellyfin_item_ids) - imdb_matches} additional items matched by title"
                )

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
                            sync_db,
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
            plex_media_maps = build_plex_media_map(server_manager)
            
            # Determine which image types to sync
            image_types = ["thumb"]  # Default to just primary/poster images
            if sync_all_artwork:
                image_types = ["thumb", "art", "banner"]
                logger.info("Syncing all artwork types: Primary, Backdrop, and Banner images")
            else:
                logger.info("Syncing only Primary/Poster images")
                
            # Sync the images - pass both IMDb and title mappings
            media_with_images = sync_media_images(
                plex_media_maps, 
                (jellyfin_media_imdb, jellyfin_media_title), 
                jellyfin_client,
                sync_db,
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

