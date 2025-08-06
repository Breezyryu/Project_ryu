"""
Enhanced Toyo Battery Data Preprocessing GUI Application

확장된 배터리 데이터 전처리 GUI 애플리케이션
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import sys
import os
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import base GUI components
from gui.base_gui import (
    ConfigManager, TaskQueue, ProcessingThread, 
    StyleManager, LogManager, ValidationMixin,
    EventManager, ProgressTracker
)

# Import specialized components
from gui.components.data_preview import DataPreviewComponent
from gui.components.batch_processor import BatchProcessorComponent
from gui.components.visualization import VisualizationComponent

from preprocess import run_toyo_preprocessing, ToyoPreprocessingPipeline


class EnhancedToyoGUI(ValidationMixin):
    """향상된 Toyo 배터리 데이터 전처리 GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Toyo 배터리 데이터 전처리 시스템 v2.0")
        
        # 매니저들 초기화
        self.config_manager = ConfigManager()
        self.style_manager = StyleManager()
        self.task_queue = TaskQueue()
        self.event_manager = EventManager()
        self.progress_tracker = ProgressTracker()
        
        # 상태 변수들
        self.processing_thread: Optional[ProcessingThread] = None
        self.current_data_path = ""
        self.current_results = None
        
        # 창 설정
        self.setup_window()
        
        # UI 컴포넌트 생성
        self.create_main_interface()
        
        # 이벤트 설정
        self.setup_events()
        
        # 설정 로드
        self.load_initial_config()
        
        # 큐 모니터링 시작
        self.monitor_task_queue()
    
    def setup_window(self):
        """메인 창 설정"""
        # 창 크기와 위치
        config = self.config_manager.current_config
        geometry = config.get('window_geometry', '1200x800')
        self.root.geometry(geometry)
        
        # 최소 크기 설정
        self.root.minsize(1000, 700)
        
        # 창 닫기 이벤트
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 아이콘 설정 (있다면)
        try:
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass  # 아이콘이 없어도 계속 진행
    
    def create_main_interface(self):
        """메인 인터페이스 생성"""
        # 메인 컨테이너
        main_container = ttk.Frame(self.root, padding="5")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 상단 툴바
        self.create_toolbar(main_container)
        
        # 메인 콘텐츠 영역 (노트북 위젯)
        self.create_main_notebook(main_container)
        
        # 하단 상태바
        self.create_statusbar(main_container)
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
    
    def create_toolbar(self, parent):
        """상단 툴바 생성"""
        toolbar_frame = ttk.Frame(parent, style='Card.TFrame')
        toolbar_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 타이틀
        title_label = ttk.Label(toolbar_frame, 
                               text="🔋 Toyo 배터리 데이터 전처리 시스템 v2.0",
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, padx=10, pady=5)
        
        # 오른쪽 정렬 컨트롤들
        controls_frame = ttk.Frame(toolbar_frame)
        controls_frame.grid(row=0, column=1, sticky=tk.E, padx=10, pady=5)
        
        # 프로파일 선택
        ttk.Label(controls_frame, text="프로파일:").grid(row=0, column=0, padx=(0, 5))
        
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(controls_frame, textvariable=self.profile_var,
                                         width=15, state="readonly")
        self.profile_combo.grid(row=0, column=1, padx=(0, 10))
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)
        
        # 프로파일 관리 버튼
        ttk.Button(controls_frame, text="📝 프로파일 관리", 
                  command=self.open_profile_manager).grid(row=0, column=2, padx=5)
        
        # 설정 버튼
        ttk.Button(controls_frame, text="⚙️ 설정", 
                  command=self.open_settings).grid(row=0, column=3, padx=5)
        
        # 도움말 버튼
        ttk.Button(controls_frame, text="❓ 도움말", 
                  command=self.show_help).grid(row=0, column=4, padx=5)
        
        toolbar_frame.columnconfigure(1, weight=1)
    
    def create_main_notebook(self, parent):
        """메인 노트북 위젯 생성"""
        self.main_notebook = ttk.Notebook(parent)
        self.main_notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        
        # 기본 처리 탭
        self.create_basic_tab()
        
        # 데이터 미리보기 탭
        self.create_preview_tab()
        
        # 배치 처리 탭
        self.create_batch_tab()
        
        # 시각화 탭
        self.create_visualization_tab()
        
        # 히스토리 탭
        self.create_history_tab()
        
        # 탭 변경 이벤트
        self.main_notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
    
    def create_basic_tab(self):
        """기본 처리 탭 생성"""
        basic_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(basic_frame, text="🏠 기본 처리")
        
        # 스크롤 가능한 프레임
        canvas = tk.Canvas(basic_frame)
        scrollbar = ttk.Scrollbar(basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 경로 설정 섹션
        self.create_path_section(scrollable_frame)
        
        # 처리 옵션 섹션
        self.create_options_section(scrollable_frame)
        
        # 처리 모드 섹션
        self.create_mode_section(scrollable_frame)
        
        # 실행 버튼 섹션
        self.create_execution_section(scrollable_frame)
        
        # 진행 상태 섹션
        self.create_progress_section(scrollable_frame)
        
        # 로그 섹션
        self.create_log_section(scrollable_frame)
        
        # 배치
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 그리드 설정
        basic_frame.columnconfigure(0, weight=1)
        basic_frame.rowconfigure(0, weight=1)
    
    def create_path_section(self, parent):
        """경로 설정 섹션"""
        path_frame = ttk.LabelFrame(parent, text="📁 경로 설정", padding="10")
        path_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 입력 경로
        ttk.Label(path_frame, text="입력 경로:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_path_var = tk.StringVar()
        self.input_entry = ttk.Entry(path_frame, textvariable=self.input_path_var, width=60)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(path_frame, text="찾아보기...", 
                  command=self.browse_input_path).grid(row=0, column=2, padx=5, pady=5)
        
        # 출력 경로
        ttk.Label(path_frame, text="출력 경로:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        self.output_entry = ttk.Entry(path_frame, textvariable=self.output_path_var, width=60)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(path_frame, text="찾아보기...", 
                  command=self.browse_output_path).grid(row=1, column=2, padx=5, pady=5)
        
        # 자동 출력 경로 옵션
        self.auto_output_var = tk.BooleanVar(value=True)
        self.auto_output_check = ttk.Checkbutton(
            path_frame, 
            text="자동 출력 경로 생성 (../../preprocess/입력폴더명)",
            variable=self.auto_output_var,
            command=self.toggle_auto_output
        )
        self.auto_output_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        path_frame.columnconfigure(1, weight=1)
        
        # 경로 변경 이벤트 바인딩
        self.input_path_var.trace('w', self.on_input_path_change)
    
    def create_options_section(self, parent):
        """처리 옵션 섹션"""
        options_frame = ttk.LabelFrame(parent, text="⚙️ 처리 옵션", padding="10")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 옵션 체크박스들을 2열로 배치
        self.force_reprocess_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="강제 재처리",
                       variable=self.force_reprocess_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.create_viz_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="시각화 생성",
                       variable=self.create_viz_var).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(50, 0))
        
        self.save_intermediate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="중간 결과 저장",
                       variable=self.save_intermediate_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.save_processed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="처리된 데이터 저장",
                       variable=self.save_processed_var).grid(row=1, column=1, sticky=tk.W, pady=2, padx=(50, 0))
    
    def create_mode_section(self, parent):
        """처리 모드 섹션"""
        mode_frame = ttk.LabelFrame(parent, text="🎯 처리 모드", padding="10")
        mode_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.mode_var = tk.StringVar(value="basic")
        modes = [
            ("기본 처리", "basic"),
            ("고급 처리", "advanced"),
            ("데이터 탐색", "exploration"),
            ("개별 컴포넌트", "individual")
        ]
        
        for i, (text, value) in enumerate(modes):
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, 
                          value=value).grid(row=0, column=i, padx=10, pady=5)
    
    def create_execution_section(self, parent):
        """실행 버튼 섹션"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, pady=10)
        
        self.process_button = ttk.Button(button_frame, text="🚀 처리 시작", 
                                        style='Primary.TButton',
                                        command=self.start_processing)
        self.process_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹ 중지", 
                                      state='disabled',
                                      command=self.stop_processing)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="🗑️ 로그 지우기",
                  command=self.clear_log).grid(row=0, column=2, padx=5)
        
        ttk.Button(button_frame, text="📊 결과 보기",
                  command=self.view_results).grid(row=0, column=3, padx=5)
    
    def create_progress_section(self, parent):
        """진행 상태 섹션"""
        progress_frame = ttk.LabelFrame(parent, text="📊 진행 상태", padding="10")
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.StringVar(value="대기 중...")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=400)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        progress_frame.columnconfigure(0, weight=1)
    
    def create_log_section(self, parent):
        """로그 출력 섹션"""
        log_frame = ttk.LabelFrame(parent, text="📝 처리 로그", padding="10")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 로그 텍스트 위젯
        self.log_text = tk.Text(log_frame, height=10, width=100, wrap=tk.WORD, 
                               font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 로그 매니저 설정
        self.log_manager = LogManager(self.log_text)
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def create_preview_tab(self):
        """데이터 미리보기 탭"""
        self.preview_component = DataPreviewComponent(self.main_notebook)
        preview_frame = self.preview_component.get_frame()
        self.main_notebook.add(preview_frame, text="👀 미리보기")
        
        # 그리드 설정
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
    
    def create_batch_tab(self):
        """배치 처리 탭"""
        self.batch_component = BatchProcessorComponent(self.main_notebook)
        batch_frame = self.batch_component.get_frame()
        self.main_notebook.add(batch_frame, text="📦 배치 처리")
        
        # 그리드 설정
        batch_frame.columnconfigure(0, weight=1)
        batch_frame.rowconfigure(1, weight=1)
    
    def create_visualization_tab(self):
        """시각화 탭"""
        self.visualization_component = VisualizationComponent(self.main_notebook)
        viz_frame = self.visualization_component.get_frame()
        self.main_notebook.add(viz_frame, text="📊 시각화")
        
        # 그리드 설정
        viz_frame.columnconfigure(0, weight=1)
        viz_frame.rowconfigure(2, weight=1)
    
    def create_history_tab(self):
        """히스토리 탭"""
        history_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(history_frame, text="📋 히스토리")
        
        # TODO: 히스토리 컴포넌트 구현
        ttk.Label(history_frame, text="처리 히스토리 기능 구현 예정", 
                 font=('Segoe UI', 12), foreground='#666666').pack(expand=True)
    
    def create_statusbar(self, parent):
        """하단 상태바 생성"""
        statusbar_frame = ttk.Frame(parent)
        statusbar_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # 상태 메시지
        self.status_var = tk.StringVar(value="준비됨")
        ttk.Label(statusbar_frame, textvariable=self.status_var, 
                 style='Caption.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # 시간 표시
        self.time_var = tk.StringVar()
        ttk.Label(statusbar_frame, textvariable=self.time_var, 
                 style='Caption.TLabel').grid(row=0, column=1, sticky=tk.E, padx=5)
        
        # 시간 업데이트
        self.update_time()
        
        statusbar_frame.columnconfigure(1, weight=1)
    
    def setup_events(self):
        """이벤트 설정"""
        # 태스크 큐 콜백 설정
        self.task_queue.add_callback("LOG", self.on_log_message)
        self.task_queue.add_callback("PROGRESS", self.on_progress_update)
        self.task_queue.add_callback("STATUS", self.on_status_update)
        self.task_queue.add_callback("COMPLETE", self.on_processing_complete)
        self.task_queue.add_callback("ERROR", self.on_processing_error)
        self.task_queue.add_callback("DONE", self.on_processing_done)
        
        # 이벤트 매니저 구독
        self.event_manager.subscribe("path_changed", self.on_path_changed)
        self.event_manager.subscribe("processing_started", self.on_processing_started)
        self.event_manager.subscribe("processing_completed", self.on_processing_completed)
    
    def load_initial_config(self):
        """초기 설정 로드"""
        config = self.config_manager.current_config
        
        # UI 값들 설정
        self.input_path_var.set(config.get('input_path', ''))
        self.output_path_var.set(config.get('output_path', ''))
        self.auto_output_var.set(config.get('auto_output', True))
        self.force_reprocess_var.set(config.get('force_reprocess', False))
        self.create_viz_var.set(config.get('create_viz', True))
        self.save_intermediate_var.set(config.get('save_intermediate', True))
        self.save_processed_var.set(config.get('save_processed', True))
        self.mode_var.set(config.get('mode', 'basic'))
        
        # 프로파일 콤보박스 설정
        self.update_profile_combo()
        
        # 자동 출력 경로 토글
        self.toggle_auto_output()
        
        self.log_manager.log("설정을 불러왔습니다.", "INFO")
    
    def update_profile_combo(self):
        """프로파일 콤보박스 업데이트"""
        profiles = list(self.config_manager.profiles.keys())
        self.profile_combo['values'] = profiles
        if profiles:
            self.profile_combo.set(profiles[0])
    
    # =========================
    # 이벤트 핸들러들
    # =========================
    
    def browse_input_path(self):
        """입력 경로 선택"""
        path = filedialog.askdirectory(title="입력 데이터 폴더 선택")
        if path:
            self.input_path_var.set(path)
            self.event_manager.emit("path_changed", "input", path)
    
    def browse_output_path(self):
        """출력 경로 선택"""
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self.output_path_var.set(path)
            self.auto_output_var.set(False)
            self.event_manager.emit("path_changed", "output", path)
    
    def toggle_auto_output(self):
        """자동 출력 경로 토글"""
        if self.auto_output_var.get():
            self.output_entry.config(state='disabled')
            self.on_input_path_change()
        else:
            self.output_entry.config(state='normal')
    
    def on_input_path_change(self, *args):
        """입력 경로 변경 시"""
        if self.auto_output_var.get() and self.input_path_var.get():
            input_path = Path(self.input_path_var.get())
            output_path = Path("../../preprocess") / input_path.name
            self.output_path_var.set(str(output_path))
            
            # 미리보기 컴포넌트에 경로 전달
            if hasattr(self, 'preview_component'):
                self.preview_component.set_data_path(self.input_path_var.get())
    
    def on_profile_change(self, event=None):
        """프로파일 변경"""
        profile_name = self.profile_var.get()
        if profile_name:
            config = self.config_manager.load_profile(profile_name)
            self.apply_config(config)
            self.log_manager.log(f"프로파일 '{profile_name}' 을(를) 적용했습니다.", "INFO")
    
    def apply_config(self, config: Dict[str, Any]):
        """설정 적용"""
        self.input_path_var.set(config.get('input_path', ''))
        self.output_path_var.set(config.get('output_path', ''))
        self.auto_output_var.set(config.get('auto_output', True))
        self.force_reprocess_var.set(config.get('force_reprocess', False))
        self.create_viz_var.set(config.get('create_viz', True))
        self.save_intermediate_var.set(config.get('save_intermediate', True))
        self.save_processed_var.set(config.get('save_processed', True))
        self.mode_var.set(config.get('mode', 'basic'))
        
        self.toggle_auto_output()
    
    def on_tab_change(self, event):
        """탭 변경 시"""
        selected_tab = event.widget.tab('current')['text']
        self.status_var.set(f"현재 탭: {selected_tab}")
    
    def on_path_changed(self, path_type: str, path: str):
        """경로 변경 이벤트"""
        self.log_manager.log(f"{path_type} 경로 설정: {path}", "INFO")
    
    def on_processing_started(self):
        """처리 시작 이벤트"""
        self.process_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar.start(10)
        self.status_var.set("처리 중...")
    
    def on_processing_completed(self, results):
        """처리 완료 이벤트"""
        self.current_results = results
        # 시각화 컴포넌트에 결과 전달
        if hasattr(self, 'visualization_component'):
            self.visualization_component.load_processing_results(results)
    
    # =========================
    # 태스크 큐 콜백들
    # =========================
    
    def on_log_message(self, message: str, level: str, data: Any = None):
        """로그 메시지 콜백"""
        self.log_manager.log(message, level)
    
    def on_progress_update(self, message: str, level: str, data: Any = None):
        """진행 상태 콜백"""
        self.progress_var.set(message)
    
    def on_status_update(self, message: str, level: str, data: Any = None):
        """상태 업데이트 콜백"""
        self.status_var.set(message)
    
    def on_processing_complete(self, message: str, level: str, data: Any = None):
        """처리 완료 콜백"""
        self.log_manager.log(message, level)
        messagebox.showinfo("완료", message)
        self.event_manager.emit("processing_completed", data)
    
    def on_processing_error(self, message: str, level: str, data: Any = None):
        """처리 오류 콜백"""
        self.log_manager.log(message, level)
        messagebox.showerror("오류", message)
    
    def on_processing_done(self, message: str, level: str, data: Any = None):
        """처리 종료 콜백"""
        self.reset_ui_state()
    
    # =========================
    # 처리 관련 메서드들
    # =========================
    
    def start_processing(self):
        """처리 시작"""
        # 유효성 검사
        valid, error_msg = self.validate_inputs()
        if not valid:
            messagebox.showerror("입력 오류", error_msg)
            return
        
        # 설정 저장
        self.save_current_config()
        
        # 이벤트 발생
        self.event_manager.emit("processing_started")
        
        # UI 상태 변경
        self.on_processing_started()
        
        # 처리 스레드 시작
        self.processing_thread = ProcessingThread(
            self.task_queue,
            self._processing_worker
        )
        self.processing_thread.start()
    
    def validate_inputs(self) -> tuple[bool, str]:
        """입력 검증"""
        # 입력 경로 검증
        valid, msg = self.validate_path(self.input_path_var.get())
        if not valid:
            return False, f"입력 경로 오류: {msg}"
        
        # 출력 경로가 수동 설정된 경우 검증
        if not self.auto_output_var.get():
            output_path = self.output_path_var.get()
            if not output_path:
                return False, "출력 경로를 설정해주세요."
        
        return True, ""
    
    def _processing_worker(self, task_queue: TaskQueue, stop_event):
        """처리 워커"""
        try:
            input_path = self.input_path_var.get()
            output_path = self.output_path_var.get()
            mode = self.mode_var.get()
            
            task_queue.put("LOG", f"처리 시작: {mode} 모드", "INFO")
            task_queue.put("PROGRESS", "데이터 처리 중...", "INFO")
            
            # 자동 출력 경로 생성
            if self.auto_output_var.get():
                output_path = str(Path("../../preprocess") / Path(input_path).name)
                Path(output_path).mkdir(parents=True, exist_ok=True)
            
            if mode == "basic":
                results = run_toyo_preprocessing(
                    src_path=input_path,
                    dst_path=output_path,
                    force_reprocess=self.force_reprocess_var.get(),
                    create_visualizations=self.create_viz_var.get()
                )
            elif mode == "advanced":
                pipeline = ToyoPreprocessingPipeline(input_path, output_path)
                results = pipeline.run_complete_pipeline(
                    save_intermediate=self.save_intermediate_var.get(),
                    create_visualizations=self.create_viz_var.get(),
                    save_processed_data=self.save_processed_var.get()
                )
            else:
                # 기타 모드들 처리
                results = {"mode": mode, "message": f"{mode} 모드 처리 완료"}
            
            task_queue.put("COMPLETE", "처리가 성공적으로 완료되었습니다!", "SUCCESS", results)
            
        except Exception as e:
            task_queue.put("ERROR", f"처리 중 오류 발생: {str(e)}", "ERROR")
        finally:
            task_queue.put("DONE", "", "")
    
    def stop_processing(self):
        """처리 중지"""
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.stop()
            self.log_manager.log("사용자에 의해 처리가 중지되었습니다.", "WARNING")
    
    def reset_ui_state(self):
        """UI 상태 리셋"""
        self.process_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar.stop()
        self.progress_var.set("대기 중...")
        self.status_var.set("준비됨")
    
    # =========================
    # 유틸리티 메서드들
    # =========================
    
    def save_current_config(self):
        """현재 설정 저장"""
        config = {
            'input_path': self.input_path_var.get(),
            'output_path': self.output_path_var.get(),
            'auto_output': self.auto_output_var.get(),
            'force_reprocess': self.force_reprocess_var.get(),
            'create_viz': self.create_viz_var.get(),
            'save_intermediate': self.save_intermediate_var.get(),
            'save_processed': self.save_processed_var.get(),
            'mode': self.mode_var.get(),
            'window_geometry': self.root.geometry()
        }
        
        self.config_manager.current_config.update(config)
        self.config_manager.save_config()
    
    def clear_log(self):
        """로그 지우기"""
        self.log_manager.clear()
    
    def view_results(self):
        """결과 보기"""
        if self.current_results:
            # 시각화 탭으로 이동
            for i in range(self.main_notebook.index("end")):
                if "시각화" in self.main_notebook.tab(i, "text"):
                    self.main_notebook.select(i)
                    break
        else:
            messagebox.showinfo("알림", "표시할 결과가 없습니다. 먼저 데이터를 처리해주세요.")
    
    def open_profile_manager(self):
        """프로파일 관리자 열기"""
        # TODO: 프로파일 관리 다이얼로그 구현
        messagebox.showinfo("알림", "프로파일 관리 기능 구현 예정")
    
    def open_settings(self):
        """설정 창 열기"""
        # TODO: 설정 다이얼로그 구현
        messagebox.showinfo("알림", "설정 기능 구현 예정")
    
    def show_help(self):
        """도움말 표시"""
        help_text = """
