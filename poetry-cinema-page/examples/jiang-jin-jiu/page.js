/* ============================================================
   《将进酒》页面行为
   - 渲染：hero / 七幕 / 结语 / 章节导航
   - 图像舞台：两层交叉淡入（移动端另加模糊底衬）
   - 激活判定：视口 30% 处最近的段落（按几何位置，不用滚动百分比）
   - 载入层有 onError 与超时兜底；单张图失败会被记住，不会被反复重试
   ============================================================ */

(function () {
  'use strict';

  var poem = window.POEM;
  if (!poem) {
    console.error('[poem] window.POEM 未找到，检查 poem-config.js 是否先于 page.js 加载');
    return;
  }

  // ---------------------------------------------------------- 小工具

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;   // 一律用 textContent，杜绝 HTML 注入
    return node;
  }

  var motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  var reduceMotion = motionQuery.matches;
  motionQuery.addEventListener('change', function (event) {
    reduceMotion = event.matches;              // 用户中途改系统设置也生效
  });

  // ---------------------------------------------------------- 微型视觉组件

  function renderMicro(micro) {
    var box = el('div', 'micro micro-' + micro.type);

    if (micro.label) box.appendChild(el('p', 'micro-label', micro.label));

    if (micro.type === 'scale') {
      box.appendChild(el('div', 'rail'));
      var ends = el('div', 'ends');
      micro.marks.forEach(function (mark) {
        ends.appendChild(el('span', mark.side, mark.text));
      });
      box.appendChild(ends);
    }

    if (micro.type === 'contrast') {
      var pair = el('div', 'pair');
      [micro.left, micro.right].forEach(function (side, i) {
        var cell = el('div', 'side' + (i === 1 ? ' hi' : ''));
        cell.appendChild(el('span', 'big', side.text));
        cell.appendChild(el('span', 'sub', side.sub));
        pair.appendChild(cell);
        if (i === 0) pair.appendChild(el('div', 'divider'));
      });
      box.appendChild(pair);
    }

    if (micro.type === 'verbs') {
      var beats = el('div', 'beats');
      micro.beats.forEach(function (beat) {
        beats.appendChild(el('span', 'beat ' + beat.tone, beat.verb));
      });
      box.appendChild(beats);
    }

    if (micro.type === 'counter') {
      box.appendChild(el('div', 'value', micro.value));
      box.appendChild(el('p', 'caption', micro.caption));
    }

    if (micro.type === 'timeline') {
      var rows = el('div', 'rows');
      micro.rows.forEach(function (row) {
        var line = el('div', 'row ' + row.state);
        line.appendChild(el('span', 'tag', row.tag));
        line.appendChild(el('span', 'text', row.text));
        line.appendChild(el('span', 'result', row.result));
        rows.appendChild(line);
      });
      box.appendChild(rows);
    }

    if (micro.note) box.appendChild(el('p', 'micro-note', micro.note));
    return box;
  }

  // ---------------------------------------------------------- 渲染内容

  function renderHero() {
    document.getElementById('heroKicker').textContent = poem.kicker;
    document.getElementById('heroTitle').textContent = poem.title;
    document.getElementById('heroAuthor').textContent = poem.author;
    document.getElementById('heroEra').textContent = poem.era;
    document.getElementById('heroLine').textContent = poem.definingLine;
    document.getElementById('heroIntro').textContent = poem.intro;
    document.title = poem.title + ' · ' + poem.author + '｜沉浸式解读';
  }

  function renderBeats() {
    var main = document.getElementById('main');
    var anchor = document.getElementById('closing');

    poem.sections.forEach(function (section, index) {
      var node = el('section', 'poem-section');
      node.id = section.id;
      node.dataset.scene = String(index + 1);   // 0 是 hero

      var card = el('article', 'card reveal');

      var eyebrow = el('p', 'card-eyebrow');
      eyebrow.appendChild(el('span', 'numeral', section.index));
      eyebrow.appendChild(el('span', 'chapter', section.chapter));
      card.appendChild(eyebrow);

      card.appendChild(el('h2', null, section.original));   // 原文用 pre-line 保留换行
      card.appendChild(el('p', 'literal', section.literal));
      card.appendChild(el('p', 'analysis', section.analysis));

      if (section.micro) card.appendChild(renderMicro(section.micro));

      node.appendChild(card);
      main.insertBefore(node, anchor);
    });
  }

  function renderClosing() {
    var closing = poem.closing;
    document.getElementById('closingHeading').textContent = closing.heading;
    document.getElementById('closingLead').textContent = closing.lead;

    var list = document.getElementById('closingLayers');
    closing.layers.forEach(function (layer) {
      list.appendChild(el('dt', null, layer.term));
      list.appendChild(el('dd', null, layer.text));
    });

    document.getElementById('variantsHeading').textContent = closing.variants.heading;
    document.getElementById('variantsText').textContent = closing.variants.text;
  }

  function renderNav() {
    var nav = document.getElementById('chapters');
    poem.nav.forEach(function (item) {
      var link = el('a', null, item.label);
      link.href = '#' + item.id;
      link.dataset.target = item.id;
      nav.appendChild(link);
    });
  }

  // ---------------------------------------------------------- 图像舞台

  var images = [poem.heroImage].concat(poem.sections.map(function (s) { return s.image; }));

  var stageFront = document.getElementById('stageFront');
  var stageBack = document.getElementById('stageBack');
  var stageBlur = document.getElementById('stageBlur');

  var currentIndex = 0;
  var desiredIndex = 0;
  var busy = false;
  var FADE_MS = 1100;
  var failed = {};        // 已确认载入失败的图：记录后不再重试，避免滚动时反复报错

  function commit(index) {
    var src = images[index];
    currentIndex = index;

    stageBack.src = src;
    stageBlur.src = src;

    // 把 front 静默复位，为下一次淡入做准备
    stageFront.style.transition = 'none';
    stageFront.style.opacity = '0';
    void stageFront.offsetWidth;              // 强制回流，确保复位立即生效
    stageFront.style.transition = '';
  }

  function reconcile() {
    if (busy || desiredIndex === currentIndex) return;

    var index = desiredIndex;
    busy = true;
    stageFront.src = images[index];

    var begin = function () {
      // 用户可能在等待加载期间又滚走了
      if (desiredIndex !== index) {
        busy = false;
        reconcile();
        return;
      }
      stageFront.style.opacity = '1';

      var finish = function () {
        commit(index);
        busy = false;
        reconcile();
      };

      if (reduceMotion) finish();
      else window.setTimeout(finish, FADE_MS);
    };

    if (stageFront.complete && stageFront.naturalWidth > 0) begin();
    else {
      stageFront.onload = begin;
      stageFront.onerror = function () {
        // 单张图失败不应卡住整页：记下来并保持当前画面，继续响应后续滚动
        console.warn('[poem] 图像加载失败，保持当前画面：' + images[index]);
        failed[index] = true;
        busy = false;
      };
    }
  }

  function requestScene(index) {
    if (index < 0 || index >= images.length) return;
    if (failed[index]) return;                 // 该图不可用，不做无谓重试
    desiredIndex = index;
    reconcile();
  }

  // 预取相邻段落，让交叉淡入时不必等待网络
  function preloadNeighbours(index) {
    [index - 1, index + 1].forEach(function (i) {
      if (i >= 0 && i < images.length && !failed[i]) {
        var img = new Image();
        img.decoding = 'async';
        img.src = images[i];
      }
    });
  }

  // ---------------------------------------------------------- 滚动主循环

  var sections = [];
  var navLinks = [];
  var progressBar = document.getElementById('progressBar');
  var ticking = false;

  function update() {
    ticking = false;

    // 激活段落：取「上沿」最接近视口 30% 处的那个，而不是按滚动总百分比
    var target = window.innerHeight * 0.3;
    var active = sections[0];
    var best = Infinity;

    for (var i = 0; i < sections.length; i++) {
      var distance = Math.abs(sections[i].getBoundingClientRect().top - target);
      if (distance < best) {
        best = distance;
        active = sections[i];
      }
    }

    for (var j = 0; j < sections.length; j++) {
      var isActive = sections[j] === active;
      sections[j].classList.toggle('active', isActive);
      if (navLinks[j]) {
        if (isActive) navLinks[j].setAttribute('aria-current', 'true');
        else navLinks[j].removeAttribute('aria-current');
      }
    }

    var scene = Number(active.dataset.scene || 0);
    requestScene(scene);
    preloadNeighbours(scene);

    var scrollable = document.documentElement.scrollHeight - window.innerHeight;
    var ratio = scrollable > 0 ? Math.min(1, Math.max(0, window.scrollY / scrollable)) : 0;
    progressBar.style.width = (ratio * 100).toFixed(2) + '%';
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(update);
    }
  }

  // ---------------------------------------------------------- 朗读控件

  function setupNarration() {
    if (!poem.audioSrc) return;   // 未提供音频时不渲染控件

    var tools = document.getElementById('tools');
    var button = el('button', 'narration', '朗读');
    button.type = 'button';
    button.setAttribute('aria-pressed', 'false');
    tools.appendChild(button);

    var audio = new Audio(poem.audioSrc);
    audio.preload = 'metadata';
    audio.hidden = true;
    document.body.appendChild(audio);

    var setState = function (state) {
      var playing = state === 'playing';
      button.classList.toggle('playing', playing);
      button.setAttribute('aria-pressed', String(playing));
      button.textContent = playing ? '暂停'
        : state === 'ended' ? '重播'
        : state === 'error' ? '音频不可用'
        : '朗读';
    };

    var play = function (automatic) {
      audio.play()['catch'](function (error) {
        var blocked = automatic && error && error.name === 'NotAllowedError';
        setState(blocked ? 'idle' : 'error');   // 自动播放被拦截不是错误
      });
    };

    button.addEventListener('click', function () {
      if (!audio.paused) audio.pause();
      else {
        if (audio.ended) audio.currentTime = 0;
        play(false);
      }
    });

    audio.addEventListener('playing', function () { setState('playing'); });
    audio.addEventListener('pause', function () { if (!audio.ended) setState('idle'); });
    audio.addEventListener('ended', function () { setState('ended'); });
    audio.addEventListener('error', function () { setState('error'); });

    play(true);
  }

  // ---------------------------------------------------------- 载入层

  function dismissLoading() {
    var loading = document.getElementById('loading');
    if (loading) loading.classList.add('done');
  }

  function setupLoading() {
    var hero = new Image();
    var settled = false;

    var settle = function (failedFlag) {
      if (settled) return;
      settled = true;
      if (failedFlag) {
        var loading = document.getElementById('loading');
        // 主图失败也要退出载入态，只是把话说明白
        if (loading) {
          loading.textContent = '主视觉未能载入，文字内容仍可阅读';
          window.setTimeout(dismissLoading, 2200);
        }
      } else {
        dismissLoading();
      }
    };

    hero.onload = function () { settle(false); };
    hero.onerror = function () { settle(true); };
    hero.src = poem.heroImage;

    // 兜底：无论图片状态如何，8 秒后一定退出载入层
    window.setTimeout(function () { settle(false); }, 8000);
  }

  // ---------------------------------------------------------- 启动

  renderHero();
  renderBeats();
  renderClosing();
  renderNav();

  sections = Array.prototype.slice.call(document.querySelectorAll('.poem-section'));
  navLinks = poem.nav.map(function (item) {
    return document.querySelector('.chapters a[data-target="' + item.id + '"]');
  });

  // 结语不引入新图，沿用最后一幕的画面
  var closingNode = document.getElementById('closing');
  closingNode.dataset.scene = String(images.length - 1);

  // 先亮出 hero，避免首屏空白
  stageBack.src = images[0];
  stageBlur.src = images[0];

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);

  setupNarration();
  setupLoading();
  update();

  // 便于浏览器验收：暴露内部状态
  window.__poem = {
    images: images,
    get current() { return currentIndex; },
    get desired() { return desiredIndex; },
    get failed() { return Object.keys(failed); },
  };
})();
