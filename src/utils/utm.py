"""Pure-numpy Transverse Mercator (UTM) forward projection, WGS84 ellipsoid.
Used because pyproj/GDAL are not available in this environment. For production,
replace with pyproj.Transformer (EPSG:4326 -> EPSG:32632) which gives identical
results to <1 cm; this implementation is the standard Snyder/UTM forward formula
and is accurate to a few cm within a single zone, which is more than sufficient
for buffer distances and nearest-neighbour spatial weights at settlement scale.
"""
import numpy as np

A = 6378137.0          # WGS84 semi-major axis
F = 1 / 298.257223563  # WGS84 flattening
K0 = 0.9996
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)

def latlon_to_utm(lat_deg, lon_deg, zone=32):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    lon0 = np.radians((zone - 1) * 6 - 180 + 3)
    N = A / np.sqrt(1 - E2 * np.sin(lat) ** 2)
    T = np.tan(lat) ** 2
    C = EP2 * np.cos(lat) ** 2
    Aterm = np.cos(lat) * (lon - lon0)
    M = A * (
        (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256) * lat
        - (3 * E2 / 8 + 3 * E2 ** 2 / 32 + 45 * E2 ** 3 / 1024) * np.sin(2 * lat)
        + (15 * E2 ** 2 / 256 + 45 * E2 ** 3 / 1024) * np.sin(4 * lat)
        - (35 * E2 ** 3 / 3072) * np.sin(6 * lat)
    )
    easting = K0 * N * (
        Aterm + (1 - T + C) * Aterm ** 3 / 6
        + (5 - 18 * T + T ** 2 + 72 * C - 58 * EP2) * Aterm ** 5 / 120
    ) + 500000.0
    northing = K0 * (
        M + N * np.tan(lat) * (
            Aterm ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * Aterm ** 4 / 24
            + (61 - 58 * T + T ** 2 + 600 * C - 330 * EP2) * Aterm ** 6 / 720
        )
    )
    return easting, northing
