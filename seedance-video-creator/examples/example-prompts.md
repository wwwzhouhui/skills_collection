# Seedance 2.0 分镜提示词示例库

## 示例一：情感叙事类

**场景**：男人下班回家的温情故事

```
电影级写实风格，10秒，16:9宽屏，温馨家庭氛围

0-2秒：中景跟随镜头，男人疲惫地走在走廊，脚步逐渐变缓
2-4秒：脸部特写，男人深呼吸，调整情绪，表情变得轻松，手插入钥匙开门
4-7秒：室内中景，小女儿和宠物狗欢快地跑过来迎接，男人蹲下拥抱
7-9秒：近景，男人脸上洋溢着幸福的笑容，室内暖光营造温馨氛围
9-10秒：全景拉远，一家人温馨画面定格

背景音效：轻缓的钢琴配乐，脚步声、开门声、孩子的笑声
```

**API 调用**（带角色参考图）：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0" \
  -F "prompt=电影级写实风格，10秒，16:9宽屏，温馨家庭氛围\n\n0-2秒：中景跟随镜头，@1 疲惫地走在走廊，脚步逐渐变缓\n2-4秒：脸部特写，@1 深呼吸调整情绪，表情变得轻松，手插入钥匙开门\n4-7秒：室内中景，@2 和宠物狗欢快地跑过来迎接，@1 蹲下拥抱\n7-10秒：近景，@1 脸上洋溢幸福笑容，室内暖光营造温馨氛围" \
  -F "ratio=16:9" \
  -F "duration=10" \
  -F "files=@/path/to/father.jpg" \
  -F "files=@/path/to/daughter.jpg"
```

---

## 示例二：动作打斗类

**场景**：武侠风格双人对打

```
中国水墨武侠风格，10秒，16:9，枫叶飘落的秋季场景

0-2秒：远景，@1 持长枪和 @2 持双刀对峙，杀气弥漫
2-4秒：快速推近，两人眼神交锋，枫叶缓缓飘落
4-8秒：中景快速剪辑，长枪突刺，双刀格挡，武器碰撞火花四溅，枫叶被气浪卷起
8-10秒：定格pose，两人武器相交，画面渐隐

金属碰撞音效 + 古风激昂配乐
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0" \
  -F "prompt=中国水墨武侠风格，10秒，16:9，枫叶飘落的秋季场景\n\n0-2秒：远景，@1 持长枪和 @2 持双刀对峙，杀气弥漫\n2-4秒：快速推近，两人眼神交锋，枫叶缓缓飘落\n4-8秒：中景快速剪辑，长枪突刺，双刀格挡，武器碰撞火花四溅\n8-10秒：定格pose，两人武器相交，画面渐隐" \
  -F "ratio=16:9" \
  -F "duration=10" \
  -F "files=@/path/to/warrior1.jpg" \
  -F "files=@/path/to/warrior2.jpg"
```

---

## 示例三：产品广告类

**场景**：咖啡品牌广告（纯文本，无参考图）

```
高端商业广告风格，10秒，16:9，暖色调晨光氛围

0-2秒：微距特写，咖啡液缓缓注入杯中，油脂丰富，蒸汽升腾
2-4秒：中景环绕，手握咖啡杯，阳光透过窗户洒在桌面
4-7秒：推镜头至咖啡豆，一粒咖啡豆从上方飘落，镜头跟随推进
7-8秒：画面黑屏转场
8-10秒：文字渐显，品牌名 + slogan

咖啡倒入声 + 轻松的爵士乐
```

**API 调用**（纯文本生成）：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "seedance-2.0",
    "prompt": "高端商业广告风格，10秒，16:9，暖色调晨光氛围\n\n0-2秒：微距特写，咖啡液缓缓注入杯中，油脂丰富，蒸汽升腾\n2-4秒：中景环绕，手握咖啡杯，阳光透过窗户洒在桌面\n4-7秒：推镜头至咖啡豆，一粒咖啡豆从上方飘落，镜头跟随推进\n7-8秒：画面黑屏转场\n8-10秒：文字渐显，品牌名 + slogan\n\n咖啡倒入声 + 轻松的爵士乐",
    "ratio": "16:9",
    "resolution": "720p",
    "duration": 10
  }'
```

---

## 示例四：科幻穿梭类

**场景**：科幻世界穿梭（多图参考）

```
赛博朋克科幻风格，10秒，16:9，霓虹光效

0-2秒：@1 戴上虚拟科幻眼镜，特写
2-4秒：极速环绕镜头，从第三人称变成主观视角，在AI虚拟世界中穿梭
4-7秒：镜头推进至深邃蓝色宇宙（参考@2），飞船穿梭向远方
7-9秒：视角仰拍，穿梭到像素世界（参考@3），低空飞过像素山林
9-10秒：掠过纹理星球表面（参考@4），画面定格

电子音效 + 科幻氛围配乐
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0" \
  -F "prompt=赛博朋克科幻风格，10秒，16:9，霓虹光效\n\n0-2秒：@1 戴上虚拟科幻眼镜，特写\n2-4秒：极速环绕镜头，在AI虚拟世界中穿梭\n4-7秒：镜头推进至深邃蓝色宇宙（参考@2），飞船穿梭\n7-9秒：穿梭到像素世界（参考@3），低空飞过像素山林\n9-10秒：掠过星球表面（参考@4），画面定格" \
  -F "ratio=16:9" \
  -F "duration=10" \
  -F "files=@/path/to/character.jpg" \
  -F "files=@/path/to/universe.jpg" \
  -F "files=@/path/to/pixel_world.jpg" \
  -F "files=@/path/to/planet.jpg"
```

