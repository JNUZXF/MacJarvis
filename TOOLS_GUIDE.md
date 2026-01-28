# MacJarvis 工具完整指南

> **无所不能的Mac电脑管家 - 47个强大工具，覆盖工作生活的方方面面**

## 📊 工具概览

MacJarvis现在拥有**47个强大工具**，从基础的系统信息到高级的文档批量处理，全方位满足您的日常需求。

### 工具分类统计

| 类别 | 工具数量 | 主要功能 |
|------|---------|---------|
| 🖥️ 系统信息与监控 | 4 | 系统状态、磁盘、电池 |
| ⚙️ 进程管理 | 2 | 进程列表、性能监控 |
| 🌐 网络工具 | 7 | DNS、WiFi、下载、Ping |
| 📁 文件管理 | 9 | 读写、搜索、目录操作 |
| 📄 文档处理 | 2 | **多线程批量总结**、文本提取 |
| 🎨 媒体处理 | 3 | 图片压缩、截屏、视频信息 |
| 💻 开发者工具 | 3 | Git操作、Python执行 |
| 🚀 生产力工具 | 4 | 压缩、哈希、剪贴板 |
| 🔧 系统管理 | 2 | 环境变量、Spotlight |
| 📊 数据处理 | 3 | JSON、CSV、文本统计 |
| ⏰ 时间工具 | 1 | 时区转换 |
| 🎯 应用管理 | 3 | 打开应用、URL |

---

## 🌟 重点功能：多线程文档批量总结

### batch_summarize_documents

这是MacJarvis的**核心功能**之一，能够以多线程方式快速总结大量文档，并生成精美的Markdown报告。

**支持的文档格式：**
- 📕 PDF文件
- 📘 Word文档（.docx, .doc）
- 📗 Excel表格（.xlsx, .xls）
- 📄 纯文本文件（.txt, .md, .json, .csv, .log）

**参数说明：**

```json
{
  "file_paths": ["~/Documents/report1.pdf", "~/Downloads/data.xlsx"],
  "output_path": "~/Desktop/summary_report.md",
  "max_workers": 4,
  "summary_length": "medium"
}
```

- `file_paths`: 要总结的文件路径列表
- `output_path`: 保存摘要报告的路径（Markdown格式）
- `max_workers`: 并发线程数（1-10，默认4）
- `summary_length`: 摘要长度
  - `short`: 简短摘要（约5行）
  - `medium`: 中等摘要（约15行）
  - `long`: 详细摘要（约30行）

**使用示例：**

```
请帮我总结以下文档：
1. ~/Documents/项目报告.pdf
2. ~/Documents/数据分析.xlsx
3. ~/Downloads/会议记录.docx

生成摘要到 ~/Desktop/文档总结.md，使用中等长度，4个并发线程
```

**输出示例：**

生成的Markdown报告包含：
- 📋 处理摘要（时间、文件数、成功率）
- 📄 每个文档的详细摘要
- ✅ 处理状态（成功/失败）
- 📊 统计信息（字符数、行数）

---

## 📖 所有工具详细说明

### 🖥️ 系统信息与监控工具

#### 1. system_info
**功能**: 获取系统版本、内核与硬件概览

**参数**: 无

**示例**:
```
告诉我电脑的系统信息
```

---

#### 2. disk_usage
**功能**: 查看磁盘空间使用情况

**参数**: 无

**示例**:
```
查看磁盘使用情况
```

---

#### 3. battery_status
**功能**: 查看电源与电池状态

**参数**: 无

**示例**:
```
电池还剩多少电？
```

---

#### 4. system_sleep_settings
**功能**: 查看睡眠与电源策略

**参数**: 无

**示例**:
```
查看电源管理设置
```

---

### ⚙️ 进程管理工具

#### 5. process_list
**功能**: 列出当前所有进程

**参数**: 无

**示例**:
```
显示所有正在运行的进程
```

---

#### 6. top_processes
**功能**: 按CPU使用率排序获取前N个进程

