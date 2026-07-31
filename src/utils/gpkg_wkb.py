"""Minimal GeoPackage WKB polygon/multipolygon parser (no GDAL/pyproj/shapely available)."""
import struct

def parse_gpkg_geom(blob):
    """Return list of polygons; each polygon = list of rings; each ring = list of (x,y)."""
    assert blob[0:2] == b'GP'
    flags = blob[3]
    envelope_code = (flags >> 1) & 0x07
    envelope_bytes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[envelope_code]
    header_len = 8 + envelope_bytes
    wkb = blob[header_len:]
    return _parse_wkb(wkb)

def _read_pts(buf, off, n, endian):
    pts = []
    for i in range(n):
        x, y = struct.unpack_from(endian + 'dd', buf, off)
        pts.append((x, y))
        off += 16
    return pts, off

def _parse_wkb(buf):
    order = buf[0]
    endian = '<' if order == 1 else '>'
    geom_type = struct.unpack_from(endian + 'I', buf, 1)[0]
    off = 5
    polygons = []
    if geom_type == 3:  # Polygon
        num_rings = struct.unpack_from(endian + 'I', buf, off)[0]; off += 4
        rings = []
        for _ in range(num_rings):
            n = struct.unpack_from(endian + 'I', buf, off)[0]; off += 4
            pts, off = _read_pts(buf, off, n, endian)
            rings.append(pts)
        polygons.append(rings)
    elif geom_type == 6:  # MultiPolygon
        num_poly = struct.unpack_from(endian + 'I', buf, off)[0]; off += 4
        for _ in range(num_poly):
            p_order = buf[off]
            p_endian = '<' if p_order == 1 else '>'
            p_type = struct.unpack_from(p_endian + 'I', buf, off + 1)[0]
            off += 5
            num_rings = struct.unpack_from(p_endian + 'I', buf, off)[0]; off += 4
            rings = []
            for _ in range(num_rings):
                n = struct.unpack_from(p_endian + 'I', buf, off)[0]; off += 4
                pts, off = _read_pts(buf, off, n, p_endian)
                rings.append(pts)
            polygons.append(rings)
    else:
        raise ValueError(f"Unsupported geometry type {geom_type}")
    return polygons
