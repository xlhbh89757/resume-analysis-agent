"""向量搜索服务 - 使用 Qdrant 进行语义搜索"""
import logging
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    Range,
    MatchValue,
)

from src.core.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    """向量搜索服务
    
    使用 Qdrant 进行简历的向量存储和语义搜索。
    """
    
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection_name
        self._embedding_model = None
        self._init_collection()
    
    def _init_collection(self):
        """初始化向量集合"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    @property
    def embedding_model(self):
        """延迟加载 Embedding 模型"""
        if self._embedding_model is None:
            from fastembed import TextEmbedding
            self._embedding_model = TextEmbedding(settings.embedding_model_name)
            logger.info(f"Loaded embedding model: {settings.embedding_model_name}")
        return self._embedding_model
    
    def embed_text(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        embeddings = list(self.embedding_model.embed([text]))
        return embeddings[0].tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本嵌入向量"""
        embeddings = list(self.embedding_model.embed(texts))
        return [e.tolist() for e in embeddings]
    
    async def add_candidate_vector(
        self,
        candidate_id: int,
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """添加候选人向量
        
        Args:
            candidate_id: 候选人 ID
            text: 用于生成向量的文本（简历摘要）
            metadata: 元数据（用于过滤和展示）
            
        Returns:
            是否成功
        """
        try:
            # 生成嵌入向量
            embedding = self.embed_text(text)
            
            # 存入 Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=candidate_id,
                        vector=embedding,
                        payload=metadata
                    )
                ]
            )
            
            logger.info(f"Added vector for candidate: {candidate_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add candidate vector: {e}")
            return False
    
    async def search_candidates(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """语义搜索候选人
        
        Args:
            query: 自然语言查询
            top_k: 返回数量
            filters: 过滤条件
            
        Returns:
            搜索结果列表
        """
        try:
            # 查询向量化
            query_embedding = self.embed_text(query)
            
            # 构建过滤器
            qdrant_filter = self._build_filter(filters) if filters else None
            
            # 搜索
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=qdrant_filter,
            )
            
            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "candidate_id": result.id,
                    "similarity_score": result.score,
                    **result.payload
                })
            
            logger.info(f"Search completed, found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """构建 Qdrant 过滤器"""
        conditions = []
        
        if "min_experience" in filters:
            conditions.append(
                FieldCondition(
                    key="years_of_experience",
                    range=Range(gte=filters["min_experience"])
                )
            )
        
        if "max_experience" in filters:
            conditions.append(
                FieldCondition(
                    key="years_of_experience",
                    range=Range(lte=filters["max_experience"])
                )
            )
        
        if "education_level" in filters:
            edu_levels = filters["education_level"]
            if isinstance(edu_levels, str):
                edu_levels = [edu_levels]
            # 使用 should 来实现 OR 条件
            conditions.append(
                FieldCondition(
                    key="education_level",
                    match=MatchValue(value=edu_levels[0])  # 简化处理
                )
            )
        
        if conditions:
            return Filter(must=conditions)
        return None
    
    async def delete_candidate_vector(self, candidate_id: int) -> bool:
        """删除候选人向量"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[candidate_id]
            )
            logger.info(f"Deleted vector for candidate: {candidate_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vector: {e}")
            return False