**参数**:
- `limit`: 显示的进程数量（1-50，默认10）

**示例**:
```
显示CPU占用最高的5个进程
```

---

### 🌐 网络工具

#### 7. open_ports
**功能**: 列出正在监听的网络端口

**参数**: 无

**示例**:
```
查看哪些端口在监听
```

---

#### 8. network_info
**功能**: 获取网络接口信息

**参数**: 无

**示例**:
```
显示网络配置
```

---

#### 9. dns_info
**功能**: 获取DNS配置

**参数**: 无

**示例**:
```
查看DNS设置
```

---

#### 10. wifi_info
**功能**: 获取当前WiFi连接信息

**参数**: 无

**示例**:
```
我连的是哪个WiFi？
```

---

#### 11. download_file
**功能**: 从URL下载文件到本地

**参数**:
- `url`: 文件URL
- `output_path`: 保存路径

**示例**:
```
下载 https://example.com/file.zip 到 ~/Downloads/file.zip
```

---

#### 12. check_website_status
**功能**: 检查网站是否可访问及HTTP状态码

**参数**:
- `url`: 网站URL

**示例**:
```
检查 https://www.google.com 是否可以访问
```

---

#### 13. ping_host
**功能**: Ping指定主机检测网络连接

**参数**:
- `host`: 主机名或IP地址
- `count`: Ping次数（1-10，默认4）

**示例**:
```
ping google.com 5次
```

---

### 📁 文件管理工具

#### 14. list_directory
**功能**: 列出目录内容

**参数**:
- `path`: 目录路径

**示例**:
```
列出 ~/Documents 下的所有文件
```

---

#### 15. search_files
**功能**: 按通配符在目录中搜索文件

**参数**:
- `path`: 搜索目录
- `pattern`: 文件名通配符（如*.pdf）
- `max_results`: 最大结果数（1-500，默认100）

**示例**:
```
在 ~/Documents 中搜索所有PDF文件
```

---

#### 16. read_file
**功能**: 读取文件内容

**参数**:
- `path`: 文件路径
- `max_bytes`: 最大读取字节数（默认20000）

**示例**:
```
读取 ~/Documents/notes.txt 的内容
```

---

#### 17. write_file
**功能**: 写入文本到文件

**参数**:
- `path`: 文件路径
- `content`: 要写入的内容
- `overwrite`: 是否覆盖（默认false）
- `max_bytes`: 最大写入字节数（默认50000）

**示例**:
```
创建文件 ~/Desktop/test.txt，内容为"Hello World"
```

---

#### 18. append_file
**功能**: 追加文本到文件

**参数**:
- `path`: 文件路径
- `content`: 要追加的内容
- `create_if_missing`: 文件不存在时是否创建（默认false）

**示例**:
```
在 ~/Documents/log.txt 末尾添加一行"新的日志记录"
```

---

#### 19. make_directory
**功能**: 创建目录

**参数**:
- `path`: 目录路径
- `parents`: 是否创建父目录（默认true）
- `exist_ok`: 目录已存在时是否报错（默认true）

**示例**:
```
创建目录 ~/Projects/NewProject/src
```

---

#### 20. file_info
**功能**: 获取文件或目录的详细信息

**参数**:
- `path`: 文件路径

**示例**:
```
查看 ~/Documents/report.pdf 的详细信息
```

---

#### 21. find_in_file
**功能**: 在文本文件中查找关键词

**参数**:
- `path`: 文件路径
- `query`: 搜索关键词
- `case_sensitive`: 是否区分大小写（默认true）
- `max_matches`: 最大匹配数（默认50）

**示例**:
```
在 ~/Documents/code.py 中查找"function"这个词
```

---

#### 22. move_to_trash
**功能**: 将文件或目录移动到回收站

**参数**:
- `path`: 文件路径

**示例**:
```
把 ~/Desktop/old_file.txt 移到回收站
```

---

### 📄 文档处理工具（核心功能）

