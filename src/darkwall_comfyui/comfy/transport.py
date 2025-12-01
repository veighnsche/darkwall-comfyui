"""
HTTP and WebSocket transport for ComfyUI API.

TEAM_007: Extracted from client.py for better separation of concerns.

Handles low-level communication: session management, requests, WebSocket events.
"""

import json
import logging
import time
import uuid
from typing import Any, Optional, Callable
from urllib.parse import urljoin, urlparse, urlunparse, urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import websocket

from ..config import ComfyUIConfig
from ..exceptions import (
    ComfyClientError,
    ComfyConnectionError,
    ComfyTimeoutError,
    ComfyGenerationError,
)


logger = logging.getLogger(__name__)


class ComfyTransport:
    """
    Low-level HTTP/WebSocket transport for ComfyUI.
    
    Handles:
    - Session management with retry logic and connection pooling
    - Health checks
    - Workflow submission
    - WebSocket-based result waiting
    - History retrieval
    - Image download
    """
    
    def __init__(self, config: ComfyUIConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.timeout = config.timeout
        self.poll_interval = config.poll_interval
        self.client_id = str(uuid.uuid4())
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=2,
            raise_on_status=False,
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False
        )
        
        # Create session with optimized configuration
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'darkwall-comfyui/0.1.0'
        })
        if config.headers:
            self.session.headers.update(config.headers)
        
        logger.debug("ComfyUI transport initialized with retry logic and connection pooling")
    
    def health_check(self) -> bool:
        """
        Check if ComfyUI is reachable.
        
        Returns:
            True if ComfyUI is reachable and healthy
        """
        try:
            response = self.session.get(
                urljoin(self.base_url, '/system_stats'),
                timeout=10
            )
            if response.status_code == 200:
                logger.debug("ComfyUI health check passed")
                return True
            else:
                logger.warning(f"ComfyUI health check failed: HTTP {response.status_code}")
                return False
        except requests.ConnectionError as e:
            logger.debug(f"ComfyUI connection error during health check: {e}")
            return False
        except requests.Timeout as e:
            logger.debug(f"ComfyUI health check timeout: {e}")
            return False
        except requests.RequestException as e:
            logger.debug(f"ComfyUI health check request error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
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
                    logger.warning("ComfyUI returned invalid JSON in system_stats")
                    health_info['system_stats'] = {'raw_response': response.text}
                
                logger.debug(f"ComfyUI detailed health check passed in {response_time:.2f}ms")
            else:
                health_info['error'] = f"HTTP {response.status_code}"
                logger.warning(f"ComfyUI detailed health check failed: HTTP {response.status_code}")
                
        except requests.ConnectionError as e:
            health_info['error'] = f"Connection error: {e}"
            logger.debug(f"ComfyUI connection error during detailed health check: {e}")
        except requests.Timeout as e:
            health_info['error'] = f"Timeout error: {e}"
            logger.debug(f"ComfyUI timeout during detailed health check: {e}")
        except requests.RequestException as e:
            health_info['error'] = f"Request error: {e}"
            logger.debug(f"ComfyUI request error during detailed health check: {e}")
        except Exception as e:
            health_info['error'] = f"Unexpected error: {e}"
            logger.error(f"Unexpected error during detailed health check: {e}")
        
        return health_info
    
    def submit(self, workflow: dict[str, Any]) -> str:
        """
        Submit workflow and return prompt_id.
        
        Args:
            workflow: ComfyUI workflow dict (API format)
            
        Returns:
            prompt_id for tracking the generation
            
        Raises:
            ComfyConnectionError: On connection issues
            ComfyGenerationError: On workflow validation errors
            ComfyClientError: On other errors
        """
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
            logger.debug(f"Workflow submitted successfully: {prompt_id}")
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
        """Build WebSocket URL from base HTTP URL."""
        parsed = urlparse(self.base_url)
        ws_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        netloc = parsed.netloc or parsed.path
        query = urlencode({"clientId": self.client_id})
        return urlunparse((ws_scheme, netloc, '/ws', "", query, ""))

    def wait_for_result(
        self,
        prompt_id: str,
        on_event: Optional[Callable[[Any], None]] = None,
    ) -> dict[str, Any]:
        """
        Wait for generation completion via WebSocket and read history.

        Args:
            prompt_id: The prompt ID to wait for
            on_event: Optional callback for WebSocket events
            
        Returns:
            Dict with filename, subfolder, type
            
        Raises:
            ComfyConnectionError: On WebSocket connection issues
            ComfyTimeoutError: If generation times out
            ComfyGenerationError: If no output found
        """
        start = time.time()
        ws_url = self._build_ws_url()

        logger.debug(
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
                    continue
                except websocket.WebSocketConnectionClosedException as e:
                    raise ComfyClientError(f"WebSocket closed while waiting for {prompt_id}: {e}")

                if isinstance(message, bytes):
                    continue

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.debug(f"Non-JSON WebSocket message: {message!r}")
                    if on_event is not None:
                        try:
                            on_event(message)
                        except Exception as cb_err:
                            logger.warning(f"on_event callback raised: {cb_err}")
                    continue

                if on_event is not None:
                    try:
                        on_event(data)
                    except Exception as cb_err:
                        logger.warning(f"on_event callback raised: {cb_err}")

                event_type = data.get("type")
                if event_type == "executing":
                    payload = data.get("data", {})
                    event_prompt_id = payload.get("prompt_id")
                    node = payload.get("node")

                    if event_prompt_id != prompt_id:
                        continue

                    if node is None:
                        elapsed = time.time() - start
                        logger.debug(
                            f"WebSocket reports execution complete for {prompt_id} in {elapsed:.1f}s"
                        )
                        break
                    else:
                        logger.debug(f"WebSocket executing node {node} for {prompt_id}")
                elif event_type == "execution_error":
                    payload = data.get("data", {})
                    event_prompt_id = payload.get("prompt_id")
                    if event_prompt_id == prompt_id:
                        error_msg = payload.get("exception_message", "Unknown error")
                        node_id = payload.get("node_id", "unknown")
                        node_type = payload.get("node_type", "unknown")
                        logger.error(f"ComfyUI execution error in node {node_id} ({node_type}): {error_msg}")
                        raise ComfyGenerationError(f"ComfyUI error in {node_type}: {error_msg}")
                elif event_type is not None:
                    logger.debug(f"WebSocket event {event_type} for {prompt_id}: {data}")
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

        # Read history with grace period
        history = None
        history_start = time.time()
        while history is None and time.time() - history_start < max(self.poll_interval, 1):
            history = self.get_history(prompt_id)
            if history is None:
                time.sleep(min(self.poll_interval, 1))

        if not history:
            raise ComfyGenerationError(f"No history found for completed prompt {prompt_id}")

        logger.debug(f"History for {prompt_id}: {list(history.keys())}")
        logger.debug(f"Full history: {history}")
        outputs = history.get('outputs', {})
        
        # Check for errors in status
        status = history.get('status', {})
        if status.get('status_str') == 'error' or status.get('messages'):
            messages = status.get('messages', [])
            for msg in messages:
                if isinstance(msg, (list, tuple)) and len(msg) >= 2:
                    if msg[0] == 'execution_error':
                        error_data = msg[1] if isinstance(msg[1], dict) else {}
                        node_id = error_data.get('node_id', 'unknown')
                        node_type = error_data.get('node_type', 'unknown')
                        exception_msg = error_data.get('exception_message', 'Unknown error')
                        logger.error(f"Execution error in node {node_id} ({node_type}): {exception_msg}")
                        raise ComfyGenerationError(f"ComfyUI error in {node_type}: {exception_msg}")
        
        if not outputs:
            # Log full history for debugging
            logger.error(f"No outputs in history for {prompt_id}. History keys: {list(history.keys())}")
            if status:
                logger.error(f"Status: {status}")
            # Include status in exception for visibility
            status_str = status.get('status_str', 'unknown') if status else 'no status'
            completed = status.get('completed', False) if status else False
            raise ComfyGenerationError(
                f"No outputs found for {prompt_id} (status: {status_str}, completed: {completed}). "
                f"This may indicate workflow caching or an execution error. "
                f"Run with --log-level DEBUG for full history."
            )

        # Collect all candidate images, preferring type='output' over type='temp'
        output_images: list[dict[str, Any]] = []
        temp_images: list[dict[str, Any]] = []
        
        for node_id, output in outputs.items():
            if not isinstance(output, dict):
                continue

            images = output.get('images', [])
            for image in images:
                if not isinstance(image, dict):
                    continue
                
                filename = image.get('filename')
                if not filename:
                    continue
                
                img_type = image.get('type', 'output')
                candidate = {
                    "filename": filename,
                    "subfolder": image.get('subfolder', ''),
                    "type": img_type,
                    "node_id": node_id,
                }
                
                if img_type == 'output':
                    output_images.append(candidate)
                else:
                    temp_images.append(candidate)
        
        # Prefer final output images, fall back to temp if none
        candidates = output_images if output_images else temp_images
        if not candidates:
            raise ComfyGenerationError(f"No images in output for {prompt_id}")
        
        # Use the last output image (typically the final SaveImage node)
        result = candidates[-1]
        
        elapsed = time.time() - start
        logger.debug(
            f"Generation complete: {prompt_id} -> {result['filename']} "
            f"(type={result['type']}, node={result['node_id']}) in {elapsed:.1f}s"
        )
        return result
    
    def get_history(self, prompt_id: str) -> Optional[dict[str, Any]]:
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
            logger.debug(f"Connection error getting history for {prompt_id}: {e}")
            return None
        except requests.Timeout as e:
            logger.debug(f"Timeout getting history for {prompt_id}: {e}")
            return None
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"History not found for {prompt_id} (generation may not be started)")
                return None
            else:
                logger.warning(f"HTTP error getting history for {prompt_id}: {e}")
                return None
        except requests.RequestException as e:
            logger.debug(f"Request error getting history for {prompt_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in history response for {prompt_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error getting history for {prompt_id}: {e}")
            return None
    
    def download_image(self, filename: str, subfolder: str = "", type_: str = "output") -> bytes:
        """
        Download generated image.
        
        Args:
            filename: Image filename
            subfolder: Optional subfolder
            type_: Image type (default: "output")
            
        Returns:
            Image bytes
            
        Raises:
            ComfyConnectionError: On connection issues
            ComfyClientError: On download errors
        """
        params = {"filename": filename, "subfolder": subfolder, "type": type_}
        
        try:
            logger.debug(f"Downloading image: {filename} (subfolder={subfolder}, type={type_})")
            
            response = self.session.get(
                urljoin(self.base_url, '/view'),
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            content = response.content
            if not content:
                raise ComfyClientError(f"Empty image data received for {filename}")
            
            if len(content) < 100:
                raise ComfyClientError(f"Image data too small for {filename}: {len(content)} bytes")
            
            logger.debug(f"Downloaded {len(content)} bytes for {filename}")
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
