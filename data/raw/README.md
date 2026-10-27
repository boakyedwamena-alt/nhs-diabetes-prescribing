# data/raw

Source files go here. They are not committed to the repository (see `.gitignore`) because they are large and are published by their original
owners under the Open Government Licence.

Expected layout once downloaded (details and links in [`docs/DATA_SOURCES.md`](../../docs/DATA_SOURCES.md)):

```
data/raw/
  epd/epd_202304.csv ... epd_202403.csv   (written by python -m src.download_epd)
  gp_lsoa.csv                              (GP registrations by LSOA, January 2024)
  qof_diabetes.csv                         (QOF 2023-24 prevalence file)
  imd.csv                                  (English Indices of Deprivation 2019, File 7)
```
