"""
Toyo Battery Data Visualizer Module

This module provides comprehensive visualization functionality for battery 
experimental data analysis and battery life prediction insights.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from pathlib import Path
import warnings

# Set style
plt.style.use('default')
sns.set_palette("husl")

logger = logging.getLogger(__name__)


class ToyoVisualizer:
    """
    Comprehensive visualizer for Toyo battery experimental data.
    
    Provides various plotting functions for battery analysis including
    voltage curves, capacity fade, charge/discharge analysis, and more.
    """
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8), dpi: int = 100):
        """
        Initialize the visualizer.
        
        Args:
            figsize: Default figure size for plots
            dpi: Default DPI for plots
        """
        self.figsize = figsize
        self.dpi = dpi
        self.colors = plt.cm.tab10(np.linspace(0, 1, 10))
        
    def plot_voltage_curves(
        self, 
        voltage_curves: Dict[int, pd.DataFrame], 
        channel: str,
        cycles_to_plot: Optional[List[int]] = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot voltage curves for selected cycles.
        
        Args:
            voltage_curves: Dictionary of cycle voltage curves
            channel: Channel name for title
            cycles_to_plot: List of specific cycles to plot (None for all)
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure object
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, dpi=self.dpi)
        
        if not voltage_curves:
            ax1.text(0.5, 0.5, 'No voltage curve data available', 
                    ha='center', va='center', transform=ax1.transAxes)
            ax2.text(0.5, 0.5, 'No voltage curve data available', 
                    ha='center', va='center', transform=ax2.transAxes)
            return fig
        
        cycles = list(voltage_curves.keys())
        if cycles_to_plot:
            cycles = [c for c in cycles if c in cycles_to_plot]
        
        # Limit to reasonable number of cycles for visibility
        if len(cycles) > 20:
            step = len(cycles) // 20
            cycles = cycles[::step]
        
        # Plot voltage vs time
        for i, cycle in enumerate(cycles):
            df = voltage_curves[cycle]
            if df.empty or 'voltage_v' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            
            # Plot vs time if available
            if 'datetime' in df.columns and not df['datetime'].isna().all():
                time_data = df['datetime']
                ax1.plot(time_data, df['voltage_v'], 
                        color=color, alpha=0.7, linewidth=1.5,
                        label=f'Cycle {cycle}')
            elif 'pass_time_sec' in df.columns:
                time_data = df['pass_time_sec'] / 3600  # Convert to hours
                ax1.plot(time_data, df['voltage_v'], 
                        color=color, alpha=0.7, linewidth=1.5,
                        label=f'Cycle {cycle}')
        
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Voltage (V)')
        ax1.set_title(f'Voltage vs Time - Channel {channel}')
        ax1.grid(True, alpha=0.3)
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Plot voltage vs capacity if current data available
        for i, cycle in enumerate(cycles):
            df = voltage_curves[cycle]
            if df.empty or 'voltage_v' not in df.columns or 'current_a' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            
            # Calculate cumulative capacity (simple integration)
            if 'pass_time_sec' in df.columns:
                dt = df['pass_time_sec'].diff().fillna(0) / 3600  # hours
                capacity = (df['current_a'].abs() * dt).cumsum()
                
                ax2.plot(capacity, df['voltage_v'], 
                        color=color, alpha=0.7, linewidth=1.5,
                        label=f'Cycle {cycle}')
        
        ax2.set_xlabel('Capacity (Ah)')
        ax2.set_ylabel('Voltage (V)')
        ax2.set_title(f'Voltage vs Capacity - Channel {channel}')
        ax2.grid(True, alpha=0.3)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Voltage curves plot saved to {save_path}")
        
        return fig
    
    def plot_capacity_fade(
        self,
        capacity_fade_data: Dict[str, pd.DataFrame],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot capacity fade over cycles for all channels.
        
        Args:
            capacity_fade_data: Dictionary of capacity fade DataFrames by channel
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10), dpi=self.dpi)
        
        if not capacity_fade_data:
            for ax in [ax1, ax2, ax3, ax4]:
                ax.text(0.5, 0.5, 'No capacity fade data available', 
                       ha='center', va='center', transform=ax.transAxes)
            return fig
        
        # Plot capacity vs cycle
        for i, (channel, df) in enumerate(capacity_fade_data.items()):
            if df.empty or 'cycle' not in df.columns or 'capacity_ah' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            ax1.plot(df['cycle'], df['capacity_ah'], 
                    marker='o', markersize=4, linewidth=2,
                    color=color, label=f'Channel {channel}')
        
        ax1.set_xlabel('Cycle Number')
        ax1.set_ylabel('Capacity (Ah)')
        ax1.set_title('Capacity vs Cycle')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot capacity retention vs cycle
        for i, (channel, df) in enumerate(capacity_fade_data.items()):
            if df.empty or 'cycle' not in df.columns or 'capacity_retention' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            ax2.plot(df['cycle'], df['capacity_retention'], 
                    marker='o', markersize=4, linewidth=2,
                    color=color, label=f'Channel {channel}')
        
        ax2.set_xlabel('Cycle Number')
        ax2.set_ylabel('Capacity Retention (%)')
        ax2.set_title('Capacity Retention vs Cycle')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Plot capacity fade vs cycle
        for i, (channel, df) in enumerate(capacity_fade_data.items()):
            if df.empty or 'cycle' not in df.columns or 'capacity_fade' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            ax3.plot(df['cycle'], df['capacity_fade'], 
                    marker='o', markersize=4, linewidth=2,
                    color=color, label=f'Channel {channel}')
        
        ax3.set_xlabel('Cycle Number')
        ax3.set_ylabel('Capacity Fade (%)')
        ax3.set_title('Capacity Fade vs Cycle')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        # Plot fade rate vs cycle
        for i, (channel, df) in enumerate(capacity_fade_data.items()):
            if df.empty or 'cycle' not in df.columns or 'fade_rate' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            # Remove NaN values for fade rate
            valid_data = df.dropna(subset=['fade_rate'])
            if not valid_data.empty:
                ax4.plot(valid_data['cycle'], valid_data['fade_rate'], 
                        marker='o', markersize=4, linewidth=2,
                        color=color, label=f'Channel {channel}', alpha=0.7)
        
        ax4.set_xlabel('Cycle Number')
        ax4.set_ylabel('Fade Rate (%/cycle)')
        ax4.set_title('Capacity Fade Rate vs Cycle')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Capacity fade plot saved to {save_path}")
        
        return fig
    
    def plot_charge_discharge_analysis(
        self,
        charge_discharge_data: Dict[str, Dict[str, pd.DataFrame]],
        channel: str,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot charge and discharge analysis for a specific channel.
        
        Args:
            charge_discharge_data: Dictionary of charge/discharge data by channel
            channel: Channel to analyze
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10), dpi=self.dpi)
        
        if channel not in charge_discharge_data:
            for ax in [ax1, ax2, ax3, ax4]:
                ax.text(0.5, 0.5, f'No data available for channel {channel}', 
                       ha='center', va='center', transform=ax.transAxes)
            return fig
        
        data = charge_discharge_data[channel]
        charge_df = data.get('charge', pd.DataFrame())
        discharge_df = data.get('discharge', pd.DataFrame())
        
        # Plot voltage vs time for charge/discharge
        if not charge_df.empty and 'voltage_v' in charge_df.columns:
            if 'datetime' in charge_df.columns:
                ax1.plot(charge_df['datetime'], charge_df['voltage_v'], 
                        color='red', alpha=0.6, linewidth=1, label='Charge')
            elif 'pass_time_sec' in charge_df.columns:
                ax1.plot(charge_df['pass_time_sec']/3600, charge_df['voltage_v'], 
                        color='red', alpha=0.6, linewidth=1, label='Charge')
        
        if not discharge_df.empty and 'voltage_v' in discharge_df.columns:
            if 'datetime' in discharge_df.columns:
                ax1.plot(discharge_df['datetime'], discharge_df['voltage_v'], 
                        color='blue', alpha=0.6, linewidth=1, label='Discharge')
            elif 'pass_time_sec' in discharge_df.columns:
                ax1.plot(discharge_df['pass_time_sec']/3600, discharge_df['voltage_v'], 
                        color='blue', alpha=0.6, linewidth=1, label='Discharge')
        
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Voltage (V)')
        ax1.set_title(f'Charge/Discharge Voltage - Channel {channel}')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot current vs time
        if not charge_df.empty and 'current_a' in charge_df.columns:
            if 'datetime' in charge_df.columns:
                ax2.plot(charge_df['datetime'], charge_df['current_a'], 
                        color='red', alpha=0.6, linewidth=1, label='Charge')
            elif 'pass_time_sec' in charge_df.columns:
                ax2.plot(charge_df['pass_time_sec']/3600, charge_df['current_a'], 
                        color='red', alpha=0.6, linewidth=1, label='Charge')
        
        if not discharge_df.empty and 'current_a' in discharge_df.columns:
            if 'datetime' in discharge_df.columns:
                ax2.plot(discharge_df['datetime'], discharge_df['current_a'], 
                        color='blue', alpha=0.6, linewidth=1, label='Discharge')
            elif 'pass_time_sec' in discharge_df.columns:
                ax2.plot(discharge_df['pass_time_sec']/3600, discharge_df['current_a'], 
                        color='blue', alpha=0.6, linewidth=1, label='Discharge')
        
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Current (A)')
        ax2.set_title(f'Charge/Discharge Current - Channel {channel}')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Plot voltage vs current (I-V characteristics)
        if not charge_df.empty and 'voltage_v' in charge_df.columns and 'current_a' in charge_df.columns:
            ax3.scatter(charge_df['current_a'], charge_df['voltage_v'], 
                       c='red', alpha=0.3, s=1, label='Charge')
        
        if not discharge_df.empty and 'voltage_v' in discharge_df.columns and 'current_a' in discharge_df.columns:
            ax3.scatter(discharge_df['current_a'], discharge_df['voltage_v'], 
                       c='blue', alpha=0.3, s=1, label='Discharge')
        
        ax3.set_xlabel('Current (A)')
        ax3.set_ylabel('Voltage (V)')
        ax3.set_title(f'I-V Characteristics - Channel {channel}')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        # Plot temperature vs time
        combined_df = pd.concat([charge_df, discharge_df], ignore_index=True)
        if not combined_df.empty and 'temperature_deg' in combined_df.columns:
            if 'datetime' in combined_df.columns:
                ax4.plot(combined_df['datetime'], combined_df['temperature_deg'], 
                        color='green', alpha=0.6, linewidth=1)
            elif 'pass_time_sec' in combined_df.columns:
                ax4.plot(combined_df['pass_time_sec']/3600, combined_df['temperature_deg'], 
                        color='green', alpha=0.6, linewidth=1)
        
        ax4.set_xlabel('Time')
        ax4.set_ylabel('Temperature (°C)')
        ax4.set_title(f'Temperature Profile - Channel {channel}')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Charge/discharge analysis plot saved to {save_path}")
        
        return fig
    
    def plot_energy_metrics(
        self,
        energy_metrics: Dict[str, pd.DataFrame],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot energy-related metrics for all channels.
        
        Args:
            energy_metrics: Dictionary of energy metrics DataFrames by channel
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10), dpi=self.dpi)
        
        if not energy_metrics:
            for ax in [ax1, ax2, ax3, ax4]:
                ax.text(0.5, 0.5, 'No energy metrics data available', 
                       ha='center', va='center', transform=ax.transAxes)
            return fig
        
        # Plot average voltage vs cycle
        for i, (channel, df) in enumerate(energy_metrics.items()):
            if df.empty or 'cycle' not in df.columns or 'avg_voltage' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            valid_data = df.dropna(subset=['avg_voltage'])
            if not valid_data.empty:
                ax1.plot(valid_data['cycle'], valid_data['avg_voltage'], 
                        marker='o', markersize=3, linewidth=1.5,
                        color=color, label=f'Channel {channel}')
        
        ax1.set_xlabel('Cycle Number')
        ax1.set_ylabel('Average Voltage (V)')
        ax1.set_title('Average Voltage vs Cycle')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot average current vs cycle
        for i, (channel, df) in enumerate(energy_metrics.items()):
            if df.empty or 'cycle' not in df.columns or 'avg_current' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            valid_data = df.dropna(subset=['avg_current'])
            if not valid_data.empty:
                ax2.plot(valid_data['cycle'], valid_data['avg_current'], 
                        marker='o', markersize=3, linewidth=1.5,
                        color=color, label=f'Channel {channel}')
        
        ax2.set_xlabel('Cycle Number')
        ax2.set_ylabel('Average Current (A)')
        ax2.set_title('Average Current vs Cycle')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Plot average temperature vs cycle
        for i, (channel, df) in enumerate(energy_metrics.items()):
            if df.empty or 'cycle' not in df.columns or 'avg_temperature' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            valid_data = df.dropna(subset=['avg_temperature'])
            if not valid_data.empty:
                ax3.plot(valid_data['cycle'], valid_data['avg_temperature'], 
                        marker='o', markersize=3, linewidth=1.5,
                        color=color, label=f'Channel {channel}')
        
        ax3.set_xlabel('Cycle Number')
        ax3.set_ylabel('Average Temperature (°C)')
        ax3.set_title('Average Temperature vs Cycle')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        # Plot energy vs cycle (if available)
        for i, (channel, df) in enumerate(energy_metrics.items()):
            if df.empty or 'cycle' not in df.columns or 'energy_wh' not in df.columns:
                continue
                
            color = self.colors[i % len(self.colors)]
            valid_data = df.dropna(subset=['energy_wh'])
            if not valid_data.empty:
                ax4.plot(valid_data['cycle'], valid_data['energy_wh'], 
                        marker='o', markersize=3, linewidth=1.5,
                        color=color, label=f'Channel {channel}')
        
        ax4.set_xlabel('Cycle Number')
        ax4.set_ylabel('Energy (Wh)')
        ax4.set_title('Energy vs Cycle')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Energy metrics plot saved to {save_path}")
        
        return fig
    
    def plot_data_overview(
        self,
        processed_data: Dict[str, Any],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create an overview plot showing summary statistics for all channels.
        
        Args:
            processed_data: Dictionary containing all processed data
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure object
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10), dpi=self.dpi)
        
        summary = processed_data.get('summary', {})
        
        if not summary:
            for ax in [ax1, ax2, ax3, ax4]:
                ax.text(0.5, 0.5, 'No summary data available', 
                       ha='center', va='center', transform=ax.transAxes)
            return fig
        
        channels = list(summary.keys())
        
        # Plot total records per channel
        total_records = [summary[ch].get('total_records', 0) for ch in channels]
        bars1 = ax1.bar(channels, total_records, color=self.colors[:len(channels)])
        ax1.set_xlabel('Channel')
        ax1.set_ylabel('Total Records')
        ax1.set_title('Total Records per Channel')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, value in zip(bars1, total_records):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(total_records)*0.01,
                    f'{value:,}', ha='center', va='bottom', fontsize=9)
        
        # Plot total cycles per channel
        total_cycles = [summary[ch].get('total_cycles', 0) for ch in channels]
        bars2 = ax2.bar(channels, total_cycles, color=self.colors[:len(channels)])
        ax2.set_xlabel('Channel')
        ax2.set_ylabel('Total Cycles')
        ax2.set_title('Total Cycles per Channel')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, value in zip(bars2, total_cycles):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(total_cycles)*0.01,
                    f'{value}', ha='center', va='bottom', fontsize=9)
        
        # Plot voltage ranges
        voltage_ranges = []
        voltage_labels = []
        for ch in channels:
            v_range = summary[ch].get('voltage_range')
            if v_range and len(v_range) == 2:
                voltage_ranges.append([v_range[0], v_range[1]])
                voltage_labels.append(ch)
        
        if voltage_ranges:
            voltage_ranges = np.array(voltage_ranges)
            x_pos = np.arange(len(voltage_labels))
            ax3.errorbar(x_pos, voltage_ranges[:, 1], 
                        yerr=[voltage_ranges[:, 1] - voltage_ranges[:, 0], 
                              np.zeros(len(voltage_ranges))],
                        fmt='o', capsize=5, capthick=2, linewidth=2)
            ax3.set_xticks(x_pos)
            ax3.set_xticklabels(voltage_labels)
            ax3.set_xlabel('Channel')
            ax3.set_ylabel('Voltage Range (V)')
            ax3.set_title('Voltage Ranges per Channel')
            ax3.grid(True, alpha=0.3)
        
        # Plot current ranges
        current_ranges = []
        current_labels = []
        for ch in channels:
            c_range = summary[ch].get('current_range')
            if c_range and len(c_range) == 2:
                current_ranges.append([c_range[0], c_range[1]])
                current_labels.append(ch)
        
        if current_ranges:
            current_ranges = np.array(current_ranges)
            x_pos = np.arange(len(current_labels))
            ax4.errorbar(x_pos, current_ranges[:, 1], 
                        yerr=[current_ranges[:, 1] - current_ranges[:, 0], 
                              np.zeros(len(current_ranges))],
                        fmt='s', capsize=5, capthick=2, linewidth=2)
            ax4.set_xticks(x_pos)
            ax4.set_xticklabels(current_labels)
            ax4.set_xlabel('Channel')
            ax4.set_ylabel('Current Range (A)')
            ax4.set_title('Current Ranges per Channel')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Data overview plot saved to {save_path}")
        
        return fig
    
    def create_comprehensive_report(
        self,
        processed_data: Dict[str, Any],
        capacity_data: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, str]:
        """
        Create a comprehensive visualization report.
        
        Args:
            processed_data: Processed battery data
            capacity_data: Processed capacity data
            output_dir: Directory to save all plots
            
        Returns:
            Dictionary mapping plot names to file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_plots = {}
        
        try:
            # Data overview plot
            fig1 = self.plot_data_overview(processed_data)
            path1 = output_path / "01_data_overview.png"
            fig1.savefig(path1, dpi=self.dpi, bbox_inches='tight')
            saved_plots['data_overview'] = str(path1)
            plt.close(fig1)
            
            # Capacity fade plot
            if capacity_data and 'capacity_fade' in capacity_data:
                fig2 = self.plot_capacity_fade(capacity_data['capacity_fade'])
                path2 = output_path / "02_capacity_fade.png"
                fig2.savefig(path2, dpi=self.dpi, bbox_inches='tight')
                saved_plots['capacity_fade'] = str(path2)
                plt.close(fig2)
            
            # Energy metrics plot
            if 'energy_metrics' in processed_data:
                fig3 = self.plot_energy_metrics(processed_data['energy_metrics'])
                path3 = output_path / "03_energy_metrics.png"
                fig3.savefig(path3, dpi=self.dpi, bbox_inches='tight')
                saved_plots['energy_metrics'] = str(path3)
                plt.close(fig3)
            
            # Individual channel plots
            if 'voltage_curves' in processed_data:
                for channel, curves in processed_data['voltage_curves'].items():
                    fig4 = self.plot_voltage_curves(curves, channel)
                    path4 = output_path / f"04_voltage_curves_channel_{channel}.png"
                    fig4.savefig(path4, dpi=self.dpi, bbox_inches='tight')
                    saved_plots[f'voltage_curves_{channel}'] = str(path4)
                    plt.close(fig4)
            
            # Charge/discharge analysis for each channel
            if 'charge_discharge_cycles' in processed_data:
                for channel in processed_data['charge_discharge_cycles'].keys():
                    fig5 = self.plot_charge_discharge_analysis(
                        processed_data['charge_discharge_cycles'], channel
                    )
                    path5 = output_path / f"05_charge_discharge_channel_{channel}.png"
                    fig5.savefig(path5, dpi=self.dpi, bbox_inches='tight')
                    saved_plots[f'charge_discharge_{channel}'] = str(path5)
                    plt.close(fig5)
            
            logger.info(f"Comprehensive report created with {len(saved_plots)} plots in {output_dir}")
            
        except Exception as e:
            logger.error(f"Error creating comprehensive report: {e}")
        
        return saved_plots