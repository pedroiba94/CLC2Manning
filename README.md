# CLC2Manning

CLC2Manning is a QGIS plugin that assigns Manning roughness coefficients to CORINE Land Cover 2018 polygons and clips them to a user-defined Area of Interest (AOI).

The plugin is designed to support hydraulic and hydrological modelling workflows, such as HEC-RAS flood studies, by preparing land-use roughness inputs directly from CORINE data.

## Main features

- Load CORINE Land Cover 2018 from a GeoPackage (GPKG)
- Select an Area of Interest (AOI) by clicking on any visible polygon layer
- Clip CORINE polygons to the selected AOI
- Assign Manning roughness values automatically based on the CORINE `CODE_18` classification
- Calculate polygon areas (m² and hectares)
- Optionally inherit the original CORINE symbology in the output layer

## Intended use

CLC2Manning is intended for preliminary and detailed hydraulic studies where CORINE land cover is used as the roughness reference, including:
- Flood hazard and risk studies
- HEC-RAS 1D / 2D modelling
- Catchment-scale hydrological analysis

## Data scope

Current version supports **CORINE Land Cover 2018 – Peninsular Spain**.

Support for **Canary and Baleares Islands** and additional CORINE datasets is planned for future releases.

## Requirements

- QGIS 3.28 or later

## Author

Pedro Bohorquez  
Hugo Bohorquez

## License

GPL v2 or later
