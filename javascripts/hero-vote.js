(function () {
  "use strict";

  var STORAGE_PREFIX = "saowiki:hero-vote:";
  var LOCK_PREFIX = "saowiki:hero-vote-lock:";
  var COOLDOWN_PREFIX = "saowiki:hero-vote-cooldown:";
  var DEFAULT_POLL = "balance-2026-06";
  var DISABLED_HEROES = {
    "封弊者_桐谷和人_桐人": "桐人还加强个P"
  };

  function qs(root, selector) {
    return root.querySelector(selector);
  }

  function qsa(root, selector) {
    return Array.prototype.slice.call(root.querySelectorAll(selector));
  }

  function htmlEscape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function heroHref(hero) {
    return "../heroes/" + encodeURIComponent(hero.slug).replace(/%2F/g, "/") + "/";
  }

  function apiUrl(base, path) {
    return base.replace(/\/$/, "") + path;
  }

  function apiBases(app) {
    return [app.getAttribute("data-api-base"), app.getAttribute("data-api-fallback")]
      .filter(function (base, index, list) {
        return base && base.trim() && list.indexOf(base) === index;
      });
  }

  function fetchJson(url, options, timeoutMs) {
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = controller ? window.setTimeout(function () { controller.abort(); }, timeoutMs || 5000) : null;
    var requestOptions = Object.assign({}, options || {});
    if (controller) requestOptions.signal = controller.signal;
    return fetch(url, requestOptions).finally(function () {
      if (timer) window.clearTimeout(timer);
    });
  }

  function fetchApi(state, path, options, timeoutMs) {
    var bases = state.apiBases.slice();
    function next(lastError) {
      var base = bases.shift();
      if (!base) return Promise.reject(lastError || new Error("投票服务不可用"));
      return fetchJson(apiUrl(base, path), options, timeoutMs).then(function (res) {
        if (!res.ok && bases.length > 0 && (res.status === 404 || res.status >= 500)) {
          return next(new Error("投票服务不可用"));
        }
        return res;
      }).catch(function (err) {
        if (bases.length > 0) return next(err);
        throw err;
      });
    }
    return next();
  }

  function readLocalVotes(pollId) {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_PREFIX + pollId) || "[]");
    } catch (err) {
      return [];
    }
  }

  function writeLocalVotes(pollId, votes) {
    try {
      localStorage.setItem(STORAGE_PREFIX + pollId, JSON.stringify(votes));
    } catch (err) {
      // localStorage 可能被隐私模式禁用，忽略即可。
    }
  }

  function readLockedVotes(pollId) {
    try {
      return JSON.parse(localStorage.getItem(LOCK_PREFIX + pollId) || "[]");
    } catch (err) {
      return [];
    }
  }

  function lockVote(pollId, slug) {
    var votes = readLockedVotes(pollId);
    if (votes.indexOf(slug) < 0) votes.push(slug);
    try {
      localStorage.setItem(LOCK_PREFIX + pollId, JSON.stringify(votes));
    } catch (err) {
      // localStorage 可能被隐私模式禁用，后端仍会做去重。
    }
  }

  function unlockVote(pollId, slug) {
    var votes = readLockedVotes(pollId).filter(function (item) { return item !== slug; });
    try {
      localStorage.setItem(LOCK_PREFIX + pollId, JSON.stringify(votes));
    } catch (err) {
      // 忽略本地存储失败。
    }
  }

  function cooldownActive(pollId) {
    try {
      var until = Number(localStorage.getItem(COOLDOWN_PREFIX + pollId) || 0);
      return Date.now() < until;
    } catch (err) {
      return false;
    }
  }

  function startCooldown(pollId) {
    try {
      localStorage.setItem(COOLDOWN_PREFIX + pollId, String(Date.now() + 8000));
    } catch (err) {
      // 忽略本地存储失败。
    }
  }

  function createState(app) {
    var heroes = (window.SAOWIKI_HERO_VOTE_DATA || []).map(function (hero, index) {
      return Object.assign({
        votes: 0,
        rank: index + 1,
        voted: false,
        disabledReason: DISABLED_HEROES[hero.slug] || ""
      }, hero);
    });
    return {
      app: app,
      pollId: app.getAttribute("data-poll-id") || DEFAULT_POLL,
      apiBase: app.getAttribute("data-api-base") || "",
      apiBases: apiBases(app),
      heroes: heroes,
      query: "",
      sort: "rank",
      loading: false,
      error: "",
      localOnly: apiBases(app).length === 0
    };
  }

  function render(app, state) {
    var totalVotes = state.heroes.reduce(function (sum, hero) { return sum + hero.votes; }, 0);
    var votedCount = state.heroes.filter(function (hero) { return hero.voted; }).length;
    app.className = "hero-vote";
    app.innerHTML = [
      '<section class="hero-vote__hero">',
      '  <div class="hero-vote__copy">',
      '    <p class="hero-vote__eyebrow">Balance Vote</p>',
      '    <h2>你觉得谁最需要加强？</h2>',
      '    <p>每个英雄可投一次。票数用于收集玩家体感，不直接代表最终改动优先级。</p>',
      '  </div>',
      '  <div class="hero-vote__stats" aria-label="投票概览">',
      '    <div><strong data-total-votes>' + totalVotes + '</strong><span>总票数</span></div>',
      '    <div><strong>' + state.heroes.length + '</strong><span>英雄</span></div>',
      '    <div><strong data-voted-count>' + votedCount + '</strong><span>已支持</span></div>',
      '  </div>',
      '</section>',
      '<section class="hero-vote__toolbar" aria-label="投票工具栏">',
      '  <label class="hero-vote__search"><span>搜索</span><input type="search" placeholder="输入英雄名" value="' + htmlEscape(state.query) + '"></label>',
      '  <div class="hero-vote__sort" role="tablist" aria-label="排序方式">',
      '    <button type="button" data-sort="rank" aria-selected="' + (state.sort === "rank") + '">默认</button>',
      '    <button type="button" data-sort="votes" aria-selected="' + (state.sort === "votes") + '">票数</button>',
      '    <button type="button" data-sort="name" aria-selected="' + (state.sort === "name") + '">名称</button>',
      '  </div>',
      '</section>',
      state.localOnly ? '<p class="hero-vote__notice">投票后端尚未配置，当前为本地演示模式，不会写入真实票数。部署 Worker 后填写 <code>data-api-base</code> 即可启用真实投票。</p>' : '',
      state.error ? '<p class="hero-vote__notice hero-vote__notice--error">' + htmlEscape(state.error) + '</p>' : '',
      '<section class="hero-vote__grid" aria-live="polite"></section>'
    ].join("");

    bindShell(app, state);
    renderGrid(app, state);
  }

  function filteredHeroes(state) {
    var query = state.query.trim().toLowerCase();
    var heroes = state.heroes.filter(function (hero) {
      return !query || hero.title.toLowerCase().indexOf(query) >= 0 || hero.slug.toLowerCase().indexOf(query) >= 0;
    });
    if (state.sort === "votes") {
      heroes.sort(function (a, b) { return b.votes - a.votes || a.rank - b.rank; });
    } else if (state.sort === "name") {
      heroes.sort(function (a, b) { return a.title.localeCompare(b.title, "zh-Hans-CN"); });
    } else {
      heroes.sort(function (a, b) { return a.rank - b.rank; });
    }
    return heroes;
  }

  function renderGrid(app, state) {
    var grid = qs(app, ".hero-vote__grid");
    var heroes = filteredHeroes(state);
    if (!heroes.length) {
      grid.innerHTML = '<div class="hero-vote__empty">没有匹配的英雄。</div>';
      return;
    }
    grid.innerHTML = heroes.map(function (hero) {
      var initials = hero.title.replace(/[（(].*?[）)]/g, "").trim().slice(0, 2);
      var style = hero.banner ? ' style="--hero-vote-image:url(\'' + htmlEscape(hero.banner) + '\')"' : "";
      var isDisabled = !!hero.disabledReason;
      var buttonText = isDisabled ? hero.disabledReason : (hero.voted ? "已支持" : "投一票");
      return [
        '<article class="hero-vote-card' + (hero.voted ? " is-voted" : "") + (isDisabled ? " is-disabled" : "") + '"' + style + ' data-hero="' + htmlEscape(hero.slug) + '">',
        '  <a class="hero-vote-card__link" href="' + heroHref(hero) + '" aria-label="查看' + htmlEscape(hero.title) + '页面"></a>',
        '  <div class="hero-vote-card__media" aria-hidden="true"><span>' + htmlEscape(initials) + '</span></div>',
        '  <div class="hero-vote-card__body">',
        '    <h3>' + htmlEscape(hero.title) + '</h3>',
        '    <p>当前支持 <strong>' + hero.votes + '</strong> 票</p>',
        '    <a class="hero-vote-card__wiki" href="' + heroHref(hero) + '">查看 Wiki</a>',
        '  </div>',
        '  <button class="hero-vote-card__button" type="button" data-vote="' + htmlEscape(hero.slug) + '"' + ((hero.voted || isDisabled) ? " disabled" : "") + '>',
        '    <span class="hero-vote-card__icon" aria-hidden="true">♥</span>',
        '    <span>' + htmlEscape(buttonText) + '</span>',
        '  </button>',
        '</article>'
      ].join("");
    }).join("");

    qsa(grid, "[data-vote]").forEach(function (button) {
      button.addEventListener("click", function (event) {
        event.preventDefault();
        vote(state, button.getAttribute("data-vote"), button);
      });
    });
  }

  function bindShell(app, state) {
    var search = qs(app, "input[type='search']");
    search.addEventListener("input", function () {
      state.query = search.value;
      renderGrid(app, state);
    });

    qsa(app, "[data-sort]").forEach(function (button) {
      button.addEventListener("click", function () {
        state.sort = button.getAttribute("data-sort");
        qsa(app, "[data-sort]").forEach(function (item) {
          item.setAttribute("aria-selected", item === button ? "true" : "false");
        });
        renderGrid(app, state);
      });
    });
  }

  function applyResults(state, payload) {
    var bySlug = {};
    (payload.results || []).forEach(function (row) {
      bySlug[row.hero] = Number(row.votes || 0);
    });
    var voted = payload.voted || readLocalVotes(state.pollId);
    var locked = readLockedVotes(state.pollId);
    var local = readLocalVotes(state.pollId);
    state.heroes.forEach(function (hero) {
      hero.votes = bySlug[hero.slug] || 0;
      hero.voted = voted.indexOf(hero.slug) >= 0 || locked.indexOf(hero.slug) >= 0 || local.indexOf(hero.slug) >= 0;
    });
  }

  function updateCounters(state) {
    var total = state.heroes.reduce(function (sum, hero) { return sum + hero.votes; }, 0);
    var votedCount = state.heroes.filter(function (hero) { return hero.voted; }).length;
    var totalNode = qs(state.app, "[data-total-votes]");
    var votedNode = qs(state.app, "[data-voted-count]");
    if (totalNode) totalNode.textContent = total;
    if (votedNode) votedNode.textContent = votedCount;
  }

  function burst(button) {
    var card = button.closest(".hero-vote-card");
    if (!card) return;
    card.classList.add("is-popping");
    for (var i = 0; i < 12; i++) {
      var particle = document.createElement("i");
      particle.className = "hero-vote-particle";
      particle.style.setProperty("--x", Math.cos(i / 12 * Math.PI * 2) * (26 + Math.random() * 22) + "px");
      particle.style.setProperty("--y", Math.sin(i / 12 * Math.PI * 2) * (22 + Math.random() * 18) + "px");
      particle.style.setProperty("--d", (Math.random() * 80) + "ms");
      button.appendChild(particle);
      setTimeout(function (node) { node.remove(); }, 700, particle);
    }
    setTimeout(function () { card.classList.remove("is-popping"); }, 420);
  }

  function vote(state, slug, button) {
    var hero = state.heroes.find(function (item) { return item.slug === slug; });
    if (!hero || hero.voted || hero.disabledReason || state.loading) return;
    if (cooldownActive(state.pollId)) {
      state.error = "操作太快了，请稍等几秒再投。";
      render(state.app, state);
      return;
    }

    if (state.localOnly) {
      hero.voted = true;
      hero.votes += 1;
      var localDemoVotes = readLocalVotes(state.pollId);
      if (localDemoVotes.indexOf(slug) < 0) {
        localDemoVotes.push(slug);
        writeLocalVotes(state.pollId, localDemoVotes);
      }
      state.error = "后端尚未接入，本次投票仅作为本地动效演示。";
      burst(button);
      updateCounters(state);
      window.setTimeout(function () { renderGrid(state.app, state); }, 360);
      return;
    }

    state.loading = true;
    hero.voted = true;
    lockVote(state.pollId, slug);
    button.disabled = true;
    fetchApi(state, "/api/votes", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ poll: state.pollId, hero: slug })
    }, 6000)
      .then(function (res) {
        return res.json().then(function (payload) {
          if (!res.ok && payload.error !== "vote_limit_reached") throw new Error("投票提交失败");
          payload.rateLimited = payload.error === "vote_limit_reached";
          return payload;
        });
      })
      .then(function (payload) {
        if (payload.rateLimited) {
          unlockVote(state.pollId, slug);
          hero.voted = false;
          startCooldown(state.pollId);
          applyResults(state, payload);
          state.error = "本轮投票已达到上限，先看看其他玩家的结果吧。";
          return;
        }
        var localVotes = readLocalVotes(state.pollId);
        if (localVotes.indexOf(slug) < 0) {
          localVotes.push(slug);
          writeLocalVotes(state.pollId, localVotes);
        }
        applyResults(state, payload);
        state.error = "";
        burst(button);
      })
      .catch(function () {
        unlockVote(state.pollId, slug);
        hero.voted = false;
        startCooldown(state.pollId);
        state.error = "投票服务暂时不可用，请稍后再试。";
      })
      .finally(function () {
        state.loading = false;
        updateCounters(state);
        renderGrid(state.app, state);
      });
  }

  function loadResults(state) {
    var localVotes = readLocalVotes(state.pollId);
    var lockedVotes = readLockedVotes(state.pollId);
    state.heroes.forEach(function (hero) {
      hero.voted = localVotes.indexOf(hero.slug) >= 0 || lockedVotes.indexOf(hero.slug) >= 0;
      if (state.localOnly && hero.voted && hero.votes === 0) hero.votes = 1;
    });
    render(state.app, state);
    if (state.localOnly) {
      return;
    }
    fetchApi(state, "/api/votes?poll=" + encodeURIComponent(state.pollId), {}, 4500)
      .then(function (res) {
        if (!res.ok) throw new Error("结果加载失败");
        return res.json();
      })
      .then(function (payload) {
        applyResults(state, payload);
      })
      .catch(function () {
        state.error = "投票结果加载失败，当前显示本地状态。";
      })
      .finally(function () {
        render(state.app, state);
      });
  }

  function init() {
    var app = document.getElementById("hero-vote-app");
    if (!app || app.dataset.initialized === "true") return;
    app.dataset.initialized = "true";
    loadResults(createState(app));
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
