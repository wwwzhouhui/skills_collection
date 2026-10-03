// 发布文案渲染：把 script.json 的 publish 段 + timeline 的时间轴，合成一份《发布文案.md》。
//
// 章节时间轴**由场景时间自动推导**，不手写 —— 因为 YouTube 对章节有硬性要求：
//   ① 第一条必须是 00:00  ② 至少 3 条  ③ 每条至少 10 秒
// 任一条不满足，整组章节会被 YouTube 直接忽略。所以这里会把不足 10 秒的场景自动并进当前章节。

const pad2 = (n) => String(n).padStart(2, '0');

/** 秒 → 章节时间戳（<1 小时用 M:SS，否则 H:MM:SS） */
export function stamp(sec) {
  const t = Math.max(0, Math.floor(sec));
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = t % 60;
  return h ? `${h}:${pad2(m)}:${pad2(s)}` : `${m}:${pad2(s)}`;
}

/**
 * 把场景合并成满足 YouTube 要求的章节分组。
 * 规则：当前章节已够长才允许开新章；不足 minSeconds 的场景并进当前章；
 *      末尾若剩一个过短的章节则并入上一章（避免出现一闪而过的章节）。
 */
export function groupChapters(scenes, minSeconds = 10) {
  const groups = [];
  for (let i = 0; i < scenes.length; i++) {
    const end = scenes[i].start + scenes[i].duration;
    const cur = groups[groups.length - 1];
    if (!cur || cur.end - cur.start >= minSeconds) {
      groups.push({ start: scenes[i].start, end, idxs: [i] });
    } else {
      cur.end = end;
      cur.idxs.push(i);
    }
  }
  if (groups.length > 1) {
    const last = groups[groups.length - 1];
    if (last.end - last.start < minSeconds) {
      const prev = groups[groups.length - 2];
      prev.end = last.end;
      prev.idxs.push(...last.idxs);
      groups.pop();
    }
  }
  return groups;
}

/** 按场景索引取标题，取不到就退化为屏上大字（heading） */
const titleAt = (list, scenes, i) => {
  const v = list && list[i];
  const t = v === undefined || v === null ? '' : String(v).trim();
  return t || String((scenes[i] || {}).heading || '').trim();
};

const bullets = (list) =>
  (list || [])
    .filter((x) => String(x || '').trim())
    .map((x) => `- ${String(x).trim()}`)
    .join('\n');

/**
 * 渲染《发布文案.md》。
 * ctx = { title, total, scenes, pub, ratios, engine, voice, speed, avatarLabel,
 *         hasEnCues, srtCount }
 */
