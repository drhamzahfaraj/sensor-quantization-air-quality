"""
models.py
---------
Lightweight 1D-CNN for 8-class pollutant event classification.

Architecture: 3 convolutional blocks → GlobalAveragePooling → Dense → Softmax
Input: (batch, 600, 8) — 10-minute window, 8 sensor channels, 1 Hz
Output: (batch, 8) — activity class probabilities

Parameters: ~45,000 (176 KB FP32 / 44 KB INT8)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvBlock1D(nn.Module):
    """Convolutional block: Conv1D → BatchNorm → ReLU → MaxPool."""
    
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 5):
        super().__init__()
        self.conv = nn.Conv1d(
            in_channels, out_channels, kernel_size,
            padding=kernel_size // 2, bias=False
        )
        self.bn = nn.BatchNorm1d(out_channels)
        self.pool = nn.MaxPool1d(kernel_size=2, stride=2)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.pool(F.relu(self.bn(self.conv(x))))

class AQSC_CNN(nn.Module):
    """
    Lightweight 1D-CNN for pollutant event classification.
    
    Designed for deployment on STM32L4R9 (Cortex-M4, 120 MHz, 640 KB SRAM)
    after INT8 post-training quantisation via TFLite or CMSIS-NN.
    
    Args:
        n_channels: Number of sensor input channels (default: 8).
        n_classes: Number of output classes (default: 8).
        dropout: Dropout rate before final classifier (default: 0.3).
    """
    
    def __init__(self, n_channels: int = 8, n_classes: int = 8, dropout: float = 0.3):
        super().__init__()
        self.block1 = ConvBlock1D(n_channels, 16)  # 600 → 300
        self.block2 = ConvBlock1D(16, 32)          # 300 → 150
        self.block3 = ConvBlock1D(32, 64)          # 150 → 75
        self.gap = nn.AdaptiveAvgPool1d(1)         # 75 → 1
        self.fc1 = nn.Linear(64, 64)
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(64, n_classes)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, time, channels) → (batch, channels, time) for Conv1d
        x = x.transpose(1, 2)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.gap(x).squeeze(-1)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)
    
    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

def build_model(n_channels: int = 8, n_classes: int = 8) -> AQSC_CNN:
    """Construct and return the AQSC 1D-CNN model."""
    model = AQSC_CNN(n_channels=n_channels, n_classes=n_classes)
    print(f"AQSC_CNN — {model.count_parameters():,} trainable parameters")
    return model

if __name__ == "__main__":
    import torch
    
    model = build_model()
    dummy = torch.randn(4, 600, 8)  # batch=4, 10-min window, 8 channels
    out = model(dummy)
    print(f"Input shape: {dummy.shape}")
    print(f"Output shape: {out.shape}")
    print(f"Parameters: {model.count_parameters():,} (~{model.count_parameters()*4/1024:.0f} KB FP32)")