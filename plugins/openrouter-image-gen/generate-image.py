#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "rich"]
# ///
"""
Generate images via OpenRouter's image generation API.
Uses the chat completions endpoint with image modalities.
"""

import argparse
import base64
import json
import mimetypes
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_MODEL = "google/gemini-3-pro-image-preview"

# Config file search locations (in order of priority)
CONFIG_LOCATIONS = [
    Path.cwd() / ".openrouter-config",
    Path.home() / ".config" / "openrouter" / "config",
    Path.home() / ".openrouter-config",
]

# Use XDG state directory for all generated content
XDG_STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
OUTPUT_DIR = XDG_STATE_HOME / "openrouter-image-gen" / "output"
SESSIONS_DIR = XDG_STATE_HOME / "openrouter-image-gen" / "sessions"

ASPECT_RATIOS = {
    "1:1": "1024×1024",
    "2:3": "832×1248",
    "3:2": "1248×832",
    "3:4": "864×1184",
    "4:3": "1184×864",
    "4:5": "896×1152",
    "5:4": "1152×896",
    "9:16": "768×1344",
    "16:9": "1344×768",
    "21:9": "1536×672",
}

IMAGE_SIZES = ["1K", "2K", "4K"]

console = Console()


def load_api_key() -> str:
    """Load the OpenRouter API key from environment or config file."""
    # Check environment variable first
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    # Search config file locations
    config_file = None
    for path in CONFIG_LOCATIONS:
        if path.exists():
            config_file = path
            break

    if not config_file:
        locations = "\n".join(f"  - {p}" for p in CONFIG_LOCATIONS)
        console.print(
            Panel(
                f"OpenRouter API key not found.\n\n"
                f"Set the OPENROUTER_API_KEY environment variable, or create a config file at one of:\n"
                f"{locations}\n\n"
                f"Config file format:\n"
                f"  OPENROUTER_API_KEY=your-key-here",
                title="Configuration Error",
                border_style="red",
            )
        )
        sys.exit(1)

    config = {}
    for line in config_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()

    api_key = config.get("OPENROUTER_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        console.print(f"[red]Error:[/red] OPENROUTER_API_KEY not set in {config_file}")
        sys.exit(1)

    return api_key


def upload_to_litterbox(image_path: Path, expiry: str = "1h") -> str:
    """Upload an image to Litterbox temporary hosting and return the URL."""
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": expiry},
            files={"fileToUpload": (image_path.name, f)},
            timeout=60,
        )
        response.raise_for_status()
        return response.text.strip()


# Session management functions
def get_session_dir(name: str) -> Path:
    """Get the directory path for a named session."""
    return SESSIONS_DIR / name


def load_session(name: str) -> dict | None:
    """Load session state from disk. Returns None if session doesn't exist."""
    session_dir = get_session_dir(name)
    session_file = session_dir / "session.json"
    if not session_file.exists():
        return None
    return json.loads(session_file.read_text())


def save_session(name: str, data: dict) -> None:
    """Save session state to disk."""
    session_dir = get_session_dir(name)
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "session.json"
    session_file.write_text(json.dumps(data, indent=2))


def get_latest_session() -> str | None:
    """Find the most recently modified session. Returns session name or None."""
    if not SESSIONS_DIR.exists():
        return None
    sessions = [d for d in SESSIONS_DIR.iterdir() if d.is_dir() and (d / "session.json").exists()]
    if not sessions:
        return None
    # Sort by modification time of session.json
    sessions.sort(key=lambda d: (d / "session.json").stat().st_mtime, reverse=True)
    return sessions[0].name


