# 前端交付说明

目录：`frontend/`。使用 Node.js 与 npm：`npm install`、`npm run dev`、`npm run typecheck`、`npm test -- --run`、`npm run build`。

开发时 Vite 将 `/api` 代理到 `http://127.0.0.1:8000`；生产环境应由同源反向代理提供 `/api/v1`，或按部署环境修改 Vite/网关配置。模型 API Base 在设置中心配置；完整 API Key 只在浏览器表单中输入，保存后清空，界面仅显示后端掩码。

LIVE 功能调用已注册 API；MOCK 功能由 `src/mocks/` 提供本地演示数据；UNAVAILABLE 功能不发送请求。随 R2-WP03 接入 PubMed 后，应先新增并验收结果列表 API，再将文献检索页的明确 MOCK 边界替换为 LIVE 适配器。
