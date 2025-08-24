from typing import Optional, Union, Literal
from pydantic import BaseModel, Field, RootModel


class TextContent(BaseModel):
    """纯文本内容"""
    type: Literal["text"] = Field("text", description="内容类型")
    text: str = Field(..., description="纯文本内容")


class MarkdownContent(BaseModel):
    """Markdown 格式内容"""
    type: Literal["markdown"] = Field("markdown", description="内容类型")
    markdown: str = Field(..., description="Markdown 格式文本")


class HTMLContent(BaseModel):
    """HTML 格式内容"""
    type: Literal["html"] = Field("html", description="内容类型")
    html: str = Field(..., description="HTML 文本")


class JSONContent(BaseModel):
    """结构化 JSON 格式内容"""
    type: Literal["json"] = Field("json", description="内容类型")
    json_data: dict = Field(..., description="JSON 对象格式数据")


class BinaryContent(BaseModel):
    """二进制内容（例如图片、文件）"""
    type: Literal["binary"] = Field("binary", description="内容类型")
    url: Optional[str] = Field(None, description="可选的访问链接")
    data: Optional[bytes] = Field(None, description="二进制数据")
    media_type: Optional[str] = Field(None, description="媒体类型，例如 'image/png'")


# -------- 核心内容模型 --------
ContentPart = RootModel[Union[TextContent, MarkdownContent, HTMLContent,
                              JSONContent, BinaryContent]]
