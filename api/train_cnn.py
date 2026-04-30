import json
import os
import random
import time
import copy
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms
from transformers import AutoImageProcessor, SiglipForImageClassification, logging as transformers_logging


CURRENT_DIR = Path(__file__).resolve().parent
TRAIN_DIR = CURRENT_DIR / "datasets" / "training"
VAL_DIR = CURRENT_DIR / "datasets" / "validating"
MODEL_DIR = CURRENT_DIR / "weights" / "aeris-weather-siglip2"
CLASSES_SAVE_PATH = CURRENT_DIR / "weights" / "aeris-classes.json"
BASE_MODEL_ID = "prithivMLmods/Weather-Image-Classification"
TARGET_CLASSES = [
    "cloudy/overcast",
    "foggy/hazy",
    "rain/storm",
    "snow/frosty",
    "sun/clear",
]
SOURCE_TO_TARGET_CLASS = {
    "cloudy": "cloudy/overcast",
    "fogsmog": "foggy/hazy",
    "sandstorm": "foggy/hazy",
    "hail": "rain/storm",
    "lightning": "rain/storm",
    "rain": "rain/storm",
    "rainbow": "rain/storm",
    "frost": "snow/frosty",
    "glaze": "snow/frosty",
    "rime": "snow/frosty",
    "snow": "snow/frosty",
    "dew": "sun/clear",
    "shine": "sun/clear",
    "sunrise": "sun/clear",
}

BATCH_SIZE = int(os.getenv("AERIS_BATCH_SIZE", "8"))
NUM_EPOCHS = 12
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01
VALIDATION_RATIO = 0.2
SEED = 42
IMAGE_SIZE = 224
NUM_WORKERS = 0 if os.name == "nt" else 2
DEVICE_PREFERENCE = os.getenv("AERIS_DEVICE", "auto").strip().lower()
FREEZE_BACKBONE = os.getenv("AERIS_FREEZE_BACKBONE", "0").strip().lower() in {"1", "true", "yes", "sim"}
LOG_EVERY_N_BATCHES = int(os.getenv("AERIS_LOG_EVERY_N_BATCHES", "25"))


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def find_source_classes(*base_dirs: Path) -> list[str]:
    source_classes: set[str] = set()

    for base_dir in base_dirs:
        if not base_dir.exists():
            continue

        for dataset_dir in base_dir.iterdir():
            if not dataset_dir.is_dir():
                continue

            for class_dir in dataset_dir.iterdir():
                if class_dir.is_dir():
                    source_classes.add(class_dir.name)

    return sorted(source_classes)


def collect_samples(base_dir: Path, target_to_idx: dict[str, int], source_to_target: dict[str, str]) -> list[tuple[str, int]]:
    samples: list[tuple[str, int]] = []
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    if not base_dir.exists():
        return samples

    for dataset_dir in base_dir.iterdir():
        if not dataset_dir.is_dir():
            continue

        for class_dir in dataset_dir.iterdir():
            if not class_dir.is_dir() or class_dir.name not in source_to_target:
                continue

            target_class = source_to_target[class_dir.name]
            label_idx = target_to_idx[target_class]
            for image_path in class_dir.iterdir():
                if image_path.is_file() and image_path.suffix.lower() in valid_extensions:
                    samples.append((str(image_path), label_idx))

    return samples


def stratified_split(samples: list[tuple[str, int]], validation_ratio: float, seed: int) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    grouped: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for sample in samples:
        grouped[sample[1]].append(sample)

    rng = random.Random(seed)
    train_split: list[tuple[str, int]] = []
    val_split: list[tuple[str, int]] = []

    for label_samples in grouped.values():
        rng.shuffle(label_samples)
        if len(label_samples) == 1:
            train_split.extend(label_samples)
            continue

        validation_count = max(1, int(round(len(label_samples) * validation_ratio)))
        validation_count = min(validation_count, len(label_samples) - 1)

        val_split.extend(label_samples[:validation_count])
        train_split.extend(label_samples[validation_count:])

    rng.shuffle(train_split)
    rng.shuffle(val_split)
    return train_split, val_split


