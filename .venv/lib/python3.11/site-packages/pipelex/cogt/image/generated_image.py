from pydantic import BaseModel


class GeneratedImage(BaseModel):
    # TODO: add image_format
    # image_format: str = "jpeg"
    url: str
    width: int
    height: int
