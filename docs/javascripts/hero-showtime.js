/**
 * Hero Showtime 演出引擎 v2 ——「二游抽卡」风格全屏演出
 * ────────────────────────────────────────────────────────────
 * 触发条件：HTML 中存在 <meta name="hero-id" content="...">
 *
 * 通用时间轴（每个英雄都共享）：
 *   0ms      暗场幕布 warmup + 电影黑边 letterbox 滑入 + 暗角 vignette
 *   0~聚能   Canvas 流光从四周加速汇聚中心 + 能量核心增亮 + 收缩光环
 *   爆发     竖直光柱 + 放射光芒 + 白闪 + RGB 色散 + 双重冲击波 + 震屏
 *            背景立绘在闪光中揭示（高亮 punch → 沉淀），流光化作余烬爆散
 *   标题卡   英雄名逐字浮现（模糊→锐利）+ 渐变扫光 + 装饰线展开
 *            + 副标题字距动画 + 星级逐颗弹出（抽卡式）
 *   收尾     标题卡淡出上移、黑边收回、正文内容浮入，氛围粒子常驻
 *
 * 页面接入（front matter → overrides/main.html 转 meta）：
 *   hero_id:       演出开关 + JS 钩子注册名
 *   hero_banner:   全屏背景立绘
 *   hero_theme:    CSS 主题名（body[data-hero-theme] 换色）
 *   hero_title:    标题卡大字（缺省取页面 h1）
 *   hero_subtitle: 标题卡副标题（头衔/称号，可缺省）
 *   hero_rarity:   星级数量（纯装饰，可缺省 → 显示菱形纹章）
 *   hero_intro:    入场 GIF（仅被单英雄脚本消费，如爱弥斯）
 *
 * 单英雄差异：
 *   - 颜色 / 标题渐变 / 花瓣形状 → CSS 用 body[data-hero-theme] 覆盖变量
 *   - 极端定制 → JS 注册：
 *
 *       window.HeroShowtime.register('hero-id', {
 *         particleSpawner: function (stage, ctx) { ... },  // 替换默认聚能演出
 *         particleCount: 12,                                // 旧式爆发时机参数
 *         particleStaggerMs: 50,                            //（与 v1 兼容）
 *         impactDelayMs: 2600,                              // 显式指定爆发时机（覆盖上面公式）
 *         titleDelayMs: 2600,                               // 标题卡出现时机（相对舞台开始）
 *         letterboxDelayMs: 2600,                           // 黑边滑入时机（默认 0 = 演出一开始）
 *         skipCurtain: true,                                // 不盖暗场幕布，演出前页面保持可见
 *         onBurst: function (ctx) { ... },                  // 爆发瞬间回调
 *         onShowStart: function (ctx) { ... },              // 演出开始回调
 *         onShowEnd: function (ctx) { ... },                // 舞台回收回调
 *         onReveal: function (ctx) { ... },                 // 正文放行瞬间回调（恢复被接管的 UI）
 *         onCleanup: function () { ... },                   // 切页清场回调（还原对真实 DOM 的改动）
 *         petalSpawner: function (layer, ctx) { ... }       // 替换常驻氛围粒子
 *       });
 *
 *   自定义 particleSpawner 的爆发时机沿用 v1 公式：
 *     particleStaggerMs × (particleCount - 1) + 700
 *
 * 兼容 navigation.instant：通过 document$.subscribe 订阅每次 DOM 切换。
 */
