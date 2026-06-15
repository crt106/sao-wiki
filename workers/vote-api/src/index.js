const ALLOWED_ORIGINS = new Set([
  "https://crt106.github.io",
  "http://127.0.0.1:8000",
  "http://localhost:8000",
  "http://127.0.0.1:8123",
  "http://localhost:8123"
]);

const HERO_SLUGS = new Set([
  "⑨_琪露诺",
  "爱丽丝",
  "爱弥斯",
  "暗黑红美玲",
  "暗杀者",
  "白雪公主_White_Trailer",
  "穿越时空的少女_椎名真白",
  "冬_夜刀神十香",
  "冬弥_泳装形态",
  "封弊者_桐谷和人_桐人",
  "芙兰朵露_斯卡雷特",
  "葛林瑟鲁妲",
  "公会命运之夜_CD",
  "孤独轮回观测者_祸灵梦",
  "黑猫酱_五更琉璃",
  "红叶",
  "黄泉",
  "加速世界_黑雪姬",
  "谏山黄泉",
  "结衣",
  "绝剑_优纪",
  "克萝伊_莉莉丝忒拉",
  "雷电_忘川守_芽衣_刺客",
  "蕾米莉亚_斯卡雷特",
  "莉奈娅",
  "莉伊",
  "魅影十字军",
  "梦梦_贝莉雅_戴比路克",
  "喵可莉",
  "喵露朵露薇",
  "魔法战争_相羽六",
  "魔女",
  "哦尼酱_二",
  "哦尼酱_一",
  "琪尔玛利亚_M_R",
  "穹_冬弥",
  "杀生丸",
  "闪光_亚丝娜",
  "时崎狂三",
  "水月",
  "斯托蕾亚_魔方",
  "特莉波卡",
  "缇娜",
  "天堂",
  "筒隐月子",
  "娃娃_Saber",
  "未来初音",
  "五河琴里",
  "星川凌云",
  "兄控万岁_莉法",
  "驯兽师_西莉卡",
  "一皇",
  "优库里伍德",
  "御坂美琴",
  "朱雀院椿",
  "灼眼的夏娜"
]);

const MAX_VOTES_PER_VOTER = 8;

function corsHeaders(request) {
  const origin = request.headers.get("origin") || "";
  const allowOrigin = ALLOWED_ORIGINS.has(origin) ? origin : "https://crt106.github.io";
  return {
    "access-control-allow-origin": allowOrigin,
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type",
    "access-control-max-age": "86400",
    "vary": "Origin"
  };
}

function json(request, data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...corsHeaders(request),
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function voterHash(request, env) {
  const proxySecret = request.headers.get("x-sao-wiki-proxy-secret") || "";
  const forwardedFor = request.headers.get("x-forwarded-for") || "";
  const trustedProxy = env.PROXY_SECRET && proxySecret === env.PROXY_SECRET;
  const ip = trustedProxy && forwardedFor
    ? forwardedFor.split(",")[0].trim()
    : (request.headers.get("cf-connecting-ip") || "unknown");
  const ua = request.headers.get("user-agent") || "unknown";
  const salt = env.VOTE_SALT || "dev-only-change-me";
  return sha256(`${ip}|${ua}|${salt}`);
}

function validPoll(poll) {
  return typeof poll === "string" && /^[a-z0-9-]{3,48}$/.test(poll);
}

async function readResults(env, poll, voter) {
  const totals = await env.DB.prepare(
    "SELECT hero_slug AS hero, votes FROM vote_totals WHERE poll_id = ? ORDER BY votes DESC, hero_slug ASC"
  ).bind(poll).all();

  const votedRows = await env.DB.prepare(
    "SELECT hero_slug AS hero FROM vote_events WHERE poll_id = ? AND voter_hash = ?"
  ).bind(poll, voter).all();

  return {
    poll,
    results: totals.results || [],
    voted: (votedRows.results || []).map((row) => row.hero)
  };
}

async function handleGet(request, env) {
  const url = new URL(request.url);
  const poll = url.searchParams.get("poll") || "balance-2026-06";
  if (!validPoll(poll)) return json(request, { error: "invalid_poll" }, 400);
  const voter = await voterHash(request, env);
  return json(request, await readResults(env, poll, voter));
}

async function handlePost(request, env) {
  let body;
  try {
    body = await request.json();
  } catch (err) {
    return json(request, { error: "invalid_json" }, 400);
  }

  const poll = body.poll || "balance-2026-06";
  const hero = body.hero;
  if (!validPoll(poll)) return json(request, { error: "invalid_poll" }, 400);
  if (!HERO_SLUGS.has(hero)) return json(request, { error: "invalid_hero" }, 400);

  const voter = await voterHash(request, env);
  const existingVote = await env.DB.prepare(
    "SELECT id FROM vote_events WHERE poll_id = ? AND hero_slug = ? AND voter_hash = ? LIMIT 1"
  ).bind(poll, hero, voter).first();
  if (existingVote) {
    const payload = await readResults(env, poll, voter);
    payload.accepted = false;
    payload.error = "already_voted";
    return json(request, payload);
  }

  const voterCount = await env.DB.prepare(
    "SELECT COUNT(*) AS count FROM vote_events WHERE poll_id = ? AND voter_hash = ?"
  ).bind(poll, voter).first();
  if (Number(voterCount?.count || 0) >= MAX_VOTES_PER_VOTER) {
    const payload = await readResults(env, poll, voter);
    payload.accepted = false;
    payload.error = "vote_limit_reached";
    return json(request, payload, 429);
  }

  const inserted = await env.DB.prepare(
    "INSERT OR IGNORE INTO vote_events (poll_id, hero_slug, voter_hash) VALUES (?, ?, ?)"
  ).bind(poll, hero, voter).run();

  if (inserted.meta.changes > 0) {
    await env.DB.prepare(
      [
        "INSERT INTO vote_totals (poll_id, hero_slug, votes, updated_at)",
        "VALUES (?, ?, 1, CURRENT_TIMESTAMP)",
        "ON CONFLICT(poll_id, hero_slug) DO UPDATE SET",
        "votes = votes + 1, updated_at = CURRENT_TIMESTAMP"
      ].join(" ")
    ).bind(poll, hero).run();
  }

  const payload = await readResults(env, poll, voter);
  payload.accepted = inserted.meta.changes > 0;
  return json(request, payload);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    if (url.pathname === "/api/votes" && request.method === "GET") {
      return handleGet(request, env);
    }

    if (url.pathname === "/api/votes" && request.method === "POST") {
      return handlePost(request, env);
    }

    return json(request, { error: "not_found" }, 404);
  }
};
