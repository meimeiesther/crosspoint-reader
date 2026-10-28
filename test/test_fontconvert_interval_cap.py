"""Check that the SD-font converter refuses styles the firmware would not load."""

import contextlib
import io
from pathlib import Path
import re
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib/EpdFont/scripts"))
import fontconvert_sdcard as fc  # noqa: E402

# The converter mirrors the firmware's caps.
header = (ROOT / "lib/EpdFont/SdCardFont.h").read_text()
for name in ("MAX_BMP16_INTERVALS", "MAX_FULL_INTERVALS"):
    match = re.search(rf"static constexpr uint32_t {name} = (\d+);", header)
    assert match, name
    assert int(match.group(1)) == getattr(fc, name), name

# Compact tables need BMP codepoints and at most 65535 glyphs.
assert fc.interval_cap([(0x4E00 + 2 * i,) * 2 for i in range(5000)]) == fc.MAX_BMP16_INTERVALS
assert fc.interval_cap([(0x4E00, 0x4E00), (0x20000, 0x20000)]) == fc.MAX_FULL_INTERVALS
assert fc.interval_cap([(0x0000, 0xFFFF)]) == fc.MAX_FULL_INTERVALS


# A font that has every other ideograph, rasterized without FreeType or fontTools.
class Face:
    def __init__(self, _path):
        pass

    def set_char_size(self, *_args):
        pass

    def get_char_index(self, code_point):
        return 1 if code_point % 2 == 0 else 0


sys.modules["freetype"] = types.SimpleNamespace(Face=Face, FT_LOAD_RENDER=4, FT_LOAD_FORCE_AUTOHINT=32)
fc.extract_ligature_glyph_indices_fonttools = lambda _path: {}

stderr = io.StringIO()
with contextlib.redirect_stderr(stderr):
    try:
        fc.rasterize_font_style("partial.ttf", 12, [(0x4E00, 0x4E00 + 2 * fc.MAX_BMP16_INTERVALS)])
    except SystemExit as exit_:
        assert exit_.code == 1
    else:
        raise AssertionError("a style over the cap was converted")
message = stderr.getvalue()
assert f"{fc.MAX_BMP16_INTERVALS + 1} intervals exceed the firmware's cap of {fc.MAX_BMP16_INTERVALS}" in message
assert "--fallback-regular" in message
