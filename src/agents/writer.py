import re
import threading
import time
import copy
from tqdm import tqdm
from custom_nodes.ComfyUI_Autosurvey.src.database.database import Database
from ComfyUI_Autosurvey.src.core.model import APIModel
from ComfyUI_Autosurvey.src.utils.utils import tokenCounter
from ComfyUI_Autosurvey.src.config.prompt_zh import (
    SUBSECTION_WRITING_PROMPT,
    LCE_PROMPT,
    CHECK_CITATION_PROMPT,
)
import folder_paths


class subsectionWriter:
    def __init__(
        self, model:APIModel, database: Database
    ) -> None:
        self.api_model = model
        self.db = database
        self.token_counter = tokenCounter()
        self.input_token_usage, self.output_token_usage = 0, 0

    def write(
        self,
        topic,
        outline,
        rag_num=30,
        subsection_len=500,
        refining=True,
        reflection=True,
    ):
        # Get database
        # 解析大纲
        parsed_outline = self.parse_outline(outline=outline)
        print(parsed_outline)
        # 初始化每个章节的内容
        section_content = [[]] * len(parsed_outline["sections"])

        # 初始化每个章节的参考文献
        section_paper_texts = [[]] * len(parsed_outline["sections"])

        # 初始化所有参考文献的ID
        total_ids = []
        # 初始化每个章节的参考文献ID
        section_references_ids = [[]] * len(parsed_outline["sections"])
        # 遍历每个章节
        for i in range(len(parsed_outline["sections"])):
            # 获取每个章节的子章节描述
            descriptions = parsed_outline["subsection_descriptions"][i]
            # 遍历每个子章节描述
            for d in descriptions:
                # 从数据库中获取与子章节描述相关的参考文献ID
                references_ids = self.db.get_ids_from_query(
                    d, num=rag_num, shuffle=False
                )
                # 将参考文献ID添加到总参考文献ID中
                total_ids += references_ids
                # 将参考文献ID添加到每个章节的参考文献ID中
                section_references_ids[i].append(references_ids)
        # 从数据库中获取所有参考文献的信息
        total_references_infos = self.db.get_paper_info_from_ids(list(set(total_ids)))
        # print(total_references_infos)

        # 将参考文献信息中的ID作为键，标题作为值，构建字典
        temp_title_dic = {
            id: p["title"] for id, p in zip(set(total_ids), total_references_infos)
        }
        # 将参考文献信息中的ID作为键，摘要作为值，构建字典
        temp_abs_dic = {
            id: p["content"] for id, p in zip(set(total_ids), total_references_infos)
        }

        # 遍历每个章节
        for i in range(len(parsed_outline["sections"])):
            # 遍历每个章节的参考文献ID
            for references_ids in section_references_ids[i]:

                # 获取参考文献的标题
                references_titles = [temp_title_dic[_] for _ in references_ids]
                # 获取参考文献的摘要
                references_papers = [temp_abs_dic[_] for _ in references_ids]
                # 初始化参考文献的文本
                paper_texts = ""
                # 遍历每个参考文献的标题和摘要
                for t, p in zip(references_titles, references_papers):
                    # 将标题和摘要添加到参考文献的文本中
                    paper_texts += f"---\n\npaper_title: {t}\n\npaper_content:\n\n{p}\n"
                # 添加参考文献的文本
                paper_texts += "---\n"

                # 将参考文献的文本添加到每个章节的参考文献文本中
                section_paper_texts[i].append(paper_texts)

        # 初始化线程列表
        thread_l = []
        # 遍历每个章节
        for i in range(len(parsed_outline["sections"])):
            # print(section_paper_texts[i])
            # print(parsed_outline['sections'][i])
            # print(parsed_outline['subsections'][i])
            # print(parsed_outline['subsection_descriptions'][i])
            # 创建线程，目标函数为write_subsection_with_reflection，参数为section_paper_texts[i]，topic，outline，parsed_outline['sections'][i]，parsed_outline['subsections'][i]，parsed_outline['subsection_descriptions'][i]，section_content，i，rag_num,str(subsection_len)
            thread = threading.Thread(
                target=self.write_subsection_with_reflection,
                args=(
                    section_paper_texts[i],
                    topic,
                    outline,
                    parsed_outline["sections"][i],
                    parsed_outline["subsections"][i],
                    parsed_outline["subsection_descriptions"][i],
                    section_content,
                    i,
                    rag_num,
                    str(subsection_len),
                ),
            )
            # 将线程添加到线程列表中
            thread_l.append(thread)
            # 启动线程
            thread.start()
            # 休眠0.1秒
            time.sleep(0.1)
        # 等待所有线程结束
        for thread in thread_l:
            thread.join()
        # 生成文档
        raw_survey = self.generate_document(parsed_outline, section_content)
        with open(f"{folder_paths.get_output_directory()}/raw_survey.md", "w") as f:
            f.write(raw_survey)
        # 处理参考文献
        raw_survey_with_references, raw_references = self.process_references(raw_survey)
        # 如果需要精炼
        if refining:
            # 精炼子章节
            final_section_content = self.refine_subsections(
                topic, outline, section_content
            )
            # 生成精炼后的文档
            refined_survey = self.generate_document(
                parsed_outline, final_section_content
            )
            # 处理精炼后的参考文献
            refined_survey_with_references, refined_references = (
                self.process_references(refined_survey)
            )
            with open(f"{folder_paths.get_output_directory()}/refined_survey.md", "w") as f:
                f.write(refined_survey_with_references)
            return refined_survey_with_references
        else:
            # 返回原始文档，原始文档带参考文献，原始参考文献
            return (
                raw_survey + "\n",
                raw_survey_with_references + "\n",
                raw_references,
            )  # , mindmap

    def compute_price(self):
        return self.token_counter.compute_price(
            input_tokens=self.input_token_usage,
            output_tokens=self.output_token_usage,
            model=self.model,
        )

    def refine_subsections(self, topic, outline, section_content):
        section_content_even = copy.deepcopy(section_content)

        thread_l = []
        for i in range(len(section_content)):
            for j in range(len(section_content[i])):
                if j % 2 == 0:
                    if j == 0:
                        contents = [""] + section_content[i][:2]
                    elif j == (len(section_content[i]) - 1):
                        contents = section_content[i][-2:] + [""]
                    else:
                        contents = section_content[i][j - 1 : j + 2]
                    thread = threading.Thread(
                        target=self.lce,
                        args=(topic, outline, contents, section_content_even[i], j),
                    )
                    thread_l.append(thread)
                    thread.start()
        for thread in thread_l:
            thread.join()

        final_section_content = copy.deepcopy(section_content_even)

        thread_l = []
        for i in range(len(section_content_even)):
            for j in range(len(section_content_even[i])):
                if j % 2 == 1:
                    if j == (len(section_content_even[i]) - 1):
                        contents = section_content_even[i][-2:] + [""]
                    else:
                        contents = section_content_even[i][j - 1 : j + 2]
                    thread = threading.Thread(
                        target=self.lce,
                        args=(topic, outline, contents, final_section_content[i], j),
                    )
                    thread_l.append(thread)
                    thread.start()
        for thread in thread_l:
            thread.join()

        return final_section_content

    def write_subsection_with_reflection(
        self,
        paper_texts_l,
        topic,
        outline,
        section,
        subsections,
        subdescriptions,
        res_l,
        idx,
        rag_num=20,
        subsection_len=1000,
        citation_num=8,
    ):

        prompts = []
        for j in range(len(subsections)):
            subsection = subsections[j]
            description = subdescriptions[j]

            prompt = self.__generate_prompt(
                SUBSECTION_WRITING_PROMPT,
                paras={
                    "OVERALL OUTLINE": outline,
                    "SUBSECTION NAME": subsection,
                    "DESCRIPTION": description,
                    "TOPIC": topic,
                    "PAPER LIST": paper_texts_l[j],
                    "SECTION NAME": section,
                    "WORD NUM": str(subsection_len),
                    "CITATION NUM": str(citation_num),
                },
            )
            prompts.append(prompt)

        self.input_token_usage += self.token_counter.num_tokens_from_list_string(
            prompts
        )
        contents = self.api_model.batch_chat(prompts, temperature=1)
        self.output_token_usage += self.token_counter.num_tokens_from_list_string(
            contents
        )
        contents = [
            c.replace("<format>", "").replace("</format>", "") for c in contents
        ]

        prompts = []
        for content, paper_texts in zip(contents, paper_texts_l):
            prompts.append(
                self.__generate_prompt(
                    CHECK_CITATION_PROMPT,
                    paras={
                        "SUBSECTION": content,
                        "TOPIC": topic,
                        "PAPER LIST": paper_texts,
                    },
                )
            )
        self.input_token_usage += self.token_counter.num_tokens_from_list_string(
            prompts
        )
        contents = self.api_model.batch_chat(prompts, temperature=1)
        self.output_token_usage += self.token_counter.num_tokens_from_list_string(
            contents
        )
        contents = [
            c.replace("<format>", "").replace("</format>", "") for c in contents
        ]

        res_l[idx] = contents
        return contents

    def __generate_prompt(self, template, paras):
        prompt = template
        for k in paras.keys():
            prompt = prompt.replace(f"[{k}]", paras[k])
        return prompt

    def generate_prompt(self, template, paras):
        prompt = template
        for k in paras.keys():
            prompt = prompt.replace(f"[{k}]", paras[k])
        return prompt

    def lce(self, topic, outline, contents, res_l, idx):
        """
        You are an expert in artificial intelligence who wants to write a overall and comprehensive survey about [TOPIC].\n\
        You have created a overall outline below:\n\
        ---
        [OVERALL OUTLINE]
        ---
        <instruction>

        Now you need to help to refine one of the subsection to improve th ecoherence of your survey.

        You are provied with the content of the subsection "[SUBSECTION NAME]" along with the previous subsections and following subsections.

        Previous Subsection:
        --- 
        [PREVIOUS]
        ---

        Subsection to Refine: 
        ---
        [SUBSECTION]
        ---

        Following Subsection:
        ---
        [FOLLOWING]
        ---

        If the content of Previous Subsection is empty, it means that the subsection to refine is the first subsection.
        If the content of Following Subsection is empty, it means that the subsection to refine is the last subsection.

        Now edit the middle subsection to enhance coherence, remove redundancies, and ensure that it connects more fluidly with the previous and following subsections. 
        Please keep the essence and core information of the subsection intact. 
        </instruction>

        Directly return the refined subsection without any other informations:
        """

        prompt = self.__generate_prompt(
            LCE_PROMPT,
            paras={
                "OVERALL OUTLINE": outline,
                "PREVIOUS": contents[0],
                "FOLLOWING": contents[2],
                "TOPIC": topic,
                "SUBSECTION": contents[1],
            },
        )
        self.input_token_usage += self.token_counter.num_tokens_from_string(prompt)
        refined_content = (
            self.api_model.chat(prompt, temperature=1)
            .replace("<format>", "")
            .replace("</format>", "")
        )
        self.output_token_usage += self.token_counter.num_tokens_from_string(
            refined_content
        )
        #   print(prompt+'\n---------------------------------\n'+refined_content)
        res_l[idx] = refined_content
        return refined_content.replace("Here is the refined subsection:\n", "")

    def parse_outline(self, outline):
        result = {
            "title": "",
            "sections": [],
            "section_descriptions": [],
            "subsections": [],
            "subsection_descriptions": [],
        }

        # Split the outline into lines
        lines = outline.split("\n")

        for i, line in enumerate(lines):
            # Match title, sections, subsections and their descriptions
            if line.startswith("# "):
                result["title"] = line[2:].strip()
            elif line.startswith("## "):
                result["sections"].append(line[3:].strip())
                # Extract the description in the next line
                if i + 1 < len(lines) and lines[i + 1].startswith("Description:"):
                    result["section_descriptions"].append(
                        lines[i + 1].split("Description:", 1)[1].strip()
                    )
                    result["subsections"].append([])
                    result["subsection_descriptions"].append([])
            elif line.startswith("### "):
                if result["subsections"]:
                    result["subsections"][-1].append(line[4:].strip())
                    # Extract the description in the next line
                    if i + 1 < len(lines) and lines[i + 1].startswith("Description:"):
                        result["subsection_descriptions"][-1].append(
                            lines[i + 1].split("Description:", 1)[1].strip()
                        )

        return result

    def parse_survey(self, survey, outline):
        subsections, subdescriptions = [], []
        for i in range(100):
            if f"Subsection {i+1}" in outline:
                subsections.append(
                    outline.split(f"Subsection {i+1}: ")[1].split("\n")[0]
                )
                subdescriptions.append(
                    outline.split(f"Description {i+1}: ")[1].split("\n")[0]
                )
        return subsections, subdescriptions

    def process_references(self, survey):

        citations = self.extract_citations(survey)

        return self.replace_citations_with_numbers(citations, survey)

    def generate_document(self, parsed_outline, subsection_contents):
        document = []

        # Append title
        title = parsed_outline["title"]
        document.append(f"# {title}\n")

        # Iterate over sections and their content
        for i, section in enumerate(parsed_outline["sections"]):
            document.append(f"## {section}\n")
            # Append subsections and their contents
            for j, subsection in enumerate(parsed_outline["subsections"][i]):
                document.append(f"### {subsection}\n")
                #      document.append(f"{parsed_outline['subsection_descriptions'][i][j]}\n")
                # Append detailed content for each subsection
                if i < len(subsection_contents) and j < len(subsection_contents[i]):
                    document.append(subsection_contents[i][j] + "\n")

        return "\n".join(document)

    def process_outlines(self, section_outline, sub_outlines):
        res = ""
        survey_title, survey_sections, survey_section_descriptions = (
            self.extract_title_sections_descriptions(outline=section_outline)
        )
        res += f"# {survey_title}\n\n"
        for i in range(len(survey_sections)):
            section = survey_sections[i]
            res += (
                f"## {i+1} {section}\nDescription: {survey_section_descriptions[i]}\n\n"
            )
            subsections, subsection_descriptions = (
                self.extract_subsections_subdescriptions(sub_outlines[i])
            )
            for j in range(len(subsections)):
                subsection = subsections[j]
                res += f"### {i+1}.{j+1} {subsection}\nDescription: {subsection_descriptions[j]}\n\n"
        return res

    def generate_mindmap(self, subsection_citations, outline):
        to_remove = outline.split("\n")
        for _ in to_remove:
            if not "#" in _:
                outline = outline.replace(_, "")
        subsections = re.findall(pattern=r"### (.*?)\n", string=outline)
        for subs, _ in zip(subsections, range(len(subsections))):
            outline = outline.replace(subs, subs + "\n" + str(subsection_citations[_]))
        to_remove = re.findall(pattern=r"\](.*?)#", string=outline)
        for _ in to_remove:
            outline = outline.replace(_, "")
        return outline

    def extract_citations(self, markdown_text):
        # 正则表达式匹配方括号内的内容
        pattern = re.compile(r"\[(.*?)\]")
        matches = pattern.findall(markdown_text)
        # 分割引用，处理多引用情况，并去重
        citations = list()
        for match in matches:
            # 分割各个引用并去除空格
            parts = match.split(";")
            for part in parts:
                cit = part.strip()
                if cit not in citations:
                    citations.append(cit)
        return citations

    def replace_citations_with_numbers(self, citations, markdown_text):

        ids = self.db.get_titles_from_citations(citations)

        citation_to_ids = {citation: idx for citation, idx in zip(citations, ids)}

        paper_infos = self.db.get_paper_info_from_ids(ids)
        temp_dic = {id: p["title"] for id, p in zip(ids, paper_infos)}

        titles = [temp_dic[_] for _ in tqdm(ids)]

        ids_to_titles = {idx: title for idx, title in zip(ids, titles)}
        titles_to_ids = {title: idx for idx, title in ids_to_titles.items()}

        title_to_number = {title: num + 1 for num, title in enumerate(titles)}

        title_to_number = {
            title: num + 1 for num, title in enumerate(title_to_number.keys())
        }

        number_to_title = {num: title for title, num in title_to_number.items()}
        number_to_title_sorted = {
            key: number_to_title[key] for key in sorted(number_to_title)
        }

        def replace_match(match):

            citation_text = match.group(1)

            individual_citations = citation_text.split(";")

            numbered_citations = [
                str(title_to_number[ids_to_titles[citation_to_ids[citation.strip()]]])
                for citation in individual_citations
            ]

            return "[" + "; ".join(numbered_citations) + "]"

        updated_text = re.sub(r"\[(.*?)\]", replace_match, markdown_text)

        references_section = "\n\n## References\n\n"

        references = {
            num: titles_to_ids[title] for num, title in number_to_title_sorted.items()
        }
        for idx, title in number_to_title_sorted.items():
            t = title.replace("\n", "")
            references_section += f"[{idx}] {t}\n\n"

        return updated_text + references_section, references