(function () {
  'use strict';

  // ── 注册表：英雄 ID → 自定义钩子 ──
  var registry = {};

  function register(heroId, hooks) {
    if (!heroId || !hooks) return;
    registry[heroId] = Object.assign({}, registry[heroId] || {}, hooks);
  }

  window.HeroShowtime = { register: register, registry: registry };

  // ── 时间轴常量 ──
  var CONVERGE_MS = 1050;      // 默认聚能时长（流光汇聚 → 爆发）
  var EXPLODE_MS = 950;        // 爆发余烬时长
  var TITLE_AFTER_BURST = 220; // 爆发后标题卡延迟
  var TITLE_HOLD_MS = 1800;    // 标题卡完整呈现后的停留
  var FAILSAFE_MS = 9000;      // 兜底：无论如何 9s 后收尾放行正文

  // 运行令牌：instant 导航切页时令旧定时器/动画失效
  var runToken = 0;

  function cleanupShow() {
    // 让上一个英雄有机会还原它对真实 DOM 的改动（如黄泉劈碎 UI 时的隐藏）
    var prevId = document.body.dataset.heroId;
    if (prevId && registry[prevId] && typeof registry[prevId].onCleanup === 'function') {
      try { registry[prevId].onCleanup(); } catch (e) { /* 清场失败不阻断 */ }
    }
    document.querySelectorAll(
      '.hero-stage, .hero-bg, .hero-vignette, .hero-petals, .hero-warmup, ' +
      '.hero-letterbox, .hero-titlecard'
    ).forEach(function (n) { n.remove(); });
    document.body.classList.remove(
      'hero-active', 'hero-shake', 'hero-cinema', 'hero-reveal-content', 'hero-keep-ui'
    );
    if (document.body.dataset.heroId) delete document.body.dataset.heroId;
    if (document.body.dataset.heroTheme) delete document.body.dataset.heroTheme;
  }

  function el(cls, parent) {
    var d = document.createElement('div');
    d.className = cls;
    if (parent) parent.appendChild(d);
    return d;
  }

  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

  // ── 解析 CSS 颜色（hex / rgb）为 {r,g,b}，供 Canvas 调 alpha ──
  function parseColor(str) {
    str = (str || '').trim();
    var m = /^#([0-9a-f]{3})$/i.exec(str);
    if (m) {
      return {
        r: parseInt(m[1][0] + m[1][0], 16),
        g: parseInt(m[1][1] + m[1][1], 16),
        b: parseInt(m[1][2] + m[1][2], 16)
      };
    }
    m = /^#([0-9a-f]{6})$/i.exec(str);
    if (m) {
      return {
        r: parseInt(m[1].slice(0, 2), 16),
        g: parseInt(m[1].slice(2, 4), 16),
        b: parseInt(m[1].slice(4, 6), 16)
      };
    }
    m = /^rgba?\(([^)]+)\)/i.exec(str);
    if (m) {
      var parts = m[1].split(',');
      return { r: +parts[0] || 0, g: +parts[1] || 0, b: +parts[2] || 0 };
    }
    return { r: 255, g: 77, b: 109 };
  }

  // ── 默认聚能演出：Canvas 流光汇聚 + 爆发余烬 ──
  function defaultParticleSpawner(stage, ctx) {
    var W = window.innerWidth;
    var H = window.innerHeight;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);

    var canvas = document.createElement('canvas');
    canvas.className = 'hero-fx-canvas';
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    stage.appendChild(canvas);

    var g = canvas.getContext('2d');
    g.scale(dpr, dpr);

    var cx = W / 2;
    var cy = H / 2;
    var R = Math.sqrt(cx * cx + cy * cy);

    var accentCss = getComputedStyle(document.body)
      .getPropertyValue('--hero-accent').trim() || '#ff4d6d';
    var c = parseColor(accentCss);
    function rgba(a) { return 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + a + ')'; }

    var converge = ctx.convergeMs || CONVERGE_MS;

    // 流光：从四周边缘加速冲向中心
    var streakCount = Math.round(Math.min(96, Math.max(40, W * H / 16000)));
    var streaks = [];
    for (var i = 0; i < streakCount; i++) {
      streaks.push({
        a: Math.random() * Math.PI * 2,
        d0: R * (0.6 + Math.random() * 0.55),
        len: 90 + Math.random() * 190,
        w: 1 + Math.random() * 2.6,
        delay: Math.random() * converge * 0.45,
        dur: converge * 0.45 + Math.random() * converge * 0.3
      });
    }

    // 余烬：爆发时从中心炸开
    var embers = null;
    function makeEmbers() {
      var n = Math.round(Math.min(110, Math.max(55, W * H / 16000)));
      var arr = [];
      for (var i = 0; i < n; i++) {
        var a = Math.random() * Math.PI * 2;
        var sp = 3 + Math.random() * 13;
        arr.push({
          x: cx, y: cy,
          vx: Math.cos(a) * sp,
          vy: Math.sin(a) * sp,
          life: 1,
          decay: 0.012 + Math.random() * 0.02,
          size: 1.2 + Math.random() * 2.8,
          white: i % 3 === 0
        });
      }
      return arr;
    }

    var t0 = null;
    function frame(ts) {
      if (!canvas.isConnected) return;
      if (t0 === null) t0 = ts;
      var elapsed = ts - t0;

      g.clearRect(0, 0, W, H);
      g.globalCompositeOperation = 'lighter';

      // ── 聚能阶段 ──
      if (elapsed <= converge + 80) {
        var ct = clamp01(elapsed / converge);

        // 能量核心
        var coreR = 14 + 130 * ct * ct;
        var cg = g.createRadialGradient(cx, cy, 0, cx, cy, coreR);
        cg.addColorStop(0, 'rgba(255,255,255,' + (0.9 * ct) + ')');
        cg.addColorStop(0.4, rgba(0.55 * ct));
        cg.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = cg;
        g.beginPath();
        g.arc(cx, cy, coreR, 0, Math.PI * 2);
        g.fill();

        // 收缩光环
        var ringR = Math.max(46, R * 0.5 * (1 - ct));
        g.globalAlpha = 0.5 * ct;
        g.strokeStyle = rgba(0.9);
        g.lineWidth = 1.5;
        g.beginPath();
        g.arc(cx, cy, ringR, 0, Math.PI * 2);
        g.stroke();
        g.globalAlpha = 1;

        // 汇聚流光
        g.lineCap = 'round';
        for (var s = 0; s < streaks.length; s++) {
          var st = streaks[s];
          var p = (elapsed - st.delay) / st.dur;
          if (p <= 0 || p >= 1) continue;
          var ease = p * p * p; // 加速入心
          var d = st.d0 * (1 - ease);
          var hx = cx + Math.cos(st.a) * d;
          var hy = cy + Math.sin(st.a) * d;
          var tail = d + st.len * (1 - p * 0.5);
          var tx = cx + Math.cos(st.a) * tail;
          var ty = cy + Math.sin(st.a) * tail;
          var grad = g.createLinearGradient(hx, hy, tx, ty);
          grad.addColorStop(0, 'rgba(255,255,255,' + (0.5 + 0.45 * p) + ')');
          grad.addColorStop(0.3, rgba(0.45 + 0.45 * p));
          grad.addColorStop(1, rgba(0));
          g.strokeStyle = grad;
          g.lineWidth = st.w;
          g.beginPath();
          g.moveTo(hx, hy);
          g.lineTo(tx, ty);
          g.stroke();
        }
      }

      // ── 爆发余烬 ──
      if (elapsed >= converge) {
        if (!embers) embers = makeEmbers();
        for (var e = 0; e < embers.length; e++) {
          var em = embers[e];
          if (em.life <= 0) continue;
          g.globalAlpha = em.life;
          g.fillStyle = em.white
            ? 'rgba(255,255,255,0.95)'
            : rgba(0.9);
          g.beginPath();
          g.arc(em.x, em.y, em.size * (0.4 + em.life * 0.6), 0, Math.PI * 2);
          g.fill();
          em.x += em.vx;
          em.y += em.vy;
          em.vx *= 0.965;
          em.vy = em.vy * 0.965 + 0.05;
          em.life -= em.decay;
        }
        g.globalAlpha = 1;
      }

      if (elapsed < converge + EXPLODE_MS) {
        requestAnimationFrame(frame);
      }
    }
    requestAnimationFrame(frame);
  }

  // ── 默认常驻氛围粒子（花瓣） ──
  function defaultPetalSpawner(layer /*, ctx */) {
    for (var i = 0; i < 22; i++) {
      var p = document.createElement('span');
      p.className = 'hero-petal';
      p.style.left = (Math.random() * 100) + 'vw';
      p.style.animationDelay = (-Math.random() * 16) + 's';
      p.style.animationDuration = (12 + Math.random() * 10) + 's';
      p.style.setProperty('--drift', ((Math.random() - 0.5) * 40) + 'vw');
      p.style.setProperty('--scale', (0.6 + Math.random() * 0.9).toFixed(2));
      p.style.opacity = (0.45 + Math.random() * 0.45).toFixed(2);
      layer.appendChild(p);
    }
  }

  // ── 图片预加载（带超时兜底） ──
  function preloadImage(url, timeoutMs) {
    return new Promise(function (resolve) {
      if (!url) { resolve({ ok: false, reason: 'no-url' }); return; }
      var settled = false;
      var img = new Image();
      img.decoding = 'async';
      var timer = setTimeout(function () {
        if (settled) return;
        settled = true;
        resolve({ ok: false, reason: 'timeout' });
      }, timeoutMs || 1500);
      img.onload = function () {
        var done = function () {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          resolve({ ok: true });
        };
        if (img.decode) img.decode().then(done, done);
        else done();
      };
      img.onerror = function () {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({ ok: false, reason: 'error' });
      };
      img.src = url;
    });
  }

  // ── 标题卡：抽卡式大字演出 ──
  function getTitleText() {
    var m = document.querySelector('meta[name="hero-title"]');
    if (m && m.content) return m.content;
    var h1 = document.querySelector('.md-content h1');
    if (!h1) return '';
    var clone = h1.cloneNode(true);
    clone.querySelectorAll('.headerlink').forEach(function (a) { a.remove(); });
    return clone.textContent.trim();
  }

  function showTitleCard() {
    var name = getTitleText();
    if (!name) return null;

    var card = el('hero-titlecard');
    el('hero-titlecard__halo', card);
    el('hero-titlecard__line hero-titlecard__line--top', card);

    var nameEl = el('hero-titlecard__name', card);
    var chars = Array.from ? Array.from(name) : name.split('');
    chars.forEach(function (ch, i) {
      var s = document.createElement('span');
      s.className = 'hero-titlecard__ch';
      if (ch === ' ') s.innerHTML = '&nbsp;';
      else s.textContent = ch;
      s.style.animationDelay = (120 + i * 55) + 'ms';
      nameEl.appendChild(s);
    });

    el('hero-titlecard__line hero-titlecard__line--bottom', card);

    var subMeta = document.querySelector('meta[name="hero-subtitle"]');
    if (subMeta && subMeta.content) {
      var sub = el('hero-titlecard__sub', card);
      sub.textContent = subMeta.content;
    }

    var rarMeta = document.querySelector('meta[name="hero-rarity"]');
    var rarity = rarMeta ? (parseInt(rarMeta.content, 10) || 0) : 0;
    if (rarity > 0) {
      var stars = el('hero-titlecard__stars', card);
      for (var i = 0; i < rarity; i++) {
        var star = document.createElement('span');
        star.className = 'hero-titlecard__star';
        star.textContent = '★';
        star.style.animationDelay = (chars.length * 55 + 380 + i * 110) + 'ms';
        stars.appendChild(star);
      }
    } else {
      el('hero-titlecard__emblem', card);
    }

    document.body.appendChild(card);

    // 完整呈现所需时间（逐字 + 星级）
    var inMs = 120 + chars.length * 55 + 600 + (rarity > 0 ? rarity * 110 + 280 : 0);
    return { card: card, inMs: inMs };
  }

  // ── 收尾：标题卡退场 + 黑边收回 + 放行正文 ──
  function finishCinema(letterbox, hooks, ctx) {
    var first = !document.body.classList.contains('hero-reveal-content');
    var card = document.querySelector('.hero-titlecard');
    if (card && !card.classList.contains('hero-titlecard--out')) {
      card.classList.add('hero-titlecard--out');
      setTimeout(function () { card.remove(); }, 800);
    }
    if (letterbox && letterbox.isConnected &&
        !letterbox.classList.contains('hero-letterbox--out')) {
      letterbox.classList.remove('hero-letterbox--in');
      letterbox.classList.add('hero-letterbox--out');
      setTimeout(function () {
        letterbox.remove();
        document.body.classList.remove('hero-cinema');
      }, 700);
    }
    document.body.classList.add('hero-reveal-content');
    if (first && hooks && typeof hooks.onReveal === 'function') {
      try { hooks.onReveal(ctx); } catch (e) { /* 恢复失败不阻断 */ }
    }
  }

  function runShowtime() {
    var meta = document.querySelector('meta[name="hero-id"]');
    if (!meta) { cleanupShow(); return; }
    if (document.body.classList.contains('hero-active') &&
        document.body.dataset.heroId === meta.content) return;
    cleanupShow();

    var token = ++runToken;
    function alive() { return token === runToken; }

    var heroId = meta.content;
    var bannerMeta = document.querySelector('meta[name="hero-banner"]');
    var themeMeta = document.querySelector('meta[name="hero-theme"]');
    var banner = bannerMeta ? bannerMeta.content : '';
    var theme = themeMeta ? themeMeta.content : '';
    var hooks = registry[heroId] || {};

    document.body.dataset.heroId = heroId;
    if (theme) document.body.dataset.heroTheme = theme;
    document.body.classList.add('hero-active');

    // ── 无障碍降级：静态直出，无任何动画 ──
    var reduced = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      var bgStatic = el('hero-bg hero-bg--static');
      if (banner) bgStatic.style.backgroundImage = 'url("' + banner + '")';
      document.body.insertBefore(bgStatic, document.body.firstChild);
      var vigStatic = el('hero-vignette');
      document.body.insertBefore(vigStatic, document.body.firstChild);
      document.body.classList.add('hero-reveal-content');
      return;
    }

    // 预热幕布（skipCurtain 英雄不盖，演出前保持页面可见）
    var warmup = null;
    if (hooks.skipCurtain) {
      document.body.classList.add('hero-keep-ui');
    } else {
      warmup = el('hero-warmup');
      document.body.insertBefore(warmup, document.body.firstChild);
    }

    // 暗角
    var vignette = el('hero-vignette');
    document.body.insertBefore(vignette, document.body.firstChild);

    // 背景层：保持暗场，待爆发瞬间揭示
    var bg = el('hero-bg hero-bg--pending');
    if (banner) bg.style.backgroundImage = 'url("' + banner + '")';
    document.body.insertBefore(bg, document.body.firstChild);

    // 电影黑边（letterboxDelayMs > 0 时延迟到舞台开始后再入场）
    var letterbox = el('hero-letterbox');
    el('hero-letterbox__bar hero-letterbox__bar--top', letterbox);
    el('hero-letterbox__bar hero-letterbox__bar--bottom', letterbox);
    var lbDelay = hooks.letterboxDelayMs || 0;
    function attachLetterbox() {
      if (!alive()) return;
      document.body.appendChild(letterbox);
      document.body.classList.add('hero-cinema');
      requestAnimationFrame(function () {
        letterbox.classList.add('hero-letterbox--in');
      });
    }
    if (!lbDelay) attachLetterbox();

    var particleCount = hooks.particleCount != null ? hooks.particleCount : 8;
    var particleStaggerMs = hooks.particleStaggerMs != null ? hooks.particleStaggerMs : 60;
    var ctx = {
      heroId: heroId,
      theme: theme,
      banner: banner,
      body: document.body,
      warmup: warmup,
      vignette: vignette,
      bg: bg,
      stage: null,
      particleCount: particleCount,
      particleStaggerMs: particleStaggerMs,
      convergeMs: CONVERGE_MS
    };

    if (typeof hooks.onShowStart === 'function') hooks.onShowStart(ctx);

    // 等图就绪后开演（暗场 + 黑边作为等待蓄势）
    preloadImage(banner, 1500).then(function (result) {
      if (!alive()) return;
      var bgOk = result.ok;
      bg.classList.remove('hero-bg--pending');
      bg.classList.add('hero-bg--armed');
      if (!bgOk) bg.style.backgroundImage = '';

      // 常驻氛围粒子层
      var petals = el('hero-petals');
      (hooks.petalSpawner || defaultPetalSpawner)(petals, ctx);
      document.body.appendChild(petals);

      // 演出舞台
      var stage = el('hero-stage');
      var flash = el('hero-flash', stage);
      var rays = el('hero-rays', stage);
      var shock = el('hero-shock', stage);
      var shockAlt = el('hero-shock hero-shock--alt', stage);
      var pillar = el('hero-pillar', stage);
      var chroma = el('hero-chroma', stage);
      ctx.stage = stage;

      var hasCustom = typeof hooks.particleSpawner === 'function';
      (hooks.particleSpawner || defaultParticleSpawner)(stage, ctx);
      document.body.appendChild(stage);

      // 黑边延迟入场（相对舞台开始计时）
      if (lbDelay) setTimeout(attachLetterbox, lbDelay);

      // 爆发时机：显式指定 > 自定义英雄 v1 公式 > 默认聚能时长
      var impactDelay = (typeof hooks.impactDelayMs === 'number')
        ? hooks.impactDelayMs
        : hasCustom
          ? Math.max(0, particleStaggerMs * (particleCount - 1)) + 700
          : CONVERGE_MS;

      setTimeout(function () {
        if (!alive()) return;
        flash.classList.add('hero-flash--burst');
        rays.classList.add('hero-rays--burst');
        shock.classList.add('hero-shock--burst');
        shockAlt.classList.add('hero-shock--burst');
        pillar.classList.add('hero-pillar--burst');
        chroma.classList.add('hero-chroma--burst');
        document.body.classList.add('hero-shake');
        bg.classList.add(bgOk ? 'hero-bg--reveal' : 'hero-bg--fallback');
        if (warmup) {
          warmup.classList.add('hero-warmup--out');
          setTimeout(function () { warmup.remove(); }, 600);
        }
        setTimeout(function () { document.body.classList.remove('hero-shake'); }, 650);
        if (typeof hooks.onBurst === 'function') hooks.onBurst(ctx);
      }, impactDelay);

      // 标题卡
      var titleDelay = (typeof hooks.titleDelayMs === 'number')
        ? hooks.titleDelayMs
        : impactDelay + TITLE_AFTER_BURST;
      setTimeout(function () {
        if (!alive()) return;
        var info = showTitleCard();
        var holdEnd = (info ? info.inMs : 0) + TITLE_HOLD_MS;
        setTimeout(function () {
          if (!alive()) return;
          finishCinema(letterbox, hooks, ctx);
        }, holdEnd);
      }, titleDelay);

      // 舞台淡出回收
      setTimeout(function () {
        if (!alive()) return;
        stage.classList.add('hero-stage--fade');
        setTimeout(function () {
          if (!alive()) return;
          stage.remove();
          if (typeof hooks.onShowEnd === 'function') hooks.onShowEnd(ctx);
        }, 800);
      }, impactDelay + EXPLODE_MS + 250);

      // 兜底：任何异常下也要放行正文
      setTimeout(function () {
        if (!alive()) return;
        finishCinema(letterbox, hooks, ctx);
      }, FAILSAFE_MS);
    });
  }

  // navigation.instant 友好：每次 DOM 更新触发
  if (typeof document$ !== 'undefined' && document$.subscribe) {
    document$.subscribe(function () {
      requestAnimationFrame(runShowtime);
    });
  } else {
    document.addEventListener('DOMContentLoaded', function () {
      requestAnimationFrame(runShowtime);
    });
  }
})();
