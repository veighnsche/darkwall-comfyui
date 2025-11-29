"""
ComfyUI HTTP API client.

Handles communication with ComfyUI: workflow submission, polling, and image download.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Callable
from urllib.parse import urljoin, urlparse, urlunparse, urlencode
import uuid

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import websocket

from ..config import Config, ComfyUIConfig
from ..exceptions import (
    WorkflowError,
    ComfyClientError,
    ComfyConnectionError,
    ComfyTimeoutError,
    ComfyGenerationError,
)
from ..prompt_generator import PromptResult


@dataclass
class GenerationResult:
    """Result of a successful ComfyUI generation."""
    prompt_id: str
    filename: str
    image_data: bytes


class ComfyClient:
    """
    Client for ComfyUI HTTP API.
    
    Usage:
        client = ComfyClient(config)
        result = client.generate(workflow_dict, prompt_text)
        # result.image_data contains the generated image bytes
    """
    
    def __init__(self, comfyui_config: ComfyUIConfig) -> None:
        self.config = comfyui_config
        self.base_url = comfyui_config.base_url.rstrip('/')
        self.timeout = comfyui_config.timeout
        self.poll_interval = comfyui_config.poll_interval
        self.client_id = str(uuid.uuid4())
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=3,  # Maximum number of retries
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors
            allowed_methods=["HEAD", "GET", "POST"],  # Methods to retry
            backoff_factor=2,  # Exponential backoff: 2s, 4s, 8s
            raise_on_status=False,  # Don't raise on retry status
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,      # Maximum number of connections in each pool
            pool_block=False      # Don't block when pool is full
        )
        
        # Create session with optimized configuration
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'darkwall-comfyui/0.1.0'
        })
        if comfyui_config.headers:
            self.session.headers.update(comfyui_config.headers)
        
        self.logger = logging.getLogger(__name__)
        self.logger.debug("ComfyUI client initialized with retry logic and connection pooling")
    
    def generate(
        self,
        workflow: dict[str, Any],
        prompt: str | PromptResult,
        on_event: Optional[Callable[[Any], None]] = None,
    ) -> GenerationResult:
        """
        Run a complete generation: inject prompt, submit, wait, download.
        
        Args:
            workflow: ComfyUI workflow dict (API format)
            prompt: Text prompt to inject (str) or PromptResult with positive/negative
            
        Returns:
            GenerationResult with image data
            
        Raises:
            ComfyClientError: On any failure
        """
        # Inject prompt(s) into workflow
        if isinstance(prompt, PromptResult):
            workflow = self._inject_prompts(workflow, prompt)
            # If the prompt generator provided a deterministic seed, inject it into
            # any Seed (rgthree) nodes so ComfyUI doesn't auto-generate a seed
            # and complain about "-1" seeds coming from the API.
            if getattr(prompt, "seed", None) is not None:
                workflow = self._inject_seed(workflow, prompt.seed)
        else:
            workflow = self._inject_prompt(workflow, prompt)
        
        # Submit workflow
        prompt_id = self._submit(workflow)
        self.logger.info(f"Submitted workflow: {prompt_id}")
        
        # Wait for completion
        result = self._wait_for_result(prompt_id, on_event=on_event)
        
        # Download image
        image_data = self._download_image(result["filename"])
        
        return GenerationResult(
            prompt_id=prompt_id,
            filename=result["filename"],
            image_data=image_data
        )
    
    def health_check(self) -> bool:
        """
        Check if ComfyUI is reachable with retry logic.
        
        Returns:
            True if ComfyUI is reachable and healthy, False otherwise
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, '/system_stats'),
                timeout=10  # Increased timeout for health check
            )
            if response.status_code == 200:
                self.logger.debug("ComfyUI health check passed")
                return True
            else:
                self.logger.warning(f"ComfyUI health check failed: HTTP {response.status_code}")
                return False
        except requests.ConnectionError as e:
            self.logger.debug(f"ComfyUI connection error during health check: {e}")
            return False
        except requests.Timeout as e:
            self.logger.debug(f"ComfyUI health check timeout: {e}")
            return False
        except requests.RequestException as e:
            self.logger.debug(f"ComfyUI health check request error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during health check: {e}")
            return False
    
    def detailed_health_check(self) -> dict[str, Any]:
        """
        Perform detailed health check with system information.
        
        Returns:
            Dictionary with health status and system information
        """
        health_info = {
            'healthy': False,
            'url': self.base_url,
            'response_time_ms': None,
            'system_stats': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = self.session.get(
                urljoin(self.base_url, '/system_stats'),
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000
            
            health_info['response_time_ms'] = round(response_time, 2)
            
            if response.status_code == 200:
                health_info['healthy'] = True
                try:
                    health_info['system_stats'] = response.json()
                except json.JSONDecodeError:
                    self.logger.warning("ComfyUI returned invalid JSON in system_stats")
                    health_info['system_stats'] = {'raw_response': response.text}
                
                self.logger.debug(f"ComfyUI detailed health check passed in {response_time:.2f}ms")
            else:
                health_info['error'] = f"HTTP {response.status_code}"
                self.logger.warning(f"ComfyUI detailed health check failed: HTTP {response.status_code}")
                
        except requests.ConnectionError as e:
            health_info['error'] = f"Connection error: {e}"
            self.logger.debug(f"ComfyUI connection error during detailed health check: {e}")
        except requests.Timeout as e:
            health_info['error'] = f"Timeout error: {e}"
            self.logger.debug(f"ComfyUI timeout during detailed health check: {e}")
        except requests.RequestException as e:
            health_info['error'] = f"Request error: {e}"
            self.logger.debug(f"ComfyUI request error during detailed health check: {e}")
        except Exception as e:
            health_info['error'] = f"Unexpected error: {e}"
            self.logger.error(f"Unexpected error during detailed health check: {e}")
        
        return health_info
    
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
    
    def _inject_prompts(self, workflow: dict[str, Any], prompts: PromptResult) -> dict[str, Any]:
        """Inject both positive and negative prompts into workflow nodes using placeholders."""
        import json
        workflow = json.loads(json.dumps(workflow))  # Deep copy
        
        positive_injected = False
        negative_injected = False
        
        # Look for placeholder-based injection (REQUIRED)
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            
            inputs = node.get('inputs', {})
            
            # Check for placeholder-based injection
            for field, value in inputs.items():
                if isinstance(value, str):
                    if value == "__POSITIVE_PROMPT__":
                        inputs[field] = prompts.positive
                        self.logger.debug(f"Injected positive prompt into placeholder node {node_id}.{field}")
                        positive_injected = True
                    elif value == "__NEGATIVE_PROMPT__" and prompts.negative:
                        inputs[field] = prompts.negative
                        self.logger.debug(f"Injected negative prompt into placeholder node {node_id}.{field}")
                        negative_injected = True
        
        # Validate injection was successful
        if not positive_injected:
            raise WorkflowError(
                "Workflow missing __POSITIVE_PROMPT__ placeholder. "
                "Please update your workflow to use placeholder-based prompt injection. "
                "See docs/workflow-migration.md for migration guide."
            )
        
        if prompts.negative and not negative_injected:
            # Soft behavior: warn and continue with positive-only
            self.logger.warning(
                "Negative prompt provided but workflow missing __NEGATIVE_PROMPT__ placeholder; "
                "continuing with positive prompt only."
            )
        
        self.logger.info("Successfully injected prompts using placeholder-based system")
        return workflow

    def _inject_seed(self, workflow: dict[str, Any], seed: int) -> dict[str, Any]:
        """Inject deterministic seed into Seed (rgthree) nodes if present.

        This keeps ComfyUI from treating "-1" as a special value and emitting
        warnings while still allowing workflows without Seed (rgthree) nodes to
        behave unchanged.
        """
        import json
        workflow = json.loads(json.dumps(workflow))  # Deep copy

        seed_injected = False
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue

            if node.get("class_type") == "Seed (rgthree)":
                inputs = node.setdefault("inputs", {})
                inputs["seed"] = int(seed)
                self.logger.debug(f"Injected seed {seed} into Seed (rgthree) node {node_id}")
                seed_injected = True

        if not seed_injected:
            self.logger.debug(
                "No Seed (rgthree) node found for seed injection; workflow may manage seeds internally"
            )

        return workflow
    
    def _submit(self, workflow: dict[str, Any]) -> str:
        """Submit workflow and return prompt_id."""
        # Generate a prompt_id for this submission on the client side
        prompt_id = str(uuid.uuid4())

        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
            "prompt_id": prompt_id,
        }

        try:
            response = self.session.post(
                urljoin(self.base_url, '/prompt'),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            self.logger.debug(f"Workflow submitted successfully: {prompt_id}")
            return prompt_id

        except requests.ConnectionError as e:
            raise ComfyConnectionError(f"Cannot connect to ComfyUI at {self.base_url}: {e}")
        except requests.Timeout as e:
            raise ComfyConnectionError(f"Connection to ComfyUI timed out: {e}")
        except requests.HTTPError as e:
            status = getattr(e.response, 'status_code', None)
            text = getattr(e.response, 'text', '')
            if status == 400:
                raise ComfyGenerationError(f"Invalid workflow submitted to ComfyUI: {text}")
            elif status == 500:
                raise ComfyGenerationError(f"ComfyUI server error: {text}")
            else:
                raise ComfyClientError(f"HTTP error from ComfyUI: {e}")
        except requests.RequestException as e:
            raise ComfyClientError(f"Failed to submit workflow to ComfyUI: {e}")
        except Exception as e:
            raise ComfyClientError(f"Unexpected error submitting workflow: {e}")

    def _build_ws_url(self) -> str:
        parsed = urlparse(self.base_url)
        if parsed.scheme == 'https':
            ws_scheme = 'wss'
        else:
            ws_scheme = 'ws'

        netloc = parsed.netloc or parsed.path
        path = '/ws'
        query = urlencode({"clientId": self.client_id})
        return urlunparse((ws_scheme, netloc, path, "", query, ""))

    def _wait_for_result(
        self,
        prompt_id: str,
        on_event: Optional[Callable[[Any], None]] = None,
    ) -> dict[str, Any]:
        """Wait for generation completion via WebSocket and read history once.

        If on_event is provided, it will be called with each decoded WebSocket
        message (as a dict) before internal handling, allowing higher-level
        UIs or loggers to react to queue/progress events.
        """
        start = time.time()
        ws_url = self._build_ws_url()

        self.logger.debug(
            f"Waiting for generation result via WebSocket: prompt_id={prompt_id} client_id={self.client_id}"
        )

        try:
            ws = websocket.create_connection(ws_url, timeout=self.poll_interval)
        except websocket.WebSocketException as e:
            raise ComfyConnectionError(f"Failed to open WebSocket to ComfyUI at {ws_url}: {e}")

        try:
            ws.settimeout(self.poll_interval)
            while time.time() - start < self.timeout:
                try:
                    message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    # Check overall timeout in loop condition
                    continue
                except websocket.WebSocketConnectionClosedException as e:
                    raise ComfyClientError(f"WebSocket closed while waiting for {prompt_id}: {e}")

                if isinstance(message, bytes):
                    # Binary previews; ignore for now.
                    continue

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    self.logger.debug(f"Non-JSON WebSocket message: {message!r}")
                    if on_event is not None:
                        try:
                            on_event(message)
                        except Exception as cb_err:
                            self.logger.warning(f"on_event callback raised: {cb_err}")
                    continue

                # Surface raw events to any registered handler first.
                if on_event is not None:
                    try:
                        on_event(data)
                    except Exception as cb_err:
                        self.logger.warning(f"on_event callback raised: {cb_err}")

                event_type = data.get("type")
                if event_type == "executing":
                    payload = data.get("data", {})
                    event_prompt_id = payload.get("prompt_id")
                    node = payload.get("node")

                    # Ignore events for other prompts (same clientId can be reused).
                    if event_prompt_id != prompt_id:
                        continue

                    if node is None:
                        # ComfyUI signals prompt-level completion with node=None.
                        elapsed = time.time() - start
                        self.logger.debug(
                            f"WebSocket reports execution complete for {prompt_id} in {elapsed:.1f}s"
                        )
                        break
                    else:
                        # Per-node execution progress.
                        self.logger.debug(
                            f"WebSocket executing node {node} for {prompt_id}"
                        )
                elif event_type is not None:
                    # Log other structured WS events at debug level for richer telemetry.
                    self.logger.debug(f"WebSocket event {event_type} for {prompt_id}: {data}")
            else:
                elapsed = time.time() - start
                raise ComfyTimeoutError(
                    f"Generation timed out after {elapsed:.1f}s (limit: {self.timeout}s)"
                )
        finally:
            try:
                ws.close()
            except Exception:
                pass

        # Once WebSocket reports completion, read history once (with a small grace period
        # in case the history entry lags slightly behind the executing event).
        history = None
        history_start = time.time()
        while history is None and time.time() - history_start < max(self.poll_interval, 1):
            history = self._get_history(prompt_id)
            if history is None:
                time.sleep(min(self.poll_interval, 1))

        if not history:
            raise ComfyGenerationError(f"No history found for completed prompt {prompt_id}")

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
                "type": image.get('type', 'output'),
            }

            elapsed = time.time() - start
            self.logger.debug(
                f"Generation complete: {prompt_id} -> {filename} in {elapsed:.1f}s (via WebSocket)"
            )
            return result

        raise ComfyGenerationError(f"No images in output for {prompt_id}")
    
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
