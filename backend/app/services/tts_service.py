"""
TTS 服务层
提供智能分段和文本处理功能
"""
import re
from typing import List, Generator


class TextSegmenter:
    """文本智能分段器"""

    # 句子结束标点（中英文）
    SENTENCE_ENDINGS = r'[。！？；.!?;]'

    # 次要分隔符（用于长句拆分）
    SECONDARY_DELIMITERS = r'[，、,]'

    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 200,
        prefer_length: int = 50
    ):
        """
        初始化分段器

        Args:
            min_length: 最小段落长度（字符数），低于此长度会累积
            max_length: 最大段落长度，超过此长度会强制分段
            prefer_length: 偏好段落长度，尽量在此长度附近分段
        """
        self.min_length = min_length
        self.max_length = max_length
        self.prefer_length = prefer_length
        self.buffer = ""

    def add_text(self, text: str) -> List[str]:
        """
        添加文本并返回可以发送的段落

        Args:
            text: 新增的文本片段

        Returns:
            可以发送的段落列表
        """
        self.buffer += text
        segments = []

        while True:
            segment = self._extract_segment()
            if segment is None:
                break
            segments.append(segment)

        return segments

    def _extract_segment(self) -> str | None:
        """
        从缓冲区提取一个段落

        Returns:
            提取的段落，如果没有可提取的段落则返回 None
        """
        if not self.buffer:
            return None

        # 如果缓冲区过长，强制分段
        if len(self.buffer) > self.max_length:
            return self._force_split()

        # 如果缓冲区过短，等待更多文本
        if len(self.buffer) < self.min_length:
            return None

        # 查找合适的分段点
        segment = self._find_natural_break()
        if segment:
            return segment

        # 没有找到自然分段点，等待更多文本
        return None

    def _find_natural_break(self) -> str | None:
        """
        查找自然的分段点（句子结束标点）

        Returns:
            分段的文本，如果没有找到则返回 None
        """
        # 优先查找句子结束标点
        matches = list(re.finditer(self.SENTENCE_ENDINGS, self.buffer))

        if not matches:
            return None

        # 寻找最接近偏好长度的分段点
        best_match = None
        best_distance = float('inf')

        for match in matches:
            pos = match.end()
            distance = abs(pos - self.prefer_length)

            # 必须满足最小长度要求
            if pos >= self.min_length and distance < best_distance:
                best_match = match
                best_distance = distance

        if best_match:
            pos = best_match.end()
            segment = self.buffer[:pos].strip()
            self.buffer = self.buffer[pos:].strip()
            return segment

        return None

    def _force_split(self) -> str:
        """
        强制分段（当缓冲区过长时）

        Returns:
            分段的文本
        """
        # 尝试在次要分隔符处分段
        matches = list(re.finditer(self.SECONDARY_DELIMITERS, self.buffer[:self.max_length]))

        if matches:
            # 取最后一个次要分隔符
            pos = matches[-1].end()
        else:
            # 没有次要分隔符，直接截断
            pos = self.max_length

        segment = self.buffer[:pos].strip()
        self.buffer = self.buffer[pos:].strip()
        return segment

    def flush(self) -> str | None:
        """
        刷新缓冲区，返回剩余的文本

        Returns:
            剩余的文本，如果缓冲区为空则返回 None
        """
        if not self.buffer:
            return None

        segment = self.buffer.strip()
        self.buffer = ""
        return segment


def segment_text_stream(
    text_stream: Generator[str, None, None],
    min_length: int = 10,
    max_length: int = 200,
    prefer_length: int = 50
) -> Generator[str, None, None]:
    """
    对流式文本进行智能分段

    Args:
        text_stream: 输入的文本流
        min_length: 最小段落长度
        max_length: 最大段落长度
        prefer_length: 偏好段落长度

    Yields:
        分段后的文本
    """
    segmenter = TextSegmenter(min_length, max_length, prefer_length)

    for text_chunk in text_stream:
        segments = segmenter.add_text(text_chunk)
        for segment in segments:
            yield segment

    # 刷新剩余文本
    final_segment = segmenter.flush()
    if final_segment:
        yield final_segment


# 示例用法
if __name__ == "__main__":
    # 模拟流式文本输入
    test_stream = [
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

    print("=== 智能分段测试 ===\n")

    for i, segment in enumerate(segment_text_stream(iter(test_stream)), 1):
        print(f"段落 {i} ({len(segment)} 字符): {segment}")
        print()
