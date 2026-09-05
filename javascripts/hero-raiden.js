/**
 * 雷电·忘川守·芽衣（黄泉）专属演出 v2 ——「黄泉一刀」
 * ────────────────────────────────────────────────────────────
 * 致敬原型角色的标志性太刀居合：一刀划开世界，万物归于虚无。
 *
 * 时间轴（相对舞台开始，单位 ms）：
 *   0    - 380   页面保持原样 → 画面渐暗（居合预备的静止感）
 *   240  - 400   赤红刀光极速横贯屏幕
 *   390          真实 UI 被劈成上下两半（DOM 克隆 + clip-path，原 UI 隐藏）
 *   640  - 1250  两半缓缓错开，裂隙中赤色雷光涌动
 *   1250 - 1700  两半炸碎：UI 残片混着玻璃碎片放射状爆开
 *   1500 - 2500  黑洞显现，吸积盘旋转，把虚空与碎片扭曲吞噬
 *   2500 - 2650  黑洞坍缩成一点 → 白红色内爆闪光
 *   2600         引擎爆发：banner 揭示 + 黑边滑入（letterboxDelayMs）
 *   2950         标题卡
 *
 * 对真实 DOM 的接管（隐藏 header/tabs/container）通过 onReveal /
 * onCleanup 还原，切页中断也能恢复。
 */
