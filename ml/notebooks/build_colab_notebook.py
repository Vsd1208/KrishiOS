# ruff: noqa: E501 - long lines are notebook cell source (pip and harness commands)
"""Generate the Colab benchmark notebooks (run: python build_colab_notebook.py).

* phase2_benchmarks_colab.ipynb: translation, speech-to-text and text-to-speech
* phase2_stt_colab.ipynb: speech-to-text only
"""

import json
from pathlib import Path

MD, CODE = "markdown", "code"

INTRO = """# KrishiOS Phase 2 benchmarks on a Colab GPU

Runs the Phase 2 evaluations with the **same code** as the repo (`backend/app` providers and
`ml/scripts` harnesses). Every result is logged with a `run_id` to `ml/experiments/*.jsonl` and
`ml/reports/data/*.json`.

**Before running**
1. *Runtime > Change runtime type >* **T4 GPU**.
2. Add your Hugging Face read token as a Colab secret: key icon in the left sidebar >
   *Add new secret* > name `HF_TOKEN` > paste the token > enable *Notebook access*.
   (The AI4Bharat models are gated; your account has already accepted their terms.)
3. Have `krishios_colab_bundle.zip` ready to upload.

Then **Runtime > Run all**. When cell 2 asks, upload the bundle. At the end
`RESULTS_NAME.zip` downloads: give that file back to Claude Code.
The pip cell may print dependency-conflict warnings about gradio/diffusers: they are harmless.
Expected time on a T4: about MINUTES minutes, mostly model and dataset downloads.
"""

GPU = """# 1. GPU check
import subprocess, torch
print("torch", torch.__version__, "| CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
else:
    print("WARNING: no GPU. Runtime > Change runtime type > T4 GPU, then run again.")
"""

UPLOAD = """# 2. Upload and unpack the code bundle (krishios_colab_bundle.zip)
import os, zipfile, pathlib
from google.colab import files
ROOT = pathlib.Path("/content/KrishiOS")
if not (ROOT / "backend").exists():
    uploaded = files.upload()
    name = next(iter(uploaded))
    with zipfile.ZipFile(name) as z:
        z.extractall(ROOT)
print(sorted(p.name for p in ROOT.iterdir()))
print("bundle commit:", (ROOT / "BUNDLE_COMMIT").read_text().strip())
"""

DEPS = """# 3. Dependencies (Colab already ships torch and torchaudio with CUDA)
!pip -q install "transformers==4.57.6" sentencepiece sacremoses "faster-whisper==1.2.1" "av>=14,<16" jiwer sacrebleu pyyaml loguru pydantic-settings "google-genai>=1.0" onnx onnxruntime-gpu scipy pandas pyarrow
import transformers
print("transformers", transformers.__version__)
"""

CUDA12 = """# 3b. CUDA 12 runtime for faster-whisper: CTranslate2 needs libcublas.so.12, which newer
#     Colab images no longer ship. Child processes inherit LD_LIBRARY_PATH from os.environ.
!pip -q install "nvidia-cublas-cu12" "nvidia-cudnn-cu12==9.*"
import importlib
libdirs = [list(importlib.import_module(m).__path__)[0]
           for m in ("nvidia.cublas.lib", "nvidia.cudnn.lib")]
os.environ["LD_LIBRARY_PATH"] = ":".join(libdirs + [os.environ.get("LD_LIBRARY_PATH", "")])
print("CUDA 12 libs:", libdirs)
"""

ENV = """# 4. Environment: HF token from Colab secrets (never printed), GPU device
from google.colab import userdata
os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")
os.environ.update({
    "ML_DEVICE": "cuda" if torch.cuda.is_available() else "cpu",
    "POSTGRES_PASSWORD": "unused-in-evaluation",
    "APP_ENV": "test",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
    "HF_HUB_DOWNLOAD_TIMEOUT": "600",
    "KRISHIOS_GIT_COMMIT": (ROOT / "BUNDLE_COMMIT").read_text().strip() + "+colab",
})
print("HF token set:", bool(os.environ["HF_TOKEN"]), "| device:", os.environ["ML_DEVICE"])
"""

FLEURS = """# 5. FLEURS te/hi test splits (CC BY 4.0, about 0.5 GB) for the speech benchmarks
FL = ROOT / "ml/data/raw/fleurs"
for lang in ("te_in", "hi_in"):
    d = FL / lang
    d.mkdir(parents=True, exist_ok=True)
    base = f"https://huggingface.co/datasets/google/fleurs/resolve/main/data/{lang}"
    for url, out in ((f"{base}/test.tsv", d / "test.tsv"),
                     (f"{base}/audio/test.tar.gz", d / "test.tar.gz")):
        if not out.exists():
            subprocess.run(["wget", "-q", "-O", str(out), url], check=True)
    print(lang, [(p.name, p.stat().st_size) for p in d.iterdir()])
"""

