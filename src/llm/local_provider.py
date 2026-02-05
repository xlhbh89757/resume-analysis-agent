"""本地 LLM Provider - 使用 vLLM 进行推理"""
import json
import re
from typing import Dict, Any, Optional
import logging

from src.llm.base import BaseLLMProvider
from src.core.config import settings

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    """本地 LLM Provider
    
    使用 vLLM 进行本地模型推理，支持 Qwen、Llama 等模型。
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.local_model_path
        self._engine = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保模型已初始化"""
        if not self._initialized:
            await self._init_engine()
    
    async def _init_engine(self):
        """初始化 vLLM 引擎"""
        try:
            from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams
            
            engine_args = AsyncEngineArgs(
                model=self.model_path,
                tensor_parallel_size=settings.local_model_tensor_parallel_size,
                gpu_memory_utilization=settings.local_model_gpu_memory_utilization,
                trust_remote_code=True,
            )
            self._engine = AsyncLLMEngine.from_engine_args(engine_args)
            self._initialized = True
            logger.info(f"Local LLM engine initialized: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize local LLM engine: {e}")
            raise
    
    async def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """生成文本"""
        await self._ensure_initialized()
        
        from vllm import SamplingParams
        
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # 构建聊天格式的 prompt
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self._format_chat_prompt(messages)
        
        results = await self._engine.generate(formatted_prompt, sampling_params, request_id=None)
        
        if results and results[0].outputs:
            return results[0].outputs[0].text.strip()
        return ""
    
    async def generate_json(
        self, 
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成 JSON 格式输出"""
        response = await self.generate(prompt, temperature=0.3, **kwargs)
        
        # 尝试提取 JSON
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试从代码块中提取
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 尝试修复常见的 JSON 错误
            fixed_response = self._fix_json(response)
            if fixed_response:
                return fixed_response
            
            logger.warning(f"Failed to parse JSON from response: {response[:200]}...")
            return {}
    
    def _format_chat_prompt(self, messages: list) -> str:
        """格式化聊天 prompt（Qwen 格式）"""
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                formatted += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                formatted += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        formatted += "<|im_start|>assistant\n"
        return formatted
    
    def _fix_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试修复常见的 JSON 格式错误"""
        # 移除可能的前缀/后缀文本
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return None
    
    @property
    def provider_name(self) -> str:
        return "local"
