"""Convert exported D2P image examples into a compact, web-ready copy for GitHub Pages.

Usage:
    pip install pillow
    python convert_examples.py <src_dir> [--dst .] [--quality 85]

By default the output is written next to this script (the root of the d2p_examples repo).
"""

import argparse
import json
import os
import sys

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

DEFAULT_DST = Path(__file__).resolve().parent

def rewrite_paths(node, referenced):
	"""Recursively replace ``.png`` with ``.webp`` in values of keys ending with ``_path``.

	Dict keys themselves (e.g. pair keys like ``images\\1.png-images\\2.png``) are left untouched.
	Every rewritten path is added to ``referenced`` as the original relative PNG path.
	"""
	if isinstance(node, dict):
		out = {}
		for key, value in node.items():
			if isinstance(value, str) and key.endswith('_path') and value.lower().endswith('.png'):
				referenced.add(value.replace('\\', '/'))
				out[key] = value[:-4] + '.webp'
			else:
				out[key] = rewrite_paths(value, referenced)
		return out
	if isinstance(node, list):
		return [rewrite_paths(item, referenced) for item in node]
	return node

def write_json(path, data):
	path.parent.mkdir(parents=True, exist_ok=True)
	with open(path, 'w', encoding='utf-8', newline='\n') as f:
		json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

def convert_image(job):
	src, dst, quality, method = job
	dst = Path(dst)
	if dst.exists() and dst.stat().st_mtime >= Path(src).stat().st_mtime:
		return 'skipped'
	dst.parent.mkdir(parents=True, exist_ok=True)
	with Image.open(src) as im:
		has_alpha = im.mode in ('RGBA', 'LA') or 'transparency' in im.info
		im = im.convert('RGBA' if has_alpha else 'RGB')
		tmp = dst.with_suffix('.webp.tmp')
		im.save(tmp, 'WEBP', quality=quality, method=method)
	os.replace(tmp, dst)
	return 'converted'

def process_dataset(src_root, dst_root, dataset):
	"""Rewrite all JSON files of one dataset and return the PNG paths they reference."""
	src_ds, dst_ds = src_root / dataset, dst_root / dataset
	referenced = set()
	json_files = sorted((src_ds / 'examples').glob('*.json')) + sorted((src_ds / 'results').glob('*.json'))

	for src_json in json_files:
		with open(src_json, encoding='utf-8') as f:
			data = json.load(f)
		write_json(dst_ds / src_json.relative_to(src_ds), rewrite_paths(data, referenced))

	return len(json_files), referenced

def main():
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument('src', type=Path, help='raw export folder containing listdatasets.json')
	parser.add_argument('--dst', type=Path, default=DEFAULT_DST, help=f'output folder (default: {DEFAULT_DST})')
	parser.add_argument('--quality', type=int, default=85, help='WebP quality 0-100 (default: 85)')
	parser.add_argument('--method', type=int, default=6, help='WebP encoder effort 0-6 (default: 6)')
	parser.add_argument('--workers', type=int, default=os.cpu_count(), help='parallel encoder processes')
	args = parser.parse_args()

	src_root, dst_root = args.src.resolve(), args.dst.resolve()
	with open(src_root / 'listdatasets.json', encoding='utf-8') as f:
		datasets = json.load(f)

	jobs, missing = [], []
	for dataset in datasets:
		n_json, referenced = process_dataset(src_root, dst_root, dataset)
		for rel in sorted(referenced):
			src_png = src_root / dataset / rel
			if not src_png.is_file():
				missing.append(f'{dataset}/{rel}')
				continue
			dst_webp = (dst_root / dataset / rel).with_suffix('.webp')
			jobs.append((str(src_png), str(dst_webp), args.quality, args.method))
		print(f'{dataset}: {n_json} json, {len(referenced)} images')

	write_json(dst_root / 'listdatasets.json', datasets)

	counts = {'converted': 0, 'skipped': 0}
	with ProcessPoolExecutor(max_workers=args.workers) as pool:
		for i, status in enumerate(pool.map(convert_image, jobs, chunksize=32), 1):
			counts[status] += 1
			if i % 1000 == 0 or i == len(jobs):
				print(f'images {i}/{len(jobs)}', flush=True)

	total = sum(p.stat().st_size for p in dst_root.rglob('*') if p.is_file() and '.git' not in p.relative_to(dst_root).parts)
	print(f"done: {counts['converted']} converted, {counts['skipped']} up to date, output {total / 1e9:.2f} GB in {dst_root}")
	if missing:
		print(f'WARNING: {len(missing)} referenced images not found, e.g. {missing[:5]}', file=sys.stderr)

if __name__ == '__main__':
	main()