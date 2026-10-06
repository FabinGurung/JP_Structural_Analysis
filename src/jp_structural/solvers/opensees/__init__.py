"""OpenSees/OpenSeesPy primary solver adapters."""

from .canonical_frame import (
    CanonicalBuildResult,
    CanonicalTranslationError,
    build_canonical_frame_model,
    run_modal_analysis,
)
from .canonical_seismic import (
    ResponseSpectrumError,
    interpolate_spectral_acceleration,
    normalize_response_spectrum,
    run_canonical_response_spectrum,
)

__all__ = [
    "CanonicalBuildResult",
    "CanonicalTranslationError",
    "ResponseSpectrumError",
    "build_canonical_frame_model",
    "interpolate_spectral_acceleration",
    "normalize_response_spectrum",
    "run_canonical_response_spectrum",
    "run_modal_analysis",
]
