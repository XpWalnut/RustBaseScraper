from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    youtube_api_key: str
    openai_model: str = "gpt-5.4-nano"
    use_mock_traits: bool = False
    max_candidates_per_query: int = 10
    max_search_queries: int = 3
    max_images_for_trait_extraction: int = 2
    max_image_dimension: int = 768

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()