"""Ollama LLM service for PFMEA analysis."""
import httpx
import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self):
        """Initialize Ollama service."""
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            json_mode: Whether to request JSON output
            temperature: Sampling temperature
            
        Returns:
            Response dictionary with 'content' and 'reasoning' keys
        """
        url = f"{self.base_url}/api/chat"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        if json_mode:
            payload["format"] = "json"
        
        try:
            # Log the full prompt being sent
            logger.info("=" * 60)
            logger.info(f"🤖 LLM REQUEST to {self.model}")
            logger.info("=" * 60)
            if system_prompt:
                logger.info(f"📋 SYSTEM PROMPT:\n{system_prompt[:500]}...")
            logger.info(f"📝 USER PROMPT:\n{prompt}")
            logger.info("-" * 60)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                
                content = result.get("message", {}).get("content", "")
                
                # Log the full response
                logger.info("=" * 60)
                logger.info(f"✅ LLM RESPONSE (length: {len(content)})")
                logger.info("=" * 60)
                logger.info(f"📤 RESPONSE:\n{content}")
                logger.info("-" * 60)
                
                if json_mode:
                    try:
                        parsed = json.loads(content)
                        logger.info(f"Successfully parsed JSON response with keys: {list(parsed.keys())}")
                        return parsed
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON response: {e}")
                        logger.warning(f"Raw content: {content[:500]}")
                        return {"content": content, "raw": True}
                
                return {"content": content}
                
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise Exception("LLM request timed out. Please try again.")
        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise Exception(f"LLM service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Ollama service: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """
        Check if Ollama is available.
        
        Returns:
            True if Ollama is reachable, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False


