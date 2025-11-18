import openai
import time
import base64
from pathlib import Path
from typing import List, Union
from io import BytesIO

# PDF处理
from pdf2image import convert_from_path
from PIL import Image


class QwenVLPlus:
    def __init__(self, api_key):
        self.model = "qwen-vl-plus"
        self.llm = openai.OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

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
            rsp = self.llm.chat.completions.create(**self._cons_kwargs(messages), extra_body=extra_body, response_format=response_format)
        except openai.RateLimitError as e: 
            print("OpenAI API request exceeded rate limit")
            time.sleep(60)
            rsp = self.llm.chat.completions.create(**self._cons_kwargs(messages), extra_body=extra_body, response_format=response_format)
        except openai.APITimeoutError as e:
            print("OpenAI API request timed out")
            time.sleep(60)
            rsp = self.llm.chat.completions.create(**self._cons_kwargs(messages), extra_body=extra_body, response_format=response_format)

        return rsp.choices[0].message.content


class SlideToSpeechGenerator:
    """将PDF或PPTX幻灯片文件转换为演讲稿的生成器"""
    def __init__(self, api_key: str):
        """
        初始化生成器
        
        Args:
            api_key: Qwen API密钥
        """
        self.qwen = QwenVLPlus(api_key)
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        将PIL Image对象转换为base64字符串
        Args:
            image: PIL Image对象
        Returns:
            base64编码的图片字符串
        """
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def _extract_slides_from_pdf(self, pdf_path: str, dpi: int = 150) -> List[Image.Image]:
        """
        从PDF文件提取所有幻灯片为图片
        Args:
            pdf_path: PDF文件路径
            dpi: 图片分辨率，默认150
        Returns:
            PIL Image对象列表
        """
        print(f"正在从PDF提取幻灯片...")
        images = convert_from_path(pdf_path, dpi=dpi,poppler_path=r'C:\Users\czrch\poppler\poppler-23.11.0\Library\bin')
        print(f"成功提取 {len(images)} 张幻灯片")
        return images

    
    def _create_image_message(self, image: Image.Image, prompt: str) -> List[dict]:
        """
        创建包含图片的消息
        
        Args:
            image: PIL Image对象
            prompt: 文本提示
            
        Returns:
            格式化的消息列表
        """
        base64_image = self._image_to_base64(image)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        return messages
    
    def _generate_speech_for_image_slide(
        self, 
        image: Image.Image, 
        slide_number: int, 
        total_slides: int
    ) -> str:
        """
        为单张幻灯片图片生成演讲稿
        Args:
            image: 幻灯片图片
            slide_number: 当前幻灯片编号
            total_slides: 总幻灯片数
        Returns:
            生成的演讲稿
        """
        is_first = (slide_number == 1)
        is_last = (slide_number == total_slides)
        
        prompt = f"""请基于这张幻灯片（第{slide_number}/{total_slides}张）生成一段演讲稿。
要求：
1. 语言自然流畅，适合口头表达
2. 突出幻灯片的核心信息和关键要点
3. {'这是开场幻灯片，需要有吸引人的开场白' if is_first else ''}
4. {'这是最后一张幻灯片，需要有总结和结束语' if is_last else ''}
5. 适当添加过渡语句，使演讲连贯
6. 控制在200-400字左右
7. 用生动的语言解释幻灯片上的数据、图表等内容

