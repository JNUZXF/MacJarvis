"""
测试 TTS 文本分段功能
"""
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.tts_service import TextSegmenter, segment_text_stream


def test_basic_segmentation():
    """测试基础分段功能"""
    print("=== 测试基础分段功能 ===\n")

    segmenter = TextSegmenter(min_length=10, max_length=200, prefer_length=50)

    test_text = "流式文本语音合成SDK，可以将输入的文本合成为语音二进制数据。相比于非流式语音合成，流式合成的优势在于实时性更强。用户在输入文本的同时可以听到接近同步的语音输出，极大地提升了交互体验，减少了用户等待时间。"

    # 模拟流式输入
    chunks = [test_text[i:i+10] for i in range(0, len(test_text), 10)]

    segments = []
    for chunk in chunks:
        result = segmenter.add_text(chunk)
        if result:
            segments.extend(result)

    # 刷新剩余
    final = segmenter.flush()
    if final:
        segments.append(final)

    print(f"总共分成 {len(segments)} 段：\n")
    for i, seg in enumerate(segments, 1):
        print(f"段落 {i} ({len(seg)} 字符): {seg}")
        print()


def test_stream_segmentation():
    """测试流式分段生成器"""
    print("\n=== 测试流式分段生成器 ===\n")

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

    segments = list(segment_text_stream(
        iter(test_stream),
        min_length=10,
        max_length=200,
        prefer_length=50
    ))

    print(f"总共分成 {len(segments)} 段：\n")
    for i, seg in enumerate(segments, 1):
        print(f"段落 {i} ({len(seg)} 字符): {seg}")
        print()


def test_long_text_force_split():
    """测试超长文本强制分段"""
    print("\n=== 测试超长文本强制分段 ===\n")

    segmenter = TextSegmenter(min_length=10, max_length=50, prefer_length=30)

    # 一段没有标点的长文本
    long_text = "这是一段非常非常长的文本内容它没有任何标点符号但是我们仍然需要对它进行分段处理以便于语音合成系统能够正常工作否则会导致单段文本过长影响用户体验"

    segmenter.add_text(long_text)

    segments = []
    while True:
        seg = segmenter.flush()
        if not seg:
            break
        segments.append(seg)

    # 重新测试，模拟流式输入
    segmenter = TextSegmenter(min_length=10, max_length=50, prefer_length=30)
    chunks = [long_text[i:i+5] for i in range(0, len(long_text), 5)]

    segments = []
    for chunk in chunks:
        result = segmenter.add_text(chunk)
        if result:
            segments.extend(result)

    final = segmenter.flush()
    if final:
        segments.append(final)

    print(f"总共分成 {len(segments)} 段：\n")
    for i, seg in enumerate(segments, 1):
        print(f"段落 {i} ({len(seg)} 字符): {seg}")
        print()


def test_mixed_language():
    """测试中英文混合文本"""
    print("\n=== 测试中英文混合文本 ===\n")

    segmenter = TextSegmenter(min_length=10, max_length=200, prefer_length=50)

    mixed_text = "The quick brown fox jumps over the lazy dog. 这是一段中文文本，用于测试分段功能。We can also mix English and Chinese together! 这样可以测试标点符号的识别是否正常。"

    chunks = [mixed_text[i:i+15] for i in range(0, len(mixed_text), 15)]

    segments = []
    for chunk in chunks:
        result = segmenter.add_text(chunk)
        if result:
            segments.extend(result)

    final = segmenter.flush()
    if final:
        segments.append(final)

    print(f"总共分成 {len(segments)} 段：\n")
    for i, seg in enumerate(segments, 1):
        print(f"段落 {i} ({len(seg)} 字符): {seg}")
        print()


def test_edge_cases():
    """测试边缘情况"""
    print("\n=== 测试边缘情况 ===\n")

    segmenter = TextSegmenter(min_length=10, max_length=200, prefer_length=50)

    # 空文本
    print("1. 空文本:")
    result = segmenter.add_text("")
    print(f"   结果: {result}")
    print()

    # 只有标点
    print("2. 只有标点:")
    result = segmenter.add_text("。。。！！！")
    final = segmenter.flush()
    print(f"   结果: {final}")
    print()

    # 单个字符
    segmenter = TextSegmenter(min_length=1, max_length=200, prefer_length=50)
    print("3. 单个字符:")
    result = segmenter.add_text("测")
    final = segmenter.flush()
    print(f"   结果: {final}")
    print()

    # 连续标点
    segmenter = TextSegmenter(min_length=10, max_length=200, prefer_length=50)
    print("4. 连续标点:")
    test = "测试文本一。。。测试文本二！！！测试文本三？？？"
    chunks = [test[i:i+5] for i in range(0, len(test), 5)]
    segments = []
    for chunk in chunks:
        result = segmenter.add_text(chunk)
        if result:
            segments.extend(result)
    final = segmenter.flush()
    if final:
        segments.append(final)
    print(f"   分段数: {len(segments)}")
    for i, seg in enumerate(segments, 1):
        print(f"   段 {i}: {seg}")
    print()


if __name__ == "__main__":
    print("TTS 文本分段功能测试\n")
    print("=" * 60)

    try:
        test_basic_segmentation()
        test_stream_segmentation()
        test_long_text_force_split()
        test_mixed_language()
        test_edge_cases()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
