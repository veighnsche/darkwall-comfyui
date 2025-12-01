"""
ComfyUI HTTP API client.

TEAM_007: Refactored - orchestration layer only.
Transport logic moved to transport.py, injection logic moved to injection.py.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Callable

from ..config import ComfyUIConfig
from ..prompt_generator import PromptResult
from .transport import ComfyTransport
from .injection import inject_prompt, inject_prompts, inject_seed


@dataclass
class GenerationResult:
    """Result of a successful ComfyUI generation."""
    prompt_id: str
    filename: str
    image_data: bytes


class ComfyClient:
    """
    Client for ComfyUI HTTP API.
    
    TEAM_007: Refactored to use ComfyTransport for HTTP/WebSocket
    and injection module for workflow manipulation.
    
    Usage:
        client = ComfyClient(config)
        result = client.generate(workflow_dict, prompt_text)
        # result.image_data contains the generated image bytes
    """
    
    def __init__(self, comfyui_config: ComfyUIConfig) -> None:
        self.config = comfyui_config
        self._transport = ComfyTransport(comfyui_config)
        self.logger = logging.getLogger(__name__)
    
    @property
    def base_url(self) -> str:
        """Base URL for ComfyUI API."""
        return self._transport.base_url
    
    @property
    def timeout(self) -> int:
        """Request timeout in seconds."""
        return self._transport.timeout
    
    @property
    def poll_interval(self) -> int:
        """Polling interval in seconds."""
        return self._transport.poll_interval
    
    @property
    def client_id(self) -> str:
        """Unique client identifier."""
        return self._transport.client_id
    
    @property
    def session(self):
        """HTTP session for requests."""
        return self._transport.session
        
    
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
            on_event: Optional callback for WebSocket events
            
        Returns:
            GenerationResult with image data
            
        Raises:
            ComfyClientError: On any failure
        """
        # Inject prompt(s) into workflow
        if isinstance(prompt, PromptResult):
            workflow = inject_prompts(workflow, prompt)
            # If the prompt generator provided a deterministic seed, inject it
            if getattr(prompt, "seed", None) is not None:
                workflow = inject_seed(workflow, prompt.seed)
        else:
            workflow = inject_prompt(workflow, prompt)
        
        # Submit workflow
        prompt_id = self._transport.submit(workflow)
        self.logger.info(f"Submitted workflow: {prompt_id}")
        
        # Wait for completion
        result = self._transport.wait_for_result(prompt_id, on_event=on_event)
        
        # Download image (use type/subfolder from result for correct path)
        image_data = self._transport.download_image(
            result["filename"],
            subfolder=result.get("subfolder", ""),
            type_=result.get("type", "output"),
        )
        
        return GenerationResult(
            prompt_id=prompt_id,
            filename=result["filename"],
            image_data=image_data
        )
    
    def health_check(self) -> bool:
        """
        Check if ComfyUI is reachable.
        
        Returns:
            True if ComfyUI is reachable and healthy
        """
        return self._transport.health_check()
    
    def detailed_health_check(self) -> dict[str, Any]:
        """
        Perform detailed health check with system information.
        
        Returns:
            Dictionary with health status and system information
        """
        return self._transport.detailed_health_check()
    
    # Private methods delegating to transport/injection (used by tests)
    def _inject_prompt(self, workflow: dict[str, Any], prompt: str) -> dict[str, Any]:
        """Inject prompt into workflow nodes."""
        return inject_prompt(workflow, prompt)
    
    def _inject_prompts(self, workflow: dict[str, Any], prompts: PromptResult) -> dict[str, Any]:
        """Inject prompts into workflow nodes using placeholders."""
        return inject_prompts(workflow, prompts)
    
    def _inject_seed(self, workflow: dict[str, Any], seed: int) -> dict[str, Any]:
        """Inject deterministic seed into Seed (rgthree) nodes."""
        return inject_seed(workflow, seed)
    
    def _submit(self, workflow: dict[str, Any]) -> str:
        """Submit workflow and return prompt_id."""
        return self._transport.submit(workflow)
    
    def _wait_for_result(
        self,
        prompt_id: str,
        on_event: Optional[Callable[[Any], None]] = None,
    ) -> dict[str, Any]:
        """Wait for generation completion."""
        return self._transport.wait_for_result(prompt_id, on_event=on_event)
    
    def _get_history(self, prompt_id: str) -> Optional[dict[str, Any]]:
        """Get generation history for prompt_id."""
        return self._transport.get_history(prompt_id)
    
    def _download_image(self, filename: str, subfolder: str = "", type_: str = "output") -> bytes:
        """Download generated image."""
        return self._transport.download_image(filename, subfolder, type_)
    
    def _build_ws_url(self) -> str:
        """Build WebSocket URL."""
        return self._transport._build_ws_url()
