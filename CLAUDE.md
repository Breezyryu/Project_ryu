# CLAUDE.md - PINN Project Implementation Guidelines

This document provides implementation guidelines and best practices for developing the Physics-Informed Neural Networks (PINN) project. It serves as a comprehensive reference for AI assistants and developers working on this codebase.

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