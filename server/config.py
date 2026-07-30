from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stdb_host: str = "localhost"
    stdb_port: int = 3001
    stdb_db: str = "spacetime-crm"
    server_port: int = 8723
    cors_origin: str = "http://localhost:5185"
    jwt_secret: str = "change-me-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    app_url: str = "http://localhost:8723"

    @property
    def stdb_sql_url(self) -> str:
        return (
            f"http://{self.stdb_host}:{self.stdb_port}/v1/database/{self.stdb_db}/sql"
        )

    @property
    def stdb_call_url(self) -> str:
        return (
            f"http://{self.stdb_host}:{self.stdb_port}/v1/database/{self.stdb_db}/call"
        )

    model_config = {"env_file": ".env"}


settings = Settings()
