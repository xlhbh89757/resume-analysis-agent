# 简历离线批处理运维手册

## 1. 适用范围

本手册用于离线批量结构化员工简历，入口是员工工号，执行时实时向来源系统申请 15 分钟临时 URL，再完成下载、解析、LLM 抽取和 MySQL 落库。

## 2. 环境准备

需要提前确认以下依赖可用：

1. MySQL 已连到目标环境。
2. Redis 已启动，供 Celery broker/result backend 使用。
3. Qdrant 已启动；如果本轮只关心结构化落库，可以暂时不做向量化校验。
4. `.env` 已配置以下关键项：

```env
DATABASE_URL=mysql+pymysql://root:***@host:3307/uat?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
OPENAI_API_KEY=***
RESUME_SOURCE_API_BASE_URL=https://your-source-system.example.com
RESUME_SOURCE_API_TOKEN=***
RESUME_SOURCE_API_TIMEOUT=30
```

## 3. 启动顺序

1. 初始化数据库表

```powershell
& .\.venv\Scripts\python.exe scripts/init_db.py
```

2. 启动 API

```powershell
& .\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

3. 启动 Celery Worker

```powershell
& .\.venv\Scripts\python.exe -m celery -A src.tasks.analysis worker -Q dispatch_queue,extract_queue,llm_queue,persist_queue,dead_letter_queue --loglevel=info --concurrency=4
```

4. 可选：启动 Flower 观察任务

```powershell
& .\.venv\Scripts\python.exe -m celery -A src.tasks.analysis flower
```

## 4. 批处理执行

1. 先做 dry-run，确认来源系统返回的数据范围正确：

```powershell
& .\.venv\Scripts\python.exe scripts/run_batch_structuring.py --start-employee E0001 --end-employee E9999 --batch-size 200 --dry-run
```

2. 正式投递一批任务：

```powershell
& .\.venv\Scripts\python.exe scripts/run_batch_structuring.py --start-employee E0001 --end-employee E9999 --batch-size 200
```

脚本会做两件事：

1. 在 `resume_struct_batches` 创建一条批次记录。
2. 在 `resume_struct_tasks` 创建任务记录，并投递 `dispatch_queue`。

## 5. 死信重试

按员工工号重试死信任务：

```powershell
& .\.venv\Scripts\python.exe scripts/retry_deadletter.py --employee-id E0007 --employee-id E0156
```

脚本会把对应任务状态恢复为 `queued`，清空上一轮错误，并重新投递 `extract_resume_task`。

## 6. 日常巡检

每轮批处理至少检查以下指标：

1. `resume_struct_batches`
   - `total_count`
   - `success_count`
   - `failed_count`
   - `skipped_count`
2. `resume_struct_tasks`
   - `status`
   - `attempt_count`
   - `llm_tokens_in`
   - `llm_tokens_out`
   - `llm_cost`
3. `resume_struct_deadletters`
   - 是否持续增长
   - 是否集中在同一类错误码

## 7. 告警建议

建议至少有以下告警：

1. 10 分钟窗口失败率超过 8%。
2. 死信率超过 2%。
3. 每小时预算燃烧速度超过计划阈值。
4. 403 下载失败占比异常升高，通常表示临时 URL 过期刷新策略或来源系统接口异常。

## 8. 故障定位顺序

1. 先看 `resume_struct_tasks.error_code/error_message`。
2. 再看应用日志中 `E_DOWNLOAD / E_LLM / E_PERSIST / E_BUDGET`。
3. 若是下载失败，先验证来源系统能否正常生成临时 URL。
4. 若是 LLM 失败，先核对 API Key、模型名、单份 token 长度和预算守卫状态。
5. 若是入库失败，检查 MySQL 连通性、表结构和唯一键冲突。

## 9. 验收标准

本轮批处理完成后，至少满足：

1. 所有任务都进入终态：`success / skipped / failed / dead`。
2. 关键字段完整率达到项目预期。
3. 总成本不超过预算上限。
4. 死信任务可按员工工号重试。

## 10. 回滚方式

如果上线批处理后异常率过高，按以下顺序回滚：

1. 先停止 Worker，防止继续消费。
2. 停止新的批处理投递脚本。
3. 保留 `resume_struct_tasks` 和 `resume_struct_deadletters` 现场数据用于排查。
4. 修复后只重放失败/死信任务，不要重复处理已成功批次。
