"""
Battery Data Preprocessing GUI

Modern web-based interface for battery data preprocessing, visualization, and analysis.
Built with Streamlit for rapid development and deployment.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
import logging
from typing import Optional, Dict, Any
import tempfile
import zipfile
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from preprocess.loaders import create_unified_loader, DataFormat, StandardizedData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatteryDataGUI:
    """Main GUI class for battery data preprocessing."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.setup_page_config()
        self.initialize_session_state()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Battery Data Preprocessor",
            page_icon="🔋",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main > div {
            padding-top: 2rem;
        }
        .stMetric {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .status-success {
            color: #28a745;
            font-weight: bold;
        }
        .status-error {
            color: #dc3545;
            font-weight: bold;
        }
        .status-warning {
            color: #ffc107;
            font-weight: bold;
        }
        .data-preview {
            max-height: 400px;
            overflow-y: auto;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'data_loader' not in st.session_state:
            st.session_state.data_loader = None
        if 'standardized_data' not in st.session_state:
            st.session_state.standardized_data = None
        if 'data_summary' not in st.session_state:
            st.session_state.data_summary = None
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = "Ready"
    
    def render_header(self):
        """Render application header."""
        st.title("🔋 Battery Data Preprocessor")
        st.markdown("""
        **Unified interface for processing battery testing data from multiple formats**
        - 🔄 Automatic format detection (Toyo, PNE)
        - 📊 Interactive data visualization
        - 🔍 Data quality validation
        - 📁 Multiple export formats
        """)
        st.divider()
    
    def render_sidebar(self):
        """Render sidebar with navigation and controls."""
        with st.sidebar:
            st.header("📋 Navigation")
            
            # Status indicator
            status_color = {
                "Ready": "🟢",
                "Processing": "🟡", 
                "Complete": "🔵",
                "Error": "🔴"
            }
            st.markdown(f"**Status:** {status_color.get(st.session_state.processing_status, '⚪')} {st.session_state.processing_status}")
            
            st.divider()
            
            # Data source selection
            st.subheader("📂 Data Source")
            data_source = st.radio(
                "Select data source:",
                ["Local Directory", "Upload Files"],
                help="Choose how to provide battery data"
            )
            
            return data_source
    
    def render_data_input(self, data_source: str):
        """Render data input section."""
        st.header("1️⃣ Data Input")
        
        if data_source == "Local Directory":
            col1, col2 = st.columns([3, 1])
            
            with col1:
                data_path = st.text_input(
                    "Data Directory Path:",
                    placeholder="Enter path to battery data directory",
                    help="Path to directory containing Toyo or PNE format data"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                load_button = st.button("🔍 Load Data", type="primary")
            
            if load_button and data_path:
                self.load_data_from_path(data_path)
        
        else:  # Upload Files
            uploaded_files = st.file_uploader(
                "Upload battery data files:",
                type=['csv', 'zip'],
                accept_multiple_files=True,
                help="Upload CSV files or ZIP archive containing battery data"
            )
            
            if uploaded_files:
                if st.button("🔍 Process Uploads", type="primary"):
                    self.process_uploaded_files(uploaded_files)
    
    def load_data_from_path(self, data_path: str):
        """Load data from local directory path."""
        try:
            st.session_state.processing_status = "Processing"
            
            with st.spinner("Loading and analyzing data..."):
                # Create unified loader
                loader = create_unified_loader(data_path)
                st.session_state.data_loader = loader
                
                # Get summary
                summary = loader.get_summary()
                st.session_state.data_summary = summary
                
                # Load standardized data
                standardized = loader.load_data()
                st.session_state.standardized_data = standardized
                
                st.session_state.processing_status = "Complete"
                st.success("✅ Data loaded successfully!")
                
        except Exception as e:
            st.session_state.processing_status = "Error"
            st.error(f"❌ Error loading data: {str(e)}")
            logger.error(f"Error loading data from {data_path}: {e}")
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files."""
        try:
            st.session_state.processing_status = "Processing"
            
            with st.spinner("Processing uploaded files..."):
                # Create temporary directory for uploaded files
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    # Save uploaded files
                    for uploaded_file in uploaded_files:
                        if uploaded_file.name.endswith('.zip'):
                            # Extract ZIP file
                            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                                zip_ref.extractall(temp_path)
                        else:
                            # Save individual file
                            file_path = temp_path / uploaded_file.name
                            with open(file_path, 'wb') as f:
                                f.write(uploaded_file.getvalue())
                    
                    # Try to load data from temporary directory
                    loader = create_unified_loader(temp_path)
                    st.session_state.data_loader = loader
                    
                    summary = loader.get_summary()
                    st.session_state.data_summary = summary
                    
                    standardized = loader.load_data()
                    st.session_state.standardized_data = standardized
                
                st.session_state.processing_status = "Complete"
                st.success("✅ Files processed successfully!")
                
        except Exception as e:
            st.session_state.processing_status = "Error"
            st.error(f"❌ Error processing files: {str(e)}")
            logger.error(f"Error processing uploaded files: {e}")
    
    def render_data_overview(self):
        """Render data overview section."""
        if st.session_state.data_summary is None:
            return
        
        st.header("2️⃣ Data Overview")
        
        summary = st.session_state.data_summary
        
        # Format detection
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📋 Format",
                value=summary.get('format', 'Unknown').upper()
            )
        
        with col2:
            if 'total_test_files' in summary:
                st.metric(
                    label="📄 Test Files", 
                    value=summary['total_test_files']
                )
            elif 'total_directories' in summary:
                st.metric(
                    label="📁 Directories",
                    value=summary['total_directories']
                )
        
        with col3:
            if 'total_records' in summary:
                st.metric(
                    label="📊 Records",
                    value=f"{summary['total_records']:,}"
                )
        
        with col4:
            if st.session_state.standardized_data:
                data_size = len(st.session_state.standardized_data.data)
                st.metric(
                    label="🔄 Standardized",
                    value=f"{data_size:,}"
                )
        
        # Detailed information
        with st.expander("📋 Detailed Information", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Format Details")
                for key, value in summary.items():
                    if key != 'details':
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            with col2:
                if st.session_state.standardized_data:
                    st.subheader("Data Structure")
                    data = st.session_state.standardized_data.data
                    st.write(f"**Shape:** {data.shape}")
                    st.write(f"**Columns:** {len(data.columns)}")
                    
                    if 'Datetime' in data.columns:
                        date_range = (data['Datetime'].min(), data['Datetime'].max())
                        st.write(f"**Date Range:** {date_range[0]} to {date_range[1]}")
    
    def render_data_preview(self):
        """Render data preview section."""
        if st.session_state.standardized_data is None:
            return
        
        st.header("3️⃣ Data Preview")
        
        data = st.session_state.standardized_data.data
        
        if data.empty:
            st.warning("⚠️ No data available for preview")
            return
        
        # Preview controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            preview_rows = st.slider(
                "Number of rows to preview:",
                min_value=5,
                max_value=min(1000, len(data)),
                value=10,
                step=5
            )
        
        with col2:
            if st.button("🔄 Refresh Preview"):
                st.rerun()
        
        with col3:
            show_info = st.checkbox("Show Info", value=True)
        
        # Data preview tabs
        tab1, tab2, tab3 = st.tabs(["📊 Data Sample", "📈 Statistics", "🔍 Column Info"])
        
        with tab1:
            st.markdown('<div class="data-preview">', unsafe_allow_html=True)
            st.dataframe(
                data.head(preview_rows),
                use_container_width=True,
                height=400
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                st.dataframe(
                    data[numeric_columns].describe(),
                    use_container_width=True
                )
            else:
                st.info("📋 No numeric columns found for statistics")
        
        with tab3:
            if show_info:
                col_info = []
                for col in data.columns:
                    col_info.append({
                        'Column': col,
                        'Type': str(data[col].dtype),
                        'Non-null': data[col].count(),
                        'Null': data[col].isnull().sum(),
                        'Unique': data[col].nunique()
                    })
                
                info_df = pd.DataFrame(col_info)
                st.dataframe(info_df, use_container_width=True)
    
    def render_visualizations(self):
        """Render data visualization section."""
        if st.session_state.standardized_data is None:
            return
        
        st.header("4️⃣ Data Visualization")
        
        data = st.session_state.standardized_data.data
        
        if data.empty:
            st.warning("⚠️ No data available for visualization")
            return
        
        # Visualization controls
        col1, col2 = st.columns(2)
        
        with col1:
            # Get numeric columns for plotting
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            if 'Datetime' in data.columns:
                numeric_cols.insert(0, 'Datetime')
            
            x_axis = st.selectbox("X-axis:", options=numeric_cols, index=0 if numeric_cols else None)
        
        with col2:
            y_axis = st.selectbox(
                "Y-axis:", 
                options=[col for col in numeric_cols if col != x_axis],
                index=1 if len(numeric_cols) > 1 else 0
            )
        
        if x_axis and y_axis:
            # Create visualizations
            tab1, tab2, tab3 = st.tabs(["📈 Time Series", "🔄 Cycle Analysis", "🌡️ Environmental"])
            
            with tab1:
                self.create_time_series_plot(data, x_axis, y_axis)
            
            with tab2:
                self.create_cycle_analysis_plot(data)
            
            with tab3:
                self.create_environmental_plot(data)
    
    def create_time_series_plot(self, data: pd.DataFrame, x_axis: str, y_axis: str):
        """Create time series visualization."""
        try:
            fig = px.line(
                data.head(1000),  # Limit points for performance
                x=x_axis,
                y=y_axis,
                title=f"{y_axis} vs {x_axis}",
                hover_data=['Cycle'] if 'Cycle' in data.columns else None
            )
            
            fig.update_layout(
                height=500,
                xaxis_title=x_axis,
                yaxis_title=y_axis,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Error creating time series plot: {str(e)}")
    
    def create_cycle_analysis_plot(self, data: pd.DataFrame):
        """Create cycle analysis visualization."""
        try:
            if 'Cycle' not in data.columns:
                st.info("📋 Cycle information not available")
                return
            
            # Voltage vs Cycle
            if 'Voltage_V' in data.columns:
                cycle_voltage = data.groupby('Cycle')['Voltage_V'].agg(['mean', 'min', 'max']).reset_index()
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=cycle_voltage['Cycle'],
                    y=cycle_voltage['mean'],
                    mode='lines+markers',
                    name='Average Voltage',
                    line=dict(color='blue')
                ))
                
                fig.add_trace(go.Scatter(
                    x=cycle_voltage['Cycle'],
                    y=cycle_voltage['max'],
                    fill=None,
                    mode='lines',
                    name='Max Voltage',
                    line=dict(color='rgba(0,100,80,0)')
                ))
                
                fig.add_trace(go.Scatter(
                    x=cycle_voltage['Cycle'],
                    y=cycle_voltage['min'],
                    fill='tonexty',
                    mode='lines',
                    name='Min Voltage',
                    line=dict(color='rgba(0,100,80,0)')
                ))
                
                fig.update_layout(
                    title="Voltage Analysis by Cycle",
                    xaxis_title="Cycle",
                    yaxis_title="Voltage (V)",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📋 Voltage data not available for cycle analysis")
                
        except Exception as e:
            st.error(f"❌ Error creating cycle analysis: {str(e)}")
    
    def create_environmental_plot(self, data: pd.DataFrame):
        """Create environmental conditions visualization."""
        try:
            temp_col = None
            for col in ['Temperature_C', 'Temp1[Deg]', 'Temperature1']:
                if col in data.columns:
                    temp_col = col
                    break
            
            if temp_col is None:
                st.info("📋 Temperature data not available")
                return
            
            # Temperature distribution
            fig = px.histogram(
                data,
                x=temp_col,
                title="Temperature Distribution",
                nbins=50,
                marginal="box"
            )
            
            fig.update_layout(
                xaxis_title="Temperature (°C)",
                yaxis_title="Count",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Error creating environmental plot: {str(e)}")
    
    def render_export_section(self):
        """Render data export section."""
        if st.session_state.standardized_data is None:
            return
        
        st.header("5️⃣ Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            export_format = st.selectbox(
                "Export Format:",
                ["CSV", "Parquet", "HDF5"],
                help="Choose output format for standardized data"
            )
        
        with col2:
            filename = st.text_input(
                "Filename:",
                value=f"battery_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                help="Output filename (extension will be added automatically)"
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            if st.button("📁 Export Data", type="primary"):
                self.export_data(export_format.lower(), filename)
        
        # Export summary
        data = st.session_state.standardized_data.data
        st.info(f"📊 **Export Preview:** {data.shape[0]:,} rows × {data.shape[1]} columns")
    
    def export_data(self, format: str, filename: str):
        """Export standardized data to specified format."""
        try:
            data = st.session_state.standardized_data.data
            
            # Create export data
            if format == 'csv':
                csv_data = data.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv_data,
                    file_name=f"{filename}.csv",
                    mime="text/csv"
                )
            
            elif format == 'parquet':
                parquet_data = data.to_parquet(index=False)
                st.download_button(
                    label="💾 Download Parquet",
                    data=parquet_data,
                    file_name=f"{filename}.parquet",
                    mime="application/octet-stream"
                )
            
            st.success("✅ Export ready for download!")
            
        except Exception as e:
            st.error(f"❌ Error exporting data: {str(e)}")
    
    def run(self):
        """Run the main GUI application."""
        self.render_header()
        
        # Sidebar
        data_source = self.render_sidebar()
        
        # Main content
        self.render_data_input(data_source)
        
        # Show subsequent sections only if data is loaded
        if st.session_state.data_summary is not None:
            self.render_data_overview()
            self.render_data_preview()
            self.render_visualizations()
            self.render_export_section()


def main():
    """Main application entry point."""
    try:
        gui = BatteryDataGUI()
        gui.run()
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        logger.error(f"Application error: {e}")


if __name__ == "__main__":
    main()