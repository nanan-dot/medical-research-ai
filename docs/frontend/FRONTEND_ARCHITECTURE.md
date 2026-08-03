# 前端架构

Vue 3、TypeScript、Vue Router 与 Vitest 构成前端。`layouts/AppShell.vue` 提供导航、顶部栏、移动端抽屉、上下文栏及跳过链接；`config/features.ts` 是路由状态的唯一目录。

`api/` 只封装已验证的 REST 接口；`mocks/` 只服务 MOCK 原型；`types/` 定义跨组件契约；`components/` 封装复用区块；`views/` 是路由组合层。路由采用动态 import 分块加载，避免初始包包含全部业务页面。

页面必须显示 LIVE、MOCK 或 UNAVAILABLE 边界。不得将本地原型、模型推断或缺失信息伪装为论文事实、运行结果或医学结论。
