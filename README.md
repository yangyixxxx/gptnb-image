# gptnb-image

[牛马AI](https://niuma.limyai.com) 的**图像 & 视频**生成技能（skill），基于 [gptnb.ai](https://oneapi.gptnb.ai) 中转。一个 skill 同时承载两条管道：

- **图像生成**：`gpt-image-2` / `gpt-image-2-vip`（分层）/ `dall-e-3` 等
- **视频生成**：`seedance 2.0` / `2.0 fast` / `1.5 pro` / `1.0` 系列（doubao-seedance）

## 能干什么

### 图像
- **普通生图**：单张图像生成（`gpt-image-2` / `dall-e-3` 等）
- **海报分层**：`gpt-image-2-vip` 一次调用同时返回**完整海报 + 各元素分层 PNG**，适合"先出海报，再把每个元素拆成独立图"的场景
- 自动下载图片到工作目录的 `outputs/gptnb-image/` 下

### 视频
- **文生视频**：纯 prompt 出 5~15 秒视频
- **图生视频**：单图生成（首帧）/ 双图生成（首尾帧过渡）
- **多模态参考视频**：1~9 张参考图 + 0~3 段参考视频 + 0~3 段参考音频，组合输出 1 个视频（仅 seedance 2.0 / 2.0 fast）
- **同步音频**：seedance 2.0 / 1.5 pro 默认同时生成同步音频（人声、音效、BGM）
- 异步任务流自动处理（提交 → 轮询 → 下载 mp4 到 `outputs/seedance/`）

## 在牛马AI 里使用

直接在牛马AI 对话里说出你想要的就行：

**生图：**

> 帮我生成一张蜜雪冰城和疯狂星期四的联名营销活动宣传海报，然后把生成的海报拆分成若干图像，每个元素一个独立拆分开，不要改变相对位置

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

# 分层模型（一次返回多张元素图）
python3 scripts/generate.py \
  --model gpt-image-2-vip \
  --prompt "蜜雪冰城和疯狂星期四的联名营销活动宣传海报，把海报拆分成若干图像，每个元素独立拆分开，不要改变相对位置" \
  --size auto
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
| `--prompt` | 图像描述（**必填**） | — |
| `--model` | 模型名（含 `vip` 自动切到分层协议） | `gpt-image-2` |
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
