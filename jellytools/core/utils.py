"""
Utility functions for the library card generator.
"""

import os
import sys
import logging
import pathlib
import pygame
import subprocess
import sqlite3
from typing import List, Optional, Dict, Union, Any

from jellytools.animations.base import WIDTH, HEIGHT
from jellytools.core.config import get_config

logger = logging.getLogger(__name__)


class Utils:
    @staticmethod
    def check_dependencies() -> bool:
        """
        Check if required command-line tools are installed.

        Returns:
            bool: True if all dependencies are installed, False otherwise
        """
        dependencies_ok = True

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("FFmpeg is installed.")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error(
                "ERROR: FFmpeg is not installed or not in PATH. Please install FFmpeg."
            )
            dependencies_ok = False

        return dependencies_ok
        
    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Normalize a title for comparison by removing special characters and spaces.
        
        Args:
            title (str): The title to normalize
            
        Returns:
            str: Normalized title (lowercase, alphanumeric characters only)
        """
        if not title:
            return ""
        # Remove special characters, lowercase, and remove spaces
        return ''.join(c.lower() for c in title if c.isalnum())

    # Define standard poster dimensions as constants
    POSTER_HEIGHT = 210  # Reduced from 280 for memory efficiency
    MIN_POSTER_COUNT = 300  # Minimum number of posters required for animations

    @staticmethod
    def load_posters(library_name: str) -> List[pygame.Surface]:
        """
        Load images from the posters directory for a specific library.
        Uses memory-efficient approach to handle large libraries.

        Args:
            library_name (str): Name of the library to load posters for

        Returns:
            List[pygame.Surface]: List of loaded poster images
        """
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()

        # Make sure we have a video mode set before loading images
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((WIDTH, HEIGHT))

        config = get_config()

        # Determine path to posters directory for this library
        posters_dir = pathlib.Path(config.POSTER_DIRECTORY) / library_name
        if not posters_dir.exists():
            logger.error(f"Error: posters directory {posters_dir} not found.")
            pygame.quit()
            sys.exit(1)

        logger.info(f"Loading poster images from {posters_dir}...")
        
        # First collect all valid poster files
        poster_files = [
            filename for filename in os.listdir(posters_dir)
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
        ]
        
        if not poster_files:
            logger.error(f"Error: No valid poster images found in '{posters_dir}' directory.")
            pygame.quit()
            sys.exit(1)

        # Process available poster files
        posters = []
        for filename in poster_files:
            try:
                img_path = posters_dir / filename
                img = pygame.image.load(img_path).convert_alpha()

                # Scale images to maintain aspect ratio - adjusted for 2.5K resolution
                aspect_ratio = img.get_width() / img.get_height()
                new_width = int(Utils.POSTER_HEIGHT * aspect_ratio)

                # Use smoothscale for better quality
                img = pygame.transform.smoothscale(img, (new_width, Utils.POSTER_HEIGHT))
                posters.append(img)
            except pygame.error as e:
                logger.error(f"Error loading image {filename}: {e}")

        if not posters:
            logger.error(f"Error: Failed to load any valid poster images.")
            pygame.quit()
            sys.exit(1)
            
        # Create an index generator that cycles through the available posters
        # This avoids duplicating the actual poster data in memory
        def poster_cycle_generator(posters, min_count):
            """Generate poster indices, cycling through available posters."""
            original_count = len(posters)
            idx = 0
            while idx < min_count:
                yield idx % original_count
                idx += 1
                
        # Only if we have fewer than MIN_POSTER_COUNT posters, create an index list
        # that cycles through the available posters to reach the minimum
        if len(posters) < Utils.MIN_POSTER_COUNT:
            logger.info(f"Using {len(posters)} unique posters with recycling to fill animation")
            # Create a list of poster indices that cycles through available posters
            poster_indices = list(poster_cycle_generator(posters, Utils.MIN_POSTER_COUNT))
            
            # Create a reference list that points to existing posters
            posters = [posters[i] for i in poster_indices]
        
        logger.info(f"Successfully loaded {len(posters)} poster images.")
        return posters


class DatabaseContext:
    """Context manager for database operations."""
    
    def __init__(self, db_path: str, timeout: float = 30.0):
        """
        Initialize the database context.
        
        Args:
            db_path (str): Path to the SQLite database file
            timeout (float): Connection timeout in seconds
        """
        self.db_path = db_path
        self.timeout = timeout
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        """Enter the context manager, establishing a database connection."""
        self.conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, closing the database connection."""
        if exc_type is None:
            # No exception, commit changes
            self.conn.commit()
        else:
            # Exception occurred, rollback changes
            self.conn.rollback()
            logger.error(f"Database operation failed: {exc_val}")
            
        if self.conn:
            self.conn.close()
            
        # Don't suppress exceptions
        return False
        
    def execute(self, sql: str, parameters: tuple = ()):
        """
        Execute an SQL statement.
        
        Args:
            sql (str): SQL statement to execute
            parameters (tuple): Parameters for the statement
            
        Returns:
            cursor: Database cursor after execution
        """
        return self.cursor.execute(sql, parameters)
        
    def fetchone(self):
        """Fetch one row from the result set."""
        return self.cursor.fetchone()
        
    def fetchall(self):
        """Fetch all rows from the result set."""
        return self.cursor.fetchall()