请直接输出演讲稿内容，不要添加额外的说明。"""
        
        messages = self._create_image_message(image, prompt)
        speech = self.qwen.completion(messages)
        return speech

    
    # def generate_speech_from_file(
    #     self,
    #     file_path: str,
    #     output_path: str = None,
    #     dpi: int = 150,
    #     add_transitions: bool = True
    # ) -> str:
    #     """
    #     从PDF或PPTX文件生成完整演讲稿
    #     Args:
    #         file_path: PDF或PPTX文件路径
    #         output_path: 输出文件路径（可选）
    #         dpi: PDF转图片的分辨率，默认150
    #         add_transitions: 是否优化演讲稿的连贯性
    #     Returns:
    #         完整的演讲稿
    #     """
    #     file_path = Path(file_path)
    #
    #     if not file_path.exists():
    #         raise FileNotFoundError(f"文件不存在: {file_path}")
    #
    #     # 根据文件类型提取幻灯片
    #     if file_path.suffix.lower() == '.pdf':
    #         images = self._extract_slides_from_pdf(str(file_path), dpi)
    #     else:
    #         raise ValueError(f"不支持的文件格式: {file_path.suffix}")
    #
    #     # 为每张幻灯片生成演讲稿
    #     print(f"\n开始生成演讲稿...")
    #     speeches = []
    #     total_slides = len(images)
    #
    #     for i, image in enumerate(images, 1):
    #         print(f"正在处理第 {i}/{total_slides} 张幻灯片...")
    #
    #         speech = self._generate_speech_for_image_slide(image, i, total_slides)
    #         speeches.append(f"【幻灯片 {i}】\n{speech}")
    #
    #         # 添加短暂延迟，避免API限流
    #         if i < total_slides:
    #             time.sleep(1)
    #
    #     # 合并所有演讲稿
    #     full_speech = "\n\n".join(speeches)
    #
    #     # 优化整体连贯性
    #     if add_transitions and len(images) > 1:
    #         print("\n正在优化演讲稿的整体连贯性...")
    #         full_speech = self._polish_speech(full_speech)
    #
    #     # 保存到文件
    #     if output_path:
    #         with open(output_path, 'w', encoding='utf-8') as f:
    #             f.write(full_speech)
    #         print(f"\n✅ 演讲稿已保存到: {output_path}")
    #
    #     return full_speech
    
    def _polish_speech(self, draft_speech: str) -> str:
        """
        优化演讲稿的整体连贯性和流畅度
        Args:
            draft_speech: 初稿演讲稿
        Returns:
            优化后的演讲稿
        """
        messages = [
            {
                "role": "user",
                "content": f"""以下是基于多张幻灯片生成的演讲稿初稿，请帮我优化：

                {draft_speech}

                优化要求：
                1. 保持每部分的核心内容不变
                2. 优化幻灯片之间的过渡，使演讲更连贯自然
                3. 统一语言风格和表达方式
                4. 确保开场和结尾更有感染力
                5. 保留【幻灯片 X】的标记
                6. 让整体演讲更有逻辑性和说服力

                请直接输出优化后的完整演讲稿。"""
            }
        ]
        
        polished = self.qwen.completion(messages)
        return polished

    def _generate_speech_batch(self, images: List[Image.Image]) -> str:
            """
            批量处理所有幻灯片，一次性生成完整演讲稿

            Args:
                images: 所有幻灯片图片列表

            Returns:
                完整的演讲稿
            """
            print(f"正在批量处理 {len(images)} 张幻灯片...")

            # 构建包含所有幻灯片的消息
            content = [
                {
                    "type": "text",
                    "text": f"""你是一个专业的演讲机器人，你的名字叫pepper。现在给你现在给你{len(images)}张演讲幻灯片，请你完成两件事：
(1)先为这些幻灯片设计一个完整的英文演讲规划：说明这些幻灯片的演讲结构（比如：引入-解释概念-举例-小结等等），每一页大概讲几句话、持续多长时间。
(2)根据上面的演讲规划，生成一段适合口语表达的英文演讲稿，语气自然、有条理，面向研究生和老师的学术场景。
完整要求如下：
(1)注意细节丰富度，不要简单朗读 PPT 原文，要有扩展和解释。
(2)注意内容一致性，生成的演讲稿内容需要与每一页幻灯片一一对应，并与每一页幻灯片的内容保持同步和一致。
(3)保持专业但不要太书面，注意口语化、逻辑严谨性和流畅性，多用自然的表达，注意开头能够吸引人、结尾有收束和总结。
(4)输出格式用JSON，字段包括：
a. 演讲规划的分点列表:
plan: slide,title,duration('xx seconds'),content
b.每一页slide对应的演讲稿文本内容的分点列表:script:slide,text"""
                }
            ]

            # 添加所有幻灯片图片
            for i, image in enumerate(images, 1):
                base64_image = self._image_to_base64(image)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                })

            messages = [{"role": "user", "content": content}]

            # 生成演讲稿
            speech = self.qwen.completion(messages)
            return speech

    def generate_speech_from_file(
            self,
            file_path: str,
            output_path: str = None,
            dpi: int = 150,
            batch_mode: bool = True
    ) -> str:
        """
            从PDF或PPTX文件生成完整演讲稿

            Args:
                file_path: PDF或PPTX文件路径
                output_path: 输出文件路径（可选）
                dpi: PDF转图片的分辨率，默认150
                batch_mode: 是否批量处理（推荐True，一次性处理所有幻灯片）

            Returns:
                完整的演讲稿
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

            # 根据文件类型提取幻灯片
        if file_path.suffix.lower() == '.pdf':
            images = self._extract_slides_from_pdf(str(file_path), dpi)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

        # 生成演讲稿
        print(f"\n开始生成演讲稿...")
        if batch_mode:
            # 批量模式：一次性处理所有幻灯片（推荐）
            print("使用批量模式：一次性处理所有幻灯片...")
            full_speech = self._generate_speech_batch(images)
        else:
            # 逐页模式：分别处理每张幻灯片
            print("使用逐页模式：分别处理每张幻灯片...")
            speeches = []
            total_slides = len(images)

            for i, image in enumerate(images, 1):
                print(f"正在处理第 {i}/{total_slides} 张幻灯片...")
                speech = self._generate_speech_for_image_slide(image, i, total_slides)
                speeches.append(f"【幻灯片 {i}】\n{speech}")
                # 添加短暂延迟，避免API限流
                if i < total_slides:
                    time.sleep(1)
                # 合并所有演讲稿
            full_speech = "\n\n".join(speeches)

                # 优化整体连贯性
            print("\n正在优化演讲稿的整体连贯性...")
            full_speech = self._polish_speech(full_speech)

            # 保存到文件
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_speech)
            print(f"\n演讲稿已保存到: {output_path}")

        return full_speech


def main():
    # 设置API密钥
    API_KEY = "sk-8faa7214041347609e67d5d09cec7266"
    # 创建生成器
    generator = SlideToSpeechGenerator(API_KEY)
    
    # 示例1: 从PDF生成演讲稿
    print("=" * 60)
    print("从PDF文件生成演讲稿")
    print("=" * 60)
    
    try:
        speech = generator.generate_speech_from_file(
            file_path="presentation.pdf",
            output_path="speech_qwen_vl.txt",
            dpi=150,  # 调整图片质量
            batch_mode = True
        )
        print("\n生成的演讲稿预览：")
        print(speech[:500] + "..." if len(speech) > 500 else speech)
    except FileNotFoundError:
        print("示例PDF文件不存在，请提供实际文件路径")



if __name__ == "__main__":
    main()