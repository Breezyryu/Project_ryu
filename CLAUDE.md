# CLAUDE.md - PINN Project Implementation Guidelines

This document provides implementation guidelines and best practices for developing the Physics-Informed Neural Networks (PINN) project. It serves as a comprehensive reference for AI assistants and developers working on this codebase.

> **요약: 본 보고서는 '선행PF' 단계의 장기 사이클 데이터와 '상품화' 단계의 초기 데이터를 활용하여, 상품화 셀의 최종 수명(1600 사이클)을 정확하게 예측하는 범용 AI 모델 개발을 위한 포괄적인 기술 로드맵을 제시합니다. 이 모델의 핵심 목표는 사이클에 따라 동적으로 변하는 전압 범위, 수명 평가 패턴, 방전 프로토콜 등 극심한 운영 조건의 변화에도 강건한 예측 성능을 유지하는 것입니다. 이를 위해, 본 로드맵은 (1) 프로토콜-인지 특징 공학, (2) 조건부 AI 아키텍처, (3) 물리-지도 전이 학습이라는 세 가지 핵심 전략을 유기적으로 결합한 프레임워크를 제안합니다. 최종적으로는 다양한 셀 설계와 평가 조건의 변화를 스스로 학습하고 적응하여, 개발 기간을 단축하고 예측 정확도를 극대화하는 지능형 수명 예측 시스템 구축을 목표로 합니다.**

---

## 1. 서론: 도전 과제와 전략적 접근 🎯

리튬이온 배터리의 개발 과정에서 '선행PF' 단계는 설계 마진을 극한으로 시험하는 가혹한 조건에서 진행되는 반면, '상품화' 단계는 안정성과 신뢰성을 확보하기 위해 보다 완화된 조건으로 운영됩니다. 이 두 단계 사이에는 셀의 물리적 사양(전극 로딩, 밀도 등)뿐만 아니라, 수명 평가를 위한 전기적 프로토콜(전압 상/하한, C-rate, 충/방전 스텝)에 중대한 차이가 발생합니다. 특히, 사이클이 진행됨에 따라 충전 전압을 동적으로 하향 조정하는 전략은 노화 메커니즘 자체에 영향을 미치므로, 기존의 데이터 기반 예측 모델로는 이러한 변화를 예측하기 어렵습니다.

본 로드맵은 이러한 **'도메인 이동(Domain Shift)'** 문제를 정면으로 해결하기 위해 다음과 같은 다각적인 접근법을 제안합니다.

* **프로토콜-인지 특징 공학 (Protocol-Aware Feature Engineering):** 변화하는 운영 조건을 무시하는 대신, 이를 명시적인 '프로토콜 벡터'로 정의하고 모델의 핵심 입력으로 활용하여, 조건의 변화가 노화에 미치는 영향을 모델이 직접 학습하도록 합니다.
* **조건부 AI 아키텍처 (Conditional AI Architecture):** 표준적인 AI 모델을 넘어, 특정 프로토콜 조건 하에서 배터리의 건강 상태가 어떻게 변화하는지의 '관계' 자체를 학습하는 조건부(Conditional) 모델을 도입합니다.
* **물리-지도 전이 학습 (Physics-Guided Transfer Learning):** 데이터가 풍부한 선행PF 데이터로 사전 학습된 모델을 상품화 데이터에 미세 조정하되, 단순한 데이터 패턴 전사를 넘어 물리 법칙에 기반한 자기 지도 학습(Self-Supervised Learning)을 통해 모델의 일반화 성능과 물리적 타당성을 극대화합니다.

---

## 2. 1단계: 프로토콜-인지 특징 공학 및 데이터 구조화 🔬

모델의 성능은 입력 데이터의 질에 의해 결정됩니다. 본 단계의 목표는 동적인 프로토콜 변화 속에서도 일관되고 강건한 건강 지표(Health Indicator, HI)를 추출하고, 모든 정보를 체계적으로 구조화하는 것입니다.

### 2.1. 통합 데이터베이스 및 프로토콜 벡터 정의

