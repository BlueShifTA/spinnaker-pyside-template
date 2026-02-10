"""Tests for projection analysis module."""

from __future__ import annotations

import numpy as np
import pytest

from core.projection import (
    ProjectionAnalyzer,
    ProjectionMode,
    ProjectionStats,
    calculate_fwhm,
    calculate_projection,
    calculate_stats,
    normalize_projection,
)


class TestProjectionMode:
    """Tests for projection calculation modes."""

    def test_average_mode(self) -> None:
        """Test average projection mode."""
        img = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float64)
        result = calculate_projection(img, axis=0, mode=ProjectionMode.AVERAGE)
        expected = np.array([4.0, 5.0, 6.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_sum_mode(self) -> None:
        """Test sum projection mode."""
        img = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float64)
        result = calculate_projection(img, axis=0, mode=ProjectionMode.SUM)
        expected = np.array([12.0, 15.0, 18.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_min_mode(self) -> None:
        """Test minimum projection mode."""
        img = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float64)
        result = calculate_projection(img, axis=0, mode=ProjectionMode.MIN)
        expected = np.array([1.0, 2.0, 3.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_max_mode(self) -> None:
        """Test maximum projection mode."""
        img = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float64)
        result = calculate_projection(img, axis=0, mode=ProjectionMode.MAX)
        expected = np.array([7.0, 8.0, 9.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_projection_axis_x(self) -> None:
        """Test X projection (axis=0) produces correct shape."""
        img = np.random.rand(480, 640)
        result = calculate_projection(img, axis=0, mode=ProjectionMode.AVERAGE)
        assert result.shape == (640,)

    def test_projection_axis_y(self) -> None:
        """Test Y projection (axis=1) produces correct shape."""
        img = np.random.rand(480, 640)
        result = calculate_projection(img, axis=1, mode=ProjectionMode.AVERAGE)
        assert result.shape == (480,)


class TestNormalization:
    """Tests for projection normalization."""

    def test_normalize_basic(self) -> None:
        """Test basic normalization."""
        data = np.array([0.0, 50.0, 100.0, 50.0, 0.0])
        result = normalize_projection(data)
        assert result.max() == 1.0
        assert result.min() == 0.0
        np.testing.assert_array_almost_equal(result, [0.0, 0.5, 1.0, 0.5, 0.0])

    def test_normalize_zero_max(self) -> None:
        """Test normalization when max is zero."""
        data = np.array([0.0, 0.0, 0.0])
        result = normalize_projection(data)
        np.testing.assert_array_equal(result, data)

    def test_normalize_preserves_shape(self) -> None:
        """Test that normalization preserves array shape."""
        data = np.random.rand(1920)
        result = normalize_projection(data)
        assert result.shape == data.shape


class TestFWHM:
    """Tests for FWHM calculation."""

    def test_fwhm_gaussian(self) -> None:
        """Test FWHM on a known Gaussian profile."""
        # Create Gaussian with known FWHM
        # FWHM = 2 * sqrt(2 * ln(2)) * sigma ≈ 2.355 * sigma
        sigma = 10.0
        x = np.arange(100)
        center = 50
        gaussian = np.exp(-0.5 * ((x - center) / sigma) ** 2)

        fwhm, left, right = calculate_fwhm(gaussian)

        expected_fwhm = 2.355 * sigma
        assert fwhm is not None
        assert abs(fwhm - expected_fwhm) < 0.5  # Within 0.5 pixels

    def test_fwhm_symmetric(self) -> None:
        """Test that FWHM is symmetric around peak."""
        x = np.arange(100)
        center = 50
        profile = np.exp(-0.5 * ((x - center) / 10) ** 2)

        fwhm, left, right = calculate_fwhm(profile)

        assert left is not None and right is not None
        # Check symmetry
        assert abs((center - left) - (right - center)) < 0.5

    def test_fwhm_no_peak(self) -> None:
        """Test FWHM returns None for flat profile."""
        data = np.ones(100)
        fwhm, left, right = calculate_fwhm(data)
        # Flat profile has no meaningful FWHM
        assert fwhm is None or fwhm == 0

    def test_fwhm_short_array(self) -> None:
        """Test FWHM with too-short array."""
        data = np.array([1.0, 2.0])
        fwhm, left, right = calculate_fwhm(data)
        assert fwhm is None

    def test_fwhm_edge_peak(self) -> None:
        """Test FWHM when peak is at edge."""
        data = np.array([100.0, 80.0, 60.0, 40.0, 20.0])
        fwhm, left, right = calculate_fwhm(data)
        # Peak at edge, may not have left crossing
        assert left is None or right is None


class TestProjectionStats:
    """Tests for comprehensive statistics calculation."""

    def test_stats_basic(self) -> None:
        """Test basic statistics calculation."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        stats = calculate_stats(data)

        assert stats.mean == 3.0
        assert stats.min_val == 1.0
        assert stats.max_val == 5.0
        assert stats.peak_pos == 4
        assert abs(stats.std - np.std(data)) < 0.001

    def test_stats_gaussian(self) -> None:
        """Test statistics on Gaussian profile."""
        x = np.arange(100)
        data = 100.0 * np.exp(-0.5 * ((x - 50) / 10) ** 2)
        stats = calculate_stats(data)

        assert stats.peak_pos == 50
        assert stats.max_val == pytest.approx(100.0)
        assert stats.fwhm is not None
        assert stats.fwhm > 0


class TestProjectionAnalyzer:
    """Tests for ProjectionAnalyzer class."""

    def test_analyzer_creation(self) -> None:
        """Test analyzer initialization."""
        analyzer = ProjectionAnalyzer()
        assert analyzer.mode == ProjectionMode.AVERAGE
        assert analyzer.normalize is False

    def test_analyzer_with_mode(self) -> None:
        """Test analyzer with specific mode."""
        analyzer = ProjectionAnalyzer(mode=ProjectionMode.SUM)
        assert analyzer.mode == ProjectionMode.SUM

    def test_analyze_x_grayscale(self) -> None:
        """Test X analysis on grayscale image."""
        analyzer = ProjectionAnalyzer()
        frame = np.random.randint(0, 256, (480, 640), dtype=np.uint8)

        data, stats = analyzer.analyze_x(frame)

        assert data.shape == (640,)
        assert isinstance(stats, ProjectionStats)

    def test_analyze_y_grayscale(self) -> None:
        """Test Y analysis on grayscale image."""
        analyzer = ProjectionAnalyzer()
        frame = np.random.randint(0, 256, (480, 640), dtype=np.uint8)

        data, stats = analyzer.analyze_y(frame)

        assert data.shape == (480,)
        assert isinstance(stats, ProjectionStats)

    def test_analyze_x_color(self) -> None:
        """Test X analysis on color (BGR) image."""
        analyzer = ProjectionAnalyzer()
        frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

        data, stats = analyzer.analyze_x(frame)

        assert data.shape == (640,)

    def test_analyze_with_normalization(self) -> None:
        """Test analysis with normalization enabled."""
        analyzer = ProjectionAnalyzer(normalize=True)
        frame = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        data, stats = analyzer.analyze_x(frame)

        assert data.max() == pytest.approx(1.0)

    def test_analyze_mode_affects_result(self) -> None:
        """Test that different modes produce different results."""
        frame = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        avg_analyzer = ProjectionAnalyzer(mode=ProjectionMode.AVERAGE)
        sum_analyzer = ProjectionAnalyzer(mode=ProjectionMode.SUM)

        avg_data, _ = avg_analyzer.analyze_x(frame)
        sum_data, _ = sum_analyzer.analyze_x(frame)

        # Sum should be 100x average (height of image)
        np.testing.assert_array_almost_equal(sum_data, avg_data * 100)
