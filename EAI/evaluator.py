#!/usr/bin/env python3
"""
演讲稿质量评估程序
输入：PDF幻灯片 + JSON格式演讲稿
输出：ROUGE-L、BERTScore、GPTScore评估结果
"""

import json
import pdfplumber
from typing import Dict, List
import warnings
from rouge_score import rouge_scorer
# from bert_score import score as bert_score
warnings.filterwarnings('ignore')
from openai import OpenAI
HAS_OPENAI = True

def extract_text_from_pdf(pdf_path: str) -> str:
    """从PDF中提取所有文本内容"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_content = []

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(f"--- 第{page_num}页 ---\n{text}")

            return "\n\n".join(text_content)
    except Exception as e:
        print(f"PDF读取错误: {e}")
        return ""


def load_speech_json(json_path: str) -> Dict:
    """加载JSON格式的演讲稿"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 处理可能包含```json```标记的情况
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            return json.loads(content)
    except Exception as e:
        print(f"JSON读取错误: {e}")
        return {}


def extract_speech_text(speech_data: Dict) -> str:
    """从JSON演讲数据中提取演讲稿文本"""
    speech_texts = []

    if 'script' in speech_data:
        for item in speech_data['script']:
            if 'text' in item:
                speech_texts.append(item['text'])

    return "\n\n".join(speech_texts)


def evaluate_rouge_l(reference: str, generated: str) -> Dict[str, float]:
    """计算ROUGE-L分数"""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(reference, generated)
    rouge_l = scores['rougeL']

    return {
        'precision': rouge_l.precision,
        'recall': rouge_l.recall,
        'fmeasure': rouge_l.fmeasure
    }

#
# def evaluate_bert_score(reference: str, generated: str, lang: str = 'en') -> Dict[str, float]:
#     """计算BERTScore"""
#     P, R, F1 = bert_score([generated], [reference], lang=lang, verbose=False)
#
#     return {
#         'precision': P.item(),
#         'recall': R.item(),
#         'f1': F1.item()
#     }


