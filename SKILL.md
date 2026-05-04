---
name: gptnb-image
description: "Generate images and videos via gptnb.ai. 图像：gpt-image-2 / gpt-image-2-vip(分层) / dall-e-3。视频：seedance 2.0 / 2.0 fast / 1.5 pro / 1.0 系列（doubao-seedance-*）。Use when the user asks to create/generate images, posters, layered images, videos, animations, or mentions gptnb / seedance / doubao-seedance. 支持文生图、图生视频、首尾帧视频、多模态参考视频。"
---

# gptnb 图像 & 视频生成

skill 同时承载两条管道，按用户意图分流：

| 用户诉求 | 用 | 脚本 | 端点 |
|---------|----|------|-----|
| 出图 / 海报 / 插画 / 元素分层 | gpt-image-2 系列 | `scripts/generate.py` | `one-cn2.gptnb.ai/v1/images/generations` |
| 出视频 / 动画 / 短片 | seedance 系列 | `scripts/seedance.py` | `one-cn2.gptnb.ai/seedance2/v3/contents/generations/tasks` |

两个端点的 API key **单独维护**，文件分别放在 `~/.newmax/skills/gptnb-image/.api_key` 和 `.seedance_api_key`（详见各自的「API Key 配置」段落）。

---

# 一、图像生成

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

> 前往 https://oneapi.gptnb.ai 注册账号并充值 → 在「令牌 / API Keys」页新建令牌 → **激活时务必选「api」分组**（更稳，超时/限流少）→ 写入 `~/.newmax/skills/gptnb-image/.api_key` 或 `export GPTNB_API_KEY=...`

首次使用时如果出现该提示，直接把上述链接和步骤转告用户，**特别要提醒选 api 分组**，不要尝试伪造 key 继续调用。

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

---

# 二、视频生成（seedance）

通过 `https://one-cn2.gptnb.ai/seedance2/v3/contents/generations/tasks` 中转调用，兼容 Volcengine ark 创建/查询视频任务 API。`scripts/seedance.py` 处理「**异步任务流**」：POST 提交 → 轮询 GET → 下载产出 mp4。

## 决策规则

**当用户提到「视频 / video / 动画 / 短片 / 拍 X 秒 / 让 XX 动起来」时**，用本管道，不用 gpt-image-2。常见触发：

- ✅ "做一段 5 秒的猫咪打哈欠视频" → 文生视频
- ✅ "把这张图变成视频" / "让图里人物动起来" → 图生视频（首帧）
- ✅ "从这张图开始，到那张图结束" → 首尾帧
- ✅ "用这几张参考图合成一个视频" → 参考图（reference_image，1~9 张）
- ✅ "给视频配同步音频" → seedance 2.0 默认 generate_audio=true

> ⚠️ 用户没明确说要分层时不要 vip；反过来用户没说要视频时不要 seedance。两者完全不同管道。

## 模型

- **`doubao-seedance-2-0-260128`**（默认）：最新，支持文生 / 图生（首帧/首尾帧）/ 多模态参考（图+视频+音频）
- `doubao-seedance-2-0-fast-...`：更快但 1080p 不支持
- `doubao-seedance-1-5-pro-251215`：上一代 pro，支持 draft 样片
- 1.0 系列若用户明确需要可指定（pro / pro-fast / lite t2v / lite i2v）

完整列表与能力速查见 `references/seedance-models.md`。

## 使用方式

文生视频：

```bash
python3 scripts/seedance.py --prompt "小猫对着镜头打哈欠" --duration 5 --resolution 720p --ratio 16:9
```

图生视频（首帧）：

```bash
python3 scripts/seedance.py \
  --first-frame /path/to/poster.png \
  --prompt "镜头慢慢推进，主角眨眼睛"
```

首尾帧：

```bash
python3 scripts/seedance.py \
  --first-frame /path/to/start.png \
  --last-frame /path/to/end.png \
  --prompt "从开始到结束的过渡"
```

多张参考图（仅 seedance 2.0 / 2.0 fast、1.0 lite i2v）：

```bash
python3 scripts/seedance.py \
  --reference-image url1 \
  --reference-image url2 \
  --reference-image url3 \
  --prompt "[图1]戴眼镜的男孩和[图2]的柯基，坐在[图3]的草坪上，3D 卡通风格"
```

