# LitFlow 使用与维护手册

## 1. 项目定位

LitFlow 是一个本地运行的科研文献自动化工作台，用于帮助研究者从检索、筛选、下载合法开放 PDF、解析、结构化提取、问答、导出，到长期积累研究方向资料。

它当前支持多源文献检索、Search Campaign、文献保存与去重、venue/rank 识别、Scoring Engine v3、Topics/Tags、PDF resolve/download/manual URL、PDF parse/chunking、LLM structured extraction、单篇 RAG、跨文献库 RAG、assets extraction、Markdown/BibTeX export、Save to Library workspace、Batch Process Selected、Refresh Enrichment、Delete Paper、Reset Library、Vue dashboard、FastAPI backend 和 SQLite 本地存储。

LitFlow 不是简单爬虫。它不会绕过 paywall、登录、验证码或版权限制，只处理合法 open-access PDF 来源。

LitFlow 也不是 Zotero 的直接替代品。它更像一个面向研究方向积累的自动化工作台：把候选文献发现、质量初筛、结构化阅读、RAG 问答、Markdown 笔记和本地文献包串成一个流程。Zotero 更适合通用引用管理和浏览器收藏；LitFlow 更强调可编程、可批处理、可导出、可被 LLM 接手的研究流水线。

## 2. 核心科研工作流

推荐主流程：

```text
Search / Campaign
  -> Save Selected
  -> Topic 标注
  -> Batch Process / Process Paper
  -> PDF resolve / download / parse / chunking
  -> LLM Extraction
  -> Ask Paper / Ask Library
  -> Extract Assets
  -> Save to Library
  -> Markdown / BibTeX
  -> Research Memo
```

典型使用方式：

1. 用 Search 或 Search Campaign 发现候选论文。
2. 只保存值得进入本地库的论文，避免文献库膨胀。
3. 给论文标注 Topics，例如 `AI Systems / Inference Systems`。
4. 对选中论文运行 Process Paper 或 Batch Process。
5. 让系统下载合法 PDF、解析文本、切分 chunks，并执行 LLM structured extraction。
6. 用 Ask Paper 追问单篇论文，用 Ask Library 汇总整个方向。
7. 对重要论文提取 assets，保存 workspace，导出 Markdown/BibTeX。
8. 在 Markdown 笔记基础上整理 research memo、survey outline 或实验计划。

## 3. 推荐使用场景

LitFlow 当前适合以下场景：

- AI Systems / Inference Systems 文献积累：检索推理系统、Serving、KV Cache、调度、压缩、推理加速等方向。
- Trustworthy AI Systems 文献积累：检索安全、对齐、评估、红队、可靠性、治理和系统化保障相关论文。
- Scientific ML / AI for Science：积累科学机器学习、AI for Science、仿真、分子、气候、材料等方向论文。
- Embodied AI / World Models：积累具身智能、世界模型、机器人、规划和多模态环境建模文献。
- Mechanistic Interpretability：积累 circuits、SAE、representation、causal tracing 等机制解释文献。
- 单篇论文精读：解析 PDF、生成结构化摘要、追问方法细节、导出 Markdown 笔记。
- 跨论文综述总结：按 topic 过滤后用 Ask Library 汇总共同方法、瓶颈、趋势和开放问题。

## 4. 项目目录结构

主要目录：

```text
backend/                 FastAPI 后端、数据库模型、服务逻辑、API 路由
frontend/                Vue + Vite 前端 dashboard
storage/                 本地运行数据目录
storage/pdfs/            下载后的 PDF 运行产物
storage/assets/          提取出的 page image、caption、table 等运行产物
storage/library/         Save to Library 生成的本地文献包
storage/rankings/        venue/rank seed CSV，可维护、可提交
docs/                    项目说明文档
scripts/                 维护脚本，例如 reset_litflow_library.py
```

建议提交到 Git：

- `backend/`
- `frontend/src/`
- `frontend/package.json`、`frontend/package-lock.json`、配置文件
- `storage/rankings/` 中的 ranking seed CSV 和 alias 数据
- `docs/`
- `scripts/`
- `README.md`
- `start-litflow.bat`、`stop-litflow.bat`
- `.gitignore`

不应该提交到 Git：

- `.env`
- SQLite 数据库文件，例如 `*.db`
- Python 虚拟环境 `.venv/`
- `node_modules/`
- `frontend/dist/`
- `storage/pdfs/`
- `storage/assets/`
- `storage/library/`
- `__pycache__/`

