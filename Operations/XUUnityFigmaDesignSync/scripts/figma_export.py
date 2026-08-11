#!/usr/bin/env python3
"""Generic Figma REST helper for the XUUnity Figma Design Sync pipeline.

Commands:
  list    - print the node tree of a file (or a subtree) with ids, types, names and sizes
  export  - export nodes as PNG at a scale computed from a target pixel size, then verify dimensions

The personal access token is read from an environment variable (default FIGMA_TOKEN).
Never pass tokens as command-line arguments and never write them into specs or docs.

Spec format for `export` (see the Design Tech Doc template, section 3):
{
  "file_key": "...",
  "out_dir": "Staging",
  "contract": "optional default contract id",
  "items": [
    { "item": "Name",
      "contract": "optional contract id override",
      "exports": [
        { "node_id": "12:34", "file": "Name/Card.png", "target_width": 0, "target_height": 0 },
        { "node_id": "12:35", "file": "Name/Button.png", "role": "cta_button" }
      ] }
  ]
}

A composite export ("exclude": [node ids]) re-renders the node's visible leaf parts and
stitches them, so overlay layers can be dropped. Add "bounds_node_id" when the parts live in a
wider ancestor (an overlay outside the card group): parts come from "node_id"'s subtree while the
canvas geometry and crop come from "bounds_node_id".

Per export, size resolution order: explicit "scale" > explicit target_width/target_height >
role lookup in the host config passed via --config. Host config shape:
{
  "reference_viewport": { "width": 0, "height": 0 },
  "contracts": { "<contract_id>": { "<role>": { "target_width": 0, "target_height": 0 } } }
}
The host config lives in the host overlay (project-specific values); this script stays generic.
Figma caps export scale at 4; a target that needs more fails the stage explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
import urllib.parse
import urllib.request

API_BASE = "https://api.figma.com/v1"
MAX_FIGMA_SCALE = 4.0
DIMENSION_TOLERANCE_PX = 1


DEFAULT_TOKEN_FILE = os.path.expanduser("~/.figma/token")


def _token(env_name: str) -> str:
    token = os.environ.get(env_name, "").strip()
    if token:
        return token
    if os.path.isfile(DEFAULT_TOKEN_FILE):
        with open(DEFAULT_TOKEN_FILE, "r", encoding="utf-8") as stream:
            token = stream.read().strip()
        if token:
            return token
    sys.exit(f"error: no Figma token: set {env_name} or put the token into {DEFAULT_TOKEN_FILE}")


def _api_get(path: str, token: str, retries: int = 3) -> dict:
    url = f"{API_BASE}{path}"
    request = urllib.request.Request(url, headers={"X-Figma-Token": token})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                last_error = error
                continue
            body = error.read().decode("utf-8", errors="replace")[:400]
            sys.exit(f"error: Figma API {error.code} for {path}: {body}")
        except Exception as error:  # noqa: BLE001 - network layer, retried then reported
            last_error = error
            time.sleep(1 + attempt)
    sys.exit(f"error: Figma API request failed after {retries} attempts: {last_error}")


def _download(url: str, destination: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url), timeout=120) as response:
        with open(destination, "wb") as output:
            output.write(response.read())


def _png_size(path: str) -> tuple[int, int]:
    with open(path, "rb") as stream:
        header = stream.read(26)
    if len(header) < 26 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        sys.exit(f"error: {path} is not a PNG")
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def _walk(node: dict, depth: int, max_depth: int, lines: list[str]) -> None:
    box = node.get("absoluteBoundingBox") or {}
    size = ""
    if box.get("width") is not None:
        size = f"  {round(box['width'])}x{round(box['height'])}"
    lines.append(f"{'  ' * depth}{node.get('type', '?'):<12} {node.get('id', '?'):<12} {node.get('name', '')}{size}")
    if depth >= max_depth:
        return
    for child in node.get("children", []) or []:
        _walk(child, depth + 1, max_depth, lines)


def cmd_list(args: argparse.Namespace) -> None:
    token = _token(args.token_env)
    if args.node:
        node_id = urllib.parse.quote(args.node)
        payload = _api_get(f"/files/{args.file_key}/nodes?ids={node_id}&depth={args.depth}", token)
        roots = [entry["document"] for entry in payload.get("nodes", {}).values() if entry]
    else:
        payload = _api_get(f"/files/{args.file_key}?depth={args.depth}", token)
        roots = [payload["document"]]
    lines: list[str] = []
    for root in roots:
        _walk(root, 0, args.depth, lines)
    print("\n".join(lines))


def _subtree_contains(node: dict, ids: set[str]) -> bool:
    if node.get("id") in ids:
        return True
    for child in node.get("children", []) or []:
        if _subtree_contains(child, ids):
            return True
    return False


def _flatten_for_composite(node: dict, excluded: set[str], out: list[dict]) -> None:
    if node.get("id") in excluded or node.get("visible", True) is False:
        return
    children = node.get("children", []) or []
    if children and _subtree_contains(node, excluded) and node.get("id") not in excluded:
        for child in children:
            _flatten_for_composite(child, excluded, out)
        return
    out.append(node)


def _composite_export(file_key: str, token: str, export: dict, scale: float, destination: str,
                      failures: list[str]) -> None:
    from PIL import Image

    node_id = export["node_id"]
    excluded = set(export.get("exclude", []))
    bounds_node_id = export.get("bounds_node_id")
    wanted = [node_id] + ([bounds_node_id] if bounds_node_id else [])
    payload = _api_get(
        f"/files/{file_key}/nodes?ids={','.join(urllib.parse.quote(i) for i in wanted)}", token)
    nodes = payload.get("nodes", {})
    entry = nodes.get(node_id)
    if not entry:
        failures.append(f"{export['file']}: node {node_id} not found for composite")
        return

    root = entry["document"]
    root_box = root.get("absoluteBoundingBox") or {}
    if bounds_node_id:
        bounds_entry = nodes.get(bounds_node_id)
        if not bounds_entry:
            failures.append(f"{export['file']}: bounds node {bounds_node_id} not found")
            return
        root_box = bounds_entry["document"].get("absoluteBoundingBox") or {}
    parts: list[dict] = []
    for child in root.get("children", []) or []:
        _flatten_for_composite(child, excluded, parts)
    if not parts:
        failures.append(f"{export['file']}: composite produced no visible parts")
        return

    ids = ",".join(urllib.parse.quote(part["id"]) for part in parts)
    image_payload = _api_get(f"/images/{file_key}?ids={ids}&format=png&scale={scale}", token)
    if image_payload.get("err"):
        failures.append(f"{export['file']}: composite render failed: {image_payload['err']}")
        return
    urls = image_payload.get("images", {})

    canvas = Image.new("RGBA", (round(root_box["width"] * scale), round(root_box["height"] * scale)), (0, 0, 0, 0))
    for part in parts:
        url = urls.get(part["id"])
        box = part.get("absoluteBoundingBox") or {}
        if not url or box.get("width") is None:
            failures.append(f"{export['file']}: part {part['id']} ({part.get('name')}) has no render or bounds")
            return
        part_path = destination + f".part_{part['id'].replace(':', '_').replace(';', '_')}.png"
        _download(url, part_path)
        with Image.open(part_path) as part_image:
            part_rgba = part_image.convert("RGBA")
            offset = (round((box["x"] - root_box["x"]) * scale), round((box["y"] - root_box["y"]) * scale))
            expected = (round(box["width"] * scale), round(box["height"] * scale))
            if abs(part_rgba.width - expected[0]) > 2 or abs(part_rgba.height - expected[1]) > 2:
                offset = (offset[0] - (part_rgba.width - expected[0]) // 2,
                          offset[1] - (part_rgba.height - expected[1]) // 2)
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            layer.paste(part_rgba, offset)
            canvas = Image.alpha_composite(canvas, layer)
        os.remove(part_path)

    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    canvas.save(destination)


def _resolve_scale(export: dict, natural: tuple[float, float] | None) -> float:
    if "scale" in export:
        return float(export["scale"])
    target_w = export.get("target_width")
    target_h = export.get("target_height")
    if not target_w or not natural or not natural[0]:
        sys.exit(f"error: export for node {export.get('node_id')} needs either scale or target size + readable node bounds")
    scale = float(target_w) / float(natural[0])
    if target_h and natural[1]:
        scale_h = float(target_h) / float(natural[1])
        if abs(scale - scale_h) / scale > 0.02:
            sys.exit(
                f"error: node {export['node_id']} aspect mismatch: width wants scale {scale:.4f}, "
                f"height wants {scale_h:.4f}; fix the target size or the Figma node")
    if scale > MAX_FIGMA_SCALE:
        sys.exit(f"error: node {export['node_id']} needs scale {scale:.2f} > Figma cap {MAX_FIGMA_SCALE}; "
                 "reduce the target size or ask for larger source art")
    return scale


def _load_host_config(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _apply_role_defaults(export: dict, contract_id: str | None, config: dict) -> dict:
    role = export.get("role")
    if not role or "scale" in export or ("target_width" in export and export["target_width"]):
        return export
    contracts = config.get("contracts", {})
    contract = contracts.get(contract_id or "", {})
    defaults = contract.get(role)
    if not defaults:
        sys.exit(f"error: export {export.get('file')} uses role '{role}' but no target size exists "
                 f"for contract '{contract_id}' in the host config; pass --config or set explicit targets")
    merged = dict(export)
    merged["target_width"] = defaults["target_width"]
    merged["target_height"] = defaults["target_height"]
    return merged


def cmd_export(args: argparse.Namespace) -> None:
    token = _token(args.token_env)
    with open(args.spec, "r", encoding="utf-8") as stream:
        spec = json.load(stream)
    config = _load_host_config(args.config)

    file_key = spec["file_key"]
    out_dir = args.out or spec.get("out_dir") or "."
    exports: list[dict] = []
    for item in spec.get("items", []):
        contract_id = item.get("contract") or spec.get("contract")
        for export in item.get("exports", []):
            exports.append(_apply_role_defaults(export, contract_id, config))
    if not exports:
        sys.exit("error: spec contains no exports")

    size_ids = {export.get("bounds_node_id") or export["node_id"] for export in exports}
    ids = ",".join(urllib.parse.quote(i) for i in sorted(size_ids))
    nodes_payload = _api_get(f"/files/{file_key}/nodes?ids={ids}&depth=1", token)
    natural_sizes: dict[str, tuple[float, float]] = {}
    for node_id, entry in nodes_payload.get("nodes", {}).items():
        if not entry:
            continue
        box = entry["document"].get("absoluteBoundingBox") or {}
        if box.get("width"):
            natural_sizes[node_id] = (float(box["width"]), float(box["height"]))

    failures: list[str] = []
    results: list[dict] = []
    by_scale: dict[float, list[dict]] = {}
    for export in exports:
        size_key = export.get("bounds_node_id") or export["node_id"]
        scale = round(_resolve_scale(export, natural_sizes.get(size_key)), 4)
        by_scale.setdefault(scale, []).append(export)

    for scale, batch in by_scale.items():
        plain = [export for export in batch if not export.get("exclude")]
        composites = [export for export in batch if export.get("exclude")]
        urls: dict = {}
        if plain:
            ids = ",".join(urllib.parse.quote(export["node_id"]) for export in plain)
            image_payload = _api_get(f"/images/{file_key}?ids={ids}&format=png&scale={scale}", token)
            if image_payload.get("err"):
                sys.exit(f"error: Figma image render failed: {image_payload['err']}")
            urls = image_payload.get("images", {})
        for export in composites:
            destination = os.path.join(out_dir, export["file"])
            _composite_export(file_key, token, export, scale, destination, failures)
            if os.path.isfile(destination):
                width, height = _png_size(destination)
                target_w, target_h = export.get("target_width"), export.get("target_height")
                ok = not ((target_w and abs(width - int(target_w)) > DIMENSION_TOLERANCE_PX)
                          or (target_h and abs(height - int(target_h)) > DIMENSION_TOLERANCE_PX))
                if not ok:
                    failures.append(f"{export['file']}: got {width}x{height}, wanted {target_w}x{target_h}")
                results.append({"file": destination, "width": width, "height": height, "scale": scale, "ok": ok,
                                "composited": True})
        for export in plain:
            url = urls.get(export["node_id"])
            destination = os.path.join(out_dir, export["file"])
            if not url:
                failures.append(f"{export['node_id']} -> no image URL returned")
                continue
            _download(url, destination)
            width, height = _png_size(destination)
            target_w = export.get("target_width")
            target_h = export.get("target_height")
            ok = True
            if target_w and abs(width - int(target_w)) > DIMENSION_TOLERANCE_PX:
                ok = False
            if target_h and abs(height - int(target_h)) > DIMENSION_TOLERANCE_PX:
                ok = False
            if not ok:
                failures.append(f"{export['file']}: got {width}x{height}, wanted {target_w}x{target_h}")
            results.append({"file": destination, "width": width, "height": height, "scale": scale, "ok": ok})

    print(json.dumps({"exported": results, "failures": failures}, indent=2))
    if failures:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--token-env", default="FIGMA_TOKEN", help="environment variable holding the Figma token")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="print node tree with ids/names/sizes")
    list_parser.add_argument("file_key")
    list_parser.add_argument("--node", help="restrict to a subtree by node id (e.g. 6212:47717)")
    list_parser.add_argument("--depth", type=int, default=3)
    list_parser.set_defaults(func=cmd_list)

    export_parser = sub.add_parser("export", help="export nodes per spec and verify pixel sizes")
    export_parser.add_argument("--spec", required=True)
    export_parser.add_argument("--out", help="override spec out_dir")
    export_parser.add_argument("--config", help="host config json with reference_viewport and per-contract role target sizes")
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
