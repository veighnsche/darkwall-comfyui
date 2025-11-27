"""
ComfyUI HTTP API client.

Handles communication with ComfyUI: workflow submission, polling, and image download.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests

from ..config import Config


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
    
    def __init__(self, config: Config) -> None:
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
            if response.status_code == 200:
                self.logger.debug("ComfyUI health check passed")
                return True
            else:
                self.logger.warning(f"ComfyUI health check failed: HTTP {response.status_code}")
                return False
        except requests.ConnectionError as e:
            self.logger.debug(f"ComfyUI connection error: {e}")
            return False
        except requests.Timeout as e:
            self.logger.debug(f"ComfyUI health check timeout: {e}")
            return False
        except requests.RequestException as e:
            self.logger.debug(f"ComfyUI health check error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during health check: {e}")
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
            
            data = response.json()
            prompt_id = data.get('prompt_id')
            if not prompt_id:
                raise ComfyGenerationError("No prompt_id in response from ComfyUI")
            
            self.logger.debug(f"Workflow submitted successfully: {prompt_id}")
            return prompt_id
            
        except requests.ConnectionError as e:
            raise ComfyConnectionError(f"Cannot connect to ComfyUI at {self.base_url}: {e}")
        except requests.Timeout as e:
            raise ComfyConnectionError(f"Connection to ComfyUI timed out: {e}")
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                raise ComfyGenerationError(f"Invalid workflow submitted to ComfyUI: {e.response.text}")
            elif e.response.status_code == 500:
                raise ComfyGenerationError(f"ComfyUI server error: {e.response.text}")
            else:
                raise ComfyClientError(f"HTTP error from ComfyUI: {e}")
        except requests.RequestException as e:
            raise ComfyClientError(f"Failed to submit workflow to ComfyUI: {e}")
        except json.JSONDecodeError as e:
            raise ComfyClientError(f"Invalid JSON response from ComfyUI: {e}")
        except Exception as e:
            raise ComfyClientError(f"Unexpected error submitting workflow: {e}")
    
    def _wait_for_result(self, prompt_id: str) -> dict[str, Any]:
        """Poll for generation completion."""
        start = time.time()
        
        self.logger.debug(f"Waiting for generation result: {prompt_id}")
        
        while time.time() - start < self.timeout:
            try:
                history = self._get_history(prompt_id)
                
                if history is None:
                    # History check failed, continue polling
                    time.sleep(self.poll_interval)
                    continue
                
                # Check if generation is complete
                if history:
                    # Find first image output
                    outputs = history.get('outputs', {})
                    if not outputs:
                        raise ComfyGenerationError(f"No outputs found for {prompt_id}")
                    
                    for node_id, output in outputs.items():
                        if not isinstance(output, dict):
                            continue
                            
                        images = output.get('images', [])
                        if not images:
                            continue
                            
                        image = images[0]
                        if not isinstance(image, dict):
                            continue
                            
                        filename = image.get('filename')
                        if not filename:
                            continue
                            
                        result = {
                            "filename": filename,
                            "subfolder": image.get('subfolder', ''),
                            "type": image.get('type', 'output')
                        }
                        
                        self.logger.debug(f"Generation complete: {prompt_id} -> {filename}")
                        return result
                    
                    # No images found in outputs
                    raise ComfyGenerationError(f"No images in output for {prompt_id}")
                
                # Generation still in progress
                time.sleep(self.poll_interval)
                
            except ComfyClientError:
                # Re-raise our own exceptions
                raise
            except Exception as e:
                self.logger.warning(f"Unexpected error while polling for {prompt_id}: {e}")
                time.sleep(self.poll_interval)
        
        # Timeout reached
        raise ComfyTimeoutError(f"Generation timed out after {self.timeout}s for prompt {prompt_id}")
    
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
            
        except requests.ConnectionError as e:
            self.logger.debug(f"Connection error getting history for {prompt_id}: {e}")
            return None
        except requests.Timeout as e:
            self.logger.debug(f"Timeout getting history for {prompt_id}: {e}")
            return None
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # Generation not found yet, normal during polling
                self.logger.debug(f"History not found for {prompt_id} (generation may not be started)")
                return None
            else:
                self.logger.warning(f"HTTP error getting history for {prompt_id}: {e}")
                return None
        except requests.RequestException as e:
            self.logger.debug(f"Request error getting history for {prompt_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON in history response for {prompt_id}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error getting history for {prompt_id}: {e}")
            return None
    
    def _download_image(self, filename: str, subfolder: str = "", type_: str = "output") -> bytes:
        """Download generated image."""
        params = {"filename": filename, "subfolder": subfolder, "type": type_}
        
        try:
            self.logger.debug(f"Downloading image: {filename} (subfolder={subfolder}, type={type_})")
            
            response = self.session.get(
                urljoin(self.base_url, '/view'),
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            # Validate that we got image data
            content = response.content
            if not content:
                raise ComfyClientError(f"Empty image data received for {filename}")
            
            if len(content) < 100:  # Sanity check - images should be larger than this
                raise ComfyClientError(f"Image data too small for {filename}: {len(content)} bytes")
            
            self.logger.debug(f"Downloaded {len(content)} bytes for {filename}")
            return content
            
        except requests.ConnectionError as e:
            raise ComfyConnectionError(f"Cannot connect to download image {filename}: {e}")
        except requests.Timeout as e:
            raise ComfyConnectionError(f"Download timeout for image {filename}: {e}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ComfyClientError(f"Image not found: {filename}")
            else:
                raise ComfyClientError(f"HTTP error downloading image {filename}: {e}")
        except requests.RequestException as e:
            raise ComfyClientError(f"Failed to download image {filename}: {e}")
        except Exception as e:
            raise ComfyClientError(f"Unexpected error downloading image {filename}: {e}")
