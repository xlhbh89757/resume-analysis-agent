"""OpenAI LLM Provider"""
import json
import logging
import re
from typing import Dict, Any, Optional

import httpx

from src.llm.base import BaseLLMProvider
from src.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider
    
    支持 OpenAI 官方 API 以及兼容 OpenAI 格式的其他 API（如 Azure、本地代理等）。
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = base_url or settings.openai_base_url
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    async def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """生成文本"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("choices") and data["choices"][0].get("message"):
                return data["choices"][0]["message"]["content"].strip()
            return ""
    
    async def generate_json(
        self, 
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成 JSON 格式输出"""
        # 移除 strict JSON mode，依赖 Prompt 指令和后处理，以提高兼容性
        try:
            # 尝试生成文本，使用低温度以增加确定性
            response_text = await self.generate(
                prompt, 
                temperature=0.3,
                **kwargs
            )
            
            if not response_text:
                return {}
            
            # 尝试直接解析
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass
                
            # 尝试从 Markdown 代码块提取
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 尝试查找第一个 { 和 最后一个 }
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(response_text[start:end+1])
                except json.JSONDecodeError:
                    pass
                    
            logger.warning(f"Failed to parse JSON from response: {response_text[:200]}...")
            return {}
            
        except Exception as e:
            logger.error(f"Error in generate_json: {e}")
            return {}
    
    @property
    def provider_name(self) -> str:
        return "openai"


class ClaudeProvider(BaseLLMProvider):
    """Claude API Provider"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.claude_api_key
        self.model = model or settings.claude_model
        
        if not self.api_key:
            raise ValueError("Claude API key is required")
    
    async def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """生成文本"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("content") and data["content"][0].get("text"):
                return data["content"][0]["text"].strip()
            return ""
    
    async def generate_json(
        self, 
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成 JSON 格式输出"""
        response = await self.generate(prompt, temperature=0.3, **kwargs)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试从 markdown 代码块中提取
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to parse JSON: {response[:200]}...")
            return {}
    
    @property
    def provider_name(self) -> str:
        return "claude"