参考图 + 参考音频（仅 seedance 2.0 / 2.0 fast）：

```bash
python3 scripts/seedance.py \
  --reference-image /path/to/character.png \
  --reference-audio /path/to/voice.wav \
  --prompt '让角色说："欢迎回来。"'
```

## 关键参数

- `--prompt`：文本提示词。中英文均可，2.0 系列额外支持日/印尼/西/葡语；中文 ≤500 字
- `--model`：模型 ID，默认 `doubao-seedance-2-0-260128`
- `--first-frame` / `--last-frame` / `--image`：单帧图像，URL 或本地路径
- `--reference-image` / `--reference-video` / `--reference-audio`：可重复传多个，多模态参考用（**注意三种场景互斥**：首帧 / 首尾帧 / 参考图，不能混用）
- `--resolution`：`480p` / `720p` / `1080p`
- `--ratio`：`16:9` / `9:16` / `1:1` / `3:4` / `4:3` / `21:9` / `adaptive`
- `--duration`：时长秒数。2.0 系列 [4,15] 或 -1（自适应），1.5 pro [4,12]，1.0 系列 [2,12]
- `--seed`：随机种子，[-1, 2³²-1]，-1 = 随机
- `--watermark`：`true` / `false`，默认 `false`
- `--camera-fixed`：`true` / `false`（参考图与 2.0 不支持）
- `--generate-audio`：`true` / `false`（仅 2.0 / 1.5 pro 支持，默认开）
- `--output-dir`：默认 `outputs/seedance/`
- `--prefix`：文件名前缀，默认 `seedance`
- `--api-key`：单次覆盖
- `--api-url`：覆盖 API 地址（默认 `one-cn2.gptnb.ai/seedance2/...`）
- `--poll-interval`：轮询间隔秒，默认 8
- `--timeout`：客户端总等待秒，默认 900（15 分钟）
- `--raw`：只提交任务、返回 task_id，不轮询/下载
- `--task-id`：跳过提交，直接查询/下载已有任务

## 输出

成功后打印 JSON：

```json
{
  "saved": "outputs/seedance/seedance-20260504-203012.mp4",
  "task_id": "...",
  "duration": 5,
  "ratio": "16:9",
  "resolution": "720p",
  "video_url": "https://..."
}
```

`saved` 是下载到本地的 mp4 路径（牛马AI 会自动渲染视频缩略图）。

## API Key 配置（与图像生成单独维护）

脚本按以下优先级解析 key：

1. CLI `--api-key sk-xxx`
2. 环境变量 `GPTNB_SEEDANCE_API_KEY`
3. 文件 `~/.newmax/skills/gptnb-image/.seedance_api_key`（推荐，权限 600）

**首次调用 seedance 时如果三者都没有，脚本会以非零退出码报错并打印引导文案**，转告用户：

> 前往 https://oneapi.gptnb.ai 注册账号并充值（建议 ≥200 元，视频消耗大）→ 在「令牌 / API Keys」页新建一个令牌 → **激活时务必选「api」分组**（更稳）→ 写入 `~/.newmax/skills/gptnb-image/.seedance_api_key` 或 `export GPTNB_SEEDANCE_API_KEY=...`

```bash
# 一次性配置
mkdir -p ~/.newmax/skills/gptnb-image
echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.seedance_api_key
chmod 600 ~/.newmax/skills/gptnb-image/.seedance_api_key
```

> ⚠️ 助手务必把"激活选 api 分组 + 视频消耗大建议余额 ≥200 元"两条同时转告，不要省略；不要尝试伪造 key 或 task 继续调用。

## 错误处理

- `HTTP 401/403`：seedance key 无效或失效
- `HTTP 402` / 余额不足：seedance 消耗较大，让用户去 gptnb 后台充值
- `HTTP 429`：限流，稍后重试或减少并发
- 任务 `failed`：把响应体里的 `error` 信息原样转告用户
- 任务 `expired`：服务端任务超时（`execution_expires_after` 默认 48 小时），通常是上游卡死，重新提交即可
- 客户端 `timeout`：客户端等待超时但任务仍在跑，把脚本输出的 `task_id` 给用户，可以稍后用 `--task-id <ID>` 继续查询/下载
- 永远不要伪造视频 URL 或 task ID；失败时如实输出状态码和错误体
