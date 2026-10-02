"""最小示例：从图片生成配色并保存 CSS + 预览图。

运行：
    python examples/basic.py examples/hiro.jpg
    python examples/basic.py 你的图片.jpg --out out/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from monet_palette import export, generate

def main() -> int:
    p = argparse.ArgumentParser(description="monet-palette 示例")
    default_img = Path(__file__).parent / "hiro.jpg"
    p.add_argument("image", nargs="?", default=str(default_img), help="输入图片")
    p.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"处理图片: {args.image}")
    result = generate(args.image)

    print("种子色：")
    for i, s in enumerate(result.seeds):
        print(f"  #{i}  {export.to_hex(s.to_rgb())}  H={s.hue:.1f} C={s.chroma:.1f} T={s.tone:.1f}")

    print("primary (light):", export.to_hex(result.light["primary"]))
    print("primary (dark) :", export.to_hex(result.dark["primary"]))

    css_path = out_dir / "theme.css"
    json_path = out_dir / "theme.json"
    png_path = out_dir / "preview.png"

    css_path.write_text(export.to_css(result), encoding="utf-8")
    json_path.write_text(export.to_json(result), encoding="utf-8")
    export.render_preview(result, str(png_path))

    print(f"已写入: {css_path}, {json_path}, {png_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())