# File: backend/agent/tools/media/processor.py
# Purpose: 媒体处理工具（图片压缩、截图、视频信息等）
import json
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path


@dataclass
class CompressImagesTool:
    """批量压缩图片"""

    name: str = "compress_images"
    description: str = "批量压缩图片文件，支持JPG/PNG格式，减小文件大小"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "image_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "图片文件路径列表",
                    },
                    "output_directory": {"type": "string", "description": "输出目录"},
                    "quality": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "压缩质量（1-100，默认85）",
                    },
                },
                "required": ["image_paths", "output_directory"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        image_paths = args.get("image_paths", [])
        output_dir_str = args.get("output_directory", "")
        quality = int(args.get("quality", 85))

        if not image_paths or not output_dir_str:
            return {"ok": False, "error": "image_paths and output_directory are required"}

        try:
            from PIL import Image

            output_dir = normalize_path(output_dir_str)
            ensure_path_allowed(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            results = []
            for img_path_str in image_paths:
                img_path = normalize_path(img_path_str)
                ensure_path_allowed(img_path)

                if not img_path.exists():
                    results.append(
                        {
                            "file": str(img_path),
                            "success": False,
                            "error": "文件不存在",
                        }
                    )
                    continue

                try:
                    img = Image.open(img_path)
                    output_file = output_dir / img_path.name

                    # 转换RGBA到RGB
                    if img.mode == "RGBA":
                        img = img.convert("RGB")

                    img.save(output_file, optimize=True, quality=quality)

                    original_size = img_path.stat().st_size
                    compressed_size = output_file.stat().st_size
                    ratio = (
                        (1 - compressed_size / original_size) * 100
                        if original_size > 0
                        else 0
                    )

                    results.append(
                        {
                            "file": str(img_path),
                            "output": str(output_file),
                            "success": True,
                            "original_size": original_size,
                            "compressed_size": compressed_size,
                            "compression_ratio": f"{ratio:.1f}%",
                        }
                    )
                except Exception as e:
                    results.append(
                        {"file": str(img_path), "success": False, "error": str(e)}
                    )

            return {"ok": True, "data": {"results": results}}

        except ImportError:
            return {"ok": False, "error": "PIL库未安装，请安装pillow: pip install pillow"}
        except Exception as e:
            return {"ok": False, "error": f"图片压缩失败: {str(e)}"}


@dataclass
class CaptureScreenshotTool:
    """截屏工具"""

    name: str = "capture_screenshot"
    description: str = "捕获屏幕截图，可选择全屏或指定区域"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "保存截图的路径"},
                    "display": {
                        "type": "integer",
                        "description": "显示器编号（默认1）",
                    },
                    "interactive": {
                        "type": "boolean",
                        "description": "是否交互式选择区域",
                    },
                },
                "required": ["output_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        output_path_str = args.get("output_path", "")
        display = args.get("display", 1)
        interactive = args.get("interactive", False)

        if not output_path_str:
            return {"ok": False, "error": "output_path is required"}

        try:
            output_path = normalize_path(output_path_str)
            ensure_path_allowed(output_path)

            cmd = ["/usr/sbin/screencapture"]

            if interactive:
                cmd.append("-i")  # 交互式选择
            else:
                cmd.extend(["-D", str(display)])  # 指定显示器

            cmd.append(str(output_path))

            runner = CommandRunner(timeout_s=30)
            result = runner.run(cmd)

            if result.get("ok"):
                return {
                    "ok": True,
                    "data": {"screenshot_path": str(output_path)},
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"截图失败: {str(e)}"}


@dataclass
class GetVideoInfoTool:
    """获取视频文件信息"""

    name: str = "get_video_info"
    description: str = "获取视频文件的详细信息（时长、分辨率、编码等）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"video_path": {"type": "string", "description": "视频文件路径"}},
                "required": ["video_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        video_path_str = args.get("video_path", "")

        if not video_path_str:
            return {"ok": False, "error": "video_path is required"}

        try:
            video_path = normalize_path(video_path_str)
            ensure_path_allowed(video_path)

            if not video_path.exists():
                return {"ok": False, "error": "视频文件不存在"}

            # 使用ffprobe获取视频信息
            runner = CommandRunner(timeout_s=30)
            result = runner.run(
                [
                    "/usr/local/bin/ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(video_path),
                ]
            )

            if result.get("ok"):
                try:
                    info = json.loads(result.get("stdout", "{}"))
                    return {"ok": True, "data": info}
                except json.JSONDecodeError:
                    return {"ok": False, "error": "解析视频信息失败"}
            else:
                # ffprobe不可用，返回基本信息
                stat = video_path.stat()
                return {
                    "ok": True,
                    "data": {
                        "file": str(video_path),
                        "size": stat.st_size,
                        "note": "ffprobe不可用，仅提供基本信息",
                    },
                }

        except Exception as e:
            return {"ok": False, "error": f"获取视频信息失败: {str(e)}"}
