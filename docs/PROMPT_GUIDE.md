这是我的 LitFlow 项目，一个本地运行的科研文献自动化工作台。
请先阅读 README.md 和 docs/LITFLOW_MANUAL.md。
修改前请先判断当前模块：frontend / backend / ranking / RAG / extraction / export。
不要提交 .env、storage/pdfs、storage/assets、storage/library。
每次只做一个功能，小步修改。
后端修改后运行 python -m compileall backend/app。
前端修改后运行 cd frontend && npm run build。