#### 23. batch_summarize_documents ⭐
**功能**: **多线程批量总结多个文档**

详见上方"重点功能"部分

---

#### 24. extract_text_from_documents
**功能**: 批量从多个文档中提取纯文本

**参数**:
- `file_paths`: 文件路径列表
- `output_directory`: 输出目录

**示例**:
```
从以下文件提取文本并保存到 ~/Desktop/extracted/：
1. ~/Documents/report.pdf
2. ~/Documents/data.xlsx
```

---

### 🎨 媒体处理工具

#### 25. compress_images
**功能**: 批量压缩图片文件

**参数**:
- `image_paths`: 图片文件路径列表
- `output_directory`: 输出目录
- `quality`: 压缩质量（1-100，默认85）

**示例**:
```
压缩 ~/Pictures/photo1.jpg 和 photo2.jpg，质量80，保存到 ~/Desktop/compressed/
```

---

#### 26. capture_screenshot
**功能**: 捕获屏幕截图

**参数**:
- `output_path`: 保存路径
- `display`: 显示器编号（默认1）
- `interactive`: 是否交互式选择区域（默认false）

**示例**:
```
截屏并保存到 ~/Desktop/screenshot.png
```

---

#### 27. get_video_info
**功能**: 获取视频文件的详细信息

**参数**:
- `video_path`: 视频文件路径

**示例**:
```
查看 ~/Movies/video.mp4 的视频信息
```

---

### 💻 开发者工具

#### 28. git_status
**功能**: 查询Git仓库的当前状态

**参数**:
- `repository_path`: Git仓库路径（默认当前目录）

**示例**:
```
查看 ~/Projects/MyApp 的git状态
```

---

#### 29. git_log
**功能**: 查看Git提交日志

**参数**:
- `repository_path`: Git仓库路径
- `limit`: 显示的提交数量（1-100，默认10）

**示例**:
```
查看最近20条git提交记录
```

---

#### 30. run_python_script
**功能**: 执行指定的Python脚本

**参数**:
- `script_path`: Python脚本路径
- `args`: 脚本参数列表（可选）
- `working_directory`: 工作目录（可选）

**示例**:
```
运行 ~/Scripts/test.py，参数为 --verbose
```

---

### 🚀 生产力工具

#### 31. compress_files
**功能**: 将文件或目录压缩为ZIP格式

**参数**:
- `source_paths`: 要压缩的文件或目录路径列表
- `output_zip`: 输出ZIP文件路径

**示例**:
```
将 ~/Documents/Project 文件夹压缩到 ~/Desktop/project.zip
```

---

#### 32. extract_archive
**功能**: 解压缩ZIP文件

**参数**:
- `archive_path`: ZIP文件路径
- `output_directory`: 解压到的目录

**示例**:
```
解压 ~/Downloads/archive.zip 到 ~/Desktop/extracted/
```

---

#### 33. calculate_hash
**功能**: 计算文件的哈希值

**参数**:
- `file_path`: 文件路径
- `algorithm`: 哈希算法（md5/sha1/sha256，默认sha256）

**示例**:
```
计算 ~/Downloads/file.zip 的SHA256哈希值
```

---

#### 34. clipboard_operations
**功能**: 读取或写入系统剪贴板

**参数**:
- `operation`: 操作类型（read/write）
- `content`: 写入的内容（write操作时需要）

**示例**:
```
读取剪贴板内容
```

```
将"Hello World"写入剪贴板
```

---

### 🔧 系统管理工具

#### 35. get_environment_variables
**功能**: 获取系统环境变量

**参数**:
- `variable_name`: 特定环境变量名（可选，留空返回所有）

**示例**:
```
获取PATH环境变量
```

---

#### 36. spotlight_search
**功能**: 使用macOS Spotlight搜索文件和应用

**参数**:
- `query`: 搜索关键词
- `limit`: 返回结果数量（1-50，默认10）

**示例**:
```
用Spotlight搜索"Python"相关的文件
```