class WeatherImageDataset(Dataset):
    def __init__(self, samples: list[tuple[str, int]], processor: AutoImageProcessor, augment=None):
        self.samples = samples
        self.processor = processor
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        path, label = self.samples[idx]
        with Image.open(path) as image:
            image = image.convert("RGB")
            if self.augment is not None:
                image = self.augment(image)
            encoded = self.processor(images=image, return_tensors="pt")

        pixel_values = encoded["pixel_values"].squeeze(0)
        return pixel_values, label


def build_train_augmentations() -> transforms.Compose:
    return transforms.Compose([
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.72, 1.0), ratio=(0.85, 1.15)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomApply(
            [
                transforms.ColorJitter(
                    brightness=0.24,
                    contrast=0.24,
                    saturation=0.20,
                    hue=0.03,
                )
            ],
            p=0.75,
        ),
        transforms.RandomAutocontrast(p=0.25),
        transforms.RandomRotation(degrees=12, fill=0),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.4)),
    ])


def build_class_weights(samples: list[tuple[str, int]], num_classes: int) -> tuple[torch.Tensor, list[float]]:
    class_counts = Counter(label for _, label in samples)
    total_samples = len(samples)

    class_weights = [
        total_samples / max(num_classes * class_counts.get(label, 1), 1)
        for label in range(num_classes)
    ]
    sample_weights = [1.0 / max(class_counts[label], 1) for _, label in samples]

    return torch.tensor(class_weights, dtype=torch.float32), sample_weights


def is_directml_device(device: object) -> bool:
    device_type = getattr(device, "type", None)
    if isinstance(device_type, str):
        return device_type.lower() == "privateuseone"
    return str(device).lower().startswith("privateuseone")


class DirectMLAdamW(optim.Optimizer):
    def __init__(
        self,
        params,
        lr: float = 1e-3,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        weight_decay: float = 0.0,
    ):
        if lr < 0.0:
            raise ValueError(f"Learning rate inválido: {lr}")
        if eps < 0.0:
            raise ValueError(f"Epsilon inválido: {eps}")
        if not 0.0 <= betas[0] < 1.0:
            raise ValueError(f"Beta 1 inválido: {betas[0]}")
        if not 0.0 <= betas[1] < 1.0:
            raise ValueError(f"Beta 2 inválido: {betas[1]}")
        if weight_decay < 0.0:
            raise ValueError(f"Weight decay inválido: {weight_decay}")

        defaults = {
            "lr": lr,
            "betas": betas,
            "eps": eps,
            "weight_decay": weight_decay,
        }
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            lr = group["lr"]
            beta1, beta2 = group["betas"]
            eps = group["eps"]
            weight_decay = group["weight_decay"]

            for param in group["params"]:
                if param.grad is None:
                    continue

                grad = param.grad
                if grad.is_sparse:
                    raise RuntimeError("DirectMLAdamW não suporta gradientes esparsos.")

                state = self.state[param]
                if len(state) == 0:
                    state["step"] = 0
                    state["exp_avg"] = torch.zeros_like(param, memory_format=torch.preserve_format)
                    state["exp_avg_sq"] = torch.zeros_like(param, memory_format=torch.preserve_format)

                exp_avg = state["exp_avg"]
                exp_avg_sq = state["exp_avg_sq"]
                state["step"] += 1

                if weight_decay != 0:
                    param.mul_(1 - lr * weight_decay)

                exp_avg.mul_(beta1).add_(grad, alpha=1 - beta1)
                exp_avg_sq.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)

                bias_correction1 = 1 - beta1 ** state["step"]
                bias_correction2 = 1 - beta2 ** state["step"]
                step_size = lr / bias_correction1
                denom = exp_avg_sq.sqrt().div_(bias_correction2 ** 0.5).add_(eps)

                param.addcdiv_(exp_avg, denom, value=-step_size)

        return loss