## 5. 启动方式

一键启动：

```bat
start-litflow.bat
```

该脚本会分别启动后端和前端窗口。

常用地址：

- 后端 API 文档：`http://127.0.0.1:8000/docs`
- 前端 Dashboard：`http://localhost:5173`

手动启动后端：

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

手动启动前端：

```bat
cd frontend
npm install
npm run dev
```

停止服务：

```bat
stop-litflow.bat
```

也可以直接关闭后端和前端终端窗口。

## 6. 环境变量

项目根目录或后端目录可放置 `.env`。不要提交 `.env`。

常用变量：

```text
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4.1-mini
S2_API_KEY=your_semantic_scholar_api_key
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_api_key
UNPAYWALL_EMAIL=your_email@example.com
```

说明：

- `OPENAI_API_KEY`：openai 模式的 LLM extraction 和 RAG answer synthesis 需要。
- `LLM_MODEL`：可选，未设置时使用代码默认模型。
- `S2_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY`：Semantic Scholar 搜索使用。具体环境变量名以当前代码读取为准；保留两种命名便于未来兼容。
- `UNPAYWALL_EMAIL`：Unpaywall 查询需要，建议填写真实邮箱。

## 7. 前端操作指南

### Search candidate papers

在顶部 Search 面板输入关键词和 limit，点击 `Search`。系统会聚合 Semantic Scholar、OpenAlex、arXiv 等来源，返回候选论文。结果区支持展开/收起，便于一次查看多篇论文。

### Search Campaign

Campaign 是预置研究方向的 query expansion。选择 campaign 后点击 `Run Campaign`，系统会运行多条 curated queries，合并候选结果并按分数排序。它适合从一个研究方向批量发现论文。

### Save Selected

Search 和 Campaign 结果都支持勾选论文后 `Save Selected`。保存时会进行去重，避免同一 DOI 或同一 normalized title 重复进入 Library。

### Library filters

左侧 FilterSidebar 用于按 stage、capability、priority、year、topic 等过滤当前 Library。它只影响前端展示，不删除数据。

### PaperTable

中间 PaperTable 展示保存后的本地文献库。点击某行可在右侧打开 PaperDetailPanel。表格支持排序、筛选后的展示，以及 Batch Mode 选择。

### PaperDetailPanel

右侧 PaperDetailPanel 是单篇论文的操作中心，展示 metadata、rank & score、topics、actions、PDF preview、assets、extraction summary、workspace 和 markdown preview。

### Batch Mode

点击 `Enter Batch Mode` 后可勾选多篇论文。Batch Process 会对选中论文运行同一套处理流程。当前批处理适合少量论文，不建议一次处理过多，以免 API quota 或下载失败。

### Process Paper

`Process Paper` 是单篇一键流程。它可以 resolve PDF、download PDF、parse PDF、extract，并根据当前 Extraction Mode 使用 mock 或 openai。

### Manual PDF URL

当自动 resolve-pdf 找不到合法 PDF，但用户知道合法 open-access PDF 地址时，可在 PaperDetailPanel 的 `Manual PDF URL` 区域手动保存 `pdf_url`。保存后再点击 `Download PDF`、`Parse PDF` 或 `Process Paper`。

仅使用合法开放来源，例如 arXiv、OpenReview、official proceedings、author homepage、institutional repository。不要使用非法来源，不要绕过 paywall。

### Delete Paper

PaperDetailPanel 中的 `Danger Zone` 支持删除论文。默认只删除数据库记录；如果勾选 `Also delete local files`，后端会尝试删除相关本地 PDF、assets、workspace。删除前会二次确认。

### Refresh Rank & Score

`Refresh Rank & Score` 会刷新单篇论文的 enrichment 展示，包括 venue normalized、rank、score 等。顶部也有 `Refresh All Rankings` 用于批量刷新展示。

### Extract Assets

`Extract Assets` 会从已下载 PDF 中提取 page images、figure captions、table captions 或 table text 等当前支持的 assets。它是 MVP 能力，不等于完整 OCR 或精确图表理解。

### Save to Library

`Save to Library` 会在 `storage/library/` 下生成本地文献包，包括 PDF、Markdown note、BibTeX、metadata 和 assets 目录。

### Export Markdown / BibTeX

`Export Markdown` 和 `Export BibTeX` 会通过浏览器下载文件，适合把单篇笔记或引用导出到外部目录。

