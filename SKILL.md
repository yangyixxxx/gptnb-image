---
name: gptnb-image
description: "Generate images via gptnb.ai using gpt-image-2 / gpt-image-2-vip (layered) / dall-e-3. Use when the user asks to create/generate images with gptnb, gpt-image-2, vip 分层, or mentions the gptnb.ai API. Supports configurable prompt, model, count (n), size, quality, output_format and response_format."
---

# gptnb 图像生成

通过 `https://one-cn2.gptnb.ai/v1/images/generations` 调用 gpt-image-2 系列生成图像。脚本兼容 OpenAI 经典 image generation 接口风格。如需切换上游可用 `GPTNB_API_URL` 环境变量或 `--api-url` 参数覆盖。

## 决策规则（最重要）

**只要用户提到"分层 / 拆分 / 拆开 / 每个元素一张 / 图层 / layered / split"等关键词，无论是否同时要求"先生成海报"，都只发一次 `gpt-image-2-vip` 调用**，把"生成 + 拆分"写进同一个 prompt，由 vip 模型一次性返回合成图 + 各元素分层图。

- ❌ 错误：先用 `gpt-image-2` 生成海报，再用 `gpt-image-2-vip` 分层（两次调用，且第二次无法读到第一次的像素，结果对不齐）
- ✅ 正确：直接一次 `gpt-image-2-vip`，prompt 写成"帮我生成 X 海报，然后把生成的海报拆分成若干图像，每个元素独立拆分开，不要改变相对位置"

vip 模型本身就是「生成 + 同源分层」的复合模型，所有图层来自它内部生成的同一张主图，必须信任它一次出全部产物。

## 模型

- `gpt-image-2`（默认）：单图生成，支持 `n` / `quality`
- `gpt-image-2-vip`：**分层模型**，单次返回多张图（把生成的画面按元素拆开，每个元素一张图，相对位置不变）。负载里**不要传** `n` / `quality`，需要传 `output_format` / `response_format`，脚本会自动按 vip 协议构造 payload
- `dall-e-3` 等也可通过 `--model` 指定

## 使用方式

普通模型：

```bash
python3 scripts/generate.py --prompt "一只在月光下奔跑的银狐" --size 1536x1024 --quality high
```

vip 分层模型（自动产出多张元素图）：

```bash
python3 scripts/generate.py \
  --model gpt-image-2-vip \
  --prompt "蜜雪冰城和疯狂星期四的联名营销活动宣传海报，把海报拆分成若干图像，每个元素独立拆分开，不要改变相对位置" \
  --size auto
```

返回的 `data` 数组里每个 url 都会被下载，文件名 `<prefix>-<时间戳>-<序号>.png`。

参数：

- `--prompt` 必填，图像描述
- `--model` 默认 `gpt-image-2`，模型名含 `vip` 时自动切到分层协议
- `--n` 生成张数，1-10，默认 1（vip 模式忽略）
- `--size` `WIDTHxHEIGHT` 或 `auto`，默认 `auto`
- `--quality` `low` / `medium` / `high` / `auto`，默认 `auto`（vip 模式忽略）
- `--output-format` 输出图像格式 `png` / `jpeg` / `webp`（默认不传；vip 模式自动 `png`）
- `--response-format` `url` 或 `b64_json`（默认不传；vip 模式自动 `url`）
- `--output-dir` 默认 `outputs/gptnb-image/`
- `--prefix` 文件名前缀，默认 `gptnb`
- `--raw` 只打印 API 原始 JSON，不下载图片
- `--api-key` 单次覆盖；优先级：CLI > `GPTNB_API_KEY` > `~/.newmax/skills/gptnb-image/.api_key`，详见下方「API Key 配置」

脚本本地校验 `size` 是否满足约束（16 倍数 / 最长边 ≤ 3840 / 长短比 ≤ 3:1 / 总像素 655,360–8,294,400），不合法直接报错，不打 API。`size=auto` 跳过校验。

## API Key 配置

脚本按以下优先级解析 key：

1. CLI `--api-key sk-xxx`
2. 环境变量 `GPTNB_API_KEY`
3. 文件 `~/.newmax/skills/gptnb-image/.api_key`（推荐持久化方式，权限建议 600）

三者都没有时，脚本会以非零退出码报错并打印引导文案，提示用户：

> 前往 https://oneapi.gptnb.ai 注册账号并充值 → 在「令牌 / API Keys」页新建令牌 → 写入 `~/.newmax/skills/gptnb-image/.api_key` 或 `export GPTNB_API_KEY=...`

首次使用时如果出现该提示，直接把上述链接和步骤转告用户，不要尝试伪造 key 继续调用。

```bash
# 一次性配置
mkdir -p ~/.newmax/skills/gptnb-image
echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.api_key
chmod 600 ~/.newmax/skills/gptnb-image/.api_key
```

## 输出

下载完成后打印 JSON：

```json
{ "saved": ["outputs/gptnb-image/gptnb-20260504-153012-1.png"], "count": 1 }
```

vip 模式会把所有图层一次性下载下来：

```json
{
  "saved": [
    "outputs/gptnb-image/poster-20260504-181200-1.png",
    "outputs/gptnb-image/poster-20260504-181200-2.png",
    "outputs/gptnb-image/poster-20260504-181200-3.png"
  ],
  "count": 3
}
```

## 尺寸/质量速查

详见 `references/sizes.md`。

## 错误处理

- `HTTP 401/403`：检查 API key（默认 key 失效时让用户提供新 key 或设 `GPTNB_API_KEY`）
- `HTTP 402` / 余额/额度错误：让用户去 gptnb 后台充值
- `HTTP 429`：减少并发或稍后重试
- 内容安全错误：让用户调整 prompt
- 永远不要伪造图像或 URL；失败时如实输出状态码和错误体
