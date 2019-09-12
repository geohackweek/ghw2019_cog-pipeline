"""maap-tiler: utility functions."""

import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling, ColorInterp
from rasterio.warp import transform_bounds

from rio_tiler.utils import get_vrt_transform, has_alpha_band, _stats


def get_area_stats(
    src,
    bounds,
    max_img_size=512,
    indexes=None,
    nodata=None,
    resampling_method="bilinear",
    bbox_crs="epsg:4326",
    histogram_bins=20,
    histogram_range=None,
):
    """
    Read data and mask.

    Attributes
    ----------
    srd_dst : rasterio.io.DatasetReader
        rasterio.io.DatasetReader object
    bounds : list
        bounds (left, bottom, right, top)
    tilesize : int
        Output image size
    indexes : list of ints or a single int, optional, (defaults: None)
        If `indexes` is a list, the result is a 3D array, but is
        a 2D array if it is a band index number.
    nodata: int or float, optional (defaults: None)
    resampling_method : str, optional (default: "bilinear")
         Resampling algorithm
    histogram_bins: int, optional
        Defines the number of equal-width histogram bins (default: 10).
    histogram_range: str, optional
        The lower and upper range of the bins. If not provided, range is simply
        the min and max of the array.

    Returns
    -------
    out : array, int
        returns pixel value.

    """
    if isinstance(indexes, int):
        indexes = [indexes]
    elif isinstance(indexes, tuple):
        indexes = list(indexes)

    with rasterio.open(src) as src_dst:
        bounds = transform_bounds(bbox_crs, src_dst.crs, *bounds, densify_pts=21)

        vrt_params = dict(add_alpha=True, resampling=Resampling[resampling_method])

        indexes = indexes if indexes is not None else src_dst.indexes
        nodata = nodata if nodata is not None else src_dst.nodata

        def _get_descr(ix):
            """Return band description."""
            name = src_dst.descriptions[ix - 1]
            if not name:
                name = "band{}".format(ix)
            return name

        band_descriptions = [(ix, _get_descr(ix)) for ix in indexes]

        vrt_transform, vrt_width, vrt_height = get_vrt_transform(
            src_dst, bounds, bounds_crs=src_dst.crs
        )
        vrt_params.update(
            dict(transform=vrt_transform, width=vrt_width, height=vrt_height)
        )

        width = round(vrt_width) if vrt_width < max_img_size else max_img_size
        height = round(vrt_height) if vrt_height < max_img_size else max_img_size
        out_shape = (len(indexes), width, height)
        if nodata is not None:
            vrt_params.update(dict(nodata=nodata, add_alpha=False, src_nodata=nodata))

        if has_alpha_band(src_dst):
            vrt_params.update(dict(add_alpha=False))

        with WarpedVRT(src_dst, **vrt_params) as vrt:
            arr = vrt.read(out_shape=out_shape, indexes=indexes, masked=True)
            if not arr.any():
                return None, band_descriptions

            params = {}
            if histogram_bins:
                params.update(dict(bins=histogram_bins))
            if histogram_range:
                params.update(dict(range=histogram_range))

            stats = {
                indexes[b]: _stats(arr[b], **params)
                for b in range(arr.shape[0])
                if vrt.colorinterp[b] != ColorInterp.alpha
            }

    return stats, band_descriptions
