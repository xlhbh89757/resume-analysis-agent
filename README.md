# Resume Analysis Agent

用于简历解析、结构化和离线批处理入库的服务端项目。

## 当前能力

1. 支持 PDF/DOCX 简历文本提取。
2. 支持通过上传文件或简历 URL 进行同步结构化。
3. 支持基于 Celery 的离线批处理链路：
   - `dispatch -> extract -> llm -> persist -> deadletter`
4. 支持 MySQL 落库、Redis 队列和 Qdrant 向量库。
5. 支持预算守卫、死信重试和批次治理表。

## 快速启动

### 依赖

1. Python 3.10+
2. Docker / Docker Compose
3. MySQL、Redis、Qdrant

### 启动步骤

```powershell
docker compose up -d
& .\.venv\Scripts\python.exe scripts/init_db.py
& .\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

API 文档：

- `http://localhost:8000/docs`

## 关键接口

1. 上传文件结构化
- `POST /api/v1/resumes/upload`
2. 通过 URL 同步结构化
- `POST /api/v1/resumes/structure-from-url`
3. 通过员工工号同步结构化
- `POST /api/v1/resumes/structure-from-employee`

## 离线批处理

1. dry-run 预览：

```powershell
& .\.venv\Scripts\python.exe scripts/run_batch_structuring.py --start-employee E0001 --end-employee E9999 --batch-size 200 --dry-run
```

2. 正式投递：

```powershell
& .\.venv\Scripts\python.exe scripts/run_batch_structuring.py --start-employee E0001 --end-employee E9999 --batch-size 200
```

3. 死信重试：

```powershell
& .\.venv\Scripts\python.exe scripts/retry_deadletter.py --employee-id E0007 --employee-id E0156
```

## 运维文档

- `docs/runbooks/resume-batch-ops.md`
- `docs/runbooks/resume-batch-rollout-checklist.md`
