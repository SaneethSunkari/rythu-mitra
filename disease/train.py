"""Train a ResNet18 disease model on an ImageFolder-style dataset."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the Rythu Mitra disease model.")
    parser.add_argument("--dataset-dir", required=True, help="ImageFolder dataset directory.")
    parser.add_argument("--output", default="disease/weights/resnet18_diseases.pt", help="Checkpoint output path.")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="Inspect the dataset and exit without training.")
    return parser


def set_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def main() -> None:
    args = build_parser().parse_args()
    set_seed(args.seed)

    import torch
    from torch import nn
    from torch.utils.data import DataLoader, random_split
    from torchvision import datasets, models, transforms

    dataset_dir = Path(args.dataset_dir)
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    dataset = datasets.ImageFolder(str(dataset_dir), transform=transform)
    if len(dataset.classes) < 2:
        raise ValueError("Need at least 2 classes to train the disease model.")

    if args.dry_run:
        summary = {
            "dataset_dir": str(dataset_dir),
            "classes": dataset.classes,
            "samples": len(dataset),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    val_size = max(int(len(dataset) * args.val_split), 1)
    train_size = max(len(dataset) - val_size, 1)
    if train_size + val_size > len(dataset):
        val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(args.seed),
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers)

    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, len(dataset.classes))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    best_state = None
    best_val_acc = -1.0
    history: list[dict] = []

    for epoch in range(args.epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            train_loss += float(loss.item()) * labels.size(0)
            train_correct += int((logits.argmax(dim=1) == labels).sum().item())
            train_total += int(labels.size(0))

        model.eval()
        val_correct = 0
        val_total = 0
        val_loss = 0.0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                logits = model(images)
                loss = criterion(logits, labels)
                val_loss += float(loss.item()) * labels.size(0)
                val_correct += int((logits.argmax(dim=1) == labels).sum().item())
                val_total += int(labels.size(0))

        train_acc = train_correct / max(train_total, 1)
        val_acc = val_correct / max(val_total, 1)
        epoch_summary = {
            "epoch": epoch + 1,
            "train_loss": round(train_loss / max(train_total, 1), 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss / max(val_total, 1), 4),
            "val_acc": round(val_acc, 4),
        }
        history.append(epoch_summary)

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_state = {
                "state_dict": model.state_dict(),
                "class_names": dataset.classes,
                "metrics": {
                    "best_val_acc": val_acc,
                    "history": history,
                },
            }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if best_state is None:
        raise RuntimeError("Training ended without a checkpoint state.")
    torch.save(best_state, output_path)

    print(
        json.dumps(
            {
                "checkpoint": str(output_path),
                "classes": dataset.classes,
                "samples": len(dataset),
                "best_val_acc": round(best_val_acc, 4),
                "history": history,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
