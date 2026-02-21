# Seedance 2.0 分镜提示词示例库

> **重要**：Seedance 2.0 **必须至少提供一张参考图片**，不支持纯文本生成视频。
> 当没有用户图片时，需要先通过文生图 API 生成首帧参考图，再用图片+提示词调用 Seedance。

---

## 示例一：情感叙事类（有用户图片）

**场景**：男人下班回家的温情故事

**视频分镜提示词**：
```
电影级写实风格，10秒，16:9宽屏，温馨家庭氛围

@1 作为画面首帧参考

0-2秒：中景跟随镜头，@1 疲惫地走在走廊，脚步逐渐变缓
2-4秒：脸部特写，深呼吸调整情绪，表情变得轻松，手插入钥匙开门
4-7秒：室内中景，@2 和宠物狗欢快地跑过来迎接，@1 蹲下拥抱
7-10秒：近景，@1 脸上洋溢幸福笑容，室内暖光营造温馨氛围

背景音效：轻缓的钢琴配乐，脚步声、开门声、孩子的笑声
```

**API 调用**（直接使用用户图片，跳过文生图）：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=电影级写实风格，10秒，16:9宽屏，温馨家庭氛围

@1 作为画面首帧参考

0-2秒：中景跟随镜头，@1 疲惫地走在走廊，脚步逐渐变缓
2-4秒：脸部特写，深呼吸调整情绪，手插入钥匙开门
4-7秒：室内中景，@2 和宠物狗欢快地跑过来迎接，@1 蹲下拥抱
7-10秒：近景，@1 脸上洋溢幸福笑容，室内暖光营造温馨氛围

背景音效：轻缓的钢琴配乐，脚步声、开门声、孩子的笑声" \
  -F "ratio=16:9" \
  -F "resolution=720p" \
  -F "duration=10" \
  -F "files=@/path/to/father.jpg" \
  -F "files=@/path/to/daughter.jpg"
```

---

## 示例二：动作打斗类（有用户图片）

**场景**：武侠风格双人对打

**视频分镜提示词**：
```
中国水墨武侠风格，10秒，16:9，枫叶飘落的秋季场景

@1 和 @2 作为角色参考

0-2秒：远景，@1 持长枪和 @2 持双刀对峙，杀气弥漫
2-4秒：快速推近，两人眼神交锋，枫叶缓缓飘落
4-8秒：中景快速剪辑，长枪突刺，双刀格挡，武器碰撞火花四溅，枫叶被气浪卷起
8-10秒：定格pose，两人武器相交，画面渐隐

金属碰撞音效 + 古风激昂配乐
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=中国水墨武侠风格，10秒，16:9，枫叶飘落的秋季场景

@1 和 @2 作为角色参考

0-2秒：远景，@1 持长枪和 @2 持双刀对峙，杀气弥漫
2-4秒：快速推近，两人眼神交锋，枫叶缓缓飘落
4-8秒：中景快速剪辑，长枪突刺，双刀格挡，武器碰撞火花四溅
8-10秒：定格pose，两人武器相交，画面渐隐

金属碰撞音效 + 古风激昂配乐" \
  -F "ratio=16:9" \
  -F "resolution=720p" \
  -F "duration=10" \
  -F "files=@/path/to/warrior1.jpg" \
  -F "files=@/path/to/warrior2.jpg"
```

---

## 示例三：产品广告类（无用户图片 → 三阶段工作流）

**场景**：咖啡品牌广告

**第一阶段 - 首帧图片提示词**（用于文生图）：
```
高端商业广告风格，微距特写，透明玻璃杯中的咖啡液面，油脂丰富呈现金棕色光泽，蒸汽升腾，暖色调晨光从窗户斜射入，背景虚化的木质桌面
```

**第一阶段 - 视频分镜提示词**（用于 Seedance）：
```
高端商业广告风格，10秒，16:9，暖色调晨光氛围

@1 作为画面首帧参考

0-2秒：微距特写，咖啡液缓缓注入杯中，油脂丰富，蒸汽升腾
2-5秒：中景环绕，手握咖啡杯，阳光透过窗户洒在桌面
5-8秒：推镜头至咖啡豆，一粒咖啡豆从上方飘落，镜头跟随推进
8-10秒：画面渐暗，品牌文字渐显

咖啡倒入声 + 轻松的爵士乐
```

**第二阶段 - 文生图生成首帧**：
```bash
# 1. 调用文生图 API 生成首帧
RESPONSE=$(curl -s --max-time 120 -X POST "${API_URL}/v1/images/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jimeng-4.5",
    "prompt": "高端商业广告风格，微距特写，透明玻璃杯中的咖啡液面，油脂丰富呈现金棕色光泽，蒸汽升腾，暖色调晨光从窗户斜射入，背景虚化的木质桌面",
    "ratio": "16:9",
    "resolution": "2k"
  }')