class SyncDatabase:
    """Manage synced item state in an SQLite database."""
    
    # Define SQL queries as constants
    CREATE_COLLECTION_TABLE = '''
    CREATE TABLE IF NOT EXISTS collection_sync (
        collection_id TEXT PRIMARY KEY,
        collection_name TEXT,
        last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    '''
    
    CREATE_MEDIA_TABLE = '''
    CREATE TABLE IF NOT EXISTS media_sync (
        media_id TEXT PRIMARY KEY,
        media_name TEXT,
        sync_type TEXT,
        last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    '''
    
    INSERT_COLLECTION = '''
    INSERT OR REPLACE INTO collection_sync (collection_id, collection_name, last_synced)
    VALUES (?, ?, CURRENT_TIMESTAMP)
    '''
    
    CHECK_COLLECTION = 'SELECT collection_id FROM collection_sync WHERE collection_id = ?'
    
    INSERT_MEDIA = '''
    INSERT OR REPLACE INTO media_sync (media_id, media_name, sync_type, last_synced)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    '''
    
    CHECK_MEDIA = 'SELECT media_id FROM media_sync WHERE media_id = ? AND sync_type = ?'
    
    def __init__(self, db_path: str = "jellytools_sync.db"):
        """
        Initialize the sync database.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()
        
    def _initialize_db(self):
        """Create the database and tables if they don't exist."""
        try:
            with DatabaseContext(self.db_path) as db:
                # Create collections sync table
                db.execute(self.CREATE_COLLECTION_TABLE)
                
                # Create media sync table
                db.execute(self.CREATE_MEDIA_TABLE)
                
            logger.debug(f"Successfully initialized sync database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize sync database: {e}")
    
    def mark_collection_synced(self, collection_id: str, collection_name: str) -> bool:
        """
        Mark a collection as having been synced.
        
        Args:
            collection_id (str): Jellyfin collection ID
            collection_name (str): Collection name for reference
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with DatabaseContext(self.db_path) as db:
                db.execute(self.INSERT_COLLECTION, (collection_id, collection_name))
            return True
        except Exception as e:
            logger.error(f"Failed to mark collection {collection_id} as synced: {e}")
            return False
    
    def is_collection_synced(self, collection_id: str) -> bool:
        """
        Check if a collection has been synced.
        
        Args:
            collection_id (str): Jellyfin collection ID
            
        Returns:
            bool: True if synced, False otherwise
        """
        try:
            with DatabaseContext(self.db_path) as db:
                db.execute(self.CHECK_COLLECTION, (collection_id,))
                result = db.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check if collection {collection_id} is synced: {e}")
            return False
    
    def mark_media_synced(self, media_id: str, media_name: str, sync_type: str = "artwork") -> bool:
        """
        Mark a media item as having been synced.
        
        Args:
            media_id (str): Jellyfin media ID
            media_name (str): Media name for reference
            sync_type (str): Type of sync performed
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with DatabaseContext(self.db_path) as db:
                db.execute(self.INSERT_MEDIA, (media_id, media_name, sync_type))
            return True
        except Exception as e:
            logger.error(f"Failed to mark media {media_id} as synced: {e}")
            return False
    
    def is_media_synced(self, media_id: str, sync_type: str = "artwork") -> bool:
        """
        Check if a media item has been synced.
        
        Args:
            media_id (str): Jellyfin media ID
            sync_type (str): Type of sync to check
            
        Returns:
            bool: True if synced, False otherwise
        """
        try:
            with DatabaseContext(self.db_path) as db:
                db.execute(self.CHECK_MEDIA, (media_id, sync_type))
                result = db.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check if media {media_id} is synced: {e}")
            return False
    
    def reset_sync_data(self, sync_type: Optional[str] = None) -> bool:
        """
        Reset sync data, either for a specific type or all.
        
        Args:
            sync_type (str, optional): Type of sync to reset (collections, artwork),
                                      or None to reset all data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with DatabaseContext(self.db_path) as db:
                if sync_type == "collections":
                    db.execute('DELETE FROM collection_sync')
                    logger.info("Reset all collection sync data")
                elif sync_type == "artwork":
                    db.execute('DELETE FROM media_sync WHERE sync_type = ?', (sync_type,))
                    logger.info(f"Reset sync data for {sync_type}")
                else:
                    # Reset all data
                    db.execute('DELETE FROM collection_sync')
                    db.execute('DELETE FROM media_sync')
                    logger.info("Reset all sync data")
            return True
        except Exception as e:
            logger.error(f"Failed to reset sync data: {e}")
            return False
