"""
Toyo Battery Data Loader

Loads and processes Toyo1/Toyo2 format battery testing data.
Structure: data_path/93/000001, 000002, etc. + CAPACITY.LOG
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToyoTestData:
    """Container for Toyo test data from individual test files."""
    data: pd.DataFrame
    metadata: Dict
    file_path: Path
    
    def __post_init__(self):
        """Validate data integrity after initialization."""
        if self.data.empty:
            raise ValueError(f"Empty data in {self.file_path}")
        
        required_columns = ['Date', 'Time', 'PassTime[Sec]', 'Voltage[V]', 'Current[mA]', 'Temp1[Deg]']
        missing_cols = [col for col in required_columns if col not in self.data.columns]
        if missing_cols:
            logger.warning(f"Missing expected columns in {self.file_path}: {missing_cols}")

@dataclass  
class ToyoCapacityData:
    """Container for Toyo CAPACITY.LOG data."""
    data: pd.DataFrame
    metadata: Dict
    file_path: Path
    
    def __post_init__(self):
        """Validate capacity data integrity."""
        if self.data.empty:
            raise ValueError(f"Empty capacity data in {self.file_path}")
        
        required_columns = ['Date', 'Time', 'Cap[mAh]', 'Condition', 'Mode', 'Cycle']
        missing_cols = [col for col in required_columns if col not in self.data.columns]
        if missing_cols:
            logger.warning(f"Missing expected capacity columns in {self.file_path}: {missing_cols}")

class ToyoDataLoader:
    """
    Load and process Toyo format battery testing data.
    
    Supports both Toyo1 and Toyo2 formats with automatic format detection.
    """
    
    def __init__(self, data_path: Union[str, Path]):
        """
        Initialize Toyo data loader.
        
        Args:
            data_path: Path to Toyo data directory containing numbered folders
        """
        self.data_path = Path(data_path)
        self.format_version = None
        self._validate_data_path()
        
    def _validate_data_path(self):
        """Validate that the data path exists and contains expected structure."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {self.data_path}")
        
        # Check for numbered directories (93/, 86/, etc.)
        numbered_dirs = [d for d in self.data_path.iterdir() 
                        if d.is_dir() and d.name.isdigit()]
        
        if not numbered_dirs:
            raise ValueError(f"No numbered directories found in {self.data_path}")
        
        logger.info(f"Found {len(numbered_dirs)} numbered directories: {[d.name for d in numbered_dirs]}")
    
    def _detect_format_version(self, sample_file: Path) -> str:
        """
        Detect whether this is Toyo1 or Toyo2 format based on column structure.
        
        Args:
            sample_file: Path to a sample individual test file
            
        Returns:
            Format version: 'toyo1' or 'toyo2'
        """
        try:
            # Read first few lines to check column structure
            sample_data = pd.read_csv(sample_file, nrows=5)
            
            # Toyo1 has PassedDate column, Toyo2 doesn't
            if 'PassedDate' in sample_data.columns:
                return 'toyo1'
            else:
                return 'toyo2'
        except Exception as e:
            logger.warning(f"Could not detect format version from {sample_file}: {e}")
            return 'toyo1'  # Default to toyo1
    
    def _load_individual_file(self, file_path: Path) -> ToyoTestData:
        """
        Load individual test file (000001, 000002, etc.).
        
        Args:
            file_path: Path to individual test file
            
        Returns:
            ToyoTestData object containing parsed data
        """
        try:
            # Auto-detect format if not already detected
            if self.format_version is None:
                self.format_version = self._detect_format_version(file_path)
                logger.info(f"Detected format version: {self.format_version}")
            
            # Read CSV data
            data = pd.read_csv(file_path)
            
            # Parse datetime columns
            if 'Date' in data.columns and 'Time' in data.columns:
                data['Datetime'] = pd.to_datetime(
                    data['Date'].astype(str) + ' ' + data['Time'].astype(str),
                    format='%Y/%m/%d %H:%M:%S',
                    errors='coerce'
                )
            
            # Convert numeric columns
            numeric_columns = ['PassTime[Sec]', 'Voltage[V]', 'Current[mA]', 'Temp1[Deg]']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
            
            # Extract metadata
            metadata = {
                'file_name': file_path.name,
                'format_version': self.format_version,
                'total_records': len(data),
                'date_range': (data['Datetime'].min(), data['Datetime'].max()) if 'Datetime' in data else None,
                'voltage_range': (data['Voltage[V]'].min(), data['Voltage[V]'].max()) if 'Voltage[V]' in data else None,
                'current_range': (data['Current[mA]'].min(), data['Current[mA]'].max()) if 'Current[mA]' in data else None
            }
            
            return ToyoTestData(data=data, metadata=metadata, file_path=file_path)
            
        except Exception as e:
            logger.error(f"Error loading individual file {file_path}: {e}")
            raise
    
    def _load_capacity_file(self, file_path: Path) -> ToyoCapacityData:
        """
        Load CAPACITY.LOG file.
        
        Args:
            file_path: Path to CAPACITY.LOG file
            
        Returns:
            ToyoCapacityData object containing parsed data
        """
        try:
            # Read CSV data
            data = pd.read_csv(file_path)
            
            # Parse datetime columns
            if 'Date' in data.columns and 'Time' in data.columns:
                data['Datetime'] = pd.to_datetime(
                    data['Date'].astype(str) + ' ' + data['Time'].astype(str),
                    format='%Y/%m/%d %H:%M:%S',
                    errors='coerce'
                )
            
            # Convert numeric columns
            numeric_columns = ['Cap[mAh]', 'Pow[mWh]', 'AveVolt[V]', 'PeakVolt[V]', 'PeakTemp[Deg]', 'Ocv']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
            
            # Parse time duration columns
            time_columns = ['PassTime', 'TotlPassTime']
            for col in time_columns:
                if col in data.columns:
                    # Convert HH:MM:SS format to total seconds
                    data[f'{col}_seconds'] = pd.to_timedelta(data[col], errors='coerce').dt.total_seconds()
            
            # Extract metadata
            metadata = {
                'file_name': file_path.name,
                'total_cycles': len(data),
                'date_range': (data['Datetime'].min(), data['Datetime'].max()) if 'Datetime' in data else None,
                'capacity_range': (data['Cap[mAh]'].min(), data['Cap[mAh]'].max()) if 'Cap[mAh]' in data else None,
                'cycle_range': (data['Cycle'].min(), data['Cycle'].max()) if 'Cycle' in data else None
            }
            
            return ToyoCapacityData(data=data, metadata=metadata, file_path=file_path)
            
        except Exception as e:
            logger.error(f"Error loading capacity file {file_path}: {e}")
            raise
    
    def load_directory(self, directory: Path) -> Dict[str, Union[List[ToyoTestData], ToyoCapacityData]]:
        """
        Load all data from a numbered directory (e.g., 93/, 86/).
        
        Args:
            directory: Path to numbered directory
            
        Returns:
            Dictionary containing 'test_data' list and 'capacity_data'
        """
        result = {
            'test_data': [],
            'capacity_data': None
        }
        
        # Load individual test files
        test_files = [f for f in directory.iterdir() 
                     if f.is_file() and f.name.isdigit()]
        test_files.sort(key=lambda x: int(x.name))  # Sort numerically
        
        for file_path in test_files:
            try:
                test_data = self._load_individual_file(file_path)
                result['test_data'].append(test_data)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue
        
        # Load CAPACITY.LOG file
        capacity_file = directory / 'CAPACITY.LOG'
        if capacity_file.exists():
            try:
                result['capacity_data'] = self._load_capacity_file(capacity_file)
            except Exception as e:
                logger.error(f"Failed to load {capacity_file}: {e}")
        else:
            logger.warning(f"No CAPACITY.LOG found in {directory}")
        
        return result
    
    def load_all_data(self) -> Dict[str, Dict]:
        """
        Load all data from all numbered directories.
        
        Returns:
            Dictionary with directory names as keys, containing all loaded data
        """
        all_data = {}
        
        # Get all numbered directories
        numbered_dirs = [d for d in self.data_path.iterdir() 
                        if d.is_dir() and d.name.isdigit()]
        numbered_dirs.sort(key=lambda x: int(x.name))
        
        for directory in numbered_dirs:
            logger.info(f"Loading directory: {directory.name}")
            try:
                dir_data = self.load_directory(directory)
                all_data[directory.name] = dir_data
                
                # Log summary
                test_count = len(dir_data['test_data'])
                has_capacity = dir_data['capacity_data'] is not None
                logger.info(f"Loaded {test_count} test files, capacity data: {has_capacity}")
                
            except Exception as e:
                logger.error(f"Failed to load directory {directory}: {e}")
                continue
        
        return all_data
    
    def get_combined_capacity_data(self) -> pd.DataFrame:
        """
        Get combined capacity data from all directories.
        
        Returns:
            Combined DataFrame with capacity data from all directories
        """
        all_data = self.load_all_data()
        capacity_dfs = []
        
        for dir_name, dir_data in all_data.items():
            if dir_data['capacity_data'] is not None:
                df = dir_data['capacity_data'].data.copy()
                df['Directory'] = dir_name
                capacity_dfs.append(df)
        
        if capacity_dfs:
            return pd.concat(capacity_dfs, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def get_summary_statistics(self) -> Dict:
        """
        Get summary statistics for all loaded data.
        
        Returns:
            Dictionary containing summary statistics
        """
        all_data = self.load_all_data()
        
        summary = {
            'total_directories': len(all_data),
            'total_test_files': sum(len(data['test_data']) for data in all_data.values()),
            'directories_with_capacity': sum(1 for data in all_data.values() 
                                           if data['capacity_data'] is not None),
            'format_version': self.format_version,
            'directory_details': {}
        }
        
        for dir_name, dir_data in all_data.items():
            test_count = len(dir_data['test_data'])
            has_capacity = dir_data['capacity_data'] is not None
            
            detail = {
                'test_files': test_count,
                'has_capacity_data': has_capacity
            }
            
            # Add capacity data summary if available
            if has_capacity:
                cap_data = dir_data['capacity_data'].data
                detail['capacity_summary'] = {
                    'cycle_count': len(cap_data),
                    'capacity_mean': cap_data['Cap[mAh]'].mean() if 'Cap[mAh]' in cap_data else None,
                    'capacity_std': cap_data['Cap[mAh]'].std() if 'Cap[mAh]' in cap_data else None
                }
            
            summary['directory_details'][dir_name] = detail
        
        return summary


def create_toyo_loader(data_path: Union[str, Path]) -> ToyoDataLoader:
    """
    Factory function to create a ToyoDataLoader instance.
    
    Args:
        data_path: Path to Toyo data directory
        
    Returns:
        Configured ToyoDataLoader instance
    """
    return ToyoDataLoader(data_path)


# Example usage and validation
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Example usage
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
        
        try:
            loader = create_toyo_loader(data_path)
            summary = loader.get_summary_statistics()
            
            print(f"Data Summary:")
            print(f"Format Version: {summary['format_version']}")
            print(f"Total Directories: {summary['total_directories']}")
            print(f"Total Test Files: {summary['total_test_files']}")
            print(f"Directories with Capacity Data: {summary['directories_with_capacity']}")
            
            # Show combined capacity data sample
            combined_capacity = loader.get_combined_capacity_data()
            if not combined_capacity.empty:
                print(f"\nCombined Capacity Data Shape: {combined_capacity.shape}")
                print(f"Columns: {list(combined_capacity.columns)}")
                print("\nFirst 5 rows:")
                print(combined_capacity.head())
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python toyo_loader.py <data_path>")
        print("Example: python toyo_loader.py /path/to/toyo/data")