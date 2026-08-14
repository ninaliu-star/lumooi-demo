from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).with_name('resume_editor_frontend')
_resume_editor = components.declare_component('careerpilot_resume_editor_v2', path=str(_COMPONENT_DIR))


def resume_editor(
    value: str,
    settings: dict,
    key: str,
    height: int = 980,
    mode: str = "edit",
    base_value: str = "",
    document_version: str = "",
):
    """Render the rich-text resume editor and return its HTML + page settings."""
    default = {"html": value, "settings": settings, "selected_text": "", "selection_id": 0, "page_count": 1}
    return _resume_editor(
        value=value,
        settings=settings,
        mode=mode,
        base_value=base_value,
        document_version=document_version,
        key=key,
        default=default,
        height=height,
    )
