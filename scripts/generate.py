#!/usr/bin/env python3
"""Generate images via gptnb /v1/images/generations endpoint."""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path

API_URL = os.environ.get("GPTNB_API_URL", "https://one-cn2.gptnb.ai/v1/images/generations")
EDITS_URL = os.environ.get(
    "GPTNB_EDITS_URL",
    "https://one-cn2.gptnb.ai/v1/images/edits",
)
KEY_FILE = Path.home() / ".newmax" / "skills" / "gptnb-image" / ".api_key"

ALLOWED_QUALITY = {"low", "medium", "high", "auto"}
SIZE_RE = re.compile(r"^(\d+)x(\d+)$")

ONBOARDING_MSG = """\
未找到 gptnb API key。请按以下任一方式配置：

  1. 临时使用环境变量：
       export GPTNB_API_KEY="sk-xxx"

  2. 持久化（推荐）写入用户配置文件：
       mkdir -p ~/.newmax/skills/gptnb-image
       echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.api_key
       chmod 600 ~/.newmax/skills/gptnb-image/.api_key

  3. 单次调用通过 --api-key 参数传入

如果还没有 key：
  → 前往 https://oneapi.gptnb.ai 注册账号并充值
  → 在「令牌 / API Keys」页新建一个令牌，复制以 sk- 开头的字符串
  → ⚠️ 激活令牌时务必选「api」分组（更稳定，超时/限流明显少）
  → 按上面任一方式配置即可
"""


def load_api_key(cli_key: str | None) -> str:
    if cli_key:
        return cli_key.strip()
    env_key = os.environ.get("GPTNB_API_KEY")
    if env_key:
        return env_key.strip()
    if KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    sys.stderr.write(ONBOARDING_MSG)
    sys.exit(2)


def validate_size(size: str) -> str:
    if size == "auto":
        return size
    m = SIZE_RE.match(size)
    if not m:
        sys.exit(f"size 格式错误: {size}（应为 WIDTHxHEIGHT 或 auto）")
    w, h = int(m.group(1)), int(m.group(2))
    if w % 16 or h % 16:
        sys.exit(f"size {size} 两边必须是 16 的倍数")
    if max(w, h) > 3840:
        sys.exit(f"size {size} 最长边不能超过 3840px")
    long_side, short_side = max(w, h), min(w, h)
    if long_side / short_side > 3:
        sys.exit(f"size {size} 长短边比不能超过 3:1")
    pixels = w * h
    if pixels < 655_360 or pixels > 8_294_400:
        sys.exit(f"size {size} 总像素 {pixels} 超出 [655,360, 8,294,400]")
    return size


def call_api(payload: dict, api_key: str, timeout: int, url: str = API_URL) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (gptnb-image-skill)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误: {e}")


def _encode_multipart(fields: dict, files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    """编码 multipart/form-data 请求体，返回 (body, boundary)。

    fields: 普通文本字段 dict[str, str/int/bool]
    files:  [(field_name, file_path), ...]
    """
    boundary = "----newmax-" + uuid.uuid4().hex
    parts: list[bytes] = []
    for key, val in fields.items():
        if val is None:
            continue
        s = str(val).lower() if isinstance(val, bool) else str(val)
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        )
        parts.append(s.encode("utf-8"))
        parts.append(b"\r\n")
    for field_name, fp in files:
        if not fp.is_file():
            sys.exit(f"找不到上传文件: {fp}")
        filename = fp.name
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            (
                f'Content-Disposition: form-data; '
                f'name="{field_name}"; filename="{filename}"\r\n'
            ).encode()
        )
        parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        parts.append(fp.read_bytes())
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def call_edits_api(
    fields: dict,
    image_files: list[Path],
    api_key: str,
    timeout: int,
    url: str = EDITS_URL,
) -> dict:
    """上传图片 + 字段，走 OpenAI 兼容的 /v1/images/edits 端点。

    多图时字段名按顺序为 image / image[] / image[1] / image[2]…，与不同代理实现兼容；
    若只有 1 张图就用经典字段名 `image`。
    """
    if not image_files:
        sys.exit("call_edits_api 至少需要 1 张输入图")
    if len(image_files) == 1:
        files = [("image", image_files[0])]
    else:
        # 大多数 OpenAI 兼容实现接受重复同名 `image` 字段表示多图
        files = [("image", fp) for fp in image_files]

    body, boundary = _encode_multipart(fields, files)
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (gptnb-image-skill)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {e.code} ({url}): {body}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误 ({url}): {e}")


def save_outputs(data: list[dict], out_dir: Path, prefix: str, ext: str = "png") -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for i, item in enumerate(data):
        ts = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{prefix}-{ts}-{i+1}.{ext}"
        path = out_dir / filename
        if "b64_json" in item and item["b64_json"]:
            path.write_bytes(base64.b64decode(item["b64_json"]))
            saved.append(str(path))
        elif "url" in item and item["url"]:
            try:
                with urllib.request.urlopen(item["url"], timeout=120) as r:
                    path.write_bytes(r.read())
                saved.append(str(path))
            except Exception as e:
                print(f"下载失败 {item['url']}: {e}", file=sys.stderr)
                saved.append(item["url"])
        else:
            print(f"未识别返回项: {item}", file=sys.stderr)
    return saved


