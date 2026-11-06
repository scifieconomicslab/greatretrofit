"""The paperdolls scene frame (ingest/geo.py LocalFrame): tangent plane at area.origin, x east, y south, then rotated by -rotation_deg.
Re-implemented here (paperdolls is read-only for this repo); keep in step with LocalFrame."""
import math

R_EARTH = 6371008.8
DEG = math.pi / 180.0


class Frame:
    def __init__(self, area):
        self.lat0, self.lon0 = area["origin"]["lat"], area["origin"]["lon"]
        self.rot = area.get("rotation_deg", 0.0)
        self.kx = R_EARTH * math.cos(self.lat0 * DEG) * DEG
        self.ky = R_EARTH * DEG
        a = self.rot * DEG
        self.c, self.s = math.cos(a), math.sin(a)

    def xy(self, lat, lon):
        x = (lon - self.lon0) * self.kx
        y = -(lat - self.lat0) * self.ky
        return (x * self.c + y * self.s, -x * self.s + y * self.c)

    def latlon(self, xr, yr):
        x = xr * self.c - yr * self.s
        y = xr * self.s + yr * self.c
        return (self.lat0 - y / self.ky, self.lon0 + x / self.kx)
