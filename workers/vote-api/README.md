# 英雄投票 API

Cloudflare Worker + D1 后端，用于 `docs/vote/index.md` 的英雄加强投票页面。

## 部署步骤

1. 安装 Wrangler 并登录：

   ```powershell
   npm install -g wrangler
   wrangler login
   ```

2. 创建 D1 数据库：

   ```powershell
   wrangler d1 create sao-wiki-votes
   ```

3. 复制配置文件并填入 `database_id`：

   ```powershell
   Copy-Item wrangler.example.toml wrangler.toml
   ```

4. 初始化表结构：

   ```powershell
   wrangler d1 execute sao-wiki-votes --file=./schema.sql
   ```

5. 设置匿名投票盐值：

   ```powershell
   wrangler secret put VOTE_SALT
   ```

   如果投票页通过自建服务器反代访问 Worker，再设置一个反代密钥：

   ```powershell
   wrangler secret put PROXY_SECRET
   ```

   Nginx 反代到 Worker 时同步发送：

   ```nginx
   proxy_set_header X-Forwarded-For $remote_addr;
   proxy_set_header X-Sao-Wiki-Proxy-Secret "同一个 PROXY_SECRET";
   ```

   Worker 只有在密钥匹配时才信任 `X-Forwarded-For`，否则使用 Cloudflare 提供的 `cf-connecting-ip`。这样 GitHub Pages 直连 Worker 和自建服务器反代两种场景都能正确按访客去重。

6. 部署 Worker：

   ```powershell
   wrangler deploy
   ```

7. 将 `docs/vote/index.md` 中 `data-api-base` 改为 Worker 地址，例如：

   ```html
   <div id="hero-vote-app" data-poll-id="balance-2026-06" data-api-base="https://sao-wiki-vote-api.xxx.workers.dev"></div>
   ```

## 自建站点注意事项

投票页的 CSS/JS 都是站内本地静态资源，不依赖第三方 CDN。外部依赖只有 `data-api-base` 指向的投票 API。

如果 Wiki 部署在自建服务器或大陆网络环境：

1. `*.workers.dev` 可能不可达或很慢，建议把本 Worker 改部署到自有域名，或把同等接口部署到自建服务器。
2. 若继续使用 Cloudflare Worker，需要在 `src/index.js` 的 `ALLOWED_ORIGINS` 中加入自建站点 origin，例如 `https://wiki.example.com`。
3. 若投票 API 与 Wiki 同域，可把 `data-api-base` 改成同源前缀，例如 `/vote-api`，再由 Nginx 反代到真实 API。
4. 前端会先渲染英雄卡片，再异步拉取票数；API 不可用时页面仍可打开，只是会显示结果加载失败。

## 接口

- `GET /api/votes?poll=balance-2026-06`
- `POST /api/votes`，JSON body：`{"poll":"balance-2026-06","hero":"爱弥斯"}`

每个访问者对同一个英雄只能投一次。访问者标识使用 `IP + User-Agent + VOTE_SALT` 哈希，不保存明文 IP。
