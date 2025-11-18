"""
演讲稿评估系统 - 完整使用示例
使用你上传的 presentation.pdf 和 speech.txt 文件
"""

# 首先需要安装必要的库来提取PDF文本
# pip install PyPDF2 或 pip install pdfplumber

import json
import re
from pathlib import Path

# 方法1: 使用 PyPDF2
def extract_text_from_pdf_pypdf2(pdf_path):
    """使用PyPDF2提取PDF文本"""
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        print("请安装PyPDF2: pip install PyPDF2")
        return None


# 方法2: 使用 pdfplumber (推荐，效果更好)
def extract_text_from_pdf_pdfplumber(pdf_path):
    """使用pdfplumber提取PDF文本"""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        print("请安装pdfplumber: pip install pdfplumber")
        return None


# 方法3: 使用已经提取好的文本（如果你已经有了）
def use_existing_text():
    """
    如果你已经通过 window.fs.readFile 或其他方式获得了PDF文本，
    可以直接使用
    """
    # 这是从你上传的 presentation.pdf 中提取的文本
    # 在实际使用中，你可以通过上面的方法获取
    pdf_text = """你的PDF文本内容"""
    return pdf_text


# ========== 完整的评估流程 ==========

def run_complete_evaluation():
    """运行完整的评估流程"""

    print("=" * 70)
    print("开始演讲稿质量评估...")
    print("=" * 70)

    # 步骤1: 提取PDF文本
    print("\n[步骤 1/4] 提取PDF幻灯片文本...")

    pdf_path = "presentation.pdf"

    # 尝试使用pdfplumber（推荐）
    pdf_text = extract_text_from_pdf_pdfplumber(pdf_path)

    # 如果pdfplumber不可用，尝试PyPDF2
    if pdf_text is None:
        pdf_text = extract_text_from_pdf_pypdf2(pdf_path)

    # 如果都不可用，使用预先提取的文本
    if pdf_text is None:
        print("⚠ PDF库未安装，使用预提取的文本...")
        # 从你提供的文档中，我们已经有了文本内容
        pdf_text = """Advancing Fact-checking for Large Language Models
via Argumentative Reasoning
Zhaoqun Li

Background: LLM fact-checking
Critical Factual Drawbacks
Large language models (LLMs) inherently tend to produce false, wrong, or
misleading content—known as "hallucinations"
...
"""  # 完整的PDF文本

    print(f"✓ PDF文本提取成功 ({len(pdf_text)} 字符)")

    # 步骤2: 读取演讲稿JSON
    print("\n[步骤 2/4] 读取演讲稿JSON...")

    speech_path = "speech.txt"
    try:
        with open(speech_path, 'r', encoding='utf-8') as f:
            speech_json = f.read()
        print(f"✓ 演讲稿读取成功")
    except FileNotFoundError:
        print(f"✗ 文件未找到: {speech_path}")
        return

    # 步骤3: 创建评估器并评估
    print("\n[步骤 3/4] 执行质量评估...")

    # 导入评估器类（需要先运行上面的代码）
    from speech_evaluator import SpeechEvaluator

    evaluator = SpeechEvaluator(pdf_text, speech_json)
    results = evaluator.evaluate_all()

    print(f"✓ 评估完成")

    # 步骤4: 生成并保存报告
    print("\n[步骤 4/4] 生成评估报告...")

    report = evaluator.generate_report()

    # 保存报告
    report_path = "evaluation_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✓ 报告已保存至: {report_path}")

    # 同时打印到控制台
    print("\n" + report)

    # 返回结果供进一步分析
    return results


# ========== 批量评估多个演讲稿 ==========

