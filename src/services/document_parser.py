"""文档解析服务 - 支持 PDF/DOCX 格式"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentParser:
    """文档解析服务
    
    支持 PDF 和 DOCX 格式的简历解析。
    """
    
    def parse(self, file_path: str) -> str:
        """解析文档并提取文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
            
        Raises:
            ValueError: 不支持的文件格式
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            return self._parse_pdf(file_path)
        elif suffix in ['.docx', '.doc']:
            return self._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def _parse_pdf(self, file_path: str) -> str:
        """解析 PDF 文件"""
        try:
            import PyPDF2
            
            text_parts = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            text = "\n".join(text_parts)
            
            # 清理文本
            text = self._clean_text(text)
            
            logger.info(f"Parsed PDF: {file_path}, length: {len(text)} chars")
            return text
            
        except Exception as e:
            logger.error(f"Failed to parse PDF: {file_path}, error: {e}")
            raise
    
    def _parse_docx(self, file_path: str) -> str:
        """解析 DOCX 文件"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            
            # 提取段落文本
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            
            # 提取表格文本
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        tables_text.append(" | ".join(row_text))
            
            # 合并所有文本
            all_text = paragraphs + tables_text
            text = "\n".join(all_text)
            
            # 清理文本
            text = self._clean_text(text)
            
            logger.info(f"Parsed DOCX: {file_path}, length: {len(text)} chars")
            return text
            
        except Exception as e:
            logger.error(f"Failed to parse DOCX: {file_path}, error: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        import re
        
        # 移除多余的空白行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 移除多余的空格
        text = re.sub(r' {2,}', ' ', text)
        
        # 移除首尾空白
        text = text.strip()
        
        return text
    
    def get_file_info(self, file_path: str) -> dict:
        """获取文件信息"""
        path = Path(file_path)
        
        return {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
