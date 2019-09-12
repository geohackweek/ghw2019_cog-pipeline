"""Setup ard-tiler."""

from setuptools import setup, find_packages


# Runtime requirements.
inst_reqs = [
    "lambda-proxy~=4.1",
    "rio-color",
    "rio_rgbify",
    "rio-tiler>=1.2.7",
    "rio-tiler-mosaic",
    "rio-tiler-mvt",
]

vt = "vector-tile-base @ git+https://github.com/mapbox/vector-tile-base.git@93c87d370dd68d3710bcf20c55d336c32750246e"
extra_reqs = {
    "test": ["pytest", "pytest-cov", vt]
}

setup(
    name="tiler",
    version="0.0.1",
    description=u"""""",
    long_description=u"",
    python_requires=">=3",
    classifiers=["Programming Language :: Python :: 3.6"],
    keywords="",
    author=u"Vincent Sarago",
    author_email="vincent@developmentseed.org",
    url="",
    license="BSD",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
    entry_points={"console_scripts": ["tiler = tiler.scripts.cli:run"]},
)
