"""
基于Qwen VL Plus API的演讲稿评估系统
Speech Evaluation System with Qwen VL Plus API
"""

import json
import re
import time
from typing import Dict, Optional
import openai


class QwenVLPlus:
    """Qwen VL Plus API 封装"""

    def __init__(self, api_key):
        self.model = "qwen-vl-plus"
        self.llm = openai.OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def _cons_kwargs(self, messages: list[dict]) -> dict:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "timeout": 60,
        }
        return kwargs

    def completion(self, messages: list[dict], enable_thinking=False, return_json=False) -> dict:
        response_format = {"type": "json_object"} if not enable_thinking and return_json else {"type": "text"}
        extra_body = {"enable_thinking": enable_thinking}

        try:
            rsp = self.llm.chat.completions.create(
                **self._cons_kwargs(messages),
                extra_body=extra_body,
                response_format=response_format
            )
        except openai.RateLimitError as e:
            print("⚠️  API请求超过速率限制,等待60秒后重试...")
            time.sleep(60)
            rsp = self.llm.chat.completions.create(
                **self._cons_kwargs(messages),
                extra_body=extra_body,
                response_format=response_format
            )
        except openai.APITimeoutError as e:
            print("⚠️  API请求超时,等待60秒后重试...")
            time.sleep(60)
            rsp = self.llm.chat.completions.create(
                **self._cons_kwargs(messages),
                extra_body=extra_body,
                response_format=response_format
            )

        return rsp.choices[0].message.content