def list_sessions() -> None:
    """Display all available sessions."""
    if not SESSIONS_DIR.exists():
        console.print("[yellow]No sessions found.[/yellow]")
        return

    sessions = [d for d in SESSIONS_DIR.iterdir() if d.is_dir() and (d / "session.json").exists()]
    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    # Sort by modification time
    sessions.sort(key=lambda d: (d / "session.json").stat().st_mtime, reverse=True)

    table = Table(title="Image Generation Sessions")
    table.add_column("Session", style="cyan")
    table.add_column("Model", style="dim")
    table.add_column("Messages", justify="right")
    table.add_column("Images", justify="right")
    table.add_column("Last Modified", style="dim")

    for session_dir in sessions:
        data = load_session(session_dir.name)
        if data:
            msg_count = len(data.get("messages", []))
            img_count = len(list(session_dir.glob("*.png"))) + len(list(session_dir.glob("*.jpg")))
            mtime = datetime.fromtimestamp((session_dir / "session.json").stat().st_mtime)
            table.add_row(
                session_dir.name,
                data.get("model", "unknown"),
                str(msg_count),
                str(img_count),
                mtime.strftime("%Y-%m-%d %H:%M"),
            )

    console.print(table)


def delete_session(name: str) -> bool:
    """Delete a session and all its files. Returns True if successful."""
    session_dir = get_session_dir(name)
    if not session_dir.exists():
        return False
    shutil.rmtree(session_dir)
    return True


