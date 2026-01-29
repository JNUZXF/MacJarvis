#!/bin/bash
# 验证测试交付文件的完整性

echo "=================================="
echo "Mac Agent 测试交付验证"
echo "=================================="
echo ""

# 检查核心文件
echo "📋 检查核心文件..."
files=(
    "tests/run_tool_tests.py"
    "tests/test_cases_config.py"
    "tests/view_results.py"
    "tests/README_测试交付.md"
    "tests/测试使用指南.md"
    "docs/工具测试完整报告_20260129.md"
)

missing=0
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
        missing=$((missing + 1))
    fi
done

echo ""
echo "📊 检查测试结果文件..."
result_count=$(ls tests/test_results/*.json 2>/dev/null | wc -l)
report_count=$(ls tests/test_results/*.md 2>/dev/null | wc -l)
echo "  JSON结果文件: $result_count 个"
echo "  Markdown报告: $report_count 个"

if [ $result_count -gt 0 ] && [ $report_count -gt 0 ]; then
    echo "  ✅ 测试结果文件存在"
else
    echo "  ❌ 测试结果文件缺失"
    missing=$((missing + 1))
fi

echo ""
echo "🔍 检查最新测试结果..."
latest_json=$(ls -t tests/test_results/*.json 2>/dev/null | head -1)
if [ -f "$latest_json" ]; then
    echo "  最新JSON: $(basename $latest_json)"
    total=$(cat "$latest_json" | grep -o '"total_tests": [0-9]*' | grep -o '[0-9]*')
    passed=$(cat "$latest_json" | grep -o '"passed": [0-9]*' | grep -o '[0-9]*')
    failed=$(cat "$latest_json" | grep -o '"failed": [0-9]*' | grep -o '[0-9]*')
    echo "  总测试数: $total"
    echo "  通过: $passed ✅"
    echo "  失败: $failed ❌"
    if [ ! -z "$total" ] && [ ! -z "$passed" ]; then
        success_rate=$(echo "scale=1; $passed * 100 / $total" | bc)
        echo "  成功率: ${success_rate}%"
    fi
fi

echo ""
echo "=================================="
if [ $missing -eq 0 ]; then
    echo "✅ 所有交付文件完整"
    echo "=================================="
    exit 0
else
    echo "❌ 有 $missing 个文件缺失"
    echo "=================================="
    exit 1
fi
