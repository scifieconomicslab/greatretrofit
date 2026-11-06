# Geodata: building heights and terrain for Jette

**The first section below ("Verification update") records what was actually downloaded and checked on 2026-11-06; the survey that follows it was written before that and some of its open items are now closed.**

Tags: **[R]** = read from the metadata record / file / feed on 2026-11-06; **[S]** = search summary only. Jette's municipal (NIS) code is 21010.

## Verification update (2026-11-06, geodata session)

The survey's claims were checked by downloading the data. Sources, hashes and licence text are in `geodata-acquired.md`; code in `scripts/geodata/`, tests in `tests/geodata/` (`.venv/bin/python -m pytest tests/geodata`).

| survey claim | result |
|---|---|
| UrbIS 3D GPKG for Jette is 16.7 MB and may hold only face classes | **Confirmed.** `BuildingFaces` (162,458 faces) and `EngineeringWorkFaces` (34). No solid layer, no height or storey field. 10,105 building solids (`BUSOLID_ID`), each with a GROUNDSURFACE, ROOFSURFACE and WALLSURFACE faces with Z. `INSPIRE_ID` is the *face* id, not the building's |
| Height must be computed from Z | **Done** (`urbis3d.py`): ridge height = highest roof Z minus mean ground Z; eave height = area-weighted 20th percentile of roof-face Z minus ground. Median ridge height 12.9 m, 90th percentile 17.6 m; towers up to about 80 m |
| Join on `inspire_Id` / OSM `ref:databrussels` | **Not usable here.** 36 of 10,132 OSM building ways in the Jette extract carry the tag and the GPKG's ids are face ids. The join is spatial (below) |
| Licence ambiguity CC0 vs "Other restrictions" | **Partly resolved.** The licence text of the 3D, DTM-dataset and raster-view records all read CC0 ("no conditions for reuse, public domain"). The "other restrictions" field was not found again. Confirmation from Paradigm is still advisable before wide publication |
| DTM raster download and cell size "not found" | **Found: the Region's public WCS serves the DTM at 1 m** (`urbisgrid__DTM`, EPSG:31370, no key; WMS returns images only, WCS returns the float heights). Also downloadable as tiles from the DTM ATOM feed. Dataset date 2021-10-09, from the LiDAR flight |
| 2021 LiDAR is the best raw source, CC BY 4.0 | **Not fetched:** one tile is 2.3 GB. The 1 m DTM is the same flight already processed |
| Vertical accuracy | **Not stated by the publisher; measured only as a mutual check.** UrbIS 3D ground Z is a median **1.3 m below** the DTM at the building (5th to 95th percentile -2.5 to -0.7 m, 12% within 1 m). A steady offset with a narrow spread means the two products do not share a vertical reference, or the 3D ground face sits below the DTM. Not resolved. It does not affect the pictures (the renderer's building height is relative to its own ground), but absolute heights from the two sources must not be mixed |
| Built density dataset (storeys average) | not opened |

### Result: heights

Scene 9,214 OSM buildings against 10,105 UrbIS solids (`build/jette-scene-enriched-report.json` after `scripts/geodata/build_enriched.sh`):

| | |
|---|---|
| matched and applied | **9,074 (98.5%)**: 9,051 good (at least half the OSM footprint inside one solid, no rival), 23 multi (several solids whose heights agree within 1.5 m) |
| ambiguous (several solids, heights disagree) | 21, left as OSM |
| weak (30 to 50% overlap, nothing else) | 13, left as OSM |
| unmatched | 106, left as OSM |
| UrbIS solids matched by more than one OSM building | 47 (OSM split a building UrbIS keeps whole); 1,081 solids used by none, median 5.5 m2 (sheds under the scene's 8 m2 cut) |
| **storeys assumed** | **9,101 of 9,214 (98.8%) before, 140 (1.5%) after** (113 OSM-tagged storeys kept, 22 type default, 118 global default among the unmatched/ambiguous) |
| OSM `building:levels` against UrbIS-derived storeys (113 tagged, all matched) | 44 equal, 95 within one storey, mean difference -0.07. The derived count is therefore consistent with local mappers' own counts to one storey in 84% of cases |

Storeys are derived as `round(eave height / 3.0 m)`, minimum 1; the real error is about one storey (ground floors are taller, attics and mansards are counted by the roof rule, flat roofs with parapets read a little high). 24% of applied buildings come out at 1 storey: garages, sheds and low extensions, as expected. Written onto each building: `height` (ridge, m), `height_eave`, `ground_z`, `height_source: "urbis3d"`, `height_match`, `urbis_id`, `height_cover`, `levels`, `levels_assumed: false`, `osm.levels_source: "urbis3d"`.

**paperdolls ignores `height`.** The renderer's drawn height is `levels x storeyH` (`viz/vizlib.js`, `entityHeight`); `height` is only validated. So the heights reach the picture through `levels` rounded to whole storeys with an archetype storey height of about 3 m. Owner: paperdolls (use `height` when `levels_source` is a measured one, and set the roof from `height - height_eave`).

### Result: relief

`make_elevation.py` writes a 848 x 892 float32 EPSG:4326 GeoTIFF at 4 m (2 MB) from the 1 m tiles: heights 21.8 to 87.0 m, 65 m of relief over the commune, the Molenbeek valley in the south-west rising to the north-east. `paperdolls ingest --elevation` accepted it as is: all 9,214 buildings and 1,318 of 1,320 roads got `z` (the grid covers 89% of the scene box, the rest is the margin outside the Region).

Images (`docs/images/geodata/`, made by `scripts/geodata/render_compare.js` with the paperdolls renderer; panels A flat with OSM storeys, B flat with UrbIS storeys, C real relief x1 + UrbIS, D relief x3 + UrbIS): `jette-overview.jpg`, `jette-hill.jpg` (steepest dense ground), `jette-tall.jpg` (the tower blocks).

Honest reading of the pictures and `scripts/geodata/check_relief.py`:

- **Heights are the large visible gain.** B against A: the towers, the 4 to 5-storey blocks, the 1-storey sheds, the terraces' real storey counts are all there. Policymakers will recognise the towers.
- **Relief at true scale is subtle**, as the paperdolls spike predicted: it reads in the overview as shading and a slight tilt, and at street scale as rows stepping up. x3 is clearer; label it if shown.
- **No floating or buried buildings are visible** at x1, and at x3 none that catch the eye. Measured on the 1 m DTM: the ground varies by a median 0.47 m across a footprint (p90 1.5 m, p99 3.2 m); **19% of footprints span more than 1 m and 5.5% more than 2 m** (max 13.8 m, a few buildings on embankments), so those sprites sit up to half that off their ground on the low or high side. paperdolls anchors each building at the mean ground under the footprint (scene `z` minus DTM mean: median 0.001 m, 95th percentile 0.13 m, so the sampling is right). Slope plinths (the spike's own proposal) would hide the gap; owner paperdolls.
- **Roads are continuous**, no gaps at joins. Grades: median 1.9%, 99th percentile 10%, 1.1% of segments above 10%, maximum 62% on a few short segments, probably bridges or cuttings where the DTM shows the ground under or beside the road. `road.z` is sampled only at the road's own vertices, so a long straight segment across a valley cuts the corner (a handful of 100 to 190 m segments differ by 5 to 8 m at their ends, grades near 5%). Densifying road points before sampling would fix it; owner paperdolls ingest.
- **Terrain shading is blocky at 25 m cells.** The `soft-light` relief layer shows rectangular facets in flat areas and parks, and streaks at the box edge where NoData is filled with the nearest value (overview, outside the commune). `--terrain-cell 10` or smoothing the relief image would help; owner paperdolls (the spike flagged `RELIEF_GAIN` as untuned on real data).
- Not checked: a real browser render (node-canvas only), and `scripts/build_jette_demo.sh ENRICHED=1` through to the pack: the pack check on `packs/great-retrofit` currently fails on the default scene as well (manifest `mappings[6]`, `layout.right[6].kpis`, which `gr-dashboard` is editing), so the build stops before the scene is used. The enriched scene itself builds and renders in the paperdolls simulator.

### Reproduce

```bash
scripts/geodata/build_enriched.sh          # downloads ~75 MB once into data/raw/, writes build/jette-scene-enriched.json
ENRICHED=1 scripts/build_jette_demo.sh     # same, then builds the demo page from it (default stays the flat OSM scene)
node scripts/geodata/render_compare.js     # needs the paperdolls checkout's node_modules (canvas)
```
Python needs numpy, Pillow, pyyaml and shapely.

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
