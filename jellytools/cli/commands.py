"""
Command-line interface for jellytools.
"""
import os
import sys
import time
import logging
import click
import pygame
import cv2
from typing import List, Optional

from jellytools.core.config import load_config, create_default_config_file
from jellytools.core.server import ServerManager
from jellytools.core.utils import Utils
from jellytools.cli.syncing import sync_collections
from jellytools.animations.base import AnimationManager, WIDTH, HEIGHT, FPS, TOTAL_ANIMATION_TIME
from jellytools.animations import (
    PosterGridAnimation, 
    PosterMosaicAnimation, 
    PosterSpinAnimation, 
    PosterWaterfallAnimation
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def register_animations(animation_manager: AnimationManager) -> None:
    """
    Register available animations with the animation manager.
    
    Args:
        animation_manager (AnimationManager): Animation manager to register animations with
    """
    animation_manager.register_animation('grid', PosterGridAnimation)
    animation_manager.register_animation('waterfall', PosterWaterfallAnimation)
    animation_manager.register_animation('mosaic', PosterMosaicAnimation)
    animation_manager.register_animation('spiral', PosterSpinAnimation)


def render_animation(
    animation_manager: AnimationManager,
    library_name: str,
    animation_type: str,
    output_filename: str,
) -> str:
    """
    Render the entire animation to a high-res video file.
    
    Args:
        animation_manager (AnimationManager): Animation manager
        library_name (str): Name of the library to render
        animation_type (str): Type of animation to use
        output_filename (str): Path to save the output video
        
    Returns:
        str: Path to the rendered video file
    """
    # Initialize pygame if not already initialized
    if not pygame.get_init():
        pygame.init()

    # Load poster images
    posters = Utils.load_posters(library_name)

    # Create the animation
    animation = animation_manager.create_animation(
        animation_type, library_name, posters
    )

    # Set up video writer with 2.5K resolution
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Use mp4v codec
    video = cv2.VideoWriter(output_filename, fourcc, FPS, (WIDTH, HEIGHT))

    if not video.isOpened():
        logger.error(f"Error: Could not create video file {output_filename}")
        pygame.quit()
        sys.exit(1)

    # Create a surface for rendering
    surface = pygame.Surface((WIDTH, HEIGHT))

    # Calculate total frames
    total_frames = int(TOTAL_ANIMATION_TIME * FPS)

    logger.info(f"Rendering {total_frames} frames at {FPS} FPS in 2.5K resolution...")

    # Batch the rendering in chunks to avoid memory overruns
    chunk_size = 100
    for chunk_start in range(0, total_frames, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_frames)
        logger.info(f"Processing frames {chunk_start} to {chunk_end - 1}...")

        # Render each frame in this chunk
        for frame in range(chunk_start, chunk_end):
            # Calculate the time for this frame
            elapsed_seconds = frame / FPS

            # Clear surface with black
            surface.fill((0, 0, 0))

            # Update and draw the animation
            animation.update(elapsed_seconds)
            animation.draw(surface)

            # Render text overlay
            animation.render_text(elapsed_seconds, surface)

            # Convert pygame surface to numpy array for OpenCV
            frame_data = pygame.surfarray.array3d(surface)

            # Transpose array (pygame and OpenCV use different coordinate systems)
            frame_data = frame_data.transpose([1, 0, 2])

            # Convert RGB to BGR (pygame uses RGB, OpenCV uses BGR)
            frame_data = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)

            # Write the frame to the video
            video.write(frame_data)

            # Print progress within chunk
            if frame % 20 == 0:
                progress_msg = " ".join(
                    (
                        f"-- progress: {frame}/{total_frames} frames",
                        f"({frame / total_frames * 100:.1f}%)",
                    )
                )
                logger.info(progress_msg)

        # Force garbage collector to free memory after each chunk
        import gc
        gc.collect()

    # Release video writer
    video.release()
    logger.info(f"Animation rendered to {output_filename}")
    return output_filename


# Function for generating web versions (GIF/APNG) has been removed


@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """Jellytools - Utilities for working with Jellyfin media servers"""
    # Set up logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)


@cli.command()
@click.option('--file', '-f', type=click.Path(), default='config.py', 
              help='Path to create the configuration file (default: config.py)')
def init(file):
    """Initialize a new configuration file with default settings"""
    if os.path.exists(file):
        if not click.confirm(f"File {file} already exists. Overwrite?"):
            click.echo("Aborted.")
            return
    
    if create_default_config_file(file):
        click.echo(f"Configuration file created at {file}")
        click.echo("Please edit this file with your server details before running other commands.")
    else:
        click.echo(f"Failed to create configuration file at {file}")


