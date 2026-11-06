# Geodata acquired for the Jette scene

Everything is under `data/raw/` (gitignored, never committed). Fetched on **2026-11-06** from Brussels Region open-data services; no key, registration or form was needed for any of it. Total about 77 MB of the 300 MB allowed (the 2021 LiDAR tiles are 2.3 GB each and were not fetched, see below). Requests were made one at a time, 3 s apart; one tile needed a retry after an HTTP 500.

## 1. UrbIS Digital Terrain Model, 1 m (elevation)

| | |
|---|---|
| What | Digital terrain model (ground, not buildings or trees), 1 m cells, float64, EPSG:31370, heights in metres. Derived from the 2021-10-09 airborne LiDAR (dataset date in the record) |
| URL | `https://geoservices-grid.irisnet.be/geoserver/urbisgrid/ows` (OGC WCS 2.0.1, `coverageId=urbisgrid__DTM`, `format=image/tiff&geotiff:compression=Deflate`, `subset=X(..)&subset=Y(..)`), 16 tiles of up to 1 km x 1 km covering x 144900 to 148200, y 172600 to 176100 (EPSG:31370) |
| Script | `scripts/geodata/fetch_dtm.py` (reproduces the download and writes `data/raw/dtm_wcs/manifest.json`) |
| Licence | The dataset record (Geobru `1d7bd49d-fe83-4388-af85-6f5dc8ec7909`) and the view-service record (`99e17c00-6b3a-11ed-aa8d-010101010000`) both state: "Creative Commons (CC-0) - no conditions for reuse, the data is in the public domain"; the dataset record also says "no restriction on public access". Publisher: Paradigm / CIRB-CIBG. (The survey's "other restrictions" wording did not appear in the licence text of these two records when searched on 2026-11-06; it may sit in a field that was not checked, so the CC0 confirmation with Paradigm is still advisable before public release.) |
| Date fetched | 2026-11-06 |
| Size | 59.9 MB in 16 files |
| Quirk | Ground the service has no data for (outside the Region: the north-west corner of the box, in Flanders) comes back as exactly `0.0`, not NaN. `make_elevation.py` treats exact 0 as NoData (2.6% of the box) |

| file | size | sha256 |
|---|---|---|
| `dtm_144900_172600_145900_173600.tif` | 5.18 MB | `644217d917d76a61614d0268926cf4de57423bf6a1a858e0f7cbf37d321f10d5` |
| `dtm_145900_172600_146900_173600.tif` | 5.49 MB | `c089cf4582748b97e9020a9ea295bb0a480b27c8336477f40e69155e760d4851` |
| `dtm_146900_172600_147900_173600.tif` | 5.17 MB | `36cb5103caad345cbfdb172218397d55c8a391a5d551bc38e507c3e99e5771fa` |
| `dtm_147900_172600_148200_173600.tif` | 1.65 MB | `84398572e4cbecf89796e56cef605866f5c8d6dc039e2febd987dc43bbd8a538` |
| `dtm_144900_173600_145900_174600.tif` | 4.91 MB | `717c66c2557b2918dbb4e444d20e6f01d1eae0f2e1904cd917393175ee48606d` |
| `dtm_145900_173600_146900_174600.tif` | 4.59 MB | `d697f75d2606bbe7ceb85e8eb288740ec826a359b04c0f05ea1710bd41633ed3` |
| `dtm_146900_173600_147900_174600.tif` | 5.31 MB | `4bf09cd41aa8fff985e3f51d8cf4392b0f62e45acf4eff00ddfcb3031d422b55` |
| `dtm_147900_173600_148200_174600.tif` | 1.48 MB | `88d0bf1b6b7616a5a0f960cfbd7f62c4810ea09a8da827ad8b17626b889af69c` |
| `dtm_144900_174600_145900_175600.tif` | 5.90 MB | `0bed25eb1d513d7e40fda9122c3187f1c80b850c7a72d880c10625a86e0612fd` |
| `dtm_145900_174600_146900_175600.tif` | 5.56 MB | `b4e32a7db5a6dcee5697177c6b0f83e539b9064f78382b45e8c4de311ba0271a` |
| `dtm_146900_174600_147900_175600.tif` | 5.62 MB | `702d053bd078c48282e884756fe6479f84e021c94c5cb556577794baf59461fc` |
| `dtm_147900_174600_148200_175600.tif` | 1.48 MB | `184669a20c6dec106453d8ff41a31a50e527d83bcbe56634e848d7bc138c3887` |
| `dtm_144900_175600_145900_176100.tif` | 1.16 MB | `d552b58668b78f277435c768a309cf9469fb1d564b13b13c68c3002007e0dd62` |
| `dtm_145900_175600_146900_176100.tif` | 2.65 MB | `1dedaf5fe2663ff962d54264b26fffc28cd4157ed4f12239228c05fb88bc47a0` |
| `dtm_146900_175600_147900_176100.tif` | 2.89 MB | `3cc5571f9253dbd86587d2db154072e524c99e7ee50b9cf1b10a02fe231c3c39` |
| `dtm_147900_175600_148200_176100.tif` | 0.82 MB | `f282d6941e2225ec5f82ec358b259ee002367df126a4899709b63fc61c43105d` |

## 2. UrbIS 3D Buildings, Jette (building heights)

| | |
|---|---|
| What | LoD2 building solids as faces (`BuildingFaces`, 162,458 faces, 10,105 solids; plus `EngineeringWorkFaces`, 34 faces), EPSG:31370, MultiPolygon Z. Edition 2026-10-03 (`BEGINLIFE` of the faces 2023-05-02 onward) |
| URL | `https://urbisdownload.datastore.brussels/UrbIS/Vector/M8/UrbIS-Buildings3D/GPKG/UrbISBuildings3D_31370_GPKG_21010_20261003.zip` (listed in the ATOM feed `https://urbisdownload.datastore.brussels/atomfeed/e9ec2aa4-cffd-11ee-bccc-00090ffe0001-en.xml`) |
| Licence | Geobru record `e9ec2aa4-cffd-11ee-bccc-00090ffe0001`: "Creative Commons (CC-0) - no conditions for reuse, the data is in the public domain" (stated in the licence text of the record; same note as above about the survey's "other restrictions") |
| Date fetched | 2026-11-06 |
| Size | 16,733,216 bytes (zip), 84 MB unzipped |
| sha256 (zip) | `ec75a554c2daba1b63f061ee7e056fd7719345a28c57163ede9bc05addcf461c` |
| sha256 (gpkg) | `2fb8be3b90e062078631176f9ea461daca6bae93471282369019444ccdd7699b` (`UrbISBuildings3D_21010.gpkg`) |

## Sources looked at and not fetched

| source | why not |
|---|---|
| Airborne LiDAR 2021 point cloud (ATOM feed `ff1124e1-424e-11ee-b156-00090ffe0001`) | one km tile (`PointCloud_31370_LAS_142167_20210910.zip`) is 2,321,270,524 bytes by HTTP HEAD, far over the cap; the DTM above is derived from the same flight and needs no processing. CC BY 4.0 per the survey (attribution) |
| UrbIS DTM 2021 as downloadable tiles (ATOM feed `1d7bd49d-fe83-4388-af85-6f5dc8ec7909-en.xml`, files `DTM_31370_TIFF_<tile>_20211009_50.zip`) | the WCS already gave 1 m; the `_50` suffix may mean 0.5 m, not checked. Sizes seen by HEAD: 7 KB to 11 MB per tile |
| OSM `ref:databrussels` as a join key | only 36 of 10,132 OSM building ways in the cached extract carry it, so the join is spatial |
| Copernicus / SRTM | not needed |
