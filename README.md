# typedrat Claude Code Plugin Marketplace

A collection of Claude Code plugins.

## Installation

Add the marketplace to Claude Code:

```bash
/plugin marketplace add typedrat/claude-stuff
```

## Plugins

### openrouter-image-gen

Generate images using OpenRouter's image generation API with models like Gemini and FLUX.

**Install:**
```bash
/plugin install openrouter-image-gen@typedrat
```

**Usage:**
```bash
/generate-image "A sunset over mountains"
```

**Features:**
- Multiple aspect ratios (1:1, 16:9, 9:16, 4:3, etc.)
- Resolution options (1K, 2K, 4K for Gemini models)
- Model selection (Gemini, FLUX, and more)
- List available models with `--list-models`

**Configuration:**

Set your OpenRouter API key using one of these methods:

1. Environment variable:
   ```bash
   export OPENROUTER_API_KEY=your-key-here
   ```

2. Config file at one of:
   - `./.openrouter-config` (current directory)
   - `~/.config/openrouter/config`
   - `~/.openrouter-config`

Get your API key at: https://openrouter.ai/keys

## License

MIT
