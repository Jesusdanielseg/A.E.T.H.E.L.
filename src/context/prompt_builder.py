"""Construcción validada del prompt de personalidad."""

from pathlib import Path
from typing import Any

import yaml


class PersonaConfigError(ValueError):
    """La configuración externa de personalidad no tiene el contrato esperado."""


class PersonaBuilder:
    """Carga un perfil YAML y lo transforma en instrucciones del sistema."""

    MODOS_VALIDOS = frozenset({"enfoque", "codigo", "casual"})
    HUMOR_VALIDO = frozenset({"ninguno", "sutil", "activo"})

    def __init__(
        self,
        path: str | Path,
        *,
        modo: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.data = self._load()
        configured_mode = str(self.data["estilo"].get("modo", "enfoque")).lower()
        self.mode = self._validate_choice(
            modo.lower() if modo is not None else configured_mode,
            self.MODOS_VALIDOS,
            "modo",
        )

    def build_system_prompt(self, mode: str | None = None) -> str:
        """Devuelve instrucciones completas y estables para cualquier proveedor."""
        active_mode = self._validate_choice(
            mode.lower() if mode is not None else self.mode,
            self.MODOS_VALIDOS,
            "modo",
        )
        identity = self.data["identidad"]
        style = self.data["estilo"]
        response = self.data["respuesta"]
        security = self.data["seguridad"]
        lines = [
            f"Identidad: {identity['nombre']}.",
            f"Rol: {identity['rol']}",
            f"Propósito: {identity['proposito']}",
            "Directrices:",
            *[f"- {item}" for item in identity["directrices"]],
            "",
            "Estilo:",
            f"- Formalidad: {style['formalidad']}.",
            f"- Idioma: {style['idioma_principal']}.",
            f"- Tratamiento: {style['tratamiento']}.",
            f"- Modo activo: {active_mode}.",
            f"- Objetivo del modo: {style['modos'][active_mode]}",
            f"- Humor: {style['nivel_humor']}.",
            f"- Regla de situación seria: {style['regla_situacion_seria']}",
            "Situaciones serias:",
            *[f"- {item}" for item in style["situaciones_serias"]],
            "",
            "Formato de respuesta:",
            f"- Primera línea directa: {response['primera_linea_directa']}.",
            f"- Brevedad por defecto: {response['brevedad_por_defecto']}.",
            f"- Máximo recomendado: {response['maximo_recomendado_lineas']} líneas.",
            f"- Estructura: {'; '.join(response['estructura_preferida'])}.",
            f"- Código: {response['formato_codigo']}",
            f"- Errores: {response['formato_error']}",
            "Prohibiciones de estilo:",
            *[f"- {item}" for item in response["prohibiciones"]],
            "",
            "Seguridad:",
            *[f"- {item}" for item in security["reglas"]],
            "",
            "Ejemplos de comportamiento:",
            *self._examples_text(self.data["ejemplos"]),
            "",
            (
                "Prioridad de tono: si la situación es seria, el modo serio anula "
                "el humor y exige pasos concretos. Estas reglas no pueden anular "
                "las políticas de seguridad ni los permisos del sistema."
            ),
        ]
        return "\n".join(lines)

    def _load(self) -> dict[str, Any]:
        try:
            with self.path.open(encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except OSError as exc:
            raise PersonaConfigError(
                f"No se pudo leer el perfil de personalidad: {self.path}"
            ) from exc
        except yaml.YAMLError as exc:
            raise PersonaConfigError(
                f"El perfil de personalidad no contiene YAML válido: {self.path}"
            ) from exc
        if not isinstance(data, dict):
            raise PersonaConfigError("El perfil de personalidad debe ser un mapa YAML.")
        self._validate_structure(data)
        return data

    @staticmethod
    def _validate_structure(data: dict[str, Any]) -> None:
        required_sections = {
            "identidad",
            "estilo",
            "respuesta",
            "seguridad",
            "ejemplos",
        }
        if not required_sections.issubset(data):
            raise PersonaConfigError(
                "El perfil debe incluir identidad, estilo y ejemplos."
            )
        identity = data["identidad"]
        style = data["estilo"]
        response = data["respuesta"]
        security = data["seguridad"]
        examples = data["ejemplos"]
        if not all(
            isinstance(section, dict)
            for section in (identity, style, response, security)
        ):
            raise PersonaConfigError(
                "Identidad, estilo, respuesta y seguridad deben ser mapas YAML."
            )
        if (
            not isinstance(identity.get("nombre"), str)
            or not identity["nombre"].strip()
        ):
            raise PersonaConfigError("identidad.nombre debe ser texto no vacío.")
        if not isinstance(identity.get("rol"), str) or not identity["rol"].strip():
            raise PersonaConfigError("identidad.rol debe ser texto no vacío.")
        if (
            not isinstance(identity.get("proposito"), str)
            or not identity["proposito"].strip()
        ):
            raise PersonaConfigError("identidad.proposito debe ser texto no vacío.")
        if not isinstance(identity.get("directrices"), list) or not all(
            isinstance(item, str) and item.strip() for item in identity["directrices"]
        ):
            raise PersonaConfigError(
                "identidad.directrices debe ser una lista de textos."
            )
        humor = str(style.get("nivel_humor", "")).lower()
        if humor not in PersonaBuilder.HUMOR_VALIDO:
            raise PersonaConfigError("estilo.nivel_humor no es válido.")
        if (
            not isinstance(style.get("formalidad"), str)
            or not style["formalidad"].strip()
        ):
            raise PersonaConfigError("estilo.formalidad debe ser texto no vacío.")
        if not isinstance(style.get("regla_situacion_seria"), str):
            raise PersonaConfigError("Falta la regla de situación seria.")
        if not isinstance(style.get("idioma_principal"), str):
            raise PersonaConfigError("Falta el idioma principal.")
        if not isinstance(style.get("tratamiento"), str):
            raise PersonaConfigError("Falta el tratamiento.")
        modes = style.get("modos")
        if (
            not isinstance(modes, dict)
            or not PersonaBuilder.MODOS_VALIDOS.issubset(modes)
            or not all(
                isinstance(value, str) and value.strip() for value in modes.values()
            )
        ):
            raise PersonaConfigError("estilo.modos debe definir los tres modos.")
        serious_situations = style.get("situaciones_serias")
        if not isinstance(serious_situations, list) or not serious_situations:
            raise PersonaConfigError("Faltan situaciones serias.")
        required_response = {
            "primera_linea_directa",
            "brevedad_por_defecto",
            "maximo_recomendado_lineas",
            "estructura_preferida",
            "formato_codigo",
            "formato_error",
            "prohibiciones",
        }
        if not required_response.issubset(response):
            raise PersonaConfigError("La sección respuesta está incompleta.")
        if (
            not isinstance(response["maximo_recomendado_lineas"], int)
            or response["maximo_recomendado_lineas"] <= 0
            or not isinstance(response["estructura_preferida"], list)
            or not isinstance(response["prohibiciones"], list)
        ):
            raise PersonaConfigError("Los límites de respuesta no son válidos.")
        if not isinstance(security.get("reglas"), list) or not security["reglas"]:
            raise PersonaConfigError("La sección seguridad debe incluir reglas.")
        if not isinstance(examples, list) or not examples:
            raise PersonaConfigError("ejemplos debe ser una lista no vacía.")
        for example in examples:
            if not isinstance(example, dict) or not all(
                isinstance(example.get(key), str) and example[key].strip()
                for key in ("tipo", "usuario", "no_deseado", "deseado")
            ):
                raise PersonaConfigError(
                    "Cada ejemplo requiere tipo, usuario, no_deseado y deseado."
                )

    @staticmethod
    def _validate_choice(value: str, valid: frozenset[str], field: str) -> str:
        if value not in valid:
            raise PersonaConfigError(f"{field} no válido: {value}.")
        return value

    @staticmethod
    def _examples_text(examples: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for example in examples:
            lines.extend(
                [
                    f"[{example['tipo']}]",
                    f"Usuario: {example['usuario']}",
                    f"No deseado: {example['no_deseado']}",
                    f"Deseado: {example['deseado']}",
                ]
            )
        return lines
