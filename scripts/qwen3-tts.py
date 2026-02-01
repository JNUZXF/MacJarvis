
"""
文件功能：通义千问流式语音合成（TTS）测试脚本
文件路径：scripts/qwen3-tts.py

使用方法：
1. 激活虚拟环境：
   cd /Users/xinfuzhang/Desktop/Code/mac_agent && source backend/.venv/bin/activate

2. 安装依赖（如果未安装）：
   pip install dashscope python-dotenv pyaudio

3. 运行脚本：
   python scripts/qwen3-tts.py

注意：
- 需要确保 .env 文件中配置了 DASHSCOPE_API_KEY
- macOS 系统需要先安装 portaudio: brew install portaudio

cd /Users/xinfuzhang/Desktop/Code/mac_agent && source backend/.venv/bin/activate && python scripts/qwen3-tts.py
"""

# coding=utf-8
import os
import time
from datetime import datetime

import dashscope
from dashscope.audio.tts_v2 import *
from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
from dotenv import load_dotenv
import pyaudio

load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")


def get_timestamp():
    now = datetime.now()
    formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
    return formatted_timestamp

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
dashscope.api_key = DASHSCOPE_API_KEY

# 音色列表
[
    "longyingxiao_v3",
    "longyingtao_v3",
    "longxing_v3",
    "longfeifei_v3",
    "cosyvoice-v3-plus-feifei-15100975513d4875a83113a8200d0d9e"
]

# 模型
model = "cosyvoice-v3-plus"
# 音色
voice = "cosyvoice-v3-plus-feifei-15100975513d4875a83113a8200d0d9e"

# 定义回调接口
class Callback(ResultCallback):
    _player = None
    _stream = None

    def on_open(self):
        print("连接建立：" + get_timestamp())
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        print("语音合成完成，所有合成结果已被接收：" + get_timestamp())

    def on_error(self, message: str):
        print(f"语音合成出现异常：{message}")

    def on_close(self):
        print("连接关闭：" + get_timestamp())
        # 停止播放器
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " 二进制音频长度为：" + str(len(data)))
        self._stream.write(data)

callback = Callback()

test_text = [
    "流式文本语音合成SDK，",
    "可以将输入的文本",
    "合成为语音二进制数据，",
    "相比于非流式语音合成，",
    "流式合成的优势在于实时性",
    "更强。用户在输入文本的同时",
    "可以听到接近同步的语音输出，",
    "极大地提升了交互体验，",
    "减少了用户等待时间。",
    "适用于调用大规模",
    "语言模型（LLM），以",
    "流式输入文本的方式",
    "进行语音合成的场景。",
]

# 实例化SpeechSynthesizer，并在构造方法中传入模型（model）、音色（voice）等请求参数
synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    format=AudioFormat.PCM_22050HZ_MONO_16BIT,  
    callback=callback,
)

# 流式发送待合成文本。在回调接口的on_data方法中实时获取二进制音频
for text in test_text:
    synthesizer.streaming_call(text)
    time.sleep(0.1)
# 结束流式语音合成
synthesizer.streaming_complete()

# 首次发送文本时需建立 WebSocket 连接，因此首包延迟会包含连接建立的耗时
print('[Metric] requestId为：{}，首包延迟为：{}毫秒'.format(
    synthesizer.get_last_request_id(),
    synthesizer.get_first_package_delay()))

