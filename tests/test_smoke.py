"""冒烟测试：确认整个流程能跑通。"""

import numpy as np

import monet_palette as mp

def test_generate_returns_result(result):
    assert result.seeds, "至少应产出一个种子色"
    assert "primary" in result.light
    assert "primary" in result.dark
    assert len(result.quantized) > 0

def test_seeds_have_valid_hct(result):
    for seed in result.seeds:
        assert 0.0 <= seed.hue < 360.0
        assert seed.chroma >= 0.0
        assert 0.0 <= seed.tone <= 100.0

def test_hex_format(result):
    hex_str = mp.to_hex(result.light["primary"])
    assert hex_str.startswith("#")
    assert len(hex_str) == 7
    int(hex_str[1:], 16)  # 能解析成整数才算合法

def test_all_roles_present(result):
    required = ["primary", "onPrimary", "surface", "onSurface", "error"]
    for role in required:
        assert role in result.light
        assert role in result.dark

def test_light_dark_differ(result):
    # 浅色和深色主题的 primary 不应完全相同
    assert not np.allclose(result.light["primary"], result.dark["primary"])

def test_css_export(result):
    css = mp.to_css(result)
    assert ":root" in css
    assert "--md-sys-color-primary" in css
    assert '[data-theme="dark"]' in css

def test_json_export(result):
    import json

    data = json.loads(mp.to_json(result))
    assert "seeds" in data
    assert "light" in data
    assert "dark" in data
    assert "primary" in data["light"]

def test_generate_from_file(example_image_path):
    """如果 examples/hiro.jpg 存在，测试从文件加载。"""
    res = mp.generate(example_image_path, max_side=64)
    assert res.seeds