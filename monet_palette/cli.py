"""命令行入口。"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

import numpy as np

from . import export
from .engine import generate


def _swatch(rgb) -> str:
    r, g, b = np.round(np.clip(np.asarray(rgb), 0, 1) * 255).astype(int)
    return f"\x1b[48;2;{r};{g};{b}m    \x1b[0m"


def _print_result(result) -> None:
    print("种子色 (seeds):")
    for i, s in enumerate(result.seeds):
        print(
            f"  {_swatch(s.to_rgb())} #{i}  {export.to_hex(s.to_rgb())}"
            f"   H={s.hue:6.1f}  C={s.chroma:5.1f}  T={s.tone:5.1f}"
        )

    for label, scheme in (("浅色 Light", result.light), ("深色 Dark", result.dark)):
        print(f"\n{label}:")
        for k, v in scheme.items():
            print(f"  {_swatch(v)} {k:<22} {export.to_hex(v)}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="monet-palette",
        description="从图片中提取 Material You (Monet) 动态配色",
    )
    p.add_argument("image", help="输入图片路径")
    p.add_argument("-n", "--colors", type=int, default=128, help="量化颜色数（默认 128）")
    p.add_argument("-s", "--seeds", type=int, default=4, help="保留的种子色数量（默认 4）")
    p.add_argument("--content", action="store_true", help="使用 content 风格（更忠实原图）")
    p.add_argument("--no-refine", action="store_true", help="跳过 K-Means 精炼")
    p.add_argument("--max-side", type=int, default=256, help="分析前的图片最长边（默认 256）")

    p.add_argument("-o", "--out", metavar="DIR",
                   help="一键导出：写入 DIR/theme.css、theme.json、preview.png")
    p.add_argument("--json", dest="json_out", metavar="FILE", help="导出 JSON")
    p.add_argument("--css", dest="css_out", metavar="FILE", help="导出 CSS 变量")
    p.add_argument("--preview", metavar="FILE", help="导出预览图 PNG")
    p.add_argument("--print", dest="do_print", action="store_true", help="在终端打印配色")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # -o/--out 展开成三个具体路径
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        args.css_out = args.css_out or os.path.join(args.out, "theme.css")
        args.json_out = args.json_out or os.path.join(args.out, "theme.json")
        args.preview = args.preview or os.path.join(args.out, "preview.png")

    try:
        result = generate(
            args.image,
            max_colors=args.colors,
            seed_count=args.seeds,
            is_content=args.content,
            refine=not args.no_refine,
            max_side=args.max_side,
        )
    except FileNotFoundError:
        print(f"[错误] 找不到图片: {args.image}", file=sys.stderr)
        return 2

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            f.write(export.to_json(result))
        print(f"已写入 {args.json_out}", file=sys.stderr)

    if args.css_out:
        with open(args.css_out, "w", encoding="utf-8") as f:
            f.write(export.to_css(result))
        print(f"已写入 {args.css_out}", file=sys.stderr)

    if args.preview:
        export.render_preview(result, args.preview)
        print(f"已写入 {args.preview}", file=sys.stderr)

    if args.do_print or not (args.json_out or args.css_out or args.preview):
        _print_result(result)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())