### Ask Paper

Ask Paper 用于追问当前选中论文。它依赖该论文已经 parse PDF 并生成 PaperChunk。没有 chunks 时通常没有 evidence。

### Ask Library

Ask Library 用于向整个文献库提问，可选择 topic 过滤。它适合问综述型问题，例如“这个方向主要瓶颈是什么”“常见方法有哪些”“哪些论文讨论了 KV cache”。

## 8. 后端主要接口

### Search

- `GET /search/all`：聚合多源搜索候选论文。
- `POST /search/save-selected`：保存前端选中的候选论文。
- `GET /search/campaigns`：获取预置 Search Campaign 列表。
- `POST /search/campaigns/run`：运行指定 campaign，返回合并后的候选论文。

### Papers

- `GET /papers/enriched`：读取本地库论文，并计算展示用 enrichment 字段。
- `POST /papers/{id}/process`：单篇论文一键处理流程。
- `POST /papers/process-batch`：批量处理选中论文。
- `PATCH /papers/{id}`：更新论文 metadata，例如 title、venue、pdf_url 等。
- `DELETE /papers/{id}`：删除论文记录，可配合参数删除本地文件。
- `POST /papers/{id}/refresh-enrichment`：刷新单篇 enrichment 展示。
- `POST /papers/refresh-enrichment-batch`：批量刷新 enrichment 展示。

### PDF / extraction

- `POST /papers/{id}/resolve-pdf`：尝试解析合法 open-access PDF URL。
- `POST /papers/{id}/download-pdf`：下载合法 PDF 到 `storage/pdfs/`。
- `POST /papers/{id}/parse-pdf`：解析 PDF 文本并生成 chunks。
- `POST /papers/{id}/extract`：运行 mock 或 openai structured extraction。
- `POST /papers/{id}/extract-assets`：提取 PDF assets。

### RAG

- `POST /papers/{id}/ask`：单篇论文问答。
- `POST /ask/library`：跨文献库问答，可按 topic 过滤。

### Topics

- `GET /topics`：读取 topic 列表。
- `POST /topics/seed-defaults`：创建默认 topics。
- `PUT /papers/{id}/topics`：设置某篇论文的 topic 标签。

### Export

- `GET /papers/{id}/export/markdown`：导出 Markdown。
- `GET /papers/{id}/export/bibtex`：导出 BibTeX。
- `POST /papers/{id}/save-workspace`：保存本地文献 workspace。

## 9. 数据库与数据模型说明

主要表：

- `Paper`：论文主表。保存 title、doi、year、venue、abstract、citation_count、pdf_url、local_pdf_path、status 等字段。大部分基础 metadata 来自搜索源，也可人工更新。
- `PaperText`：保存从 PDF 解析出的全文文本。
- `PaperChunk`：保存按 chunk 切分后的文本片段，是 RAG 和 LLM extraction 的基础 evidence。
- `Extraction`：保存 LLM structured extraction 的 JSON、raw LLM output、模型名、prompt version 等。
- `PaperAsset`：保存 PDF assets metadata，例如 page image、figure caption、table caption、table text、本地路径等。
- `Author` / `PaperAuthor`：保存作者和论文作者关联，用于去重和展示。
- `ResearchTopic` / `PaperTopic`：保存 research topic 以及论文和 topic 的多对多关系。

字段来源：

- 搜索源字段：title、authors、doi、year、venue、abstract、citation_count、open-access PDF URL、source 等。
- 本地处理字段：local_pdf_path、status、PaperText、PaperChunk、Extraction、PaperAsset、workspace 路径等。
- 展示计算字段：venue_normalized、rank_value、rank_source、final_score 等 enrichment 字段通常在读取时计算或刷新，不应被视为绝对事实。

## 10. Ranking 与 Scoring 机制

LitFlow 当前支持本地 venue/rank 识别：

- conference ranking CSV：位于 `storage/rankings/`，采用 CORE-style rank，例如 `A*`、`A`、`B`、`C`、`Unranked`、`Unknown`。
- journal ranking CSV：位于 `storage/rankings/`，当前是 seed 数据，可扩展为 SCImago/JCR 风格 quartile。
- aliases：用于把会议缩写、全称、常见别名归一化。
- `venue_normalized`：归一化后的 venue 名称。
- `rank_value`：展示用 rank。
- `rank_source`：rank 来源，例如本地 CSV、fallback 或 ready 状态。

