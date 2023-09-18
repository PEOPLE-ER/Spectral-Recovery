import pytest
import xarray as xr
import numpy as np
import pandas as pd
import rioxarray

from spectral_recovery.metrics import (
    Y2R,
    dNBR,
    RRI,
    YrYr,
    R80P,
)

# TODO: simplfy parameterize calls using this func.
def make_da(data, dims, time=None, band=None, y=None, x=None, crs=None):
    coords = {"time":time, "band":band, "y":y, "x":x}
    coords = {k: v for k, v in coords.items() if v is not None}
    obs = xr.DataArray(
            data,
            coords=coords,
            dims=dims,
    )
    if crs:
        obs = obs.rio.write_crs("4326")
    return obs

@pytest.mark.parametrize(
    ("recovery_target", "obs", "expected"),
    [
        (   
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[70]], [[80]]]], # meets recovery target
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            xr.DataArray([[[1.0]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
        (
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[70]], [[90]]]], # surpasses recovery target
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            xr.DataArray([[[1.0]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
        (
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[80]], [[90]]]], # equals recovery target at start
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            xr.DataArray([[[0.0]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
        (
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[60]], [[70]]]], # never meets recovery target
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            xr.DataArray([[[np.nan]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
        (
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[70, 60], [70, 60]], [[80, 70], [70, 70]], [[100, 70], [70, 80]]]],
                coords={
                    "time": [
                        pd.to_datetime("2020"),
                        pd.to_datetime("2021"),
                        pd.to_datetime("2022"),
                    ]
                },
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            xr.DataArray(
                [[[1.0, np.nan], [np.nan, 2.0]]], dims=["band", "y", "x"]
            ).rio.write_crs("4326"),
        ),
    ],
)
def test_default_y2r(recovery_target, obs, expected):
    print(expected)
    assert Y2R(
        image_stack=obs,
        recovery_target=recovery_target,
        rest_start="2020",
    ).equals(expected)

@pytest.mark.parametrize(
    ("recovery_target", "obs", "percent", "expected"),
    [
        (
            xr.DataArray([87], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[80]], [[100]]]],
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            100, # take full recovery target
            xr.DataArray([[[1.0]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
        (
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[30]], [[110]]]],
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            0, # recovery target of 0
            xr.DataArray([[[0.0]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
        (
            xr.DataArray([100], dims=["band"]).rio.write_crs("4326"),
            xr.DataArray(
                [[[[10]], [[19]]]],
                coords={"time": [pd.to_datetime("2020"), pd.to_datetime("2021")]},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            20, # X percent of recovery target
            xr.DataArray([[[np.nan]]], dims=["band", "y", "x"]).rio.write_crs("4326"),
        ),
    ],
)
def test_percent_y2r(recovery_target, obs, percent, expected):
    assert Y2R(
        image_stack=obs,
        recovery_target=recovery_target,
        percent=percent,
        rest_start="2020",
    ).equals(expected)


# TODO: make this into func
year_period = [
    pd.to_datetime("2010"),
    pd.to_datetime("2011"),
    pd.to_datetime("2012"),
    pd.to_datetime("2013"),
    pd.to_datetime("2014"),
    pd.to_datetime("2015"),
]   


@pytest.mark.parametrize(
    ("obs", "restoration_date", "expected"),
    [
        (
            xr.DataArray(
                [[[[50]], [[60]], [[70]], [[80]], [[90]], [[100]]]],
                coords={"time": year_period},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            "2010",
            xr.DataArray(
                [[[50]]],
                dims=["band", "y", "x"],
            ).rio.write_crs("4326"),
        ),
        (
            xr.DataArray(
                [
                    [
                        [[50, 10], [10, 20]],
                        [[60, 20], [10, 20]],
                        [[70, 30], [10, 20]],
                        [[80, 40], [10, 20]],
                        [[90, 50], [10, 20]],
                        [[100, 80], [10, 20]],
                    ]
                ],
                coords={"time": year_period},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            "2010",
            xr.DataArray(
                [[[50, 70], [0, 0]]],
                dims=["band", "y", "x"],
            ).rio.write_crs("4326"),
        ),
        (
            xr.DataArray(
                [
                    [
                        [[50]],
                        [[60]],
                        [[70]],
                        [[80]],
                        [[90]],
                        [[100]],
                    ],
                    [
                        [[10]],
                        [[20]],
                        [[40]],
                        [[60]],
                        [[80]],
                        [[100]],
                    ],
                ],
                coords={"time": year_period},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            "2010",
            xr.DataArray(
                [[[50]], [[90]]],
                dims=["band", "y", "x"],
            ).rio.write_crs("4326"),
        ),
    ],
)
def test_correct_dNBR(obs, restoration_date, expected):
    assert dNBR(
        image_stack=obs,
        rest_start=restoration_date,
    ).equals(expected)


year_period_RI = [
    pd.to_datetime("2000"),
    pd.to_datetime("2001"),
    pd.to_datetime("2002"),
    pd.to_datetime("2003"),
    pd.to_datetime("2004"),
    pd.to_datetime("2005"),
    pd.to_datetime("2006"),
]


# TODO: follow-up on test cases with Melissa
@pytest.mark.parametrize(
    ("obs", "restoration_date", "expected"),
    [
        (
            xr.DataArray(
                [[[[70]], [[60]], [[70]], [[80]], [[90]], [[100]], [[110]]]],
                coords={"time": year_period_RI},
                dims=["band", "time", "y", "x"],
            ).rio.write_crs("4326"),
            "2001",
            xr.DataArray(
                [[[5.0]]],
                dims=["band", "y", "x"],
            ).rio.write_crs("4326"),
        ),
    ],
)
def test_correct_RRI(obs, restoration_date, expected):
    assert RRI(
        image_stack=obs,
        rest_start=restoration_date,
    ).equals(expected)
