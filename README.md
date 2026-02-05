# Resume Analysis Agent

智能简历分析 Agent - 支持 HR 批量筛选和 ATS 系统集成。

## 功能特性

- 📄 支持 PDF/DOCX 简历解析
- 🤖 本地 LLM (Qwen 14B) + 云端 API 支持
- 🎯 JD 职位匹配评分
- 🔍 语义搜索候选人
- ⚡ 批量处理能力

## 快速开始

### 环境要求

- Python 3.10+
- NVIDIA GPU (推荐 RTX 4090 24GB)
- Docker & Docker Compose

### 安装

```bash
# 1. 克隆项目
git clone <repo-url>
cd resume-agent

# 2. 安装依赖
poetry install

# 3. 启动依赖服务
docker-compose up -d

# 4. 初始化数据库
python scripts/init_db.py

# 5. 启动服务
uvicorn src.api.main:app --reload --port 8000
```

### API 文档

启动服务后访问: http://localhost:8000/docs

## 项目结构

```
resume-agent/
├── src/
│   ├── api/           # FastAPI 应用
│   ├── services/      # 业务逻辑
│   ├── llm/           # LLM Provider
│   ├── models/        # 数据模型
│   ├── tasks/         # 异步任务
│   └── core/          # 核心配置
├── tests/             # 测试
├── scripts/           # 脚本工具
└── config/            # 配置文件
```

## 许可证

MIT License