Scoring Engine v3 主要字段：

- `relevance_score`：与查询或研究主题的相关度。
- `authority_score`：引用、venue、来源等权威信号。
- `foundation_score`：基础性、经典性或长期价值。
- `implementation_score`：系统实现、工程可复现、实现细节相关信号。
- `survey_value_score`：survey、benchmark、taxonomy、evaluation 等综述价值信号。
- `frontier_score`：近期性、前沿性、新方向信号。
- `accessibility_score`：开放 PDF、可获取性等信号。
- `final_score`：综合分数，用于排序和筛选。

这些分数是辅助筛选工具，不是绝对学术评价。高分论文不一定必须精读，低分论文也可能对特定研究问题很重要。

## 11. 文献质量判断规则

前端 Literature Quality Board 会把论文分为：

- `Must Read`：强相关、高价值或高权威论文。建议优先精读、做笔记、追踪引用。
- `High Priority`：值得认真阅读，但优先级略低于 Must Read。适合进入近期阅读列表。
- `Frontier Watch`：新近、前沿、可能引用较低但方向相关。建议关注后续版本、代码和引用增长。
- `Skim`：可以快速浏览摘要、方法和结论，必要时再深入。
- `Archive`：暂时归档。保留记录但不投入阅读时间，除非后续研究问题需要。

这些标签是前端根据 rank、score、year、publication status 等信号计算的阅读建议，不是论文质量的最终判断。

## 12. PDF 失败时怎么办

`resolve-pdf` 失败不代表论文不可读，也不代表论文没有合法 PDF。它只表示当前自动 resolver 没有找到可用的合法 open-access PDF。

建议顺序：

1. 查看论文 DOI、标题、venue、作者主页。
2. 优先搜索 arXiv、OpenReview、official proceedings、author homepage、institutional repository。
3. 找到合法 PDF 或合法可重定向到 PDF 的 URL。
4. 在前端 `Manual PDF URL` 保存。
5. 再执行 `Download PDF`、`Parse PDF` 或 `Process Paper`。

不要使用盗版论文站点，不要绕过 paywall、登录、验证码或版权限制。

## 13. RAG 使用说明

### Single-paper RAG

Single-paper RAG 面向一篇论文。适合问：

- 这篇论文的核心方法是什么？
- 实验设置有哪些？
- 作者声称的贡献是什么？
- 方法限制在哪里？

它依赖该论文已经执行 PDF parse 并生成 PaperChunk。没有 chunks 时没有可检索 evidence。

### Library RAG

Library RAG 面向整个本地文献库。适合问：

- 某个方向的主要技术路线有哪些？
- 多篇论文共同指出的瓶颈是什么？
- 哪些论文讨论了某个系统组件？
- 某个 topic 下有哪些值得读的工作？

Library RAG 支持按 topic 过滤。它同样依赖 PaperChunk；未解析 PDF 的论文不会贡献正文 evidence。

### mock / openai 模式

- `mock`：用于本地流程测试，不调用外部 LLM，回答或 extraction 是占位性质。
- `openai`：调用 OpenAI API，需要 `OPENAI_API_KEY`，可能消耗 quota。

## 14. Save to Library 说明

`Save to Library` 会在项目本地生成文献包：

```text
storage/library/{paper_id-year-title}/
  paper.pdf
  note.md
  citation.bib
  metadata.json
  assets/
```

说明：

- `paper.pdf`：本地 PDF 副本，若已下载。
- `note.md`：Markdown 文献笔记，包含 metadata 和 structured extraction。
- `citation.bib`：BibTeX 引用。
- `metadata.json`：机器可读 metadata。
- `assets/`：与该论文相关的图片、caption、table 等 assets。

`Export Markdown` 和 `Save to Library` 的区别：

- `Export Markdown`：通过浏览器下载单个 `.md` 文件到浏览器默认下载目录。
- `Save to Library`：在项目内 `storage/library/` 保存完整本地文献包，适合长期归档和后续自动化处理。

## 15. Reset Library 维护脚本

预览将要清理的内容：

```bat
python scripts/reset_litflow_library.py --dry-run
```

执行清理：

```bat
python scripts/reset_litflow_library.py
```

该脚本用于清理开发或测试过程中的本地文献库数据。它会清空 paper 相关数据、PDF、assets、library workspace 等运行产物。根据当前实现，它会保留代码、`.env`、README、docs、rankings CSV，并默认保留 research topics。

