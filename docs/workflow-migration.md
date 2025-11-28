# Workflow Migration Guide

Guide for updating ComfyUI workflows to use the new placeholder-based prompt injection system.

## Overview

DarkWall ComfyUI has moved from heuristic-based prompt injection to a deterministic placeholder system. This change ensures reliable prompt injection and gives users precise control over where prompts are placed in their workflows.

## Why This Change Was Needed

### Old System (Heuristic - Deprecated)
The old system tried to guess prompt fields by:
- Looking for field names like 'text', 'prompt', 'positive'
- Checking if existing text contained 'negative' to avoid injecting positive prompts
- This was fragile and failed with custom workflows

### New System (Placeholder-Based)
The new system uses exact placeholders:
- `__POSITIVE_PROMPT__` - Replaced with the generated positive prompt
- `__NEGATIVE_PROMPT__` - Replaced with the generated negative prompt (if provided)
- Deterministic: No guessing, exact replacement
- User control: You decide exactly where prompts go

## Migration Steps

### Step 1: Export Your Workflow

1. Open your workflow in ComfyUI
2. Make sure it works correctly with a test prompt
3. Export the workflow as JSON

### Step 2: Identify Prompt Nodes

Look for nodes that contain text prompts, typically:
- `CLIPTextEncode` nodes
- Nodes with 'text' inputs containing your prompt text
- Positive and negative prompt nodes

