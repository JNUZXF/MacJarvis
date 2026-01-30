# TTS 功能快速启动指南

## 一分钟启动

### 第 1 步：配置 API Key

在项目根目录的 `.env` 文件中添加：

```bash
DASHSCOPE_API_KEY=your_api_key_here
```

> 📌 获取 API Key：https://dashscope.console.aliyun.com/

### 第 2 步：安装依赖

```bash
# 安装 portaudio (macOS)
brew install portaudio

# 安装 Python 依赖
cd backend
pip install dashscope pyaudio
```

### 第 3 步：启动服务

**后端**：
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 18888
```

**前端**：
```bash
cd frontend
npm run dev
```

### 第 4 步：启用 TTS

1. 打开 http://localhost:5173
2. 点击右上角 ⚙️ 设置图标
3. 滚动到"语音合成 (TTS)"部分
4. 打开"启用语音播放"开关
5. 选择你喜欢的音色

### 第 5 步：开始使用！

发送一条消息，智能体回复时会自动播放语音！🎉

## 验证安装

运行测试脚本验证分段功能：

```bash
python tests/test_tts_segmentation.py
```

应该看到：
```
✅ 所有测试完成！
```

## 常用音色推荐

| 音色 | 性别 | 特点 | 推荐场景 |
|------|------|------|----------|
| 龙吟桃 (longyingtao_v3) | 女 | 温柔自然 | 日常对话 |
| 知甜 (zhitian_v3) | 女 | 活泼清脆 | 轻松场景 |
| 知硕 (zhishuo_v3) | 男 | 稳重大气 | 正式场景 |

## 配置建议

### 推荐配置（默认）

适合大多数场景：

```
最小段落长度: 10
最大段落长度: 200
偏好段落长度: 50
```

### 快速响应配置

希望更快听到声音：

```
最小段落长度: 5
最大段落长度: 150
偏好段落长度: 30
```

### 流畅播放配置

希望更连贯的语音：

```
最小段落长度: 20
最大段落长度: 300
偏好段落长度: 100
```

## 故障排查

### 问题 1: 没有声音

**检查清单**：
- [ ] TTS 开关已启用
- [ ] DASHSCOPE_API_KEY 已配置
- [ ] 浏览器允许音频播放
- [ ] 后端服务正常运行
- [ ] 查看浏览器控制台是否有错误

**解决方案**：
```bash
# 检查后端日志
# 应该看到 TTS 相关的路由已注册

# 测试 API
curl http://localhost:18888/api/v1/tts/voices
```

### 问题 2: 播放延迟高

**原因**：网络延迟或分段配置不当

**解决方案**：
1. 降低"最小段落长度"到 5
2. 降低"偏好段落长度"到 30
3. 检查网络连接

### 问题 3: 语音不连贯

**原因**：分段过碎

**解决方案**：
1. 提高"最小段落长度"到 15-20
2. 提高"偏好段落长度"到 60-80

## API 测试

测试单次合成：

```bash
curl -X POST http://localhost:18888/api/v1/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是一段测试语音。",
    "voice": "longyingtao_v3",
    "model": "cosyvoice-v3-flash"
  }'
```

应该返回：
```json
{
  "success": true,
  "audio": "base64_encoded_audio...",
  "format": "pcm_22050hz_mono_16bit",
  "sample_rate": 22050
}
```

## 目录结构

```
mac_agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── tts.py          ← TTS API 路由
│   │   └── services/
│   │       └── tts_service.py  ← 分段服务
│   └── requirements.txt         ← 已添加 TTS 依赖
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── TTSSettings.tsx      ← TTS 配置组件
│       │   └── TTSSettings.module.css
│       ├── utils/
│       │   └── tts-manager.ts       ← TTS 管理器
│       └── types.ts                 ← 类型定义
├── docs/
│   └── TTS功能使用指南.md            ← 完整文档
├── tests/
│   └── test_tts_segmentation.py     ← 测试脚本
└── scripts/
    └── qwen3-tts.py                 ← 原始测试脚本
```

## 下一步

完成基础设置后，可以：

1. **调整参数**：在设置中试验不同的分段参数
2. **切换音色**：尝试不同的音色，找到最喜欢的
3. **阅读文档**：查看 `docs/TTS功能使用指南.md` 了解更多

## 需要帮助？

- 📖 完整文档：`docs/TTS功能使用指南.md`
- 📊 实现总结：`TTS功能实现总结.md`
- 🧪 测试脚本：`tests/test_tts_segmentation.py`
- 💻 示例代码：`scripts/qwen3-tts.py`

## 享受语音体验！

现在你可以体验流畅的 AI 语音对话了！🎤✨

如有问题，请参考完整文档或提交 Issue。

---

**快速链接**：
- DashScope 控制台：https://dashscope.console.aliyun.com/
- 通义千问 TTS 文档：https://help.aliyun.com/zh/dashscope/developer-reference/tts-api

祝使用愉快！🚀
