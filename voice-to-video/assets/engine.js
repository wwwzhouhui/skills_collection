/* HF — 口播视频合成引擎(确定性时钟驱动)
 *
 * 核心约定: 一切画面状态都是时间 t(毫秒) 的纯函数。
 *   HF.seek(t)  —— 把整个 DOM 设到 t 时刻的状态; 相同 t 永远得到相同画面。
 *   HF.play()   —— 预览模式: 用 <audio> 的 currentTime 作为时钟逐帧 seek(画音天然同步)。
 * 渲染器(render.py)只调用 seek(); 预览只调用 play()/pause()。
 *
 * 页面需提供:
 *   .scene 元素, 带 data-start / data-end(毫秒); 不写 data-end 则自动停到下一场景开始或片尾
 *   元素可带 data-anim(data-delay data-dur data-ease data-out data-out-dur)
 *   window.SUBTITLES = [{text,start,end,words:[{w,t,d}]}]  (tts.py 的 timeline.json.sentences)
 *   #hf-subtitle / #hf-progress-fill / #hf-timecode 可选容器
 *   #hf-audio 指定配音文件名(预览用)
 */
(function () {
  "use strict";

  // ---------- 缓动 ----------
  var EASE = {
    linear: function (p) { return p; },
    out: function (p) { return 1 - Math.pow(1 - p, 3); },
    in: function (p) { return p * p * p; },
    inout: function (p) { return p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; },
    back: function (p) { var c = 1.70158; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); },
    spring: function (p) { return 1 - Math.cos(p * Math.PI * 1.35) / Math.pow(2 * p + 1, 2.2) / .35; }
  };

  function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }
  function num(v, dflt) { return (v === undefined || v === "" || isNaN(+v)) ? dflt : +v; }

  var HF = {
    ready: false,
    t: 0,
    playing: false,
    durationMs: Infinity,
    cfg: { audio: "", subtitle: true, karaoke: true, timecode: false },
    scenes: [],       // {el, start, end}
    anims: [],        // {el, type, base, dur, ease, scene, out, outDur}
    subs: [],
    _renderers: [],
    _subCache: {},
  };

  // ---------- 场景收集 ----------
  function collectScenes() {
    var els = [].slice.call(document.querySelectorAll(".scene"));
    HF.scenes = els.map(function (el, i) {
      var start = num(el.dataset.start, i * 3000);
      var end = el.dataset.end !== undefined ? num(el.dataset.end, start + 3000) : null;
      return { el: el, i: i, start: start, explicitEnd: end, end: end };
    });
    // 未显式给 data-end 的场景: 停到下一个显式/隐式边界, 最后由 setDuration 兜底
    for (var i = 0; i < HF.scenes.length; i++) {
      var s = HF.scenes[i];
      if (s.explicitEnd === null) {
        var nextStart = (HF.scenes[i + 1] && HF.scenes[i + 1].start) || HF.durationMs;
        s.end = Math.min(nextStart, HF.durationMs);
      }
    }
  }

  // ---------- 声明式动画收集 ----------
  function collectAnims() {
    HF.anims = [];
    [].slice.call(document.querySelectorAll("[data-anim]")).forEach(function (el) {
      var sceneEl = el.closest(".scene");
      var scene = sceneEl && HF.scenes.filter(function (s) { return s.el === sceneEl; })[0];
      var base = (scene ? scene.start : 0) + num(el.dataset.delay, 0);
      HF.anims.push({
        el: el, type: el.dataset.anim, scene: scene,
        base: base, dur: num(el.dataset.dur, 500),
        ease: EASE[el.dataset.ease] || EASE.out,
        out: el.dataset.out || null, outDur: num(el.dataset.outDur, 350),
        text: el.textContent, countTo: num(el.dataset.count, NaN),
      });
    });
  }

  function applyAnim(a, t) {
    var el = a.el;
    if (a.type === "count") {
      var p = a.ease(clamp((t - a.base) / a.dur, 0, 1));
      var v = Math.round(a.countTo * p);
      var suffix = el.dataset.suffix || "";
      el.textContent = v.toLocaleString("en-US") + suffix;
      el.style.opacity = t >= a.base ? 1 : 0;
      return;
    }
    if (a.type === "type") { // 打字机
      var p2 = clamp((t - a.base) / a.dur, 0, 1);
      var n = Math.round(a.text.length * p2);
      el.textContent = a.text.slice(0, n);
      el.style.opacity = n > 0 ? 1 : 0;
      return;
    }
    var e = a.ease(clamp((t - a.base) / a.dur, 0, 1));
    var ox = 0, oy = 0, sc = 1, op = e, clip = null;
    switch (a.type) {
      case "up": oy = (1 - e) * 42; break;
      case "down": oy = -(1 - e) * 42; break;
      case "left": ox = (1 - e) * 60; break;   // 从右往左进
      case "right": ox = -(1 - e) * 60; break; // 从左往右进
      case "pop": sc = .82 + .18 * e; break;
      case "fade": break;
      case "wipe-l": clip = "inset(0 " + (1 - e) * 100 + "% 0 0)"; break;
      case "wipe-r": clip = "inset(0 0 0 " + (1 - e) * 100 + "%)"; break;
      default: break;
    }
    // 出场
    if (a.out && a.scene) {
      var ob = a.scene.end - a.outDur;
      if (t > ob) {
        var eo = clamp((t - ob) / a.outDur, 0, 1);
        op *= (1 - eo);
        if (a.out === "up") oy -= eo * 30;
        if (a.out === "down") oy += eo * 30;
        if (a.out === "pop") sc *= 1 - eo * .08;
      }
    }
    var tr = "";
    if (ox || oy) tr += "translate(" + ox.toFixed(2) + "px," + oy.toFixed(2) + "px) ";
    if (sc !== 1) tr += "scale(" + sc.toFixed(4) + ") ";
    el.style.transform = tr || "none";
    el.style.opacity = op.toFixed(3);
    if (clip !== null) el.style.clipPath = clip;
  }

  // ---------- 字幕(逐句 + 逐词卡拉OK) ----------
  var WORD_RE = /[\p{L}\p{N}]/u;

  // 词边界不含标点: 从原句文本里把词之间的标点/空格并回显示, 卡拉OK更自然
  function karaokeSpans(box, s) {
    var text = s.text || "", ti = 0;
    s.words.forEach(function (w, k) {
      var wn = (String(w.w).match(new RegExp(WORD_RE.source, "gu")) || [w.w]).length;
      var start = ti, cnt = 0, end;
      while (ti < text.length && cnt < wn) { if (WORD_RE.test(text[ti])) cnt++; ti++; }
      if (k + 1 < s.words.length) {           // 吞到下一词开始之前的标点
        var j = ti;
        while (j < text.length && !WORD_RE.test(text[j])) j++;
        end = ti = j;
      } else {
        end = text.length;                     // 末词吞掉剩余(含句尾标点)
      }
      var sp = document.createElement("span");
      sp.textContent = text.slice(start, end) || w.w;
      sp.dataset.t = w.t; sp.dataset.d = w.d;
      box.appendChild(sp);
    });
  }

  function buildSub(i) {
    var s = HF.subs[i];
    var box = document.createElement("div");
    box.className = "hf-sent";
    if (HF.cfg.karaoke && s.words && s.words.length) {
      karaokeSpans(box, s);
    } else {
      box.textContent = s.text;
    }
    return box;
  }

  function renderSubtitle(t) {
    var box = document.getElementById("hf-subtitle");
    if (!box) return;
    var cur = -1;
    for (var i = 0; i < HF.subs.length; i++) {
      var s = HF.subs[i];
      var showEnd = (i + 1 < HF.subs.length)
        ? Math.min(HF.subs[i + 1].start, s.end + 800)
        : s.end + 800;
      if (t >= s.start && t < showEnd) { cur = i; break; }
    }
    if (cur < 0) { box.innerHTML = ""; box.dataset.i = "-1"; return; }
    if (box.dataset.i !== String(cur)) {
      box.innerHTML = "";
      box.appendChild(buildSub(cur));
      box.dataset.i = String(cur);
    }
    if (HF.cfg.karaoke) {
      var s2 = HF.subs[cur];
      [].slice.call(box.children[0].children).forEach(function (sp) {
        var wt = +sp.dataset.t, wd = +sp.dataset.d;
        var on = t >= wt && t < wt + wd;
        var done = t >= wt + wd;
        sp.className = done ? "done" : (on ? "on" : "");
      });
    }
  }

  // ---------- seek: 一切状态的唯一入口 ----------
  HF.seek = function (t) {
    t = clamp(+t || 0, 0, HF.durationMs);
    HF.t = t;
    var i, s;
    for (i = 0; i < HF.scenes.length; i++) {
      s = HF.scenes[i];
      var end = s.explicitEnd !== null ? s.explicitEnd
        : (HF.scenes[i + 1] ? HF.scenes[i + 1].start : HF.durationMs);
      var active = t >= s.start && t < end;
      if (active) {
        if (s.el.style.display !== "block") s.el.style.display = "block";
        s.el.dataset.p = clamp((t - s.start) / Math.max(1, end - s.start), 0, 1);
      } else if (s.el.style.display !== "none") {
        s.el.style.display = "none";
      }
    }
    for (i = 0; i < HF.anims.length; i++) {
      var a = HF.anims[i];
      if (a.scene && a.scene.el.style.display === "none") {
        // 场景隐藏时仍需落位, 保证截图首帧正确
      }
      applyAnim(a, t);
    }
    for (i = 0; i < HF._renderers.length; i++) HF._renderers[i](t);
    if (HF._videos.length) syncVideos(t);
    renderSubtitle(t);

    var fill = document.getElementById("hf-progress-fill");
    if (fill && isFinite(HF.durationMs)) {
      fill.style.width = (clamp(t / HF.durationMs, 0, 1) * 100).toFixed(3) + "%";
    }
    var tc = document.getElementById("hf-timecode");
    if (tc) tc.textContent = fmtTC(t) + " / " + fmtTC(HF.durationMs);
  };

  function fmtTC(ms) {
    var s = Math.floor(ms / 1000);
    return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2) + "." + ("0" + Math.floor(ms % 1000 / 100)).slice(-1);
  }

  // ---------- 预览播放(时钟 = 音频 currentTime) ----------
  var audioEl = null, rafId = 0;

  function loop() {
    if (!HF.playing) return;
    var t = audioEl ? audioEl.currentTime * 1000 : HF.t + 16.7;
    if (t >= HF.durationMs) {
      HF.seek(HF.durationMs);
      HF.pause();
      return;
    }
    HF.seek(t);
    rafId = requestAnimationFrame(loop);
  }

  HF.play = function () {
    if (HF.playing) return;
    HF.playing = true;
    if (audioEl) {
      if (HF.t >= HF.durationMs - 50) HF.seek(0);
      audioEl.currentTime = HF.t / 1000;
      var pr = audioEl.play();
      if (pr && pr.catch) pr.catch(function () { });
    }
    document.body.classList.add("hf-playing");
    for (var vi = 0; vi < HF._videos.length; vi++) {
      var rv = HF._videos[vi];
      try { rv.el.currentTime = Math.max(0, (HF.t - rv.offset) / 1000); rv.el.play().catch(function () { }); } catch (e) { }
    }
    rafId = requestAnimationFrame(loop);
  };
  HF.pause = function () {
    HF.playing = false;
    if (audioEl) audioEl.pause();
    for (var vi = 0; vi < HF._videos.length; vi++) { try { HF._videos[vi].el.pause(); } catch (e) { } }
    if (rafId) cancelAnimationFrame(rafId);
    document.body.classList.remove("hf-playing");
  };
  HF.toggle = function () { HF.playing ? HF.pause() : HF.play(); };
  HF.nudge = function (dMs) { HF.pause(); HF.seek(HF.t + dMs); };

  HF.on = function (fn) { HF._renderers.push(fn); };   // 自定义逐帧渲染

  // ---------- 面板内嵌视频素材(确定性 seek 同步) ----------
  HF._videos = [];
  // HF.bindVideo("#id 或元素", 场景相对偏移毫秒): 注册后每次 seek 会把视频 currentTime
  // 精确对到 (t-offset)/1000; 渲染器每帧前会等 HF.waitVideos() 确认 seek 完成。
  HF.bindVideo = function (el, offsetMs) {
    var v = typeof el === "string" ? document.querySelector(el) : el;
    if (!v || v.tagName !== "VIDEO") return null;
    v.muted = true; v.playsInline = true; v.preload = "auto";
    var rec = { el: v, offset: +offsetMs || 0 };
    HF._videos.push(rec);
    return v;
  };
  HF.waitVideos = function () {
    var raf2 = function () { return new Promise(function (res) { requestAnimationFrame(function () { requestAnimationFrame(function () { res(); }); }); }); };
    return Promise.all(HF._videos.map(function (r) {
      var v = r.el;
      var p = (!v.seeking && v.readyState >= 2) ? Promise.resolve() : new Promise(function (res) {
        var done = function () { v.removeEventListener("seeked", done); res(); };
        v.addEventListener("seeked", done);
        setTimeout(done, 1500);
      });
      return p.then(raf2);   // seeked 事件后仍需等合成器上帧, 否则截到黑帧
    }));
  };
  function syncVideos(t) {
    for (var i = 0; i < HF._videos.length; i++) {
      var r = HF._videos[i], v = r.el;
      if (HF.playing && !v.paused) continue;      // 播放态交给媒体时钟自走
      var target = Math.max(0, (t - r.offset) / 1000);
      if (isFinite(v.duration) && target > v.duration) target = v.duration;
      if (Math.abs(v.currentTime - target) > 0.034 && !v.seeking) {
        try { v.currentTime = target; } catch (e) { /* 未加载完时忽略 */ }
      }
    }
  }
  HF.setDuration = function (ms) {
    HF.durationMs = +ms || Infinity;
    for (var i = 0; i < HF.scenes.length; i++) {
      var s = HF.scenes[i];
      if (s.explicitEnd === null) {
        var nextStart = (HF.scenes[i + 1] && HF.scenes[i + 1].start) || HF.durationMs;
        s.end = Math.min(nextStart, HF.durationMs);
      }
    }
  };

  // ---------- 舞台缩放(预览用; 渲染时视口=舞台尺寸, scale=1) ----------
  HF.fit = function () {
    var stage = document.getElementById("stage");
    if (!stage) return;
    var w = num(stage.dataset.width, 1920), h = num(stage.dataset.height, 1080);
    var k = Math.min(window.innerWidth / w, window.innerHeight / h);
    stage.style.transform = "scale(" + k + ")";
    stage.style.left = ((window.innerWidth - w * k) / 2) + "px";
    stage.style.top = ((window.innerHeight - h * k) / 2) + "px";
  };

  HF.init = function (cfg) {
    if (HF.ready) return;
    Object.assign(HF.cfg, cfg || {});
    // SUBTITLES 可用 window.SUBTITLES 或 const SUBTITLES(全局词法作用域)声明
    var subs = window.SUBTITLES;
    if (!subs) { try { subs = (typeof SUBTITLES !== "undefined") ? SUBTITLES : null; } catch (e) { subs = null; } }
    if (subs) HF.subs = subs;
    HF.durationMs = HF.cfg.durationMs || Infinity;
    collectScenes();
    collectAnims();
    HF.fit();
    window.addEventListener("resize", HF.fit);

    if (HF.cfg.audio) {
      audioEl = new Audio(HF.cfg.audio);
      audioEl.preload = "auto";
      audioEl.addEventListener("loadedmetadata", function () {
        if (!HF.cfg.durationMs) HF.setDuration(audioEl.duration * 1000);
      });
    }
    // 预览交互: 空格播放, 方向键微调, 点击进度条跳转
    window.addEventListener("keydown", function (e) {
      if (e.code === "Space") { e.preventDefault(); HF.toggle(); }
      if (e.code === "ArrowRight") HF.nudge(5000);
      if (e.code === "ArrowLeft") HF.nudge(-5000);
    });
    var bar = document.getElementById("hf-progress");
    if (bar) {
      bar.addEventListener("click", function (e) {
        var r = bar.getBoundingClientRect();
        HF.pause();
        HF.seek(clamp((e.clientX - r.left) / r.width, 0, 1) * HF.durationMs);
      });
    }
    var stage = document.getElementById("stage");
    if (stage) {
      stage.addEventListener("click", function (e) {
        if (e.target.closest("#hf-progress")) return;
        HF.toggle();
      });
    }
    HF.seek(0);
    (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve())
      .then(function () { HF.ready = true; document.body.classList.add("hf-ready"); });
  };

  window.HF = HF;
})();
