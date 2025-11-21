"""Configuración centralizada de la aplicación."""
from functools import lru_cache
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "PhpMyAdminMW5"
    db_user: str = "root"
    db_password: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_workers: int = 4
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_ttl: int = 300
    
    # Aplicación
    app_name: str = "FUTUISP Analytics"
    app_version: str = "0.1.0"
    debug: bool = False

    score_umbral_minimo_facturas: int = 2 # Default 3 si no está en .env
    
    @property
    def database_url(self) -> str:
        """URL de conexión a la base de datos con password encoding."""
        # Escapar caracteres especiales en password
        encoded_password = quote_plus(self.db_password)
        
        return (
            f"mysql+aiomysql://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            "?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """Obtiene instancia única de configuración."""
    return Settings()
