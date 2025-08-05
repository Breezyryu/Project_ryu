"""
Toyo Battery Data Loader Module

This module provides functionality to load and parse battery experimental data
in Toyo format for battery life prediction preprocessing.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime
import glob

logger = logging.getLogger(__name__)


class ToyoDataLoader:
    """
    Data loader for Toyo format battery experimental data.
    
    Handles loading of multiple channel data with sequential file numbering
    and CAPACITY.LOG files for cycle information.
    """
    
    def __init__(self, src_path: str):
        """
        Initialize the Toyo data loader.
        
        Args:
            src_path: Source path containing Toyo format data
        """
        self.src_path = Path(src_path)
        if not self.src_path.exists():
            raise ValueError(f"Source path does not exist: {src_path}")
    
    def get_channel_folders(self) -> List[str]:
        """
        Get all channel folder names in the source directory.
        
        Returns:
            List of channel folder names (e.g., ['93', '86', '84', '81'])
        """
        folders = []
        for item in self.src_path.iterdir():
            if item.is_dir() and item.name.isdigit():
                folders.append(item.name)
        
        return sorted(folders, key=int, reverse=True)
    
    def _read_single_file(self, file_path: Path) -> pd.DataFrame:
        """
        Read a single Toyo format data file.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            DataFrame containing the parsed data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Skip the first metadata line (0,0,1,0,0,0,0)
            if lines and lines[0].strip().startswith('0,0,1,0,0,0,0'):
                lines = lines[1:]
            
            # Skip empty lines and find header
            data_lines = [line.strip() for line in lines if line.strip()]
            
            if not data_lines:
                logger.warning(f"No data found in file: {file_path}")
                return pd.DataFrame()
            
            # Find header line
            header_line = data_lines[0]
            if not header_line.startswith('Date,Time'):
                logger.warning(f"Unexpected header format in file: {file_path}")
                return pd.DataFrame()
            
            # Create DataFrame
            data_rows = data_lines[1:]
            if not data_rows:
                logger.warning(f"No data rows found in file: {file_path}")
                return pd.DataFrame()
            
            # Parse CSV data
            columns = [col.strip() for col in header_line.split(',')]
            rows = []
            
            for row_line in data_rows:
                row_data = [cell.strip() for cell in row_line.split(',')]
                if len(row_data) == len(columns):
                    rows.append(row_data)
                else:
                    logger.debug(f"Skipping malformed row in {file_path}: {row_line}")
            
            if not rows:
                logger.warning(f"No valid data rows found in file: {file_path}")
                return pd.DataFrame()
            
            df = pd.DataFrame(rows, columns=columns)
            
            # Add file info
            df['source_file'] = file_path.name
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return pd.DataFrame()
    
    def load_channel_data(self, channel: str) -> pd.DataFrame:
        """
        Load all data files for a specific channel.
        
        Args:
            channel: Channel name (e.g., '93', '86')
            
        Returns:
            Combined DataFrame containing all data for the channel
        """
        channel_path = self.src_path / channel
        if not channel_path.exists():
            raise ValueError(f"Channel folder does not exist: {channel_path}")
        
        # Find all data files (files without extension with numeric names)
        data_files = []
        for file_path in channel_path.iterdir():
            if file_path.is_file() and file_path.suffix == '' and file_path.name.isdigit():
                data_files.append(file_path)
        
        if not data_files:
            logger.warning(f"No data files found in channel: {channel}")
            return pd.DataFrame()
        
        # Sort files by numeric name
        data_files.sort(key=lambda x: int(x.name))
        
        logger.info(f"Loading {len(data_files)} files for channel {channel}")
        
        # Load and combine all files
        all_dfs = []
        for file_path in data_files:
            df = self._read_single_file(file_path)
            if not df.empty:
                all_dfs.append(df)
        
        if not all_dfs:
            logger.warning(f"No valid data loaded for channel: {channel}")
            return pd.DataFrame()
        
        # Combine all DataFrames
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df['channel'] = channel
        
        logger.info(f"Loaded {len(combined_df)} records for channel {channel}")
        
        return combined_df
    
    def load_capacity_log(self, channel: str) -> Optional[pd.DataFrame]:
        """
        Load CAPACITY.LOG file for a specific channel.
        
        Args:
            channel: Channel name
            
        Returns:
            DataFrame containing capacity log data or None if not found
        """
        capacity_file = self.src_path / channel / "CAPACITY.LOG"
        
        if not capacity_file.exists():
            logger.warning(f"CAPACITY.LOG not found for channel {channel}")
            return None
        
        try:
            # Read capacity log file
            with open(capacity_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find header and data
            data_lines = [line.strip() for line in lines if line.strip()]
            
            if not data_lines:
                logger.warning(f"Empty CAPACITY.LOG file for channel {channel}")
                return None
            
            # Parse CSV data
            header = data_lines[0]
            columns = [col.strip() for col in header.split(',')]
            
            rows = []
            for row_line in data_lines[1:]:
                row_data = [cell.strip() for cell in row_line.split(',')]
                if len(row_data) == len(columns):
                    rows.append(row_data)
            
            if not rows:
                logger.warning(f"No data rows in CAPACITY.LOG for channel {channel}")
                return None
            
            df = pd.DataFrame(rows, columns=columns)
            df['channel'] = channel
            
            logger.info(f"Loaded {len(df)} capacity records for channel {channel}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading CAPACITY.LOG for channel {channel}: {e}")
            return None
    
    def load_all_channels(self) -> Dict[str, pd.DataFrame]:
        """
        Load data for all available channels.
        
        Returns:
            Dictionary mapping channel names to their combined DataFrames
        """
        channels = self.get_channel_folders()
        logger.info(f"Found channels: {channels}")
        
        channel_data = {}
        
        for channel in channels:
            try:
                df = self.load_channel_data(channel)
                if not df.empty:
                    channel_data[channel] = df
                    logger.info(f"Successfully loaded channel {channel}")
                else:
                    logger.warning(f"No data loaded for channel {channel}")
            except Exception as e:
                logger.error(f"Failed to load channel {channel}: {e}")
        
        return channel_data
    
    def load_all_capacity_logs(self) -> Dict[str, pd.DataFrame]:
        """
        Load CAPACITY.LOG files for all available channels.
        
        Returns:
            Dictionary mapping channel names to their capacity log DataFrames
        """
        channels = self.get_channel_folders()
        capacity_data = {}
        
        for channel in channels:
            try:
                df = self.load_capacity_log(channel)
                if df is not None:
                    capacity_data[channel] = df
                    logger.info(f"Successfully loaded capacity log for channel {channel}")
            except Exception as e:
                logger.error(f"Failed to load capacity log for channel {channel}: {e}")
        
        return capacity_data
    
    def get_data_summary(self) -> Dict[str, Dict[str, Union[int, str]]]:
        """
        Get summary information about available data.
        
        Returns:
            Dictionary containing summary statistics for each channel
        """
        channels = self.get_channel_folders()
        summary = {}
        
        for channel in channels:
            channel_path = self.src_path / channel
            
            # Count data files
            data_files = list(channel_path.glob('[0-9]*'))
            data_files = [f for f in data_files if f.is_file() and f.suffix == '']
            
            # Check for capacity log
            capacity_log_exists = (channel_path / "CAPACITY.LOG").exists()
            
            summary[channel] = {
                'data_files': len(data_files),
                'capacity_log': 'Yes' if capacity_log_exists else 'No',
                'path': str(channel_path)
            }
        
        return summary