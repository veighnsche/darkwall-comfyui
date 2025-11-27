"""
ComfyUI HTTP API client.

Handles communication with ComfyUI: workflow submission, polling, and image download.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests


@dataclass
class GenerationResult:
    """Result of a successful ComfyUI generation."""
    prompt_id: str
    filename: str
    image_data: bytes


class ComfyClientError(Exception):
    """Base exception for ComfyUI client errors."""
    pass


class ComfyConnectionError(ComfyClientError):
    """Failed to connect to ComfyUI."""
    pass


class ComfyTimeoutError(ComfyClientError):
    """Generation timed out."""
    pass


class ComfyGenerationError(ComfyClientError):
    """Generation failed."""
    pass


class ComfyClient:
    """
    Client for ComfyUI HTTP API.
    
    Usage:
        client = ComfyClient(config)
        result = client.generate(workflow_dict, prompt_text)
        # result.image_data contains the generated image bytes
    """
    
    def __init__(self, config):
        self.config = config
        self.base_url = config.comfyui.base_url.rstrip('/')
        self.timeout = config.comfyui.timeout
        self.poll_interval = config.comfyui.poll_interval
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'darkwall-comfyui/0.1.0'
        })
        if config.comfyui.headers:
            self.session.headers.update(config.comfyui.headers)
        
        self.logger = logging.getLogger(__name__)
    
    def generate(self, workflow: dict[str, Any], prompt: str) -> GenerationResult:
        """
        Run a complete generation: inject prompt, submit, wait, download.
        
        Args:
            workflow: ComfyUI workflow dict (API format)
            prompt: Text prompt to inject
            
        Returns:
            GenerationResult with image data
            
        Raises:
            ComfyClientError: On any failure
        """
        # Inject prompt into workflow
        workflow = self._inject_prompt(workflow, prompt)
        
        # Submit workflow
        prompt_id = self._submit(workflow)
        self.logger.info(f"Submitted workflow: {prompt_id}")
        
        # Wait for completion
        result = self._wait_for_result(prompt_id)
        
        # Download image
        image_data = self._download_image(result["filename"])
        
        return GenerationResult(
            prompt_id=prompt_id,
            filename=result["filename"],
            image_data=image_data
        )
    
    def health_check(self) -> bool:
        """Check if ComfyUI is reachable."""
        try:
            response = self.session.get(
                urljoin(self.base_url, '/system_stats'),
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def _inject_prompt(self, workflow: dict[str, Any], prompt: str) -> dict[str, Any]:
        """Inject prompt into workflow nodes."""
        import json
        workflow = json.loads(json.dumps(workflow))  # Deep copy
        
        injected = False
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            
            inputs = node.get('inputs', {})
            
            # Try common prompt field names
            for field in ['text', 'prompt', 'positive']:
                if field in inputs and isinstance(inputs[field], str):
                    inputs[field] = prompt
                    self.logger.debug(f"Injected prompt into node {node_id}.{field}")
                    injected = True
                    break
        
        if not injected:
            self.logger.warning("No prompt field found in workflow")
        
        return workflow
    
    def _submit(self, workflow: dict[str, Any]) -> str:
        """Submit workflow and return prompt_id."""
        try:
            response = self.session.post(
                urljoin(self.base_url, '/prompt'),
                json={'prompt': workflow},
                timeout=30
            )
            response.raise_for_status()
            
            prompt_id = response.json().get('prompt_id')
            if not prompt_id:
                raise ComfyGenerationError("No prompt_id in response")
            
            return prompt_id
            
        except requests.ConnectionError as e:
            raise ComfyConnectionError(f"Cannot connect to ComfyUI at {self.base_url}: {e}")
        except requests.RequestException as e:
            raise ComfyClientError(f"Failed to submit workflow: {e}")
    
    def _wait_for_result(self, prompt_id: str) -> dict[str, Any]:
        """Poll for generation completion."""
        start = time.time()
        
        while time.time() - start < self.timeout:
            history = self._get_history(prompt_id)
            
            if history:
                # Find first image output
                for node_id, output in history.get('outputs', {}).items():
                    if 'images' in output and output['images']:
                        image = output['images'][0]
                        return {
                            "filename": image['filename'],
                            "subfolder": image.get('subfolder', ''),
                            "type": image.get('type', 'output')
                        }
                
                raise ComfyGenerationError(f"No images in output for {prompt_id}")
            
            time.sleep(self.poll_interval)
        
        raise ComfyTimeoutError(f"Generation timed out after {self.timeout}s")
    
    def _get_history(self, prompt_id: str) -> Optional[dict[str, Any]]:
        """Get generation history for prompt_id."""
        try:
            response = self.session.get(
                urljoin(self.base_url, f'/history/{prompt_id}'),
                timeout=10
            )
            response.raise_for_status()
            
            history = response.json()
            return history.get(prompt_id)
            
        except requests.RequestException as e:
            self.logger.debug(f"History check failed: {e}")
            return None
    
    def _download_image(self, filename: str, subfolder: str = "", type_: str = "output") -> bytes:
        """Download generated image."""
        params = {"filename": filename, "subfolder": subfolder, "type": type_}
        
        try:
            response = self.session.get(
                urljoin(self.base_url, '/view'),
                params=params,
                timeout=60
            )
            response.raise_for_status()
            return response.content
            
        except requests.RequestException as e:
            raise ComfyClientError(f"Failed to download image: {e}")