def batch_evaluation(pdf_path, speech_files):
    """
    批量评估多个演讲稿

    Args:
        pdf_path: PDF幻灯片路径
        speech_files: 演讲稿JSON文件列表
    """
    from speech_evaluator import SpeechEvaluator

    # 提取PDF文本
    pdf_text = extract_text_from_pdf_pdfplumber(pdf_path)
    if pdf_text is None:
        pdf_text = extract_text_from_pdf_pypdf2(pdf_path)

    results_summary = []

    for speech_file in speech_files:
        print(f"\n评估: {speech_file}")
        print("-" * 70)

        with open(speech_file, 'r', encoding='utf-8') as f:
            speech_json = f.read()

        evaluator = SpeechEvaluator(pdf_text, speech_json)
        results = evaluator.evaluate_all()

        results_summary.append({
            'file': speech_file,
            'overall_score': results['overall_score'],
            'grade': results['grade'],
            'scores': {
                'content': results['content_consistency']['overall_score'],
                'structure': results['structure']['overall_score'],
                'language': results['language_quality']['overall_score'],
                'detail': results['detail_richness']['overall_score'],
                'time': results['time_management']['overall_score']
            }
        })

        # 保存单独的报告
        report = evaluator.generate_report()
        report_file = speech_file.replace('.txt', '_evaluation.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

    # 生成对比报告
    generate_comparison_report(results_summary)

    return results_summary


def generate_comparison_report(results_summary):
    """生成多个演讲稿的对比报告"""

    report = "=" * 70 + "\n"
    report += " " * 20 + "演讲稿质量对比报告\n"
    report += "=" * 70 + "\n\n"

    # 按总分排序
    sorted_results = sorted(results_summary,
                            key=lambda x: x['overall_score'],
                            reverse=True)

    report += "排名 | 文件名 | 总分 | 等级 | 内容 | 结构 | 语言 | 细节 | 时间\n"
    report += "-" * 70 + "\n"

    for i, result in enumerate(sorted_results, 1):
        scores = result['scores']
        report += f"{i:2d}. {Path(result['file']).stem:20s} "
        report += f"{result['overall_score']:5.1%} {result['grade']:8s} "
        report += f"{scores['content']:5.1%} {scores['structure']:5.1%} "
        report += f"{scores['language']:5.1%} {scores['detail']:5.1%} "
        report += f"{scores['time']:5.1%}\n"

    report += "\n" + "=" * 70 + "\n"

    # 保存对比报告
    with open('comparison_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print("对比报告已保存至: comparison_report.txt")


# ========== 详细的评估指标导出 ==========

def export_detailed_metrics(pdf_path, speech_path, output_format='json'):
    """
    导出详细的评估指标

    Args:
        pdf_path: PDF路径
        speech_path: 演讲稿路径
        output_format: 输出格式 ('json', 'csv', 'excel')
    """
    from speech_evaluator import SpeechEvaluator

    # 提取和评估
    pdf_text = extract_text_from_pdf_pdfplumber(pdf_path)
    with open(speech_path, 'r', encoding='utf-8') as f:
        speech_json = f.read()

    evaluator = SpeechEvaluator(pdf_text, speech_json)
    results = evaluator.evaluate_all()

    if output_format == 'json':
        # 导出JSON格式
        output_file = 'evaluation_metrics.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✓ 指标已导出至: {output_file}")

    elif output_format == 'csv':
        # 导出CSV格式
        import csv
        output_file = 'evaluation_metrics.csv'

        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['维度', '子指标', '得分'])

            for dimension, data in results.items():
                if dimension in ['overall_score', 'grade', 'weights']:
                    continue
                for metric, score in data.items():
                    if metric != 'overall_score':
                        writer.writerow([dimension, metric, f"{score:.2%}" if isinstance(score, float) else score])

        print(f"✓ 指标已导出至: {output_file}")

    return results


# ========== 主函数 ==========

if __name__ == "__main__":


    speech_files = ['speech_qwen_vl.txt', 'speech_gemini.txt']
    batch_evaluation('presentation.pdf', speech_files)
    export_detailed_metrics('presentation.pdf', 'speech_qwen_vl.txt', 'json')
    export_detailed_metrics('presentation.pdf', 'speech_gemini.txt', 'json')


