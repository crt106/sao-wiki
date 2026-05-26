/**
 * Hero Showtime 演出引擎
 * ────────────────────────────────────────────────────────────
 * 触发条件：HTML 中存在 <meta name="hero-id" content="...">
 *
 * 通用流程（每个英雄都共享）：
 *   1. 注入 warmup 暗场幕布（在背景图就绪前遮盖裸内容）
 *   2. 注入 vignette 暗角层（淡入）
 *   3. 注入 hero-bg 背景层（pending 状态等待图就绪）
 *   4. 预加载背景图（preload + decode + 1500ms 超时兜底）
 *      └─ 成功：bg → ready；失败：bg → fallback（纯色渐变兜底）
 *   5. 注入花瓣层（持续）
 *   6. 注入演出舞台 stage：粒子（默认红枪）+ 爆裂闪光 + 冲击波
 *   7. 在所有粒子聚拢中心瞬间：爆裂 + 屏幕震动 + warmup 淡出
 *   8. stage 在演出后自动淡出移除
 *
 * 单英雄差异：
 *   - 颜色 / 标题渐变 / 花瓣形状 → 通过 CSS 用 body[data-hero-id="xxx"] 覆盖
 *   - 极端定制（粒子生成、爆裂回调、自定义图层）→ 通过 JS 注册：
 *
 *       window.HeroShowtime.register('hero-id', {
 *         particleSpawner: function (stage, ctx) { ... },  // 替换默认红枪生成
 *         particleCount: 12,                                // 改默认粒子数
 *         particleStaggerMs: 50,                            // 改默认间隔
 *         onBurst: function (ctx) { ... },                  // 爆裂瞬间回调
 *         onShowStart: function (ctx) { ... },              // 演出开始回调
 *         onShowEnd: function (ctx) { ... },                // 演出结束回调
 *         petalSpawner: function (layer, ctx) { ... }       // 替换默认花瓣
 *       });
 *
 *   ctx 上下文包含：{ heroId, theme, banner, stage, body, vignette, warmup, bg }
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

  // 暴露到全局，单英雄脚本可通过 window.HeroShowtime.register() 注册
  window.HeroShowtime = { register: register, registry: registry };

  function cleanupShow() {
    document.querySelectorAll(
      '.hero-stage, .hero-bg, .hero-vignette, .hero-petals, .hero-warmup'
    ).forEach(function (n) { n.remove(); });
    document.body.classList.remove('hero-active', 'hero-shake');
    if (document.body.dataset.heroId) delete document.body.dataset.heroId;
    if (document.body.dataset.heroTheme) delete document.body.dataset.heroTheme;
  }

  // ── 默认粒子（红枪）生成 ──
  function defaultParticleSpawner(stage, ctx) {
    var total = ctx.particleCount;
    var stagger = ctx.particleStaggerMs;
    for (var i = 0; i < total; i++) {
      var spear = document.createElement('div');
      spear.className = 'hero-spear';
      var angle = (i / total) * Math.PI * 2 + (Math.random() - 0.5) * 0.15;
      var dist = Math.max(window.innerWidth, window.innerHeight) * 0.85;
      spear.style.setProperty('--sx', Math.cos(angle) * dist + 'px');
      spear.style.setProperty('--sy', Math.sin(angle) * dist + 'px');
      spear.style.setProperty('--rot', (angle * 180 / Math.PI + 180) + 'deg');
      spear.style.animationDelay = (i * stagger) + 'ms';
      stage.appendChild(spear);
    }
  }

  // ── 默认花瓣生成 ──
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

  function runShowtime() {
    var meta = document.querySelector('meta[name="hero-id"]');
    if (!meta) { cleanupShow(); return; }
    if (document.body.classList.contains('hero-active') &&
        document.body.dataset.heroId === meta.content) return;
    cleanupShow();

    var heroId = meta.content;
    var bannerMeta = document.querySelector('meta[name="hero-banner"]');
    var themeMeta = document.querySelector('meta[name="hero-theme"]');
    var banner = bannerMeta ? bannerMeta.content : '';
    var theme = themeMeta ? themeMeta.content : '';
    var hooks = registry[heroId] || {};

    document.body.dataset.heroId = heroId;
    if (theme) document.body.dataset.heroTheme = theme;
    document.body.classList.add('hero-active');

    // 预热幕布
    var warmup = document.createElement('div');
    warmup.className = 'hero-warmup';
    document.body.insertBefore(warmup, document.body.firstChild);

    // 暗角
    var vignette = document.createElement('div');
    vignette.className = 'hero-vignette';
    document.body.insertBefore(vignette, document.body.firstChild);

    // 背景层
    var bg = document.createElement('div');
    bg.className = 'hero-bg hero-bg--pending';
    if (banner) bg.style.backgroundImage = 'url("' + banner + '")';
    document.body.insertBefore(bg, document.body.firstChild);

    // 上下文（提供给所有 hooks）
    var particleCount = hooks.particleCount || 8;
    var particleStaggerMs = hooks.particleStaggerMs || 60;
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
      particleStaggerMs: particleStaggerMs
    };

    if (typeof hooks.onShowStart === 'function') hooks.onShowStart(ctx);

    // 等图就绪
    preloadImage(banner, 1500).then(function (result) {
      if (result.ok) {
        bg.classList.remove('hero-bg--pending');
        bg.classList.add('hero-bg--ready');
      } else {
        bg.classList.remove('hero-bg--pending');
        bg.classList.add('hero-bg--fallback');
        bg.style.backgroundImage = '';
      }

      // 花瓣层
      var petals = document.createElement('div');
      petals.className = 'hero-petals';
      (hooks.petalSpawner || defaultPetalSpawner)(petals, ctx);
      document.body.appendChild(petals);

      // 演出舞台
      var stage = document.createElement('div');
      stage.className = 'hero-stage';
      var flash = document.createElement('div');
      flash.className = 'hero-flash';
      var shock = document.createElement('div');
      shock.className = 'hero-shock';
      stage.appendChild(flash);
      stage.appendChild(shock);
      ctx.stage = stage;

      (hooks.particleSpawner || defaultParticleSpawner)(stage, ctx);
      document.body.appendChild(stage);

      // 爆裂时机：所有粒子到达中心
      var impactDelay = particleStaggerMs * (particleCount - 1) + 700;
      setTimeout(function () {
        flash.classList.add('hero-flash--burst');
        shock.classList.add('hero-shock--burst');
        document.body.classList.add('hero-shake');
        warmup.classList.add('hero-warmup--out');
        setTimeout(function () { warmup.remove(); }, 600);
        setTimeout(function () { document.body.classList.remove('hero-shake'); }, 650);
        if (typeof hooks.onBurst === 'function') hooks.onBurst(ctx);
      }, impactDelay);

      // 舞台淡出回收
      setTimeout(function () {
        stage.classList.add('hero-stage--fade');
        setTimeout(function () {
          stage.remove();
          if (typeof hooks.onShowEnd === 'function') hooks.onShowEnd(ctx);
        }, 800);
      }, impactDelay + 600);
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
