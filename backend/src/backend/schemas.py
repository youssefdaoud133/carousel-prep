from __future__ import annotations

from pydantic import BaseModel, Field

from .imaging import Corner, FitMode, LogoSettings, Orientation, PadColor


class ImageInfo(BaseModel):
    id: str
    filename: str
    width: int
    height: int
    orientation: Orientation
    slides: int  # how many carousel slides this photo becomes


class UploadError(BaseModel):
    filename: str
    message: str


class UploadResult(BaseModel):
    images: list[ImageInfo]
    errors: list[UploadError]


class SessionInfo(BaseModel):
    id: str


class LogoInfo(BaseModel):
    width: int
    height: int


class LogoOptions(BaseModel):
    enabled: bool = False
    corner: Corner = Corner.BOTTOM_RIGHT
    size_pct: float = Field(15.0, ge=2, le=60)
    margin_pct: float = Field(4.0, ge=0, le=20)
    opacity: int = Field(100, ge=0, le=100)

    def to_settings(self) -> LogoSettings:
        return LogoSettings(self.corner, self.size_pct, self.margin_pct, self.opacity)


class OrderItem(BaseModel):
    id: str
    focus: float = Field(0.5, ge=0, le=1)


class RenderRequest(BaseModel):
    order: list[OrderItem] = Field(min_length=1)
    fit_mode: FitMode = FitMode.CROP
    pad_color: PadColor = PadColor.WHITE
    logo: LogoOptions = LogoOptions()
    title: str = ""


class PreviewSlide(BaseModel):
    index: int
    image_id: str
    part: str  # "full" | "left" | "right"
    name: str | None  # output filename, when the title is valid
    data_url: str


class PreviewResult(BaseModel):
    slides: list[PreviewSlide]
