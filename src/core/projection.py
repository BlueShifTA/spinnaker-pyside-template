"""Projection analysis utilities for beam profiling.

This module provides classes and functions for calculating and analyzing
1D projections from 2D camera images, including FWHM calculation for
Gaussian-like beam profiles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt


class ProjectionMode(Enum):
    """Projection calculation modes.

    Attributes:
        SUM: Sum of pixel values along axis (true projection/integral).
        MIN: Minimum pixel value along axis.
        MAX: Maximum pixel value along axis.
        AVERAGE: Mean pixel value along axis.
    """

    SUM = "sum"
    MIN = "min"
    MAX = "max"
    AVERAGE = "avg"


@dataclass
class ProjectionStats:
    """Statistics for a 1D projection profile.

    Attributes:
        mean: Mean value of the projection.
        std: Standard deviation of the projection.
        min_val: Minimum value in the projection.
        max_val: Maximum value in the projection.
        fwhm: Full Width at Half Maximum (None if not calculable).
        fwhm_left: Left position of FWHM crossing.
        fwhm_right: Right position of FWHM crossing.
        peak_pos: Position of the maximum value.
    """

    mean: float
    std: float
    min_val: float
    max_val: float
    fwhm: float | None = None
    fwhm_left: float | None = None
    fwhm_right: float | None = None
    peak_pos: int = 0


def calculate_projection(
    image: npt.NDArray[np.float64],
    axis: int,
    mode: ProjectionMode = ProjectionMode.AVERAGE,
) -> npt.NDArray[np.float64]:
    """Calculate 1D projection from a 2D image.

    Args:
        image: 2D grayscale image array.
        axis: Axis along which to project (0 for X projection, 1 for Y).
        mode: Projection calculation mode.

    Returns:
        1D array containing the projection values.

    Example:
        >>> img = np.random.rand(480, 640)
        >>> x_proj = calculate_projection(img, axis=0)  # Shape: (640,)
        >>> y_proj = calculate_projection(img, axis=1)  # Shape: (480,)
    """
    if mode == ProjectionMode.SUM:
        result: npt.NDArray[np.float64] = np.sum(image, axis=axis, dtype=np.float64)
    elif mode == ProjectionMode.MIN:
        result = np.min(image, axis=axis).astype(np.float64)
    elif mode == ProjectionMode.MAX:
        result = np.max(image, axis=axis).astype(np.float64)
    else:  # AVERAGE
        result = np.mean(image, axis=axis, dtype=np.float64)
    return result


def normalize_projection(
    data: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Normalize projection data to [0, 1] range.

    Args:
        data: 1D projection array.

    Returns:
        Normalized array where max value is 1.0.
    """
    max_val = np.max(data)
    if max_val > 0:
        return data / max_val
    return data.copy()


def calculate_fwhm(
    data: npt.NDArray[np.float64],
) -> tuple[float | None, float | None, float | None]:
    """Calculate Full Width at Half Maximum for a profile.

    Uses linear interpolation to find precise crossing points.

    Args:
        data: 1D array representing the profile (e.g., beam intensity).

    Returns:
        Tuple of (fwhm, left_pos, right_pos). Returns (None, None, None)
        if FWHM cannot be calculated (e.g., no clear peak).

    Example:
        >>> # Gaussian-like profile
        >>> x = np.linspace(-5, 5, 100)
        >>> profile = np.exp(-x**2 / 2)
        >>> fwhm, left, right = calculate_fwhm(profile)
    """
    if len(data) < 3:
        return None, None, None

    # Find peak
    peak_idx = int(np.argmax(data))
    peak_val = data[peak_idx]
    min_val = np.min(data)

    # Half maximum level (relative to baseline)
    half_max = (peak_val + min_val) / 2

    # Find left crossing (search from peak leftward)
    left_pos: float | None = None
    for i in range(peak_idx, 0, -1):
        if data[i - 1] <= half_max <= data[i]:
            # Linear interpolation
            if data[i] != data[i - 1]:
                left_pos = i - 1 + (half_max - data[i - 1]) / (data[i] - data[i - 1])
            else:
                left_pos = float(i)
            break

    # Find right crossing (search from peak rightward)
    right_pos: float | None = None
    for i in range(peak_idx, len(data) - 1):
        if data[i] >= half_max >= data[i + 1]:
            # Linear interpolation
            if data[i] != data[i + 1]:
                right_pos = i + (data[i] - half_max) / (data[i] - data[i + 1])
            else:
                right_pos = float(i)
            break

    if left_pos is not None and right_pos is not None:
        fwhm = right_pos - left_pos
        return fwhm, left_pos, right_pos

    return None, None, None


