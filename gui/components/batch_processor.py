"""
Batch Processor Component

다중 폴더/파일 배치 처리 컴포넌트
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import json
from typing import List, Dict, Any, Optional
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gui.base_gui import BaseGUIComponent, ProcessingThread, ProgressTracker
from preprocess import run_toyo_preprocessing


class BatchItem:
    """배치 처리 항목"""
    
    def __init__(self, source_path: str, output_path: str = None, options: Dict = None):
        self.source_path = Path(source_path)
        self.output_path = Path(output_path) if output_path else None
        self.options = options or {}
        self.status = "대기"  # 대기, 처리중, 완료, 오류
        self.progress = 0.0
        self.error_message = ""
        self.result = None
        self.start_time = None
        self.end_time = None
    
    def get_display_name(self) -> str:
        """표시 이름 반환"""
        return self.source_path.name
    
    def get_output_path(self) -> Path:
        """출력 경로 반환 (자동 생성 포함)"""
        if self.output_path:
            return self.output_path
        
        # 자동 출력 경로 생성
        return Path("../../preprocess") / self.source_path.name


class BatchProcessorComponent(BaseGUIComponent):
    """배치 처리 컴포넌트"""
    
    def setup_component(self):
        """컴포넌트 설정"""
        self.batch_items: List[BatchItem] = []
        self.processing_thread: Optional[ProcessingThread] = None
        self.progress_tracker = ProgressTracker()
        
        self.frame = ttk.LabelFrame(self.parent, text="📦 배치 처리", padding="10")
        
        # 상단 컨트롤 영역
        self.setup_controls()
        
        # 배치 목록 영역
        self.setup_batch_list()
        
        # 하단 진행 상태 영역
        self.setup_progress_area()
        
        # 이벤트 바인딩
        self.setup_events()
    
    def setup_controls(self):
        """컨트롤 영역 설정"""
        control_frame = ttk.Frame(self.frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 추가/제거 버튼
        ttk.Button(control_frame, text="📁 폴더 추가", 
                  command=self.add_folders).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(control_frame, text="📄 목록에서 추가", 
                  command=self.add_from_list).grid(row=0, column=1, padx=5)
        
        ttk.Button(control_frame, text="🗑️ 선택 제거", 
                  command=self.remove_selected).grid(row=0, column=2, padx=5)
        
        ttk.Button(control_frame, text="🧹 모두 제거", 
                  command=self.clear_all).grid(row=0, column=3, padx=5)
        
        # 구분선
        ttk.Separator(control_frame, orient="vertical").grid(row=0, column=4, sticky=(tk.N, tk.S), padx=10)
        
        # 저장/불러오기 버튼
        ttk.Button(control_frame, text="💾 목록 저장", 
                  command=self.save_batch_list).grid(row=0, column=5, padx=5)
        
        ttk.Button(control_frame, text="📂 목록 불러오기", 
                  command=self.load_batch_list).grid(row=0, column=6, padx=5)
        
        # 우측 정렬 버튼들
        control_frame.columnconfigure(7, weight=1)
        
        # 일괄 설정 버튼
        ttk.Button(control_frame, text="⚙️ 일괄 설정", 
                  command=self.configure_all).grid(row=0, column=8, padx=5)
    
    def setup_batch_list(self):
        """배치 목록 영역 설정"""
        list_frame = ttk.LabelFrame(self.frame, text="처리 목록", padding="5")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 트리뷰로 배치 목록 표시
        columns = ("이름", "소스 경로", "출력 경로", "상태", "진행률", "옵션")
        self.batch_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=8)
        
        # 헤더 설정
        self.batch_tree.heading("#0", text="", anchor=tk.W)
        self.batch_tree.column("#0", width=0, stretch=False)
        
        column_widths = {"이름": 120, "소스 경로": 200, "출력 경로": 200, 
                        "상태": 80, "진행률": 80, "옵션": 100}
        
        for col in columns:
            self.batch_tree.heading(col, text=col, anchor=tk.W)
            self.batch_tree.column(col, width=column_widths.get(col, 100), anchor=tk.W)
        
        # 스크롤바
        batch_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                       command=self.batch_tree.yview)
        self.batch_tree.configure(yscrollcommand=batch_scrollbar.set)
        
        # 배치
        self.batch_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        batch_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 더블클릭 이벤트
        self.batch_tree.bind("<Double-1>", self.on_item_double_click)
        
        # 우클릭 메뉴
        self.setup_context_menu()
        
        # 그리드 설정
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
    
    def setup_context_menu(self):
        """우클릭 컨텍스트 메뉴 설정"""
        self.context_menu = tk.Menu(self.batch_tree, tearoff=0)
        self.context_menu.add_command(label="설정 편집", command=self.edit_selected_item)
        self.context_menu.add_command(label="출력 경로 변경", command=self.change_output_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="위로 이동", command=self.move_up)
        self.context_menu.add_command(label="아래로 이동", command=self.move_down)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="제거", command=self.remove_selected)
        
        self.batch_tree.bind("<Button-3>", self.show_context_menu)
    
    def setup_progress_area(self):
        """진행 상태 영역 설정"""
        progress_frame = ttk.LabelFrame(self.frame, text="진행 상태", padding="5")
        progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 전체 진행률
        ttk.Label(progress_frame, text="전체 진행률:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.overall_progress = ttk.Progressbar(progress_frame, length=300)
        self.overall_progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 10), pady=2)
        
        self.overall_progress_text = tk.StringVar(value="0/0 완료 (0%)")
        ttk.Label(progress_frame, textvariable=self.overall_progress_text).grid(row=0, column=2, sticky=tk.W, pady=2)
        
        # 현재 작업 진행률
        ttk.Label(progress_frame, text="현재 작업:").grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.current_progress = ttk.Progressbar(progress_frame, length=300)
        self.current_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 10), pady=2)
        
        self.current_progress_text = tk.StringVar(value="대기 중...")
        ttk.Label(progress_frame, textvariable=self.current_progress_text).grid(row=1, column=2, sticky=tk.W, pady=2)
        
        # 제어 버튼
        button_frame = ttk.Frame(progress_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        
        self.start_button = ttk.Button(button_frame, text="🚀 배치 처리 시작", 
                                      command=self.start_batch_processing)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.pause_button = ttk.Button(button_frame, text="⏸️ 일시정지", 
                                      command=self.pause_processing, state='disabled')
        self.pause_button.grid(row=0, column=1, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ 중지", 
                                     command=self.stop_processing, state='disabled')
        self.stop_button.grid(row=0, column=2, padx=5)
        
        # 그리드 설정
        progress_frame.columnconfigure(1, weight=1)
    
    def setup_events(self):
        """이벤트 설정"""
        self.progress_tracker.add_callback(self.on_progress_update)
    
    def get_frame(self) -> ttk.Frame:
        """컴포넌트 프레임 반환"""
        return self.frame
    
    def add_folders(self):
        """폴더 추가"""
        folders = filedialog.askdirectory(title="배치 처리할 폴더들을 선택하세요")
        if folders:
            # 여러 폴더 선택을 위해 개별적으로 처리
            folder_path = Path(folders)
            self.add_batch_item(str(folder_path))
    
    def add_from_list(self):
        """목록 파일에서 추가"""
        file_path = filedialog.askopenfilename(
            title="배치 목록 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    paths = [line.strip() for line in f if line.strip()]
                
                for path in paths:
                    if Path(path).exists():
                        self.add_batch_item(path)
                    else:
                        messagebox.showwarning("경고", f"경로가 존재하지 않습니다: {path}")
                        
            except Exception as e:
                messagebox.showerror("오류", f"파일 읽기 오류: {str(e)}")
    
    def add_batch_item(self, source_path: str, output_path: str = None, options: Dict = None):
        """배치 항목 추가"""
        if not Path(source_path).exists():
            messagebox.showerror("오류", f"경로가 존재하지 않습니다: {source_path}")
            return
        
        # 중복 확인
        for item in self.batch_items:
            if item.source_path == Path(source_path):
                messagebox.showwarning("중복", f"이미 목록에 있는 경로입니다: {source_path}")
                return
        
        # 새 항목 생성
        batch_item = BatchItem(source_path, output_path, options)
        self.batch_items.append(batch_item)
        
        # UI 업데이트
        self.refresh_batch_list()
    
    def remove_selected(self):
        """선택된 항목 제거"""
        selection = self.batch_tree.selection()
        if not selection:
            messagebox.showinfo("알림", "제거할 항목을 선택해주세요.")
            return
        
        # 선택된 항목들의 인덱스 찾기
        indices_to_remove = []
        for item_id in selection:
            index = self.batch_tree.index(item_id)
            indices_to_remove.append(index)
        
        # 역순으로 제거 (인덱스 변화 방지)
        for index in sorted(indices_to_remove, reverse=True):
            if 0 <= index < len(self.batch_items):
                del self.batch_items[index]
        
        self.refresh_batch_list()
    
    def clear_all(self):
        """모든 항목 제거"""
        if self.batch_items:
            result = messagebox.askyesno("확인", "모든 항목을 제거하시겠습니까?")
            if result:
                self.batch_items.clear()
                self.refresh_batch_list()
    
    def refresh_batch_list(self):
        """배치 목록 새로고침"""
        # 기존 항목 제거
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
        
        # 새 항목 추가
        for batch_item in self.batch_items:
            options_str = f"{len(batch_item.options)} 개 옵션" if batch_item.options else "기본값"
            
            values = (
                batch_item.get_display_name(),
                str(batch_item.source_path),
                str(batch_item.get_output_path()),
                batch_item.status,
                f"{batch_item.progress:.1f}%",
                options_str
            )
            
            item_id = self.batch_tree.insert("", "end", values=values)
            
            # 상태에 따른 색상 설정
            if batch_item.status == "완료":
                self.batch_tree.item(item_id, tags=("completed",))
            elif batch_item.status == "오류":
                self.batch_tree.item(item_id, tags=("error",))
            elif batch_item.status == "처리중":
                self.batch_tree.item(item_id, tags=("processing",))
        
        # 태그 스타일 설정
        self.batch_tree.tag_configure("completed", background="#E8F5E8")
        self.batch_tree.tag_configure("error", background="#FFE8E8")
        self.batch_tree.tag_configure("processing", background="#E8F0FF")
    
    def save_batch_list(self):
        """배치 목록 저장"""
        if not self.batch_items:
            messagebox.showinfo("알림", "저장할 배치 목록이 없습니다.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="배치 목록 저장",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")]
        )
        
        if file_path:
            try:
                batch_data = []
                for item in self.batch_items:
                    batch_data.append({
                        "source_path": str(item.source_path),
                        "output_path": str(item.output_path) if item.output_path else None,
                        "options": item.options
                    })
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(batch_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("완료", "배치 목록이 저장되었습니다.")
                
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {str(e)}")
    
    def load_batch_list(self):
        """배치 목록 불러오기"""
        file_path = filedialog.askopenfilename(
            title="배치 목록 불러오기",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    batch_data = json.load(f)
                
                # 기존 목록에 추가할지 확인
                if self.batch_items:
                    result = messagebox.askyesnocancel("확인", 
                        "기존 목록에 추가하시겠습니까?\n예: 추가, 아니오: 교체, 취소: 중단")
                    if result is None:  # 취소
                        return
                    elif result is False:  # 교체
                        self.batch_items.clear()
                
                # 데이터 로드
                for item_data in batch_data:
                    source_path = item_data["source_path"]
                    if Path(source_path).exists():
                        self.add_batch_item(
                            source_path,
                            item_data.get("output_path"),
                            item_data.get("options", {})
                        )
                    else:
                        print(f"경로가 존재하지 않아 제외됨: {source_path}")
                
                messagebox.showinfo("완료", "배치 목록이 불러와졌습니다.")
                
            except Exception as e:
                messagebox.showerror("오류", f"불러오기 실패: {str(e)}")
    
    def configure_all(self):
        """일괄 설정"""
        # 설정 다이얼로그 창 생성
        config_window = tk.Toplevel(self.frame)
        config_window.title("일괄 설정")
        config_window.geometry("400x300")
        config_window.transient(self.frame)
        config_window.grab_set()
        
        # TODO: 설정 옵션들 구현
        ttk.Label(config_window, text="일괄 설정 기능 구현 예정").pack(pady=20)
        
        ttk.Button(config_window, text="확인", 
                  command=config_window.destroy).pack(pady=10)
    
    def start_batch_processing(self):
        """배치 처리 시작"""
        if not self.batch_items:
            messagebox.showinfo("알림", "처리할 항목이 없습니다.")
            return
        
        # UI 상태 변경
        self.start_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.stop_button.config(state='normal')
        
        # 진행 상태 초기화
        self.progress_tracker.set_total_steps(len(self.batch_items))
        
        # 처리 스레드 시작
        self.processing_thread = ProcessingThread(
            None,  # TaskQueue는 별도로 관리
            self._batch_processing_worker
        )
        self.processing_thread.start()
    
    def _batch_processing_worker(self, task_queue, stop_event):
        """배치 처리 작업자"""
        for i, batch_item in enumerate(self.batch_items):
            if stop_event.is_set():
                break
            
            try:
                # 상태 업데이트
                batch_item.status = "처리중"
                self.frame.after(0, self.refresh_batch_list)
                
                # 현재 작업 정보 업데이트
                self.frame.after(0, lambda: self.current_progress_text.set(
                    f"처리 중: {batch_item.get_display_name()}"))
                
                # 실제 처리 수행
                results = run_toyo_preprocessing(
                    src_path=str(batch_item.source_path),
                    dst_path=str(batch_item.get_output_path()),
                    force_reprocess=batch_item.options.get('force_reprocess', False),
                    create_visualizations=batch_item.options.get('create_viz', True)
                )
                
                # 완료 상태 업데이트
                batch_item.status = "완료"
                batch_item.progress = 100.0
                batch_item.result = results
                
            except Exception as e:
                batch_item.status = "오류"
                batch_item.error_message = str(e)
            
            # 진행 상태 업데이트
            self.progress_tracker.update_step(i + 1, f"완료: {batch_item.get_display_name()}")
            self.frame.after(0, self.refresh_batch_list)
        
        # 처리 완료
        self.frame.after(0, self.on_batch_processing_complete)
    
    def on_batch_processing_complete(self):
        """배치 처리 완료"""
        # UI 상태 복원
        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        
        self.current_progress_text.set("배치 처리 완료")
        
        # 결과 요약
        completed = sum(1 for item in self.batch_items if item.status == "완료")
        errors = sum(1 for item in self.batch_items if item.status == "오류")
        
        messagebox.showinfo("완료", f"배치 처리 완료\n성공: {completed}개\n오류: {errors}개")
    
    def pause_processing(self):
        """처리 일시정지"""
        # TODO: 일시정지 기능 구현
        pass
    
    def stop_processing(self):
        """처리 중지"""
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.stop()
        
        self.on_batch_processing_complete()
    
    def on_progress_update(self, tracker: ProgressTracker):
        """진행 상태 업데이트"""
        progress = tracker.get_progress()
        self.overall_progress['value'] = progress * 100
        
        completed = tracker.current_step
        total = tracker.total_steps
        self.overall_progress_text.set(f"{completed}/{total} 완료 ({progress*100:.1f}%)")
    
    def show_context_menu(self, event):
        """컨텍스트 메뉴 표시"""
        self.context_menu.post(event.x_root, event.y_root)
    
    def on_item_double_click(self, event):
        """항목 더블클릭"""
        self.edit_selected_item()
    
    def edit_selected_item(self):
        """선택된 항목 편집"""
        # TODO: 항목 편집 다이얼로그 구현
        pass
    
    def change_output_path(self):
        """출력 경로 변경"""
        # TODO: 출력 경로 변경 구현
        pass
    
    def move_up(self):
        """선택된 항목을 위로 이동"""
        # TODO: 항목 순서 변경 구현
        pass
    
    def move_down(self):
        """선택된 항목을 아래로 이동"""
        # TODO: 항목 순서 변경 구현
        pass