(function () {
  'use strict';

  if (!window.HeroShowtime) return;

  var PI = Math.PI;
  var TAU = PI * 2;
  var CRIMSON = { r: 255, g: 42, b: 77 };   // 赤红雷光
  var VIOLET = { r: 179, g: 136, b: 255 };  // 主题紫

  function rand(a, b) { return a + Math.random() * (b - a); }
  function rgba(c, a) { return 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + a + ')'; }
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function easeInCubic(t) { return t * t * t; }
  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  // ── 页面顶层 UI 元素（去掉互相嵌套的重复，如 .md-tabs 位于 .md-header 内） ──
  function topLevelUiEls() {
    var els = ['.md-header', '.md-tabs', '.md-container']
      .map(function (s) { return document.querySelector(s); })
      .filter(Boolean);
    return els.filter(function (n) {
      return !els.some(function (m) { return m !== n && m.contains(n); });
    });
  }

  // ── 被接管隐藏的真实 UI 元素（用于恢复） ──
  // 注意：Material 会在 body 下挂载 .md-container 之外的零散节点
  // （如独立的 .md-nav），所以这里隐藏 body 下除演出图层 / 资源标签
  // 之外的全部元素，记录原 inline 值用于恢复。
  // 接管隐藏走纯 CSS（raiden.css 的 body.yomi-takeover 规则）：
  // 对演出期间被 Material 动态挂载到 body 的零散节点也自动生效
  function hideRealUi() {
    document.body.classList.add('yomi-takeover');
  }

  function restoreRealUi() {
    document.body.classList.remove('yomi-takeover');
  }

  // ── 把真实页面克隆成上/下两个 clip-path 半屏 ──
  function buildHalves(stage, yL, yR) {
    var W = window.innerWidth;
    var H = window.innerHeight;
    var srcs = topLevelUiEls();

    function makeHalf(clip) {
      var half = document.createElement('div');
      half.className = 'yomi-half';
      half.style.clipPath = clip;
      var inner = document.createElement('div');
      inner.className = 'yomi-half__inner';
      inner.style.transform = 'translateY(' + (-window.scrollY) + 'px)';
      srcs.forEach(function (n) { inner.appendChild(n.cloneNode(true)); });
      half.appendChild(inner);
      stage.appendChild(half);
      return half;
    }

    var top = makeHalf(
      'polygon(0px 0px, ' + W + 'px 0px, ' + W + 'px ' + yR + 'px, 0px ' + yL + 'px)');
    var bottom = makeHalf(
      'polygon(0px ' + yL + 'px, ' + W + 'px ' + yR + 'px, ' + W + 'px ' + H + 'px, 0px ' + H + 'px)');
    return { top: top, bottom: bottom };
  }

  // ── 玻璃渣：从冲击点放射状炸开 ──
  function spawnShards(stage, icx, icy) {
    var count = 46;
    for (var i = 0; i < count; i++) {
      var a = rand(0, TAU);
      var d0 = rand(20, 290);
      var x = icx + Math.cos(a) * d0;
      var y = icy + Math.sin(a) * d0;
      var size = rand(20, 86);

      var verts = 4 + Math.floor(Math.random() * 3);
      var pts = [];
      for (var j = 0; j < verts; j++) {
        var va = (j / verts) * TAU + rand(-0.4, 0.4);
        var vr = rand(0.4, 1);
        pts.push(Math.round(50 + Math.cos(va) * vr * 46) + '% ' +
                 Math.round(50 + Math.sin(va) * vr * 46) + '%');
      }

      // 沿自身方位角放射飞出（带少量散布）
      var flyAngle = a + rand(-0.3, 0.3);
      var flyDist = rand(280, 780);

      var elShard = document.createElement('div');
      elShard.className = 'yomi-shard';
      elShard.style.left = (x - size / 2) + 'px';
      elShard.style.top = (y - size / 2) + 'px';
      elShard.style.width = size + 'px';
      elShard.style.height = size * rand(0.6, 1.3) + 'px';
      elShard.style.setProperty('--clip', pts.join(', '));
      elShard.style.setProperty('--tx', Math.cos(flyAngle) * flyDist + 'px');
      elShard.style.setProperty('--ty', (Math.sin(flyAngle) * flyDist - rand(20, 90)) + 'px');
      elShard.style.setProperty('--rot', rand(-160, 160) + 'deg');
      elShard.style.setProperty('--delay', rand(0, 0.12) + 's');
      elShard.style.setProperty('--dur', rand(0.55, 1.0) + 's');
      elShard.style.setProperty('--shard-angle', rand(0, 360) + 'deg');
      stage.appendChild(elShard);
    }
  }

  // ── 蛛网裂纹几何：以冲击点为心，含两条沿斩线的主裂缝 ──
  function makeCrackPattern(W, H, icx, icy, slashA, spokeCount) {
    var spokes = [slashA];
    var above = Math.ceil((spokeCount - 2) / 2);
    var below = spokeCount - 2 - above;
    var i;
    for (i = 1; i <= above; i++) {
      spokes.push(slashA + PI * i / (above + 1) + rand(-0.12, 0.12));
    }
    spokes.push(slashA + PI);
    for (i = 1; i <= below; i++) {
      spokes.push(slashA + PI + PI * i / (below + 1) + rand(-0.12, 0.12));
    }

    var Rmax = 0;
    [[0, 0], [W, 0], [0, H], [W, H]].forEach(function (c) {
      Rmax = Math.max(Rmax, Math.hypot(c[0] - icx, c[1] - icy));
    });
    var R2 = Rmax * 1.45;
    var r1 = spokes.map(function () { return Rmax * (0.16 + Math.random() * 0.16); });

    // 每条主裂缝的折线点（带垂直抖动，供 Canvas 画裂纹蔓延）
    var polylines = spokes.map(function (a) {
      var pts = [];
      var steps = 7;
      for (var k = 0; k <= steps; k++) {
        var rr = R2 * k / steps;
        var jit = k === 0 ? 0 : rand(-1, 1) * Math.min(14, rr * 0.05);
        pts.push({
          x: icx + Math.cos(a) * rr - Math.sin(a) * jit,
          y: icy + Math.sin(a) * rr + Math.cos(a) * jit,
          r: rr
        });
      }
      return pts;
    });
    return { cx: icx, cy: icy, spokes: spokes, r1: r1, Rmax: Rmax, R2: R2, polylines: polylines };
  }

  // ── 把 UI 劈成蛛网状真实碎块 ──
  // 每块 = clip-path 多边形包一份整页克隆。预先构建并隐藏（克隆/布局成本
  // 提前消化），爆碎瞬间只切换动画状态。初始姿态与两半漂移末态严格对齐
  //（绕碎块质心旋转的等效平移补偿），衔接无跳变。
  function buildFragments(stage, crack, yAt) {
    var W = window.innerWidth;
    var H = window.innerHeight;
    var srcs = topLevelUiEls();
    var icx = crack.cx, icy = crack.cy;
    function pt(a, r) { return { x: icx + Math.cos(a) * r, y: icy + Math.sin(a) * r }; }

    var frags = [];
    var batch = document.createDocumentFragment();

    function makeFrag(poly, isInner) {
      var gx = 0, gy = 0;
      poly.forEach(function (p) { gx += p.x; gy += p.y; });
      gx /= poly.length;
      gy /= poly.length;

      // 与漂移末态对齐：绕质心旋转 θ 等效于绕屏心旋转 θ + 平移补偿
      var side = gy < yAt(gx) ? -1 : 1;
      var th = side * 1.2 * PI / 180;
      var rx = gx - W / 2, ry = gy - H / 2;
      var ex = (Math.cos(th) * rx - Math.sin(th) * ry) - rx;
      var ey = (Math.sin(th) * rx + Math.cos(th) * ry) - ry;
      var f0x = side * 26 + ex, f0y = side * 38 + ey;

      // 放射飞散：内圈小块快而狂转，外圈大块缓慢翻出
      var dl = Math.hypot(gx - icx, gy - icy) || 1;
      var dirX = (gx - icx) / dl, dirY = (gy - icy) / dl;
      var dist = isInner ? rand(320, 580) : rand(160, 320);
      var rot = th + (Math.random() < 0.5 ? -1 : 1) * (isInner ? rand(0.3, 0.85) : rand(0.06, 0.16));

      var frag = document.createElement('div');
      frag.className = 'yomi-frag' + (isInner ? ' yomi-frag--sm' : '');
      frag.style.clipPath = 'polygon(' + poly.map(function (p) {
        return p.x.toFixed(1) + 'px ' + p.y.toFixed(1) + 'px';
      }).join(', ') + ')';
      frag.style.transformOrigin = gx.toFixed(1) + 'px ' + gy.toFixed(1) + 'px';
      frag.style.setProperty('--f0x', f0x.toFixed(1) + 'px');
      frag.style.setProperty('--f0y', f0y.toFixed(1) + 'px');
      frag.style.setProperty('--f0r', (th * 180 / PI).toFixed(2) + 'deg');
      frag.style.setProperty('--f1x', (f0x + dirX * dist).toFixed(1) + 'px');
      frag.style.setProperty('--f1y', (f0y + dirY * dist).toFixed(1) + 'px');
      frag.style.setProperty('--f1r', (rot * 180 / PI).toFixed(2) + 'deg');
      frag.style.setProperty('--fdel', (isInner ? rand(0, 40) : rand(60, 140)).toFixed(0) + 'ms');
      frag.style.setProperty('--fdur', (isInner ? rand(0.55, 0.75) : rand(0.85, 1.1)).toFixed(2) + 's');

      var inner = document.createElement('div');
      inner.className = 'yomi-frag__inner';
      inner.style.transform = 'translateY(' + (-window.scrollY) + 'px)';
      srcs.forEach(function (n) { inner.appendChild(n.cloneNode(true)); });
      frag.appendChild(inner);
      batch.appendChild(frag);
      frags.push(frag);
    }

    var s = crack.spokes.length;
    for (var i = 0; i < s; i++) {
      var a = crack.spokes[i];
      var b = i === s - 1 ? crack.spokes[0] + TAU : crack.spokes[i + 1];
      var ra = crack.r1[i];
      var rb = crack.r1[(i + 1) % s];
      var mid = pt((a + b) / 2, (ra + rb) / 2 * (0.92 + Math.random() * 0.2));
      var pA = pt(a, ra);
      var pB = pt(b, rb);
      makeFrag([{ x: icx, y: icy }, pA, mid, pB], true);
      makeFrag([pA, mid, pB, pt(b, crack.R2), pt(a, crack.R2)], false);
    }
    stage.appendChild(batch);
    return frags;
  }

  // ════════════════════════════════════════════════════════════
  //  WebGL 黑洞：引力透镜 + fbm 噪声吸积盘 + 涡流吸入条纹 + 胶片噪点
  //  初始化失败（不支持 WebGL）返回 null，外层退回 CSS 版黑洞
  // ════════════════════════════════════════════════════════════
  var GL_VERT = [
    'attribute vec2 a_pos;',
    'varying vec2 v_uv;',
    'void main() {',
    '  v_uv = a_pos * 0.5 + 0.5;',
    '  gl_Position = vec4(a_pos, 0.0, 1.0);',
    '}'
  ].join('\n');

  var GL_FRAG = [
    'precision highp float;',
    'uniform vec2 u_res;',
    'uniform float u_t;',     // 秒
    'uniform float u_mass;',  // 黑洞强度 0→1
    'uniform float u_col;',   // 坍缩进度 0→1
    'varying vec2 v_uv;',
    '',
    'float hash(vec2 p) {',
    '  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);',
    '}',
    'float noise(vec2 p) {',
    '  vec2 i = floor(p); vec2 f = fract(p);',
    '  vec2 u = f * f * (3.0 - 2.0 * f);',
    '  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),',
    '             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);',
    '}',
    'float fbm(vec2 p) {',
    '  float v = 0.0; float a = 0.5;',
    '  for (int i = 0; i < 4; i++) {',
    '    v += a * noise(p);',
    '    p = p * 2.07 + vec2(13.7, 7.3);',
    '    a *= 0.5;',
    '  }',
    '  return v;',
    '}',
    '',
    'void main() {',
    '  float aspect = u_res.x / u_res.y;',
    '  vec2 p = vec2((v_uv.x - 0.5) * aspect, v_uv.y - 0.54);', // 黑洞中心：屏幕 46% 高度
    '  float r = length(p);',
    '  float ang = atan(p.y, p.x);',
    '  float m = u_mass;',
    '  float lensM = m * (1.0 + u_col * 2.5);',
    '',
    '  // 引力透镜：径向内拉 + 涡旋偏转（坍缩时加剧）',
    '  float swirl = lensM * 1.7 / (r + 0.22);',
    '  float pull  = lensM * 0.045 / (r + 0.06);',
    '  float a2 = ang + swirl + u_t * 0.05;',
    '  float r2 = max(r - pull, 0.001);',
    '  vec2 q = vec2(cos(a2), sin(a2)) * r2;',
    '',
    '  // 暗红虚空星云（域扭曲 fbm，全部在笛卡尔 q 空间采样避免极角接缝）',
    '  float n1 = fbm(q * 2.6 + vec2(0.0, u_t * 0.06));',
    '  float n2 = fbm(q * 5.2 - vec2(u_t * 0.11, 0.0) + n1 * 1.4);',
    '  vec3 deep    = vec3(0.02, 0.003, 0.04);',
    '  vec3 violet  = vec3(0.28, 0.09, 0.48);',
    '  vec3 crimson = vec3(0.78, 0.05, 0.16);',
    '  float nebAmp = 0.3 + 0.5 * m;',
    '  vec3 col = deep + (violet * n1 * 0.45 + crimson * n2 * n1 * 0.5) * nebAmp;',
    '',
    '  // 涡流吸入条纹：径向流入环纹 × 无缝角向噪声破碎',
    '  float angN = fbm(vec2(cos(a2), sin(a2)) * 2.5);',
    '  float streak = fbm(vec2(r * 10.0 - u_t * (1.8 + m * 3.0), angN * 6.0));',
    '  streak = pow(max(streak - 0.42, 0.0) * 1.9, 2.0);',
    '  col += mix(crimson, violet, n1) * streak * (0.4 + m * 1.5) * smoothstep(0.95, 0.12, r);',
    '',
    '  // 事件视界与吸积盘',
    '  float rh = 0.1 * m * (1.0 - u_col * 0.99);',
    '  float diskR = rh * 1.8 + 0.015;',
    '  float band = exp(-pow((r - diskR) / (0.028 + 0.032 * m), 2.0));',
    '  float dn = 0.55 + 0.45 * fbm(q * 16.0 + vec2(u_t * 1.3, 0.0));',
    '  float dop = 1.0 + 0.5 * sin(a2 + u_t * 1.3);', // 多普勒亮度不对称
    '  vec3 diskCol = mix(vec3(1.0, 0.88, 0.8), crimson * 1.8, 0.62);',
    '  col += diskCol * band * dn * dop * m * 1.45;',
    '',
    '  // 视界吞噬 + 赤红边缘辉光',
    '  col *= smoothstep(rh * 0.82, rh, r);',
    '  col += crimson * exp(-pow((r - rh) / (0.012 + 0.02 * m), 2.0)) * m * 1.5;',
    '',
    '  // 坍缩白闪（从中心涌出）',
    '  col += vec3(1.0, 0.86, 0.8) * smoothstep(0.6, 1.0, u_col) * (0.9 / (r * 6.0 + 0.3));',
    '',
    '  // 胶片噪点 + 暗角',
    '  col += (hash(v_uv * u_res + fract(u_t) * 61.7) - 0.5) * 0.05;',
    '  col *= 1.0 - smoothstep(0.55, 1.15, r) * 0.5;',
    '',
    '  gl_FragColor = vec4(col, 1.0);',
    '}'
  ].join('\n');

  function smoothstepJs(e0, e1, x) {
    var t = clamp01((x - e0) / (e1 - e0));
    return t * t * (3 - 2 * t);
  }

  function initYomiGL(stage) {
    var W = window.innerWidth;
    var H = window.innerHeight;
    // 限制总像素 ~220 万，防止高分屏全屏 shader 掉帧
    var scale = Math.min(Math.min(window.devicePixelRatio || 1, 2),
      Math.sqrt(2200000 / (W * H)));
    if (!(scale > 0)) scale = 1;

    var canvas = document.createElement('canvas');
    canvas.className = 'yomi-gl';
    canvas.width = Math.max(2, Math.round(W * scale));
    canvas.height = Math.max(2, Math.round(H * scale));
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';

    var gl = null;
    try {
      gl = canvas.getContext('webgl', { alpha: false, antialias: false, depth: false, stencil: false }) ||
           canvas.getContext('experimental-webgl');
    } catch (e) { gl = null; }
    if (!gl) return null;

    function compile(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
    }
    var vs = compile(gl.VERTEX_SHADER, GL_VERT);
    var fs = compile(gl.FRAGMENT_SHADER, GL_FRAG);
    if (!vs || !fs) return null;
    var prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
    gl.useProgram(prog);

    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, 'a_pos');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    var uRes = gl.getUniformLocation(prog, 'u_res');
    var uT = gl.getUniformLocation(prog, 'u_t');
    var uMass = gl.getUniformLocation(prog, 'u_mass');
    var uCol = gl.getUniformLocation(prog, 'u_col');
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.uniform2f(uRes, canvas.width, canvas.height);

    stage.appendChild(canvas);

    return {
      canvas: canvas,
      draw: function (tMs) {
        // 1450→2150ms 黑洞成长；2480→2640ms 坍缩
        gl.uniform1f(uT, tMs / 1000);
        gl.uniform1f(uMass, smoothstepJs(1450, 2150, tMs));
        gl.uniform1f(uCol, smoothstepJs(2480, 2640, tMs));
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      }
    };
  }

  // ── Canvas：刀光 / 裂隙雷光 / 爆散火花 / 黑洞吸入流 ──
  function runCanvas(stage, geo) {
    var W = window.innerWidth;
    var H = window.innerHeight;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var canvas = document.createElement('canvas');
    canvas.className = 'yomi-canvas';
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    stage.appendChild(canvas);
    var g = canvas.getContext('2d');
    g.scale(dpr, dpr);

    var cx = geo.cx, cy = geo.cy, yAt = geo.yAt;

    // 爆散火花（1250ms 触发）
    var sparks = null;
    function makeSparks() {
      var arr = [];
      for (var i = 0; i < 60; i++) {
        var x = rand(0.05, 0.95) * W;
        var y = yAt(x) + rand(-40, 40);
        var a = rand(0, TAU);
        var sp = rand(3, 12);
        arr.push({
          x: x, y: y,
          vx: Math.cos(a) * sp, vy: Math.sin(a) * sp,
          life: 1, decay: rand(0.014, 0.035),
          size: rand(1.4, 3.6),
          crimson: i % 3 !== 0
        });
      }
      return arr;
    }

    // 黑洞吸入流（1700ms 触发）
    var streams = null;
    function makeStreams() {
      var arr = [];
      var n = 80;
      for (var i = 0; i < n; i++) {
        arr.push({
          ang: rand(0, TAU),
          r: rand(160, Math.max(W, H) * 0.72),
          w: rand(0.8, 2.4),
          sp: rand(0.965, 0.985),
          crimson: i % 2 === 0
        });
      }
      return arr;
    }

    // 裂隙雷光：缓存的折线，周期性重新生成制造闪烁
    var bolts = [];
    var lastBolt = 0;
    function makeBolt() {
      var x0 = rand(-0.05, 0.55) * W;
      var x1 = x0 + rand(0.25, 0.5) * W;
      var segs = 9;
      var pts = [];
      for (var i = 0; i <= segs; i++) {
        var x = x0 + (x1 - x0) * (i / segs);
        pts.push({ x: x, y: yAt(x) + rand(-26, 26) });
      }
      return { pts: pts, life: 1, w: rand(1, 2.6) };
    }

    var t0 = null;
    function frame(ts) {
      if (!canvas.isConnected) return;
      if (t0 === null) t0 = ts;
      var t = ts - t0;

      g.clearRect(0, 0, W, H);
      g.globalCompositeOperation = 'lighter';
      g.lineCap = 'round';

      // ── 刀光横贯（240-400ms 掠过，余晖到 560ms） ──
      if (t >= 240 && t <= 560) {
        var p = clamp01((t - 240) / 140);
        var fade = t <= 400 ? 1 : 1 - (t - 400) / 160;
        var xHead = easeOutCubic(p) * (W * 1.06);
        var layers = [
          { w: 26, a: 0.10, c: CRIMSON },
          { w: 12, a: 0.30, c: CRIMSON },
          { w: 5,  a: 0.75, c: { r: 255, g: 170, b: 190 } },
          { w: 1.8, a: 1,   c: { r: 255, g: 255, b: 255 } }
        ];
        for (var l = 0; l < layers.length; l++) {
          var ly = layers[l];
          g.strokeStyle = rgba(ly.c, ly.a * fade);
          g.lineWidth = ly.w;
          g.shadowColor = rgba(CRIMSON, 0.8 * fade);
          g.shadowBlur = ly.w * 1.6;
          g.beginPath();
          g.moveTo(-20, yAt(-20));
          g.lineTo(Math.min(xHead, W + 20), yAt(Math.min(xHead, W + 20)));
          g.stroke();
        }
        g.shadowBlur = 0;
        // 刀尖辉光
        if (p > 0.02 && p < 0.98) {
          var tipX = xHead, tipY = yAt(xHead);
          var tg = g.createRadialGradient(tipX, tipY, 0, tipX, tipY, 46);
          tg.addColorStop(0, 'rgba(255,255,255,0.95)');
          tg.addColorStop(0.35, rgba(CRIMSON, 0.6));
          tg.addColorStop(1, rgba(CRIMSON, 0));
          g.fillStyle = tg;
          g.beginPath();
          g.arc(tipX, tipY, 46, 0, TAU);
          g.fill();
        }
      }

      // ── 玻璃裂纹蛛网：从冲击点放射蔓延（1090-1250），爆碎后余晖（-1470） ──
      if (geo.crack && t >= 1090 && t <= 1470) {
        var cr = geo.crack;
        var grow = easeOutCubic(clamp01((t - 1090) / 160)) * cr.R2;
        var calpha = t < 1250 ? 0.95 : Math.max(0, 0.95 - (t - 1250) / 220);
        if (calpha > 0) {
          g.shadowColor = rgba(CRIMSON, 0.85);
          g.shadowBlur = 9;
          g.lineWidth = 1.7;
          for (var pl = 0; pl < cr.polylines.length; pl++) {
            var pts2 = cr.polylines[pl];
            g.strokeStyle = 'rgba(255,255,255,' + calpha + ')';
            g.beginPath();
            var started = false;
            for (var pk = 0; pk < pts2.length; pk++) {
              if (pts2[pk].r > grow) break;
              if (!started) { g.moveTo(pts2[pk].x, pts2[pk].y); started = true; }
              else g.lineTo(pts2[pk].x, pts2[pk].y);
            }
            if (started) g.stroke();
          }
          // 环形裂纹（碎块内外圈分界）
          if (grow > cr.Rmax * 0.34) {
            g.lineWidth = 1.2;
            g.strokeStyle = 'rgba(255,235,240,' + (calpha * 0.75) + ')';
            g.beginPath();
            for (var sp = 0; sp <= cr.spokes.length; sp++) {
              var si = sp % cr.spokes.length;
              var px2 = cr.cx + Math.cos(cr.spokes[si]) * cr.r1[si];
              var py2 = cr.cy + Math.sin(cr.spokes[si]) * cr.r1[si];
              if (sp === 0) g.moveTo(px2, py2);
              else g.lineTo(px2, py2);
            }
            g.stroke();
          }
          g.shadowBlur = 0;
        }
      }

      // ── 裂隙雷光（640-1500ms） ──
      if (t >= 640 && t <= 1500) {
        if (t - lastBolt > 85) {
          lastBolt = t;
          bolts.push(makeBolt());
          if (bolts.length > 4) bolts.shift();
        }
        for (var b = 0; b < bolts.length; b++) {
          var bolt = bolts[b];
          bolt.life -= 0.06;
          if (bolt.life <= 0) continue;
          g.strokeStyle = rgba(CRIMSON, 0.85 * bolt.life);
          g.lineWidth = bolt.w;
          g.shadowColor = rgba(CRIMSON, 0.9);
          g.shadowBlur = 12;
          g.beginPath();
          g.moveTo(bolt.pts[0].x, bolt.pts[0].y);
          for (var k = 1; k < bolt.pts.length; k++) g.lineTo(bolt.pts[k].x, bolt.pts[k].y);
          g.stroke();
        }
        g.shadowBlur = 0;
      }

      // ── 爆散火花（1250ms~） ──
      if (t >= 1250) {
        if (!sparks) sparks = makeSparks();
        for (var s = 0; s < sparks.length; s++) {
          var sk = sparks[s];
          if (sk.life <= 0) continue;
          g.globalAlpha = sk.life;
          g.fillStyle = sk.crimson ? rgba(CRIMSON, 0.95) : rgba(VIOLET, 0.9);
          g.beginPath();
          g.arc(sk.x, sk.y, sk.size * sk.life, 0, TAU);
          g.fill();
          sk.x += sk.vx;
          sk.y += sk.vy;
          sk.vx *= 0.97;
          sk.vy *= 0.97;
          sk.life -= sk.decay;
        }
        g.globalAlpha = 1;
      }

      // ── 黑洞吸入流（1700-2550ms；WebGL 版黑洞自带涡流条纹，跳过） ──
      if (!geo.noStreams && t >= 1700 && t <= 2550) {
        if (!streams) streams = makeStreams();
        var pull = clamp01((t - 1700) / 850);
        for (var q = 0; q < streams.length; q++) {
          var st = streams[q];
          if (st.r < 24) { st.r = rand(260, Math.max(W, H) * 0.7); st.ang = rand(0, TAU); }
          var prevA = st.ang, prevR = st.r;
          st.ang += 0.16 * (240 / st.r) * (1 + pull * 2.2);
          st.r *= st.sp - pull * 0.02;
          var x1 = cx + Math.cos(prevA) * prevR;
          var y1 = cy + Math.sin(prevA) * prevR;
          var x2 = cx + Math.cos(st.ang) * st.r;
          var y2 = cy + Math.sin(st.ang) * st.r;
          var alpha = clamp01(1 - st.r / (Math.max(W, H) * 0.7)) * 0.8;
          g.strokeStyle = st.crimson ? rgba(CRIMSON, alpha) : rgba(VIOLET, alpha * 0.85);
          g.lineWidth = st.w;
          g.beginPath();
          g.moveTo(x1, y1);
          g.lineTo(x2, y2);
          g.stroke();
        }
      }

      if (t < 2600) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // ── 注册 ──
  window.HeroShowtime.register('raiden', {
    skipCurtain: true,       // 演出前页面保持原样（被一刀劈碎的就是真实 UI）
    impactDelayMs: 2600,     // 黑洞坍缩瞬间 = banner 揭示
    letterboxDelayMs: 2600,  // 黑边随 banner 一起入场
    titleDelayMs: 2950,

    particleSpawner: function (stage) {
      var W = window.innerWidth;
      var H = window.innerHeight;
      var cx = W / 2;
      var cy = H * 0.46;
      var slope = Math.tan(-7 * PI / 180); // 微微上扬的横斩
      function yAt(x) { return cy + slope * (x - cx); }
      var yL = yAt(0), yR = yAt(W);

      // 渐暗（居合预备）
      var dim = document.createElement('div');
      dim.className = 'yomi-dim';
      stage.appendChild(dim);
      requestAnimationFrame(function () { dim.classList.add('yomi-dim--in'); });

      // WebGL 黑洞（失败为 null → 退回 CSS 版）
      var glHole = initYomiGL(stage);

      // 蛛网裂纹几何：碎块数按页面 DOM 体量自动缩减（每块都是整页克隆）
      var srcNodes = topLevelUiEls().reduce(function (n, elx) {
        return n + elx.getElementsByTagName('*').length;
      }, 0);
      var spokeCount = Math.max(5, Math.min(9, Math.floor(90000 / Math.max(srcNodes, 1) / 2)));
      var crack = makeCrackPattern(W, H, cx, cy, -7 * PI / 180, spokeCount);

      // Canvas 演出层
      runCanvas(stage, { cx: cx, cy: cy, yAt: yAt, noStreams: !!glHole, crack: crack });

      // GL 渲染循环：1050ms 淡入接管虚空，2600ms 随 banner 揭示淡出
      if (glHole) {
        var glT0 = performance.now();
        // 用 rAF 启动：spawner 执行时 stage 尚未挂载，立即调用会因
        // isConnected=false 直接退出
        var glLoop = function () {
          if (!glHole.canvas.isConnected) return;
          var t = performance.now() - glT0;
          if (t > 1040 && !glHole.on) {
            glHole.on = true;
            glHole.canvas.classList.add('yomi-gl--on');
          }
          if (t > 2600 && !glHole.off) {
            glHole.off = true;
            glHole.canvas.classList.add('yomi-gl--off');
          }
          if (t > 1000) glHole.draw(t);
          if (t < 2780) requestAnimationFrame(glLoop);
        };
        requestAnimationFrame(glLoop);
      }

      var halves = null;
      var voidTex = null;
      var frags = null;

      // 390ms：劈开 —— 克隆出上下两半，隐藏真实 UI，虚空垫底
      setTimeout(function () {
        if (!stage.isConnected) return;

        var blackout = document.createElement('div');
        blackout.className = 'yomi-blackout';
        stage.insertBefore(blackout, stage.firstChild);
        voidTex = document.createElement('div');
        voidTex.className = 'yomi-void';
        stage.insertBefore(voidTex, blackout.nextSibling);

        halves = buildHalves(stage, yL, yR);
        hideRealUi();

        document.body.classList.add('hero-shake');
        setTimeout(function () { document.body.classList.remove('hero-shake'); }, 500);
      }, 390);

      // 600ms：预构建碎块并隐藏（克隆 + 布局成本在漂移空档消化，
      // 爆碎瞬间只切动画状态，不卡顿）
      setTimeout(function () {
        if (!stage.isConnected) return;
        frags = buildFragments(stage, crack, yAt);
      }, 600);

      // 640ms：两半错开漂移
      setTimeout(function () {
        if (!halves) return;
        halves.top.classList.add('yomi-half--drift-top');
        halves.bottom.classList.add('yomi-half--drift-bottom');
      }, 640);

      // 1250ms：蛛网爆碎 —— 两半撤场，UI 碎块放射飞散
      setTimeout(function () {
        if (!stage.isConnected) return;
        if (halves) {
          halves.top.remove();
          halves.bottom.remove();
          halves = null;
        }
        if (frags) {
          frags.forEach(function (f) { f.classList.add('yomi-frag--go'); });
          setTimeout(function () {
            frags.forEach(function (f) { f.remove(); });
            frags = null;
          }, 1700);
        }
        if (glHole && voidTex) voidTex.remove();
        spawnShards(stage, cx, cy);
      }, 1250);

      // 1500ms：黑洞显现（CSS 降级版；WebGL 版由 shader 内 u_mass 驱动）
      if (!glHole) {
        setTimeout(function () {
          if (!stage.isConnected) return;
          var hole = document.createElement('div');
          hole.className = 'yomi-hole';
          hole.innerHTML =
            '<div class="yomi-hole__glow"></div>' +
            '<div class="yomi-hole__disk"></div>' +
            '<div class="yomi-hole__core"></div>';
          stage.appendChild(hole);
          requestAnimationFrame(function () { hole.classList.add('yomi-hole--in'); });

          // 1700ms：虚空被吸入扭曲
          setTimeout(function () {
            if (voidTex) voidTex.classList.add('yomi-void--suck');
          }, 200);

          // 2500ms：坍缩
          setTimeout(function () {
            hole.classList.add('yomi-hole--collapse');
          }, 1000);
        }, 1500);
      }

      // 2500ms：内爆闪光（两种版本共用）
      setTimeout(function () {
        if (!stage.isConnected) return;
        var imp = document.createElement('div');
        imp.className = 'yomi-implosion';
        stage.appendChild(imp);
      }, 2500);

      // 2580ms：黑场退散，交棒给引擎的 banner 揭示
      setTimeout(function () {
        var blackout = stage.querySelector('.yomi-blackout');
        if (blackout) blackout.classList.add('yomi-blackout--off');
        dim.classList.add('yomi-dim--off');
      }, 2580);
    },

    // 正文放行瞬间：恢复被接管的真实 UI
    onReveal: function () {
      restoreRealUi();
    },

    // 切页中断：无论演到哪都还原真实 DOM
    onCleanup: function () {
      restoreRealUi();
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
