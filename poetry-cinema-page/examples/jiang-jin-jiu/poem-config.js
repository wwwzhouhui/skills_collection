/**
 * 《将进酒》页面数据。
 * 与 scene-map.md 的段落记录表一一对应：原文 / 直译 / 细读 / 微型视觉组件。
 */
window.POEM = {
  title: '将进酒',
  author: '李白',
  era: '唐 · 天宝年间',
  kicker: '乐府歌行 · 劝酒歌',
  definingLine: '君不见，黄河之水天上来，奔流到海不复回。',
  intro:
    '一场从白昼喝到破晓的酒。他把黄河、镜子、月亮、剑和裘衣都拉进来，只为了问一件事：既然时间不回头，此刻该怎么活。',
  audioSrc: 'public/audio/jiang-jin-jiu-doubao.mp3', // 由 scripts/narration.py 生成（豆包 seed-tts-2.0 · qingcang 男声）
  heroImage: 'public/generated/jiang-jin-jiu/hero.jpg',

  sections: [
    {
      id: 'beat-1',
      image: 'public/generated/jiang-jin-jiu/scene-1.jpg',
      index: '壹',
      chapter: '时空之大',
      original: '君不见，黄河之水天上来，\n奔流到海不复回。',
      literal:
        '你没看见吗——黄河之水仿佛从天而降，一路奔涌入海，再也不会回头。',
      analysis:
        '开篇不写酒，先写一条河。视角被拉到高空，河水从「天上来」到「不复回」，一句话就走完了从起点到终点的全过程。真正被写出来的不是水，是「不可逆」：它越壮观，越像时间。这两句把读者抬到天地的高度，只是为了下一句骤然收进一面镜子时，落差够狠。',
      micro: {
        type: 'scale',
        label: '空间尺度',
        marks: [
          { text: '天上来', side: 'left', weight: 1 },
          { text: '不复回', side: 'right', weight: 0.35 },
        ],
        note: '起于极高，止于极远；中间没有停顿',
      },
    },
    {
      id: 'beat-2',
      image: 'public/generated/jiang-jin-jiu/scene-2.jpg',
      index: '贰',
      chapter: '生命之短',
      original: '君不见，高堂明镜悲白发，\n朝如青丝暮成雪。',
      literal:
        '你没看见吗——高堂明镜里令人悲叹的白发，早晨还是青丝，傍晚已如白雪。',
      analysis:
        '第二个「君不见」，镜头从天地缩到一面镜子、一双眼。夸张用在这里格外毒：把一生的衰老压进「朝」到「暮」一天之内。前一段用的是空间的远，这一段用的是时间的短，两个尺度合起来，才逼出后面那句「须尽欢」——不是享乐主义的鸡汤，是被时间追出来的结论。',
      micro: {
        type: 'contrast',
        label: '一日之内',
        left: { text: '朝', sub: '青丝' },
        right: { text: '暮', sub: '成雪' },
        note: '一生的长度被压缩成一天',
      },
    },
    {
      id: 'beat-3',
      image: 'public/generated/jiang-jin-jiu/scene-3.jpg',
      index: '叁',
      chapter: '豪迈自解',
      original: '人生得意须尽欢，莫使金樽空对月。\n天生我材必有用，千金散尽还复来。',
      literal:
        '人生得意就该尽情欢乐，别让金樽空对着月亮；上天生我必有去处，千金散尽也还会再来。',
      analysis:
        '情绪第一次掉头向上。「莫使金樽空对月」是行动指令，「天生我材必有用」是自我估价——两者之间没有论证，是直接宣布。注意「千金散尽还复来」的口气：他不是在算账，是在把「钱」的重量当场卸下。这份底气正是全诗此后所有挥霍的许可证。',
      micro: {
        type: 'verbs',
        label: '动词节奏',
        beats: [
          { verb: '尽欢', tone: 'high' },
          { verb: '莫使', tone: 'mid' },
          { verb: '必有用', tone: 'high' },
          { verb: '还复来', tone: 'high' },
        ],
        note: '四个短促的判断句连打，语气一句比一句硬',
      },
    },
    {
      id: 'beat-4',
      image: 'public/generated/jiang-jin-jiu/scene-4.jpg',
      index: '肆',
      chapter: '纵饮狂欢',
      original: '烹羊宰牛且为乐，会须一饮三百杯。\n岑夫子，丹丘生，将进酒，杯莫停。',
      literal:
        '烹羊宰牛暂且行乐，要喝就得一次喝三百杯；岑夫子，丹丘生，快来喝酒，杯子不要停。',
      analysis:
        '抽象的豪言落地成动作：宰、烹、饮、举杯。孤独的独酌在这里被换成群饮——两个朋友被直接点名喊进诗里，诗句从此有了听众。「三百杯」不是量词，是态度的计量单位；「杯莫停」三个字把节奏也带快了，读起来像在催。',
      micro: {
        type: 'counter',
        label: '酒量即态度',
        value: '三百杯',
        caption: '以数字写豪气：不可信的数字，恰恰是可信的情绪',
      },
    },
    {
      id: 'beat-5',
      image: 'public/generated/jiang-jin-jiu/scene-5.jpg',
      index: '伍',
      chapter: '价值反叛',
      original: '与君歌一曲，请君为我倾耳听。\n钟鼓馔玉不足贵，但愿长醉不复醒。',
      literal:
        '我为你们唱一曲，请侧耳倾听；钟鼓之乐、珍馐之味都不值得珍视，只愿长醉不再醒来。',
      analysis:
        '由「饮」转「歌」，放纵升级为宣言。此前是劝人喝，这里是当众宣判「钟鼓馔玉不足贵」——被否定的是整套世俗价值排序，而不只是某一件事。「不复醒」说得极狠：他要的不是醉，是拒绝醒来面对那面镜子。这就是前面「悲白发」的账单。',
      micro: {
        type: 'contrast',
        label: '价值天平',
        left: { text: '钟鼓馔玉', sub: '世人以为贵' },
        right: { text: '长醉不醒', sub: '他要的' },
        note: '当场把天平压向「不值」的一端',
      },
    },
    {
      id: 'beat-6',
      image: 'public/generated/jiang-jin-jiu/scene-6.jpg',
      index: '陆',
      chapter: '历史共鸣',
      original: '古来圣贤皆寂寞，惟有饮者留其名。\n陈王昔时宴平乐，斗酒十千恣欢谑。',
      literal:
        '自古以来的圣贤都已寂寞无闻，只有善饮的人留下了名字；陈王曹植当年宴饮平乐观，斗酒万钱，纵情戏谑。',
      analysis:
        '他为自己的行为找历史依据，请出曹植。「圣贤皆寂寞」是一句极重的挑衅——把立德立言的正途判为无效，反而给「饮者」发了一张留名的凭证。有酒意上头时的自我辩护成分，但正是这份不讲理的自信，把个人的放纵托进了历史的长河里。',
      micro: {
        type: 'timeline',
        label: '两条留名之路',
        rows: [
          { tag: '古', text: '圣贤', result: '寂寞', state: 'lost' },
          { tag: '今', text: '饮者', result: '留名', state: 'won' },
          { tag: '典', text: '陈王曹植 · 平乐观', result: '斗酒十千，恣欢谑', state: 'won' },
        ],
        note: '用典故为自己背书：孤独在这里被接进了一条谱系',
      },
    },
    {
      id: 'beat-7',
      image: 'public/generated/jiang-jin-jiu/scene-7.jpg',
      index: '柒',
      chapter: '销万古愁',
      original:
        '主人何为言少钱，径须沽取对君酌。\n五花马，千金裘，呼儿将出换美酒，\n与尔同销万古愁。',
      literal:
        '主人何必说钱不够，只管买酒来喝；五花马、千金裘，叫孩子拿出去换美酒，和你们一同消解这万古的愁。',
      analysis:
        '终幕把价值倒置做到极致：用最贵的东西去换最便宜的东西——马、裘换酒。这不是失控，是清醒的取舍，所以他姿态里有一种近乎悲壮的洒脱。最后三个字是全诗的升格器：「万古愁」把一己的短促，接到时间的长度上去。全诗从「黄河之水不复回」开始，到这里才承认：愁本身也是万古的，那就用万古的酒去销它。',
      micro: {
        type: 'scale',
        label: '愁的尺度',
        marks: [
          { text: '我', side: 'left', weight: 0.25 },
          { text: '万古', side: 'right', weight: 1 },
        ],
        note: '个人的愁被抬进永恒：与开篇的黄河遥相对称',
      },
    },
  ],

  closing: {
    heading: '全诗解读',
    lead: '《将进酒》不是一首劝人喝酒的诗，是一首关于「时间不可逆」的诗，酒只是唯一的对策。',
    layers: [
      {
        term: '体式',
        text: '乐府歌行。题目即「劝酒歌」，句式长短错落，以呼告（君不见、岑夫子、丹丘生、主人）推进节奏，适合即席放歌，不适合案头吟咏。',
      },
      {
        term: '结构',
        text: '三起三落：以黄河与明镜两记「君不见」下坠，以「须尽欢」「天生我材」两度上扬，再以「与君歌」「古来圣贤」把放纵推进到历史维度，最后以「换美酒」收束。每次下坠都比上次更沉，每次上扬都比上次更放。',
      },
      {
        term: '意象系统',
        text: '两条线索贯穿：流动的（黄河、酒、月）与凝固的（镜、剑、裘）。流动的表示时间与消解，凝固的表示世俗价值；终幕让凝固的（马、裘）去换流动的（酒），完成了意象层面的交换。',
      },
      {
        term: '技法',
        text: '夸张（三百杯、斗酒十千、万古愁）、对偶（黄河对明镜、青丝对白雪）、用典（曹植平乐观）、呼告与顶真式的递进。夸张在此不是修辞装饰，而是把抽象的情绪换算成可计量的尺度的工具。',
      },
      {
        term: '核心张力',
        text: '「时间的不可逆」对「此刻的极度挥霍」。他从不否认时间的胜利，只是在承认它的前提下，要求把每一个此刻都用到极限——这才是这首诗意气风发同时又异常沉重的原因。',
      },
    ],
    variants: {
      heading: '文本异文',
      text: '本页采用通行本。主要异文：「但愿长醉不复醒」一作「不用醒」；「径须沽取对君酌」一作「沽酒对君酌」；「与尔同销万古愁」一作「同消」；「钟鼓馔玉不足贵」一作「钟鼎玉帛」。这些差异不影响本页的解读。',
    },
  },

  nav: [
    { id: 'opening', label: '序' },
    { id: 'beat-1', label: '壹' },
    { id: 'beat-2', label: '贰' },
    { id: 'beat-3', label: '叁' },
    { id: 'beat-4', label: '肆' },
    { id: 'beat-5', label: '伍' },
    { id: 'beat-6', label: '陆' },
    { id: 'beat-7', label: '柒' },
    { id: 'closing', label: '解' },
  ],
};
