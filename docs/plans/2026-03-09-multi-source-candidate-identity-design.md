# Multi-Source Candidate Identity Design

## Goal

让 `candidates` 支持同时挂接多种业务来源标识，并把现有仅支持 `employee_id` 的 URL/Celery 结构化链路升级为统一的 `source_type + source_id` 模式，先覆盖在职员工和报备候选人两类来源。

## Scope

1. `candidates` 新增 `employee_id / entrant_id / submit_candidate_id`。
2. 候选人定位策略统一为：外部来源 ID 优先，`phone/email` 兜底。
3. 同步 API 和 Celery 内部任务统一使用 `source_type + source_id + resume_created_time`。
4. 保留旧的 `structure-from-employee` 接口作为兼容层。
5. `ResumeSourceClient` 支持按来源类型获取临时 URL 和分页拉取待处理简历。

## Data Model

### candidates

新增可空字段：

- `employee_id`
- `entrant_id`
- `submit_candidate_id`

设计原则：

1. 三个字段允许同时存在。
2. 仅建立索引，不加唯一约束，避免历史脏数据或业务流转导致写入失败。
3. 命中已有候选人时，回填本次来源 ID。

### batch/deadletter governance tables

治理表从仅记录 `employee_id` 升级为记录：

- `source_type`
- `source_id`
- `resume_created_time`

原因：Celery 批处理后续要同时支持 `employee` 和 `submit_candidate`，继续复用 `employee_id` 会让内部语义失真。

## Source Abstraction

统一来源模型：

```json
{
  "source_type": "employee | submit_candidate | entrant",
  "source_id": "业务主键",
  "resume_created_time": "2026-03-09T10:00:00"
}
```

本次先跑通：

- `employee`
- `submit_candidate`

`entrant` 这次只把字段和定位逻辑铺好，批处理入口后续再接。

## Source API Contract

### 获取临时简历 URL

- 在职员工：`GET /employees/{source_id}/resume/temp-url`
- 报备候选人：`GET /submit-candidates/{source_id}/resume/temp-url`

响应至少包含：

```json
{
  "temp_url": "https://cdn.example.com/resume.pdf"
}
```

可选返回：

```json
{
  "temp_url": "https://cdn.example.com/resume.pdf",
  "expires_at": "2026-03-09T12:30:00+08:00"
}
```

### 分页拉取待处理简历

统一为：

`GET /resumes/pending?source_type=employee|submit_candidate&cursor=...&limit=...`

返回：

```json
{
  "items": [
    {
      "source_type": "employee",
      "source_id": "E001",
      "resume_created_time": "2026-03-09T10:00:00"
    }
  ],
  "next_cursor": "abc123"
}
```

## Matching Strategy

结构化落库时按以下顺序定位候选人：

1. `employee_id`
2. `entrant_id`
3. `submit_candidate_id`
4. `phone`
5. `email`

命中后：

1. 回填缺失的来源字段。
2. 更新结构化字段和明细表。
3. 保留多个来源 ID 共存。

## API Design

### 保留兼容接口

- `POST /api/v1/resumes/structure-from-employee`

内部转换为：

```json
{
  "source_type": "employee",
  "source_id": "E001",
  "resume_created_time": "..."
}
```

### 新增通用接口

- `POST /api/v1/resumes/structure-from-source`

请求：

```json
{
  "source_type": "employee",
  "source_id": "E001",
  "resume_created_time": "2026-03-09T10:00:00"
}
```

或：

```json
{
  "source_type": "submit_candidate",
  "source_id": "S001",
  "resume_created_time": "2026-03-09T10:00:00"
}
```

## Celery Changes

内部链路统一改成：

- `dispatch(source_type, source_id, resume_created_time)`
- `extract(source_type, source_id, resume_created_time)`
- `llm(...)`
- `persist(...)`
- `deadletter(...)`

这样：

1. 调度层不再把报备候选人伪装成员工。
2. 403 刷新临时 URL 时也能按来源类型重新取链接。
3. 批处理脚本可按来源类型分别跑。

## Testing

至少补齐以下验证：

1. 候选人模型与 schema 能读写新的来源字段。
2. `ResumeSourceClient` 能按 `source_type` 调不同 URL。
3. `PersistService` 能按来源 ID 命中已有候选人，并按 `phone/email` 兜底。
4. `URLStructuringService` 能处理 `submit_candidate` 来源。
5. API 新通用接口可用，旧员工接口仍兼容。
6. Celery/pipeline payload 已升级为 `source_type/source_id`。
