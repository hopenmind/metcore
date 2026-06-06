"""
Smoke tests — package imports and public API surface.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""


def test_version_exposed():
    import boltz_kernel
    assert isinstance(boltz_kernel.__version__, str)
    assert boltz_kernel.__version__.count(".") >= 2  # semver-ish


def test_public_api():
    from boltz_kernel import (
        ComparisonResult,
        LindbladSolver,
        MemoryKernel,
        Result,
        SpectralDensities,
        compare,
    )
    # All objects are importable and non-None
    assert MemoryKernel is not None
    assert Result is not None
    assert LindbladSolver is not None
    assert compare is not None
    assert ComparisonResult is not None
    assert SpectralDensities is not None


def test_core_submodule():
    from boltz_kernel.core import MemoryKernel as MK1
    from boltz_kernel import MemoryKernel as MK2
    assert MK1 is MK2  # re-export identity


def test_branding_defaults_are_neutral():
    """Default branding must not expose the author company name on figures."""
    from boltz_kernel.branding import BrandingConfig
    cfg = BrandingConfig()
    # Visible fields must be tool-focused, not company-focused
    assert "Hope" not in cfg.institute_name
    assert "Hope" not in cfg.footer_text
    assert cfg.institute_name == "BoltZ-Kernel"
