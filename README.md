# gptnb-image

[牛马AI](https://niuma.limyai.com) 的**图像 & 视频**生成技能（skill），基于 [gptnb.ai](https://oneapi.gptnb.ai) 中转。一个 skill 同时承载两条管道：

- **图像**：`gpt-image-2` / `gpt-image-2-vip`（分层）/ `dall-e-3` 等
- **视频**：`seedance 2.0` / `2.0 fast` / `1.5 pro` / `1.0` 系列（doubao-seedance）

## 目录

- [能力一览](#能力一览)
- [在牛马AI 里使用](#在牛马ai-里使用)
- [安装](#安装)
- [命令行直接用](#命令行直接用不通过牛马ai)
- [参数说明](#参数说明)
- [错误排查](#错误排查)

## 能力一览

| 能力 | 触发关键词 / 用法 | 端点 | 脚本 |
|------|------------------|------|------|
| 普通生图 | "画一张..." | `/v1/images/generations` | `generate.py` |
| 文生 + 分层 | "生成 X 海报，把每个元素拆开" | `/v1/images/generations` (vip) | `generate.py --model gpt-image-2-vip` |
| **上传图分层** ⭐ | 上传图 + "把这张图拆成图层" | `/v1/images/edits` (vip + multipart) | `generate.py --model gpt-image-2-vip --input-image <file>` |
| 文生视频 | "做一段 5 秒的视频..." | seedance create task | `seedance.py --prompt ...` |
| 图生视频 | 上传图 + "让它动起来" | seedance create task | `seedance.py --first-frame ...` |
| 首尾帧视频 | 上传两张 + "从 A 到 B" | seedance create task | `seedance.py --first-frame ... --last-frame ...` |
| 参考图视频 | 多张参考图 + "合成一段视频" | seedance create task (2.0+) | `seedance.py --reference-image ...` |
| 同步音频视频 | "带配音 / 带 BGM" | seedance create task (2.0/1.5) | `seedance.py --generate-audio true` |

> ⭐ **新功能**：上传图分层，把你已经做好的海报/插画交给 vip 模型按元素拆成透明背景 PNG，不用让模型重新画一遍。

## 在牛马AI 里使用

直接在牛马AI 对话里说出你想要的就行：

**生图：**

> 帮我生成一张蜜雪冰城和疯狂星期四的联名营销活动宣传海报，然后把生成的海报拆分成若干图像，每个元素一个独立拆分开，不要改变相对位置

**上传海报分层：**

> 我刚做好一张海报（拖入图片），帮我把这张图的每个元素拆成独立透明 PNG 图层

**生视频：**

> 帮我做一段 5 秒的视频，画面是小猫对着镜头打哈欠
> 把这张海报变成视频，让主角眨眼睛镜头慢慢推进
> 用这 3 张参考图合成一段视频：[图1]戴眼镜的男孩和[图2]的柯基，坐在[图3]的草坪上

牛马AI 会自动调用本 skill：
- 图像产物以**主图 + 缩略图条**画廊展示，点主图放大、右键打开文件 / 文件目录
- 视频产物自动渲染缩略图，点击播放

## 安装

### 第一步：下载牛马AI

前往 [https://niuma.limyai.com](https://niuma.limyai.com) 下载并安装牛马AI 客户端。

### 第二步：把本 skill 放到 newmax skills 目录

```bash
# 克隆仓库到 ~/.newmax/skills/gptnb-image
git clone https://github.com/yangyixxxx/gptnb-image.git ~/.newmax/skills/gptnb-image
```

或者下载本仓库的 ZIP，解压后把整个文件夹改名为 `gptnb-image` 放到 `~/.newmax/skills/` 下。最终目录结构应该是：

```
~/.newmax/skills/gptnb-image/
├── SKILL.md
├── scripts/
│   ├── generate.py       # 图像生成
│   └── seedance.py       # 视频生成
└── references/
    ├── sizes.md
    └── seedance-models.md
```

### 第三步：申请并配置 API key

> 图像生成和视频生成的 API key **单独维护**（同一个 sk-xxx 也可以、分开更便于跟踪用量）。视频消耗较大，单独配 key 更稳。

1. 前往 [https://oneapi.gptnb.ai](https://oneapi.gptnb.ai) **注册账号并充值**
   > ⚠️ **视频生成消耗大，建议账户余额 ≥200 元**
2. 在「**令牌 / API Keys**」页新建令牌，复制以 `sk-` 开头的字符串
   > ⚠️ **激活令牌时务必选「api」分组**（不要用默认或其它分组），api 分组上游更稳，超时/限流明显少。
3. 配置 key：

   **图像 key**（必填，否则 `generate.py` 会报错并打印引导）：
   ```bash
   mkdir -p ~/.newmax/skills/gptnb-image
   echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.api_key
   chmod 600 ~/.newmax/skills/gptnb-image/.api_key
   ```

   **视频 key**（首次调用 seedance 时若没配会报错并打印引导）：
   ```bash
   echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.seedance_api_key
   chmod 600 ~/.newmax/skills/gptnb-image/.seedance_api_key
   ```

   **环境变量替代**：
   ```bash
   export GPTNB_API_KEY="sk-xxx"            # 图像
   export GPTNB_SEEDANCE_API_KEY="sk-xxx"   # 视频
   ```

   **CLI 替代**：每次调用都用 `--api-key sk-xxx` 传。

优先级：CLI 参数 > 环境变量 > 配置文件。

### 第四步：在牛马AI 里使用

在牛马AI 中开启本 skill（默认已自动发现 `~/.newmax/skills/` 下的 skill），然后正常对话即可：

> "用 gptnb 帮我生成一张赛博朋克风格的城市夜景"
> "帮我做一张蜜雪冰城海报，把每个元素分层拆出来"
> "做一段 5 秒的视频，画面是小猫对着镜头打哈欠"
> "把这张海报变成视频，让主角眨眼镜头推进"

## 命令行直接用（不通过牛马AI）

### 图像

```bash
# 普通生图
python3 scripts/generate.py --prompt "一只在月光下奔跑的银狐" --size 1536x1024 --quality high

# 文生 + 分层（一次调用返回完整海报 + 各元素 PNG）
python3 scripts/generate.py \
  --model gpt-image-2-vip \
  --prompt "蜜雪冰城和疯狂星期四的联名营销活动宣传海报，把海报拆分成若干图像，每个元素独立拆分开，不要改变相对位置" \
  --size auto

# 上传图分层（vip 把已有海报/插画按元素拆成透明 PNG 图层）
python3 scripts/generate.py \
  --model gpt-image-2-vip \
  --input-image /path/to/poster.png
# --prompt 可省略，默认用"按元素拆分、保持相对位置"模板
```

### 视频

```bash
# 文生视频
python3 scripts/seedance.py --prompt "小猫对着镜头打哈欠" --duration 5 --resolution 720p --ratio 16:9

# 图生视频（首帧）
python3 scripts/seedance.py --first-frame /path/to/poster.png --prompt "镜头慢慢推进，主角眨眼睛"

# 首尾帧
python3 scripts/seedance.py \
  --first-frame /path/to/start.png \
  --last-frame /path/to/end.png \
  --prompt "从开始到结束的过渡"

# 多张参考图（仅 seedance 2.0 / 2.0 fast）
python3 scripts/seedance.py \
  --reference-image url1 \
  --reference-image url2 \
  --prompt "[图1]戴眼镜男孩和[图2]的柯基坐在草坪上"

# 续查已有任务
python3 scripts/seedance.py --task-id <ID>
```

## 参数说明

### `generate.py`（图像）

| 参数 | 说明 | 默认 |
|------|------|------|
| `--prompt` | 图像描述（生成模式必填；"上传图 + vip 分层"可省略，用默认拆分模板） | — |
| `--model` | 模型名（含 `vip` 自动切到分层协议） | `gpt-image-2` |
| `--input-image` | 上传本地图（multipart），传入后自动走 `/v1/images/edits` 端点；可重复传多张 | — |
| `--n` | 生成张数（1-10） | `1`（vip 模式忽略） |
| `--size` | `WIDTHxHEIGHT` 或 `auto` | `auto` |
| `--quality` | `low` / `medium` / `high` / `auto` | `auto`（vip 模式忽略） |
| `--output-format` | `png` / `jpeg` / `webp` | 不传（vip 自动 png） |
| `--response-format` | `url` / `b64_json` | 不传（vip 自动 url） |
| `--output-dir` | 输出目录 | `outputs/gptnb-image/` |
| `--prefix` | 文件名前缀 | `gptnb` |
| `--raw` | 只打印 API 原始 JSON，不下载 | false |
| `--api-key` | 单次覆盖 key | — |

更多尺寸约束见 `references/sizes.md`。

### `seedance.py`（视频）

| 参数 | 说明 | 默认 |
|------|------|------|
| `--prompt` | 文本提示词 | 空 |
| `--model` | 模型 ID | `doubao-seedance-2-0-260128` |
| `--image` / `--first-frame` / `--last-frame` | 单帧图（URL 或本地路径） | — |
| `--reference-image` | 参考图（可重复传，1~9 张） | — |
| `--reference-video` | 参考视频（仅 2.0 / 2.0 fast，可重复） | — |
| `--reference-audio` | 参考音频（仅 2.0 / 2.0 fast，可重复，需配图/视频） | — |
| `--resolution` | `480p` / `720p` / `1080p` | 模型默认 |
| `--ratio` | `16:9` / `9:16` / `1:1` / `3:4` / `4:3` / `21:9` / `adaptive` | 模型默认 |
| `--duration` | 时长秒；2.0 [4,15] 或 -1，1.0 [2,12] | `5` |
| `--seed` | 随机种子 | `-1` |
| `--watermark` | `true` / `false` | `false` |
| `--camera-fixed` | `true` / `false` | `false` |
| `--generate-audio` | `true` / `false`（仅 2.0 / 1.5 pro） | `true` |
| `--output-dir` | 输出目录 | `outputs/seedance/` |
| `--prefix` | 文件名前缀 | `seedance` |
| `--poll-interval` | 轮询间隔秒 | `8` |
| `--timeout` | 客户端总等待秒 | `900` |
| `--raw` | 只提交，返回 task_id 不轮询 | false |
| `--task-id` | 跳过提交，续查/下载已有任务 | — |
| `--api-key` | 单次覆盖 key | — |

模型列表与能力速查见 `references/seedance-models.md`。

## 错误排查

### 图像（`generate.py`）

- **HTTP 401/403**：API key 无效或已失效，去 [oneapi.gptnb.ai](https://oneapi.gptnb.ai) 看令牌状态
- **HTTP 402** / 余额不足：去 gptnb 后台充值
- **HTTP 429**：限流，稍后重试或减少并发
- **内容安全错误**：调整 prompt，避免敏感词
- **size 校验失败**：参考 `references/sizes.md` 里的尺寸约束

### 视频（`seedance.py`）

- **HTTP 401/403**：seedance key 无效，注意是 `.seedance_api_key` 不是 `.api_key`
- **HTTP 402** / 余额不足：seedance 消耗较大，建议账户 ≥200 元
- **HTTP 429**：限流，稍后重试
- 任务 `failed`：响应里的 `error` 信息会被打到 stderr
- 任务 `expired`：服务端任务超时（`execution_expires_after` 默认 48 小时），重新提交即可
- 客户端 `timeout`：客户端等够 15 分钟还没完成，脚本会输出 `task_id`，可用 `--task-id <ID>` 继续等

## License

MIT
