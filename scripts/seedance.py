#!/usr/bin/env python3
"""Generate videos via gptnb seedance proxy (Volcengine ark API compatible).

支持：
- 文生视频
- 图生视频（首帧 / 首尾帧）
- 多模态参考生视频（参考图/视频/音频任意组合）
- seedance 2.0 / 2.0 fast / 1.5 pro / 1.0 系列模型

异步任务流：POST 创建 → 轮询 GET → 下载产出视频。
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

API_URL_DEFAULT = os.environ.get(
    "GPTNB_SEEDANCE_API_URL",
    "https://one-cn2.gptnb.ai/seedance2/v3/contents/generations/tasks",
)
KEY_FILE = Path.home() / ".newmax" / "skills" / "gptnb-image" / ".seedance_api_key"

DEFAULT_MODEL = "doubao-seedance-2-0-260128"

ONBOARDING_MSG = """\
未找到 seedance 视频生成 API key。请按以下任一方式配置：

  1. 临时使用环境变量：
       export GPTNB_SEEDANCE_API_KEY="sk-xxx"

  2. 持久化（推荐）写入用户配置文件：
       mkdir -p ~/.newmax/skills/gptnb-image
       echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.seedance_api_key
       chmod 600 ~/.newmax/skills/gptnb-image/.seedance_api_key

  3. 单次调用通过 --api-key 参数传入

如果还没有 key：
  → 前往 https://oneapi.gptnb.ai 注册账号并充值
  → 在「令牌 / API Keys」页新建一个令牌，复制以 sk- 开头的字符串
  → ⚠️ 激活令牌时务必选「api」分组（更稳定，超时/限流明显少）
  → ⚠️ seedance 视频生成消耗额度较大，建议账户余额 ≥200 元
  → 按上面任一方式配置即可

注：seedance API key 与 gptnb-image 图像生成的 .api_key 单独维护。
    可以是同一个 sk-xxx，也可以分开（推荐分开，便于跟踪用量）。
"""


def load_api_key(cli_key: str | None) -> str:
    if cli_key:
        return cli_key.strip()
    env_key = os.environ.get("GPTNB_SEEDANCE_API_KEY")
    if env_key:
        return env_key.strip()
    if KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    sys.stderr.write(ONBOARDING_MSG)
    sys.exit(2)


def encode_local_file(path: Path, kind: str = "image") -> str:
    """本地文件 → data URL，自动嗅探 MIME。kind ∈ {image, video, audio}。"""
    if not path.is_file():
        sys.exit(f"找不到文件: {path}")
    size = path.stat().st_size
    if size > 30 * 1024 * 1024:
        print(
            f"⚠️  文件 {path.name} 体积 {size / 1024 / 1024:.1f}MB，"
            "Base64 编码后会进一步放大；接口请求体上限 64MB，"
            "建议改用公网 URL 形式传入",
            file=sys.stderr,
        )
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        ext = path.suffix.lower().lstrip(".")
        mime = f"{kind}/{ext}" if ext else f"{kind}/*"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def resolve_url_or_path(value: str, kind: str) -> str:
    """URL / asset:// 原样返回；本地文件转 data URL。"""
    if value.startswith(("http://", "https://", "data:", "asset://")):
        return value
    p = Path(value).expanduser()
    if p.is_file():
        return encode_local_file(p, kind=kind)
    sys.exit(f"无法解析 {kind} 输入: {value}（既不是 URL/asset，也不是存在的本地文件）")


