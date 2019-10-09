import multiprocessing
import numpy
import os
import rasterio
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import argparse

def generate_cog(sourcefile, options = {}):
    try: 
        # Create GTiff from source
        gtiff_translate_output = f"{sourcefile}.tif"
        sourcefile_format = 'NETCDF'
        sourcefile_bandname = options.get('bandname')
        command = "gdal_translate"
        input_arg = f"{sourcefile_format}:{sourcefile}:{sourcefile_bandname}"
        output_arg = f"-of GTiff {gtiff_translate_output}"
        os.system(f"{command} {input_arg} {output_arg}")

        # Reproject GeoTiff
        reprojected_geotiff = f"{sourcefile}_reprojected.tif"
        command = "gdalwarp"
        input_arg = gtiff_translate_output
        target_spatial_reference = '+proj=longlat +ellps=WGS84'
        output_arg = f"{reprojected_geotiff} -t_srs '{target_spatial_reference}'"
        os.system(f"{command} {input_arg} {output_arg}")

        # Create Cloud-Optimized GTiff
        MAX_THREADS = int(os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5))
        in_tif = os.path.join(reprojected_geotiff)
        out_cog = os.path.join(f"{sourcefile}.cog.tif")

        config = dict(
            NUM_THREADS=MAX_THREADS,
            GDAL_TIFF_OVR_BLOCKSIZE=os.environ.get("GDAL_TIFF_OVR_BLOCKSIZE", "128"),
        )

        source = rasterio.open(in_tif)
        profile = cog_profiles.get("deflate")
        profile.update({"blockxsize": 256, "blockysize": 256})

        nodatavalue = numpy.nan if numpy.isnan(source.nodatavals[0]) else source.nodatavals[0]
        cog_translate(
            in_tif,
            out_cog,
            profile,
            nodata=nodatavalue,
            overview_resampling="bilinear",
            config=config,
            quiet=True
        )

        # Cleanup
        os.system(f"rm {gtiff_translate_output}")
        os.system(f"rm {reprojected_geotiff}")
        return out_cog
    except Exception as err:
        print(f"Caught exception {err}\n")
        return None

if __name__ == "__main__":
    """
    args:
    filename - file to use in generating cog
    --src_fmt - optional, default NETCDF
    --bandnames - required, comma-seperated list of bands
    --reproject - optional, default 'True'
    --nodata - nodata value, default numpy.nan or source.nodatavals[0]
    """
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('filename', type=str, help='file for generating cog')
    parser.add_argument('--bandname', help='required, name of band to generate cog')

    args = parser.parse_args()
    options = {
      'bandname': args.bandname
    }
    generate_cog(args.filename, options)

# # For testing
# python file-to-cog.py 'L8_001_004_016_2014_080_2014_096_v1.1.nc' --bandname corr
