from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    WORDPRESS_URL: str
    WORDPRESS_USERNAME: str
    WORDPRESS_PASSWORD: str
    status: str

    # Optional site root for media uploads (default: derived from WORDPRESS_URL)
    BASE_URL: str | None = None

    # Imagen (same API key as Gemini Developer API in many setups)
    IMAGEN_MODEL: str = "imagen-3.0-generate-002"
    ENABLE_ARTICLE_IMAGES: bool = True
    GENERATED_IMAGE_MAX_WIDTH: int = 1024
    GENERATED_IMAGE_JPEG_QUALITY: int = 68

    app_dir: ClassVar[Path] = Path(__file__).resolve().parents[1]
    project_root: ClassVar[Path] = app_dir.parent

    # Support running from either project root or app directory.
    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            str(project_root / ".env"),
            str(app_dir / ".env"),
        ),
        env_file_encoding="utf-8",
    )

settings = Settings()