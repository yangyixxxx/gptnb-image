# seedance 视频生成模型速查

通过 `https://one-cn2.gptnb.ai/seedance2/v3/contents/generations/tasks` 中转调用，兼容 Volcengine ark API。

## 模型列表

| 模型 ID | 能力 | 备注 |
|---------|------|------|
| `doubao-seedance-2-0-260128` | 文生 / 图生（首帧/首尾帧）/ 多模态参考（1-9 图 + 0-3 视频 + 0-3 音频）| **默认推荐** |
| `doubao-seedance-2-0-fast-...` | 同 2.0，速度更快但 1080p 不支持 | 对时延敏感 |
| `doubao-seedance-1-5-pro-251215` | 文生 / 图生 / 首尾帧 | 支持 draft 样片 |
| `doubao-seedance-1-0-pro` | 文生 / 图生 / 首尾帧 | |
| `doubao-seedance-1-0-pro-fast` | 文生 / 图生（仅首帧） | |
| `doubao-seedance-1-0-lite-t2v` | 仅文生 | 轻量 |
| `doubao-seedance-1-0-lite-i2v` | 图生（首帧/首尾帧/参考图 1-4 张） | 轻量 |

## 输入组合

seedance 2.0 / 2.0 fast 支持：
- 文本
- 文本（可选）+ 图片
- 文本（可选）+ 视频
- 文本（可选）+ 图片 + 音频
- 文本（可选）+ 图片 + 视频
- 文本（可选）+ 视频 + 音频
- 文本（可选）+ 图片 + 视频 + 音频
- 注：**不能单独传音频**，必须搭配图或视频

注意 **图生视频-首帧、图生视频-首尾帧、多模态参考生视频** 是三种**互斥**场景，不可混用：
- 首帧：1 张 image_url，role=`first_frame`（或不传）
- 首尾帧：2 张 image_url，role 必填 `first_frame` / `last_frame`
- 参考图：1~9 张 image_url，role 必填 `reference_image`

## 视频参数

| 参数 | 取值 | 默认 |
|------|------|------|
| `resolution` | `480p` / `720p` / `1080p` | 2.0 / 1.5 / 1.0 lite: `720p`；1.0 pro/pro-fast: `1080p`；2.0 fast 不支持 1080p |
| `ratio` | `16:9` / `4:3` / `1:1` / `3:4` / `9:16` / `21:9` / `adaptive` | 2.0 / 1.5: `adaptive`；1.0 lite 参考图: `16:9`；其他文生 `16:9` 图生 `adaptive` |
| `duration` | 2.0: [4,15] 或 -1；1.5: [4,12] 或 -1；1.0: [2,12] | `5` |
| `seed` | [-1, 2³²-1] | `-1`（随机） |
| `watermark` | `true` / `false` | `false` |
| `camera_fixed` | `true` / `false`（参考图场景与 2.0 不支持） | `false` |
| `generate_audio` | `true` / `false`（仅 2.0 / 1.5 pro 支持） | `true` |

## 提示词建议

- 中英文均支持；2.0 系列还支持日/印尼/西/葡语
- 中文 ≤500 字，英文 ≤1000 词
- 多图参考时建议显式指代："[图1]xxx，[图2]yyy"
- 对话内容用双引号优化音频生成：`男人叫住女人说："你记住，以后不可以用手指指月亮。"`

## 异步任务

POST 创建后返回 `id`，需轮询 `GET .../tasks/{id}` 直到 status 为：
- `queued` / `running`：继续等
- `succeeded`：响应里取 `video_url` 下载
- `failed` / `expired`：报错
