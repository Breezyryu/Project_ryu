"""
Battery Data Loaders Package

Provides unified interface for loading different battery testing data formats
including Toyo and PNE formats with automatic format detection.
"""

from .toyo_loader import ToyoDataLoader, ToyoTestData, ToyoCapacityData, create_toyo_loader
from .pne_loader import PNEDataLoader, PNETestData, PNEChannelData, create_pne_loader
from .unified_loader import UnifiedDataLoader, StandardizedData, DataFormat, create_unified_loader

__all__ = [
    # Main unified interface
    'UnifiedDataLoader',
    'StandardizedData',
    'DataFormat',
    'create_unified_loader',
    
    # Toyo-specific
    'ToyoDataLoader',
    'ToyoTestData',
    'ToyoCapacityData',
    'create_toyo_loader',
    
    # PNE-specific
    'PNEDataLoader',
    'PNETestData',
    'PNEChannelData',
    'create_pne_loader',
]

__version__ = "1.0.0"