@cli.command()
@click.option('--animation-type', '-a', 
              type=click.Choice(['grid', 'waterfall', 'mosaic', 'spiral']), 
              help='Animation type to use (overrides config)')
@click.option('--skip-hi-res', is_flag=True, help='Skip generating high-resolution MP4')
@click.option('--skip-download', is_flag=True, help='Skip downloading posters from servers')
@click.option('--output-dir', '-o', help='Output directory for videos')
@click.pass_context
def generate(ctx, animation_type, skip_hi_res, skip_download, output_dir):
    """Generate library card animations"""
    # Check dependencies first
    if not Utils.check_dependencies():
        click.echo("Missing required dependencies. Please install FFmpeg.")
        return 1

    click.echo("\n=== Starting Generation Process ===\n")
    start_time = time.time()

    # Initialize server manager
    server_manager = ServerManager()

    # Download posters if required
    if not skip_download:
        click.echo("\n--- Gathering Jellyfin Data ---")
        server_manager.download_jellyfin_posters()

    # Initialize animation manager
    animation_manager = AnimationManager()
    register_animations(animation_manager)

    # Show available animation types
    click.echo(f"Available animation types: {', '.join(animation_manager.get_animation_types())}")
    
    config = ctx.obj['config']
    
    # Use the output directory from config if not specified
    if output_dir is None:
        output_dir = config.DEFAULT_OUTPUT_DIR
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for library_name in config.JELLYFIN_LIBRARIES:
        # Initialize pygame
        pygame.init()
        
        # Determine which animation type to use:
        # 1. Command line argument overrides everything
        # 2. Library-specific configuration in config file
        # 3. Default animation type
        library_animation_type = animation_type
        if library_animation_type is None:
            library_animation_type = config.get_library_animation_type(library_name)
            
        click.echo(f"\n=== Processing library: {library_name} ===")
        click.echo(f"Using animation type: {library_animation_type}")

        # Generate the high-resolution animation
        hi_res_output = None
        if not skip_hi_res:
            click.echo("\n=== Generating High-Resolution Animation ===")
            hi_res_output = render_animation(
                animation_manager,
                library_name,
                library_animation_type,
                os.path.join(
                    output_dir,
                    f"{library_name}_{library_animation_type}_animation_hi_res.mp4",
                ),
            )
        else:
            click.echo("Skipping high-resolution animation generation.")
            # Look for existing high-res file
            potential_file = os.path.join(
                output_dir,
                f"{library_name}_{library_animation_type}_animation_hi_res.mp4",
            )
            if os.path.exists(potential_file):
                hi_res_output = potential_file

        # Web-friendly version generation has been removed

        elapsed_time = time.time() - start_time
        click.echo(f"\n=== Generation for {library_name} Complete ===")
        click.echo(f"Time elapsed: {elapsed_time:.2f} seconds")

        # Cleanup
        pygame.quit()

    click.echo("\nDone!")
    return 0


@cli.command()
@click.pass_context
def libraries(ctx):
    """List available libraries from configured servers"""
    # Initialize server manager
    server_manager = ServerManager()
    
    # Check Jellyfin libraries
    jellyfin_client = server_manager.get_jellyfin_client()
    if jellyfin_client:
        click.echo("\n=== Jellyfin Libraries ===")
        
        # Use the dedicated libraries_list method
        library_result = jellyfin_client.libraries_list()
        libraries = library_result.get("Items", [])
        
        if libraries:
            for lib in libraries:
                # Get collection type if available, otherwise use type
                lib_type = lib.get("CollectionType", lib.get("Type", "Unknown"))
                click.echo(f"- {lib['Name']} ({lib_type})")
        else:
            click.echo("No libraries found. This may be due to permission issues or API limitations.")
            
            # Fall back to the old method for debugging
            click.echo("\nTrying alternative method to list libraries...")
            items = jellyfin_client.items_list()
            alt_libraries = [item for item in items.get("Items", []) 
                          if item.get("Type") in ["CollectionFolder", "UserView", "Folder"]]
            
            if alt_libraries:
                click.echo("Found libraries using alternative method:")
                for lib in alt_libraries:
                    click.echo(f"- {lib['Name']} ({lib.get('Type', 'Unknown')})")
            else:
                # Additional debugging info
                click.echo("\nDebug information:")
                click.echo(f"Total items returned: {len(items.get('Items', []))}")
                click.echo("Item types found:")
                types_found = set(item.get("Type", "Unknown") for item in items.get("Items", []))
                for t in types_found:
                    click.echo(f"  - {t}")
    else:
        click.echo("Jellyfin client not configured.")
    
    # Check Plex libraries
    plex_client = server_manager.get_plex_client()
    if plex_client:
        click.echo("\n=== Plex Libraries ===")
        try:
            libraries = plex_client.library.sections()
            if libraries:
                for lib in libraries:
                    click.echo(f"- {lib.title} ({lib.type})")
            else:
                click.echo("No libraries found.")
        except Exception as e:
            click.echo(f"Error retrieving Plex libraries: {e}")
    else:
        click.echo("Plex client not configured.")