def build_content(args: argparse.Namespace) -> list[dict]:
    content: list[dict] = []
    if args.prompt:
        content.append({"type": "text", "text": args.prompt})

    # 首帧
    if args.first_frame:
        content.append({
            "type": "image_url",
            "image_url": {"url": resolve_url_or_path(args.first_frame, "image")},
            "role": "first_frame",
        })
    # 尾帧
    if args.last_frame:
        content.append({
            "type": "image_url",
            "image_url": {"url": resolve_url_or_path(args.last_frame, "image")},
            "role": "last_frame",
        })
    # 单张图（首帧的简化别名）
    if args.image:
        content.append({
            "type": "image_url",
            "image_url": {"url": resolve_url_or_path(args.image, "image")},
        })
    # 多张参考图
    for ref in (args.reference_image or []):
        content.append({
            "type": "image_url",
            "image_url": {"url": resolve_url_or_path(ref, "image")},
            "role": "reference_image",
        })
    # 参考视频
    for v in (args.reference_video or []):
        content.append({
            "type": "video_url",
            "video_url": {"url": resolve_url_or_path(v, "video")},
            "role": "reference_video",
        })
    # 参考音频
    for a in (args.reference_audio or []):
        content.append({
            "type": "audio_url",
            "audio_url": {"url": resolve_url_or_path(a, "audio")},
            "role": "reference_audio",
        })

    return content


def call_api(method: str, url: str, payload: dict | None, api_key: str, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (gptnb-seedance-skill)",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {e.code} ({method} {url}): {body}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误 ({method} {url}): {e}")


def submit_task(payload: dict, api_key: str, api_url: str) -> str:
    result = call_api("POST", api_url, payload, api_key)
    task_id = result.get("id") or result.get("task_id")
    if not task_id:
        sys.exit(f"创建任务失败，响应缺少 id 字段: {json.dumps(result, ensure_ascii=False)}")
    return task_id


def query_task(task_id: str, api_key: str, api_url: str) -> dict:
    return call_api("GET", f"{api_url.rstrip('/')}/{task_id}", None, api_key)


def find_video_url(obj) -> str | None:
    """递归搜索响应里的 video_url 字段，兼容不同包装层级。"""
    if isinstance(obj, dict):
        v = obj.get("video_url")
        if isinstance(v, str) and v:
            return v
        # 也检查 url 字段位于明显的视频 wrapper 下
        for k, val in obj.items():
            r = find_video_url(val)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_video_url(v)
            if r:
                return r
    return None


