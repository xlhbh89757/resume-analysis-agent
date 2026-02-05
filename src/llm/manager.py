"""LLM Provider 管理器 - 支持多 Provider 切换和降级"""
import logging
from typing import Optional, Dict, Any, List

from src.llm.base import BaseLLMProvider
from src.llm.local_provider import LocalLLMProvider
from src.llm.openai_provider import OpenAIProvider, ClaudeProvider
from src.core.config import settings

logger = logging.getLogger(__name__)


class LLMProviderManager:
    """LLM Provider 管理器
    
    负责创建、管理和切换不同的 LLM Provider，支持降级策略。
    """
    
    _providers: Dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """获取指定的 LLM Provider
        
        Args:
            provider_name: Provider 名称，可选值: local, openai, claude
                          如果不指定，使用配置文件中的默认值
        
        Returns:
            LLM Provider 实例
        """
        name = provider_name or settings.llm_provider
        
        if name not in cls._providers:
            cls._providers[name] = cls._create_provider(name)
        
        return cls._providers[name]
    
    @classmethod
    def _create_provider(cls, name: str) -> BaseLLMProvider:
        """创建 Provider 实例"""
        if name == "local":
            return LocalLLMProvider()
        elif name == "openai":
            return OpenAIProvider()
        elif name == "claude":
            return ClaudeProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {name}")
    
    @classmethod
    async def generate_with_fallback(
        cls,
        prompt: str,
        primary_provider: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """使用降级策略生成文本
        
        当主 Provider 失败时，自动尝试备用 Provider。
        
        Args:
            prompt: 输入提示词
            primary_provider: 主 Provider
            fallback_providers: 备用 Provider 列表
            **kwargs: 其他参数
        
        Returns:
            生成的文本
        """
        primary = primary_provider or settings.llm_provider
        fallbacks = fallback_providers or cls._get_default_fallbacks(primary)
        
        all_providers = [primary] + fallbacks
        
        for provider_name in all_providers:
            try:
                provider = cls.get_provider(provider_name)
                result = await provider.generate(prompt, **kwargs)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        raise RuntimeError("All LLM providers failed")
    
    @classmethod
    async def generate_json_with_fallback(
        cls,
        prompt: str,
        primary_provider: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """使用降级策略生成 JSON"""
        primary = primary_provider or settings.llm_provider
        fallbacks = fallback_providers or cls._get_default_fallbacks(primary)
        
        all_providers = [primary] + fallbacks
        
        for provider_name in all_providers:
            try:
                provider = cls.get_provider(provider_name)
                result = await provider.generate_json(prompt, **kwargs)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        raise RuntimeError("All LLM providers failed")
    
    @classmethod
    def _get_default_fallbacks(cls, primary: str) -> List[str]:
        """获取默认的降级 Provider 列表"""
        all_providers = ["local", "openai", "claude"]
        
        # 移除当前 primary，并检查哪些 provider 可用
        available = []
        for p in all_providers:
            if p == primary:
                continue
            if p == "openai" and not settings.openai_api_key:
                continue
            if p == "claude" and not settings.claude_api_key:
                continue
            available.append(p)
        
        return available