export function renderPublish(ctx) {
  const { title, total, scenes, pub, ratios, engine, voice, speed, avatarLabel, hasEnCues, srtCount } = ctx;
  const yt = pub.youtube || {};
  const L = [];
  const p = (s = '') => L.push(s);
  const hr = () => {
    p();
    p('---');
    p();
  };

  const ratioLine = ratios.length > 1 ? `${ratios.join(' 与 ')} 双版本` : `${ratios.join(' / ')} 单版本`;
  const subLine = hasEnCues
    ? '`字幕.srt` · `字幕.vtt`（中文）｜ `字幕.en.srt` · `字幕.en.vtt`（英文）'
    : '`字幕.srt` · `字幕.vtt`（中文）｜ **英文字幕待补**（见文件末尾）';

  // ── 头 ────────────────────────────────────────────────────────────
  p(`# 发布文案 —《${title}》`);
  p();
  p(`> 成片：${total.toFixed(1)} 秒 ｜ ${scenes.length} 个分镜 ｜ ${ratioLine}`);
  p(`> 配音：${engine}（${voice}）@${speed}x ｜ 出镜形象：${avatarLabel}`);
  p(`> 字幕：${subLine}`);
  hr();

  // ── 主用标题 ──────────────────────────────────────────────────────
  p('## 主用标题（全平台通用）');
  p();
  p(`**${pub.title || title}**`);
  if (pub.titles && pub.titles.length) {
    p();
    p('备选：');
    p(bullets(pub.titles));
  }
  hr();

  // ── 时间轴 ────────────────────────────────────────────────────────
  // 章节（合并，满足 YouTube 每章 ≥10s）
  const groups = groupChapters(scenes, Number(yt.chapterMinSeconds) || 10);
  const zhTitles = yt.chapterTitles || null;
  const enTitles = yt.chapterTitlesEn || null;
  const zhChapters = groups.map((g) => ({ start: g.start, title: titleAt(zhTitles, scenes, g.idxs[0]) }));
  const enChapters = groups.map((g) => ({ start: g.start, title: titleAt(enTitles, scenes, g.idxs[0]) }));

  // 场景级时间轴（不合并）—— 给抖音/B站这类"看点导航"用，通过 {{chapters}} 插入。
  // 片尾卡（outro）没有标题也不该出现在导航里，剔除。
  const sceneChapters = scenes
    .filter((s) => s.kind !== 'outro' && String(s.heading || '').trim())
    .map((s) => `${stamp(s.start)} ${String(s.heading).trim()}`)
    .join('\n');
  const fill = (text) => String(text || '').trim().replace(/\{\{chapters\}\}/g, sceneChapters);

  // ── YouTube（中英双语） ───────────────────────────────────────────
  const youtubeSection = () => {
    const y = [];
    const q = (s = '') => y.push(s);
    const ytTitleZh = yt.title || pub.title || title;
    const ytTitleEn = yt.titleEn || '';
    const ytTags = (yt.tags || []).join(', ');
    const ytHash = yt.hashtags || pub.hashtags || '';

    q('## YouTube（中视频 · 双语）');
    q();
    q('YouTube 的标题、描述、字幕都建议**中英双语**：中文抓华语观众，英文吃搜索与外推。');
    q('两套字幕文件共用同一条时间轴，上传时语言分别选「中文（简体）」与「英语」。');
    q();

    q('### 标题（Title）');
    q();
    q('| 语言 | 标题 | 字符数 |');
    q('| --- | --- | --- |');
    if (ytTitleEn) q(`| English | ${ytTitleEn} | ${[...ytTitleEn].length} / 100 |`);
    q(`| 中文 | ${ytTitleZh} | ${[...ytTitleZh].length} / 100 |`);
    q();
    q('> 上限 100 字符；移动端只展示前 ~40 字符，**把钩子放在最前面**。');
    q();

    if (zhChapters.length >= 3) {
      q('### 章节（Chapters）');
      q();
      if (groups.length < scenes.length) {
        q(`> 已把 ${scenes.length} 个分镜合并为 ${groups.length} 章 —— YouTube 要求每章 ≥ 10 秒，`);
        q('> 不足 10 秒的分镜会被并进上一章，否则**整组章节都会失效**。');
        q('> 章节名取组内首个分镜的屏上大字；想精确控制就在 `publish.youtube.chapterTitles` 里逐条写。');
      } else {
        q(`> ${groups.length} 个分镜正好对应 ${groups.length} 章，全部满足 YouTube 每章 ≥ 10 秒的要求。`);
      }
      q();
      q('```');
      zhChapters.forEach((c, i) => {
        const en = enChapters[i].title;
        q(`${stamp(c.start)} ${c.title}${en && en !== c.title ? ` · ${en}` : ''}`);
      });
      q('```');
      q();
    } else {
      q('> ⚠️ 分镜不足以凑出 3 个 ≥10 秒的章节，YouTube 章节功能用不上 —— 描述里别放时间戳列表。');
      q();
    }

    q('### 描述（Description）');
    q();
    q('**English** — 整段复制粘贴');
    q();
    q('```');
    if (yt.descEn) q(String(yt.descEn).trim());
    if (enChapters.length >= 3) {
      q();
      q('⏱️ Chapters');
      enChapters.forEach((c) => q(`${stamp(c.start)} ${c.title}`));
    }
    if (yt.ctaEn) {
      q();
      q(String(yt.ctaEn).trim());
    }
    if (ytHash) {
      q();
      q(ytHash);
    }
    q('```');
    q();
    q('**中文** — 整段复制粘贴');
    q();
    q('```');
    if (yt.desc) q(String(yt.desc).trim());
    if (zhChapters.length >= 3) {
      q();
      q('⏱️ 章节');
      zhChapters.forEach((c) => q(`${stamp(c.start)} ${c.title}`));
    }
    if (yt.cta) {
      q();
      q(String(yt.cta).trim());
    }
    if (ytHash) {
      q();
      q(ytHash);
    }
    q('```');
    q();
    q('> 描述上限 5000 字符；**前 3 行是搜索与推荐的主力**，把最想说的一句放开头。');
    q();
    if (ytTags) {
      q('### 标签（Tags）');
      q();
      q('```');
      q(ytTags);
      q('```');
      q();
      q('> 上限 500 字符。写「别人会搜什么」，不是「你讲了什么」。');
      q();
    }
    q('### 话题标签（Hashtags）');
    q();
    q('```');
    q(ytHash || '(未填 publish.youtube.hashtags)');
    q('```');
    q();
    return y;
  };

  // 只有填了实质内容才渲染 YouTube 板块 —— 空模板不该产出一份半截文案
  const hasYt = Boolean(yt.title || yt.titleEn || yt.desc || yt.descEn || yt.tags);
  if (hasYt) {
    L.push(...youtubeSection());
    hr();
  } else {
    p('> ℹ️ 没写 `publish.youtube` 段，所以没有 YouTube 板块。');
    p('> 想补：见 `references/publish.md`。');
    hr();
  }

  // ── 其他平台 ──────────────────────────────────────────────────────
  const platforms = [
    ['视频号 / 朋友圈', pub.videoAccount],
    ['小红书', pub.xiaohongshu],
    ['抖音 / B 站', pub.douyin],
    ['公众号（导语）', pub.articleLead],
  ];
  let usedPlaceholder = false;
  for (const [name, body] of platforms) {
    const raw = String(body || '').trim();
    if (!raw) continue;
    if (raw.includes('{{chapters}}')) usedPlaceholder = true;
    p(`## ${name}`);
    p();
    p(fill(raw));
    hr();
  }

  if (pub.tags && pub.tags.length) {
    p('## 通用标签');
    p();
    p('```');
    p(pub.tags.join(', '));
    p('```');
    hr();
  }

  // ── 配套文件 ──────────────────────────────────────────────────────
  p('## 配套文件');
  p();
  p('| 文件 | 用途 |');
  p('| --- | --- |');
  p('| `final-16x9.mp4` | 横屏成片（1920×1080，YouTube / B 站 / 公众号） |');
  if (ratios.includes('9:16')) p('| `final-9x16.mp4` | 竖屏成片（1080×1920，抖音 / 视频号 / 小红书） |');
  p('| `字幕.srt` | 中文字幕（YouTube 上传 / 剪映导入） |');
  p('| `字幕.vtt` | 中文 WebVTT（YouTube 更推荐这个格式） |');
  if (hasEnCues) {
    p('| `字幕.en.srt` | 英文字幕（YouTube 语言选「英语」） |');
    p('| `字幕.en.vtt` | 英文 WebVTT |');
  }
  p('| `旁白稿.md` | 逐场景旁白与时长，改稿用 |');
  p();
  p('YouTube 上传字幕：进「字幕」页 → 添加语言「中文（简体）」上传 `字幕.vtt`；');
  p('再加一门「英语」上传 `字幕.en.vtt`。两份共用同一条时间轴，不会有偏移。');
  p();

  if (usedPlaceholder) {
    hr();
    p('> 平台文案里的 `{{chapters}}` 已替换为**场景级**时间轴（不合并）；');
    p('> YouTube 那份是**合并后**的章节，两者条数不同是正常的。');
    p();
  }

  if (!hasEnCues) {
    hr();
    p('## ⚠️ 英文字幕还没出');
    p();
    p(`\`script.json\` 的 \`publish.en.cues\` 需要 **${srtCount} 条**英文，与中文字幕逐条对应`);
    p('（`iph srt <期>` 可以把中文条数逐条列出来对照）。填好后重新 `iph build` 就会');
    p('自动生成 `字幕.en.srt` 与 `字幕.en.vtt`。条数对不上会跳过英文 —— 错位的时间轴比没有更糟。');
    p();
  }

  return `${L.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd()}\n`;
}
