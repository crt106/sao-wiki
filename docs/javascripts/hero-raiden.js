/**
 * 雷电·忘川守·芽衣 专属演出
 * ────────────────────────────────────────────────────────────
 * Canvas 2D 实现：
 *   Phase 1 (0-400ms)   : 弧形刀光从左下向右上划出，穿过屏幕中心
 *   Phase 2 (300-500ms) : 斩击线上裂缝扩散 + 电弧火花
 *   Phase 3 (450-900ms) : 屏幕碎片沿斩击方向飞散
 *   Phase 4 (500ms)     : 全屏紫色闪光 + 屏幕震动
 */
(function () {
  'use strict';

  if (!window.HeroShowtime) return;

  // ── 工具函数 ──
  var PI = Math.PI;
  var TAU = PI * 2;

  function rand(a, b) { return a + Math.random() * (b - a); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }
  function easeInOutQuart(t) { return t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2; }

  // ── 刀光路径：穿过屏幕中心的弧线 ──
  // 二次贝塞尔曲线：控制点偏离起终点连线才能产生弧度
  // 起点左下 → 终点右上，控制点向左偏移产生向左凸的弧
  function getSlashPath() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    return {
      // 起点：左下
      sx: w * 0.08, sy: h * 0.92,
      // 控制点：偏左，让弧线向左侧鼓出（像挥刀的弧度）
      cx: w * 0.25, cy: h * 0.3,
      // 终点：右上
      ex: w * 0.92, ey: h * 0.08
    };
  }

  // 二次贝塞尔曲线取点
  function bezAt(t, p) {
    var u = 1 - t;
    return {
      x: u * u * p.sx + 2 * u * t * p.cx + t * t * p.ex,
      y: u * u * p.sy + 2 * u * t * p.cy + t * t * p.ey
    };
  }

  // 贝塞尔切线
  function bezTan(t, p) {
    var dx = 2 * (1 - t) * (p.cx - p.sx) + 2 * t * (p.ex - p.cx);
    var dy = 2 * (1 - t) * (p.cy - p.sy) + 2 * t * (p.ey - p.cy);
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    return { x: dx / len, y: dy / len };
  }

  // ── 火花粒子 ──
  function createSparks(path) {
    var sparks = [];
    for (var i = 0; i < 40; i++) {
      var t = rand(0.15, 0.85);
      var pt = bezAt(t, path);
      var tan = bezTan(t, path);
      var side = Math.random() > 0.5 ? 1 : -1;
      var speed = rand(3, 10);
      var angle = Math.atan2(-tan.x, tan.y) * side + rand(-0.8, 0.8);
      sparks.push({
        x: pt.x, y: pt.y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1,
        decay: rand(0.012, 0.035),
        size: rand(1.5, 4),
        hue: rand(255, 310)
      });
    }
    return sparks;
  }

  // ── 碎片数据 ──
  function createShards(path) {
    var shards = [];
    var count = 14;
    for (var i = 0; i < count; i++) {
      var t = (i + rand(0.2, 0.8)) / count;
      var pt = bezAt(t, path);
      var tan = bezTan(t, path);
      var side = (i % 2 === 0) ? 1 : -1;
      var offset = rand(40, 130) * side;
      var cx = pt.x + (-tan.y) * offset;
      var cy = pt.y + tan.x * offset;

      var verts = 4 + Math.floor(Math.random() * 3);
      var points = [];
      var size = rand(60, 150);
      for (var j = 0; j < verts; j++) {
        var a = (j / verts) * TAU + rand(-0.4, 0.4);
        var r = rand(0.4, 1);
        points.push(Math.round(50 + Math.cos(a) * r * 42) + '% ' + Math.round(50 + Math.sin(a) * r * 42) + '%');
      }

      var flyAngle = Math.atan2(-tan.x * side, tan.y * side) + rand(-0.5, 0.5);
      var flyDist = rand(180, 500);

      shards.push({
        x: cx - size / 2, y: cy - size / 2,
        w: size, h: size * rand(0.7, 1.3),
        clip: points.join(', '),
        tx: Math.cos(flyAngle) * flyDist,
        ty: Math.sin(flyAngle) * flyDist - rand(40, 120),
        rot: rand(-70, 70),
        delay: 0.38 + t * 0.12,
        dur: rand(0.9, 1.5),
        angle: rand(0, 360)
      });
    }
    return shards;
  }

  // ── Canvas 动画 ──
  function runAnimation(canvas, ctx, path, sparks, onDone) {
    var startTime = null;
    var totalMs = 950;
    var slashMs = 420;
    var sparkStartMs = 180;
    var crackStartMs = 220;

    // 将弧线离散化为点序列，用于精确绘制部分路径
    function drawSlashTrail(progress) {
      var headT = easeInOutQuart(Math.min(1, progress * 1.1));
      // 尾部淡出：头部走过 30% 后尾部开始追赶
      var tailT = progress > 0.35 ? easeOutCubic((progress - 0.35) / 0.65) * headT * 0.6 : 0;

      var steps = 60;
      var pts = [];
      for (var i = 0; i <= steps; i++) {
        var t = tailT + (headT - tailT) * (i / steps);
        pts.push(bezAt(t, path));
      }

      // 多层绘制
      var layers = [
        { w: 50, a: 0.06, c: '100, 50, 200' },
        { w: 30, a: 0.12, c: '130, 90, 220' },
        { w: 16, a: 0.28, c: '179, 136, 255' },
        { w: 7,  a: 0.6,  c: '220, 190, 255' },
        { w: 2.5, a: 0.95, c: '255, 255, 255' }
      ];

      var fadeIn = Math.min(1, progress * 4);

      for (var l = 0; l < layers.length; l++) {
        var ly = layers[l];
        ctx.save();
        ctx.lineWidth = ly.w;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.globalAlpha = ly.a * fadeIn;
        ctx.strokeStyle = 'rgba(' + ly.c + ', 1)';
        ctx.shadowColor = 'rgba(' + ly.c + ', 0.7)';
        ctx.shadowBlur = ly.w * 0.8;

        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (var s = 1; s < pts.length; s++) {
          ctx.lineTo(pts[s].x, pts[s].y);
        }
        ctx.stroke();
        ctx.restore();
      }

      // 刀尖辉光
      if (headT > 0.02 && headT < 0.98) {
        var tip = bezAt(headT, path);
        var intensity = 1 - Math.pow(Math.abs(progress - 0.45) * 2, 2);
        intensity = Math.max(0, Math.min(1, intensity));

        ctx.save();
        ctx.globalAlpha = intensity * 0.9;
        var g = ctx.createRadialGradient(tip.x, tip.y, 0, tip.x, tip.y, 35);
        g.addColorStop(0, 'rgba(255, 255, 255, 1)');
        g.addColorStop(0.25, 'rgba(220, 190, 255, 0.8)');
        g.addColorStop(0.6, 'rgba(179, 136, 255, 0.3)');
        g.addColorStop(1, 'rgba(100, 50, 200, 0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(tip.x, tip.y, 35, 0, TAU);
        ctx.fill();
        ctx.restore();
      }
    }

    function drawCracks(elapsed) {
      if (elapsed < crackStartMs) return;
      var t = Math.min(1, (elapsed - crackStartMs) / 350);
      var fadeOut = 1 - easeOutCubic(Math.max(0, (elapsed - 650) / 300));

      ctx.save();
      ctx.globalAlpha = fadeOut * 0.8;
      ctx.strokeStyle = 'rgba(179, 136, 255, 0.7)';
      ctx.shadowColor = 'rgba(179, 136, 255, 0.9)';
      ctx.shadowBlur = 10;
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';

      // 主裂缝
      var segs = 20;
      ctx.beginPath();
      for (var i = 0; i <= segs; i++) {
        var st = (i / segs) * t;
        var pt = bezAt(st, path);
        var jx = (i > 0 && i < segs) ? rand(-3, 3) : 0;
        var jy = (i > 0 && i < segs) ? rand(-3, 3) : 0;
        if (i === 0) ctx.moveTo(pt.x + jx, pt.y + jy);
        else ctx.lineTo(pt.x + jx, pt.y + jy);
      }
      ctx.stroke();

      // 分支
      ctx.lineWidth = 1.2;
      ctx.globalAlpha = fadeOut * 0.5;
      var branches = Math.floor(t * 10);
      for (var b = 0; b < branches; b++) {
        var bt = rand(0.08, t * 0.92);
        var bp = bezAt(bt, path);
        var btan = bezTan(bt, path);
        var bside = (b % 2 === 0) ? 1 : -1;
        var blen = rand(25, 70) * t;
        var ba = Math.atan2(-btan.x, btan.y) * bside + rand(-0.6, 0.6);
        ctx.beginPath();
        ctx.moveTo(bp.x, bp.y);
        ctx.lineTo(bp.x + Math.cos(ba) * blen, bp.y + Math.sin(ba) * blen);
        ctx.stroke();
      }
      ctx.restore();
    }

    function drawSparks(elapsed) {
      if (elapsed < sparkStartMs) return;
      for (var i = 0; i < sparks.length; i++) {
        var s = sparks[i];
        if (s.life <= 0) continue;

        ctx.save();
        ctx.globalAlpha = s.life;

        // 辉光
        var g = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.size * 4);
        g.addColorStop(0, 'hsla(' + s.hue + ', 80%, 85%, 1)');
        g.addColorStop(0.3, 'hsla(' + s.hue + ', 70%, 65%, 0.5)');
        g.addColorStop(1, 'hsla(' + s.hue + ', 60%, 40%, 0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size * 4, 0, TAU);
        ctx.fill();

        // 核心
        ctx.fillStyle = 'hsla(' + s.hue + ', 50%, 95%, ' + s.life + ')';
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, TAU);
        ctx.fill();
        ctx.restore();

        s.x += s.vx;
        s.y += s.vy;
        s.vy += 0.12;
        s.life -= s.decay;
      }
    }

    function frame(ts) {
      if (!startTime) startTime = ts;
      var elapsed = ts - startTime;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (elapsed < slashMs + 200) {
        drawSlashTrail(Math.min(1, elapsed / slashMs));
      }
      drawCracks(elapsed);
      drawSparks(elapsed);

      if (elapsed < totalMs) {
        requestAnimationFrame(frame);
      } else {
        onDone();
      }
    }

    requestAnimationFrame(frame);
  }

  // ── 注册 ──
  window.HeroShowtime.register('raiden', {
    particleCount: 0,
    particleStaggerMs: 0,

    particleSpawner: function (stage) {
      var w = window.innerWidth;
      var h = window.innerHeight;

      // Canvas：直接用 CSS 像素尺寸，通过 dpr 缩放保证清晰
      var dpr = window.devicePixelRatio || 1;
      var canvas = document.createElement('canvas');
      canvas.className = 'raiden-canvas';
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      stage.appendChild(canvas);

      var ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr); // 缩放后所有绘制用 CSS 像素坐标

      var path = getSlashPath();
      var sparks = createSparks(path);
      var shardData = createShards(path);

      // 碎片 DOM
      setTimeout(function () {
        for (var i = 0; i < shardData.length; i++) {
          var sd = shardData[i];
          var el = document.createElement('div');
          el.className = 'raiden-shard';
          el.style.left = sd.x + 'px';
          el.style.top = sd.y + 'px';
          el.style.width = sd.w + 'px';
          el.style.height = sd.h + 'px';
          el.style.setProperty('--clip', sd.clip);
          el.style.setProperty('--tx', sd.tx + 'px');
          el.style.setProperty('--ty', sd.ty + 'px');
          el.style.setProperty('--rot', sd.rot + 'deg');
          el.style.setProperty('--delay', sd.delay + 's');
          el.style.setProperty('--dur', sd.dur + 's');
          el.style.setProperty('--shard-angle', sd.angle + 'deg');
          stage.appendChild(el);
        }

        var whiteout = document.createElement('div');
        whiteout.className = 'raiden-whiteout';
        stage.appendChild(whiteout);
      }, 350);

      runAnimation(canvas, ctx, path, sparks, function () {
        canvas.classList.add('raiden-canvas--fade');
      });
    },

    onBurst: function () {
      document.body.classList.add('hero-shake');
    },

    petalSpawner: function (layer) {
      for (var i = 0; i < 18; i++) {
        var p = document.createElement('span');
        p.className = 'hero-petal';
        p.style.left = (Math.random() * 100) + 'vw';
        p.style.animationDelay = (-Math.random() * 18) + 's';
        p.style.animationDuration = (13 + Math.random() * 10) + 's';
        p.style.setProperty('--drift', ((Math.random() - 0.5) * 30) + 'vw');
        p.style.setProperty('--scale', (0.5 + Math.random() * 0.7).toFixed(2));
        p.style.opacity = (0.3 + Math.random() * 0.4).toFixed(2);
        layer.appendChild(p);
      }
    }
  });
})();
