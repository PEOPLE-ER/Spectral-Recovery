"""Methods for computing spectral indices.

Most functions are decorated with `compatible_with` and `requires_bands` decorators, 
which check that the input stack is compatible with the function and that the stack
contains the required bands.

Most notably, exports the `compute_indices` function, which computes a stack of
spectral indices from a stack of images and str of index names.

"""
import functools
from typing import List

import xarray as xr
from pandas import Index as pdIndex

import spyndex as spx

from spectral_recovery._utils import maintain_rio_attrs
from spectral_recovery.enums import Index, BandCommon, Platform


def compatible_with(platform: List[Platform]):
    """A decorator for assigning platform compatibility to a function.

    Parameters
    ----------
    platform : List[Platform]
        List of platforms compatible with the function.

    """
    def compatible_with_decorator(func):
        """Sub-decorator for assigning platform compatibility to a function."""

        @functools.wraps(func)
        def compatible_with_wrapper(stack, *args, **kwargs):
            for input_platform in stack.attrs["platform"]:
                if input_platform not in platform:
                    raise ValueError(
                        f"Function {func.__name__} is not compatible with platform"
                        f" {stack.attrs['platform']}. Only compatible with {platform}"
                    ) from None
            return func(stack, *args, **kwargs)

        return compatible_with_wrapper

    return compatible_with_decorator


def requires_bands(bands: List[BandCommon]):
    """A decorator for assigning band requirements to a function.

    Parameters
    ----------
    bands : List[BandCommon]
        List of bands required by the function.

    """

    def requires_bands_decorator(func):
        """Sub-decorator for assigning band requirements to a function."""

        @functools.wraps(func)
        def requires_bands_wrapper(stack, *args, **kwargs):
            for band in bands:
                if band not in stack["band"].values:
                    raise ValueError(
                        f"Function {func.__name__} requires bands {bands} but"
                        f" image_stack only contains {stack['band'].values}"
                    ) from None
            return func(stack, *args, **kwargs)

        return requires_bands_wrapper

    return requires_bands_decorator


@compatible_with(
    [
        Platform.LANDSAT_OLI,
        Platform.LANDSAT_TM,
        Platform.LANDSAT_ETM,
        Platform.SENTINEL_2,
    ]
)
@requires_bands([BandCommon.NIR, BandCommon.GREEN])
@maintain_rio_attrs
def gci(stack):
    """Compute the Green Chlorophyll Index (GCI)"""
    nir = stack.sel(band=BandCommon.NIR)
    green = stack.sel(band=BandCommon.GREEN)
    gci_v = (nir / green) - 1
    return gci_v

_indices_map = {
    Index.GCI: gci,
}


SUPPORTED_DOMAINS = ["vegetation", "burn"] 

@maintain_rio_attrs
def compute_indices(image_stack: xr.DataArray, indices: list[str], **kwargs):
    """Compute spectral indices using the spyndex package.


    Parameters
    ----------
    image_stack : xr.DataArray
        stack of images. The 'band' dimension coordinates must contain
        enums.BandCommon types.
    indices : list of str
        list of spectral indices to compute
    kwargs : dict, optional 
        Additional kwargs for wrapped spyndex.computeIndex function, like
        constant values e.g 'L = 0.5'.

    Returns
    -------
        xr.DataArray: stack of images with spectral indices stacked along
        the band dimension.

    """
    platforms = image_stack.attrs["platform"]
    if _supported_domain(indices):
        params_dict = _build_params_dict(image_stack)
        params_dict = params_dict | kwargs
        index_stack = spx.computeIndex(
            index=indices,
            params=params_dict
        )
        try:
            # rename 'index' dim to 'bands' to match tool's expected dims
            index_stack = index_stack.rename({"index": "band"})
        except ValueError:
            # computeIndex will not return an index dim if only 1 index passed
            index_stack = index_stack.expand_dims(dim={"band": indices})
    return index_stack

def _supported_domain(indices: list[str]):
    """ Determine whether indices application domains are supported by tool.
    
    Parameters
    ----------
    indices : list of str
        list of indices
    
    Raises
    ------
    ValueError
        If any index has an unsupported application domain.
    """
    for i in indices:
        if spx.indices[i].application_domain not in SUPPORTED_DOMAINS:
            raise ValueError(
                f"only application domain 'vegetation' and 'burn' are supported (index {i} has application domain '{spx.indices[i].application_domain}')"
            ) from None
    return True

def _compatible_platform(indices: list[str], platforms: list[str]):
    """ Determine whether platform and selected indices are compatible.
    
    Parameters
    ----------
    indices : list of str
        list of indices
    platforms : list of str
        list of platforms
    
    Raises
    ------
    ValueError
        If an index is compatible with any of the platforms.
    """
    for i in indices:
        compatible_platforms = spx.indices[i].platforms
        compatible = False
        for p in platforms:
            if p in compatible_platforms:
                compatible = True
        if not compatible:
            raise ValueError(
                    f"incompatible platforms for index {i}. {i} requires any of {spx.indices[i].platforms} ({platforms} provided)"
                ) from None
    return True
      


def _build_params_dict(image_stack: xr.DataArray):
    """Build dict of standard names and slices required by computeIndex.
    
    Slices will be taken along the band dimension of image_stack,
    selecting for each of the standard band/constant names that computeIndex
    accepts. Any name that is not in image_stack will not be included
    in the dictionary.

    Parameters
    ----------
    image_stack : xr.DataArray
        DataArray from which to take slices. Must have a band
        dimension and band coordinates value should be standard names
        for the respective band. For more info, see here:
        https://github.com/awesome-spectral-indices/awesome-spectral-indices

    Returns
    -------
    band_dict : dict    
        Dictionary mapping standard names to slice of image_stack.

    """
    standard_names = list(spx.bands)
    params_dict = {}
    for standard in standard_names:
        try:
            band_slice = image_stack.sel(band=standard)
            params_dict[standard] = band_slice
        except KeyError:
            continue

    return params_dict




