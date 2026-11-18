# D2P image examples 

Web-ready image examples for the [Depth2Pose](https://github.com/kocurvik/depth2pose) project page.
The `website` branch of `depth2pose` loads them from GitHub Pages of this repository
(`https://kocurvik.github.io/d2p_examples/`).

## Layout

- `listdatasets.json` – list of dataset folders
- `<dataset>/examples/<dataset>_examples.json` – pairs of the dataset
- `<dataset>/results/*.json` – per-pair results
- `<dataset>/images/*.webp`, `<dataset>/depths/*.webp` – RGB images and depth visualizations

## Regenerating

The files are generated from the raw export (PNG + JSON) by `convert_examples.py`,
which converts referenced PNGs to WebP (quality 85) and rewrites the `*_path` fields in the JSON files.

```bash
pip install pillow
python convert_examples.py <path/to/raw/export>
```

The output is written next to the script. Re-running only re-encodes images that are missing or older than their source PNG.
The script does not delete anything, so remove folders of datasets that were dropped from the export by hand.