def download_video(url: str, out_dir: Path, prefix: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{prefix}-{ts}.mp4"
    path = out_dir / filename
    with urllib.request.urlopen(url, timeout=600) as r:
        path.write_bytes(r.read())
    return str(path)


def main() -> None:
    p = argparse.ArgumentParser(description="seedance 视频生成（via gptnb 中转）")
    p.add_argument("--prompt", default="", help="文本提示词（描述期望生成的视频内容）")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"模型 ID（默认 {DEFAULT_MODEL}）。可选值见 references/seedance-models.md")

    # 输入媒体
    p.add_argument("--image", help="单张输入图片，URL 或本地路径（按首帧处理）")
    p.add_argument("--first-frame", help="首帧图片，URL 或本地路径")
    p.add_argument("--last-frame", help="尾帧图片，URL 或本地路径（与 --first-frame 配对）")
    p.add_argument("--reference-image", action="append", default=[],
                   help="参考图（可重复传多张，多模态参考生视频用）")
    p.add_argument("--reference-video", action="append", default=[],
                   help="参考视频（可重复，仅 seedance 2.0/2.0 fast）")
    p.add_argument("--reference-audio", action="append", default=[],
                   help="参考音频（可重复，仅 seedance 2.0/2.0 fast，必须搭配图/视频）")

    # 视频参数
    p.add_argument("--resolution", choices=["480p", "720p", "1080p"], help="分辨率")
    p.add_argument("--ratio", help="宽高比，如 16:9 / 9:16 / 1:1 / 3:4 / 4:3 / 21:9 / adaptive")
    p.add_argument("--duration", type=int,
                   help="时长秒数；2.0 系列 [4,15] 或 -1（自适应），1.0 系列 [2,12]")
    p.add_argument("--seed", type=int, help="随机种子，[-1, 2^32-1]")
    p.add_argument("--watermark", choices=["true", "false"], help="是否含水印（默认 false）")
    p.add_argument("--camera-fixed", choices=["true", "false"], help="固定摄像头（默认 false）")
    p.add_argument("--generate-audio", choices=["true", "false"],
                   help="生成同步音频（2.0/1.5 默认 true）")

    # 输出
    p.add_argument("--output-dir", default="outputs/seedance", help="视频输出目录")
    p.add_argument("--prefix", default="seedance", help="文件名前缀")

    # 任务控制
    p.add_argument("--poll-interval", type=int, default=8, help="轮询间隔秒数")
    p.add_argument("--timeout", type=int, default=900,
                   help="客户端总等待秒数（默认 15 分钟，超过则放弃轮询，任务仍在服务端跑）")
    p.add_argument("--api-key", help="单次覆盖 API key（优先级 CLI > GPTNB_SEEDANCE_API_KEY > 文件）")
    p.add_argument("--api-url", default=API_URL_DEFAULT, help="API 地址（默认 gptnb cn2 中转）")
    p.add_argument("--raw", action="store_true", help="只提交任务、返回 task_id；不轮询/下载")
    p.add_argument("--task-id", help="跳过提交，直接查询/下载已有任务（与 --raw 互补）")

    args = p.parse_args()

    api_key = load_api_key(args.api_key)

    # 直查模式：用户已有 task_id，跳过提交
    if args.task_id:
        task_id = args.task_id
        print(f"直查模式: {task_id}", file=sys.stderr)
    else:
        if not args.prompt and not (
            args.image or args.first_frame or args.last_frame
            or args.reference_image or args.reference_video
        ):
            sys.exit("错误：必须至少提供 --prompt 或一个图/视频输入")

        payload: dict = {
            "model": args.model,
            "content": build_content(args),
        }
        if args.resolution:
            payload["resolution"] = args.resolution
        if args.ratio:
            payload["ratio"] = args.ratio
        if args.duration is not None:
            payload["duration"] = args.duration
        if args.seed is not None:
            payload["seed"] = args.seed
        if args.watermark:
            payload["watermark"] = args.watermark == "true"
        if args.camera_fixed:
            payload["camera_fixed"] = args.camera_fixed == "true"
        if args.generate_audio:
            payload["generate_audio"] = args.generate_audio == "true"

        task_id = submit_task(payload, api_key, args.api_url)
        print(f"已提交任务: {task_id}", file=sys.stderr)

    if args.raw:
        print(json.dumps({"task_id": task_id}, ensure_ascii=False, indent=2))
        return

    # 轮询直到 succeeded / failed / expired，或客户端超时
    deadline = time.time() + args.timeout
    last_status = None
    while time.time() < deadline:
        result = query_task(task_id, api_key, args.api_url)
        status = result.get("status")
        if status != last_status:
            print(f"  状态: {status}", file=sys.stderr)
            last_status = status

        if status == "succeeded":
            video_url = find_video_url(result)
            if not video_url:
                sys.exit(
                    f"任务成功但响应里没找到 video_url:\n"
                    f"{json.dumps(result, ensure_ascii=False, indent=2)}"
                )
            saved = download_video(video_url, Path(args.output_dir), args.prefix)
            print(json.dumps({
                "saved": saved,
                "task_id": task_id,
                "duration": result.get("duration"),
                "ratio": result.get("ratio"),
                "resolution": result.get("resolution"),
                "video_url": video_url,
            }, ensure_ascii=False, indent=2))
            return
        if status == "failed":
            err = result.get("error") or result
            sys.exit(f"任务失败: {json.dumps(err, ensure_ascii=False)}")
        if status == "expired":
            sys.exit("任务在服务端过期（expired）")

        time.sleep(args.poll_interval)

    sys.exit(
        f"客户端等待超时（{args.timeout}s），任务仍未完成。\n"
        f"task_id={task_id}，可用 `--task-id {task_id}` 继续查询/下载。"
    )


if __name__ == "__main__":
    main()