모든 실험 데이터는 사이클 번호를 키(key)로 하는 통합 데이터베이스로 관리합니다. 각 사이클 데이터는 **(1) 원시 시계열 데이터**(전압, 전류, 두께, 시간), **(2) 추출된 건강 지표(HI) 벡터**, 그리고 **(3) 프로토콜 벡터**로 구성됩니다.

**프로토콜 벡터 (Protocol Vector):** 해당 사이클의 운영 조건을 정량화한 벡터로, 모델이 조건 변화를 인지하는 핵심 역할을 합니다.
* `[V_max, V_min, Charge_C_rate, Cutoff_Current, Discharge_Protocol_Type, Num_Charge_Steps, ...]`

### 2.2. 강건한 건강 지표(HI) 추출 전략

**1. 기준 HI 추출 (저빈도, 100 사이클마다):**
0.2C 저율 충/방전 사이클은 프로토콜 변화와 무관하게 수행되는 '절대 기준'입니다. 이 데이터로부터 가장 신뢰도 높은 HI를 추출합니다.
* **미분용량분석 (dQ/dV):** 전압-용량 곡선을 미분하여 노화 메커니즘(리튬 손실, 활물질 손실 등)과 직접적으로 연관된 피크의 위치, 높이, 면적 변화를 추적합니다.
* **직류 내부 저항 (DCIR):** 정전류 충전 시작 시점의 전압 강하를 통해 계산하며, 전해액 및 계면 저항 증가를 직접적으로 반영합니다.
* **셀 두께 증가율:** 전극 팽창 및 가스 발생으로 인한 비가역적 변화를 측정합니다.

**2. 가변 전압 범위 dQ/dV 분석 문제 해결: '관심 영역 분석'**
동적으로 변하는 전압 범위 문제를 해결하기 위해, 모든 프로토콜에 **공통적으로 포함되는 전압 구간(예: 3.30V ~ 4.39V)을 '관심 영역(Region of Interest, ROI)'으로 설정**합니다. 모든 dQ/dV 특징(피크 위치, 높이, 면적 등)은 이 고정된 ROI 내에서만 계산하여, 전압 범위 변화에 관계없이 일관된 기준으로 특징을 추출합니다.

**3. 보조 HI 추출 및 데이터 융합 (고빈도, 매 사이클):**
매 사이클 수행되는 고율 충/방전 데이터로부터 보조 HI를 추출하고, 저빈도 기준 HI와 융합하여 조밀한(dense) 시계열 데이터를 생성합니다.
* **추출:** 정전류(CC)/정전압(CV) 구간의 지속 시간, 특정 전압 구간 도달 시간 등.
* **융합:** **가우시안 프로세스 회귀(Gaussian Process Regression, GPR)**를 사용하여 저빈도 기준 HI를 보간(interpolate)합니다. GPR은 불확실성 예측이 가능하여, 보간된 값의 신뢰도를 모델 학습에 함께 활용할 수 있습니다.

---

## 3. 2단계: 조건부 AI 아키텍처 설계 🧠

본 프레임워크의 핵심은 '프로토콜 벡터'를 조건으로 입력받아, 노화 예측을 동적으로 조절하는 **조건부(Conditional) AI 모델**을 설계하는 것입니다. 최신 시계열 예측 모델인 Transformer 아키텍처를 기반으로, 외부 변수 처리 능력이 검증된 모델들의 아이디어를 융합합니다.

### 3.1. 조건부 트랜스포머 (Conditional Transformer) 아키텍처