def list_image_models() -> None:
    """Fetch and display all models that support image output."""
    api_key = load_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    with console.status("[bold blue]Fetching models...[/bold blue]"):
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching models:[/red] {e}")
            sys.exit(1)

    models = result.get("data", [])

    # Filter to models with image output capability
    image_models = [
        m
        for m in models
        if "image" in m.get("architecture", {}).get("output_modalities", [])
    ]

    if not image_models:
        console.print("[yellow]No image generation models found.[/yellow]")
        return

    # Sort by name
    image_models.sort(key=lambda m: m.get("name", "").lower())

    # Build table
    table = Table(title=f"Image Generation Models ({len(image_models)} available)")
    table.add_column("Model ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Context", justify="right", style="dim")
    table.add_column("Pricing (per image)", justify="right", style="green")

    for model in image_models:
        model_id = model.get("id", "")
        name = model.get("name", "")
        context = model.get("context_length")
        context_str = f"{context:,}" if context else "-"

        # Get image output pricing
        pricing = model.get("pricing", {})
        image_price = pricing.get("image_output") or pricing.get("image")
        if image_price:
            try:
                price_float = float(image_price)
                if price_float == 0:
                    price_str = "[bold green]free[/bold green]"
                else:
                    price_str = f"${price_float:.4f}"
            except (ValueError, TypeError):
                price_str = str(image_price)
        else:
            price_str = "-"

        table.add_row(model_id, name, context_str, price_str)

    console.print(table)


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    output_file: str | None = None,
    reference_images: list[Path] | None = None,
    session_name: str | None = None,
) -> list[Path]:
    """Generate images using OpenRouter's chat completions API."""
    api_key = load_api_key()

    # Load existing session if continuing
    session_data: dict | None = None
    messages: list[dict] = []
    if session_name:
        session_data = load_session(session_name)
        if session_data:
            messages = session_data.get("messages", [])
            # Use session's model/config if not explicitly overridden
            if model == DEFAULT_MODEL and session_data.get("model"):
                model = session_data["model"]
            if aspect_ratio is None and session_data.get("aspect_ratio"):
                aspect_ratio = session_data["aspect_ratio"]
            if image_size is None and session_data.get("image_size"):
                image_size = session_data["image_size"]
            console.print(f"[dim]Continuing session: {session_name} ({len(messages)} previous messages)[/dim]")

    console.print(f"[bold]Prompt:[/bold] {prompt}")
    console.print(f"[dim]Model: {model}[/dim]")
    if aspect_ratio:
        console.print(
            f"[dim]Aspect ratio: {aspect_ratio} ({ASPECT_RATIOS.get(aspect_ratio, 'custom')})[/dim]"
        )
    if image_size:
        console.print(f"[dim]Image size: {image_size}[/dim]")

    # Upload reference images if provided
    reference_urls: list[str] = []
    if reference_images:
        console.print(f"[dim]Reference images: {len(reference_images)}[/dim]")
        with console.status("[bold blue]Uploading reference images...[/bold blue]"):
            for img_path in reference_images:
                if not img_path.exists():
                    console.print(f"[yellow]Warning:[/yellow] Reference image not found: {img_path}")
                    continue
                try:
                    url = upload_to_litterbox(img_path)
                    reference_urls.append(url)
                    console.print(f"[dim]  Uploaded: {img_path.name}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Warning:[/yellow] Failed to upload {img_path.name}: {e}")

    # For continuing sessions, upload previous generated images so model can see them
    if session_name and session_data and not reference_urls:
        session_dir = get_session_dir(session_name)
        prev_images = sorted(session_dir.glob("*.png")) + sorted(session_dir.glob("*.jpg"))
        if prev_images:
            # Upload the most recent image(s) for context
            latest_image = prev_images[-1]
            console.print(f"[dim]Including previous image: {latest_image.name}[/dim]")
            with console.status("[bold blue]Uploading previous image for context...[/bold blue]"):
                try:
                    url = upload_to_litterbox(latest_image)
                    reference_urls.append(url)
                except Exception as e:
                    console.print(f"[yellow]Warning:[/yellow] Failed to upload previous image: {e}")

    console.print()

    # Build message content - multimodal if we have reference images
    if reference_urls:
        content: list[dict] | str = []
        for url in reference_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url},
            })
        content.append({
            "type": "text",
            "text": prompt,
        })
    else:
        content = prompt

    # Add new user message to history
    new_user_message = {"role": "user", "content": content}
    messages.append(new_user_message)

    # Build request payload
    payload = {
        "model": model,
        "messages": messages,
        "modalities": ["image", "text"],
    }

    # Add image config if specified
    if aspect_ratio or image_size:
        payload["image_config"] = {}
        if aspect_ratio:
            payload["image_config"]["aspect_ratio"] = aspect_ratio
        if image_size:
            payload["image_config"]["image_size"] = image_size

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anthropics/claude-code",
        "X-Title": "Claude Code Image Generation",
    }

    with console.status("[bold blue]Generating image...[/bold blue]"):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = response.json().get("error", {}).get("message", "")  # pyright: ignore[reportPossiblyUnboundVariable]
            except Exception:
                error_detail = response.text[:200]  # pyright: ignore[reportPossiblyUnboundVariable]
            console.print(
                f"[red]API Error ({response.status_code}):[/red] {error_detail or e}"  # pyright: ignore[reportPossiblyUnboundVariable]
            )
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Request Error:[/red] {e}")
            sys.exit(1)

    # Extract images from response
    choices = result.get("choices", [])
    if not choices:
        console.print("[red]Error:[/red] No choices in response")
        sys.exit(1)

    message = choices[0].get("message", {})
    images = message.get("images", [])

    # Also print any text content from the model
    text_content = message.get("content")
    if text_content:
        console.print(Panel(text_content, title="[cyan]Model Response[/cyan]", border_style="cyan"))

    if not images:
        console.print("[red]Error:[/red] No images in response")
        console.print(
            "[dim]The model may not support image generation, or the prompt was filtered.[/dim]"
        )
        sys.exit(1)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate base filename if not provided
    if output_file:
        base_name = Path(output_file).stem
        extension = Path(output_file).suffix or ".png"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"image_{timestamp}"
        extension = ".png"

    saved_files: list[Path] = []
    session_image_files: list[str] = []  # Track image filenames for session

    for i, image_data in enumerate(images):
        # Determine filename
        if len(images) == 1:
            filename = f"{base_name}{extension}"
        else:
            filename = f"{base_name}_{i + 1}{extension}"

        file_path = OUTPUT_DIR / filename

        # Extract base64 data from data URL
        image_url = image_data.get("image_url", {}).get("url", "")

        if not image_url:
            console.print(f"[yellow]Warning:[/yellow] No image URL for result {i + 1}")
            continue

        # Parse data URL (format: data:image/png;base64,<data>)
        if image_url.startswith("data:"):
            try:
                # Split off the header
                header, b64_data = image_url.split(",", 1)
                image_bytes = base64.b64decode(b64_data)
                file_path.write_bytes(image_bytes)
                saved_files.append(file_path)
                session_image_files.append(filename)
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to decode image {i + 1}: {e}"
                )
        else:
            # It's a regular URL, download it
            try:
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                file_path.write_bytes(img_response.content)
                saved_files.append(file_path)
                session_image_files.append(filename)
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to download image {i + 1}: {e}"
                )

    # Save session state if using sessions
    if session_name:
        # Build assistant message with images as proper content parts
        assistant_content: list[dict] | str
        if images:
            assistant_content = []
            # Include any text response
            if text_content:
                assistant_content.append({"type": "text", "text": text_content})
            # Include generated images with their base64 data URLs
            for image_data in images:
                image_url = image_data.get("image_url", {}).get("url", "")
                if image_url:
                    assistant_content.append({
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    })
        else:
            assistant_content = text_content or ""

        assistant_message = {
            "role": "assistant",
            "content": assistant_content,
        }
        messages.append(assistant_message)

        # Save session
        session_data = {
            "model": model,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "messages": messages,
            "created": session_data.get("created") if session_data else datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        save_session(session_name, session_data)

        # Copy images to session folder
        session_dir = get_session_dir(session_name)
        for file_path in saved_files:
            dest = session_dir / file_path.name
            shutil.copy2(file_path, dest)

        console.print(f"[dim]Session saved: {session_name}[/dim]")

    return saved_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using OpenRouter's API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Aspect ratios:
  {", ".join(ASPECT_RATIOS.keys())}

Image sizes (Gemini only):
  {", ".join(IMAGE_SIZES)}

Examples:
  %(prog)s "A serene mountain landscape at sunset"
  %(prog)s -a 16:9 -o landscape.png "Mountain at sunset"
  %(prog)s -a 1:1 -s 4K "High resolution portrait"
  %(prog)s --list-models
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="The image generation prompt",
    )
    parser.add_argument(
        "-l",
        "--list-models",
        action="store_true",
        help="List all available image generation models",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename (default: auto-generated timestamp)",
    )
    parser.add_argument(
        "-a",
        "--aspect-ratio",
        choices=list(ASPECT_RATIOS.keys()),
        help="Aspect ratio for the image",
    )
    parser.add_argument(
        "-s",
        "--size",
        choices=IMAGE_SIZES,
        help="Image size/resolution (Gemini models only)",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-r",
        "--reference",
        action="append",
        type=Path,
        dest="reference_images",
        metavar="IMAGE",
        help="Reference image(s) for style/content guidance (can be used multiple times)",
    )

    # Session management arguments
    parser.add_argument(
        "--session",
        metavar="NAME",
        help="Create or continue a named session for iterative refinement",
    )
    parser.add_argument(
        "--continue",
        dest="continue_latest",
        action="store_true",
        help="Continue the most recent session",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all available sessions",
    )
    parser.add_argument(
        "--delete-session",
        metavar="NAME",
        help="Delete a session and all its files",
    )

    args = parser.parse_args()

    if args.list_sessions:
        list_sessions()
        return

    if args.delete_session:
        if delete_session(args.delete_session):
            console.print(f"[green]Deleted session:[/green] {args.delete_session}")
        else:
            console.print(f"[red]Session not found:[/red] {args.delete_session}")
        return

    if args.list_models:
        list_image_models()
        return

    if not args.prompt:
        parser.error("prompt is required unless using --list-models or --list-sessions")

    # Determine session name
    session_name = args.session
    if args.continue_latest:
        session_name = get_latest_session()
        if not session_name:
            console.print("[red]Error:[/red] No previous session to continue")
            sys.exit(1)

    saved_files = generate_image(
        prompt=args.prompt,
        model=args.model,
        aspect_ratio=args.aspect_ratio,
        image_size=args.size,
        output_file=args.output,
        reference_images=args.reference_images,
        session_name=session_name,
    )

    if saved_files:
        console.print(
            Panel(
                "\n".join(str(f) for f in saved_files),
                title=f"[green]Generated {len(saved_files)} image(s)[/green]",
                border_style="green",
            )
        )
    else:
        console.print("[red]No images were saved[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
