# Generate Image

Generate images using OpenRouter's image generation API.

## Usage

When the user asks you to generate an image, create a picture, or make visual content, use this command.

## Instructions

1. Extract the image prompt from the user's request
2. Determine any optional parameters:
   - **Reference images**: One or more images to use as style/content guidance
   - **Aspect ratio**: 1:1, 16:9, 9:16, 4:3, 3:4, etc.
   - **Image size**: 1K, 2K, or 4K (Gemini models only)
   - **Output filename**: Custom name or auto-generated
   - **Model**: Override the default model

3. Run the generation script:

```bash
${CLAUDE_PLUGIN_ROOT}/generate-image.py [OPTIONS] "prompt"
```

The script uses uv for dependency management - dependencies install automatically on first run.

## Options

- `-l, --list-models` - List all available image generation models with pricing
- `-o, --output FILE` - Custom output filename
- `-a, --aspect-ratio RATIO` - Aspect ratio (1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
- `-s, --size SIZE` - Image resolution: 1K, 2K, or 4K (Gemini models only)
- `-m, --model MODEL` - Override the model (default: google/gemini-2.0-flash-exp:free)
- `-r, --reference IMAGE` - Reference image for style/content guidance (can be used multiple times)
- `--session NAME` - Create or continue a named session for iterative refinement
- `--continue` - Continue the most recent session
- `--list-sessions` - List all available sessions
- `--delete-session NAME` - Delete a session and all its files

## Examples

```bash
# Simple generation
${CLAUDE_PLUGIN_ROOT}/generate-image.py "A serene mountain landscape at sunset"

# With aspect ratio and filename
${CLAUDE_PLUGIN_ROOT}/generate-image.py -a 16:9 -o sunset.png "Golden sunset over calm ocean"

# High resolution square image
${CLAUDE_PLUGIN_ROOT}/generate-image.py -a 1:1 -s 4K "Detailed portrait of a robot"

# Using a different model
${CLAUDE_PLUGIN_ROOT}/generate-image.py -m "black-forest-labs/flux-1.1-pro" "Abstract art"

# With reference image(s) for style guidance
${CLAUDE_PLUGIN_ROOT}/generate-image.py -r style_reference.png "A castle in this artistic style"

# Multiple reference images
${CLAUDE_PLUGIN_ROOT}/generate-image.py -r style1.png -r style2.png "Combine these styles into a landscape"

# List all available image generation models
${CLAUDE_PLUGIN_ROOT}/generate-image.py --list-models

# Start a session for iterative refinement
${CLAUDE_PLUGIN_ROOT}/generate-image.py --session my-cover -a 2:3 "VHS cover for a horror game"

# Continue refining in the same session (automatically includes previous image)
${CLAUDE_PLUGIN_ROOT}/generate-image.py --session my-cover "Make the title text larger and move it to the bottom"

# Continue the most recent session without specifying the name
${CLAUDE_PLUGIN_ROOT}/generate-image.py --continue "Add more film grain texture"

# List all sessions
${CLAUDE_PLUGIN_ROOT}/generate-image.py --list-sessions

# Delete a session when done
${CLAUDE_PLUGIN_ROOT}/generate-image.py --delete-session my-cover
```

## Sessions

Sessions allow you to have a conversation with the image generation model to iteratively refine your images. When you use `--session NAME`:

1. A new session is created (or continued if it exists)
2. Your prompt and the generated image are saved
3. On subsequent calls, the previous image is automatically uploaded so the model can see and refine it
4. All generated images are copied to the session folder for reference

Session state is stored in `$XDG_STATE_HOME/openrouter-image-gen/sessions/` (defaults to `~/.local/state/openrouter-image-gen/sessions/`).

## Discovering Models

Use `--list-models` to see all available image generation models with their pricing. This queries the OpenRouter API for models with image output capability.

## Output

Images are saved to `$XDG_STATE_HOME/openrouter-image-gen/output/` (defaults to `~/.local/state/openrouter-image-gen/output/`). The script outputs the full paths to generated images. Use the Read tool to view them, then copy to the appropriate location when finalized.

## Setup Required

The script needs an OpenRouter API key. Configure it using one of these methods (checked in order):

1. **Environment variable** (recommended):
   ```bash
   export OPENROUTER_API_KEY=your-key-here
   ```

2. **Config file** at one of these locations (checked in order):
   - `./.openrouter-config` (current directory)
   - `~/.config/openrouter/config`
   - `~/.openrouter-config`

   Config file format:
   ```
   OPENROUTER_API_KEY=your-key-here
   ```

Get your API key at: https://openrouter.ai/keys
