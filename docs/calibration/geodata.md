# Geodata: building heights and terrain for Jette

Tags: **[R]** = read from the metadata record / file / feed on 2026-11-06; **[S]** = search summary only. Jette's municipal (NIS) code is 21010.

## (a) Building heights / storeys

### UrbIS – 3D Constructions (Paradigm, Brussels Region) — **confidence: high**
- Contents [R]: individually modelled 3D buildings and civil-engineering structures in four classes (3D buildings, building faces, 3D structures, structure faces), made by photogrammetry from aerial photos and plans, level of detail equivalent to LoD2 (CityGML). Face types include ROOFSURFACE. Updated monthly.
- Attributes in the technical spec [R]: `inspire_Id` (stable building ID), `bu2d_Id` (ID of the 2D building), `detailsLevel` (LoD 2), `beginLife`/`endLife`. The attribute list I read has **no height or storey-count field**; height must be computed from Z coordinates of the 3D geometry. No height accuracy is given in the metadata.
- Metadata: https://geobru-geonetwork.irisnet.be/geonetwork/srv/api/records/e9ec2aa4-cffd-11ee-bccc-00090ffe0001 ; spec: https://urbisdownload.datastore.brussels/UrbIS/TechSpec/3D_TechSpec_FR20240409.pdf [R].
- Licence [R]: metadata cites CC0 1.0 and "freely downloadable"; access/use constraints are also marked "Other restrictions". The record is internally ambiguous — confirm with Paradigm (irisline@paradigm.brussels) before publishing derived data.
- Download [R]: ATOM feed https://urbisdownload.datastore.brussels/atomfeed/e9ec2aa4-cffd-11ee-bccc-00090ffe0001-en.xml lists per-commune zips in SHP, DWG, SKP and GPKG. Jette GeoPackage, latest edition in the feed (HTTP 200, 16.7 MB): `https://urbisdownload.datastore.brussels/UrbIS/Vector/M8/UrbIS-Buildings3D/GPKG/UrbISBuildings3D_31370_GPKG_21010_20261003.zip`. The spec says the 3D-building and 3D-structure classes are not supported in GeoPackage, so the GPKG probably holds only the face classes; **I did not unzip it** — check, or use the SHP/SKP variant.
- CRS: EPSG:31370 (Belgian Lambert 72); reproject for OSM/paperdolls.

### UrbIS – Landscape (3D buildings + terrain) — **confidence: medium**
Combines 3D Constructions with the terrain model; distributed as SketchUp; created/revised 2024-09-01; same CC0 / "Other restrictions" ambiguity [R] https://geobru-geonetwork.irisnet.be/geonetwork/srv/api/records/713171e6-65e3-11ef-b378-010101010000 . Good for visual checks, not attributes.

### Brussels "Built density" dataset — **confidence: low-medium (not opened)**
A Geobru record dated 2026-07-06 lists indicators including **average number of storeys and maximum building height**, derived from field surveys, UrbIS parcels/buildings and UrbIS 3D buildings; downloads in SHP/GPKG/JSON/GML [S]. Spatial unit and licence unconfirmed.

### Other height sources
- 2021 LiDAR (below): heights as DSM minus DTM per footprint; heavy processing.
- Copernicus Urban Atlas building height 2012 [S]: old and coarse; not recommended.
- OSM `building:levels` / `height` coverage in Jette: not measured.
- Per-building *storey counts* as an open attribute: **not found**; estimate as height / ~3 m with a stated error.

### Joining to OpenStreetMap buildings — **feasible**
OSM key `ref:databrussels` holds the UrbIS identifier; for buildings it is the `INSPIRE_ID` field, status "imported" [R] https://wiki.openstreetmap.org/wiki/Key:ref:databrussels . The 3D dataset carries `inspire_Id` and `bu2d_Id` [R], so join on ID where the OSM building has the tag. Where OSM merged or split buildings relative to UrbIS, mappers use `building:part=yes` with the ID, so expect many-to-one cases; for untagged buildings use spatial overlay after reprojecting. The wiki documents no licence/permission for the import. Share of Jette buildings carrying the tag: not measured.

## (b) Terrain / elevation

### Brussels DTM via UrbIS raster services — **confidence: medium**
- The Region's WMS "View service – UrbIS raster" has layers `DTM` (Digital Terrain Model), `Relief`, `Hillshade` and orthophotos 2004–2024 [R, GetCapabilities] https://geoservices-grid.irisnet.be/geoserver/urbisgrid/ows?Service=WMS&Version=1.3.0&Request=GetCapabilities . CRS EPSG:31370 and EPSG:3812; CC0 cited with the same ambiguity [R] (record 99e17c00-6b3a-11ed-aa8d-010101010000). WMS returns rendered images only. The raster download and its cell size: **not found** in the records I read — look under https://datastore.brussels/web/urbis-download. An older INSPIRE-listed DTM is a 3 m grid from 2012 (`UrbDTM_GridCoverage.GRID_2012_3m.zip`) [S].

### Airborne LiDAR 2021, Brussels — **best raw source**
Record "Airborne LiDAR pointcloud – 2021" [R] https://geobru-geonetwork.irisnet.be/geonetwork/srv/api/records/ff1124e1-424e-11ee-b156-00090ffe0001 : flown 9 Oct 2021 (RIEGL VQ-1560 II), average 67 points/m², LAS, EPSG:31370, whole Region; no access limitation; use under **CC BY 4.0** (attribution). Download via https://datastore.brussels/web/urbis-download or ATOM feed https://urbisdownload.datastore.brussels/atomfeed/ff1124e1-424e-11ee-b156-00090ffe0001-en.xml . Vertical accuracy not stated; the record carries an unexplained "not conformant" entry dated 2008. Large files: clip to Jette first.

### Alternatives
- Flemish DHMV II (2013–2015) 1 m DSM/DTM also covers Brussels [S] https://metadata.vlaanderen.be/srv/api/records/242ddabc-3cbc-44f0-9623-bee874b29549 — older.
- Copernicus DEM (30 m) and SRTM: not opened here; far coarser than street scale, fallback only.

## Recommendations
- **(a) Heights: UrbIS 3D Constructions for Jette, joined via `inspire_Id` ↔ OSM `ref:databrussels`.** Official per-building LoD2 geometry, public-domain label, monthly updates, and an ID that OSM already carries. Compute height as roof max Z − ground Z; spot-check a few dozen buildings against LiDAR since no accuracy is published.
- **(b) Terrain: a DTM raster from the 2021 LiDAR (CC BY 4.0, 67 pts/m²) at 1–2 m**, unless the UrbIS DTM download turns out to be ≤1 m and current — check its cell size first and use it if so (no processing needed). SRTM/Copernicus at 30 m cannot resolve Jette's streets.
- Open item: confirm the CC0 vs "Other restrictions" wording with Paradigm before showing derived data to policymakers.