DEFAULT_LAYER_PROMPT = (
    "把这张图按元素拆分成若干图层，每个元素独立成一张透明背景的 PNG，"
    "保持各元素相对位置不变，不要修改画面内容。"
)


def main() -> None:
    p = argparse.ArgumentParser(description="gptnb 图像生成")
    p.add_argument("--prompt", default=None,
                   help="图像描述（生成模式必填；分层上传图模式可选，默认用拆分模板）")
    p.add_argument("--model", default="gpt-image-2", help="模型名（默认 gpt-image-2）")
    p.add_argument("--n", type=int, default=1, help="生成数量（默认 1）")
    p.add_argument("--size", default="auto", help="尺寸 WIDTHxHEIGHT 或 auto（默认 auto）")
    p.add_argument("--quality", default="auto", choices=sorted(ALLOWED_QUALITY), help="质量")
    p.add_argument("--output-dir", default="outputs/gptnb-image", help="输出目录")
    p.add_argument("--prefix", default="gptnb", help="文件名前缀")
    p.add_argument("--timeout", type=int, default=300, help="请求超时秒数")
    p.add_argument("--api-key", default=None,
                   help="API key（优先级：CLI > GPTNB_API_KEY > ~/.newmax/skills/gptnb-image/.api_key）")
    p.add_argument("--api-url", default=None,
                   help="完整接口地址（默认按模式自动选 generations / edits）")
    p.add_argument("--output-format", default=None,
                   help="输出图像格式 png/jpeg/webp（默认不传；vip 模型自动 png）")
    p.add_argument("--response-format", default=None,
                   choices=["url", "b64_json"],
                   help="返回形式 url 或 b64_json（默认不传；vip 模型自动 url）")
    p.add_argument("--input-image", action="append", default=[],
                   help="上传本地图片做编辑/分层（multipart 上传），可重复传多张；"
                        "传入后自动走 /v1/images/edits 端点。"
                        "搭配 vip 模型可对任意上传图做元素拆分。")
    p.add_argument("--raw", action="store_true", help="只打印原始 JSON，不下载")
    args = p.parse_args()

    has_input_image = bool(args.input_image)
    is_vip = "vip" in args.model.lower()

    # 校验 prompt
    if not args.prompt:
        if has_input_image and is_vip:
            args.prompt = DEFAULT_LAYER_PROMPT
        else:
            sys.exit('--prompt 必填（仅"上传图 + vip 分层"模式可省略）')

    validate_size(args.size)
    if args.n < 1 or args.n > 10:
        sys.exit("n 应在 1-10 之间")

    api_key = load_api_key(args.api_key)

    # ── 路径 1：上传图 → 走 /v1/images/edits（multipart） ──
    if has_input_image:
        url = args.api_url or EDITS_URL
        image_paths = [Path(p).expanduser() for p in args.input_image]
        for ip in image_paths:
            if not ip.is_file():
                sys.exit(f"--input-image 文件不存在: {ip}")

        fields: dict = {
            "model": args.model,
            "prompt": args.prompt,
            "size": args.size,
        }
        if is_vip:
            fields["output_format"] = args.output_format or "png"
            fields["response_format"] = args.response_format or "url"
        else:
            fields["n"] = args.n
            fields["quality"] = args.quality
            if args.output_format:
                fields["output_format"] = args.output_format
            if args.response_format:
                fields["response_format"] = args.response_format

        result = call_edits_api(fields, image_paths, api_key, args.timeout, url)
        ext_hint = fields.get("output_format") or "png"

    # ── 路径 2：纯文本生成 → 走 /v1/images/generations（JSON） ──
    else:
        url = args.api_url or API_URL
        payload: dict = {
            "model": args.model,
            "prompt": args.prompt,
            "size": args.size,
        }
        if is_vip:
            payload["output_format"] = args.output_format or "png"
            payload["response_format"] = args.response_format or "url"
        else:
            payload["n"] = args.n
            payload["quality"] = args.quality
            if args.output_format:
                payload["output_format"] = args.output_format
            if args.response_format:
                payload["response_format"] = args.response_format

        result = call_api(payload, api_key, args.timeout, url)
        ext_hint = payload.get("output_format") or "png"

    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    data = result.get("data") or []
    if not data:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit("响应中无 data 字段")

    ext = ext_hint.lower()
    if ext == "jpg":
        ext = "jpeg"
    saved = save_outputs(data, Path(args.output_dir), args.prefix, ext=ext)
    print(json.dumps({"saved": saved, "count": len(saved)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