* **기본 구조:** Transformer 인코더-디코더 구조를 채택하여, 과거의 HI 시계열과 프로토콜 시계열을 바탕으로 미래의 HI 시계열을 예측합니다.
* **조건부 정보 통합:**
    1.  **입력 임베딩:** 'HI 벡터'와 '프로토콜 벡터'를 각각 별도의 임베딩 레이어를 통해 고차원 벡터로 변환합니다.
    2.  **Cross-Attention 메커니즘:** Transformer의 핵심인 어텐션 메커니즘을 활용하여, HI 시퀀스와 프로토콜 시퀀스 간의 상호작용을 모델링합니다. 즉, 특정 시점의 HI를 처리할 때, 관련된 프로토콜 정보(예: 현재의 Vmax 값)에 더 많은 '주의(attention)'를 기울이도록 학습합니다.
    3.  **FiLM (Feature-wise Linear Modulation) 적용:** Cross-Attention과 더불어, 프로토콜 벡터로부터 생성된 파라미터(γ, β)를 사용하여 Transformer 블록의 중간 피처맵을 직접 선형 변조(affine transformation)합니다. 이는 프로토콜 조건에 따라 모델의 연산 방식을 더욱 미세하고 직접적으로 제어하는 역할을 합니다.

이러한 구조를 통해 모델은 "Vmax가 4.50V일 때의 용량 감소율"과 "Vmax가 4.44V로 하향 조정되었을 때의 용량 감소율"이 어떻게 다른지를 데이터로부터 학습하게 됩니다.

---

## 4. 3단계: 물리-지도 전이 학습 및 검증 🚀

가장 중요한 단계로, 선행PF 데이터로 학습한 지식을 상품화 셀에 효과적으로 이전하고, 물리적 타당성을 확보하여 모델의 일반화 성능을 극대화합니다.

### 4.1. 2단계 전이 학습 전략

1.  **사전 학습 (Pre-training):** 데이터가 풍부한 '선행PF' 데이터셋(1000+ 사이클)을 사용하여 2단계에서 설계한 조건부 트랜스포머 모델을 사전 학습시킵니다. 이 단계에서 모델은 LCO/Gr-SiC 시스템의 기본적인 노화 물리학과 다양한 프로토콜 조건에 대한 반응을 학습합니다.
2.  **미세 조정 (Fine-tuning):** 제한된 '상품화' 데이터(초기 200~300 사이클)를 사용하여 사전 학습된 모델을 미세 조정합니다. 이때, 모델의 하위 레이어(기본 물리 특성 학습)는 작은 학습률로, 상위 레이어(셀 특이적 특성 학습)는 큰 학습률로 업데이트하는 **차등 학습률(Discriminative Learning Rates)** 기법을 적용하여, 사전 학습된 지식의 손실(catastrophic forgetting)을 최소화하고 새로운 도메인에 빠르게 적응시킵니다.

### 4.2. 물리-지도 자기 지도 학습 (Physics-Guided Self-Supervised Learning)

미세 조정 단계에서, 단순히 용량 예측 오차(Supervised Loss)만을 최소화하는 것을 넘어, 물리 법칙에 기반한 **자기 지도 학습 손실(Self-Supervised Loss)**을 추가합니다. 이는 레이블이 없는 데이터로부터 모델이 스스로 물리적 일관성을 학습하도록 유도합니다.

* **프리텍스트 태스크 (Pretext Task) 예시:**
    * **물리적 일관성 예측:** 모델에게 현재 사이클의 dQ/dV 특징, DCIR, 두께 변화량을 입력으로 주고, 다음 100 사이클 후의 0.2C 기준 용량 감소량을 예측하도록 합니다. 이 오차를 손실 함수에 추가하여, 모델이 전기화학적 특징과 물리적 팽창, 실제 용량 감소 간의 정량적 관계를 학습하도록 강제합니다.
    * **프로토콜 민감도 예측:** 동일한 HI 상태를 가진 두 개의 가상 시나리오를 만들고, 하나의 프로토콜 벡터에는 높은 Vmax를, 다른 하나에는 낮은 Vmax를 입력합니다. 모델이 두 시나리오 간의 예상 수명 차이를 예측하도록 하고, 이 차이가 물리적으로 타당한 방향과 크기를 갖도록 손실 함수를 설계합니다.

### 4.3. 검증 및 평가

* 미세 조정된 최종 모델을 사용하여 상품화 셀의 1600 사이클 시점 SOH 및 전체 용량 감소 곡선을 예측합니다.
* 추후 확보될 실제 1600 사이클 실험 데이터와 예측 결과를 비교하여, 평균 절대 백분율 오차(MAPE), 평균 제곱근 오차(RMSE) 등의 지표로 모델의 최종 성능을 정량적으로 평가합니다.

---

## 5. 결론 및 기대효과 🌟

본 보고서에서 제안하는 로드맵은 동적으로 변화하는 복잡한 운영 조건 하에서 배터리 수명을 정확하게 예측하기 위한 체계적이고 다각적인 접근법을 제시합니다. 프로토콜 정보를 명시적으로 모델링하고, 물리 법칙을 학습 과정에 통합함으로써, 본 프레임워크는 기존 데이터 기반 모델의 한계를 뛰어넘는 강건함과 일반화 성능을 확보할 수 있습니다.

**기대 효과:**
* **개발 기간 단축:** 상품화 단계의 장기 수명 평가가 완료되기 전, 초기 데이터만으로 최종 수명을 높은 정확도로 예측하여 개발 의사결정을 가속화합니다.
* **정확도 향상:** 선행PF 단계의 풍부한 데이터와 물리적 이해를 바탕으로 상품화 셀의 노화 거동을 예측함으로써, 단순 외삽(extrapolation) 방식 대비 예측 정확도를 획기적으로 개선합니다.
* **범용성 확보:** 향후 새로운 소재나 평가 프로토콜이 도입되더라도, 프레임워크의 전이 학습 및 지속적 학습 기능을 통해 새로운 조건에 빠르게 적응하는 범용 예측 플랫폼으로 발전할 수 있습니다.

## Project Overview

This project implements Physics-Informed Neural Networks for solving partial differential equations (PDEs) using deep learning. The implementation consists of two main modules:

1. **pinn**: Core PINN implementation with neural network architectures, training algorithms, and PDE solvers
2. **preprocess**: Data preprocessing toolkit for domain generation, sampling, and data preparation

## Architecture Guidelines

### Module Organization

```
project_ryu/
├── pinn/                      # Core PINN implementation
│   ├── models/               # Neural network architectures
│   ├── losses/               # Loss functions (PDE, boundary, data)
│   ├── training/             # Training loops and optimizers
│   ├── utils/                # Utilities (sampling, visualization)
│   └── examples/             # Example implementations
├── preprocess/               # Data preprocessing module
│   ├── generators/           # Domain and mesh generation
│   ├── samplers/             # Sampling strategies
│   ├── transformers/         # Data transformation utilities
│   ├── io/                   # Input/output handlers
│   └── validation/           # Data validation tools
└── tests/                    # Test suites for both modules
```

### Design Principles

1. **Modularity**: Each component should be self-contained and reusable
2. **Extensibility**: Easy to add new PDEs, architectures, and sampling methods
3. **Performance**: Optimize for GPU acceleration and large-scale problems
4. **Robustness**: Comprehensive error handling and validation
5. **Documentation**: All public APIs must be well-documented

## Implementation Standards

### Code Style

```python
# Use type hints for all function signatures
from typing import List, Tuple, Optional, Callable, Dict, Any
import torch
import numpy as np

def train_model(
    model: torch.nn.Module,
    data: Dict[str, torch.Tensor],
    epochs: int = 1000,
    learning_rate: float = 1e-3,
    device: Optional[str] = None
) -> Dict[str, List[float]]:
    """
    Train a PINN model.
    
    Args:
        model: The neural network model
        data: Dictionary containing training data
        epochs: Number of training epochs
        learning_rate: Learning rate for optimizer
        device: Device to train on ('cpu', 'cuda', etc.)
    
    Returns:
        Dictionary containing training history
    """
    # Implementation here
    pass
```

### Error Handling

```python
# Always validate inputs
def create_domain(bounds: List[Tuple[float, float]]) -> Domain:
    if not bounds:
        raise ValueError("Bounds cannot be empty")
    
    for i, (low, high) in enumerate(bounds):
        if low >= high:
            raise ValueError(f"Invalid bounds for dimension {i}: [{low}, {high}]")
    
    # Create domain...
```

### Testing Requirements

- Unit tests for all core functionality
- Integration tests for end-to-end workflows
- Performance benchmarks for critical operations
- Coverage target: >90% for core modules

