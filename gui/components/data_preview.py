"""
Data Preview Component

데이터 미리보기 및 요약 정보 표시 컴포넌트
"""

import tkinter as tk
from tkinter import ttk
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import sys
import threading

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gui.base_gui import BaseGUIComponent
from preprocess import ToyoDataLoader


class DataPreviewComponent(BaseGUIComponent):
    """데이터 미리보기 컴포넌트"""
    
    def setup_component(self):
        """컴포넌트 설정"""
        self.data_loader = None
        self.current_data_summary = {}
        self.preview_data = {}
        
        self.frame = ttk.LabelFrame(self.parent, text="📊 데이터 미리보기", padding="10")
        
        # 상단 컨트롤 영역
        control_frame = ttk.Frame(self.frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(control_frame, text="데이터 경로:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(control_frame, textvariable=self.path_var, width=50, state='readonly')
        self.path_entry.grid(row=0, column=1, padx=(0, 5))
        
        self.refresh_btn = ttk.Button(control_frame, text="🔄 새로고침", 
                                     command=self.refresh_preview)
        self.refresh_btn.grid(row=0, column=2, padx=5)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="자동 새로고침", 
                       variable=self.auto_refresh_var).grid(row=0, column=3, padx=5)
        
        # 노트북 위젯으로 탭 구성
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # 요약 정보 탭
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="📋 요약 정보")
        self.setup_summary_tab()
        
        # 채널 상세 탭
        self.channels_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.channels_frame, text="📁 채널 정보")
        self.setup_channels_tab()
        
        # 데이터 샘플 탭
        self.sample_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sample_frame, text="📄 데이터 샘플")
        self.setup_sample_tab()
        
        # 상태 표시 영역
        self.status_var = tk.StringVar(value="경로를 선택하면 미리보기가 표시됩니다.")
        status_label = ttk.Label(self.frame, textvariable=self.status_var, 
                                font=('Segoe UI', 9), foreground='#666666')
        status_label.grid(row=2, column=0, pady=(10, 0))
        
        # 그리드 가중치 설정
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        control_frame.columnconfigure(1, weight=1)
    
    def setup_summary_tab(self):
        """요약 정보 탭 설정"""
        # 스크롤 가능한 프레임
        canvas = tk.Canvas(self.summary_frame, height=200)
        scrollbar = ttk.Scrollbar(self.summary_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 요약 정보 레이블들
        self.summary_labels = {}
        summary_items = [
            ("총 채널 수", "total_channels"),
            ("총 파일 수", "total_files"),
            ("데이터 크기", "total_size"),
            ("날짜 범위", "date_range"),
            ("처리 상태", "processing_status")
        ]
        
        for i, (label, key) in enumerate(summary_items):
            ttk.Label(scrollable_frame, text=f"{label}:", 
                     font=('Segoe UI', 9, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=2, padx=(10, 5))
            
            value_label = ttk.Label(scrollable_frame, text="--", font=('Segoe UI', 9))
            value_label.grid(row=i, column=1, sticky=tk.W, pady=2, padx=(5, 10))
            self.summary_labels[key] = value_label
        
        # 그리드 설정
        self.summary_frame.columnconfigure(0, weight=1)
        self.summary_frame.rowconfigure(0, weight=1)
    
    def setup_channels_tab(self):
        """채널 정보 탭 설정"""
        # 트리뷰로 채널 목록 표시
        columns = ("채널", "파일수", "용량로그", "크기", "상태")
        self.channels_tree = ttk.Treeview(self.channels_frame, columns=columns, show="tree headings", height=8)
        
        # 헤더 설정
        self.channels_tree.heading("#0", text="", anchor=tk.W)
        self.channels_tree.column("#0", width=0, stretch=False)
        
        for col in columns:
            self.channels_tree.heading(col, text=col, anchor=tk.W)
            self.channels_tree.column(col, width=100, anchor=tk.W)
        
        # 스크롤바
        channels_scrollbar = ttk.Scrollbar(self.channels_frame, orient="vertical", 
                                          command=self.channels_tree.yview)
        self.channels_tree.configure(yscrollcommand=channels_scrollbar.set)
        
        # 배치
        self.channels_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        channels_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 채널 선택 이벤트
        self.channels_tree.bind("<<TreeviewSelect>>", self.on_channel_select)
        
        # 그리드 설정
        self.channels_frame.columnconfigure(0, weight=1)
        self.channels_frame.rowconfigure(0, weight=1)
    
    def setup_sample_tab(self):
        """데이터 샘플 탭 설정"""
        # 채널 선택 드롭다운
        control_frame = ttk.Frame(self.sample_frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(control_frame, text="채널 선택:").grid(row=0, column=0, padx=(0, 5))
        
        self.sample_channel_var = tk.StringVar()
        self.sample_channel_combo = ttk.Combobox(control_frame, textvariable=self.sample_channel_var,
                                                state="readonly", width=15)
        self.sample_channel_combo.grid(row=0, column=1, padx=(0, 10))
        self.sample_channel_combo.bind("<<ComboboxSelected>>", self.on_sample_channel_change)
        
        ttk.Label(control_frame, text="샘플 크기:").grid(row=0, column=2, padx=(10, 5))
        
        self.sample_size_var = tk.StringVar(value="100")
        sample_size_combo = ttk.Combobox(control_frame, textvariable=self.sample_size_var,
                                        values=["50", "100", "500", "1000"], width=10)
        sample_size_combo.grid(row=0, column=3, padx=(0, 10))
        sample_size_combo.bind("<<ComboboxSelected>>", self.on_sample_size_change)
        
        # 데이터 테이블 (트리뷰 사용)
        self.sample_tree = ttk.Treeview(self.sample_frame, show="tree headings", height=12)
        
        # 스크롤바
        sample_v_scrollbar = ttk.Scrollbar(self.sample_frame, orient="vertical", 
                                         command=self.sample_tree.yview)
        sample_h_scrollbar = ttk.Scrollbar(self.sample_frame, orient="horizontal", 
                                         command=self.sample_tree.xview)
        
        self.sample_tree.configure(yscrollcommand=sample_v_scrollbar.set,
                                 xscrollcommand=sample_h_scrollbar.set)
        
        # 배치
        self.sample_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        sample_v_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        sample_h_scrollbar.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # 그리드 설정
        self.sample_frame.columnconfigure(0, weight=1)
        self.sample_frame.rowconfigure(1, weight=1)
    
    def get_frame(self) -> ttk.Frame:
        """컴포넌트 프레임 반환"""
        return self.frame
    
    def set_data_path(self, path: str):
        """데이터 경로 설정"""
        self.path_var.set(path)
        if self.auto_refresh_var.get():
            self.refresh_preview()
    
    def refresh_preview(self):
        """미리보기 새로고침"""
        path = self.path_var.get()
        if not path:
            self.status_var.set("경로가 설정되지 않았습니다.")
            return
        
        if not Path(path).exists():
            self.status_var.set("경로가 존재하지 않습니다.")
            return
        
        self.status_var.set("데이터 로딩 중...")
        
        # 백그라운드에서 데이터 로드
        thread = threading.Thread(target=self._load_data_async, args=(path,), daemon=True)
        thread.start()
    
    def _load_data_async(self, path: str):
        """비동기 데이터 로드"""
        try:
            # 데이터 로더 생성
            self.data_loader = ToyoDataLoader(path)
            
            # 데이터 요약 정보 가져오기
            summary = self.data_loader.get_data_summary()
            
            # UI 업데이트는 메인 스레드에서
            self.frame.after(0, lambda: self._update_preview_ui(summary))
            
        except Exception as e:
            self.frame.after(0, lambda: self.status_var.set(f"데이터 로드 오류: {str(e)}"))
    
    def _update_preview_ui(self, summary: Dict[str, Any]):
        """미리보기 UI 업데이트"""
        try:
            self.current_data_summary = summary
            
            # 요약 정보 업데이트
            self._update_summary_info(summary)
            
            # 채널 정보 업데이트
            self._update_channels_info(summary)
            
            # 샘플 채널 콤보박스 업데이트
            channels = list(summary.keys())
            self.sample_channel_combo['values'] = channels
            if channels:
                self.sample_channel_combo.set(channels[0])
                self._load_sample_data(channels[0])
            
            self.status_var.set(f"미리보기 완료 - {len(summary)}개 채널")
            
        except Exception as e:
            self.status_var.set(f"UI 업데이트 오류: {str(e)}")
    
    def _update_summary_info(self, summary: Dict[str, Any]):
        """요약 정보 업데이트"""
        total_files = sum(info.get('data_files', 0) for info in summary.values())
        total_size = "계산 중..."  # 실제로는 파일 크기 계산 필요
        
        # 날짜 범위 (첫 번째 채널의 데이터에서 추출)
        date_range = "확인 중..."
        
        self.summary_labels['total_channels'].config(text=str(len(summary)))
        self.summary_labels['total_files'].config(text=str(total_files))
        self.summary_labels['total_size'].config(text=total_size)
        self.summary_labels['date_range'].config(text=date_range)
        self.summary_labels['processing_status'].config(text="준비됨")
    
    def _update_channels_info(self, summary: Dict[str, Any]):
        """채널 정보 업데이트"""
        # 기존 항목 제거
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        # 새 항목 추가
        for channel, info in summary.items():
            values = (
                channel,
                info.get('data_files', 0),
                "예" if info.get('capacity_log') else "아니오",
                "계산 중...",  # 파일 크기
                "준비됨"
            )
            self.channels_tree.insert("", "end", values=values)
    
    def on_channel_select(self, event):
        """채널 선택 이벤트"""
        selection = self.channels_tree.selection()
        if selection:
            item = self.channels_tree.item(selection[0])
            channel = item['values'][0]
            # 선택된 채널 정보를 사용해서 추가 작업 가능
    
    def on_sample_channel_change(self, event=None):
        """샘플 채널 변경 이벤트"""
        channel = self.sample_channel_var.get()
        if channel:
            self._load_sample_data(channel)
    
    def on_sample_size_change(self, event=None):
        """샘플 크기 변경 이벤트"""
        channel = self.sample_channel_var.get()
        if channel:
            self._load_sample_data(channel)
    
    def _load_sample_data(self, channel: str):
        """샘플 데이터 로드"""
        if not self.data_loader:
            return
        
        try:
            sample_size = int(self.sample_size_var.get())
            
            # 백그라운드에서 샘플 데이터 로드
            thread = threading.Thread(target=self._load_sample_async, 
                                     args=(channel, sample_size), daemon=True)
            thread.start()
            
        except Exception as e:
            self.status_var.set(f"샘플 데이터 로드 오류: {str(e)}")
    
    def _load_sample_async(self, channel: str, sample_size: int):
        """비동기 샘플 데이터 로드"""
        try:
            # 채널 데이터 로드
            data = self.data_loader.load_channel_data(channel)
            
            if not data.empty:
                # 샘플 추출
                sample_data = data.head(sample_size)
                self.frame.after(0, lambda: self._update_sample_tree(sample_data))
            else:
                self.frame.after(0, lambda: self.status_var.set("샘플 데이터가 없습니다."))
                
        except Exception as e:
            self.frame.after(0, lambda: self.status_var.set(f"샘플 로드 오류: {str(e)}"))
    
    def _update_sample_tree(self, data: pd.DataFrame):
        """샘플 데이터 트리 업데이트"""
        # 기존 컬럼과 데이터 제거
        self.sample_tree["columns"] = ()
        for item in self.sample_tree.get_children():
            self.sample_tree.delete(item)
        
        if data.empty:
            return
        
        # 컬럼 설정
        columns = list(data.columns)
        self.sample_tree["columns"] = columns
        self.sample_tree["show"] = "headings"
        
        # 헤더 설정
        for col in columns:
            self.sample_tree.heading(col, text=col, anchor=tk.W)
            self.sample_tree.column(col, width=100, anchor=tk.W)
        
        # 데이터 추가
        for _, row in data.iterrows():
            values = [str(value) for value in row.values]
            self.sample_tree.insert("", "end", values=values)