Example workflow snippet:
```json
{
  "75:6": {
    "inputs": {
      "text": "a beautiful landscape with mountains",
      "clip": ["75:38", 0]
    },
    "class_type": "CLIPTextEncode"
  },
  "75:7": {
    "inputs": {
      "text": "blurry, low quality, distorted",
      "clip": ["75:38", 0]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

### Step 3: Replace with Placeholders

Replace the actual prompt text with placeholders:

```json
{
  "75:6": {
    "inputs": {
      "text": "__POSITIVE_PROMPT__",  // ← Replace positive prompt
      "clip": ["75:38", 0]
    },
    "class_type": "CLIPTextEncode"
  },
  "75:7": {
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",  // ← Replace negative prompt
      "clip": ["75:38", 0]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

### Step 4: Save Updated Workflow

Save the modified workflow with a clear name, like:
- `my_workflow_placeholders.json`
- `portrait_darkwall.json`

### Step 5: Test the Updated Workflow

```bash
# Test with dry-run to see validation warnings
darkwall --dry-run generate --workflow my_workflow_placeholders.json

# Should show: "Workflow uses placeholder-based prompt injection (recommended)"

# Generate actual wallpaper
darkwall generate --workflow my_workflow_placeholders.json
```

## Detailed Examples

### Example 1: Simple Single Prompt

**Before (Heuristic):**
```json
{
  "1": {
    "inputs": {
      "text": "a majestic dragon perched on a mountain peak",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

**After (Placeholder):**
```json
{
  "1": {
    "inputs": {
      "text": "__POSITIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

### Example 2: Positive and Negative Prompts

**Before (Heuristic):**
```json
{
  "positive": {
    "inputs": {
      "text": "cinematic lighting, highly detailed, 8k resolution",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "negative": {
    "inputs": {
      "text": "blurry, low quality, artifacts, distorted",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

**After (Placeholder):**
```json
{
  "positive": {
    "inputs": {
      "text": "__POSITIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "negative": {
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

### Example 3: Complex Workflow with Multiple Text Fields

**Before (Heuristic):**
```json
{
  "main_prompt": {
    "inputs": {
      "text": "abstract geometric patterns",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "style_prompt": {
    "inputs": {
      "text": "modern, minimalist, clean lines",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "negative": {
    "inputs": {
      "text": "cluttered, busy, noisy",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

**After (Placeholder):**
```json
{
  "main_prompt": {
    "inputs": {
      "text": "__POSITIVE_PROMPT__",  // Main generation prompt
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "style_prompt": {
    "inputs": {
      "text": "modern, minimalist, clean lines",  // Keep fixed style text
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "negative": {
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",  // Negative prompt
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

## Common Migration Issues

### Issue 1: Multiple Prompt Nodes

**Problem**: Workflow has multiple text nodes and you're not sure which to replace.

**Solution**: 
1. Test the workflow in ComfyUI to see which text node affects the output
2. Replace only the main prompt node with `__POSITIVE_PROMPT__`
3. Keep other text nodes with fixed text if they're for styling

### Issue 2: No Negative Prompt Support

**Problem**: Your workflow doesn't have a negative prompt node.

**Solution**: 
1. Add a new `CLIPTextEncode` node for negative prompts
2. Connect it to the same CLIP model as your positive prompt
3. Set its text to `__NEGATIVE_PROMPT__`
4. Connect it to the KSampler's negative input

**Example addition:**
```json
{
  "negative_node": {
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",
      "clip": ["4", 1]  // Same CLIP as positive
    },
    "class_type": "CLIPTextEncode"
  },
  "ksampler": {
    "inputs": {
      "positive": ["positive_node", 0],
      "negative": ["negative_node", 0],  // Connect negative here
      // ... other inputs
    },
    "class_type": "KSampler"
  }
}
```

### Issue 3: Workflow Still Uses Heuristics

**Problem**: After migration, you still see "Using deprecated heuristic injection" warnings.

**Solution**: 
1. Check that placeholders are exactly `__POSITIVE_PROMPT__` and `__NEGATIVE_PROMPT__`
2. Ensure no extra spaces or typos
3. Verify the workflow file is being loaded correctly

## Validation and Testing

### Check Migration Success

```bash
# Test workflow validation
darkwall --dry-run generate --workflow your_workflow.json

# Look for these messages:
# ✅ "Workflow uses placeholder-based prompt injection (recommended)"
# ❌ "WARNING: Using deprecated heuristic prompt injection"
```

### Test Prompt Generation

```bash
# Preview prompts without generation
darkwall prompt preview --workflow your_workflow.json

# Generate actual wallpaper
darkwall generate --workflow your_workflow.json
```

## Backwards Compatibility

The system maintains backwards compatibility:
- Workflows without placeholders will still work (with warnings)
- Heuristic injection is deprecated but functional
- Migration is optional but recommended

**Timeline:**
- Current version: Placeholders recommended, heuristics supported with warnings
- Next major version: Heuristics removed, placeholders required

## Troubleshooting

### "No prompt placeholders found" Warning

**Cause**: Workflow doesn't contain `__POSITIVE_PROMPT__` placeholder.

**Solution**: Add the placeholder to your main text node or migrate the workflow.

### "Workflow contains __POSITIVE_PROMPT__ placeholder but injection failed"

**Cause**: Placeholder found but injection failed for some reason.

**Solution**: 
1. Check workflow structure is valid JSON
2. Verify placeholder is in a text input field
3. Check logs for detailed error information

### Generation Still Uses Old Prompts

**Cause**: Using cached workflow or wrong file.

**Solution**: 
1. Verify you're using the updated workflow file
2. Check configuration file workflow paths
3. Use `--workflow` flag to specify exact file

## Template Workflows

Use these as starting points for your own workflows:

### Basic Portrait Workflow
```json
{
  "positive": {
    "inputs": {
      "text": "__POSITIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "negative": {
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

### Landscape Workflow
```json
{
  "landscape_prompt": {
    "inputs": {
      "text": "__POSITIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "quality_negative": {
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

## Getting Help

If you need help with migration:

1. **Check logs**: Use `--verbose` flag for detailed information
2. **Validate workflow**: Use `darkwall --dry-run generate` to check placeholders
3. **Test incrementally**: Start with a simple workflow, then add complexity
4. **Reference examples**: Look at the template workflows in the documentation

## Summary

The placeholder-based system provides:
- ✅ Deterministic prompt injection
- ✅ User control over prompt placement
- ✅ Support for multiple prompt nodes
- ✅ Better error messages and validation
- ✅ Future-proof workflow design

Migration is straightforward and provides immediate benefits in reliability and control.