def select_device(preference: str) -> torch.device:
    if preference == "cpu":
        return torch.device("cpu")

    if preference == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        print("[AVISO] CUDA solicitado, mas não está disponível. Usando CPU.")
        return torch.device("cpu")

    if preference == "directml":
        try:
            import torch_directml

            if torch_directml.is_available():
                return torch_directml.device()
        except ImportError:
            pass

        print("[AVISO] DirectML solicitado, mas não está disponível. Usando CPU.")
        return torch.device("cpu")

    if preference != "auto":
        print(f"[AVISO] AERIS_DEVICE='{preference}' não reconhecido. Usando seleção automática.")

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def freeze_backbone(model: SiglipForImageClassification) -> None:
    for parameter in model.vision_model.parameters():
        parameter.requires_grad = False
    model.vision_model.eval()


def save_artifacts(model: SiglipForImageClassification, processor: AutoImageProcessor, classes: list[str]) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.config.id2label = {index: label for index, label in enumerate(classes)}
    model.config.label2id = {label: index for index, label in enumerate(classes)}
    processor.save_pretrained(MODEL_DIR)

    model_to_save = model
    if any(is_directml_device(parameter.device) for parameter in model.parameters()):
        model_to_save = copy.deepcopy(model).cpu()

    model_to_save.save_pretrained(MODEL_DIR)

    with open(CLASSES_SAVE_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(classes, file_handle, ensure_ascii=False, indent=2)


def main() -> None:
    print("Iniciando fine-tuning do Aeris com SigLIP2...")
    set_seed(SEED)

    if not TRAIN_DIR.exists():
        print(f"\n[ERRO] A pasta '{TRAIN_DIR}' não foi encontrada!")
        return

    source_classes = find_source_classes(TRAIN_DIR, VAL_DIR)
    if not source_classes:
        print("[ERRO] Nenhuma classe encontrada nos datasets de treino/validação.")
        return

    unmapped_classes = sorted(set(source_classes) - set(SOURCE_TO_TARGET_CLASS))
    if unmapped_classes:
        print(f"[ERRO] Existem classes sem mapeamento para as 5 classes alvo: {unmapped_classes}")
        return

    classes = TARGET_CLASSES
    class_to_idx = {class_name: index for index, class_name in enumerate(classes)}
    train_samples = collect_samples(TRAIN_DIR, class_to_idx, SOURCE_TO_TARGET_CLASS)
    val_samples = collect_samples(VAL_DIR, class_to_idx, SOURCE_TO_TARGET_CLASS)

    if not train_samples:
        print("[ERRO] Nenhuma imagem encontrada nas subpastas de treino.")
        return

    if not val_samples:
        print("[AVISO] Nenhuma imagem encontrada em 'validating'. Fazendo split estratificado (80% treino / 20% validação)...")
        train_samples, val_samples = stratified_split(train_samples, VALIDATION_RATIO, SEED)

    num_classes = len(classes)
    print(f"Classes encontradas no dataset: {source_classes}")
    print(f"Mapeamento para {num_classes} classes alvo: {classes}")
    for source_class in source_classes:
        print(f"  - {source_class} -> {SOURCE_TO_TARGET_CLASS[source_class]}")
    print(f"Imagens de treino: {len(train_samples)}")
    print(f"Imagens de validação: {len(val_samples)}")

    print("\nCarregando processor e modelo base do Hugging Face...")
    try:
        processor = AutoImageProcessor.from_pretrained(BASE_MODEL_ID, use_fast=True)

        previous_transformers_verbosity = transformers_logging.get_verbosity()
        transformers_logging.set_verbosity_error()
        try:
            model = SiglipForImageClassification.from_pretrained(
                BASE_MODEL_ID,
            )
        finally:
            transformers_logging.set_verbosity(previous_transformers_verbosity)
    except Exception as exc:
        print(f"[ERRO] Não foi possível carregar o modelo base '{BASE_MODEL_ID}': {exc}")
        return

    model.config.id2label = {index: label for index, label in enumerate(classes)}
    model.config.label2id = {label: index for index, label in enumerate(classes)}

    if FREEZE_BACKBONE:
        freeze_backbone(model)
        print("[INFO] Backbone SigLIP congelado. Treinando apenas a cabeça classificadora.")

    train_augmentations = build_train_augmentations()
    train_dataset = WeatherImageDataset(train_samples, processor, augment=train_augmentations)
    val_dataset = WeatherImageDataset(val_samples, processor)

    class_weights, sample_weights = build_class_weights(train_samples, num_classes)
    sampler = WeightedRandomSampler(weights=sample_weights, num_samples=len(sample_weights), replacement=True)

    device = select_device(DEVICE_PREFERENCE)
    print(f"Usando processamento via: {device}")
    if is_directml_device(device):
        print("[AVISO] DirectML ativado manualmente. Na RX580, use batch pequeno para reduzir risco de TDR do driver.")
    model = model.to(device)

    dataloaders = {
        "train": DataLoader(
            train_dataset,
            batch_size=BATCH_SIZE,
            sampler=sampler,
            num_workers=NUM_WORKERS,
        ),
        "val": DataLoader(
            val_dataset,
            batch_size=BATCH_SIZE,
            shuffle=False,
            num_workers=NUM_WORKERS,
        ),
    }

    dataset_sizes = {
        "train": len(train_dataset),
        "val": len(val_dataset),
    }

    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable_parameters:
        print("[ERRO] Nenhum parâmetro treinável encontrado.")
        return

    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    if is_directml_device(device):
        optimizer = DirectMLAdamW(trainable_parameters, lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    else:
        optimizer = optim.AdamW(trainable_parameters, lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)

    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(NUM_EPOCHS, 1))

    print(f"\nIniciando treinamento por {NUM_EPOCHS} épocas...\n")
    best_loss = float("inf")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLASSES_SAVE_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(classes, file_handle, ensure_ascii=False, indent=2)

    for epoch in range(NUM_EPOCHS):
        print(f"Época {epoch + 1}/{NUM_EPOCHS}")
        print("-" * 30)

        start_time = time.time()

        for phase in ["train", "val"]:
            model.train() if phase == "train" else model.eval()
            if FREEZE_BACKBONE:
                model.vision_model.eval()

            running_loss = 0.0
            corrects = 0
            seen_samples = 0

            for batch_index, (inputs, labels) in enumerate(dataloaders[phase], start=1):
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad(set_to_none=True)

                with torch.set_grad_enabled(phase == "train"):
                    outputs = model(pixel_values=inputs)
                    logits = outputs.logits
                    loss = criterion(logits, labels)
                    preds = torch.argmax(logits, dim=1)

                    if phase == "train":
                        loss.backward()
                        optimizer.step()

                batch_size = inputs.size(0)
                running_loss += loss.detach().cpu().item() * batch_size
                corrects += (preds.detach().cpu() == labels.detach().cpu()).sum().item()
                seen_samples += batch_size

                if batch_index == 1 or batch_index % LOG_EVERY_N_BATCHES == 0:
                    partial_loss = running_loss / max(seen_samples, 1)
                    partial_acc = corrects / max(seen_samples, 1)
                    total_batches = len(dataloaders[phase])
                    print(
                        f"[{phase.upper()}] batch {batch_index}/{total_batches} | "
                        f"Loss parcial: {partial_loss:.4f} | Acurácia parcial: {partial_acc:.4f}",
                        flush=True,
                    )

            epoch_loss = running_loss / max(dataset_sizes[phase], 1)
            epoch_acc = corrects / max(dataset_sizes[phase], 1)

            print(f"[{phase.upper()}] Loss: {epoch_loss:.4f} | Acurácia: {epoch_acc:.4f}")

            if phase == "val" and epoch_loss < best_loss:
                best_loss = epoch_loss
                save_artifacts(model, processor, classes)
                print(f"--> Novo melhor modelo salvo (Loss: {best_loss:.4f})")

        scheduler.step()

        time_elapsed = time.time() - start_time
        print(f"Tempo da época: {time_elapsed:.0f}s\n")

    save_artifacts(model, processor, classes)
    print("Treinamento finalizado!")
    print(f"Modelo salvo em: {MODEL_DIR}")
    print(f"Classes salvas em: {CLASSES_SAVE_PATH}")


if __name__ == "__main__":
    main()