🔋 Toyo 배터리 데이터 전처리 시스템 v2.0

주요 기능:
• 기본 처리: 단일 폴더 배터리 데이터 전처리
• 미리보기: 데이터 로드 전 요약 정보 확인
• 배치 처리: 여러 폴더 동시 처리
• 시각화: 처리 결과 그래프 생성
• 프로파일: 설정 저장 및 불러오기

사용법:
1. 입력 경로에 배터리 데이터 폴더 선택
2. 처리 옵션과 모드 설정
3. 처리 시작 버튼 클릭

문제 해결:
• 경로에 한글이나 특수문자가 있는지 확인
• 데이터 구조가 올바른지 확인
• 충분한 디스크 공간이 있는지 확인
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("도움말")
        help_window.geometry("500x400")
        help_window.transient(self.root)
        help_window.grab_set()
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=20, pady=20)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, help_text)
        text_widget.config(state='disabled')
    
    def update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_time)  # 1초마다 업데이트
    
    def monitor_task_queue(self):
        """태스크 큐 모니터링"""
        self.task_queue.process_messages()
        self.root.after(100, self.monitor_task_queue)  # 100ms마다 확인
    
    def on_closing(self):
        """창 닫기 시"""
        # 처리 중인 작업이 있으면 확인
        if self.processing_thread and self.processing_thread.is_alive():
            result = messagebox.askyesno("확인", "처리 작업이 진행 중입니다. 정말 종료하시겠습니까?")
            if not result:
                return
            
            # 처리 중지
            self.stop_processing()
        
        # 현재 설정 저장
        self.save_current_config()
        
        # 창 닫기
        self.root.destroy()


def main():
    """메인 함수"""
    root = tk.Tk()
    app = EnhancedToyoGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()