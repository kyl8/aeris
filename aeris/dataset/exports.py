from __future__ import annotations

import json
import tarfile
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .schema import AerisSample


def samples_to_dataframe(samples: Iterable[AerisSample | dict[str, Any]], *, flat: bool = True) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for sample in samples:
        if isinstance(sample, AerisSample):
            records.append(sample.to_flat_record() if flat else sample.to_record())
        else:
            records.append(_flatten(sample) if flat else dict(sample))
    return pd.DataFrame(records)


def export_csv(samples: Iterable[AerisSample | dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples_to_dataframe(samples, flat=True).to_csv(path, index=False, encoding="utf-8")
    return path


def export_jsonl(samples: Iterable[AerisSample | dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            record = sample.to_record() if isinstance(sample, AerisSample) else dict(sample)
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path


def export_parquet(samples: Iterable[AerisSample | dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples_to_dataframe(samples, flat=True).to_parquet(path, index=False)
    return path


def export_huggingface(samples: Iterable[AerisSample | dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [sample.to_record() if isinstance(sample, AerisSample) else dict(sample) for sample in samples]
    try:
        from datasets import Dataset  # type: ignore

        dataset = Dataset.from_list(records)
        dataset.save_to_disk(str(output_dir))
    except Exception:
        export_jsonl(records, output_dir / "dataset.jsonl")
        (output_dir / "README.md").write_text(
            "# Aeris Hugging Face export\n\n"
            "Install `datasets` to convert this JSONL folder into a native HF dataset.\n",
            encoding="utf-8",
        )
    return output_dir


def export_webdataset(samples: Iterable[AerisSample | dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w") as tar:
        for index, sample in enumerate(samples):
            record = sample.to_record() if isinstance(sample, AerisSample) else dict(sample)
            image_path = Path(str(record.get("image_path", "")))
            key = f"{index:08d}"
            metadata_bytes = json.dumps(record, ensure_ascii=False, default=str).encode("utf-8")
            info = tarfile.TarInfo(f"{key}.json")
            info.size = len(metadata_bytes)
            tar.addfile(info, fileobj=_BytesReader(metadata_bytes))
            if image_path.exists():
                suffix = image_path.suffix.lower().lstrip(".") or "jpg"
                tar.add(str(image_path), arcname=f"{key}.{suffix}")
    return path


def export_pytorch_dataset_module(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '''from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from torch.utils.data import Dataset


class AerisTorchDataset(Dataset):
    def __init__(self, jsonl_path, transform=None, target_transform=None):
        self.jsonl_path = Path(jsonl_path)
        self.transform = transform
        self.target_transform = target_transform
        with self.jsonl_path.open("r", encoding="utf-8") as handle:
            self.records = [json.loads(line) for line in handle if line.strip()]

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]
        image = Image.open(record["image_path"]).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        target = {
            "visual_label": record.get("visual_label"),
            "weather_label": record.get("weather_label"),
            "weather": record.get("weather", {}),
            "metadata": {
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "timestamp_image": record.get("timestamp_image"),
                "source_image": record.get("source_image"),
            },
        }
        if self.target_transform is not None:
            target = self.target_transform(target)
        return image, target
''',
        encoding="utf-8",
    )
    return path


def export_dataset(
    samples: Iterable[AerisSample | dict[str, Any]],
    output_dir: Path,
    *,
    formats: tuple[str, ...] = ("csv", "jsonl", "parquet", "huggingface", "pytorch", "webdataset"),
) -> dict[str, str]:
    materialized = list(samples)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}
    if "csv" in formats:
        outputs["csv"] = str(export_csv(materialized, output_dir / "aeris_dataset.csv"))
    if "jsonl" in formats:
        outputs["jsonl"] = str(export_jsonl(materialized, output_dir / "aeris_dataset.jsonl"))
    if "parquet" in formats:
        try:
            outputs["parquet"] = str(export_parquet(materialized, output_dir / "aeris_dataset.parquet"))
        except Exception as exc:
            outputs["parquet_error"] = str(exc)
    if "huggingface" in formats:
        outputs["huggingface"] = str(export_huggingface(materialized, output_dir / "huggingface"))
    if "pytorch" in formats:
        outputs["pytorch"] = str(export_pytorch_dataset_module(output_dir / "pytorch_dataset.py"))
    if "webdataset" in formats:
        outputs["webdataset"] = str(export_webdataset(materialized, output_dir / "aeris-webdataset.tar"))
    return outputs


def _flatten(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    for nested_name in ("weather", "quality", "metadata"):
        nested = output.pop(nested_name, {})
        if isinstance(nested, dict):
            for key, value in nested.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    output[f"{nested_name}.{key}"] = value
    return output


class _BytesReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk
