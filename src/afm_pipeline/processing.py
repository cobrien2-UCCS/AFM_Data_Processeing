"""
Processing stubs for the AFM pipeline (Py3 side).

Real pygwy work will occur in the Py2 runner. This module defines the API so
summarize_folder_to_csv can be called in tests or with a custom processor.
"""

from pathlib import Path
from typing import Dict, Any, Tuple


def process_tiff_with_gwyddion(path: Path, mode: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder: in Py3 environment, this should be replaced or mocked.

    The Py2 pygwy runner is expected to perform real processing. This function
    exists so summarize_folder_to_csv can import it; it raises by default.
    """
    raise NotImplementedError(
        "process_tiff_with_gwyddion is not implemented in the Py3 scaffold. "
        "Use the Py2 pygwy runner or inject a processor for testing."
    )


def APPLY_MODE_PIPELINE(field, source_file: str, mode: str, cfg: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    """Stub matching the spec signature; implemented in Py2 pygwy runner."""
    raise NotImplementedError("APPLY_MODE_PIPELINE is implemented in the Py2 pygwy runner.")