---

## 示例五：音乐卡点类

**场景**：时尚换装展示（竖屏短视频）

```
时尚MV风格，10秒，9:16竖屏，高饱和炫彩

0-2秒：快速四格闪切，@1 @2 @3 @4 四款造型依次定格
2-4秒：音乐重拍，@1 全身展示，鱼眼镜头效果
4-6秒：快速切换 @2 造型，重影闪烁效果
6-8秒：@3 造型，镜头推拉有节奏
8-10秒：@4 造型炫影特效，四款并排定格收尾

节奏感强的电子音乐，鼓点清晰
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0" \
  -F "prompt=时尚MV风格，10秒，9:16竖屏，高饱和炫彩\n\n0-2秒：快速四格闪切，@1 @2 @3 @4 四款造型依次定格\n2-4秒：音乐重拍，@1 全身展示，鱼眼镜头效果\n4-6秒：快速切换 @2 造型，重影闪烁\n6-8秒：@3 造型，镜头推拉有节奏\n8-10秒：@4 造型炫影特效，四款并排定格" \
  -F "ratio=9:16" \
  -F "duration=10" \
  -F "files=@/path/to/look1.jpg" \
  -F "files=@/path/to/look2.jpg" \
  -F "files=@/path/to/look3.jpg" \
  -F "files=@/path/to/look4.jpg"
```

---

## 示例六：情绪演绎类

**场景**：情绪爆发（单图参考 + 纯文本）

```
戏剧化写实风格，10秒，16:9，压抑到爆发的情绪曲线

0-2秒：中景，@1 走到镜子前，看着镜中自己
2-4秒：脸部特写，沉思表情，眼神逐渐变化
4-7秒：突然崩溃大叫，抓镜子的动作，情绪完全爆发
7-9秒：慢动作，眼泪滑落
9-10秒：画面渐暗，只剩镜中倒影

从安静到突然爆发的音效，情绪配乐
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0" \
  -F "prompt=戏剧化写实风格，10秒，16:9，压抑到爆发\n\n0-2秒：中景，@1 走到镜子前\n2-4秒：脸部特写，沉思表情\n4-7秒：突然崩溃大叫，情绪爆发\n7-10秒：慢动作，眼泪滑落，画面渐暗" \
  -F "ratio=16:9" \
  -F "duration=10" \
  -F "files=@/path/to/character.jpg"
```

---

## 示例七：一镜到底类

**场景**：谍战追踪镜头

```
谍战片风格，10秒，16:9宽屏，紧张氛围

0-2秒：@1 红衣女特工正面向前走，全景，路人遮挡
2-4秒：镜头跟随到拐角处（参考@2），女子离开画面
4-7秒：@3 戴面具女孩在拐角躲着，恶狠狠盯着，镜头摇向红衣女子
7-9秒：红衣女子走进豪宅（参考@4）消失不见
9-10秒：镜头推近豪宅大门，画面定格

全程一镜到底，保持紧张节奏
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0" \
  -F "prompt=谍战片风格，10秒，16:9宽屏，紧张氛围，全程一镜到底\n\n0-2秒：@1 红衣女特工正面向前走，路人遮挡\n2-4秒：镜头跟随到拐角处（参考@2）\n4-7秒：@3 戴面具女孩在拐角躲着盯着\n7-9秒：红衣女子走进豪宅（参考@4）\n9-10秒：镜头推近豪宅大门定格" \
  -F "ratio=16:9" \
  -F "duration=10" \
  -F "files=@/path/to/spy_woman.jpg" \
  -F "files=@/path/to/corner.jpg" \
  -F "files=@/path/to/mask_girl.jpg" \
  -F "files=@/path/to/mansion.jpg"
```

---

## 视频下载通用脚本

所有示例生成完成后，使用以下方式下载视频：

```bash
# 将 API 响应保存并提取 URL 下载
RESPONSE=$(curl -s --max-time 300 -X POST "http://127.0.0.1:8000/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"model":"seedance-2.0","prompt":"...","ratio":"16:9","duration":10}')

VIDEO_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url')

if [ "${VIDEO_URL}" != "null" ] && [ -n "${VIDEO_URL}" ]; then
  OUTPUT="seedance_$(date +%Y%m%d_%H%M%S).mp4"
  curl -L -o "${OUTPUT}" "${VIDEO_URL}"
  echo "下载完成: ${OUTPUT} ($(du -h "${OUTPUT}" | cut -f1))"
else
  echo "生成失败: $(echo "${RESPONSE}" | jq -r '.error.message // .message // "未知错误"')"
fi
```