HELPER = """# 6. Helper: run a harness from backend/ and show its summary lines
LOGS = ROOT / "ml/data/interim/colab_logs"
LOGS.mkdir(parents=True, exist_ok=True)
KEEP = ("{", "run_id", "indictrans2 ", "opus-mt ", "[te 30", "[hi 30", "Traceback", "RuntimeError")

def run(script, *args):
    cmd = ["python", f"../ml/scripts/{script}", *args]
    print("$", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=ROOT / "backend", capture_output=True, text=True)
    lines = (p.stdout + p.stderr).splitlines()
    for line in lines:
        if line.startswith(KEEP) or "Error" in line[:60]:
            print(line[:1500])
    tag = "_".join(a.lstrip("-") for a in args)[:90]
    (LOGS / f"{script}_{tag}.log").write_text("\\n".join(lines))
    print("exit code", p.returncode, "\\n")
"""

MT_MD = """## Translation: test split, scored once per configuration
- IndicTrans2 with its dev-chosen strategy (protect terms and crop names; ADR-014)
- opus-mt re-run with the fixed checker (supersedes run `955550580258`)
"""
MT = """run("run_mt_eval.py", "--providers", "indictrans2", "--targets", "te", "hi", "--split", "test")
run("run_mt_eval.py", "--providers", "opus-mt", "--targets", "te", "hi", "--split", "test")
"""

STT_MD = """## Speech-to-text: FLEURS test, 30 utterances per language, seed 13
Same sample as the local Whisper-small run (run `5c0b02cf7fef`).
- IndicConformer RNNT and CTC with the language known (`--hint`, as from the farmer's profile)
- IndicConformer with Whisper language ID (unknown-speaker case)
- Whisper large-v3 as the strongest Whisper reference

Latency here is **GPU** latency; CPU latency is measured separately on the target machine.
"""
STT = """S = ("--languages", "te", "hi", "--n", "30", "--seed", "13")
run("run_stt_eval.py", "--provider", "indicconformer-600m-rnnt", *S, "--hint")
run("run_stt_eval.py", "--provider", "indicconformer-600m-ctc", *S, "--hint")
run("run_stt_eval.py", "--provider", "indicconformer-600m-rnnt", *S)
run("run_stt_eval.py", "--provider", "faster-whisper-large-v3", *S)
"""

TTS_MD = """## Text-to-speech: MMS-TTS, 20 sentences per language
The ASR round-trip CER is a proxy for intelligibility only; naturalness needs native listeners.
"""
TTS = """run("run_tts_eval.py", "--tts", "mms-tts", "--stt", "indicconformer-600m-rnnt", "--languages", "te", "hi", "--n", "20", "--seed", "13")
"""

PACK = """# 7. Package results and download them
import shutil
out = pathlib.Path("/content/RESULTS_NAME")
if out.exists():
    shutil.rmtree(out)
for rel in ("ml/experiments", "ml/reports/data", "ml/data/interim/colab_logs"):
    src = ROOT / rel
    if src.exists():
        shutil.copytree(src, out / rel)
(out / "GPU.txt").write_text(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
shutil.make_archive("/content/RESULTS_NAME", "zip", out)
files.download("/content/RESULTS_NAME.zip")
"""

SETUP = [(CODE, GPU), (CODE, UPLOAD), (CODE, DEPS), (CODE, CUDA12), (CODE, ENV), (CODE, FLEURS),
         (CODE, HELPER)]


def _fill(text: str, results: str, minutes: str) -> str:
    return text.replace("RESULTS_NAME", results).replace("MINUTES", minutes)


NOTEBOOKS = {
    "phase2_benchmarks_colab.ipynb": [
        (MD, _fill(INTRO, "krishios_phase2_results", "30-60")), *SETUP,
        (MD, MT_MD), (CODE, MT), (MD, STT_MD), (CODE, STT), (MD, TTS_MD), (CODE, TTS),
        (CODE, _fill(PACK, "krishios_phase2_results", "")),
    ],
    "phase2_stt_colab.ipynb": [
        (MD, _fill(INTRO, "krishios_phase2_stt_results", "20-40").replace(
            "Phase 2 benchmarks", "Phase 2 speech-to-text benchmarks")), *SETUP,
        (MD, STT_MD), (CODE, STT),
        (CODE, _fill(PACK, "krishios_phase2_stt_results", "")),
    ],
}


def main() -> None:
    for filename, cells in NOTEBOOKS.items():
        nb = {"nbformat": 4, "nbformat_minor": 5,
              "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                           "kernelspec": {"name": "python3", "display_name": "Python 3"},
                           "language_info": {"name": "python"}},
              "cells": []}
        for kind, src in cells:
            cell = {"cell_type": kind, "metadata": {},
                    "source": src.strip("\n").splitlines(True)}
            if kind == CODE:
                cell.update({"execution_count": None, "outputs": []})
            nb["cells"].append(cell)
        out = Path(__file__).with_name(filename)
        out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        print("wrote", out, len(cells), "cells")


if __name__ == "__main__":
    main()
