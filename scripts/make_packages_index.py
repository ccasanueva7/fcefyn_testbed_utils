#!/usr/bin/env python3
"""Create opkg Packages and Packages.gz index from a directory of .ipk files."""

import gzip
import io
import os
import sys
import tarfile

packages_dir = sys.argv[1] if len(sys.argv) > 1 else "./packages"
entries = []

for f in sorted(os.listdir(packages_dir)):
    if not f.endswith(".ipk"):
        continue
    fpath = os.path.join(packages_dir, f)
    try:
        with tarfile.open(fpath, "r:gz") as outer:
            ctrl_tar_data = io.BytesIO(outer.extractfile("./control.tar.gz").read())
        with tarfile.open(fileobj=ctrl_tar_data, mode="r:gz") as inner:
            control = inner.extractfile("./control").read().decode("utf-8").strip()
        size = os.path.getsize(fpath)
        entries.append(f"{control}\nFilename: {f}\nSize: {size}\n")
        print(f"  indexed: {f}")
    except Exception as e:
        print(f"  warning: {f}: {e}", file=sys.stderr)

content = "\n\n".join(entries) + "\n"
with open(os.path.join(packages_dir, "Packages"), "w") as fh:
    fh.write(content)
with gzip.open(os.path.join(packages_dir, "Packages.gz"), "wb", 9) as fh:
    fh.write(content.encode())

print(f"\nIndexed {len(entries)} packages")
