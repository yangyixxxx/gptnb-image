# gptnb-image

[牛马AI](https://niuma.limyai.com) 的图像生成技能（skill），基于 [gptnb.ai](https://oneapi.gptnb.ai) 中转的 `gpt-image-2` / `gpt-image-2-vip`（分层）/ `dall-e-3` 等模型。

## 能干什么

- **普通生图**：单张图像生成（`gpt-image-2` / `dall-e-3` 等）
- **海报分层**：`gpt-image-2-vip` 一次调用同时返回**完整海报 + 各元素分层 PNG**，适合"先出海报，再把每个元素拆成独立图"的场景
- 自动下载图片到工作目录的 `outputs/gptnb-image/` 下

## 在牛马AI 里使用

直接在牛马AI 对话里说出你想要的图就行，比如：

> 帮我生成一张蜜雪冰城和疯狂星期四的联名营销活动宣传海报，然后把生成的海报拆分成若干图像，每个元素一个独立拆分开，不要改变相对位置

牛马AI 会自动调用本 skill，多张图会以**主图 + 缩略图条**的画廊形式展示，支持点击放大、右键打开文件 / 文件目录。

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
│   └── generate.py
└── references/
    └── sizes.md
```

### 第三步：申请并配置 API key

1. 前往 [https://oneapi.gptnb.ai](https://oneapi.gptnb.ai) **注册账号并充值**
2. 在「**令牌 / API Keys**」页新建一个令牌，复制以 `sk-` 开头的字符串
3. 任选一种方式配置：

   **方式 A：写入用户配置文件（推荐，持久化）**
   ```bash
   mkdir -p ~/.newmax/skills/gptnb-image
   echo "sk-xxx" > ~/.newmax/skills/gptnb-image/.api_key
   chmod 600 ~/.newmax/skills/gptnb-image/.api_key
   ```

   **方式 B：环境变量（临时）**
   ```bash
   export GPTNB_API_KEY="sk-xxx"
   ```

   **方式 C：CLI 参数**（每次调用都传）
   ```bash
   python3 scripts/generate.py --api-key sk-xxx --prompt "..."
   ```

优先级：CLI 参数 > 环境变量 > 配置文件。

### 第四步：在牛马AI 里使用

在牛马AI 中开启本 skill（默认已自动发现 `~/.newmax/skills/` 下的 skill），然后正常对话即可：

> "用 gptnb 帮我生成一张赛博朋克风格的城市夜景"
> "帮我做一张蜜雪冰城海报，把每个元素分层拆出来"

## 命令行直接用（不通过牛马AI）

```bash
# 普通生图
python3 scripts/generate.py --prompt "一只在月光下奔跑的银狐" --size 1536x1024 --quality high

# 分层模型（一次返回多张元素图）
python3 scripts/generate.py \
  --model gpt-image-2-vip \
  --prompt "蜜雪冰城和疯狂星期四的联名营销活动宣传海报，把海报拆分成若干图像，每个元素独立拆分开，不要改变相对位置" \
  --size auto
```

## 参数说明

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

## 错误排查

- **HTTP 401/403**：API key 无效或已失效，去 [oneapi.gptnb.ai](https://oneapi.gptnb.ai) 看令牌状态
- **HTTP 402** / 余额不足：去 gptnb 后台充值
- **HTTP 429**：限流，稍后重试或减少并发
- **内容安全错误**：调整 prompt，避免敏感词
- **size 校验失败**：参考 `references/sizes.md` 里的尺寸约束

## License

MIT
