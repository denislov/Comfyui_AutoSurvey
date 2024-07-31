import os
import folder_paths


class UploadFiles:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "file_list": ("STRING", {
                    "multiline": True,  # True if you want the field to look like the one on the ClipTextEncode node
                    "default": sorted(files)
                }),
            },
        }

    RETURN_TYPES = ("STRING", "ARRAY_STRING")
    RETURN_NAMES = ("text", "file_list")
    OUTPUT_NODE = True
    FUNCTION = "upload_files"

    CATEGORY = "Senser/Utils"

    def upload_files(self, file_list: str):
        return file_list, file_list.split('\n')


# Add custom API routes, using router
from aiohttp import web  # noqa: E402
from server import PromptServer  # noqa: E402


def get_dir_by_type(dir_type):
    if dir_type is None:
        dir_type = "input"

    type_dir = folder_paths.get_input_directory()
    if dir_type == "temp":
        type_dir = folder_paths.get_temp_directory()
    elif dir_type == "output":
        type_dir = folder_paths.get_output_directory()

    return type_dir, dir_type


@PromptServer.instance.routes.post("/upload/files")
async def upload_files(request):
    post = await request.post()
    file = post.get("file")
    if file and file.file:
        filename = file.filename
        if not filename:
            return web.Response(status=400)
    image_upload_type = post.get("type")
    upload_dir, image_upload_type = get_dir_by_type(image_upload_type)
    subfolder = post.get("subfolder", "")
    full_output_folder = os.path.join(upload_dir, os.path.normpath(subfolder))
    filepath = os.path.abspath(os.path.join(full_output_folder, filename))
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return web.json_response({"file": ["post", "get"]}, status=200)
