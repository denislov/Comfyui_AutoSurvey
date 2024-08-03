from .database.database import Database
from .core.model import APIModel
from .agents.outline_writer import outlineWriter
from .agents.writer import subsectionWriter
import logging

def remove_descriptions(text):
    lines = text.split("\n")
    filtered_lines = [
        line for line in lines if not line.strip().startswith("Description")
    ]
    result = "\n".join(filtered_lines)
    return result


class AutoSurvey:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "topic": (
                    "STRING",
                    {
                        "placeholder": "Enter your tpoic here...",
                    },
                ),
                "outline_reference_num": ("INT", {"default": 20}),
                "section_num": ("INT", {"default": 3}),
                "rag_num": ("INT", {"default": 10}),
                "subsection_len": ("INT", {"default": 700}),
            }
        }

    RETURN_TYPES = ("AUTOSURVEY",)
    RETURN_NAMES = ("Auto Survey",)
    FUNCTION = "autosurvey"

    CATEGORY = "Senser/autosurvey"

    def autosurvey(
        self, topic, outline_reference_num, section_num,rag_num,subsection_len
    ):
        self.topic = topic
        self.rag_num = rag_num
        self.outline_reference_num = outline_reference_num
        self.subsection_len = subsection_len
        self.section_num = section_num
        instance = self
        return (instance,)


class WriteOutline:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "autosurvey": ("AUTOSURVEY",),
                "chatmodel": ("CHATMODEL",),
                "database": ("DB_CLIENT",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Outline",)
    FUNCTION = "write_outline"

    CATEGORY = "Senser/autosurvey"

    def write_outline(
        self, autosurvey: AutoSurvey, chatmodel: APIModel, database: Database
    ):
        outline_writer = outlineWriter(model=chatmodel, database=database)
        test_txt = chatmodel.chat("hello")
        logging.info(test_txt)
        final_outline = outline_writer.draft_outline(
            autosurvey.topic,
            autosurvey.outline_reference_num,
            autosurvey.section_num,
        )
        return (final_outline,)


class WriteSection:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "outline": (
                    "STRING",
                    {
                        "multiline": True,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "hello",
                    },
                ),
                "autosurvey": ("AUTOSURVEY",),
                "chatmodel": ("CHATMODEL",),
                "database": ("DB_CLIENT",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "write_section"

    CATEGORY = "Senser/autosurvey"

    def write_section(
        self,
        outline,
        autosurvey:AutoSurvey,
        chatmodel: APIModel,
        database: Database,
        refinement=True,
    ):
        subsection_writer = subsectionWriter(
            model=chatmodel, database=database
        )
        if refinement:
            return (subsection_writer.write(
                autosurvey.topic,
                outline,
                subsection_len=autosurvey.subsection_len,
                rag_num=autosurvey.rag_num,
                refining=True,
            ),)
        else:
            return (subsection_writer.write(
                autosurvey.topic,
                outline,
                subsection_len=autosurvey.subsection_len,
                rag_num=autosurvey.rag_num,
                refining=False,
            ),)


AS_NODE_CLASS_MAPPINGS = {
    "AutoSurvey": AutoSurvey,
    "WriteOutline": WriteOutline,
    "WriteSection": WriteSection,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
AS_NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoSurvey": "Auto Survey",
    "WriteOutline": "Write Outline",
    "WriteSection": "Write Section",
}