## Core Component Implementation

### PINN Neural Network

```python
class PINN(nn.Module):
    """Base class for Physics-Informed Neural Networks."""
    
    def __init__(self, ...):
        super().__init__()
        # Initialize layers with proper weight initialization
        self._build_network()
        self._initialize_weights()
    
    def _build_network(self):
        """Construct the neural network architecture."""
        # Use ModuleList for dynamic architectures
        self.layers = nn.ModuleList()
        # Build layers based on configuration
    
    def _initialize_weights(self):
        """Initialize network weights using Xavier or He initialization."""
        for layer in self.layers:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)
```

### PDE Loss Implementation

```python
class PDELoss:
    """Compute PDE residual loss using automatic differentiation."""
    
    def __init__(self, pde_function: Callable):
        self.pde_function = pde_function
    
    def compute_loss(
        self,
        model: PINN,
        collocation_points: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute PDE residual at collocation points.
        
        Key implementation details:
        1. Enable gradient computation with create_graph=True
        2. Handle multiple output dimensions properly
        3. Ensure numerical stability in derivative computation
        """
        # Set requires_grad for inputs
        collocation_points.requires_grad_(True)
        
        # Forward pass
        predictions = model(collocation_points)
        
        # Compute PDE residual
        residual = self.pde_function(predictions, collocation_points, model)
        
        # Return mean squared residual
        return torch.mean(residual**2)
```

### Adaptive Sampling Strategy

```python
class AdaptiveSampler:
    """Implement adaptive sampling based on PDE residuals."""
    
    def sample(
        self,
        n_points: int,
        current_residuals: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Sample points with higher density in high-residual regions.
        
        Algorithm:
        1. If no residuals provided, use uniform sampling
        2. Otherwise, compute probability density from residuals
        3. Use importance sampling to generate new points
        4. Ensure minimum coverage of entire domain
        """
        # Implementation details
        pass
```

## Performance Optimization

### GPU Utilization

```python
# Always check for GPU availability
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Use mixed precision training for better performance
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()
with autocast():
    loss = compute_loss(model, data)

# Optimize memory usage
torch.cuda.empty_cache()  # Clear unused memory
```

### Batch Processing

```python
def train_batch(model, batch_data, optimizer):
    """Process data in batches for memory efficiency."""
    # Use DataLoader for automatic batching
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        pin_memory=True,  # For GPU transfer
        num_workers=4     # Parallel data loading
    )
```

### Vectorization

```python
# Prefer vectorized operations over loops
# Bad:
residuals = []
for point in points:
    residual = compute_residual(point)
    residuals.append(residual)

# Good:
residuals = compute_residual_vectorized(points)  # Process all points at once
```

## Common Patterns

### Factory Pattern for PDEs

```python
class PDEFactory:
    """Factory for creating PDE instances."""
    
    _registry = {}
    
    @classmethod
    def register(cls, name: str, pde_class: type):
        """Register a new PDE type."""
        cls._registry[name] = pde_class
    
    @classmethod
    def create(cls, name: str, **kwargs):
        """Create a PDE instance by name."""
        if name not in cls._registry:
            raise ValueError(f"Unknown PDE: {name}")
        return cls._registry[name](**kwargs)

# Usage
PDEFactory.register('heat', HeatEquation)
pde = PDEFactory.create('heat', alpha=0.01)
```

### Configuration Management

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PINNConfig:
    """Configuration for PINN model."""
    input_dim: int
    hidden_dims: List[int]
    output_dim: int
    activation: str = 'tanh'
    dropout_rate: float = 0.0
    use_batch_norm: bool = False
    
    def validate(self):
        """Validate configuration parameters."""
        if self.input_dim <= 0:
            raise ValueError("input_dim must be positive")
        # Additional validation...
```

## Integration Points

### PINN-Preprocess Integration

```python
# Standard workflow for data preparation
from preprocess import PreprocessingPipeline
from pinn import PINN