def evaluate_gpt_score(reference: str, generated: str,
                       openai_api_key: str = None,
                       openai_base_url: str = None) -> Dict:
    """使用GPT模型评估质量"""
    if not HAS_OPENAI:
        return {
            'error': '未安装openai库',
            'overall': None,
            'coherence': None,
            'relevance': None,
            'fluency': None
        }

    if not openai_api_key:
        return {
            'error': '未提供OpenAI API密钥',
            'overall': None,
            'coherence': None,
            'relevance': None,
            'fluency': None
        }

    try:
        if openai_base_url:
            client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)
        else:
            client = OpenAI(api_key=openai_api_key)

        results = {}
        aspects = {
            'overall': 'Overall Quality (content coverage, logical coherence, language fluency)',
            'coherence': 'Logical Coherence (clear reasoning, well-structured)',
            'relevance': 'Content Relevance (match with slide content)',
            'fluency': 'Language Fluency (natural expression, easy to understand)'
        }

        for aspect, description in aspects.items():
            prompt = f"""As a professional speech evaluation expert, please evaluate the {description} of the following speech script.

【Slide Reference Content】
{reference[:2000]}  # 限制长度避免token超限

【Generated Speech Script】
{generated[:2000]}

Please rate the speech script from 1-10 (10 being the highest) and provide brief feedback.

Output in JSON format:
{{
    "score": <score from 1-10>,
    "feedback": "<brief evaluation>"
}}
"""

            response = client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[
                    {"role": "system", "content": "You are a professional speech evaluation expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )

            result_text = response.choices[0].message.content.strip()

            try:
                if '```json' in result_text:
                    result_text = result_text.split('```json')[1].split('```')[0].strip()
                elif '```' in result_text:
                    result_text = result_text.split('```')[1].split('```')[0].strip()

                result = json.loads(result_text)
                results[aspect] = {
                    'score': result.get('score', 0) / 10.0,
                    'raw_score': result.get('score', 0),
                    'feedback': result.get('feedback', '')
                }
            except:
                results[aspect] = {
                    'score': None,
                    'raw_score': None,
                    'feedback': result_text
                }

        return results

    except Exception as e:
        return {
            'error': f'GPT API调用失败: {str(e)}',
            'overall': None,
            'coherence': None,
            'relevance': None,
            'fluency': None
        }


def comprehensive_evaluation(pdf_path: str, json_path: str,
                             use_gpt: bool = False,
                             openai_api_key: str = None,
                             openai_base_url: str = None,
                             lang: str = 'en') -> Dict:
    """综合评估"""
    print("=" * 70)
    print("演讲稿质量评估系统")
    print("=" * 70)

    # 1. 读取PDF幻灯片
    print("\n[1/5] 正在读取PDF幻灯片...")
    slide_content = extract_text_from_pdf(pdf_path)
    if not slide_content:
        print("错误：无法读取PDF内容")
        return {}
    print(f"      成功提取 {len(slide_content)} 个字符")

    # 2. 读取JSON演讲稿
    print("\n[2/5] 正在读取JSON演讲稿...")
    speech_data = load_speech_json(json_path)
    if not speech_data:
        print("错误：无法读取JSON内容")
        return {}

    speech_text = extract_speech_text(speech_data)
    if not speech_text:
        print("错误：无法从JSON中提取演讲文本")
        return {}
    print(f"      成功提取 {len(speech_text)} 个字符")

    # 3. ROUGE-L评估
    print("\n[3/5] 计算ROUGE-L分数（关键点覆盖率）...")
    rouge_scores = evaluate_rouge_l(slide_content, speech_text)
    print(f"      ROUGE-L F-measure: {rouge_scores['fmeasure']:.4f}")

    # # 4. BERTScore评估
    # print("\n[4/5] 计算BERTScore（语义覆盖率）...")
    # bert_scores = evaluate_bert_score(slide_content, speech_text, lang=lang)
    # print(f"      BERTScore F1: {bert_scores['f1']:.4f}")

    # 5. GPTScore评估
    gpt_scores = None
    if use_gpt and openai_api_key:
        print("\n[5/5] 使用GPT进行质量评估...")
        gpt_scores = evaluate_gpt_score(slide_content, speech_text,
                                        openai_api_key, openai_base_url)
        if 'error' not in gpt_scores:
            print("      GPT评估完成")
        else:
            print(f"      {gpt_scores['error']}")
    else:
        print("\n[5/5] 跳过GPTScore评估")

    return {
        'slide_content_length': len(slide_content),
        'speech_text_length': len(speech_text),
        'rouge_l': rouge_scores,
        'gpt_score': gpt_scores
    }


def print_evaluation_report(results: Dict):
    """打印评估报告"""
    if not results:
        print("\n评估失败，无结果")
        return

    print("\n" + "=" * 70)
    print("评估报告")
    print("=" * 70)

    print(f"\n【内容统计】")
    print(f"  幻灯片内容长度: {results.get('slide_content_length', 0)} 字符")
    print(f"  演讲稿内容长度: {results.get('speech_text_length', 0)} 字符")

    # ROUGE-L
    if 'rouge_l' in results:
        print("\n【1. ROUGE-L - 关键点覆盖率】")
        print(f"  Precision (精确率): {results['rouge_l']['precision']:.4f}")
        print(f"  Recall (召回率):    {results['rouge_l']['recall']:.4f}")
        print(f"  F-measure (F值):    {results['rouge_l']['fmeasure']:.4f}")
        print(f"  说明: F值越高，表示演讲稿越好地覆盖了幻灯片的关键点")

    # GPTScore
    if 'gpt_score' in results and results['gpt_score']:
        print("\n【3. GPTScore - 语义质量评估】")
        gpt_scores = results['gpt_score']

        if 'error' in gpt_scores:
            print(f"  错误: {gpt_scores['error']}")
        else:
            aspect_names = {
                'overall': 'Overall Quality',
                'coherence': 'Logical Coherence',
                'relevance': 'Content Relevance',
                'fluency': 'Language Fluency'
            }

            for aspect, name in aspect_names.items():
                if aspect in gpt_scores and gpt_scores[aspect]:
                    print(f"\n  {name}:")
                    score_data = gpt_scores[aspect]
                    if score_data.get('raw_score'):
                        print(f"    Score: {score_data['raw_score']}/10")
                    if score_data.get('feedback'):
                        print(f"    Feedback: {score_data['feedback']}")
    else:
        print("\n【3. GPTScore - 语义质量评估】")
        print("  未执行（需要OpenAI API密钥）")

    # 综合评价
    print("\n【综合评价】")
    rouge_f = results.get('rouge_l', {}).get('fmeasure', 0)

    if rouge_f >= 0.4:
        quality = "优秀 (Excellent)"
    elif rouge_f >= 0.3 :
        quality = "良好 (Good)"
    elif rouge_f >= 0.2:
        quality = "中等 (Fair)"
    else:
        quality = "需要改进 (Needs Improvement)"

    print(f"  整体质量评级: {quality}")
    print("=" * 70 + "\n")


def main():
    """主函数"""
    # 文件路径
    pdf_path = "presentation.pdf"
    json_path = "speech_gemini.txt"

    # 执行评估（不使用GPT）
    results = comprehensive_evaluation(
        pdf_path=pdf_path,
        json_path=json_path,
        use_gpt=True,
        openai_api_key="YOUR_API_KEY",
        openai_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        lang='en'  # 'en'表示英文，'zh'表示中文
    )

    # 打印报告
    print_evaluation_report(results)

    # 保存结果
    output_path = "rouge_score_gemini.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"评估结果已保存到: {output_path}\n")


if __name__ == "__main__":
    main()
