"""
ComfyUI HTTP API client.

This module handles communication with ComfyUI instances including
workflow submission, result polling, and image downloading.

ComfyUI API endpoints used:
- POST /prompt - Submit workflow for generation
- GET /history/{prompt_id} - Check generation status and results
- GET /view?filename={filename} - Download generated images

The client is designed to work with configurable base URLs and can be
extended with authentication headers as needed.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from urllib.parse import urljoin

import requests


@dataclass
class GenerationResult:
    """Result of a ComfyUI generation request."""
    prompt_id: str
    success: bool
    image_url: str
    filename: str
    metadata: Dict[str, Any]


class ComfyClient:
    """
    Client for communicating with ComfyUI HTTP API.
    
    This client handles the complete workflow:
    1. Loading workflow JSON from file
    2. Injecting generated prompts into workflow nodes
    3. Submitting workflow to ComfyUI
    4. Polling for completion
    5. Providing download URLs for results
    """
    
    def __init__(self, config):
        """Initialize client with configuration."""
        self.config = config
        self.base_url = config.comfyui_base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'darkwall-comfyui/0.1.0'
        })
        
        # Add custom headers if configured (for future auth support)
        if config.comfyui_headers:
            self.session.headers.update(config.comfyui_headers)
        
        self.logger = logging.getLogger(__name__)
    
    def load_workflow(self, workflow_path: Path) -> Dict[str, Any]:
        """
        Load ComfyUI workflow from JSON file.
        
        Args:
            workflow_path: Path to workflow JSON file in API format
            
        Returns:
            Parsed workflow dictionary
            
        Raises:
            FileNotFoundError: If workflow file doesn't exist
            json.JSONDecodeError: If workflow file is invalid JSON
        """
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
        
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        self.logger.debug(f"Loaded workflow from {workflow_path}")
        return workflow
    
    def inject_prompt(self, workflow: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        Inject generated prompt into workflow nodes.
        
        This method looks for nodes that typically contain text prompts
        (like KSampler, CLIPTextEncode, etc.) and injects our generated prompt.
        
        Args:
            workflow: ComfyUI workflow dictionary
            prompt: Generated prompt string
            
        Returns:
            Workflow with prompt injected
        """
        workflow_copy = json.loads(json.dumps(workflow))  # Deep copy
        
        # Find nodes that typically contain prompts
        prompt_nodes = []
        
        for node_id, node in workflow_copy.items():
            if isinstance(node, dict):
                # Look for common prompt input patterns
                inputs = node.get('inputs', {})
                if 'text' in inputs or 'prompt' in inputs:
                    prompt_nodes.append((node_id, node))
                elif any('clip' in key.lower() for key in inputs.keys()):
                    prompt_nodes.append((node_id, node))
        
        if not prompt_nodes:
            self.logger.warning("No prompt nodes found in workflow")
            return workflow_copy
        
        # Inject prompt into the first suitable node found
        node_id, node = prompt_nodes[0]
        inputs = node['inputs']
        
        # Choose the appropriate input field
        if 'text' in inputs:
            inputs['text'] = prompt
            self.logger.debug(f"Injected prompt into node {node_id} field 'text'")
        elif 'prompt' in inputs:
            inputs['prompt'] = prompt
            self.logger.debug(f"Injected prompt into node {node_id} field 'prompt'")
        else:
            # Fallback: try to find any string input
            for key, value in inputs.items():
                if isinstance(value, str):
                    inputs[key] = prompt
                    self.logger.debug(f"Injected prompt into node {node_id} field '{key}'")
                    break
        
        return workflow_copy
    
    def submit_workflow(self, workflow: Dict[str, Any]) -> str:
        """
        Submit workflow to ComfyUI for generation.
        
        Args:
            workflow: Workflow dictionary with prompt injected
            
        Returns:
            Prompt ID for tracking the generation
            
        Raises:
            requests.RequestException: If API call fails
        """
        endpoint = urljoin(self.base_url, '/prompt')
        
        payload = {
            'prompt': workflow
        }
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            prompt_id = result.get('prompt_id')
            
            if not prompt_id:
                raise ValueError("No prompt_id returned from ComfyUI")
            
            return prompt_id
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to submit workflow: {e}")
            raise
    
    def check_generation_status(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Check generation status for a given prompt ID.
        
        Args:
            prompt_id: Prompt ID to check
            
        Returns:
            Generation history if complete, None if still processing
        """
        endpoint = urljoin(self.base_url, f'/history/{prompt_id}')
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            
            history = response.json()
            
            if prompt_id in history:
                return history[prompt_id]
            else:
                return None
                
        except requests.RequestException as e:
            self.logger.warning(f"Failed to check status for {prompt_id}: {e}")
            return None
    
    def wait_for_result(self, prompt_id: str) -> Optional[GenerationResult]:
        """
        Wait for generation to complete and return result.
        
        Args:
            prompt_id: Prompt ID to wait for
            
        Returns:
            GenerationResult if successful, None if failed/timeout
        """
        start_time = time.time()
        poll_interval = self.config.poll_interval
        timeout = self.config.generation_timeout
        
        self.logger.info(f"Waiting for generation {prompt_id} (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            history = self.check_generation_status(prompt_id)
            
            if history:
                # Generation complete
                outputs = history.get('outputs', {})
                
                # Find the first image output
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        images = node_output['images']
                        if images:
                            first_image = images[0]
                            filename = first_image['filename']
                            
                            # Construct download URL
                            image_url = urljoin(self.base_url, f'/view?filename={filename}')
                            
                            return GenerationResult(
                                prompt_id=prompt_id,
                                success=True,
                                image_url=image_url,
                                filename=filename,
                                metadata=history
                            )
                
                # No images found in outputs
                self.logger.error(f"No images found in generation result for {prompt_id}")
                return None
            
            # Still processing, wait and poll again
            time.sleep(poll_interval)
        
        # Timeout reached
        self.logger.error(f"Generation timeout for {prompt_id}")
        return None
    
    def download_image(self, image_url: str, output_path: Path) -> bool:
        """
        Download image from ComfyUI to local path.
        
        Args:
            image_url: URL to download from
            output_path: Local path to save image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.debug(f"Downloaded image to {output_path}")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to download image from {image_url}: {e}")
            return False
