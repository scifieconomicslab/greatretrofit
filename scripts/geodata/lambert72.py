"""Belgian Lambert 72 (EPSG:31370) <-> WGS84 lon/lat, pure Python, no PROJ.

EPSG:31370 = Lambert Conic Conformal (2SP) on the International 1924 ellipsoid (datum BD72).
  lat_1 = 51.1666672333, lat_2 = 49.8333339, lat_0 = 90, lon_0 = 4.3674867, x_0 = 150000.013, y_0 = 5400088.438
BD72 -> WGS84 is the 7-parameter Helmert of EPSG:15739 (position vector; dX -106.8686, dY 52.2977, dZ -103.7239,
rX 0.3366", rY -0.457", rZ 1.8422", dS -1.2747 ppm). The official transformation uses the NGI grid (about 0.1 m);
the Helmert is good to roughly 1 m, which is far below the 25 m terrain grid this feeds. Checked against pyproj (PROJ, same Helmert) at two points: agrees to 2 mm; see
tests/test_geodata_lambert.py.
"""
import math

DEG = math.pi / 180.0
# International 1924
A_INT, F_INT = 6378388.0, 1 / 297.0
# WGS84
A_WGS, F_WGS = 6378137.0, 1 / 298.257223563

LAT1, LAT2, LAT0, LON0 = 51.1666672333 * DEG, 49.8333339 * DEG, 90.0 * DEG, 4.3674867 * DEG
X0, Y0 = 150000.013, 5400088.438

HELMERT = dict(dx=-106.8686, dy=52.2977, dz=-103.7239,
               rx=0.3366 / 3600 * DEG, ry=-0.457 / 3600 * DEG, rz=1.8422 / 3600 * DEG, ds=-1.2747e-6)


def _e(f):
    return math.sqrt(2 * f - f * f)


def _m(phi, e):
    return math.cos(phi) / math.sqrt(1 - (e * math.sin(phi)) ** 2)


def _t(phi, e):
    s = e * math.sin(phi)
    return math.tan(math.pi / 4 - phi / 2) / ((1 - s) / (1 + s)) ** (e / 2)


_E = _e(F_INT)
_N = (math.log(_m(LAT1, _E)) - math.log(_m(LAT2, _E))) / (math.log(_t(LAT1, _E)) - math.log(_t(LAT2, _E)))
_F = _m(LAT1, _E) / (_N * _t(LAT1, _E) ** _N)
_R0 = A_INT * _F * _t(LAT0, _E) ** _N          # lat_0 = 90: t = 0, so rho0 = 0


def _geodetic_to_ecef(lat, lon, h, a, f):
    e2 = 2 * f - f * f
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    return ((n + h) * math.cos(lat) * math.cos(lon), (n + h) * math.cos(lat) * math.sin(lon), (n * (1 - e2) + h) * math.sin(lat))


def _ecef_to_geodetic(x, y, z, a, f):
    e2 = 2 * f - f * f
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - e2))
    for _ in range(8):
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lat = math.atan2(z + e2 * n * math.sin(lat), p)
    return lat, lon


def _helmert(x, y, z, sign=1):
    h = HELMERT
    s, rx, ry, rz = sign * h["ds"], sign * h["rx"], sign * h["ry"], sign * h["rz"]
    dx, dy, dz = sign * h["dx"], sign * h["dy"], sign * h["dz"]
    # position vector convention
    return (x + dx + s * x - rz * y + ry * z, y + dy + rz * x + s * y - rx * z, z + dz - ry * x + rx * y + s * z)


def lambert72_to_lonlat(x, y):
    """(easting, northing) in EPSG:31370 -> (lon, lat) degrees, WGS84."""
    dx, dy = x - X0, _R0 - (y - Y0)
    rho = math.copysign(math.hypot(dx, dy), _N)
    theta = math.atan2(math.copysign(1, _N) * dx, math.copysign(1, _N) * dy)
    t = (rho / (A_INT * _F)) ** (1 / _N)
    lat = math.pi / 2 - 2 * math.atan(t)
    for _ in range(12):
        s = _E * math.sin(lat)
        lat = math.pi / 2 - 2 * math.atan(t * ((1 - s) / (1 + s)) ** (_E / 2))
    lon = theta / _N + LON0
    X, Y, Z = _geodetic_to_ecef(lat, lon, 0.0, A_INT, F_INT)
    lat2, lon2 = _ecef_to_geodetic(*_helmert(X, Y, Z, +1), A_WGS, F_WGS)
    return lon2 / DEG, lat2 / DEG


def lonlat_to_lambert72(lon, lat):
    """(lon, lat) degrees WGS84 -> (easting, northing) EPSG:31370."""
    X, Y, Z = _geodetic_to_ecef(lat * DEG, lon * DEG, 0.0, A_WGS, F_WGS)
    la, lo = _ecef_to_geodetic(*_helmert(X, Y, Z, -1), A_INT, F_INT)
    rho = A_INT * _F * _t(la, _E) ** _N
    th = _N * (lo - LON0)
    return X0 + rho * math.sin(th), Y0 + _R0 - rho * math.cos(th)
