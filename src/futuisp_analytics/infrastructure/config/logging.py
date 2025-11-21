"""Configuración de logging estructurado."""
import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configura logging para toda la aplicación.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado
    """
    # Formato con más información
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)-30s | "
        "%(funcName)-20s | %(message)s"
    )
    
    # Configurar handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
    
    # Logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(handler)
    
    # Reducir ruido de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Logger de la aplicación
    app_logger = logging.getLogger("futuisp_analytics")
    app_logger.setLevel(getattr(logging, level.upper()))
    
    return app_logger


# Logger global de la aplicación
logger = logging.getLogger("futuisp_analytics")
