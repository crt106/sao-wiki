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

6. 部署 Worker：

   ```powershell
   wrangler deploy
   ```

7. 将 `docs/vote/index.md` 中 `data-api-base` 改为 Worker 地址，例如：

   ```html
   <div id="hero-vote-app" data-poll-id="balance-2026-06" data-api-base="https://sao-wiki-vote-api.xxx.workers.dev"></div>
   ```

## 接口

- `GET /api/votes?poll=balance-2026-06`
- `POST /api/votes`，JSON body：`{"poll":"balance-2026-06","hero":"爱弥斯"}`

每个访问者对同一个英雄只能投一次。访问者标识使用 `IP + User-Agent + VOTE_SALT` 哈希，不保存明文 IP。
