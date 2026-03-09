# 10,000份简历URL离线结构化设计（Celery 方案C）

**日期**: 2026-03-05  
**范围**: 仅离线批处理入库，不涉及前端展示

## 1. 目标与约束

- 目标规模: 10,000 份简历
- 完成时限: 1-2 天（<= 48 小时）
- 预算上限: 500 元
- 质量目标: 关键字段完整，项目职责/成果尽量保留原文
- 输入来源: 现有系统 API
- URL 特性: 临时 URL，15 分钟过期

## 2. 核心设计结论

- 队列任务不传 URL，仅传 `employee_id`（和 `resume_created_time`）。
- Worker 执行时实时调用接口获取临时 URL，避免排队过期。
- 幂等键采用 `employee_id + resume_created_time`。
- 架构采用 Celery 多队列，支持重试、死信、可观测、成本控制。

## 3. 部署拓扑（推荐）

- 节点A（4C8G）: Redis + Celery Beat + Flower + Dispatcher
- 节点B（8C16G）: Parse/LLM/Persist Worker
- 节点C（8C16G）: Parse/LLM/Persist Worker
- 可选节点D（16C32G）: OCR Worker（低质量样本触发）

## 4. 队列与流水线

- `dispatch_queue`: 分页拉员工并投递任务
- `extract_queue`: 申请临时URL、下载、文本解析、质量评分
- `ocr_queue`: 仅低质量文本进入 OCR
- `llm_queue`: 结构化抽取
- `persist_queue`: 幂等入库
- `dead_letter_queue`: 多次失败样本

处理链路:

1. dispatch(employee_id, resume_created_time)
2. get_temp_url(employee_id)
3. download + parse (+ optional OCR)
4. llm_extract
5. normalize
6. persist(idempotent)

补充约束:

- `extract -> llm -> persist -> deadletter` 必须形成真正可执行的 Celery 闭环，不能只停留在任务骨架。
- URL 下载与文本提取必须复用共享服务，避免 API 与 Celery 出现两套解析逻辑。
- 失败任务必须统一落到标准错误码和死信表，便于按 `employee_id` 精准重试。

## 5. 并发与吞吐参数

目标最低吞吐: 208 份/小时

- parse 并发: 6/台（总12）
- llm 并发: 4/台（总8）
- persist 并发: 4/台（总8）
- `worker_prefetch_multiplier=1`
- 重试: 2m -> 10m -> 30m，最多 3 次

## 6. 成本控制策略

- 为抽取任务设置 `max_tokens` 上限。
- 仅低质量样本进入 OCR+二次抽取。
- 小时级成本统计: `tokens_in/out`, `cost_hourly`, `cost_total`。
- 预算超速自动降级:
  1) 关闭二次抽取
  2) 降低 llm_queue 并发
  3) 切换仅关键字段模式

## 7. 数据模型建议

新增三张任务治理表:

- `resume_struct_batch`
- `resume_struct_task`
- `resume_struct_deadletter`

其中 `resume_struct_task` 关键字段:

- `employee_id`
- `resume_created_time`
- `idempotency_key`
- `status`
- `attempt_count`
- `error_code/error_message`
- `llm_tokens_in/llm_tokens_out/llm_cost`

## 8. 状态机

- `queued -> running -> success`
- `queued -> running -> skipped`（幂等命中）
- `queued -> running -> failed -> retry(queued)`
- `failed(>=max_retries) -> dead`

## 9. 错误码分层

- `E_TEMP_URL`
- `E_DOWNLOAD`
- `E_PARSE`
- `E_LLM`
- `E_PERSIST`
- `E_BUDGET`

## 10. 验收标准

- 10,000 份全部进入终态（success/skipped/failed/dead）
- `success + skipped >= 97%`
- 关键字段完整率 >= 95%
- 总成本 <= 500 元
- 总时长 <= 48 小时
- 支持按 `employee_id` 精准重跑，且不重复污染已成功数据