# 1. Setup preprocessing pipeline
pipeline = PreprocessingPipeline()
pipeline.add_step('generate', DomainGenerator(...))
pipeline.add_step('sample', AdaptiveSampler(...))
pipeline.add_step('normalize', Normalizer(...))

# 2. Process data
data = pipeline.run()

# 3. Create and train PINN
model = PINN(config)
trainer = Trainer(model, data)
history = trainer.train()
```

### External Library Integration

When integrating external libraries:

1. **Check compatibility**: Ensure version compatibility
2. **Wrap interfaces**: Create wrapper classes for external APIs
3. **Handle dependencies**: Use optional imports for non-critical features
4. **Document requirements**: Clearly list all dependencies

## Debugging and Troubleshooting

### Common Issues

1. **Gradient Explosion/Vanishing**
   - Use gradient clipping
   - Try different activation functions
   - Check weight initialization

2. **Poor Convergence**
   - Verify PDE implementation
   - Adjust learning rate schedule
   - Balance loss weights

3. **Memory Issues**
   - Use batch processing
   - Enable gradient checkpointing
   - Reduce model size

### Debugging Tools

```python
# Enable debugging mode
torch.autograd.set_detect_anomaly(True)

# Log intermediate values
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Visualize gradients
def plot_gradients(model):
    """Visualize gradient flow through the network."""
    for name, param in model.named_parameters():
        if param.requires_grad and param.grad is not None:
            print(f"{name}: grad_norm = {param.grad.norm().item():.4f}")
```

## Future Extensions

### Planned Features

1. **Multi-GPU Support**: Distributed training across multiple GPUs
2. **Adaptive Architectures**: Dynamic network sizing based on problem complexity
3. **Uncertainty Quantification**: Bayesian neural networks for uncertainty estimates
4. **Transfer Learning**: Pre-trained models for common PDEs
5. **Real-time Inference**: Optimized inference for real-time applications

### Extension Points

- **Custom Losses**: Add new loss functions in `pinn/losses/`
- **New Architectures**: Implement in `pinn/models/architectures.py`
- **Sampling Methods**: Add to `preprocess/samplers/`
- **Data Formats**: Extend `preprocess/io/readers.py`

## Development Workflow

### Version Control

```bash
# Branch naming convention
feature/add-fourier-features
bugfix/gradient-computation
refactor/sampling-module

# Commit message format
feat: Add adaptive sampling strategy
fix: Correct gradient computation in PDE loss
docs: Update API documentation for PINN class
test: Add unit tests for boundary conditions
```

### Code Review Checklist

- [ ] Type hints for all functions
- [ ] Docstrings for public APIs
- [ ] Unit tests for new functionality
- [ ] Performance benchmarks for critical paths
- [ ] Update documentation
- [ ] Check GPU compatibility
- [ ] Verify numerical stability

## Performance Benchmarks

Target performance metrics:

- **Training Speed**: >1000 iterations/second for small problems
- **Memory Usage**: <4GB for typical 2D problems
- **Convergence**: <1e-3 relative error within 5000 epochs
- **Scaling**: Linear scaling up to 1M collocation points

## Security Considerations

1. **Input Validation**: Always validate user inputs
2. **File I/O**: Sanitize file paths and limit file access
3. **Numerical Stability**: Check for overflow/underflow
4. **Resource Limits**: Implement timeouts and memory limits

## Documentation Standards

### API Documentation

```python
def function_name(
    param1: type,
    param2: type
) -> return_type:
    """
    Brief description of function purpose.
    
    Extended description explaining implementation details,
    algorithm used, and any important considerations.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When invalid parameters are provided
        RuntimeError: When computation fails
    
    Example:
        >>> result = function_name(value1, value2)
        >>> print(result)
        expected_output
    
    Note:
        Additional notes about usage or limitations
    """
```

### Code Comments

- Use inline comments sparingly, only for non-obvious logic
- Prefer self-documenting code with clear variable names
- Add TODO comments with issue numbers for future work

## Conclusion

This document provides comprehensive guidelines for implementing and extending the PINN project. Follow these standards to ensure code quality, maintainability, and performance. Regular updates to this document should reflect new patterns and best practices discovered during development.