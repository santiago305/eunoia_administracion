"""Adaptador ligero sobre ``fuvexbn.config.settings`` para la capa de aplicación."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fuvexbn.config import settings as raw_settings
from fuvexbn.features.Ingresar.settings import ingresar_settings
from fuvexbn.features.buscar.settings import buscar_settings


@dataclass
class AppSettings:
    """Vista parcial de ``settings`` con sólo los atributos usados por la app."""

    _source: Any

    @property
    def excels_base_path(self) -> str:
        return getattr(self._source, "EXCELS_BASE_PATH", "")

    @property
    def user_name(self) -> str:
        return getattr(self._source, "USER_NAME", "")

    @property
    def excel_path_buscar(self) -> str:
        return buscar_settings.EXCEL_PATH_BUSCAR

    @property
    def excel_path_filtrar(self) -> str:
        return ingresar_settings.EXCEL_PATH_FILTRAR

    @property
    def excel_path_registros(self) -> str:
        return ingresar_settings.EXCEL_PATH_REGISTROS

    @property
    def EXCEL_PATH_BUSCAR(self) -> str:
        """Mantiene compatibilidad con código que espera atributos en mayúsculas."""

        return buscar_settings.EXCEL_PATH_BUSCAR

    @property
    def EXCEL_PATH_FILTRAR(self) -> str:
        return ingresar_settings.EXCEL_PATH_FILTRAR

    @property
    def EXCEL_PATH_REGISTROS(self) -> str:
        return ingresar_settings.EXCEL_PATH_REGISTROS

    def __getattr__(self, item: str) -> Any:
        return getattr(self._source, item)


def load_app_settings() -> AppSettings:
    """Construye una instancia de :class:`AppSettings`."""

    return AppSettings(raw_settings)


settings = load_app_settings()

__all__ = ["AppSettings", "load_app_settings", "settings"]