---

### 📊 数据处理工具

#### 37. json_formatter
**功能**: 格式化或压缩JSON数据

**参数**:
- `json_string`: JSON字符串
- `mode`: 格式化模式（pretty/compact，默认pretty）

**示例**:
```
格式化这个JSON: {"name":"John","age":30}
```

---

#### 38. csv_analyzer
**功能**: 分析CSV文件，提供基本统计信息

**参数**:
- `csv_path`: CSV文件路径

**示例**:
```
分析 ~/Documents/data.csv 文件
```

---

#### 39. text_statistics
**功能**: 分析文本文件的统计信息

**参数**:
- `file_path`: 文本文件路径

**示例**:
```
统计 ~/Documents/article.txt 的字数和行数
```

---

### ⏰ 时间工具

#### 40. timezone_converter
**功能**: 转换时间到不同时区

**参数**:
- `timestamp`: ISO格式时间戳或"now"表示当前时间
- `target_timezone`: 目标时区（如Asia/Shanghai）

**示例**:
```
将当前时间转换到纽约时区
```

---

### 🎯 应用管理工具

#### 41. open_app
**功能**: 打开指定应用

**参数**:
- `app_name`: 应用名称

**示例**:
```
打开Safari浏览器
```

---

#### 42. open_url
**功能**: 在默认浏览器打开URL

**参数**:
- `url`: 网址

**示例**:
```
打开 https://www.apple.com
```

---

#### 43. list_applications
**功能**: 列出/Applications下的所有应用

**参数**: 无

**示例**:
```
列出所有已安装的应用
```

---

## 🎯 典型使用场景

### 场景1：文档整理大师

```
我有一堆文档需要整理：
1. 用batch_summarize_documents批量总结10个PDF报告
2. 用compress_files将整理好的文档打包
3. 用calculate_hash验证文件完整性
4. 用clipboard_operations复制文件哈希值
```

### 场景2：开发者助手

```
1. 用git_status查看项目状态
2. 用git_log查看最近提交
3. 用run_python_script运行测试脚本
4. 用text_statistics统计代码行数
```

### 场景3：网络管理员

```
1. 用ping_host检测网络连接
2. 用check_website_status监控网站状态
3. 用open_ports查看开放端口
4. 用network_info获取网络配置
```

### 场景4：媒体处理专家

```
1. 用compress_images批量压缩100张照片
2. 用capture_screenshot截取屏幕
3. 用get_video_info分析视频信息
```

---

## 🚀 性能特点

- **多线程处理**: batch_summarize_documents支持最多10个并发线程
- **大文件支持**: 可处理大型PDF、Excel文件（自动限制读取大小）
- **安全性**: 所有文件操作都经过路径验证和权限检查
- **容错性**: 批量操作中单个文件失败不影响其他文件处理
- **详细报告**: 所有批量操作都会生成详细的执行报告

---

## 📝 最佳实践

### 1. 文件路径
- 使用绝对路径或波浪号（~）表示用户目录
- 示例: `~/Documents/file.txt` 或 `/Users/username/Documents/file.txt`

### 2. 批量操作
- 建议并发线程数不超过4-6个，避免系统负载过高
- 大文件列表建议分批处理

### 3. 权限控制
- 默认只能访问用户目录及其子目录
- 可通过环境变量配置额外的允许路径

### 4. 错误处理
- 所有工具都会返回详细的错误信息
- 批量操作会记录每个文件的处理状态

---

## 🔮 未来规划

- [ ] 添加OCR文字识别工具
- [ ] 支持更多文档格式（PPT、Pages等）
- [ ] 增加AI驱动的智能文档分类
- [ ] 实现云存储集成（iCloud、Dropbox）
- [ ] 添加日历和提醒功能
- [ ] 支持数据库操作工具

---

## 📞 技术支持

如有问题或建议，请查看项目README.md或提交Issue。

**享受MacJarvis带来的高效工作体验！** 🎉