执行真实清理前请确认 dry-run 输出，并按脚本提示输入确认文本。

## 16. 常见问题与排查

### Semantic Scholar 429

表示请求过多或触发限流。减少 limit，稍后重试，或配置 Semantic Scholar API key。批量 campaign 搜索更容易触发限流。

### OpenAI quota insufficient

表示 OpenAI API quota 不足或 key 不可用。检查 `.env` 中的 `OPENAI_API_KEY`，确认账户余额和模型权限。临时可切换到 `mock` 模式验证本地流程。

### LLM JSON schema mismatch

LLM extraction 要求返回符合 `LiteratureExtraction` schema 的 JSON。当前代码已经对常见 list/string 类型偏差做 normalization，但如果仍失败，查看错误中的字段名和 raw JSON preview，定位 prompt 或 schema 差异。

### No legal open-access PDF found

自动 resolver 没找到合法 PDF。请使用 arXiv、OpenReview、official proceedings、author homepage 或 institutional repository 中的合法 PDF URL，并通过 Manual PDF URL 保存。

### rank Unknown / Unranked

说明 venue 未被本地 ranking CSV 或 fallback mapping 识别。可以维护 `storage/rankings/` 中的 CSV 和 aliases，然后刷新 enrichment。

### 已保存旧论文 ranking 没更新

点击单篇 `Refresh Rank & Score`，或顶部 `Refresh All Rankings`。LitFlow 的 enrichment 主要用于展示，更新 ranking CSV 后需要刷新读取结果。

### 前端看不到更新

先点击刷新 Library 或触发对应操作后的 refresh。若仍无变化，确认后端是否启动、浏览器请求是否报错、数据库是否写入成功。

### Batch Process 某些论文 failed

批处理中单篇失败通常不影响其他论文。检查返回的 step message，常见原因包括无合法 PDF、下载失败、parse 失败、OpenAI quota、LLM schema 问题。

### Ask Library 没有 evidence

Library RAG 依赖 PaperChunk。请先对相关论文执行 Download PDF 和 Parse PDF。若按 topic 过滤，确认论文确实标注了该 topic。

## 17. 如何让其他 LLM / Codex 接手项目

如果要让其他模型修改 LitFlow，请先让它阅读：

```text
README.md
docs/LITFLOW_MANUAL.md
```

然后明确告诉它：

- 不要提交 `.env`。
- 不要提交 `storage/pdfs/`、`storage/assets/`、`storage/library/` 等运行产物。
- 不要随意修改数据库模型；如果必须改 schema，要说明迁移策略。
- 修改前先看 `git status`，不要覆盖用户未提交改动。
- 每个功能单独 commit，避免把不相关改动混在一起。
- 后端改动后运行 `python -m compileall backend/app`。
- 前端改动后运行 `cd frontend && npm run build`。
- 不要绕过版权限制，不要实现非法下载。
- 不要把 mock 功能描述成真实 LLM 能力。

## 18. GitHub 发布前检查清单

发布前建议检查：

- `git status` clean。
- `.env` 不在 Git。
- SQLite 数据库文件不在 Git。
- `storage/pdfs/`、`storage/assets/`、`storage/library/` 不在 Git。
- `README.md` 完整。
- `docs/LITFLOW_MANUAL.md` 存在。
- `backend/requirements.txt` 存在。
- `frontend/package.json` 存在。
- `start-litflow.bat` 存在。
- `scripts/reset_litflow_library.py` 存在。
- 后端可通过 `python -m compileall backend/app`。
- 前端可通过 `npm run build`。
- 后端 API docs 可打开：`http://127.0.0.1:8000/docs`。
- 前端 dashboard 可打开：`http://localhost:5173`。

## 19. 后续扩展路线

可选扩展方向：

- 更完整的 SCImago/JCR journal import：导入授权或公开可用的 journal ranking 数据。
- Zotero integration：和 Zotero collection、Better BibTeX、PDF library 同步。
- embedding RAG：引入向量数据库或本地 embedding，提升跨论文语义检索。
- citation graph expansion：基于引用和被引网络扩展候选论文。
- Search Campaign 自动保存策略：为高置信候选设置可配置自动保存规则。
- paper recommendation：基于 topics、阅读优先级、已保存论文相似性推荐下一批论文。
- research memo generator：把 Library RAG 和 Markdown exports 汇总成研究备忘录或 survey draft。
- Electron desktop version：把当前本地前后端封装成桌面应用。

