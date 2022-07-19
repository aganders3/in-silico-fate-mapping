from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest

from in_silico_photo_manipulation.photom import PhotoM


def _line(n_samples: int = 5, length: int = 50, dim: int = 3) -> np.ndarray:
    """Generates a random line on the tracks format"""
    rng = np.random.default_rng(42)
    start = rng.uniform(5, 25, size=(1, dim))
    end = rng.uniform(60, 80, size=(1, dim))
    weight = np.linspace(0, 1, num=length)[:, np.newaxis]
    tracks = np.empty((n_samples, length, dim + 2), dtype=float)
    line = start * (1 - weight) + end * weight
    for i in range(n_samples):
        tracks[i, :, 0] = i + 1
        tracks[i, :, 1] = np.arange(length)
        tracks[i, :, 2:] = line + rng.normal(size=(length, dim))
    return tracks.reshape((n_samples * length, dim + 2))


@pytest.fixture
def line(**kwargs) -> np.ndarray:
    return _line(**kwargs)


@pytest.fixture
def line_factory() -> Callable:
    def _func(**kwargs) -> np.ndarray:
        return _line(**kwargs)

    return _func


@pytest.mark.parametrize("attr,value", [("reverse", True), ("radius", 5)])
def test_lazy_fit(attr: str, value: Any, line: np.ndarray) -> None:
    photom = PhotoM(data=line, reverse=True, radius=7, n_samples=5)
    assert not photom._fitted

    photom(line[0, 1:])
    assert photom._fitted

    setattr(photom, attr, value)
    assert not photom._fitted


def test_simple_reconstruction(
    line_factory: Callable,
    n_samples: int = 25,
    length: int = 50,
    dim: int = 3,
) -> None:

    sigma = 1
    photom = PhotoM(
        radius=5, n_samples=n_samples, bind_to_existing=False, sigma=sigma
    )

    line = line_factory(n_samples=1, length=length, dim=dim)
    photom.data = line

    tracks = photom(line[0, 1:])
    assert tracks.shape == (n_samples * length, dim + 2)

    avg = tracks[:, 2:].reshape((n_samples, length, dim)).mean(axis=0)
    assert avg.shape == (length, dim)

    error = np.mean(np.abs(avg - line[:, 2:]))
    assert error < 1e-8

    photom.heatmap = True
    heatmap = photom(line[0, 1:])

    avg = (
        pd.DataFrame(np.asarray(np.nonzero(heatmap)).T)
        .groupby(0)
        .mean()
        .values
    )

    max_error = np.abs(avg - line[:, 2:]).max()
    assert max_error < 1


def test_weights_attr(line: np.ndarray) -> None:
    photom = PhotoM(data=line, weights="distance")
    photom._fit()
    for m in photom._models.values():
        assert m.weights == "distance"

    photom.weights = "uniform"
    for m in photom._models.values():
        assert m.weights == "uniform"


def test_binding_attr(line: np.ndarray) -> None:
    photom = PhotoM(data=line, bind_to_existing=True, n_samples=5)
    result = photom(line[0, 1:])

    lines_start = np.sort(line[line[:, 1] == 0], axis=0)
    results_start = np.sort(result[result[:, 1] == 0], axis=0)

    assert np.allclose(lines_start, results_start)
