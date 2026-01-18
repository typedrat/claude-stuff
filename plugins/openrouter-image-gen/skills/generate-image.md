# Generate Image

Generate images using OpenRouter's image generation API.

## Usage

When the user asks you to generate an image, create a picture, or make visual content, use this command.

## Instructions

1. Extract the image prompt from the user's request
2. Determine any optional parameters:
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

# List all available image generation models
${CLAUDE_PLUGIN_ROOT}/generate-image.py --list-models
```

## Discovering Models

Use `--list-models` to see all available image generation models with their pricing. This queries the OpenRouter API for models with image output capability.

## Output

Images are saved to `generated-images/` directory in the current working directory. After generation, inform the user of the saved file path(s).

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