@cli.command()
@click.pass_context
def animations(ctx):
    """Show animation configuration for libraries"""
    config = ctx.obj['config']
    animation_manager = AnimationManager()
    register_animations(animation_manager)
    available_animations = animation_manager.get_animation_types()
    
    click.echo("\n=== Animation Configuration ===")
    click.echo(f"Default animation type: {config.DEFAULT_ANIMATION_TYPE}")
    click.echo(f"Available animation types: {', '.join(available_animations)}")
    
    click.echo("\n=== Per-Library Animation Configuration ===")
    if not config.LIBRARY_ANIMATIONS:
        click.echo("No library-specific animations configured.")
        return
    
    for library_name, library_config in config.LIBRARY_ANIMATIONS.items():
        animation_type = library_config.get("animation_type", config.DEFAULT_ANIMATION_TYPE)
        click.echo(f"- {library_name}: {animation_type}")
    
    click.echo("\n=== Libraries Without Specific Configuration ===")
    configured_libraries = set(config.LIBRARY_ANIMATIONS.keys())
    all_libraries = set(config.JELLYFIN_LIBRARIES)
    unconfigured = all_libraries - configured_libraries
    
    if unconfigured:
        for library in unconfigured:
            click.echo(f"- {library}: {config.DEFAULT_ANIMATION_TYPE} (default)")
    else:
        click.echo("All libraries have specific animation configurations.")


@cli.command()
@click.option('--skip-images', is_flag=True, help='Skip syncing images (faster)')
@click.option('--clean-only', is_flag=True, help='Only clean existing collections without creating new ones')
@click.pass_context
def sync(ctx, skip_images, clean_only):
    """Sync collections and artwork from Plex to Jellyfin"""
    # Initialize server manager
    server_manager = ServerManager()
    
    # Check if both servers are configured
    jellyfin_client = server_manager.get_jellyfin_client()
    plex_client = server_manager.get_plex_client()
    
    if not jellyfin_client:
        click.echo("Error: Jellyfin server not configured or connection failed")
        return 1
        
    if not plex_client:
        click.echo("Error: Plex server not configured or connection failed")
        return 1
    
    click.echo("\n=== Starting Plex to Jellyfin Synchronization ===\n")
    
    # Perform the sync
    if clean_only:
        from jellytools.cli.syncing import clean_jellyfin_collections
        click.echo("\n--- Cleaning Jellyfin Collections ---")
        clean_jellyfin_collections(server_manager)
        click.echo("\n=== Clean Operation Complete ===")
        return 0
    
    # We need to modify the sync function based on the skip_images flag
    # This implementation passes the flag all the way to the sync_collection_images function
    if skip_images:
        click.echo("Skipping image syncing for faster performance")
        # Define a wrapper function that overrides the normal collection image sync
        def skip_sync_collection_images(*args, **kwargs):
            return False
        
        # Mark the function as patched so we can detect it later
        skip_sync_collection_images.__patched_to_skip__ = True
            
        # Save the original function
        from jellytools.cli.syncing import sync_collection_images as original_sync
        
        # Replace with our no-op function
        import jellytools.cli.syncing
        jellytools.cli.syncing.sync_collection_images = skip_sync_collection_images
        
        # Run the sync
        results = sync_collections(server_manager)
        
        # Restore the original function
        jellytools.cli.syncing.sync_collection_images = original_sync
    else:
        results = sync_collections(server_manager)
    
    # Display summary
    click.echo("\n=== Synchronization Complete ===")
    click.echo(f"Time elapsed: {results['elapsed_time']:.2f} seconds")
    click.echo(f"Collections created: {results['collections_created']}")
    click.echo(f"Collections failed: {results['collections_failed']}")
    click.echo(f"Collections with images: {results['collections_with_images']}")
    click.echo(f"Media items with images: {results['media_with_images']}")
    
    return 0


def generate_cli():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    generate_cli()