# 2. 下载首帧图片
IMAGE_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url')
curl -sL -o /tmp/seedance_coffee_frame.png "${IMAGE_URL}"
```

**第三阶段 - Seedance 视频生成**：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=高端商业广告风格，10秒，16:9，暖色调晨光氛围

@1 作为画面首帧参考

0-2秒：微距特写，咖啡液缓缓注入杯中，油脂丰富，蒸汽升腾
2-5秒：中景环绕，手握咖啡杯，阳光透过窗户洒在桌面
5-8秒：推镜头至咖啡豆，一粒咖啡豆从上方飘落
8-10秒：画面渐暗，品牌文字渐显

咖啡倒入声 + 轻松的爵士乐" \
  -F "ratio=16:9" \
  -F "resolution=720p" \
  -F "duration=10" \
  -F "files=@/tmp/seedance_coffee_frame.png"
```

---

## 示例四：科幻穿梭类（有用户图片）

**场景**：科幻世界穿梭（多图参考）

**视频分镜提示词**：
```
赛博朋克科幻风格，10秒，16:9，霓虹光效

@1 作为角色参考，@2-@4 作为场景参考

0-2秒：@1 戴上虚拟科幻眼镜，特写
2-4秒：极速环绕镜头，从第三人称变成主观视角，在AI虚拟世界中穿梭
4-7秒：镜头推进至深邃蓝色宇宙（参考@2），飞船穿梭向远方
7-9秒：视角仰拍，穿梭到像素世界（参考@3），低空飞过像素山林
9-10秒：掠过纹理星球表面（参考@4），画面定格

电子音效 + 科幻氛围配乐
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=赛博朋克科幻风格，10秒，16:9，霓虹光效

@1 作为角色参考，@2-@4 作为场景参考

0-2秒：@1 戴上虚拟科幻眼镜，特写
2-4秒：极速环绕镜头，在AI虚拟世界中穿梭
4-7秒：镜头推进至深邃蓝色宇宙（参考@2），飞船穿梭
7-9秒：穿梭到像素世界（参考@3），低空飞过像素山林
9-10秒：掠过星球表面（参考@4），画面定格

电子音效 + 科幻氛围配乐" \
  -F "ratio=16:9" \
  -F "resolution=720p" \
  -F "duration=10" \
  -F "files=@/path/to/character.jpg" \
  -F "files=@/path/to/universe.jpg" \
  -F "files=@/path/to/pixel_world.jpg" \
  -F "files=@/path/to/planet.jpg"
```

---

## 示例五：橘猫捉螃蟹（无用户图片 → 三阶段工作流）

**场景**：可爱动画风格，橘猫在海边捉螃蟹

**第一阶段 - 首帧图片提示词**：
```
阳光明媚的海边沙滩，一只圆滚滚的橘色猫咪蹲在潮湿的沙滩上，好奇地盯着面前一只小螃蟹，金色阳光照射，海浪轻轻拍打岸边，色彩鲜明活泼，3D动画风格
```

**第一阶段 - 视频分镜提示词**：
```
可爱3D动画风格，4秒，9:16竖屏，阳光明媚的海边

@1 作为画面首帧参考

0-1秒：中景，画面中的橘猫好奇地盯着沙滩上的小螃蟹，海浪轻拍岸边
1-3秒：近景跟随，橘猫伸出爪子试探性地去抓螃蟹，螃蟹举起钳子反击，橘猫被吓得往后一跳，表情夸张可爱
3-4秒：中景微拉远，橘猫和螃蟹对峙，背景碧蓝大海和白色浪花

背景音效：欢快俏皮卡通配乐 + 海浪声
```

**第二阶段 - 文生图生成首帧**：
```bash
RESPONSE=$(curl -s --max-time 120 -X POST "${API_URL}/v1/images/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jimeng-4.5",
    "prompt": "阳光明媚的海边沙滩，一只圆滚滚的橘色猫咪蹲在潮湿的沙滩上，好奇地盯着面前一只小螃蟹，金色阳光照射，海浪轻轻拍打岸边，色彩鲜明活泼，3D动画风格",
    "ratio": "9:16",
    "resolution": "2k"
  }')

IMAGE_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url')
curl -sL -o /tmp/seedance_cat_frame.png "${IMAGE_URL}"
```

**第三阶段 - Seedance 视频生成**：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=可爱3D动画风格，4秒，9:16竖屏，阳光明媚的海边

@1 作为画面首帧参考

0-1秒：中景，画面中的橘猫好奇地盯着沙滩上的小螃蟹，海浪轻拍岸边
1-3秒：近景跟随，橘猫伸出爪子试探性地去抓螃蟹，螃蟹举起钳子反击，橘猫被吓得往后一跳，表情夸张可爱
3-4秒：中景微拉远，橘猫和螃蟹对峙，背景碧蓝大海和白色浪花

背景音效：欢快俏皮卡通配乐 + 海浪声" \
  -F "ratio=9:16" \
  -F "resolution=720p" \
  -F "duration=4" \
  -F "files=@/tmp/seedance_cat_frame.png"
