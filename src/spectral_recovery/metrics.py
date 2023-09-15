import xarray as xr
import numpy as np
import pandas as pd

from spectral_recovery.utils import maintain_rio_attrs


@maintain_rio_attrs
def dNBR(
    image_stack: xr.DataArray,
    rest_start: str,
    timestep: int = 5,
) -> xr.DataArray:
    """Per-pixel dNBR.

    The absolute change in a spectral index’s value at a point in the
    restoration monitoring window from the start of the restoration monitoring
    window. The default is the change that has occurred 5 years into the
    restoration from the start of the restoration.

    Parameters
    ----------
    image_stack : xr.DataArray
        DataArray of images over which to compute per-pixel dNBR.
    rest_start : str
        The starting year of the restoration monitoring window.
    timestep : int, optional
        The timestep (years) in the restoration monitoring
        window (post rest_start) from which to evaluate absolute
        change. Default = 5.

    """
    rest_post_t = str(int(rest_start) + timestep)
    dNBR = (
        image_stack.sel(time=rest_post_t).drop_vars("time")
        - image_stack.sel(time=rest_start).drop_vars("time")
    ).squeeze("time")
    return dNBR


# TODO: P80R should be using a target recovery value like the others
@maintain_rio_attrs
def P80R(
    image_stack: xr.DataArray,
    rest_start: str,
    recovery_target: xr.DataArray,
    percent: int,
) -> xr.DataArray:
    """Extent (percent) that trajectory has reached 80% of pre-disturbance value.

    Modified metric from Y2R. Value equal to 1 indicates 80% has been reached and value more or less than 1
    indicates more or less than 80% has been reached.


    """
    post_rest = [
        date >= pd.to_datetime(rest_start) for date in image_stack.coords["time"].values
    ]
    post_rest_max = image_stack.sel(time=post_rest).max(dim=["y", "x"])

    return post_rest_max / ((percent / 100) * recovery_target)


@maintain_rio_attrs
def YrYr(
    image_stack: xr.DataArray,
    rest_start: str,
    timestep: int,
):
    dist_start = str((int(rest_start) - 1))
    dist_post_t = str(int(dist_start) + timestep)

    dist_post_t_val = image_stack.sel(time=dist_post_t)
    dist_val = image_stack.sel(time=dist_start)

    return dist_post_t_val - dist_val


@maintain_rio_attrs
def Y2R(
    image_stack: xr.DataArray,
    recovery_target: xr.DataArray,
    rest_start: str,
    rest_end: str,
    percent: int = 80,
) -> xr.DataArray:
    """Per-pixel years-to-recovery

    Parameters
    ----------
    image_stack : xr.DataArray
        Timeseries of images to compute years-to-recovery across.

    """
    reco_target = recovery_target * (percent / 100)
    post_rest = image_stack.sel(time=slice(rest_start, rest_end))
    post_rest_years = post_rest["time"].values
    possible_years_to_recovery = np.arange(len(post_rest_years))

    recovered_pixels = post_rest.where(image_stack >= reco_target)
    # NOTE: the following code was my best attempt to get "find the first year that recovered"
    # working with xarray. Likely not the best way to do it, but can't figure anything else out now.
    year_of_recovery = recovered_pixels.idxmax(dim="time")

    Y2R = xr.full_like(recovered_pixels[:, 0, :, :], fill_value=np.nan)
    for i, recovery_time in enumerate(possible_years_to_recovery):
        Y2R_t = year_of_recovery
        Y2R_t = Y2R_t.where(Y2R_t == post_rest_years[i]).notnull()
        Y2R_mask = Y2R.where(Y2R_t, False)
        Y2R = xr.where(Y2R_mask, recovery_time, Y2R)

    Y2R = Y2R.drop_vars("time")
    return Y2R


@maintain_rio_attrs
def dNBR(
    image_stack: xr.DataArray,
    rest_start: str,
    timestep: int = 5,
) -> xr.DataArray:
    """Delta-NBR

    Parameters
    ----------
    restoration_stack :
    trajectory_func : callable, optional

    """
    rest_post_t = str(int(rest_start) + timestep)
    dNBR = (
        image_stack.sel(time=rest_post_t).drop_vars("time")
        - image_stack.sel(time=rest_start).drop_vars("time")
    ).squeeze("time")
    return dNBR


@maintain_rio_attrs
def RI(
    image_stack: xr.DataArray,
    rest_start: str,
    timestep: int = 5,
) -> xr.DataArray:
    """
    Notes
    -----
    This implementation currently assumes that the disturbance period is 1 year long.
    TODO: allow for multi-year disturbances?
    """
    rest_post_t = str(int(rest_start) + timestep)
    dist_start = str(int(rest_start) - 1)
    dist_end = rest_start
    RI = (
        (
            image_stack.sel(time=rest_post_t).drop_vars("time")
            - image_stack.sel(time=rest_start)
        ).drop_vars("time")
        / (
            image_stack.sel(time=dist_start).drop_vars("time")
            - image_stack.sel(time=dist_end).drop_vars("time")
        )
    ).squeeze("time")
    return RI