class QwenSpeechEvaluator:
    """使用Qwen API的演讲稿评估器"""

    def __init__(self, api_key: str):
        """
        初始化评估器

        Args:
            api_key: 阿里云DashScope API密钥
        """
        self.qwen = QwenVLPlus(api_key)

    def build_evaluation_prompt(self, slides_text: str, speech_json: str) -> str:
        """构建评估prompt"""

        prompt = """你是一名专业的演讲质量评估专家，擅长评估根据幻灯片生成的演讲规划和演讲稿的质量。
你将接收到一些信息，包括：
1. 幻灯片内容
2. 不同系统生成的“演讲规划”（plan）和“演讲稿”（script）
你的任务是对每份演讲规划和演讲稿分别进行0-100分评分，并给出结构化评价。
一、请从以下五个维度对演讲规划进行评分：
1. 覆盖完整度：是否覆盖每页幻灯片的关键内容，不遗漏、不跳页。
2. 结构合理性：是否形成合理的讲述结构，如：引入-解释-举例-小结。步骤是否清晰、逻辑是否连贯。
3. 时间合理性：每页的时间分配是否符合常规演讲节奏，不过长、不敷衍。
4. 规划清晰度：演讲步骤是否表述明确、可执行，是否易于理解。
5. 幻灯片对齐度：规划是否与幻灯片逐页严格对应，没有内容错位。
二、请从以下六个维度对演讲稿评分：
1. 内容准确性：是否忠实反映幻灯片内容，没有事实性错误或幻觉。
2. 扩展性（解释 + 举例 + 延伸）：是否对 PPT 要点进行了合理扩展，而不是简单朗读。是否提供解释、类比或示例。
3. 口语自然度：是否听起来像真实演讲者说话，而不是生硬书面语。是否存在“AI 腔”“机械化表达”等问题。
4. 逻辑流畅性：内容是否连贯，是否存在跳跃、断裂。过渡是否自然。
5. 吸引力：开头是否能吸引听众。是否有过渡、强调、小结，让内容更好听。
6. 幻灯片对齐度：每段文字是否对应正确的幻灯片页面。
三、评分规则：每个维度0-100分
0-20 = 很差  
20-40 = 较差  
40-60 = 一般  
60-80 = 良好  
80-100 = 优秀  
计算方式：
plan_total= 5个规划维度的平均分  
script_total = 6个演讲维度的平均分  
overall_score = (plan_total + script_total) / 2  
四、输出格式如下（json格式）：
  "plan_scores": coverage,structure,time_reasonableness,clarity,slide_alignment
  "script_scores":accuracy,elaboration,oral_naturalness,logical_flow,engagement,slide_alignment
  "plan_total":xx
  "script_total": xx
  "overall_score": xx
  "comments": strengths",weaknesses",suggestions

# 幻灯片内容

"""
        prompt += slides_text
        prompt += """

# 生成的演讲稿

"""
        prompt += speech_json
        prompt += """

"""

        return prompt

    def evaluate_speech(self, slides_text: str, speech_json: str) -> Optional[Dict]:
        """
        评估演讲稿

        Args:
            slides_text: 幻灯片文本
            speech_json: 演讲稿JSON

        Returns:
            评估结果字典
        """

        print("=" * 80)
        print("正在使用Qwen API评估演讲稿...")
        print("=" * 80)
        print()

        # 构建prompt
        print("步骤1: 构建评估prompt...")
        prompt = self.build_evaluation_prompt(slides_text, speech_json)
        print(f"✓ Prompt构建完成 ({len(prompt)} 字符)")
        print()

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        # 调用API
        print("步骤2: 调用Qwen API...")
        print("(这可能需要1-2分钟)")

        try:
            response_text = self.qwen.completion(
                messages=messages,
                enable_thinking=False,
                return_json=True  # 要求返回JSON格式
            )

            print("✓ API调用成功")
            print()

        except Exception as e:
            print(f"✗ API调用失败: {e}")
            return None

        # 解析响应
        print("步骤3: 解析响应...")
        result = self._parse_response(response_text)

        if result:
            print("✓ 解析成功")
            print()
        else:
            print("✗ 解析失败")
            print()

        return result

    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """解析API响应"""

        try:
            # 清理响应文本
            cleaned = response_text.strip()

            # 移除可能的markdown标记
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]

            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # 解析JSON
            result = json.loads(cleaned)

            # # 验证必要字段
            # if 'dimensions' not in result or 'overall' not in result:
            #     print("⚠️  响应缺少必要字段")
            #     return None

            return result

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"响应内容: {response_text[:500]}...")
            return None
        except Exception as e:
            print(f"解析错误: {e}")
            return None

    def generate_report(self, result: Dict) -> str:
        """生成评估报告"""

        if not result:
            return "评估失败,无法生成报告"

        lines = []
        lines.append("=" * 80)
        lines.append(" " * 20 + "Qwen API 演讲稿质量评估报告")
        lines.append("=" * 80)
        lines.append("")

        # 总体评估
        overall = result.get('overall', {})
        lines.append("【总体评估】")
        lines.append("-" * 80)
        score = overall.get('weighted_score', 0)
        grade = overall.get('grade', 'N/A')
        lines.append(f"综合得分: {score:.1f}/10")
        lines.append(f"等级: {grade}")
        lines.append("")

        summary = overall.get('summary', '')
        if summary:
            lines.append(f"总体评价:")
            lines.append(f"{summary}")
            lines.append("")

        # 各维度评分
        lines.append("=" * 80)
        lines.append("【维度详细评分】")
        lines.append("=" * 80)
        lines.append("")

        dimensions = result.get('dimensions', {})
        dim_names = {
            'content_consistency': ('内容一致性', 30),
            'structure': ('结构合理性', 25),
            'language_quality': ('语言质量', 20),
            'detail_richness': ('细节丰富度', 15),
            'speech_adaptability': ('演讲适配性', 10)
        }

        for dim_key, (dim_name, weight) in dim_names.items():
            dim_data = dimensions.get(dim_key, {})
            dim_score = dim_data.get('score', 0)

            lines.append(f"【{dim_name}】权重:{weight}% | 得分:{dim_score:.1f}/10")
            lines.append("-" * 80)

            # 分析
            analysis = dim_data.get('analysis', '')
            if analysis:
                lines.append(f"{analysis}")
                lines.append("")

            # 优点
            strengths = dim_data.get('strengths', [])
            if strengths:
                lines.append("✓ 优点:")
                for s in strengths:
                    lines.append(f"  • {s}")
                lines.append("")

            # 不足
            weaknesses = dim_data.get('weaknesses', [])
            if weaknesses:
                lines.append("✗ 不足:")
                for w in weaknesses:
                    lines.append(f"  • {w}")
                lines.append("")

        # 改进建议
        lines.append("=" * 80)
        lines.append("【改进建议】")
        lines.append("=" * 80)
        lines.append("")

        improvements = overall.get('improvements', [])
        for i, imp in enumerate(improvements, 1):
            lines.append(f"{i}. {imp}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("评估完成!")
        lines.append("=" * 80)

        return '\n'.join(lines)


# ============ 工具函数 ============

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """从PDF中提取文本"""

    print(f"\n正在从PDF提取文本: {pdf_path}")
    print("-" * 80)

    text = None
    errors = []

    # 尝试方法1: pdfplumber
    try:
        import pdfplumber
        print("✓ pdfplumber 已找到,开始提取...")

        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {i} ---\n{page_text}\n"
                print(f"  处理第 {i} 页...", end="\r")

        print(f"\n✓ pdfplumber 提取成功 ({len(text)} 字符)     ")
        return text

    except ImportError as e:
        error_msg = f"pdfplumber导入失败: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
    except Exception as e:
        error_msg = f"pdfplumber提取失败: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    # 尝试方法2: PyPDF2
    if text is None:
        try:
            import PyPDF2
            print("✓ PyPDF2 已找到,开始提取...")

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for i, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {i} ---\n{page_text}\n"
                    print(f"  处理第 {i} 页...", end="\r")

            print(f"\n✓ PyPDF2 提取成功 ({len(text)} 字符)     ")
            return text

        except ImportError as e:
            error_msg = f"PyPDF2导入失败: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"PyPDF2提取失败: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)

    # 所有方法都失败
    if text is None:
        print("\n" + "=" * 80)
        print("⚠️  PDF文本提取失败")
        print("=" * 80)
        print("\n错误信息:")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")

        print("\n【解决方案】")
        print("-" * 80)

        print("\n方案1: 安装PDF库")
        print("  在命令行运行以下命令之一:")
        import sys
        print(f"    {sys.executable} -m pip install pdfplumber")
        print("  或")
        print(f"    {sys.executable} -m pip install PyPDF2")

        print("\n方案2: 手动提取文本")
        print("  1. 用PDF阅读器打开文件")
        print("  2. 选择所有文本 (Ctrl+A)")
        print("  3. 复制 (Ctrl+C)")
        print("  4. 粘贴到文本文件并保存为 presentation_text.txt")
        print("  5. 使用文本文件代替PDF:")
        print('     load_files("presentation_text.txt", "speech.txt")')

        print("\n方案3: 运行诊断工具")
        print("  python pdf_diagnostic.py")

        print("=" * 80)

    return text


