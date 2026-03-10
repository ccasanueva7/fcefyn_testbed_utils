#!/usr/bin/env python3
"""
Generate labgrid places.yaml from labnet.yaml template.

This script reads the labnet.yaml file and the places.yaml.j2 template
to generate the places.yaml file needed by labgrid-coordinator.

Usage:
    python3 generate_places_yaml.py [--lab LAB_NAME] [--labnet PATH] [--template PATH] [--output PATH]

Examples:
    # Generate places for labgrid-fcefyn (default)
    python3 generate_places_yaml.py

    # Generate places for a different lab
    python3 generate_places_yaml.py --lab labgrid-hsn

    # Specify custom paths
    python3 generate_places_yaml.py --labnet /path/to/labnet.yaml --output ~/labgrid-coordinator/places.yaml
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from jinja2 import Template
except ImportError:
    print("Error: jinja2 is required. Install with: pip3 install jinja2", file=sys.stderr)
    sys.exit(1)


def find_openwrt_tests_dir():
    """Try to find the openwrt-tests directory."""
    # Common locations
    possible_paths = [
        Path.home() / "Documents" / "openwrt-tests",
        Path.home() / "openwrt-tests",
        Path("/home/franco/Documents/openwrt-tests"),
        Path.cwd().parent / "openwrt-tests",
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "labnet.yaml").exists():
            return path
    
    return None


def generate_places_yaml(
    lab_name: str,
    labnet_path: Path,
    template_path: Path,
    output_path: Path,
):
    """
    Generate places.yaml from labnet.yaml and template.
    
    Args:
        lab_name: Name of the lab (e.g., 'labgrid-fcefyn')
        labnet_path: Path to labnet.yaml
        template_path: Path to places.yaml.j2 template
        output_path: Path where to write places.yaml
    """
    # Read labnet.yaml
    if not labnet_path.exists():
        print(f"Error: labnet.yaml not found at {labnet_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(labnet_path, 'r') as f:
        labnet = yaml.safe_load(f)
    
    # Verify lab exists
    if lab_name not in labnet.get('labs', {}):
        print(f"Error: Lab '{lab_name}' not found in labnet.yaml", file=sys.stderr)
        print(f"Available labs: {', '.join(labnet.get('labs', {}).keys())}", file=sys.stderr)
        sys.exit(1)
    
    # Read template
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(template_path, 'r') as f:
        template_str = f.read()
    
    # Render template
    template = Template(template_str)
    places_yaml = template.render(
        labnet=labnet,
        inventory_hostname=lab_name,
        ansible_date_time={'epoch': int(datetime.now().timestamp())}
    )
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write places.yaml
    with open(output_path, 'w') as f:
        f.write(places_yaml)
    
    # Count generated places
    place_count = sum(1 for line in places_yaml.split('\n') if line.strip().endswith(':') and 'labgrid-' in line)
    
    print("✓ places.yaml generated successfully")
    print(f"  Output: {output_path}")
    print(f"  Lab: {lab_name}")
    print(f"  Places generated: {place_count}")
    
    # List generated places
    print("\nGenerated places:")
    for line in places_yaml.split('\n'):
        if line.strip().endswith(':') and 'labgrid-' in line:
            place_name = line.strip().rstrip(':')
            print(f"  - {place_name}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate labgrid places.yaml from labnet.yaml template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--lab',
        default='labgrid-fcefyn',
        help='Lab name (default: labgrid-fcefyn)'
    )
    
    parser.add_argument(
        '--labnet',
        type=Path,
        help='Path to labnet.yaml (default: auto-detect from openwrt-tests)'
    )
    
    parser.add_argument(
        '--template',
        type=Path,
        help='Path to places.yaml.j2 template (default: auto-detect from openwrt-tests)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path.home() / 'labgrid-coordinator' / 'places.yaml',
        help='Output path for places.yaml (default: ~/labgrid-coordinator/places.yaml)'
    )
    
    args = parser.parse_args()
    
    # Auto-detect openwrt-tests directory if paths not specified
    if args.labnet is None or args.template is None:
        openwrt_tests = find_openwrt_tests_dir()
        if openwrt_tests is None:
            print("Error: Could not find openwrt-tests directory.", file=sys.stderr)
            print("Please specify --labnet and --template paths manually.", file=sys.stderr)
            sys.exit(1)
        
        if args.labnet is None:
            args.labnet = openwrt_tests / 'labnet.yaml'
        
        if args.template is None:
            args.template = openwrt_tests / 'ansible' / 'files' / 'coordinator' / 'places.yaml.j2'
    
    generate_places_yaml(
        lab_name=args.lab,
        labnet_path=args.labnet,
        template_path=args.template,
        output_path=args.output,
    )


if __name__ == '__main__':
    main()

