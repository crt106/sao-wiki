/**
 * 爱弥斯 专属演出
 * ────────────────────────────────────────────────────────────
 * 当前已实现：
 *   - 粉色/青色光翼碎片持续飘落
 *   - 可选 GIF 入场层：页面 front matter 填 hero_intro 后播放并渐隐
 *
 * GIF 待提供时，在英雄页添加：
 *   hero_intro: assets/intro/爱弥斯.gif
 */
(function () {
  'use strict';

  if (!window.HeroShowtime) return;

  function getIntroUrl() {
    var meta = document.querySelector('meta[name="hero-intro"]');
    return meta ? meta.content : '';
  }

  window.HeroShowtime.register('amis', {
    particleCount: 1,
    particleStaggerMs: 0,
    titleDelayMs: 2600, // 抽卡 CG GIF 渐隐时再出标题卡

    particleSpawner: function (stage) {
      var introUrl = getIntroUrl();
      if (!introUrl) return;

      document.querySelectorAll('.amis-intro').forEach(function (n) { n.remove(); });
      var intro = document.createElement('div');
      intro.className = 'amis-intro';
      intro.style.backgroundImage = 'url("' + introUrl + '")';
      document.body.appendChild(intro);
      intro.addEventListener('animationend', function () { intro.remove(); }, { once: true });
      setTimeout(function () { intro.remove(); }, 3600);
    },

    petalSpawner: function (layer) {
      for (var i = 0; i < 26; i++) {
        var p = document.createElement('span');
        p.className = 'hero-petal';
        p.style.left = (Math.random() * 100) + 'vw';
        p.style.animationDelay = (-Math.random() * 18) + 's';
        p.style.animationDuration = (14 + Math.random() * 12) + 's';
        p.style.setProperty('--drift', ((Math.random() - 0.5) * 34) + 'vw');
        p.style.setProperty('--scale', (0.55 + Math.random() * 1.1).toFixed(2));
        p.style.opacity = (0.38 + Math.random() * 0.46).toFixed(2);
        layer.appendChild(p);
      }
    }
  });
})();
