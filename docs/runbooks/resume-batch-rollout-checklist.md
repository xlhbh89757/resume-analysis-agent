# 简历离线批处理上线检查清单

## 上线前

1. `.env` 已配置 `DATABASE_URL / CELERY_BROKER_URL / CELERY_RESULT_BACKEND / OPENAI_API_KEY / RESUME_SOURCE_API_BASE_URL / RESUME_SOURCE_API_TOKEN`。
2. `scripts/init_db.py` 已在目标环境执行，批处理治理表已创建。
3. Redis、MySQL、Qdrant 连通性已验证。
4. Celery Worker 已按 `dispatch_queue,extract_queue,llm_queue,persist_queue,dead_letter_queue` 启动。
5. Worker 并发参数已按机器规格设置，不超过来源系统和 LLM API 限流。
6. 预算阈值已确认，预算守卫配置已开启。
7. 临时 URL 接口已验证返回 15 分钟有效链接。
8. 至少用 5-10 份样本完成过全链路验证。

## 上线时

1. 先执行一次 `run_batch_structuring.py --dry-run`，确认工号范围正确。
2. 先投递一小批样本，观察 10-20 分钟。
3. 重点检查 `resume_struct_tasks` 中 `E_DOWNLOAD / E_LLM / E_PERSIST / E_BUDGET` 占比。
4. 观察成功率、死信率、平均处理时长和预算消耗。
5. 确认入库后的候选人数据字段完整，尤其是工作经历和项目经历。

## 回滚

1. 立即停止 Celery Worker。
2. 停止新的批次投递。
3. 导出当前批次和死信记录。
4. 修复问题后只按工号重放失败任务，不要全量重刷。