```

---

## 示例六：情绪演绎类（有用户图片）

**场景**：情绪爆发（单图参考）

**视频分镜提示词**：
```
戏剧化写实风格，10秒，16:9，压抑到爆发的情绪曲线

@1 作为角色参考

0-2秒：中景，@1 走到镜子前，看着镜中自己
2-4秒：脸部特写，沉思表情，眼神逐渐变化
4-7秒：突然崩溃大叫，抓镜子的动作，情绪完全爆发
7-9秒：慢动作，眼泪滑落
9-10秒：画面渐暗，只剩镜中倒影

从安静到突然爆发的音效，情绪配乐
```

**API 调用**：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=戏剧化写实风格，10秒，16:9，压抑到爆发

@1 作为角色参考

0-2秒：中景，@1 走到镜子前
2-4秒：脸部特写，沉思表情
4-7秒：突然崩溃大叫，情绪爆发
7-10秒：慢动作，眼泪滑落，画面渐暗

从安静到突然爆发的音效，情绪配乐" \
  -F "ratio=16:9" \
  -F "resolution=720p" \
  -F "duration=10" \
  -F "files=@/path/to/character.jpg"
```

---

## 示例七：海边跳舞（无用户图片 → 三阶段工作流）

**场景**：女孩海边跳舞竖屏短视频

**第一阶段 - 首帧图片提示词**：
```
日落时分的海边沙滩，一位穿着白色飘逸长裙的年轻女孩站在海边，面朝大海，夕阳逆光照射，金色光晕笼罩全身，长发和裙摆被海风轻轻吹动，远处海平线上的落日将天空染成橘红色，脚边浅浅的海浪泡沫
```

**第一阶段 - 视频分镜提示词**：
```
电影级写实风格，4秒，9:16竖屏，日落黄金时刻

@1 作为画面首帧参考

0-1秒：中景，女孩面朝大海，裙摆被海风吹动，夕阳逆光
1-3秒：近景跟随，女孩开始旋转起舞，长发和裙摆飞扬，金色光晕
3-4秒：远景拉远，女孩在落日余晖中舞蹈的剪影定格

背景音效：海浪声 + 轻柔钢琴配乐
```

**第二阶段 - 文生图生成首帧**：
```bash
RESPONSE=$(curl -s --max-time 120 -X POST "${API_URL}/v1/images/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jimeng-4.5",
    "prompt": "日落时分的海边沙滩，一位穿着白色飘逸长裙的年轻女孩站在海边，面朝大海，夕阳逆光照射，金色光晕笼罩全身，长发和裙摆被海风轻轻吹动，远处海平线上的落日将天空染成橘红色，脚边浅浅的海浪泡沫",
    "ratio": "9:16",
    "resolution": "2k"
  }')

IMAGE_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url')
curl -sL -o /tmp/seedance_beach_frame.png "${IMAGE_URL}"
```

**第三阶段 - Seedance 视频生成**：
```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=电影级写实风格，4秒，9:16竖屏，日落黄金时刻

@1 作为画面首帧参考

0-1秒：中景，女孩面朝大海，裙摆被海风吹动，夕阳逆光
1-3秒：近景跟随，女孩开始旋转起舞，长发和裙摆飞扬，金色光晕
3-4秒：远景拉远，女孩在落日余晖中舞蹈的剪影定格

背景音效：海浪声 + 轻柔钢琴配乐" \
  -F "ratio=9:16" \
  -F "resolution=720p" \
  -F "duration=4" \
  -F "files=@/tmp/seedance_beach_frame.png"
```

---

## 视频下载通用脚本

所有示例生成完成后，使用以下方式提取 URL 并下载视频：

```bash
# 从 API 响应中提取视频 URL 并下载
VIDEO_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url')

if [ "${VIDEO_URL}" != "null" ] && [ -n "${VIDEO_URL}" ]; then
  OUTPUT="seedance_$(date +%Y%m%d_%H%M%S).mp4"
  curl -L -o "${OUTPUT}" "${VIDEO_URL}"
  echo "下载完成: ${OUTPUT} ($(du -h "${OUTPUT}" | cut -f1))"
else
  echo "生成失败: $(echo "${RESPONSE}" | jq -r '.error.message // .message // "未知错误"')"
fi
```

---

## 注意事项

- **Authorization 头需要 `Bearer` 前缀**，格式为 `Bearer your_sessionid`
- **Seedance 2.0 必须至少一张图片**，纯文本会返回 `{"code":-2001,"message":"Seedance 2.0 需要至少一张图片"}`
- 没有用户图片时，先调用文生图 API（`/v1/images/generations`）生成首帧，再用图片调 Seedance
- 视频时长支持 4-15 秒连续范围
- API 是同步阻塞的，视频生成通常需要 60-120 秒
- 视频下载 URL 有时效性，生成后应立即下载
