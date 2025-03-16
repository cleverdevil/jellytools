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
    def load_posters(library_name: str) -> List[pygame.Surface]:
        """
        Load images from the posters directory for a specific library.

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
        posters = []
        posters_dir = pathlib.Path(config.POSTER_DIRECTORY) / library_name
        if not posters_dir.exists():
            logger.error(f"Error: posters directory {posters_dir} not found.")
            pygame.quit()
            sys.exit(1)

        logger.info(f"Loading poster images from {posters_dir}...")
        poster_files = []
        for filename in os.listdir(posters_dir):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                poster_files.append(filename)

        # Process all available poster files
        for filename in poster_files:
            try:
                img_path = posters_dir / filename
                img = pygame.image.load(img_path).convert_alpha()

                # Scale images to maintain aspect ratio - adjusted for 2.5K resolution
                aspect_ratio = img.get_width() / img.get_height()
                new_height = 210  # Reduced from 280 for memory efficiency
                new_width = int(new_height * aspect_ratio)

                # Use smoothscale for better quality
                img = pygame.transform.smoothscale(img, (new_width, new_height))
                posters.append(img)
            except pygame.error as e:
                logger.error(f"Error loading image {filename}: {e}")

        # Check if we loaded any posters at all
        if not posters:
            logger.error(
                f"Error: No valid poster images found in '{posters_dir}' directory."
            )
            pygame.quit()
            sys.exit(1)

        # Reduce the duplicate count to prevent memory issues
        # If we don't have at least 300 posters, duplicate existing ones to reach that number
        while len(posters) < 300:
            posters.extend(posters[: min(len(posters), 300 - len(posters))])

        logger.info(f"Successfully loaded {len(posters)} poster images.")
        return posters


class SyncDatabase:
    """Manage synced item state in an SQLite database."""
    
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
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)  # Increase timeout to handle contention
            cursor = conn.cursor()
            
            # Create collections sync table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_sync (
                collection_id TEXT PRIMARY KEY,
                collection_name TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create media sync table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_sync (
                media_id TEXT PRIMARY KEY,
                media_name TEXT,
                sync_type TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            logger.debug(f"Successfully initialized sync database at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"SQLite error initializing database: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize sync database: {e}")
        finally:
            if conn:
                conn.close()
    
    def mark_collection_synced(self, collection_id: str, collection_name: str) -> bool:
        """
        Mark a collection as having been synced.
        
        Args:
            collection_id (str): Jellyfin collection ID
            collection_name (str): Collection name for reference
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO collection_sync (collection_id, collection_name, last_synced)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (collection_id, collection_name))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error marking collection {collection_id} as synced: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to mark collection {collection_id} as synced: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def is_collection_synced(self, collection_id: str) -> bool:
        """
        Check if a collection has been synced.
        
        Args:
            collection_id (str): Jellyfin collection ID
            
        Returns:
            bool: True if synced, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            cursor.execute('SELECT collection_id FROM collection_sync WHERE collection_id = ?', (collection_id,))
            result = cursor.fetchone()
            
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"SQLite error checking if collection {collection_id} is synced: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to check if collection {collection_id} is synced: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
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
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO media_sync (media_id, media_name, sync_type, last_synced)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (media_id, media_name, sync_type))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error marking media {media_id} as synced: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to mark media {media_id} as synced: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def is_media_synced(self, media_id: str, sync_type: str = "artwork") -> bool:
        """
        Check if a media item has been synced.
        
        Args:
            media_id (str): Jellyfin media ID
            sync_type (str): Type of sync to check
            
        Returns:
            bool: True if synced, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT media_id FROM media_sync WHERE media_id = ? AND sync_type = ?', 
                (media_id, sync_type)
            )
            result = cursor.fetchone()
            
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"SQLite error checking if media {media_id} is synced: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to check if media {media_id} is synced: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def reset_sync_data(self, sync_type: Optional[str] = None) -> bool:
        """
        Reset sync data, either for a specific type or all.
        
        Args:
            sync_type (str, optional): Type of sync to reset (collections, artwork),
                                      or None to reset all data
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            if sync_type == "collections":
                cursor.execute('DELETE FROM collection_sync')
                logger.info("Reset all collection sync data")
            elif sync_type == "artwork":
                cursor.execute('DELETE FROM media_sync WHERE sync_type = ?', (sync_type,))
                logger.info(f"Reset sync data for {sync_type}")
            else:
                # Reset all data
                cursor.execute('DELETE FROM collection_sync')
                cursor.execute('DELETE FROM media_sync')
                logger.info("Reset all sync data")
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error resetting sync data: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to reset sync data: {e}")
            return False
        finally:
            if conn:
                conn.close()