def calculate_stats(data: npt.NDArray[np.float64]) -> ProjectionStats:
    """Calculate comprehensive statistics for a projection.

    Args:
        data: 1D projection array.

    Returns:
        ProjectionStats containing mean, std, min, max, FWHM, and peak position.
    """
    mean = float(np.mean(data))
    std = float(np.std(data))
    min_val = float(np.min(data))
    max_val = float(np.max(data))
    peak_pos = int(np.argmax(data))

    fwhm, fwhm_left, fwhm_right = calculate_fwhm(data)

    return ProjectionStats(
        mean=mean,
        std=std,
        min_val=min_val,
        max_val=max_val,
        fwhm=fwhm,
        fwhm_left=fwhm_left,
        fwhm_right=fwhm_right,
        peak_pos=peak_pos,
    )


class ProjectionAnalyzer:
    """Analyzer for extracting and processing image projections.

    This class handles the complete workflow of extracting projections
    from camera frames and calculating statistics for beam analysis.

    Attributes:
        mode: Current projection calculation mode.
        normalize: Whether to normalize projections to [0, 1].

    Example:
        >>> analyzer = ProjectionAnalyzer(mode=ProjectionMode.AVERAGE)
        >>> frame = camera.get_frame()
        >>> x_data, x_stats = analyzer.analyze_x(frame)
        >>> y_data, y_stats = analyzer.analyze_y(frame)
    """

    def __init__(
        self,
        mode: ProjectionMode = ProjectionMode.AVERAGE,
        normalize: bool = False,
    ) -> None:
        """Initialize the projection analyzer.

        Args:
            mode: Projection calculation mode.
            normalize: Whether to normalize output to [0, 1].
        """
        self.mode = mode
        self.normalize = normalize

    def _to_grayscale(self, frame: npt.NDArray[np.uint8]) -> npt.NDArray[np.float64]:
        """Convert frame to grayscale float array."""
        if len(frame.shape) == 3:
            # Use first channel (faster than np.mean for mono cameras)
            return frame[:, :, 0].astype(np.float64)
        return frame.astype(np.float64)

    def analyze_x(
        self, frame: npt.NDArray[np.uint8]
    ) -> tuple[npt.NDArray[np.float64], ProjectionStats]:
        """Analyze X projection (horizontal, below image).

        Projects along vertical axis (axis=0) to get intensity vs X position.

        Args:
            frame: Camera frame (grayscale or BGR).

        Returns:
            Tuple of (projection_data, statistics).
        """
        gray = self._to_grayscale(frame)
        data = calculate_projection(gray, axis=0, mode=self.mode)

        if self.normalize:
            data = normalize_projection(data)

        stats = calculate_stats(data)
        return data, stats

    def analyze_y(
        self, frame: npt.NDArray[np.uint8]
    ) -> tuple[npt.NDArray[np.float64], ProjectionStats]:
        """Analyze Y projection (vertical, left of image).

        Projects along horizontal axis (axis=1) to get intensity vs Y position.

        Args:
            frame: Camera frame (grayscale or BGR).

        Returns:
            Tuple of (projection_data, statistics).
        """
        gray = self._to_grayscale(frame)
        data = calculate_projection(gray, axis=1, mode=self.mode)

        if self.normalize:
            data = normalize_projection(data)

        stats = calculate_stats(data)
        return data, stats
