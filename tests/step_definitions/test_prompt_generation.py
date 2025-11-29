"""
Step definitions for prompt generation CLI feature.

TEAM_006: BDD tests for `darkwall prompt generate` command.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from io import StringIO

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load scenarios from feature file
scenarios('../features/prompt_generation.feature')


@pytest.fixture
def context():
    """Shared context for test steps."""
    return {
        "config_dir": None,
        "outputs": [],
        "exit_codes": [],
        "last_output": None,
        "last_exit_code": None,
    }


@pytest.fixture
def setup_test_config(tmp_path, monkeypatch):
    """Set up a test config directory with themes."""
    config_dir = tmp_path / "darkwall-comfyui"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Set XDG_CONFIG_HOME so the CLI uses our test directory
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    
    return config_dir


def create_theme_structure(config_dir: Path, theme: str, prompts: list):
    """Create theme directory structure with atoms and prompts."""
    theme_dir = config_dir / "themes" / theme
    atoms_dir = theme_dir / "atoms"
    prompts_dir = theme_dir / "prompts"
    
    atoms_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    
    # Create atom files
    atoms = {
        "subject": "mountain landscape\nocean sunset\nforest path\ncity skyline\n",
        "environment": "misty morning\nstormy weather\nclear sky\nfoggy atmosphere\n",
        "lighting": "golden hour\nblue hour\nmoonlight\nneon glow\n",
        "style": "cinematic\nphotorealistic\ndigital art\noil painting\n",
        "mood": "serene\ndramatic\nmysterious\nenergetic\n",
        "colors": "warm tones\ncool blues\nmonochrome\nvibrant neon\n",
        "composition": "wide angle\nclose up\naerial view\nlow angle\n",
    }
    
    for atom_name, content in atoms.items():
        (atoms_dir / f"{atom_name}.txt").write_text(content)
    
    # Create prompt files
    for prompt_name in prompts:
        if prompt_name == "default":
            content = "__subject__, __environment__, __lighting__, __style__, __mood__, __colors__, __composition__\n---negative---\nblurry, low quality, watermark\n"
        elif prompt_name == "cyberpunk":
            content = "cyberpunk __subject__, neon __lighting__, __environment__, futuristic __style__\n---negative---\nnature, daylight, blurry\n"
        elif prompt_name == "noir":
            content = "film noir __subject__, dramatic __lighting__, __mood__, black and white\n---negative---\ncolorful, bright, cheerful\n"
        elif prompt_name == "landscape":
            content = "beautiful __subject__ landscape, __environment__, __lighting__, nature photography\n---negative---\nurban, people, blurry\n"
        elif prompt_name == "nature":
            content = "nature __subject__, __environment__, __lighting__, wildlife photography\n---negative---\ncity, buildings, blurry\n"
        else:
            content = f"__subject__, {prompt_name} style\n---negative---\nblurry\n"
        
        (prompts_dir / f"{prompt_name}.prompt").write_text(content)


def run_prompt_command(config_dir: Path, args: str) -> tuple:
    """
    Run the prompt generate command and capture output.
    
    Returns (exit_code, output).
    """
    # Import and run via Python to avoid subprocess issues in tests
    import sys
    from io import StringIO
    from unittest.mock import patch
    
    # Build argv
    argv = ["darkwall", "prompt"] + args.split()
    
    # Capture stdout
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_out = StringIO()
    captured_err = StringIO()
    
    exit_code = 0
    
    try:
        sys.stdout = captured_out
        sys.stderr = captured_err
        
        # Import CLI after setting up environment
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        
        # Clear cached modules to pick up new config
        modules_to_clear = [k for k in sys.modules.keys() if k.startswith('darkwall_comfyui')]
        for mod in modules_to_clear:
            del sys.modules[mod]
        
        from darkwall_comfyui.cli import main
        
        with patch.object(sys, 'argv', argv):
            try:
                result = main()
                exit_code = result if result is not None else 0
            except SystemExit as e:
                exit_code = e.code if e.code is not None else 0
    except Exception as e:
        captured_err.write(str(e))
        exit_code = 1
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    output = captured_out.getvalue() + captured_err.getvalue()
    return exit_code, output


# ============================================================================
# Given steps
# ============================================================================

@given(parsers.parse('a config directory with themes "{theme1}" and "{theme2}"'))
def config_with_themes(setup_test_config, context, theme1, theme2):
    """Set up config directory with specified themes."""
    context["config_dir"] = setup_test_config
    context["themes"] = [theme1, theme2]


@given(parsers.parse('theme "{theme}" has prompts "{prompts_str}"'))
def theme_has_prompts(context, theme, prompts_str):
    """Create prompts for a theme."""
    prompts = [p.strip().strip('"') for p in prompts_str.split(",")]
    create_theme_structure(context["config_dir"], theme, prompts)


# ============================================================================
# When steps
# ============================================================================

@when(parsers.parse('I run "{command}"'))
def run_command(context, command):
    """Run a prompt generate command."""
    # Extract args after "prompt "
    if command.startswith("prompt "):
        args = command[7:]  # Remove "prompt "
    else:
        args = command
    
    exit_code, output = run_prompt_command(context["config_dir"], args)
    
    context["last_exit_code"] = exit_code
    context["last_output"] = output
    context["outputs"].append(output)
    context["exit_codes"].append(exit_code)


@when(parsers.parse('I run "{command}" again'))
def run_command_again(context, command):
    """Run the same command again."""
    run_command(context, command)


@when('I run "prompt generate" without theme flag')
def run_without_theme(context):
    """Run prompt generate without specifying theme."""
    # Create a "default" theme since that's what PromptConfig defaults to
    # when no config is loaded (theme="default" is the default)
    create_theme_structure(context["config_dir"], "default", ["default"])
    
    exit_code, output = run_prompt_command(context["config_dir"], "generate")
    context["last_exit_code"] = exit_code
    context["last_output"] = output
    context["outputs"].append(output)
    context["exit_codes"].append(exit_code)


# ============================================================================
# Then steps
# ============================================================================

@then("the exit code should be 0")
def exit_code_zero(context):
    """Verify exit code is 0."""
    assert context["last_exit_code"] == 0, f"Expected exit code 0, got {context['last_exit_code']}\nOutput: {context['last_output']}"


@then("the exit code should be non-zero")
def exit_code_nonzero(context):
    """Verify exit code is non-zero."""
    assert context["last_exit_code"] != 0, f"Expected non-zero exit code, got {context['last_exit_code']}"


@then(parsers.parse('the output should contain "{text}"'))
def output_contains(context, text):
    """Verify output contains text."""
    assert text in context["last_output"], f"Expected '{text}' in output:\n{context['last_output']}"


@then(parsers.parse('the output should not contain "{text}"'))
def output_not_contains(context, text):
    """Verify output does not contain text."""
    assert text not in context["last_output"], f"Did not expect '{text}' in output:\n{context['last_output']}"


@then("both outputs should be identical")
def outputs_identical(context):
    """Verify last two outputs are identical."""
    assert len(context["outputs"]) >= 2, "Need at least 2 outputs to compare"
    
    # Extract just the prompt parts (ignore metadata like seed display time)
    def extract_prompts(output):
        lines = output.split('\n')
        prompt_lines = []
        in_prompt = False
        for line in lines:
            if "POSITIVE PROMPT" in line or "NEGATIVE PROMPT" in line:
                in_prompt = True
                continue
            if "===" in line or "---" in line:
                in_prompt = False
                continue
            if in_prompt and line.strip():
                prompt_lines.append(line.strip())
        return '\n'.join(prompt_lines)
    
    out1 = extract_prompts(context["outputs"][-2])
    out2 = extract_prompts(context["outputs"][-1])
    
    assert out1 == out2, f"Outputs differ:\n--- First ---\n{out1}\n--- Second ---\n{out2}"


@then("the outputs should be different")
def outputs_different(context):
    """Verify last two outputs are different."""
    assert len(context["outputs"]) >= 2, "Need at least 2 outputs to compare"
    
    # Just compare the full outputs - different seeds should give different prompts
    out1 = context["outputs"][-2]
    out2 = context["outputs"][-1]
    
    assert out1 != out2, "Expected outputs to be different but they are identical"


@then("a prompt should be generated")
def prompt_generated(context):
    """Verify a prompt was generated."""
    output = context["last_output"]
    # Should have either formatted output or raw output
    has_prompt = (
        "POSITIVE PROMPT" in output or 
        "---" in output or
        len(output.strip()) > 20  # Raw output with content
    )
    assert has_prompt, f"No prompt generated in output:\n{output}"


@then("a warning should be shown")
def warning_shown(context):
    """Verify a warning is in output."""
    output = context["last_output"].lower()
    has_warning = "warning" in output or "error" in output or "not found" in output
    assert has_warning, f"Expected warning in output:\n{context['last_output']}"


@then("Or a warning should be shown")
def or_warning_shown(context):
    """Alternative: warning is shown (for invalid theme scenario)."""
    # This is used with "the exit code should be non-zero OR a warning should be shown"
    # If we get here, check if there's a warning
    output = context["last_output"].lower()
    if context["last_exit_code"] == 0:
        has_warning = "warning" in output or "not found" in output or "fallback" in output
        assert has_warning, f"Expected either non-zero exit or warning in output:\n{context['last_output']}"


@when(parsers.parse('I request help for "{command}"'))
def request_help(context, command):
    """Request help for a command."""
    exit_code, output = run_prompt_command(context["config_dir"], f"{command.replace('prompt ', '')} --help")
    context["last_exit_code"] = exit_code
    context["last_output"] = output


@then(parsers.parse('the help should mention "{text}"'))
def help_mentions(context, text):
    """Verify help output mentions text."""
    assert text.lower() in context["last_output"].lower(), f"Expected '{text}' in help:\n{context['last_output']}"
