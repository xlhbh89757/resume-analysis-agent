"""LLM Provider 抽象基类"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类
    
    所有 LLM Provider 都必须继承此类并实现 generate 和 embed 方法。
    """
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """生成文本
        
        Args:
            prompt: 输入提示词
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    async def generate_json(
        self, 
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成 JSON 格式输出
        
        Args:
            prompt: 输入提示词
            **kwargs: 其他参数
            
        Returns:
            解析后的 JSON 字典
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        pass
