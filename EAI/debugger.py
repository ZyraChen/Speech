"""
检查文本长度和内容分析工具
"""

import json
import os

def analyze_text_length(slides_path, speech_path):
    """分析文本长度"""

    print("=" * 80)
    print(" " * 25 + "文本长度分析")
    print("=" * 80)
    print()

    # 1. 分析幻灯片
    print("【1. 幻灯片文本】")
    print("-" * 80)

    if slides_path.endswith('.pdf'):
        print(f"文件类型: PDF")

        # 尝试提取
        try:
            import pdfplumber
            with pdfplumber.open(slides_path) as pdf:
                slides_text = ""
                for i, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        slides_text += page_text + "\n"
                        print(f"  第{i}页: {len(page_text)} 字符")
        except:
            try:
                import PyPDF2
                with open(slides_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    slides_text = ""
                    for i, page in enumerate(pdf.pages, 1):
                        page_text = page.extract_text()
                        if page_text:
                            slides_text += page_text + "\n"
                            print(f"  第{i}页: {len(page_text)} 字符")
            except:
                print("✗ 无法读取PDF")
                return
    else:
        # 文本文件
        with open(slides_path, 'r', encoding='utf-8') as f:
            slides_text = f.read()

    print(f"\n幻灯片总字符数: {len(slides_text)}")
    print(f"幻灯片总行数: {len(slides_text.splitlines())}")
    print(f"幻灯片总词数(英文): {len(slides_text.split())}")

    # 显示前500字符
    print(f"\n前500字符内容:")
    print("-" * 80)
    print(slides_text[:500])
    print("-" * 80)

    # 2. 分析演讲稿
    print("\n【2. 演讲稿JSON】")
    print("-" * 80)

    with open(speech_path, 'r', encoding='utf-8') as f:
        speech_json = f.read()

    print(f"JSON总字符数: {len(speech_json)}")
    print(f"JSON总行数: {len(speech_json.splitlines())}")

    # 解析JSON
    try:
        # 清理可能的markdown标记
        cleaned = speech_json.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

        plan_count = len(data.get('plan', []))
        script_count = len(data.get('script', []))

        print(f"Plan项数: {plan_count}")
        print(f"Script项数: {script_count}")

        # 分析每个script的长度
        print(f"\nScript各项长度:")
        for i, item in enumerate(data.get('script', []), 1):
            text = item.get('text', '')
            print(f"  Script {i}: {len(text)} 字符")

        # 显示第一个script
        if script_count > 0:
            first_script = data['script'][0]['text']
            print(f"\n第一个Script内容(前300字符):")
            print("-" * 80)
            print(first_script[:300])
            print("-" * 80)

    except Exception as e:
        print(f"✗ JSON解析失败: {e}")

    # 3. 计算prompt总长度
    print("\n【3. Prompt总长度估算】")
    print("-" * 80)

    prompt_template = """你是一位专业的演讲稿评审专家...
# 幻灯片内容
{slides}
# 演讲稿
{speech}
# 评估任务
...
"""

    template_length = len(prompt_template) - len("{slides}") - len("{speech}")
    total_length = template_length + len(slides_text) + len(speech_json)

    print(f"Prompt模板: ~{template_length} 字符")
    print(f"幻灯片内容: {len(slides_text)} 字符")
    print(f"演讲稿内容: {len(speech_json)} 字符")
    print(f"估算总长度: {total_length} 字符")

    # 4. 建议
    print("\n【4. 优化建议】")
    print("-" * 80)

    if total_length > 16000:
        print("⚠️  Prompt太长,容易超时")
        print("\n建议:")

        if len(slides_text) > 6000:
            print(f"  1. 幻灯片文本过长({len(slides_text)}字符)")
            print(f"     - 可能包含大量空白或重复内容")
            print(f"     - 建议清理后只保留核心内容")

        if len(speech_json) > 6000:
            print(f"  2. 演讲稿过长({len(speech_json)}字符)")
            print(f"     - 建议评估时只用关键部分")
            print(f"     - 或分段评估")

        print(f"\n  3. 使用压缩选项:")
        print(f"     evaluator.build_evaluation_prompt(")
        print(f"         slides_text[:5000],  # 只用前5000字符")
        print(f"         speech_json[:5000]")
        print(f"     )")
    else:
        print("✓ 长度合理,可以正常评估")

    print("\n" + "=" * 80)

    return slides_text, speech_json


def clean_pdf_text(text):
    """清理PDF提取的文本"""

    import re

    print("\n清理PDF文本...")
    print(f"原始长度: {len(text)} 字符")

    # 1. 移除多余空白
    text = re.sub(r'\n\s*\n', '\n\n', text)  # 多个空行变成两个
    text = re.sub(r' +', ' ', text)  # 多个空格变成一个

    # 2. 移除页眉页脚标记
    text = re.sub(r'--- Page \d+ ---\n', '', text)

    # 3. 移除重复的分隔符
    text = re.sub(r'-{3,}', '---', text)
    text = re.sub(r'={3,}', '===', text)

    print(f"清理后长度: {len(text)} 字符")
    print(f"减少了: {len(text) - len(text)} 字符")

    return text


def save_cleaned_text(slides_text, output_path="presentation_cleaned.txt"):
    """保存清理后的文本"""

    cleaned = clean_pdf_text(slides_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    print(f"✓ 清理后的文本已保存到: {output_path}")
    print(f"  使用方法: load_files('{output_path}', 'speech.txt')")

    return cleaned


def main():
    """主函数"""

    import sys

    if len(sys.argv) > 2:
        slides_path = sys.argv[1]
        speech_path = sys.argv[2]
    else:
        slides_path = "presentation.pdf"
        speech_path = "speech_gemini.txt"

    print(f"\n分析文件:")
    print(f"  幻灯片: {slides_path}")
    print(f"  演讲稿: {speech_path}")
    print()

    if not os.path.exists(slides_path):
        print(f"✗ 文件不存在: {slides_path}")
        return

    if not os.path.exists(speech_path):
        print(f"✗ 文件不存在: {speech_path}")
        return

    # 分析长度
    slides_text, speech_json = analyze_text_length(slides_path, speech_path)

    # 询问是否保存清理版本
    if slides_text and len(slides_text) > 8000:
        print("\n" + "=" * 80)
        print("是否保存清理后的幻灯片文本? (y/n): ", end="")

        # 自动保存(不需要输入)
        print("y (自动保存)")
        save_cleaned_text(slides_text)


if __name__ == "__main__":
    main()