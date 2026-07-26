from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TTS_SCRIPTS = (
    ROOT / "edu-teaching-animation/scripts/minimax_tts.py",
    ROOT / "article-explainer-video/scripts/tts_pipeline.py",
)
SCAFFOLD_SCRIPT = ROOT / "edu-teaching-animation/scripts/scaffold_video.py"


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TTSRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = [load_script(path, f"tts_review_{i}") for i, path in enumerate(TTS_SCRIPTS)]

    def test_audio_temp_paths_keep_codec_suffix(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                self.assertEqual(module.audio_temp_path(Path("clip.mp3")).suffix, ".mp3")
                self.assertEqual(module.audio_temp_path(Path("clip.mp3"), ".aiff").suffix, ".aiff")

    def test_case_insensitive_ids_are_rejected(self):
        for module in self.modules:
            sanitizer = getattr(module, "sanitize_segment_id", None) or module.sanitize_chapter_id
            used = set()
            sanitizer("A", used)
            with self.subTest(module=module.__name__), self.assertRaises(SystemExit):
                sanitizer("a", used)

    def test_invalid_duration_is_rejected(self):
        for module in self.modules:
            for value in ("0", "nan", "inf"):
                completed = types.SimpleNamespace(stdout=value)
                with self.subTest(module=module.__name__, value=value), mock.patch.object(
                    module.subprocess, "run", return_value=completed
                ):
                    with self.assertRaises(RuntimeError):
                        module.probe_duration(Path("fake.mp3"))

    def test_edge_failure_preserves_existing_audio(self):
        class FakeCommunicate:
            def __init__(self, **kwargs):
                pass

            async def save(self, path):
                Path(path).write_bytes(b"invalid replacement")

        fake_edge = types.SimpleNamespace(Communicate=FakeCommunicate)
        with mock.patch.dict(sys.modules, {"edge_tts": fake_edge}):
            for module in self.modules:
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / "clip.mp3"
                    output.write_bytes(b"existing valid audio")
                    with self.subTest(module=module.__name__), mock.patch.object(
                        module, "probe_duration", side_effect=RuntimeError("bad audio")
                    ), mock.patch.object(module.time, "sleep", return_value=None):
                        with self.assertRaises(SystemExit):
                            module.tts_edge("text", output, "zh-CN-XiaoxiaoNeural", 1.0, "ignored", timeout=1)
                    self.assertEqual(output.read_bytes(), b"existing valid audio")

    def test_say_writes_to_mp3_temp_before_replace(self):
        for module in self.modules:
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                if command[0] == "say":
                    Path(command[command.index("-o") + 1]).write_bytes(b"fake aiff")
                else:
                    Path(command[-1]).write_bytes(b"fake mp3")
                return types.SimpleNamespace(stdout="1.0")

            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "clip.mp3"
                with self.subTest(module=module.__name__), mock.patch.object(
                    module.subprocess, "run", side_effect=fake_run
                ), mock.patch.object(module, "probe_duration", return_value=1.0):
                    module.tts_say("text", output, "Tingting", 1.0, "ignored")
                self.assertEqual(Path(calls[1][-1]).suffix, ".mp3")
                self.assertEqual(output.read_bytes(), b"fake mp3")

    def test_falsey_non_object_voice_is_rejected(self):
        storyboards = (
            (TTS_SCRIPTS[0], {"segments": [{"id": 1, "narration": "text"}], "voice": []}, ["--outdir", "audio"]),
            (TTS_SCRIPTS[1], {"chapters": [{"id": 1, "narration": ["text"]}], "voice": False}, []),
        )
        for script, storyboard, extra in storyboards:
            with tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                storyboard_path = project / "storyboard.json"
                storyboard_path.write_text(json.dumps(storyboard), encoding="utf-8")
                target = storyboard_path if script == TTS_SCRIPTS[0] else project
                result = subprocess.run(
                    [sys.executable, str(script), str(target), *extra],
                    capture_output=True,
                    text=True,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                with self.subTest(script=script.name):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("storyboard.voice", result.stderr)


class ScaffoldRegressionTests(unittest.TestCase):
    def assert_palette_scaffolds_video(self, palette, topic, primary, accent):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "audio").mkdir()
            storyboard = {
                "topic": topic,
                "chapter": "初中课程",
                "palette": palette,
                "segments": [
                    {
                        "id": index,
                        "title": f"场景{index}",
                        "visual": "教学内容示意图",
                        "transition": "blur-crossfade",
                    }
                    for index in range(1, 8)
                ],
            }
            durations = {
                "total": 49.0,
                "segments": [
                    {
                        "id": index,
                        "title": f"场景{index}",
                        "start": float((index - 1) * 7),
                        "duration": 7.0,
                        "subtitle": "测试旁白",
                        "file": f"audio/seg-{index:02d}.mp3",
                        "audio_start": float((index - 1) * 7),
                        "audio_duration": 7.0,
                    }
                    for index in range(1, 8)
                ],
            }
            (project / "storyboard.json").write_text(
                json.dumps(storyboard, ensure_ascii=False), encoding="utf-8"
            )
            (project / "audio/durations.json").write_text(
                json.dumps(durations, ensure_ascii=False), encoding="utf-8"
            )

            result = subprocess.run(
                [sys.executable, str(SCAFFOLD_SCRIPT), str(project)],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"palette={palette}", result.stdout)
            html = (project / "index.html").read_text(encoding="utf-8")
            self.assertIn(f"--primary:   {primary};", html)
            self.assertIn(f"--accent:   {accent};", html)

    def test_chemistry_palette_scaffolds_video(self):
        self.assert_palette_scaffolds_video(
            "chemistry", "二氧化碳与石灰水反应", "#0B6F75", "#B84A32"
        )

    def test_history_palette_scaffolds_video(self):
        self.assert_palette_scaffolds_video(
            "history", "工业革命", "#7A2E3A", "#9A641F"
        )


class AgnesRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scripts_dir = ROOT / "ai-image-generator/scripts"
        sys.path.insert(0, str(scripts_dir))
        from providers.agnes import AgnesProvider

        cls.provider_class = AgnesProvider

    def make_provider(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            return self.provider_class("test-key")

    def test_unknown_aspect_ratio_is_rejected(self):
        provider = self.make_provider()
        with self.assertRaises(ValueError):
            provider._size_from_aspect_ratio("16:10", "2K")
        with self.assertRaises(ValueError):
            provider._size_from_aspect_ratio(16, "2K")

    def test_data_uri_mime_must_match_content(self):
        provider = self.make_provider()
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
        encoded = base64.b64encode(png).decode("ascii")
        with self.assertRaises(ValueError):
            provider._normalize_ref_image(f"data:image/jpeg;base64,{encoded}")
        normalized = provider._normalize_ref_image(f"data:image/png;base64,{encoded}")
        self.assertTrue(normalized.startswith("data:image/png;base64,"))
        with self.assertRaises(ValueError):
            provider.build_create_payload("edit", "edit", [123], "1:1", "2K")

    def test_reference_size_limit_applies_before_use(self):
        provider = self.make_provider()
        provider.max_reference_image_bytes = 8
        png = b"\x89PNG\r\n\x1a\n" + b"0"
        with self.assertRaises(ValueError):
            provider._encode_validated_image(png, "image/png")

    def test_invalid_environment_is_lazy_and_friendly(self):
        with mock.patch.dict(os.environ, {"AGNES_HTTP_TIMEOUT": "invalid"}):
            with self.assertRaisesRegex(ValueError, "AGNES_HTTP_TIMEOUT"):
                self.provider_class("test-key")


if __name__ == "__main__":
    unittest.main()
