"""LLM Prompt 模板"""

RESUME_EXTRACTION_PROMPT = """你是一个专业的简历分析专家。请从以下简历文本中提取关键信息,并以 JSON 格式返回。

简历内容:
{resume_text}

请提取以下信息(如果未提及则为 null):
{{
  "name": "姓名",
  "email": "邮箱",
  "phone": "电话",
  "education_level": "最高学历(专科/本科/硕士/博士)",
  "years_of_experience": 5 (工作年限,数字),
  "current_position": "当前职位",
  "summary": "个人简介或职业概况的简短总结",
  "work_experiences": [
    {{
      "company_name": "公司名称",
      "position": "职位",
      "start_date": "开始日期(YYYY-MM格式)",
      "end_date": "结束日期(YYYY-MM格式,若至今则为null)",
      "responsibilities": "工作职责描述(以JSON字符串形式存储)",
      "achievements": "工作成就(可选)"
    }}
  ],
  "project_experiences": [
    {{
      "project_name": "项目名称",
      "role": "担任角色",
      "start_date": "开始日期",
      "end_date": "结束日期",
      "description": "项目描述",
      "responsibilities": ["职责原文1", "职责原文2"],
      "technologies": ["技术1", "技术2"],
      "achievements": ["成果1", "成果2"]
    }}
  ],
  "skills": [
    {{
      "skill_name": "技能名称",
      "proficiency_level": "熟练度(精通/熟练/了解)"
    }}
  ],
  "certifications": ["证书1", "证书2"] (可选),
  "languages": ["语言1", "语言2"] (可选)
}}

注意事项:
1. 只返回 JSON,不要任何解释
2. 确保 JSON 格式正确
3. work_experiences 中的 responsibilities 应该是字符串,不是数组
4. 日期尽量标准化为 YYYY-MM 格式
5. 技能需要评估熟练度
6. project_experiences 中 responsibilities 和 achievements 都尽量保留原始表述，不要改写成抽象总结
7. 如果简历未明确项目成果，achievements 返回空数组，仍需尽量提取 responsibilities
8. 忽略疑似水印/噪声串（如类似 `5e2074214e41d9581HR-...~~` 的随机编码），不要把它们当作技能或经历内容
9. 若原文没有足够信息，不要猜测补全，必须返回 null 或空数组
"""

JD_EXTRACTION_PROMPT = """你是一个专业的招聘专家。请从以下职位描述（JD）文本中提取关键信息，并以 JSON 格式返回。

职位描述内容:
{jd_text}

请提取以下信息（如果未提及则为 null）:
{{
  "title": "职位名称",
  "department": "所属部门",
  "location": "工作地点",
  "min_experience": 0 (最低工作年限，数字，单位年),
  "max_experience": 100 (最高工作年限，数字，单位年),
  "education_requirement": "最低学历要求（大专/本科/硕士/博士/不限）",
  "required_skills": ["技能1", "技能2"],
  "preferred_skills": ["加分技能1", "加分技能2"],
  "description": "整理后的职位描述和职责"
}}

注意事项:
1. 只返回 JSON，不要任何解释
2. 确保 JSON 格式正确
3. 经验年限如果是一个范围（如3-5年），提取最小值和最大值
4. 技能列表只要核心技能 
"""

JD_MATCH_PROMPT = """你是一个专业的人才评估专家。请分析候选人与职位的匹配度。

候选人信息:
{candidate_info}

职位要求:
{job_info}

请进行全面的匹配分析,并以 JSON 格式返回:
{{
  "overall_score": 85 (总体匹配度 0-100),
  "skill_match_score": 90 (技能匹配度 0-100),
  "experience_match_score": 80 (经验匹配度 0-100),
  "education_match_score": 100 (学历匹配度 0-100),
  "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
  "missing_skills": ["Kubernetes", "Redis"],
  "risk_flags": ["频繁跳槽", "工作年限略低于要求"] (潜在风险),
  "summary": "候选人整体匹配度较高...",
  "recommendation": "建议/不建议 录用,理由...",
  "interview_questions": [
    "请描述你在 FastAPI 项目中的技术架构设计经验？",
    "如何处理高并发场景下的数据库优化？"
  ]
}}

评分标准:
- 90-100: 非常匹配
- 75-89: 匹配度高
- 60-74: 基本匹配
- 50-59: 勉强匹配
- <50: 不匹配

注意:
1. 只返回 JSON,不要解释
2. 评分客观公正
3. 风险标识要具体
4. 面试问题要有针对性
"""

RISK_ANALYSIS_PROMPT = """你是一个专业的背景调查专家。请分析候选人的潜在风险。

候选人信息:
{candidate_info}

工作经历:
{work_experiences}

请识别以下风险并以 JSON 格式返回:
{{
  "risk_flags": [
    "频繁跳槽(1年内更换3次工作)",
    "工作空档期(2020年6月-2021年3月)",
    "职位title倒退",
    "行业跨度过大"
  ]
}}

风险类别:
- 稳定性: 跳槽频率、空档期
- 真实性: 职位title不匹配、经历重复
- 发展性: 职位倒退、能力停滞

注意:
1. 只返回 JSON
2. 风险要具体,包含时间/次数
3. 没有风险则返回空数组
"""

RESUME_SUMMARY_PROMPT = """请为以下简历生成一段简洁的职业概况摘要(100字以内):

{resume_text}

摘要应包含:
1. 当前职位和年限
2. 核心技能
3. 主要成就

请直接返回摘要文本,不需要任何格式标记。
"""
