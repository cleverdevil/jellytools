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
import pathlib
from typing import List, Optional

from jellytools.core.config import load_config, create_default_config_file
from jellytools.core.server import ServerManager
from jellytools.core.utils import Utils
from jellytools.animations.base import (
    AnimationManager,
    WIDTH,
    HEIGHT,
    FPS,
    TOTAL_ANIMATION_TIME,
)
from jellytools.animations import (
    PosterGridAnimation,
    PosterSpinAnimation,
    PosterWaterfallAnimation,
    PosterMosaicAnimation,
    PosterVortexAnimation,
    PosterCascadeAnimation,
    PosterExplodeAnimation,
    PosterKaleidoscopeAnimation,
    PosterShockwaveAnimation,
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
    # Original animations
    animation_manager.register_animation("grid", PosterGridAnimation)
    animation_manager.register_animation("waterfall", PosterWaterfallAnimation)
    animation_manager.register_animation("spiral", PosterSpinAnimation)
    animation_manager.register_animation("mosaic", PosterMosaicAnimation)
    animation_manager.register_animation("vortex", PosterVortexAnimation)
    animation_manager.register_animation("cascade", PosterCascadeAnimation)
    animation_manager.register_animation("explode", PosterExplodeAnimation)
    animation_manager.register_animation("kaleidoscope", PosterKaleidoscopeAnimation)
    animation_manager.register_animation("shockwave", PosterShockwaveAnimation)


def render_animation(
    animation_manager: AnimationManager,
    library_name: str,
    animation_type: str,
    output_filename: str,
    save_last_frame: bool = True,
) -> dict:
    """
    Render the entire animation to a high-res video file.

    Args:
        animation_manager (AnimationManager): Animation manager
        library_name (str): Name of the library to render
        animation_type (str): Type of animation to use
        output_filename (str): Path to save the output video
        save_last_frame (bool): Whether to save the last frame as a PNG

    Returns:
        dict: Dictionary with paths to the rendered files:
              - 'video': Path to the rendered video file
              - 'thumbnail': Path to the PNG thumbnail (if saved)
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

    # Variables to store the last frame for thumbnail
    last_frame_data = None
    thumbnail_path = None

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

            # Store the last frame for thumbnail
            if frame == total_frames - 1:
                last_frame_data = frame_data.copy()

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

    # Save the last frame as PNG thumbnails if requested
    if save_last_frame and last_frame_data is not None:
        # Extract base naming components
        filename_parts = os.path.basename(output_filename).split('_')
        library_name = filename_parts[0]
        animation_name = filename_parts[1]
        
        # Save high-res thumbnail
        thumbnail_path = os.path.join(
            os.path.dirname(output_filename),
            f"{library_name}_{animation_name}_thumbnail_2k.png"
        )
        cv2.imwrite(thumbnail_path, last_frame_data)
        logger.info(f"High-res thumbnail saved to {thumbnail_path}")

        # Generate low-res thumbnail (480p)
        low_res_thumbnail_path = os.path.join(
            os.path.dirname(output_filename),
            f"{library_name}_{animation_name}_thumbnail_480p.png"
        )
        low_res_frame = cv2.resize(last_frame_data, (854, 480))
        cv2.imwrite(low_res_thumbnail_path, low_res_frame)
        logger.info(f"Low-res thumbnail saved to {low_res_thumbnail_path}")

    return {
        "video": output_filename,
        "thumbnail": thumbnail_path,
        "thumbnail_480p": low_res_thumbnail_path
        if save_last_frame and last_frame_data is not None
        else None,
    }


def generate_low_res_video(
    input_filename: str, width: int = 854, height: int = 480
) -> str:
    """
    Generate a low-resolution version of the video using ffmpeg.

    Args:
        input_filename (str): Path to the high-resolution video
        width (int): Target width (default: 854)
        height (int): Target height (default: 480)

    Returns:
        str: Path to the generated low-resolution video, or None if failed
    """
    import subprocess
    import os

    # Extract base naming components from input filename
    filename_parts = os.path.basename(input_filename).split('_')
    if len(filename_parts) >= 3:
        library_name = filename_parts[0]
        animation_name = filename_parts[1]
        
        # Generate output filename with consistent naming pattern
        output_filename = os.path.join(
            os.path.dirname(input_filename), 
            f"{library_name}_{animation_name}_video_480p.mp4"
        )
    else:
        # Fallback if the input filename format doesn't match expected pattern
        output_filename = input_filename.replace("_video_2k.mp4", "_video_480p.mp4")

    # Run ffmpeg to convert the video to low resolution
    try:
        logger.info(f"Generating low-resolution 480p version of {input_filename}")
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i",
            input_filename,  # Input file
            "-vf",
            f"scale={width}:{height}",  # Scale video
            "-c:v",
            "libx264",  # Use H.264 codec
            "-crf",
            "23",  # Quality setting (lower = better quality, higher = smaller file)
            "-preset",
            "medium",  # Encoding speed/compression trade-off
            "-c:a",
            "copy",  # Copy audio stream without re-encoding
            output_filename,
        ]

        # Use subprocess.run to execute the command
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check if the command was successful
        if result.returncode == 0:
            logger.info(
                f"Low-resolution video generated successfully: {output_filename}"
            )
            return output_filename
        else:
            logger.error(f"Failed to generate low-resolution video: {result.stderr}")
            return None
    except Exception as e:
        logger.error(f"Error generating low-resolution video: {e}")
        return None


@click.group()
@click.option("--config", "-c", help="Path to configuration file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, config, verbose):
    """Jellytools - Utilities for working with Jellyfin media servers"""
    # Set up logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.option(
    "--file",
    "-f",
    type=click.Path(),
    default="config.py",
    help="Path to create the configuration file (default: config.py)",
)
def init(file):
    """Initialize a new configuration file with default settings"""
    if os.path.exists(file):
        if not click.confirm(f"File {file} already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    if create_default_config_file(file):
        click.echo(f"Configuration file created at {file}")
        click.echo(
            "Please edit this file with your server details before running other commands."
        )
    else:
        click.echo(f"Failed to create configuration file at {file}")


@cli.command()
@click.option(
    "--animation-type",
    "-a",
    type=click.Choice(
        [
            "grid",
            "waterfall",
            "spiral",
            "mosaic",
            "vortex",
            "cascade",
            "explode",
            "kaleidoscope",
            "shockwave",
        ]
    ),
    help="Animation type to use (overrides config)",
)
@click.option("--skip-hi-res", is_flag=True, help="Skip generating high-resolution MP4")
@click.option(
    "--skip-low-res", is_flag=True, help="Skip generating 480p low-resolution MP4"
)
@click.option(
    "--skip-download", is_flag=True, help="Skip downloading posters from servers"
)
@click.option(
    "--skip-thumbnails",
    is_flag=True,
    help="Skip generating PNG thumbnails of the last frame",
)
@click.option("--skip-existing", is_flag=True, help="Skip animations that already exist in the output directory")
@click.option("--libraries", help="Comma-separated list of libraries to process (e.g. 'Movies,TV Shows')")
@click.option("--output-dir", "-o", help="Output directory for videos")
@click.pass_context
def generate(
    ctx,
    animation_type,
    skip_hi_res,
    skip_low_res,
    skip_download,
    skip_thumbnails,
    skip_existing,
    libraries,
    output_dir,
):
    """Generate library card animations
    
    By default, this command will generate animations for all libraries configured
    in your config file. Use the --libraries option to specify a subset of libraries.
    
    The --skip-existing flag allows you to skip regenerating animations that already
    exist in the output directory, which is useful when adding new animations or
    libraries to an existing set.
    """
    # Check dependencies first
    if not Utils.check_dependencies():
        click.echo("Missing required dependencies. Please install FFmpeg.")
        return 1

    click.echo("\n=== Starting Generation Process ===\n")
    start_time = time.time()

    # Initialize server manager
    server_manager = ServerManager()
    
    config = ctx.obj["config"]
    
    # Use the output directory from config if not specified
    if output_dir is None:
        output_dir = config.DEFAULT_OUTPUT_DIR

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Show additional information about operation modes
    if skip_existing:
        click.echo("\n--- Skip existing mode enabled: Only generating new animations ---")
        
    # Filter libraries if specified
    if libraries:
        target_libraries = [lib.strip() for lib in libraries.split(',')]
        click.echo(f"\n--- Only processing specified libraries: {', '.join(target_libraries)} ---")
        library_list = [lib for lib in config.JELLYFIN_LIBRARIES if lib in target_libraries]
        if not library_list:
            click.echo(f"Warning: None of the specified libraries {target_libraries} found in configuration")
            click.echo(f"Available libraries: {', '.join(config.JELLYFIN_LIBRARIES)}")
            return 1
    else:
        library_list = config.JELLYFIN_LIBRARIES
    
    # Download posters if required
    if not skip_download:
        click.echo("\n--- Gathering Jellyfin Data ---")
        # Call the poster download function with the specified libraries
        result = server_manager.download_jellyfin_posters(libraries=library_list)
        # Show simple summary of downloads
        total_downloaded = sum(result.get('downloaded', {}).values())
        total_skipped = sum(result.get('skipped', {}).values())
        click.echo(f"Downloaded {total_downloaded} new poster images, skipped {total_skipped} existing poster images")

    # Initialize animation manager
    animation_manager = AnimationManager()
    register_animations(animation_manager)

    # Show available animation types
    click.echo(
        f"Available animation types: {', '.join(animation_manager.get_animation_types())}"
    )
    
    for library_name in library_list:
        click.echo(f"\n=== Processing library: {library_name} ===")

        # Determine which animation types to use:
        # 1. Command line argument overrides everything
        # 2. Library-specific configuration in config file with animation_types or animation_type
        # 3. Default animation type
        if animation_type:
            # Use the CLI argument if provided
            library_animation_types = [animation_type]
            click.echo(f"Using animation type from command line: {animation_type}")
        else:
            # Get animation types from configuration
            library_animation_types = config.get_library_animation_types(library_name)
            if len(library_animation_types) == 1:
                click.echo(
                    f"Using animation type from config: {library_animation_types[0]}"
                )
            else:
                click.echo(
                    f"Using multiple animation types from config: {', '.join(library_animation_types)}"
                )

        # Process each animation type
        outputs = []
        skipped_outputs = []
        new_outputs = []
        for lib_animation_type in library_animation_types:
            # Initialize pygame
            pygame.init()

            click.echo(f"\n--- Generating {lib_animation_type} animation ---")

            # Generate the high-resolution animation
            hi_res_output = None
            if not skip_hi_res:
                output_filename = os.path.join(
                    output_dir,
                    f"{library_name}_{lib_animation_type}_video_2k.mp4",
                )
                
                # Check if file already exists and skip if requested
                if skip_existing and os.path.exists(output_filename):
                    click.echo(f"Skipping existing high-resolution animation: {os.path.basename(output_filename)}")
                    hi_res_output = output_filename
                    outputs.append(hi_res_output)
                    skipped_outputs.append(hi_res_output)
                else:
                    click.echo(f"Creating high-resolution {lib_animation_type} animation")
                    output_files = render_animation(
                        animation_manager,
                        library_name,
                        lib_animation_type,
                        output_filename,
                        save_last_frame=not skip_thumbnails,
                    )

                    hi_res_output = output_files["video"]
                    thumbnail = output_files["thumbnail"]

                    if thumbnail:
                        click.echo(f"High-res thumbnail saved to: {thumbnail}")

                    if output_files.get("thumbnail_480p"):
                        click.echo(
                            f"Low-res thumbnail saved to: {output_files['thumbnail_480p']}"
                        )

                    outputs.append(hi_res_output)
                    new_outputs.append(hi_res_output)

                # Generate low-resolution version if requested
                if not skip_low_res and hi_res_output:
                    # Check if low-res version already exists
                    potential_low_res = hi_res_output.replace("_video_2k.mp4", "_video_480p.mp4")
                    
                    if skip_existing and os.path.exists(potential_low_res):
                        click.echo(f"Skipping existing low-resolution animation: {os.path.basename(potential_low_res)}")
                        outputs.append(potential_low_res)
                        skipped_outputs.append(potential_low_res)
                    else:
                        click.echo(f"Generating 480p low-resolution version...")
                        low_res_output = generate_low_res_video(hi_res_output)
                        if low_res_output:
                            click.echo(
                                f"Low-resolution video saved to: {os.path.basename(low_res_output)}"
                            )
                            outputs.append(low_res_output)
                            new_outputs.append(low_res_output)
                        else:
                            click.echo("Failed to generate low-resolution video.")
                else:
                    click.echo("Skipping low-resolution video generation.")
            else:
                click.echo("Skipping high-resolution animation generation.")
                # Look for existing high-res file
                potential_file = os.path.join(
                    output_dir,
                    f"{library_name}_{lib_animation_type}_video_2k.mp4",
                )
                if os.path.exists(potential_file):
                    hi_res_output = potential_file
                    outputs.append(hi_res_output)
                    # Since we're skipping the high-res generation but still using the file,
                    # add it to skipped outputs list if skip_existing is enabled
                    if skip_existing:
                        skipped_outputs.append(hi_res_output)

            # Cleanup after each animation
            pygame.quit()

        elapsed_time = time.time() - start_time
        click.echo(f"\n=== Generation for {library_name} Complete ===")
        
        if skip_existing:
            click.echo(f"Generated {len(new_outputs)} new animations, skipped {len(skipped_outputs)} existing animations")
        else:
            click.echo(f"Generated {len(outputs)} animations")
            
        for output in outputs:
            filename = os.path.basename(output)
            click.echo(f"- {filename}")
        click.echo(f"Time elapsed: {elapsed_time:.2f} seconds")

    # Final summary
    total_elapsed_time = time.time() - start_time
    
    # Show filtered library info if applicable
    if libraries:
        click.echo(f"\n=== Processed {len(library_list)} of {len(config.JELLYFIN_LIBRARIES)} libraries ===")
    
    click.echo(f"\n=== Total time elapsed: {total_elapsed_time:.2f} seconds ===")
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
            click.echo(
                "No libraries found. This may be due to permission issues or API limitations."
            )

            # Fall back to the old method for debugging
            click.echo("\nTrying alternative method to list libraries...")
            items = jellyfin_client.items_list()
            alt_libraries = [
                item
                for item in items.get("Items", [])
                if item.get("Type") in ["CollectionFolder", "UserView", "Folder"]
            ]

            if alt_libraries:
                click.echo("Found libraries using alternative method:")
                for lib in alt_libraries:
                    click.echo(f"- {lib['Name']} ({lib.get('Type', 'Unknown')})")
            else:
                # Additional debugging info
                click.echo("\nDebug information:")
                click.echo(f"Total items returned: {len(items.get('Items', []))}")
                click.echo("Item types found:")
                types_found = set(
                    item.get("Type", "Unknown") for item in items.get("Items", [])
                )
                for t in types_found:
                    click.echo(f"  - {t}")
    else:
        click.echo("Jellyfin client not configured.")


@cli.group()
@click.pass_context
def posters(ctx):
    """Commands for managing poster artwork"""
    pass


@posters.command(name="fetch")
@click.option(
    "--clean-first", 
    is_flag=True, 
    help="Remove all existing poster files before downloading"
)
@click.option(
    "--libraries", 
    help="Comma-separated list of libraries to process (defaults to all configured libraries)"
)
@click.pass_context
def fetch_posters(ctx, clean_first, libraries):
    """
    Download poster artwork from Jellyfin for all configured libraries
    
    This command connects to Jellyfin and downloads missing poster artwork for each 
    library configured in your config file. Use the --clean-first option to remove
    all existing artwork before downloading.
    """
    # Initialize server manager
    server_manager = ServerManager()
    config = ctx.obj["config"]
    
    # Get the poster directory
    poster_dir = pathlib.Path(config.POSTER_DIRECTORY)
    if not poster_dir.exists():
        poster_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"Created poster directory: {poster_dir}")
    
    # Filter libraries if specified
    if libraries:
        target_libraries = [lib.strip() for lib in libraries.split(',')]
        click.echo(f"\n--- Only processing specified libraries: {', '.join(target_libraries)} ---")
        library_list = [lib for lib in config.JELLYFIN_LIBRARIES if lib in target_libraries]
        if not library_list:
            click.echo(f"Warning: None of the specified libraries {target_libraries} found in configuration")
            click.echo(f"Available libraries: {', '.join(config.JELLYFIN_LIBRARIES)}")
            return 1
    else:
        library_list = config.JELLYFIN_LIBRARIES
    
    # Clean existing poster directories if requested
    if clean_first:
        click.echo("\n=== Cleaning existing poster directories ===")
        for library_name in library_list:
            library_poster_dir = poster_dir / library_name
            if library_poster_dir.exists():
                click.echo(f"Removing posters for library: {library_name}")
                try:
                    # Count files before removal
                    file_count = sum(1 for f in library_poster_dir.iterdir() if f.is_file())
                    # Remove all files in directory
                    for file_path in library_poster_dir.iterdir():
                        if file_path.is_file():
                            file_path.unlink()
                    click.echo(f"Removed {file_count} poster files from {library_name}")
                except Exception as e:
                    click.echo(f"Error cleaning directory {library_poster_dir}: {e}")
            else:
                click.echo(f"Library poster directory not found for {library_name}, skipping")
    
    # Download posters
    click.echo("\n=== Downloading poster artwork from Jellyfin ===")
    try:
        result = server_manager.download_jellyfin_posters(libraries=library_list)
        
        # Show summary
        total_libraries = len(library_list)
        total_downloaded = sum(result.get('downloaded', {}).values())
        total_skipped = sum(result.get('skipped', {}).values())
        
        click.echo("\n=== Poster Download Summary ===")
        click.echo(f"Processed {total_libraries} libraries")
        click.echo(f"Downloaded {total_downloaded} new poster images")
        click.echo(f"Skipped {total_skipped} existing poster images")
        
        # Show per-library details
        click.echo("\nPer-library details:")
        for library_name in library_list:
            downloaded = result.get('downloaded', {}).get(library_name, 0)
            skipped = result.get('skipped', {}).get(library_name, 0)
            click.echo(f"- {library_name}: {downloaded} new, {skipped} existing")
        
        return 0
    except Exception as e:
        click.echo(f"Error downloading posters: {e}")
        return 1



@cli.command()
@click.pass_context
def animations(ctx):
    """Show animation configuration for libraries"""
    config = ctx.obj["config"]
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
        animation_types = library_config.get("animation_types", [])
        if not animation_types:
            animation_type = library_config.get(
                "animation_type", config.DEFAULT_ANIMATION_TYPE
            )
            click.echo(f"- {library_name}: {animation_type}")
        else:
            click.echo(f"- {library_name}: {', '.join(animation_types)}")

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
@click.option(
    "--output", "-o", 
    type=click.Path(), 
    default="jellyfin-override.js",
    help="Output file for the JavaScript (default: jellyfin-override.js)"
)
@click.option(
    "--replay/--no-replay",
    default=False,
    help="Allow videos to replay each time the element is hovered over (default: false)"
)
@click.option(
    "--hide-labels/--show-labels",
    default=True,
    help="Hide the text labels for library cards (default: true)"
)
@click.pass_context
def generate_js(ctx, output, replay, hide_labels):
    """Generate JavaScript for the Jellyfin Custom JavaScript Plugin that adds hover-triggered videos to library cards"""
    config = ctx.obj["config"]
    
    # Initialize server manager to connect to Jellyfin
    server_manager = ServerManager()
    jellyfin_client = server_manager.get_jellyfin_client()
    
    if not jellyfin_client:
        click.echo("Error: Jellyfin server not configured or connection failed")
        return 1
    
    click.echo("\n=== Generating JavaScript for Jellyfin Custom JavaScript Plugin ===\n")
    click.echo(f"Video replay on hover: {'Enabled' if replay else 'Disabled'}")
    click.echo(f"Hide text labels: {'Enabled' if hide_labels else 'Disabled'}")
    
    # Get libraries from Jellyfin
    library_result = jellyfin_client.libraries_list()
    libraries = library_result.get("Items", [])
    
    if not libraries:
        click.echo("Error: No libraries found on Jellyfin server")
        return 1
    
    # Store libraries for JS generation
    js_libraries = []
    
    # Process each library
    for library in libraries:
        library_name = library.get("Name")
        library_id = library.get("Id")
        
        # Skip if no ID
        if not library_id:
            continue
            
        # Ask user for video URL for this library
        video_url = click.prompt(
            f"Enter video URL for library '{library_name}' (press Enter to skip)", 
            default=""
        )
        
        # Skip if no URL provided
        if not video_url:
            click.echo(f"Skipping library '{library_name}'")
            continue
            
        # Add to our libraries list
        js_libraries.append({
            "Name": library_name,
            "Id": library_id,
            "VideoURL": video_url
        })
    
    if not js_libraries:
        click.echo("No libraries selected for JavaScript generation")
        return 1
    
    # Generate JavaScript file
    try:
        with open(output, "w") as f:
            # Write the template JavaScript with the libraries configuration
            f.write("// Self-executing function to avoid global namespace pollution\n")
            f.write("(function() {\n")
            f.write("  // Configuration\n")
            f.write("  const config = {\n")
            f.write(f"    allowReplay: {str(replay).lower()},  // Allow videos to replay on hover\n")
            f.write(f"    hideLabels: {str(hide_labels).lower()}   // Hide the text labels for library cards\n")
            f.write("  };\n")
            f.write("\n")
            f.write("  const libraries = [\n")
            
            # Add each library
            for i, library in enumerate(js_libraries):
                f.write(f"    {{\n")
                f.write(f'      Id: "{library["Id"]}",\n')
                f.write(f'      VideoURL: "{library["VideoURL"]}"\n')
                f.write(f"    }}{'' if i == len(js_libraries) - 1 else ','}\n")
            
            f.write("  ];\n")
            f.write("\n")
            f.write("  // Constants\n")
            f.write("  const checkInterval = 100; // Check every 100ms\n")
            f.write("  const maxAttempts = 100;   // Try for ~10 seconds max (100 * 100ms)\n")
            f.write("\n")
            f.write("  // Clone the array to track which libraries still need processing\n")
            f.write("  let pendingLibraries = [...libraries];\n")
            f.write("  let attempts = 0;\n")
            f.write("\n")
            f.write("  // Function to set up hover video for element\n")
            f.write("  function replaceWithVideo(element, videoUrl) {\n")
            f.write("    // Check if the element already has a video (avoid duplicates)\n")
            f.write("    if (element.querySelector('video')) return;\n")
            f.write("\n")
            f.write("    // Create and configure video element\n")
            f.write("    const video = document.createElement('video');\n")
            f.write("    Object.assign(video, {\n")
            f.write("      src: videoUrl,\n")
            f.write("      muted: true,\n")
            f.write("      playsInline: true,\n")
            f.write("      preload: 'auto'\n")
            f.write("    });\n")
            f.write("\n")
            f.write("    // Style the video\n")
            f.write("    Object.assign(video.style, {\n")
            f.write("      position: 'absolute',\n")
            f.write("      top: '0',\n")
            f.write("      left: '0',\n")
            f.write("      width: '100%',\n")
            f.write("      height: '100%',\n")
            f.write("      objectFit: 'cover',\n")
            f.write("      opacity: '0',\n")
            f.write("      transition: 'opacity 0.3s ease-in-out',\n")
            f.write("      zIndex: '1000'\n")
            f.write("    });\n")
            f.write("\n")
            f.write("    // Insert the video but keep background image visible\n")
            f.write("    element.insertBefore(video, element.firstChild);\n")
            f.write("\n")
            f.write("    // Find the card indicators\n")
            f.write("    const cardIndicators = element.querySelector('.cardIndicators');\n")
            f.write("    \n")
            if not replay:
                f.write("    // Track if the video has played\n")
                f.write("    video.hasPlayed = false;\n")
                f.write("\n")
            
            f.write("    // Add hover event listener\n")
            f.write("    element.parentElement.addEventListener('mouseenter', function() {\n")
            
            if replay:
                # When replay is enabled, always play the video on mouseenter
                f.write("      video.style.opacity = '1';\n")
                f.write("      element.style.backgroundImage = 'none';\n")
                f.write("      if (cardIndicators) cardIndicators.style.opacity = '0';\n")
                f.write("      video.currentTime = 0;\n")
                f.write("      video.play().catch(() => {});\n")
            else:
                # When replay is disabled, only play if it hasn't played before
                f.write("      if (video.paused && !video.hasPlayed) {\n")
                f.write("        video.style.opacity = '1';\n")
                f.write("        element.style.backgroundImage = 'none';\n")
                f.write("        if (cardIndicators) cardIndicators.style.opacity = '0';\n")
                f.write("        video.currentTime = 0;\n")
                f.write("        video.play().catch(() => {});\n")
                f.write("        video.hasPlayed = true;\n")
                f.write("      }\n")
            
            f.write("    });\n")
            f.write("  }\n")
            f.write("\n")
            f.write("  // Function to check for each target element\n")
            f.write("  function checkForElements() {\n")
            f.write("    const stillPending = [];\n")
            f.write("\n")
            f.write("    // Check each pending library\n")
            f.write("    pendingLibraries.forEach(library => {\n")
            f.write("      const card = document.querySelector('div[data-id=\"' + library.Id + '\"]');\n")
            f.write("      \n")
            f.write("      if (card) {\n")
            f.write("        const element = card.querySelector('a.cardImageContainer');\n")
            f.write("        \n")
            f.write("        if (element) {\n")
            
            # Only hide labels if configured to do so
            if hide_labels:
                f.write("          // Hide the label if configured to do so\n")
                f.write("          if (config.hideLabels) {\n")
                f.write("            const textElement = element.parentElement.parentElement.querySelector('.cardText');\n")
                f.write("            if (textElement) textElement.style.display = 'none';\n")
                f.write("          }\n")
            
            f.write("          // Set up video\n")
            f.write("          replaceWithVideo(element, library.VideoURL);\n")
            f.write("        } else {\n")
            f.write("          stillPending.push(library);\n")
            f.write("        }\n")
            f.write("      } else {\n")
            f.write("        stillPending.push(library);\n")
            f.write("      }\n")
            f.write("    });\n")
            f.write("\n")
            f.write("    // Update pending libraries list\n")
            f.write("    pendingLibraries = stillPending;\n")
            f.write("    \n")
            f.write("    // Return whether all elements were found\n")
            f.write("    return pendingLibraries.length === 0;\n")
            f.write("  }\n")
            f.write("\n")
            f.write("  // Start polling when the document is ready\n")
            f.write("  function startPolling() {\n")
            f.write("    // First, immediately check if all elements exist\n")
            f.write("    if (checkForElements()) return;\n")
            f.write("\n")
            f.write("    // Set up interval to check periodically\n")
            f.write("    const intervalId = setInterval(() => {\n")
            f.write("      attempts++;\n")
            f.write("\n")
            f.write("      if (checkForElements()) {\n")
            f.write("        // All elements found\n")
            f.write("        clearInterval(intervalId);\n")
            f.write("      } else if (attempts >= maxAttempts) {\n")
            f.write("        // Max attempts reached\n")
            f.write("        clearInterval(intervalId);\n")
            f.write("      }\n")
            f.write("    }, checkInterval);\n")
            f.write("  }\n")
            f.write("\n")
            f.write("  // Initialize the script\n")
            f.write("  if (document.readyState === 'loading') {\n")
            f.write("    document.addEventListener('DOMContentLoaded', startPolling);\n")
            f.write("  } else {\n")
            f.write("    startPolling();\n")
            f.write("  }\n")
            f.write("})();\n")
        
        click.echo(f"\nJavaScript successfully generated to {output}")
        click.echo(f"\nLibraries included in the JavaScript:")
        for library in js_libraries:
            click.echo(f"- {library['Name']} (ID: {library['Id']})")
        
        click.echo("\nThe JavaScript will add hidden videos to Jellyfin library cards while maintaining their original appearance.")
        click.echo("The videos will play when a user hovers over a library card.")
        
        if replay:
            click.echo("Videos will replay each time a user hovers over a card.")
        else:
            click.echo("Each video will play only once per page load.")
            
        if hide_labels:
            click.echo("Text labels for library cards will be hidden to provide a cleaner video experience.")
        else:
            click.echo("Text labels for library cards will remain visible.")
            
        click.echo("\nYou can now paste this JavaScript into the Jellyfin Custom JavaScript Plugin settings.")
        click.echo("Plugin URL: https://github.com/johnpc/jellyfin-plugin-custom-javascript")
        
        click.echo("\nTo regenerate with different options, use:")
        replay_option = "--replay" if replay else "--no-replay"
        labels_option = "--hide-labels" if hide_labels else "--show-labels"
        click.echo(f"jellytools generate-js {replay_option} {labels_option}")
        
        return 0
        
    except Exception as e:
        click.echo(f"Error generating JavaScript: {e}")
        return 1




def generate_cli():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    generate_cli()
