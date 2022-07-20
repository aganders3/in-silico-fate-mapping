import napari
from magicgui.widgets import (
    CheckBox,
    ComboBox,
    Container,
    FloatSpinBox,
    PushButton,
    SpinBox,
    create_widget,
)
from napari.layers import Points, Tracks
from toolz import curry

from in_silico_photo_manipulation.photom import PhotoM


class PhotoMWidget(Container):
    def __init__(self, viewer: napari.Viewer):
        super().__init__()
        self._viewer = viewer

        self._tracks_layer_w = create_widget(
            annotation=Tracks,
            label="tracks",
            options=dict(
                tooltip="tracks layer used to compute the interpolation model"
            ),
        )
        self.append(self._tracks_layer_w)

        self._points_layer_w = create_widget(
            annotation=Points,
            label="points",
            options=dict(
                tooltip="points layer for photo manipulation area (starting/source point)"
            ),
        )
        self.append(self._points_layer_w)

        self._radius_w = FloatSpinBox(
            label="radius",
            value=30,
            step=5,
            tooltip="neighborhood radius used to interpolate each sample",
        )
        self.append(self._radius_w)

        self._n_samples_w = SpinBox(
            label="n. samples",
            value=25,
            tooltip="number of samples at each starting point",
            max=10000,
        )
        self.append(self._n_samples_w)

        self._bind_w = CheckBox(
            label="bind to tracks",
            value=True,
            tooltip="bind sample to existing tracks at starting point",
        )
        self.append(self._bind_w)

        self._reverse_w = CheckBox(
            label="reverse", tooltip="interpolate from end to start"
        )
        self.append(self._reverse_w)

        self._weights_w = ComboBox(
            label="weights",
            choices=("distance", "uniform"),
            tooltip="interpolation weight strategy",
        )
        self.append(self._weights_w)

        self._sigma_w = FloatSpinBox(
            label="noise sigma",
            value=0,
            tooltip="interpolation (jitter) sigma at each step, ignored if 0",
        )
        self.append(self._sigma_w)

        self._heatmap_w = CheckBox(
            label="heatmap",
            value=False,
            tooltip="output an heatmap, by default it return tracks",
        )
        self.append(self._heatmap_w)

        self._run_btn = PushButton(text="run", tooltip="RUNNNNNNN")
        self.append(self._run_btn)

        self._clear_btn = PushButton(
            text="clear points", tooltip="clear the selected points layer"
        )
        self.append(self._clear_btn)

        self._photom = PhotoM(
            radius=self._radius_w.value,
            reverse=self._reverse_w.value,
            sigma=self._sigma_w.value,
            weights=self._weights_w.value,
            heatmap=self._heatmap_w.value,
            n_samples=self._n_samples_w.value,
            bind_to_existing=self._bind_w.value,
        )

        self._setup_signals()

    def _setup_signals(self) -> None:
        self._run_btn.changed.connect(self._on_run)
        self._clear_btn.changed.connect(self._on_clear_points)
        self._tracks_layer_w.changed.connect(self._on_tracks_changed)
        self._reverse_w.changed.connect(
            curry(setattr, self._photom, "reverse")
        )
        self._radius_w.changed.connect(curry(setattr, self._photom, "radius"))
        self._sigma_w.changed.connect(curry(setattr, self._photom, "sigma"))
        self._bind_w.changed.connect(
            curry(setattr, self._photom, "bind_to_existing")
        )
        self._weights_w.changed.connect(
            curry(setattr, self._photom, "weights")
        )
        self._heatmap_w.changed.connect(
            curry(setattr, self._photom, "heatmap")
        )
        self._n_samples_w.changed.connect(
            curry(setattr, self._photom, "n_samples")
        )

    def _on_tracks_changed(self, layer: Tracks) -> None:
        if layer is None:
            self._photom.data = layer
            return
        data = layer.data.copy()
        # converting to anisotropic space
        data[:, 1:] = layer._data_to_world(data[:, 1:])
        self._photom.data = data

    def _on_run(self) -> None:
        layer: Points = self._points_layer_w.value
        if layer is None:
            raise ValueError("points layer must be set before running")

        coords = layer.data
        if len(coords) == 0:
            raise ValueError("No sources found.")

        coords = layer._data_to_world(coords)

        result = self._photom(coords)

        if self._heatmap_w.value:
            self._viewer.add_image(
                result,
                colormap="magma",
                blending="additive",
                name="PhotoM Heatmap",
            )
        else:
            self._viewer.add_tracks(
                result, colormap="hsv", name="PhotoM Tracks"
            )

    def _on_clear_points(self) -> None:
        if self._points_layer_w.value is None:
            return
        self._points_layer_w.value.data = []
