#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimax 声音克隆: 一段本人录音 → 专属 voice_id, 之后 TTS 都用自己的声音

用法:
    python3 clone_voice.py <audio_file> --voice-id <自定义ID> [--preview-text "试听文案"]

    audio_file: mp3/m4a/wav, 时长 10 秒 ~ 5 分钟, <20MB。
                录音要求: 单人、安静环境、语速自然、不要背景音乐, 3 分钟左右效果最好。
    --voice-id: 自定义音色 ID, ≥8 位、字母开头、含字母和数字 (例: host-voice-default)。
                同一 ID 重复克隆会覆盖旧音色。

环境变量: MINIMAX_API_KEY (必需), MINIMAX_GROUP_ID / MINIMAX_API_HOST (可选)

流程:
    1. 上传音频 (purpose=voice_clone) → file_id
    2. 调 /v1/voice_clone → 绑定 voice_id
    3. (可选 --preview-text) 用新音色合成一段试听 mp3
    完成后把 voice_id 填进 storyboard.json 的 voice.voice_id 即可。

注意: 克隆音色首次用于合成时 Minimax 会收一次性费用; 克隆的声音只允许
用于本人授权的内容生产。
"""

import argparse
import binascii
import io
import json
import os
import re
import sys
import urllib.request
import uuid
from pathlib import Path


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


# 绕过系统代理直连 (本地抓包代理的自签证书会让 TLS 校验失败)
if not os.environ.get("MINIMAX_USE_PROXY"):
    urllib.request.install_opener(
        urllib.request.build_opener(urllib.request.ProxyHandler({})))


def api_base():
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        die("MINIMAX_API_KEY 未设置")
    host = os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com").rstrip("/")
    group_id = os.environ.get("MINIMAX_GROUP_ID")
    qs = f"?GroupId={group_id}" if group_id else ""
    return host, qs, api_key


def post_json(url, payload, api_key):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_file(path, api_key, host, qs):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()

    def field(name, value):
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    field("purpose", "voice_clone")
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode())
    body.write(path.read_bytes())
    body.write(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{host}/v1/files/upload{qs}",
        data=body.getvalue(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    status = out.get("base_resp", {}).get("status_code")
    if status != 0:
        die(f"上传失败 status_code={status}: {out.get('base_resp', {}).get('status_msg')}")
    file_id = (out.get("file") or {}).get("file_id")
    if not file_id:
        die(f"上传响应缺少 file_id: {out}")
    return file_id


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="本人录音 (mp3/m4a/wav, 10s~5min, <20MB)")
    ap.add_argument("--voice-id", required=True,
                    help="自定义音色 ID: ≥8 位、字母开头、含字母和数字, 例 host-voice-default")
    ap.add_argument("--preview-text", default=None, help="克隆完成后用新音色合成一段试听")
    ap.add_argument("--no-noise-reduction", action="store_true", help="关闭自动降噪")
    args = ap.parse_args()

    path = Path(args.audio)
    if not path.exists():
        die(f"找不到 {path}")
    if path.suffix.lower() not in (".mp3", ".m4a", ".wav"):
        die("只支持 mp3 / m4a / wav")
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb > 20:
        die(f"文件 {size_mb:.1f}MB 超过 20MB 上限, 先压一下: ffmpeg -i in.wav -b:a 128k out.mp3")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{7,}", args.voice_id) or not re.search(r"\d", args.voice_id):
        die("voice_id 需 ≥8 位、字母开头、只含字母数字、且至少一个数字, 例 host-voice-default")

    host, qs, api_key = api_base()

    print(f"==> 上传录音 {path.name} ({size_mb:.1f}MB)...")
    file_id = upload_file(path, api_key, host, qs)
    print(f"    ✓ file_id={file_id}")

    print(f"==> 克隆音色 → voice_id={args.voice_id} ...")
    payload = {
        "file_id": file_id,
        "voice_id": args.voice_id,
        "need_noise_reduction": not args.no_noise_reduction,
        "need_volume_normalization": True,
    }
    out = post_json(f"{host}/v1/voice_clone{qs}", payload, api_key)
    status = out.get("base_resp", {}).get("status_code")
    if status != 0:
        die(f"克隆失败 status_code={status}: {out.get('base_resp', {}).get('status_msg')}")
    print(f"    ✓ 克隆成功")

    if args.preview_text:
        print("==> 合成试听...")
        model = os.environ.get("MINIMAX_TTS_MODEL", "speech-02-hd")
        tts = post_json(f"{host}/v1/t2a_v2{qs}", {
            "model": model,
            "text": args.preview_text,
            "stream": False,
            "language_boost": "Chinese",
            "output_format": "hex",
            "voice_setting": {"voice_id": args.voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        }, api_key)
        status = tts.get("base_resp", {}).get("status_code")
        if status != 0:
            die(f"试听合成失败 status_code={status}: {tts.get('base_resp', {}).get('status_msg')} "
                "(音色本身已克隆成功, 可稍后重试)")
        preview = path.with_name(f"preview-{args.voice_id}.mp3")
        preview.write_bytes(binascii.unhexlify(tts["data"]["audio"]))
        print(f"    ✓ 试听 → {preview}")

    print()
    print(f"✅ 完成。把下面这段填进 storyboard.json 即可用自己的声音配音:")
    print(f'   "voice": {{ "provider": "minimax", "voice_id": "{args.voice_id}", "speed": 1.05 }}')


if __name__ == "__main__":
    main()