def load_files(slides_path: str, speech_path: str) -> tuple:
    """加载文件"""

    # 读取幻灯片
    if slides_path.endswith('.pdf'):
        slides_text = extract_text_from_pdf(slides_path)
        if slides_text is None:
            return None, None
    else:
        with open(slides_path, 'r', encoding='utf-8') as f:
            slides_text = f.read()
        print(f"✓ 文本文件加载成功: {len(slides_text)} 字符")

    # 读取演讲稿
    with open(speech_path, 'r', encoding='utf-8') as f:
        speech_json = f.read()
    print(f"✓ 演讲稿加载成功: {len(speech_json)} 字符")

    return slides_text, speech_json


def save_results(result: Dict, report: str, output_dir: str = '.'):
    """保存评估结果"""

    import os

    # 保存JSON
    json_path = os.path.join(output_dir, 'evaluation_result.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"JSON结果已保存: {json_path}")

    # 保存报告
    report_path = os.path.join(output_dir, 'evaluation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"文本报告已保存: {report_path}")


# ============ 主评估函数 ============

def run_qwen_evaluation(api_key: str, slides_path: str, speech_path: str):
    """
    运行Qwen API评估

    Args:
        api_key: 阿里云DashScope API密钥
        slides_path: 幻灯片路径 (.pdf 或 .txt)
        speech_path: 演讲稿路径
    """

    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Qwen API 演讲稿质量评估" + " " * 22 + "║")
    print("╚" + "=" * 78 + "╝\n")

    # 加载文件
    print("【步骤1】加载文件")
    print("=" * 80)
    slides_text, speech_json = load_files(slides_path, speech_path)

    if not slides_text or not speech_json:
        print("\n✗ 文件加载失败,评估终止")
        return None

    print()

    # 创建评估器
    print("【步骤2】创建评估器")
    print("=" * 80)
    evaluator = QwenSpeechEvaluator(api_key)
    print("✓ 评估器创建成功")
    print()

    # 执行评估
    print("【步骤3】执行评估")
    print("=" * 80)
    result = evaluator.evaluate_speech(slides_text, speech_json)

    if not result:
        print("\n✗ 评估失败")
        return None

    # 生成报告
    print("【步骤4】生成报告")
    print("=" * 80)
    report = evaluator.generate_report(result)
    print("✓ 报告生成完成")
    print()

    # 保存结果
    print("【步骤5】保存结果")
    print("=" * 80)
    save_results(result, report)
    print()

    # 显示报告
    print(report)

    print("\n" + "=" * 80)
    print("评估完成!")
    print("=" * 80)
    print("\n查看生成的文件:")
    print("  - gemini_evaluation_result.json  (JSON格式结果)")
    print("  - gemini_evaluation_report.txt   (文本格式报告)")
    print("=" * 80)

    return result, report


if __name__ == "__main__":


    api_key = "sk-8faa7214041347609e67d5d09cec7266"
    run_qwen_evaluation(
    api_key=api_key,
    slides_path="presentation.pdf",
    speech_path="speech_gemini.txt"
    )