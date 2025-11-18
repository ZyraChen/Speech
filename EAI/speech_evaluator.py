"""
演讲稿质量评估系统 - 支持PDF幻灯片
Presentation Speech Quality Evaluation System with PDF Support
"""

import json
import re
from typing import Dict, List, Tuple
from collections import Counter
import math


class SpeechEvaluator:
    """演讲稿评估器 - 支持PDF提取的文本"""

    def __init__(self, slides_text: str, speech_json_str: str):
        """
        初始化评估器

        Args:
            slides_text: 从PDF提取的幻灯片文本内容
            speech_json_str: 演讲稿JSON字符串
        """
        self.slides_content = slides_text

        # 解析JSON,处理可能的markdown代码块
        speech_json_str = speech_json_str.strip()
        if speech_json_str.startswith('```json'):
            speech_json_str = speech_json_str[7:]
        if speech_json_str.startswith('```'):
            speech_json_str = speech_json_str[3:]
        if speech_json_str.endswith('```'):
            speech_json_str = speech_json_str[:-3]
        speech_json_str = speech_json_str.strip()

        self.speech_data = json.loads(speech_json_str)
        self.plan = self.speech_data.get('plan', [])
        self.script = self.speech_data.get('script', [])

    # ============ 1. 内容一致性评估 ============

    def evaluate_content_consistency(self) -> Dict:
        """评估内容一致性"""

        # 提取幻灯片关键词和关键概念
        slides_keywords = self._extract_keywords(self.slides_content)
        slides_concepts = self._extract_key_concepts(self.slides_content)

        # 提取演讲稿关键词和概念
        speech_text = ' '.join([s['text'] for s in self.script])
        speech_keywords = self._extract_keywords(speech_text)
        speech_concepts = self._extract_key_concepts(speech_text)

        # 计算覆盖率
        keyword_coverage = self._calculate_coverage(slides_keywords, speech_keywords)
        concept_coverage = self._calculate_coverage(slides_concepts, speech_concepts)

        # 检查幻灯片标题覆盖
        slide_coverage = self._check_slide_title_coverage()

        # 检测潜在幻觉
        hallucination_risk = self._detect_hallucination_risk(
            slides_keywords, speech_keywords
        )

        # 检查关键数据和事实
        fact_accuracy = self._check_fact_consistency()

        return {
            'keyword_coverage': keyword_coverage,
            'concept_coverage': concept_coverage,
            'slide_title_coverage': slide_coverage,
            'fact_accuracy': fact_accuracy,
            'hallucination_risk_score': hallucination_risk,
            'overall_score': (keyword_coverage + concept_coverage +
                            slide_coverage + fact_accuracy +
                            (1 - hallucination_risk)) / 5
        }

    def _extract_keywords(self, text: str) -> Counter:
        """提取关键词"""
        # 转小写
        text = text.lower()
        # 提取英文单词和中文词组
        # 英文单词
        english_words = re.findall(r'\b[a-z]{4,}\b', text)
        # 中文词组(2-4字)
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)

        # 合并
        all_words = english_words + chinese_words

        # 过滤停用词
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are',
            'was', 'were', 'be', 'been', 'have', 'has', 'had',
            'this', 'that', 'these', 'those', 'will', 'would',
            '这个', '那个', '可以', '我们', '他们', '什么', '怎么'
        }

        keywords = [w for w in all_words if w not in stopwords]
        return Counter(keywords)

    def _extract_key_concepts(self, text: str) -> set:
        """提取关键概念(多词短语)"""
        # 提取专业术语和重要概念
        # 英文: 大写字母开头的短语、连字符词组
        english_concepts = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        english_concepts += re.findall(r'\b[a-z]+-[a-z]+(?:-[a-z]+)*\b', text)

        # 中文: 常见的专业术语模式
        chinese_concepts = re.findall(r'[\u4e00-\u9fff]{3,8}', text)

        # 提取缩写词
        abbreviations = re.findall(r'\b[A-Z]{2,}\b', text)

        all_concepts = set(english_concepts + chinese_concepts + abbreviations)

        # 过滤太常见的词
        filtered = {c for c in all_concepts if len(c) >= 3}
        return filtered

    def _calculate_coverage(self, source_items, target_items) -> float:
        """计算覆盖率"""
        if not source_items:
            return 1.0

        if isinstance(source_items, Counter):
            source_keys = set(source_items.keys())
            target_keys = set(target_items.keys()) if isinstance(target_items, Counter) else set(target_items)
            covered = len(source_keys & target_keys)
            return covered / len(source_keys)
        else:
            covered = len(source_items & target_items)
            return covered / len(source_items)

    def _check_slide_title_coverage(self) -> float:
        """检查幻灯片标题覆盖率"""
        # 从plan中提取标题
        plan_titles = [p.get('title', '') for p in self.plan if p.get('title')]

        if not plan_titles:
            return 1.0

        # 在演讲稿中查找标题关键词
        speech_text = ' '.join([s['text'] for s in self.script]).lower()

        covered = 0
        for title in plan_titles:
            # 提取标题中的关键词
            title_words = re.findall(r'\b\w+\b', title.lower())
            # 至少一半的关键词出现在演讲稿中
            matches = sum(1 for word in title_words if word in speech_text and len(word) > 3)
            if matches >= len(title_words) / 2:
                covered += 1

        return covered / len(plan_titles)

    def _check_fact_consistency(self) -> float:
        """检查事实一致性"""
        # 提取数字、年份、人名等关键事实
        slides_numbers = re.findall(r'\b\d{4}\b|\b\d+%\b|\b\d+\.\d+\b', self.slides_content)
        slides_names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', self.slides_content)

        speech_text = ' '.join([s['text'] for s in self.script])
        speech_numbers = re.findall(r'\b\d{4}\b|\b\d+%\b|\b\d+\.\d+\b', speech_text)
        speech_names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', speech_text)

        # 检查幻灯片中的事实是否在演讲稿中被提及
        total_facts = len(slides_numbers) + len(slides_names)
        if total_facts == 0:
            return 1.0

        matched_facts = 0
        matched_facts += sum(1 for num in slides_numbers if num in speech_text)
        matched_facts += sum(1 for name in slides_names if name in speech_text)

        return matched_facts / total_facts

    def _detect_hallucination_risk(self, source_keywords: Counter,
                                   target_keywords: Counter) -> float:
        """检测幻觉风险"""
        if not target_keywords:
            return 0.0

        # 演讲稿中出现但幻灯片中没有的关键词
        new_keywords = set(target_keywords.keys()) - set(source_keywords.keys())

        # 计算新词占比
        risk_ratio = len(new_keywords) / len(target_keywords)

        # 正常化:新词占比在30%以内是合理的(适当扩展)
        # 超过30%认为风险增加
        if risk_ratio <= 0.3:
            return risk_ratio / 0.3 * 0.3  # 映射到0-0.3
        else:
            return 0.3 + (risk_ratio - 0.3) / 0.7 * 0.7  # 映射到0.3-1.0

    # ============ 2. 结构合理性评估 ============

    def evaluate_structure(self) -> Dict:
        """评估结构合理性"""

        coherence_score = self._evaluate_coherence()
        time_balance = self._evaluate_time_balance()
        transition_score = self._evaluate_transitions()
        organization_score = self._evaluate_organization()

        return {
            'coherence_score': coherence_score,
            'time_balance_score': time_balance,
            'transition_score': transition_score,
            'organization_score': organization_score,
            'overall_score': (coherence_score + time_balance +
                            transition_score + organization_score) / 4
        }

    def _evaluate_coherence(self) -> float:
        """评估逻辑连贯性"""
        slide_numbers = [p['slide'] for p in self.plan]
        script_slides = [s['slide'] for s in self.script]

        # 检查是否顺序合理
        is_sequential = all(slide_numbers[i] <= slide_numbers[i+1]
                           for i in range(len(slide_numbers)-1))
        script_sequential = all(script_slides[i] <= script_slides[i+1]
                               for i in range(len(script_slides)-1))

        # 检查是否每张幻灯片都有对应的演讲内容
        plan_slides = set(slide_numbers)
        script_slide_set = set(script_slides)
        coverage = len(plan_slides & script_slide_set) / len(plan_slides) if plan_slides else 1.0

        return (float(is_sequential) + float(script_sequential) + coverage) / 3

    def _parse_duration(self, duration_str: str) -> float:
        """
        解析时间字符串,统一转换为分钟
        支持格式: "2 minutes", "30 seconds", "1.5 minutes", "90s", "2min"
        """
        if not duration_str:
            return 0.0

        duration_str = duration_str.lower().strip()

        # 提取数字
        number_match = re.search(r'(\d+\.?\d*)', duration_str)
        if not number_match:
            return 0.0

        number = float(number_match.group(1))

        # 判断单位
        if 'second' in duration_str or duration_str.endswith('s'):
            # 秒转分钟
            return number / 60
        elif 'hour' in duration_str or duration_str.endswith('h'):
            # 小时转分钟
            return number * 60
        else:
            # 默认为分钟 (minute, min, m)
            return number

    def _evaluate_time_balance(self) -> float:
        """评估时间分配平衡性"""
        durations = []
        for p in self.plan:
            duration_str = p.get('duration', '0 minute')
            duration_minutes = self._parse_duration(duration_str)
            if duration_minutes > 0:
                durations.append(duration_minutes)

        if not durations or len(durations) < 3:
            return 1.0

        # 计算变异系数(标准差/均值)
        mean = sum(durations) / len(durations)
        if mean == 0:
            return 0.0

        variance = sum((x - mean) ** 2 for x in durations) / len(durations)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean

        # 变异系数小于0.5较好
        balance_score = max(0, 1 - cv)
        return min(balance_score, 1.0)

    def _evaluate_transitions(self) -> float:
        """评估过渡自然性"""
        transition_phrases = [
            "let's", 'next', 'now', 'moving', 'turn to', 'consider',
            'however', 'therefore', 'furthermore', 'additionally',
            'in conclusion', 'to summarize', 'brings us to',
            '接下来', '现在', '然后', '因此', '此外', '总之',
            '让我们', '下面', '首先', '其次', '最后'
        ]

        transition_count = 0
        for i, script in enumerate(self.script):
            if i == 0:  # 跳过第一张
                continue
            text = script['text'].lower()
            # 检查段落开头是否有过渡词
            first_sentence = text.split('.')[0] if '.' in text else text
            if any(phrase in first_sentence.lower() for phrase in transition_phrases):
                transition_count += 1

        ideal_transitions = len(self.script) - 1
        return transition_count / ideal_transitions if ideal_transitions > 0 else 1.0

    def _evaluate_organization(self) -> float:
        """评估整体组织结构"""
        # 检查是否有引言、主体、结论
        has_intro = any('introduction' in p.get('title', '').lower() or
                       'intro' in p.get('title', '').lower() or
                       i == 0 for i, p in enumerate(self.plan))

        has_conclusion = any('conclusion' in p.get('title', '').lower() or
                            'summary' in p.get('title', '').lower() or
                            'q&a' in p.get('title', '').lower() or
                            i == len(self.plan) - 1
                            for i, p in enumerate(self.plan))

        has_body = len(self.plan) >= 3

        return (float(has_intro) + float(has_conclusion) + float(has_body)) / 3

    # ============ 3. 语言质量评估 ============

    def evaluate_language_quality(self) -> Dict:
        """评估语言质量"""

        clarity_score = self._evaluate_clarity()
        conversational_score = self._evaluate_conversational_style()
        vocabulary_richness = self._evaluate_vocabulary()
        professionalism = self._evaluate_professionalism()

        return {
            'clarity_score': clarity_score,
            'conversational_score': conversational_score,
            'vocabulary_richness': vocabulary_richness,
            'professionalism_score': professionalism,
            'overall_score': (clarity_score + conversational_score +
                            vocabulary_richness + professionalism) / 4
        }

    def _evaluate_clarity(self) -> float:
        """评估清晰度"""
        all_text = ' '.join([s['text'] for s in self.script])
        sentences = re.split(r'[.!?。!?]+', all_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        # 计算平均句子长度
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)

        # 理想句子长度:12-25词
        if 12 <= avg_length <= 25:
            return 1.0
        elif avg_length < 12:
            return 0.7 + (avg_length / 12) * 0.3
        else:
            return max(0.3, 1 - (avg_length - 25) / 25)

    def _evaluate_conversational_style(self) -> float:
        """评估口语化程度"""
        conversational_markers = [
            "let's", "we'll", "i'm", "you'll", "we're", "i'll",
            'today', 'now', 'here', 'our', 'my', 'your',
            'everyone', 'thank you', 'hello', 'hi',
            '大家', '我们', '今天', '现在', '让我们',
            '你们', '咱们', '这里', '那么'
        ]

        all_text = ' '.join([s['text'] for s in self.script]).lower()
        words = all_text.split()

        marker_count = sum(1 for word in words
                          if any(marker in word for marker in conversational_markers))

        # 每100词有2-6个口语标记比较理想
        ratio = marker_count / len(words) * 100 if words else 0

        if 2 <= ratio <= 6:
            return 1.0
        elif ratio < 2:
            return ratio / 2
        else:
            return max(0.5, 1 - (ratio - 6) / 10)

    def _evaluate_vocabulary(self) -> float:
        """评估词汇丰富度"""
        all_text = ' '.join([s['text'] for s in self.script]).lower()
        # 提取所有词
        words = re.findall(r'\b[a-z]+\b', all_text)
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', all_text)
        all_words = words + chinese_words

        if not all_words:
            return 0.0

        # 类型-词例比
        unique_words = len(set(all_words))
        total_words = len(all_words)
        ttr = unique_words / total_words

        # TTR通常在0.35-0.65之间
        if 0.35 <= ttr <= 0.65:
            return 1.0
        elif ttr < 0.35:
            return ttr / 0.35
        else:
            return max(0.6, 1 - (ttr - 0.65) / 0.35)

    def _evaluate_professionalism(self) -> float:
        """评估专业性"""
        # 检查是否使用了幻灯片中的专业术语
        all_text = ' '.join([s['text'] for s in self.script])

        # 从幻灯片提取的专业术语
        technical_terms = [
            'llm', 'large language model', 'fact-checking', 'hallucination',
            'argumentation', 'evidence', 'verification', 'benchmark',
            'algorithm', 'dataset', 'evaluation', 'accuracy'
        ]

        term_usage = sum(1 for term in technical_terms if term in all_text.lower())

        # 至少使用一半的专业术语
        return min(term_usage / (len(technical_terms) / 2), 1.0)

    # ============ 4. 细节丰富度评估 ============

    def evaluate_detail_richness(self) -> Dict:
        """评估细节丰富度"""

        expansion_ratio = self._calculate_expansion_ratio()
        example_usage = self._check_example_usage()
        explanation_quality = self._evaluate_explanations()
        context_provision = self._evaluate_context()

        return {
            'expansion_ratio_score': expansion_ratio,
            'example_usage_score': example_usage,
            'explanation_quality': explanation_quality,
            'context_provision': context_provision,
            'overall_score': (expansion_ratio + example_usage +
                            explanation_quality + context_provision) / 4
        }

    def _calculate_expansion_ratio(self) -> float:
        """计算内容扩展比"""
        slides_words = len(self.slides_content.split())
        speech_words = len(' '.join([s['text'] for s in self.script]).split())

        if slides_words == 0:
            return 0.0

        ratio = speech_words / slides_words

        # 理想扩展比:1.5-3倍
        if 1.5 <= ratio <= 3:
            return 1.0
        elif ratio < 1.5:
            return ratio / 1.5
        else:
            return max(0.5, 1 - (ratio - 3) / 3)

    def _check_example_usage(self) -> float:
        """检查例子使用"""
        example_indicators = [
            'example', 'for instance', 'such as', 'like',
            'consider', "let's take", 'case', 'illustrate',
            '例如', '比如', '举例', '案例', '考虑'
        ]

        all_text = ' '.join([s['text'] for s in self.script]).lower()

        example_count = sum(all_text.count(indicator)
                           for indicator in example_indicators)

        # 每4-5张幻灯片至少1个例子
        ideal_examples = len(self.script) / 4.5
        score = min(example_count / max(ideal_examples, 1), 1.0)

        return score

    def _evaluate_explanations(self) -> float:
        """评估解释质量"""
        explanation_markers = [
            'this means', 'in other words', 'specifically',
            'that is', 'namely', 'essentially', 'simply put',
            '也就是说', '换句话说', '具体来说', '简单来说'
        ]

        all_text = ' '.join([s['text'] for s in self.script]).lower()

        explanation_count = sum(all_text.count(marker)
                               for marker in explanation_markers)

        # 每3张幻灯片至少1个解释
        ideal_explanations = len(self.script) / 3
        score = min(explanation_count / max(ideal_explanations, 1), 1.0)

        return score

    def _evaluate_context(self) -> float:
        """评估背景信息提供"""
        # 检查是否提供了背景、动机、意义等信息
        context_keywords = [
            'background', 'motivation', 'why', 'important', 'challenge',
            'problem', 'goal', 'objective', 'significance',
            '背景', '动机', '为什么', '重要', '挑战', '问题', '目标', '意义'
        ]

        all_text = ' '.join([s['text'] for s in self.script]).lower()

        context_count = sum(1 for keyword in context_keywords if keyword in all_text)

        # 至少提及3-5个背景相关概念
        return min(context_count / 4, 1.0)

    # ============ 5. 时间规划评估 ============

    def evaluate_time_management(self) -> Dict:
        """评估时间规划"""

        total_time = self._calculate_total_time()
        duration_appropriateness = self._evaluate_duration_appropriateness(total_time)
        time_distribution = self._evaluate_time_distribution()
        pace_consistency = self._evaluate_pace()

        return {
            'total_minutes': total_time,
            'duration_appropriateness': duration_appropriateness,
            'time_distribution_score': time_distribution,
            'pace_consistency': pace_consistency,
            'overall_score': (duration_appropriateness + time_distribution +
                            pace_consistency) / 3
        }

    def _calculate_total_time(self) -> float:
        """计算总时长(分钟)"""
        total = 0.0
        for p in self.plan:
            duration_str = p.get('duration', '0 minute')
            total += self._parse_duration(duration_str)
        return total

    def _evaluate_duration_appropriateness(self, total_minutes: float) -> float:
        """评估总时长合理性"""
        num_slides = len(self.plan)

        # 理想时长:每张1-2.5分钟
        ideal_min = num_slides * 1
        ideal_max = num_slides * 2.5

        if ideal_min <= total_minutes <= ideal_max:
            return 1.0
        elif total_minutes < ideal_min:
            return total_minutes / ideal_min
        else:
            return max(0.4, 1 - (total_minutes - ideal_max) / ideal_max)

    def _evaluate_time_distribution(self) -> float:
        """评估时间分布"""
        durations = []
        for p in self.plan:
            duration_str = p.get('duration', '0 minute')
            duration_minutes = self._parse_duration(duration_str)
            if duration_minutes > 0:
                durations.append(duration_minutes)

        if len(durations) < 3:
            return 1.0

        # 检查开头和结尾是否简洁
        intro_ok = durations[0] <= 2
        outro_ok = durations[-1] <= 2

        # 检查中间部分是否充实
        middle_durations = durations[1:-1] if len(durations) > 2 else durations
        middle_ok = all(d >= 1 for d in middle_durations)

        return (float(intro_ok) + float(outro_ok) + float(middle_ok)) / 3

    def _evaluate_pace(self) -> float:
        """评估节奏一致性"""
        durations = []
        for p in self.plan:
            duration_str = p.get('duration', '0 minute')
            duration_minutes = self._parse_duration(duration_str)
            if duration_minutes > 0:
                durations.append(duration_minutes)

        if not durations:
            return 1.0

        # 检查是否有极端值(过长或过短)
        mean = sum(durations) / len(durations)
        extreme_count = sum(1 for d in durations if d > mean * 2 or d < mean * 0.5)

        # 极端值越少越好
        return max(0, 1 - extreme_count / len(durations))

    # ============ 综合评估 ============

    def evaluate_all(self) -> Dict:
        """执行所有评估"""
        print("=" * 70)
        print("正在评估演讲稿质量...")
        print("=" * 70)

        results = {
            'content_consistency': self.evaluate_content_consistency(),
            'structure': self.evaluate_structure(),
            'language_quality': self.evaluate_language_quality(),
            'detail_richness': self.evaluate_detail_richness(),
            'time_management': self.evaluate_time_management()
        }

        # 加权计算总分
        weights = {
            'content_consistency': 0.30,
            'structure': 0.25,
            'language_quality': 0.20,
            'detail_richness': 0.15,
            'time_management': 0.10
        }

        overall_score = sum(
            results[key]['overall_score'] * weights[key]
            for key in weights
        )

        results['overall_score'] = overall_score
        results['grade'] = self._get_grade(overall_score)
        results['weights'] = weights

        return results

    def _get_grade(self, score: float) -> str:
        """根据分数获取等级"""
        if score >= 0.90:
            return 'A+ (优秀)'
        elif score >= 0.85:
            return 'A (优秀)'
        elif score >= 0.80:
            return 'B+ (良好)'
        elif score >= 0.75:
            return 'B (良好)'
        elif score >= 0.70:
            return 'C+ (中等)'
        elif score >= 0.65:
            return 'C (中等)'
        elif score >= 0.60:
            return 'D (及格)'
        else:
            return 'F (不及格)'

    def generate_report(self) -> str:
        """生成详细评估报告"""
        results = self.evaluate_all()

        report = "\n" + "=" * 70 + "\n"
        report += " " * 20 + "演讲稿质量评估报告\n"
        report += " " * 20 + "Speech Quality Evaluation Report\n"
        report += "=" * 70 + "\n\n"

        # 总体评分
        report += f"【总体评分】 {results['overall_score']:.1%}\n"
        report += f"【评级等级】 {results['grade']}\n"
        total_time = self._calculate_total_time()
        report += f"【演讲时长】 {total_time:.1f}分钟 ({int(total_time * 60)}秒)\n"
        report += f"【幻灯片数】 {len(self.plan)}张\n\n"

        # 各维度评分可视化
        report += "-" * 70 + "\n"
        report += "各维度得分总览:\n"
        report += "-" * 70 + "\n"
        for key, weight in results['weights'].items():
            score = results[key]['overall_score']
            bar_length = int(score * 40)
            bar = "█" * bar_length + "░" * (40 - bar_length)
            name_map = {
                'content_consistency': '内容一致性',
                'structure': '结构合理性',
                'language_quality': '语言质量',
                'detail_richness': '细节丰富度',
                'time_management': '时间规划'
            }
            report += f"{name_map[key]:8s} ({weight:.0%}) [{bar}] {score:.1%}\n"

        report += "\n" + "=" * 70 + "\n"
        report += "详细评分分析:\n"
        report += "=" * 70 + "\n\n"

        # 1. 内容一致性
        report += "【1. 内容一致性】 权重: 30%\n"
        report += "-" * 70 + "\n"
        cc = results['content_consistency']
        report += f"  关键词覆盖率:     {cc['keyword_coverage']:.1%}  "
        report += f"{'✓ 优秀' if cc['keyword_coverage'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  概念覆盖率:       {cc['concept_coverage']:.1%}  "
        report += f"{'✓ 优秀' if cc['concept_coverage'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  标题覆盖率:       {cc['slide_title_coverage']:.1%}  "
        report += f"{'✓ 优秀' if cc['slide_title_coverage'] >= 0.8 else '✗ 需改进'}\n"
        report += f"  事实准确性:       {cc['fact_accuracy']:.1%}  "
        report += f"{'✓ 优秀' if cc['fact_accuracy'] >= 0.8 else '✗ 需改进'}\n"
        report += f"  幻觉风险评分:     {cc['hallucination_risk_score']:.1%}  "
        report += f"{'✓ 风险低' if cc['hallucination_risk_score'] <= 0.3 else '⚠ 风险较高'}\n"
        report += f"  综合得分:         {cc['overall_score']:.1%}\n\n"

        # 2. 结构合理性
        report += "【2. 结构合理性】 权重: 25%\n"
        report += "-" * 70 + "\n"
        st = results['structure']
        report += f"  逻辑连贯性:       {st['coherence_score']:.1%}  "
        report += f"{'✓ 优秀' if st['coherence_score'] >= 0.8 else '✗ 需改进'}\n"
        report += f"  时间平衡性:       {st['time_balance_score']:.1%}  "
        report += f"{'✓ 优秀' if st['time_balance_score'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  过渡自然性:       {st['transition_score']:.1%}  "
        report += f"{'✓ 优秀' if st['transition_score'] >= 0.6 else '✗ 需改进'}\n"
        report += f"  组织结构:         {st['organization_score']:.1%}  "
        report += f"{'✓ 优秀' if st['organization_score'] >= 0.8 else '✗ 需改进'}\n"
        report += f"  综合得分:         {st['overall_score']:.1%}\n\n"

        # 3. 语言质量
        report += "【3. 语言质量】 权重: 20%\n"
        report += "-" * 70 + "\n"
        lq = results['language_quality']
        report += f"  表达清晰度:       {lq['clarity_score']:.1%}  "
        report += f"{'✓ 优秀' if lq['clarity_score'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  口语化程度:       {lq['conversational_score']:.1%}  "
        report += f"{'✓ 优秀' if lq['conversational_score'] >= 0.6 else '✗ 需改进'}\n"
        report += f"  词汇丰富度:       {lq['vocabulary_richness']:.1%}  "
        report += f"{'✓ 优秀' if lq['vocabulary_richness'] >= 0.5 else '✗ 需改进'}\n"
        report += f"  专业性:           {lq['professionalism_score']:.1%}  "
        report += f"{'✓ 优秀' if lq['professionalism_score'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  综合得分:         {lq['overall_score']:.1%}\n\n"

        # 4. 细节丰富度
        report += "【4. 细节丰富度】 权重: 15%\n"
        report += "-" * 70 + "\n"
        dr = results['detail_richness']
        report += f"  内容扩展比:       {dr['expansion_ratio_score']:.1%}  "
        report += f"{'✓ 优秀' if dr['expansion_ratio_score'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  例子使用:         {dr['example_usage_score']:.1%}  "
        report += f"{'✓ 优秀' if dr['example_usage_score'] >= 0.5 else '✗ 需改进'}\n"
        report += f"  解释质量:         {dr['explanation_quality']:.1%}  "
        report += f"{'✓ 优秀' if dr['explanation_quality'] >= 0.5 else '✗ 需改进'}\n"
        report += f"  背景信息:         {dr['context_provision']:.1%}  "
        report += f"{'✓ 优秀' if dr['context_provision'] >= 0.6 else '✗ 需改进'}\n"
        report += f"  综合得分:         {dr['overall_score']:.1%}\n\n"

        # 5. 时间规划
        report += "【5. 时间规划】 权重: 10%\n"
        report += "-" * 70 + "\n"
        tm = results['time_management']
        total_mins = tm['total_minutes']
        total_secs = int(total_mins * 60)
        report += f"  总时长:           {total_mins:.1f} 分钟 ({total_secs}秒)  "
        report += f"{'✓ 合理' if 10 <= total_mins <= 30 else '⚠ 注意'}\n"
        report += f"  时长合理性:       {tm['duration_appropriateness']:.1%}  "
        report += f"{'✓ 优秀' if tm['duration_appropriateness'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  时间分布:         {tm['time_distribution_score']:.1%}  "
        report += f"{'✓ 优秀' if tm['time_distribution_score'] >= 0.6 else '✗ 需改进'}\n"
        report += f"  节奏一致性:       {tm['pace_consistency']:.1%}  "
        report += f"{'✓ 优秀' if tm['pace_consistency'] >= 0.7 else '✗ 需改进'}\n"
        report += f"  综合得分:         {tm['overall_score']:.1%}\n\n"

        # 改进建议
        report += "=" * 70 + "\n"
        report += "改进建议:\n"
        report += "=" * 70 + "\n"
        suggestions = self._generate_suggestions(results)
        report += suggestions + "\n"

        # 优点总结
        report += "=" * 70 + "\n"
        report += "优点总结:\n"
        report += "=" * 70 + "\n"
        strengths = self._generate_strengths(results)
        report += strengths + "\n"

        report += "=" * 70 + "\n"
        report += "评估完成!\n"
        report += "=" * 70 + "\n"

        return report

    def _generate_suggestions(self, results: Dict) -> str:
        """生成改进建议"""
        suggestions = []

        cc = results['content_consistency']
        st = results['structure']
        lq = results['language_quality']
        dr = results['detail_richness']
        tm = results['time_management']

        # 按优先级排序
        priority_issues = []

        # 内容一致性问题（最高优先级）
        if cc['keyword_coverage'] < 0.6:
            priority_issues.append(
                " [高优先级] 关键词覆盖不足 - 确保幻灯片中的重要概念都在演讲稿中体现"
            )
        if cc['slide_title_coverage'] < 0.7:
            priority_issues.append(
                " [高优先级] 幻灯片标题覆盖不完整 - 每张幻灯片的主题都应在演讲中明确提及"
            )
        if cc['hallucination_risk_score'] > 0.4:
            priority_issues.append(
                " [高优先级] 幻觉风险较高 - 减少幻灯片中未出现的额外内容，保持一致性"
            )
        if cc['fact_accuracy'] < 0.7:
            priority_issues.append(
                " [高优先级] 事实准确性不足 - 确保幻灯片中的数字、人名等关键事实被准确传达"
            )

        # 结构问题（高优先级）
        if st['coherence_score'] < 0.7:
            priority_issues.append(
                " [中优先级] 逻辑连贯性有待提升 - 确保演讲内容按照幻灯片顺序展开"
            )
        if st['transition_score'] < 0.5:
            priority_issues.append(
                " [中优先级] 缺少过渡语句 - 在段落间添加'接下来'、'让我们看看'等过渡词"
            )
        if st['time_balance_score'] < 0.6:
            priority_issues.append(
                " [中优先级] 时间分配不均衡 - 调整各部分时长，避免某些部分过长或过短"
            )

        # 语言质量问题（中优先级）
        if lq['conversational_score'] < 0.5:
            priority_issues.append(
                " [中低优先级] 口语化程度不足 - 使用更多'我们'、'让我们'等口语化表达"
            )
        if lq['clarity_score'] < 0.6:
            priority_issues.append(
                " [中低优先级] 句子长度需优化 - 调整句子长度，建议12-25词为宜"
            )
        if lq['professionalism_score'] < 0.6:
            priority_issues.append(
                " [中低优先级] 专业性不足 - 适当使用幻灯片中的专业术语和概念"
            )

        # 细节问题（较低优先级）
        if dr['example_usage_score'] < 0.4:
            priority_issues.append(
                " [低优先级] 缺少具体例子 - 为抽象概念添加具体案例说明"
            )
        if dr['explanation_quality'] < 0.4:
            priority_issues.append(
                " [低优先级] 解释不够充分 - 为技术术语和复杂概念提供更多解释"
            )
        if dr['expansion_ratio_score'] < 0.5:
            priority_issues.append(
                " [低优先级] 内容扩展不足 - 适当增加细节描述，丰富演讲内容"
            )

        # 时间问题
        if tm['duration_appropriateness'] < 0.6:
            total_mins = tm['total_minutes']
            total_secs = int(total_mins * 60)
            priority_issues.append(
                f"🟡 [中低优先级] 总时长需调整 - 当前{total_mins:.1f}分钟({total_secs}秒)，建议调整以匹配场合需求"
            )

        if priority_issues:
            suggestions = priority_issues
        else:
            suggestions = [" 整体质量优秀，各项指标均达标，继续保持！"]

        # 添加通用建议
        if results['overall_score'] < 0.7:
            suggestions.append("\n 总体建议: 重点关注内容一致性和结构合理性，这是演讲稿的基础")
        elif results['overall_score'] < 0.85:
            suggestions.append("\n 总体建议: 在保持现有质量的基础上，可进一步优化语言表达和细节丰富度")

        return '\n'.join(f"  {i+1}. {s}" for i, s in enumerate(suggestions))


    def _generate_strengths(self, results: Dict) -> str:
        """生成优点总结"""
        strengths = []

        cc = results['content_consistency']
        st = results['structure']
        lq = results['language_quality']
        dr = results['detail_richness']
        tm = results['time_management']

        if cc['keyword_coverage'] >= 0.75:
            strengths.append("✓ 关键词覆盖全面，准确传达了幻灯片核心内容")
        if cc['fact_accuracy'] >= 0.8:
            strengths.append("✓ 事实数据准确，保持了良好的信息一致性")
        if cc['hallucination_risk_score'] <= 0.25:
            strengths.append("✓ 内容忠实于原材料，幻觉风险控制良好")

        if st['coherence_score'] >= 0.8:
            strengths.append("✓ 逻辑结构清晰，演讲流程合理")
        if st['transition_score'] >= 0.65:
            strengths.append("✓ 段落过渡自然，听众体验流畅")
        if st['organization_score'] >= 0.8:
            strengths.append("✓ 整体组织结构完整，有明确的引入和总结")

        if lq['conversational_score'] >= 0.6:
            strengths.append("✓ 口语化表达自然，适合现场演讲")
        if lq['clarity_score'] >= 0.75:
            strengths.append("✓ 表达清晰易懂，句子长度适中")
        if lq['professionalism_score'] >= 0.7:
            strengths.append("✓ 专业性强，恰当使用了学术术语")

        if dr['example_usage_score'] >= 0.5:
            strengths.append("✓ 合理使用例子，帮助听众理解")
        if dr['explanation_quality'] >= 0.5:
            strengths.append("✓ 解释充分，技术概念阐述清楚")
        if dr['context_provision'] >= 0.65:
            strengths.append("✓ 提供了充足的背景信息")

        if tm['duration_appropriateness'] >= 0.75:
            strengths.append("✓ 时长规划合理，符合演讲场合要求")
        if tm['time_distribution_score'] >= 0.7:
            strengths.append("✓ 时间分配得当，重点突出")

        if not strengths:
            strengths = ["继续努力，提升各项指标"]

        return '\n'.join(f"  • {s}" for s in strengths)


# ============ 使用示例 ============

def evaluate_from_files(pdf_text: str, speech_json_path: str):
    """
    从PDF文本和演讲稿JSON文件进行评估

    Args:
        pdf_text: 从PDF提取的文本内容
        speech_json_path: 演讲稿JSON文件路径
    """
    # 读取演讲稿JSON
    with open(speech_json_path, 'r', encoding='utf-8') as f:
        speech_json = f.read()

    # 创建评估器
    evaluator = SpeechEvaluator(pdf_text, speech_json)

    # 生成并打印报告
    report = evaluator.generate_report()
    print(report)

    # 保存报告
    with open('evaluation_report_'+speech_json_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print("\n 报告已保存到: evaluation_report_"+speech_json_path)

    # 返回评估结果供进一步分析
    return evaluator.evaluate_all()


if __name__ == "__main__":
    evaluate_from_files('presentation.pdf', 'speech_qwen_vl.txt')