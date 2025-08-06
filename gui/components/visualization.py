"""
Visualization Component

처리 결과 시각화 및 그래프 표시 컴포넌트
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import json
from typing import Dict, Any, Optional, List, Tuple
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gui.base_gui import BaseGUIComponent

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class VisualizationComponent(BaseGUIComponent):
    """결과 시각화 컴포넌트"""
    
    def setup_component(self):
        """컴포넌트 설정"""
        self.current_data = None
        self.current_plots = {}
        
        self.frame = ttk.LabelFrame(self.parent, text="📊 결과 시각화", padding="10")
        
        if not MATPLOTLIB_AVAILABLE:
            self.setup_no_matplotlib_ui()
            return
        
        # 상단 컨트롤 영역
        self.setup_controls()
        
        # 그래프 영역
        self.setup_plot_area()
        
        # 하단 정보 영역
        self.setup_info_area()
    
    def setup_no_matplotlib_ui(self):
        """matplotlib 없을 때 UI"""
        info_frame = ttk.Frame(self.frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=20)
        
        ttk.Label(info_frame, text="📊 시각화 기능을 사용하려면 matplotlib가 필요합니다.", 
                 font=('Segoe UI', 12), foreground='#666666').grid(row=0, column=0, pady=10)
        
        ttk.Label(info_frame, text="설치 명령: pip install matplotlib pandas", 
                 font=('Consolas', 10), foreground='#333333').grid(row=1, column=0, pady=5)
        
        ttk.Button(info_frame, text="🔄 다시 확인", 
                  command=self.check_dependencies).grid(row=2, column=0, pady=10)
        
        info_frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
    
    def setup_controls(self):
        """컨트롤 영역 설정"""
        control_frame = ttk.Frame(self.frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 데이터 소스 선택
        ttk.Label(control_frame, text="데이터 소스:").grid(row=0, column=0, padx=(0, 5))
        
        self.data_source_var = tk.StringVar()
        self.data_source_combo = ttk.Combobox(control_frame, textvariable=self.data_source_var,
                                             state="readonly", width=30)
        self.data_source_combo.grid(row=0, column=1, padx=(0, 10))
        self.data_source_combo.bind("<<ComboboxSelected>>", self.on_data_source_change)
        
        # 그래프 유형 선택
        ttk.Label(control_frame, text="그래프 유형:").grid(row=0, column=2, padx=(10, 5))
        
        self.plot_type_var = tk.StringVar(value="voltage_curves")
        plot_types = [
            ("전압 곡선", "voltage_curves"),
            ("용량 페이드", "capacity_fade"), 
            ("에너지 분석", "energy_analysis"),
            ("사이클 통계", "cycle_stats"),
            ("온도 분석", "temperature"),
            ("두께 변화", "thickness")
        ]
        
        self.plot_type_combo = ttk.Combobox(control_frame, textvariable=self.plot_type_var,
                                          values=[desc for desc, _ in plot_types],
                                          state="readonly", width=15)
        self.plot_type_combo.grid(row=0, column=3, padx=(0, 10))
        self.plot_type_combo.bind("<<ComboboxSelected>>", self.on_plot_type_change)
        
        # 컨트롤 버튼들
        ttk.Button(control_frame, text="📂 데이터 로드", 
                  command=self.load_data).grid(row=0, column=4, padx=5)
        
        ttk.Button(control_frame, text="📊 그래프 생성", 
                  command=self.generate_plot).grid(row=0, column=5, padx=5)
        
        ttk.Button(control_frame, text="💾 저장", 
                  command=self.save_plot).grid(row=0, column=6, padx=5)
        
        ttk.Button(control_frame, text="🖨️ 인쇄", 
                  command=self.print_plot).grid(row=0, column=7, padx=5)
        
        # 구분선
        ttk.Separator(self.frame, orient="horizontal").grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
    
    def setup_plot_area(self):
        """그래프 영역 설정"""
        # 노트북으로 여러 그래프 탭 관리
        self.plot_notebook = ttk.Notebook(self.frame)
        self.plot_notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 10))
        
        # 기본 그래프 탭 생성
        self.create_default_plot_tab()
    
    def create_default_plot_tab(self):
        """기본 그래프 탭 생성"""
        tab_frame = ttk.Frame(self.plot_notebook)
        self.plot_notebook.add(tab_frame, text="그래프 1")
        
        # matplotlib Figure 생성
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, tab_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 네비게이션 툴바 (확대/축소 등)
        toolbar = NavigationToolbar2Tk(self.canvas, tab_frame)
        toolbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        toolbar.update()
        
        # 초기 빈 그래프
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, '그래프 데이터를 로드하고\n"그래프 생성" 버튼을 클릭하세요',
               ha='center', va='center', transform=ax.transAxes,
               fontsize=14, color='gray')
        ax.set_xticks([])
        ax.set_yticks([])
        
        self.canvas.draw()
        
        # 그리드 설정
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)
    
    def setup_info_area(self):
        """정보 영역 설정"""
        info_frame = ttk.LabelFrame(self.frame, text="그래프 정보", padding="5")
        info_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        self.info_text = tk.Text(info_frame, height=3, wrap=tk.WORD, 
                                font=('Segoe UI', 9), state='disabled')
        info_scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
        
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        info_frame.columnconfigure(0, weight=1)
    
    def get_frame(self) -> ttk.Frame:
        """컴포넌트 프레임 반환"""
        return self.frame
    
    def check_dependencies(self):
        """의존성 재확인"""
        global MATPLOTLIB_AVAILABLE, PANDAS_AVAILABLE
        
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import pandas as pd
            
            MATPLOTLIB_AVAILABLE = True
            PANDAS_AVAILABLE = True
            
            # UI 다시 구성
            for widget in self.frame.winfo_children():
                widget.destroy()
            
            self.setup_controls()
            self.setup_plot_area()
            self.setup_info_area()
            
            messagebox.showinfo("완료", "시각화 라이브러리가 성공적으로 로드되었습니다!")
            
        except ImportError as e:
            messagebox.showerror("오류", f"라이브러리 로드 실패: {str(e)}")
    
    def load_data(self):
        """데이터 로드"""
        if not PANDAS_AVAILABLE:
            messagebox.showerror("오류", "pandas 라이브러리가 필요합니다.")
            return
        
        file_types = [
            ("JSON 파일", "*.json"),
            ("CSV 파일", "*.csv"),
            ("엑셀 파일", "*.xlsx"),
            ("모든 파일", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="시각화할 데이터 파일 선택",
            filetypes=file_types
        )
        
        if file_path:
            try:
                self.update_info("데이터 로딩 중...")
                
                # 백그라운드에서 데이터 로드
                thread = threading.Thread(target=self._load_data_async, 
                                         args=(file_path,), daemon=True)
                thread.start()
                
            except Exception as e:
                messagebox.showerror("오류", f"데이터 로드 실패: {str(e)}")
    
    def _load_data_async(self, file_path: str):
        """비동기 데이터 로드"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.current_data = data
                
            elif file_ext == '.csv':
                data = pd.read_csv(file_path)
                self.current_data = data
                
            elif file_ext in ['.xlsx', '.xls']:
                data = pd.read_excel(file_path)
                self.current_data = data
                
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {file_ext}")
            
            # UI 업데이트
            self.frame.after(0, lambda: self._on_data_loaded(file_path))
            
        except Exception as e:
            self.frame.after(0, lambda: self.update_info(f"데이터 로드 오류: {str(e)}"))
    
    def _on_data_loaded(self, file_path: str):
        """데이터 로드 완료"""
        self.update_info(f"데이터 로드 완료: {Path(file_path).name}")
        
        # 데이터 소스 콤보박스 업데이트
        if isinstance(self.current_data, dict):
            sources = list(self.current_data.keys())
            self.data_source_combo['values'] = sources
            if sources:
                self.data_source_combo.set(sources[0])
        elif isinstance(self.current_data, pd.DataFrame):
            self.data_source_combo['values'] = ["데이터프레임"]
            self.data_source_combo.set("데이터프레임")
    
    def on_data_source_change(self, event=None):
        """데이터 소스 변경"""
        source = self.data_source_var.get()
        self.update_info(f"선택된 데이터 소스: {source}")
    
    def on_plot_type_change(self, event=None):
        """그래프 유형 변경"""
        plot_type = self.plot_type_var.get()
        self.update_info(f"선택된 그래프 유형: {plot_type}")
    
    def generate_plot(self):
        """그래프 생성"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("오류", "matplotlib 라이브러리가 필요합니다.")
            return
        
        if self.current_data is None:
            messagebox.showwarning("경고", "먼저 데이터를 로드해주세요.")
            return
        
        plot_type = self.plot_type_var.get()
        data_source = self.data_source_var.get()
        
        try:
            self.update_info("그래프 생성 중...")
            
            # 기존 그래프 지우기
            self.figure.clear()
            
            # 선택된 그래프 유형에 따라 그래프 생성
            if plot_type == "전압 곡선":
                self._create_voltage_curves_plot(data_source)
            elif plot_type == "용량 페이드":
                self._create_capacity_fade_plot(data_source)
            elif plot_type == "에너지 분석":
                self._create_energy_analysis_plot(data_source)
            elif plot_type == "사이클 통계":
                self._create_cycle_stats_plot(data_source)
            elif plot_type == "온도 분석":
                self._create_temperature_plot(data_source)
            elif plot_type == "두께 변화":
                self._create_thickness_plot(data_source)
            else:
                self._create_sample_plot()
            
            self.canvas.draw()
            self.update_info(f"{plot_type} 그래프 생성 완료")
            
        except Exception as e:
            messagebox.showerror("오류", f"그래프 생성 실패: {str(e)}")
            self.update_info(f"그래프 생성 실패: {str(e)}")
    
    def _create_voltage_curves_plot(self, data_source: str):
        """전압 곡선 그래프 생성"""
        ax = self.figure.add_subplot(111)
        
        # 샘플 데이터로 전압 곡선 생성
        cycles = [1, 10, 50, 100, 200]
        capacities = np.linspace(0, 3.0, 100)
        
        for cycle in cycles:
            # 실제로는 데이터에서 가져와야 함
            voltage = 3.0 + 1.2 * np.exp(-capacities/2.5) + np.random.normal(0, 0.02, len(capacities))
            ax.plot(capacities, voltage, label=f'Cycle {cycle}', linewidth=2)
        
        ax.set_xlabel('Capacity (Ah)')
        ax.set_ylabel('Voltage (V)')
        ax.set_title('Battery Voltage Curves by Cycle')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def _create_capacity_fade_plot(self, data_source: str):
        """용량 페이드 그래프 생성"""
        ax = self.figure.add_subplot(111)
        
        # 샘플 데이터로 용량 감소 곡선 생성
        cycles = np.arange(1, 501)
        capacity = 3.0 * np.exp(-cycles/1000) + 2.5 + np.random.normal(0, 0.05, len(cycles))
        capacity = np.maximum(capacity, 2.0)  # 최소 용량 제한
        
        ax.plot(cycles, capacity, 'b-', linewidth=2, label='Capacity')
        ax.axhline(y=2.4, color='r', linestyle='--', alpha=0.7, label='EOL (80% of initial)')
        
        ax.set_xlabel('Cycle Number')
        ax.set_ylabel('Capacity (Ah)')
        ax.set_title('Battery Capacity Fade Over Cycles')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def _create_energy_analysis_plot(self, data_source: str):
        """에너지 분석 그래프 생성"""
        # 서브플롯 2개 생성
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212)
        
        cycles = np.arange(1, 201)
        
        # 충전/방전 에너지
        charge_energy = 9.5 + np.random.normal(0, 0.2, len(cycles)) - cycles * 0.01
        discharge_energy = 8.8 + np.random.normal(0, 0.2, len(cycles)) - cycles * 0.012
        
        ax1.plot(cycles, charge_energy, 'g-', label='Charge Energy', linewidth=2)
        ax1.plot(cycles, discharge_energy, 'r-', label='Discharge Energy', linewidth=2)
        ax1.set_ylabel('Energy (Wh)')
        ax1.set_title('Charge/Discharge Energy')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 에너지 효율
        efficiency = (discharge_energy / charge_energy) * 100
        ax2.plot(cycles, efficiency, 'b-', linewidth=2)
        ax2.set_xlabel('Cycle Number')
        ax2.set_ylabel('Efficiency (%)')
        ax2.set_title('Energy Efficiency')
        ax2.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def _create_cycle_stats_plot(self, data_source: str):
        """사이클 통계 그래프 생성"""
        # 2x2 서브플롯
        axes = self.figure.subplots(2, 2, figsize=(10, 8))
        
        cycles = np.arange(1, 101)
        
        # 충전 시간
        charge_time = 2.0 + np.random.exponential(0.5, len(cycles))
        axes[0, 0].plot(cycles, charge_time, 'g-', linewidth=2)
        axes[0, 0].set_title('Charge Time')
        axes[0, 0].set_ylabel('Time (hours)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 방전 시간
        discharge_time = 1.8 + np.random.exponential(0.3, len(cycles))
        axes[0, 1].plot(cycles, discharge_time, 'r-', linewidth=2)
        axes[0, 1].set_title('Discharge Time')
        axes[0, 1].set_ylabel('Time (hours)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 최대 전압
        max_voltage = 4.2 - cycles * 0.001 + np.random.normal(0, 0.01, len(cycles))
        axes[1, 0].plot(cycles, max_voltage, 'b-', linewidth=2)
        axes[1, 0].set_title('Maximum Voltage')
        axes[1, 0].set_xlabel('Cycle Number')
        axes[1, 0].set_ylabel('Voltage (V)')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 최소 전압
        min_voltage = 3.0 + cycles * 0.0005 + np.random.normal(0, 0.01, len(cycles))
        axes[1, 1].plot(cycles, min_voltage, 'orange', linewidth=2)
        axes[1, 1].set_title('Minimum Voltage')
        axes[1, 1].set_xlabel('Cycle Number')
        axes[1, 1].set_ylabel('Voltage (V)')
        axes[1, 1].grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def _create_temperature_plot(self, data_source: str):
        """온도 분석 그래프 생성"""
        ax = self.figure.add_subplot(111)
        
        # 시간에 따른 온도 변화 (샘플 데이터)
        time_hours = np.linspace(0, 4, 240)  # 4시간, 1분 간격
        
        # 주기적 온도 변화 (충전/방전에 따른)
        base_temp = 25.0
        temp_variation = 10.0 * np.sin(2 * np.pi * time_hours / 2) + 5.0 * np.sin(4 * np.pi * time_hours / 2)
        temperature = base_temp + temp_variation + np.random.normal(0, 1, len(time_hours))
        
        ax.plot(time_hours, temperature, 'r-', linewidth=1.5, alpha=0.8)
        ax.fill_between(time_hours, temperature, alpha=0.3, color='red')
        
        # 안전 온도 범위 표시
        ax.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='Warning (60°C)')
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.7, label='Critical (80°C)')
        
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Temperature (°C)')
        ax.set_title('Battery Temperature During Cycling')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def _create_thickness_plot(self, data_source: str):
        """두께 변화 그래프 생성"""
        ax = self.figure.add_subplot(111)
        
        cycles = np.arange(1, 301)
        
        # 기본 두께와 점진적 증가
        initial_thickness = 5.0  # mm
        thickness = initial_thickness + cycles * 0.001 + np.random.normal(0, 0.01, len(cycles))
        
        ax.plot(cycles, thickness, 'purple', linewidth=2, label='Cell Thickness')
        ax.axhline(y=initial_thickness, color='gray', linestyle='--', alpha=0.5, label='Initial Thickness')
        
        # 두께 증가율 계산
        thickness_increase = ((thickness - initial_thickness) / initial_thickness) * 100
        
        # 두 번째 y축으로 증가율 표시
        ax2 = ax.twinx()
        ax2.plot(cycles, thickness_increase, 'orange', linewidth=1, alpha=0.7, linestyle=':')
        ax2.set_ylabel('Thickness Increase (%)', color='orange')
        
        ax.set_xlabel('Cycle Number')
        ax.set_ylabel('Thickness (mm)')
        ax.set_title('Battery Cell Thickness Change')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def _create_sample_plot(self):
        """샘플 그래프 생성"""
        ax = self.figure.add_subplot(111)
        
        x = np.linspace(0, 10, 100)
        y = np.sin(x) * np.exp(-x/5)
        
        ax.plot(x, y, 'b-', linewidth=2)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title('Sample Plot')
        ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    def save_plot(self):
        """그래프 저장"""
        if self.current_data is None:
            messagebox.showwarning("경고", "저장할 그래프가 없습니다.")
            return
        
        file_types = [
            ("PNG 이미지", "*.png"),
            ("PDF 문서", "*.pdf"),
            ("SVG 벡터", "*.svg"),
            ("JPEG 이미지", "*.jpg")
        ]
        
        file_path = filedialog.asksaveasfilename(
            title="그래프 저장",
            defaultextension=".png",
            filetypes=file_types
        )
        
        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("완료", f"그래프가 저장되었습니다:\n{file_path}")
                self.update_info(f"그래프 저장 완료: {Path(file_path).name}")
                
            except Exception as e:
                messagebox.showerror("오류", f"그래프 저장 실패: {str(e)}")
    
    def print_plot(self):
        """그래프 인쇄"""
        if self.current_data is None:
            messagebox.showwarning("경고", "인쇄할 그래프가 없습니다.")
            return
        
        try:
            # 임시 파일로 저장 후 시스템 인쇄 대화상자 호출
            temp_path = Path.home() / "temp_plot.png"
            self.figure.savefig(temp_path, dpi=300, bbox_inches='tight')
            
            # 시스템 기본 이미지 뷰어로 열기 (인쇄 가능)
            import os
            os.startfile(str(temp_path))
            
            self.update_info("그래프를 기본 이미지 뷰어로 열었습니다. 인쇄하려면 Ctrl+P를 누르세요.")
            
        except Exception as e:
            messagebox.showerror("오류", f"그래프 인쇄 실패: {str(e)}")
    
    def update_info(self, message: str):
        """정보 영역 업데이트"""
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, message)
        self.info_text.config(state='disabled')
    
    def load_processing_results(self, results: Dict[str, Any]):
        """처리 결과 로드"""
        self.current_data = results
        self.update_info("처리 결과 데이터가 로드되었습니다.")
        
        # 데이터 소스 콤보박스 업데이트
        if isinstance(results, dict):
            sources = list(results.keys())
            self.data_source_combo['values'] = sources
            if sources:
                self.data_source_combo.set(sources[0])