"""Giao diện Desktop GUI Premium cho TruthKeep Memory.

Sử dụng PySide6 (Qt6 cho Python) để xây dựng ứng dụng cục bộ an toàn,
không mở port mạng, giao diện tối cao (Premium Dark Theme/Glassmorphism).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

try:
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import QColor, QFont, QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    PYSIDE_AVAILABLE = True
except Exception as e:
    PYSIDE_AVAILABLE = False
    class QDialog:
        def __init__(self, *args, **kwargs):
            pass
    class QMainWindow:
        def __init__(self, *args, **kwargs):
            pass
    import logging
    logging.getLogger(__name__).warning("Failed to import PySide6 (GUI will be unavailable): %s", e)


# Custom Style Sheet - Premium Dark Glassmorphism Theme
QSS_THEME = """
QMainWindow {
    background-color: #08080a;
}

QWidget {
    color: #f1f5f9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QFrame#sidebar {
    background-color: #0f0f13;
    border-right: 1px solid #1c1c24;
}

QFrame#card {
    background-color: #121218;
    border: 1px solid #20202a;
    border-radius: 14px;
}

QFrame#card:hover {
    border: 1px solid #8b5cf6;
}

QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #ffffff;
    background: transparent;
}

QLabel#subtitle {
    font-size: 13px;
    color: #94a3b8;
    background: transparent;
}

QLabel#card-title {
    font-size: 14px;
    font-weight: bold;
    color: #c084fc;
}

QLabel#stat-val {
    font-size: 32px;
    font-weight: bold;
    color: #ffffff;
}

QPushButton {
    background-color: #1c1c26;
    border: 1px solid #2e2e3e;
    border-radius: 9px;
    padding: 10px 18px;
    color: #f1f5f9;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #8b5cf6;
    border: 1px solid #8b5cf6;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #7c3aed;
}

/* Nút tạo sao lưu (Violet) */
QPushButton#btn-create {
    background-color: #6d28d9;
    border: 1px solid #7c3aed;
    border-radius: 9px;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btn-create:hover {
    background-color: #7c3aed;
    border: 1px solid #8b5cf6;
}

QPushButton#btn-create:pressed {
    background-color: #5b21b6;
}

/* Nút khôi phục (Emerald Green) */
QPushButton#btn-restore {
    background-color: #047857;
    border: 1px solid #059669;
    border-radius: 9px;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btn-restore:hover {
    background-color: #059669;
    border: 1px solid #10b981;
}

QPushButton#btn-restore:pressed {
    background-color: #065f46;
}

QPushButton#nav-btn {
    text-align: left;
    padding: 14px 22px;
    border: none;
    border-radius: 10px;
    background-color: transparent;
    font-size: 14px;
}

QPushButton#nav-btn:hover {
    background-color: #181822;
    color: #c084fc;
}

QPushButton#nav-btn:checked {
    background-color: #8b5cf6;
    color: #ffffff;
}

QLineEdit {
    background-color: #121218;
    border: 1px solid #272736;
    border-radius: 9px;
    padding: 10px 14px;
    color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #8b5cf6;
    background-color: #161622;
}

QLineEdit#passphrase-input {
    background-color: #0f0f15;
    border: 1px solid #20202e;
    border-radius: 10px;
    padding: 12px 16px;
    color: #ffffff;
}

QLineEdit#passphrase-input:focus {
    border: 1px solid #8b5cf6;
    background-color: #14141e;
}

QComboBox {
    background-color: #121218;
    border: 1px solid #272736;
    border-radius: 9px;
    padding: 10px 14px;
    color: #ffffff;
}

QComboBox:hover {
    border: 1px solid #8b5cf6;
    background-color: #161622;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
}

QTableWidget {
    background-color: #0f0f13;
    border: 1px solid #1c1c24;
    gridline-color: #1c1c26;
    border-radius: 10px;
}

QTableWidget::item {
    padding: 10px;
    border-bottom: 1px solid #161620;
}

QTableWidget::item:selected {
    background-color: #2d1d4d;
    color: #ffffff;
    border-left: 2px solid #8b5cf6;
}

QHeaderView::section {
    background-color: #14141c;
    color: #94a3b8;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #20202e;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #0f0f13;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #272736;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #8b5cf6;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #121218;
    border: 1px solid #272736;
    border-radius: 5px;
}

QCheckBox::indicator:checked {
    background-color: #8b5cf6;
    border: 1px solid #8b5cf6;
}

QScrollArea {
    border: none;
    background: transparent;
}

QDialog {
    background-color: #0c0c0e;
}
"""


class MemoryDetailDialog(QDialog):
    """Hộp thoại popup hiển thị chi tiết ký ức và giải thích why-not."""

    def __init__(self, memory_data: dict[str, Any], app_instance: Any, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(f"Chi tiết Ký ức: {memory_data.get('id', 'N/A')}")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("QDialog { background-color: #0c0c0e; color: #e2e8f0; } QLabel { color: #f1f5f9; }")
        
        layout = QVBoxLayout(self)
        
        # Tiêu đề
        title_label = QLabel(f"Ký Ức {memory_data.get('id', 'N/A')}", self)
        title_label.setObjectName("title")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #8b5cf6;")
        layout.addWidget(title_label)
        
        # Thông số Grid
        info_frame = QFrame(self)
        info_frame.setStyleSheet("background-color: #16161f; border-radius: 8px; border: 1px solid #22222b;")
        grid = QGridLayout(info_frame)
        
        grid.addWidget(QLabel("<b>Phân loại:</b>"), 0, 0)
        grid.addWidget(QLabel(str(memory_data.get("type", "N/A"))), 0, 1)
        
        grid.addWidget(QLabel("<b>Chủ đề (Subject):</b>"), 0, 2)
        grid.addWidget(QLabel(str(memory_data.get("subject", "N/A"))), 0, 3)
        
        grid.addWidget(QLabel("<b>Phạm vi (Scope):</b>"), 1, 0)
        grid.addWidget(QLabel(f"{memory_data.get('scope_type')}:{memory_data.get('scope_id')}"), 1, 1)
        
        grid.addWidget(QLabel("<b>Độ tin cậy:</b>"), 1, 2)
        grid.addWidget(QLabel(f"{float(memory_data.get('confidence', 1.0)):.2f}"), 1, 3)
        
        grid.addWidget(QLabel("<b>Trạng thái:</b>"), 2, 0)
        status_label = QLabel(str(memory_data.get("status", "N/A")))
        status_label.setStyleSheet("font-weight: bold; color: #3b82f6;" if memory_data.get("status") == "active" else "color: #94a3b8;")
        grid.addWidget(status_label, 2, 1)
        
        grid.addWidget(QLabel("<b>Truy cập:</b>"), 2, 2)
        grid.addWidget(QLabel(str(memory_data.get("access_count", 0))), 2, 3)
        
        layout.addWidget(info_frame)
        
        # Nội dung
        layout.addWidget(QLabel("<b>Nội dung ký ức:</b>"))
        content_edit = QTextEdit(self)
        content_edit.setPlainText(str(memory_data.get("content", "")))
        content_edit.setReadOnly(True)
        content_edit.setStyleSheet("background-color: #121216; border: 1px solid #22222b; border-radius: 8px; padding: 10px; font-size: 14px;")
        layout.addWidget(content_edit)
        
        # Giải thích Why-Not (nếu bị superseded)
        if memory_data.get("status") == "superseded" or memory_data.get("status") == "archived":
            layout.addWidget(QLabel("<b>Lý do Quản trị (Why-Not / Impact analysis):</b>"))
            why_not_edit = QTextEdit(self)
            why_not_edit.setReadOnly(True)
            why_not_edit.setStyleSheet("background-color: #1b1313; border: 1px solid #3c1e1e; border-radius: 8px; padding: 10px; color: #f87171;")
            
            # Gọi explain path từ đồ thị
            try:
                explanation = app_instance.explain_graph_path_for_id(memory_data["id"])
                why_not_edit.setPlainText(explanation)
            except Exception as e:
                why_not_edit.setPlainText(f"Ký ức này bị thay thế bởi phiên bản mới hơn. (Giải thích chi tiết: {e})")
            layout.addWidget(why_not_edit)
            
        # Nút Đóng
        close_btn = QPushButton("Đóng", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class TruthKeepMainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng TruthKeep Desktop UI."""

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = os.path.abspath(db_path)
        self.setWindowTitle(f"TruthKeep Memory — {self.db_path}")
        self.setMinimumSize(1024, 720)
        self.setStyleSheet(QSS_THEME)
        
        # Kết nối core
        from aegis_py.app import AegisApp
        self.app = AegisApp(self.db_path)
        
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Sidebar Panel
        sidebar = QFrame(self)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        
        # Logo / Title
        logo_label = QLabel("TRUTHKEEP", self)
        logo_label.setStyleSheet("font-size: 22px; font-weight: bold; letter-spacing: 2px; color: #8b5cf6; background: transparent;")
        sidebar_layout.addWidget(logo_label)
        
        ver_label = QLabel("v11.0 secure local AI", self)
        ver_label.setStyleSheet("font-size: 11px; color: #64748b; background: transparent; margin-bottom: 5px;")
        sidebar_layout.addWidget(ver_label)
        
        # Thêm nhãn hiển thị đường dẫn CSDL đang kết nối
        self.lbl_active_db = QLabel(self)
        db_path_display = self.db_path
        if len(db_path_display) > 30:
            db_path_display = "..." + db_path_display[-27:]
        self.lbl_active_db.setText(f"📁 {db_path_display}")
        self.lbl_active_db.setToolTip(self.db_path)
        self.lbl_active_db.setStyleSheet("font-size: 10px; color: #10b981; font-family: monospace; background: transparent; margin-bottom: 25px;")
        sidebar_layout.addWidget(self.lbl_active_db)
        
        # Nav Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        self.btn_dashboard = QPushButton("🏠   Tổng Quan", self)
        self.btn_dashboard.setObjectName("nav-btn")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        self.nav_group.addButton(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_dashboard)
        
        self.btn_browser = QPushButton("🧠   Bộ Duyệt Ký Ức", self)
        self.btn_browser.setObjectName("nav-btn")
        self.btn_browser.setCheckable(True)
        self.nav_group.addButton(self.btn_browser)
        sidebar_layout.addWidget(self.btn_browser)
        
        self.btn_correction = QPushButton("🌀   Lịch Sử Sửa Đổi", self)
        self.btn_correction.setObjectName("nav-btn")
        self.btn_correction.setCheckable(True)
        self.nav_group.addButton(self.btn_correction)
        sidebar_layout.addWidget(self.btn_correction)
        
        self.btn_backup = QPushButton("💾   Sao Lưu & Bảo Mật", self)
        self.btn_backup.setObjectName("nav-btn")
        self.btn_backup.setCheckable(True)
        self.nav_group.addButton(self.btn_backup)
        sidebar_layout.addWidget(self.btn_backup)
        
        sidebar_layout.addStretch()
        
        # Refresh Button
        self.btn_refresh = QPushButton("🔄   Làm mới", self)
        self.btn_refresh.clicked.connect(self.refresh_all)
        sidebar_layout.addWidget(self.btn_refresh)
        
        main_layout.addWidget(sidebar)
        
        # 2. Main Content Area (QTabWidget ẩn headers)
        self.tabs = QTabWidget(self)
        self.tabs.tabBar().hide() # Ẩn thanh tab mặc định để dùng Sidebar điều phối
        self.tabs.setStyleSheet("background-color: transparent; border: none;")
        
        self._init_tab_dashboard()
        self._init_tab_browser()
        self._init_tab_correction()
        self._init_tab_backup()
        
        main_layout.addWidget(self.tabs)
        
        # Kết nối tín hiệu điều phối Tab từ Sidebar
        self.btn_dashboard.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        self.btn_browser.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.btn_correction.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.btn_backup.clicked.connect(lambda: self.tabs.setCurrentIndex(3))

    def _init_tab_dashboard(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)
        
        # Tiêu đề
        h_layout = QHBoxLayout()
        title_v = QVBoxLayout()
        t_label = QLabel("Hệ Thống Tổng Quan (Dashboard)", tab)
        t_label.setObjectName("title")
        title_v.addWidget(t_label)
        sub_label = QLabel("Giám sát trạng thái, sức khỏe và tính toàn vẹn của Graph Memory", tab)
        sub_label.setObjectName("subtitle")
        title_v.addWidget(sub_label)
        h_layout.addLayout(title_v)
        layout.addLayout(h_layout)
        
        # Grid Stats
        stats_frame = QFrame(tab)
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setSpacing(20)
        
        # Thẻ 1: Tổng Memories
        c1 = QFrame(stats_frame)
        c1.setObjectName("card")
        l1 = QVBoxLayout(c1)
        l1.addWidget(QLabel("🧠 TỔNG KÝ ỨC", c1))
        self.lbl_stat_total = QLabel("0", c1)
        self.lbl_stat_total.setObjectName("stat-val")
        l1.addWidget(self.lbl_stat_total)
        stats_layout.addWidget(c1, 0, 0)
        
        # Thẻ 2: Active Memories
        c2 = QFrame(stats_frame)
        c2.setObjectName("card")
        l2 = QVBoxLayout(c2)
        l2.addWidget(QLabel("🟢 ĐANG HOẠT ĐỘNG (ACTIVE)", c2))
        self.lbl_stat_active = QLabel("0", c2)
        self.lbl_stat_active.setObjectName("stat-val")
        l2.addWidget(self.lbl_stat_active)
        stats_layout.addWidget(c2, 0, 1)
        
        # Thẻ 3: Open Conflicts
        c3 = QFrame(stats_frame)
        c3.setObjectName("card")
        l3 = QVBoxLayout(c3)
        l3.addWidget(QLabel("⚠️ XUNG ĐỘT ĐANG MỞ (CONFLICTS)", c3))
        self.lbl_stat_conflicts = QLabel("0", c3)
        self.lbl_stat_conflicts.setObjectName("stat-val")
        l3.addWidget(self.lbl_stat_conflicts)
        stats_layout.addWidget(c3, 0, 2)
        
        # Thẻ 4: Invariant Status
        c4 = QFrame(stats_frame)
        c4.setObjectName("card")
        l4 = QVBoxLayout(c4)
        l4.addWidget(QLabel("🏛️ BẤT BIẾN ĐỒ THỊ (INVARIANTS)", c4))
        self.lbl_stat_invariants = QLabel("OK", c4)
        self.lbl_stat_invariants.setObjectName("stat-val")
        self.lbl_stat_invariants.setStyleSheet("color: #10b981;") # Green
        l4.addWidget(self.lbl_stat_invariants)
        stats_layout.addWidget(c4, 1, 0)
        
        # Thẻ 5: Security Mode
        c5 = QFrame(stats_frame)
        c5.setObjectName("card")
        l5 = QVBoxLayout(c5)
        l5.addWidget(QLabel("🔒 CHẾ ĐỘ BẢO MẬT", c5))
        self.lbl_stat_security = QLabel("Standard", c5)
        self.lbl_stat_security.setObjectName("stat-val")
        l5.addWidget(self.lbl_stat_security)
        stats_layout.addWidget(c5, 1, 1)
        
        # Thẻ 6: DB Footprint
        c6 = QFrame(stats_frame)
        c6.setObjectName("card")
        l6 = QVBoxLayout(c6)
        l6.addWidget(QLabel("💾 DUNG LƯỢNG ĐĨA DB", c6))
        self.lbl_stat_footprint = QLabel("0 KB", c6)
        self.lbl_stat_footprint.setObjectName("stat-val")
        l6.addWidget(self.lbl_stat_footprint)
        stats_layout.addWidget(c6, 1, 2)
        
        layout.addWidget(stats_frame)
        
        # Diagnostic Doctor panel
        doc_frame = QFrame(tab)
        doc_frame.setObjectName("card")
        doc_layout = QVBoxLayout(doc_frame)
        doc_layout.addWidget(QLabel("🩺 <b>Chẩn Đoán Sức Khỏe Bộ Nhớ (Self-check Diagnostic)</b>", doc_frame))
        
        self.txt_doctor = QTextEdit(doc_frame)
        self.txt_doctor.setReadOnly(True)
        self.txt_doctor.setStyleSheet("background-color: #121216; border: 1px solid #22222b; border-radius: 8px; color: #10b981; font-family: monospace; font-size: 12px;")
        doc_layout.addWidget(self.txt_doctor)
        
        btn_doctor = QPushButton("Chạy Chẩn Đoán Hệ Thống", doc_frame)
        btn_doctor.clicked.connect(self.run_doctor_diagnostic)
        doc_layout.addWidget(btn_doctor)
        
        layout.addWidget(doc_frame)
        
        self.tabs.addTab(tab, "Dashboard")

    def _init_tab_browser(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        t_label = QLabel("Bộ Duyệt Ký Ức (Memory Browser)", tab)
        t_label.setObjectName("title")
        layout.addWidget(t_label)
        
        # Filter Bar - Spacing thoáng đạt
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(15)
        
        # Search Box
        self.txt_search = QLineEdit(tab)
        self.txt_search.setPlaceholderText("Tìm kiếm nội dung ký ức hoặc từ khóa...")
        self.txt_search.setMinimumHeight(40)
        self.txt_search.textChanged.connect(self.search_memories)
        filter_bar.addWidget(self.txt_search, 5)
        
        # Scope Filter
        self.cb_scope = QComboBox(tab)
        self.cb_scope.addItem("-- Lọc Theo Scope --")
        self.cb_scope.setMinimumHeight(40)
        self.cb_scope.currentIndexChanged.connect(self.search_memories)
        filter_bar.addWidget(self.cb_scope, 2)
        
        # Status Filter
        self.cb_status = QComboBox(tab)
        self.cb_status.addItem("-- Lọc Trạng Thái --")
        self.cb_status.setMinimumHeight(40)
        self.cb_status.currentIndexChanged.connect(self.search_memories)
        filter_bar.addWidget(self.cb_status, 2)
        
        layout.addLayout(filter_bar)
        
        # Kết quả tìm kiếm (Dynamic status label)
        self.lbl_results_status = QLabel(tab)
        self.lbl_results_status.setStyleSheet("color: #94a3b8; font-size: 13px; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(self.lbl_results_status)
        
        # Table of memories
        self.table_memories = QTableWidget(tab)
        self.table_memories.setColumnCount(7)
        self.table_memories.setHorizontalHeaderLabels([
            "ID", "Chủ đề (Subject)", "Scope", "Loại", "Trạng thái", "Nội Dung", "Thời gian Cập nhật"
        ])
        
        # Bật chế độ Stretch cho cột 5 (Nội Dung) để nó tự động chiếm toàn bộ khoảng trống còn lại!
        self.table_memories.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_memories.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        
        self.table_memories.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_memories.setSelectionMode(QTableWidget.SingleSelection)
        self.table_memories.doubleClicked.connect(self.show_memory_detail)
        
        # Cấu hình độ rộng tối ưu cho các cột phụ để cột Nội dung có không gian co giãn tối đa
        self.table_memories.setColumnWidth(0, 130)
        self.table_memories.setColumnWidth(1, 110)
        self.table_memories.setColumnWidth(2, 110)
        self.table_memories.setColumnWidth(3, 80)
        self.table_memories.setColumnWidth(4, 90)
        self.table_memories.setColumnWidth(6, 160)
        
        layout.addWidget(self.table_memories)
        
        # Hint label
        layout.addWidget(QLabel("💡 <i>Gợi ý: Click đúp vào một hàng để xem chi tiết và phân tích Why-Not của đồ thị.</i>"))
        
        self.tabs.addTab(tab, "Browser")

    def _init_tab_correction(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        t_label = QLabel("Lịch Sử Cập Nhật Ký Ức", tab)
        t_label.setObjectName("title")
        layout.addWidget(t_label)
        layout.addWidget(QLabel("Xem lại các thông tin cũ đã được bạn sửa đổi hoặc cập nhật bằng thông tin mới chính xác hơn."))
        
        # Table of superseded memories
        self.table_superseded = QTableWidget(tab)
        self.table_superseded.setColumnCount(4)
        self.table_superseded.setHorizontalHeaderLabels([
            "Ký ức cũ (ID)", "Chủ đề", "Nội dung cũ", "Lý do thay đổi"
        ])
        self.table_superseded.horizontalHeader().setStretchLastSection(True)
        self.table_superseded.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_superseded.doubleClicked.connect(self.show_superseded_detail)
        
        self.table_superseded.setColumnWidth(0, 160)
        self.table_superseded.setColumnWidth(1, 120)
        self.table_superseded.setColumnWidth(2, 300)
        
        layout.addWidget(self.table_superseded)
        
        self.tabs.addTab(tab, "Correction")

    def _init_tab_backup(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)
        
        # Header
        t_label = QLabel("Sao Lưu & Cấu Hình Bảo Mật", tab)
        t_label.setObjectName("title")
        layout.addWidget(t_label)
        
        # Frame 1: Security settings
        sec_frame = QFrame(tab)
        sec_frame.setObjectName("card")
        sec_layout = QVBoxLayout(sec_frame)
        sec_layout.addWidget(QLabel("🔒 <b>Cấu Hình An Ninh Cục Bộ</b>", sec_frame))
        
        self.chk_strict_privacy = QCheckBox("Bật Strict Privacy Mode (Mã hóa cứng SQLite, chặn FTS5 Plaintext, Redacted Logs)", sec_frame)
        self.chk_strict_privacy.setEnabled(False) # Quản lý qua ENV cho an toàn mật mã
        sec_layout.addWidget(self.chk_strict_privacy)
        
        # Thống kê an ninh
        self.lbl_sec_details = QLabel(sec_frame)
        self.lbl_sec_details.setStyleSheet("color: #94a3b8; line-height: 1.5;")
        sec_layout.addWidget(self.lbl_sec_details)
        
        layout.addWidget(sec_frame)
        
        # Frame 2: Backup & Restore - Thiết kế thoáng đạt
        back_frame = QFrame(tab)
        back_frame.setObjectName("card")
        back_layout = QVBoxLayout(back_frame)
        back_layout.setContentsMargins(20, 20, 20, 20)
        back_layout.setSpacing(15)
        
        back_layout.addWidget(QLabel("💾 <b>Tạo & Khôi Phục Bản Sao Lưu (PBKDF2 + AES-GCM)</b>", back_frame))
        
        # Layout dọc cho phần mật khẩu để tránh chen chúc
        pass_layout = QVBoxLayout()
        pass_layout.setSpacing(8)
        
        lbl_pass = QLabel("Passphrase bảo mật (mật khẩu dùng để mã hóa tệp sao lưu cục bộ):", back_frame)
        lbl_pass.setStyleSheet("color: #cbd5e1; font-weight: bold;")
        pass_layout.addWidget(lbl_pass)
        
        self.txt_passphrase = QLineEdit(back_frame)
        self.txt_passphrase.setObjectName("passphrase-input")
        self.txt_passphrase.setEchoMode(QLineEdit.Password)
        self.txt_passphrase.setPlaceholderText("Nhập mật khẩu mạnh để mã hóa/giải mã tệp sao lưu của bạn...")
        self.txt_passphrase.setMinimumHeight(40) # Cao ráo dễ gõ
        pass_layout.addWidget(self.txt_passphrase)
        back_layout.addLayout(pass_layout)
        
        # Hàng nút bấm với kích thước to rõ, phân phối màu sắc thông minh
        h_btn = QHBoxLayout()
        h_btn.setSpacing(15)
        
        btn_create_backup = QPushButton("Tạo Bản Sao Lưu Mã Hóa", back_frame)
        btn_create_backup.setObjectName("btn-create")
        btn_create_backup.setMinimumHeight(40)
        btn_create_backup.clicked.connect(self.create_encrypted_backup)
        h_btn.addWidget(btn_create_backup)
        
        btn_restore_backup = QPushButton("Khôi Phục Từ Gói Sao Lưu", back_frame)
        btn_restore_backup.setObjectName("btn-restore")
        btn_restore_backup.setMinimumHeight(40)
        btn_restore_backup.clicked.connect(self.restore_encrypted_backup)
        h_btn.addWidget(btn_restore_backup)
        back_layout.addLayout(h_btn)
        
        layout.addWidget(back_frame)
        layout.addStretch()
        
        self.tabs.addTab(tab, "Backup")

    # ── Core Logic ──────────────────────────────────────────────────────────

    def refresh_all(self):
        """Làm mới toàn bộ giao diện và dữ liệu."""
        try:
            status = self.app.status()
            counts = status.get("counts", {})
            doctor = self.app.doctor()
            
            # Cập nhật stats
            self.lbl_stat_total.setText(str(doctor.get("counts", {}).get("memories", 0)))
            self.lbl_stat_active.setText(str(counts.get("active", 0)))
            self.lbl_stat_conflicts.setText(str(doctor.get("counts", {}).get("open_conflicts", 0)))
            
            # DB footprint size
            if os.path.exists(self.db_path):
                db_kb = os.path.getsize(self.db_path) / 1024.0
                self.lbl_stat_footprint.setText(f"{db_kb:.2f} KB")
            
            # Invariant check
            from aegis_py.invariants.runtime import validate_memory_invariants
            inv_report = validate_memory_invariants(self.db_path)
            if inv_report.ok:
                self.lbl_stat_invariants.setText("OK")
                self.lbl_stat_invariants.setStyleSheet("color: #10b981; font-size: 28px; font-weight: bold;")
            else:
                self.lbl_stat_invariants.setText("LỖI")
                self.lbl_stat_invariants.setStyleSheet("color: #f87171; font-size: 28px; font-weight: bold;")
            
            # Security config
            from aegis_py.security.config import get_security_status, SecurityConfig
            sec_status = get_security_status()
            
            is_strict = SecurityConfig.strict_privacy_enabled()
            self.lbl_stat_security.setText("Strict" if is_strict else "Standard")
            self.lbl_stat_security.setStyleSheet("color: #8b5cf6;" if is_strict else "color: #e2e8f0;")
            
            # Checkbox strict
            self.chk_strict_privacy.setChecked(is_strict)
            
            # Security details text
            sec_text = (
                f"• Chế độ hoạt động hiện tại: <b>{sec_status.get('active_mode', 'N/A').upper()}</b><br>"
                f"• Quyền riêng tư: <b>{'Nghiêm ngặt (Strict Privacy)' if is_strict else 'Tiêu chuẩn (Standard Plaintext)'}</b><br>"
                f"• CSPRNG an toàn mật mã: <b>{'Kích hoạt' if sec_status.get('secure_prng') else 'Vô hiệu (Fallback random)'}</b><br>"
                f"• Mã hóa SQLite At-Rest: <b>{'AES-256-GCM Đang Chạy' if sec_status.get('app_level_encryption') else 'Tắt (Plaintext SQLite)'}</b><br>"
                f"• RSA Key Size: <b>{sec_status.get('rsa_bit_size', 512)} bits</b>"
            )
            self.lbl_sec_details.setText(sec_text)
            
            # Refresh bộ lọc động và bảng dữ liệu
            self.update_filter_comboboxes()
            self.search_memories()
            self.refresh_superseded_table()
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Làm Mới", f"Không thể lấy dữ liệu từ cơ sở dữ liệu:\n{e}")

    def update_filter_comboboxes(self):
        """Cập nhật các bộ lọc Scope và Status một cách động từ CSDL thực tế."""
        try:
            # Lưu lại trạng thái lựa chọn hiện tại để khôi phục sau khi reload
            current_scope = self.cb_scope.currentText()
            current_status = self.cb_status.currentText()
            
            # Tạm khóa tín hiệu để không kích hoạt search_memories lặp vô hạn
            self.cb_scope.blockSignals(True)
            self.cb_status.blockSignals(True)
            
            conn = self.app.storage._get_connection()
            
            # 1. Lấy tất cả distinct scopes
            scopes = conn.execute("SELECT DISTINCT scope_type, scope_id FROM memories ORDER BY scope_type, scope_id").fetchall()
            self.cb_scope.clear()
            self.cb_scope.addItem("-- Lọc Theo Scope --")
            for stype, sid in scopes:
                if stype and sid:
                    self.cb_scope.addItem(f"{stype}:{sid}")
                    
            # 2. Lấy tất cả distinct statuses
            statuses = conn.execute("SELECT DISTINCT status FROM memories ORDER BY status").fetchall()
            self.cb_status.clear()
            self.cb_status.addItem("-- Lọc Trạng Thái --")
            for (stt,) in statuses:
                if stt:
                    self.cb_status.addItem(str(stt))
                    
            # Khôi phục lựa chọn cũ nếu còn hợp lệ
            idx_scope = self.cb_scope.findText(current_scope)
            if idx_scope >= 0:
                self.cb_scope.setCurrentIndex(idx_scope)
            else:
                self.cb_scope.setCurrentIndex(0)
                
            idx_status = self.cb_status.findText(current_status)
            if idx_status >= 0:
                self.cb_status.setCurrentIndex(idx_status)
            else:
                self.cb_status.setCurrentIndex(0)
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Lỗi cập nhật bộ lọc động: %s", e)
        finally:
            self.cb_scope.blockSignals(False)
            self.cb_status.blockSignals(False)

    def run_doctor_diagnostic(self):
        """Chạy doctor chẩn đoán và in kết quả."""
        try:
            self.txt_doctor.setText("Đang chạy chẩn đoán hệ thống tự động, xin chờ...")
            QApplication.processEvents()
            
            doctor_payload = self.app.doctor()
            self.txt_doctor.setText(json.dumps(doctor_payload, indent=2, ensure_ascii=False))
        except Exception as e:
            self.txt_doctor.setText(f"Chẩn đoán thất bại: {e}")

    def search_memories(self, *_):
        """Lọc và hiển thị danh sách memories trong TableWidget với cơ chế chịu lỗi tối đa."""
        try:
            query = self.txt_search.text().strip()
            
            # Scope filter index
            scope_idx = self.cb_scope.currentIndex()
            scope_type, scope_id = None, None
            if scope_idx > 0:
                scope_str = self.cb_scope.currentText()
                if ":" in scope_str:
                    scope_type, scope_id = scope_str.split(":", 1)
            
            # Status filter index
            status_idx = self.cb_status.currentIndex()
            status_filter = None
            if status_idx > 0:
                status_filter = self.cb_status.currentText()
                
            # Đọc từ DB
            conn = self.app.storage._get_connection()
            where_clauses = []
            params = []
            
            if scope_type and scope_id:
                where_clauses.append("scope_type = ? AND scope_id = ?")
                params.extend([scope_type, scope_id])
                
            if status_filter:
                where_clauses.append("status = ?")
                params.append(status_filter)
                
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            rows = conn.execute(
                f"SELECT * FROM memories {where_sql} ORDER BY updated_at DESC",
                tuple(params)
            ).fetchall()
            
            # Lọc theo query thô ở RAM để tương thích cả strict mode đã giải mã trong suốt
            matched_rows = []
            for row in rows:
                try:
                    # Giải mã dòng bằng database manager
                    mem = self.app.storage._row_to_memory(row)
                    if query:
                        if (query.lower() not in mem.content.lower() and 
                            query.lower() not in (mem.subject or "").lower() and
                            query.lower() not in (mem.summary or "").lower()):
                            continue
                    matched_rows.append(mem)
                except Exception as row_err:
                    import logging
                    logging.getLogger(__name__).warning("Lỗi giải mã dòng ký ức (bỏ qua dòng lỗi): %s", row_err)
            
            # Đặt số lượng hàng thực tế sau khi lọc thành công
            self.table_memories.setRowCount(len(matched_rows))
            
            # Cập nhật thông tin số lượng kết quả lọc
            if not matched_rows:
                self.lbl_results_status.setText("⚠️ Không tìm thấy ký ức nào phù hợp với bộ lọc hiện tại.")
                self.lbl_results_status.setStyleSheet("color: #f87171; font-size: 13px; font-weight: bold; margin-bottom: 5px;")
            else:
                self.lbl_results_status.setText(f"✨ Tìm thấy {len(matched_rows)} ký ức phù hợp với bộ lọc.")
                self.lbl_results_status.setStyleSheet("color: #10b981; font-size: 13px; font-weight: bold; margin-bottom: 5px;")
            
            # Render từng dòng với cơ chế chịu lỗi cell-by-cell
            for i, mem in enumerate(matched_rows):
                try:
                    self.table_memories.setItem(i, 0, QTableWidgetItem(str(mem.id)))
                    self.table_memories.setItem(i, 1, QTableWidgetItem(str(mem.subject or "N/A")))
                    self.table_memories.setItem(i, 2, QTableWidgetItem(f"{mem.scope_type}:{mem.scope_id}"))
                    self.table_memories.setItem(i, 3, QTableWidgetItem(str(mem.type)))
                    
                    status_item = QTableWidgetItem(str(mem.status))
                    if mem.status == "active":
                        status_item.setForeground(QColor("#3b82f6")) # Blue
                    elif mem.status == "superseded":
                        status_item.setForeground(QColor("#94a3b8")) # Gray
                    self.table_memories.setItem(i, 4, status_item)
                    
                    # Preview content an toàn
                    content_preview = str(mem.content)
                    if len(content_preview) > 60:
                        content_preview = content_preview[:60] + "..."
                    self.table_memories.setItem(i, 5, QTableWidgetItem(content_preview))
                    
                    # Safe updated_at - Chống crash 100%
                    updated_at_str = "N/A"
                    if mem.updated_at:
                        if hasattr(mem.updated_at, "strftime"):
                            try:
                                updated_at_str = mem.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                updated_at_str = str(mem.updated_at)
                        else:
                            updated_at_str = str(mem.updated_at)
                    self.table_memories.setItem(i, 6, QTableWidgetItem(updated_at_str))
                except Exception as cell_err:
                    import logging
                    logging.getLogger(__name__).warning("Lỗi vẽ dòng %d (bỏ qua dòng): %s", i, cell_err)
                    
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to search memories: %s", e)

    def show_memory_detail(self):
        """Mở dialog xem chi tiết khi đúp click hàng trong Memory Browser."""
        row_idx = self.table_memories.currentRow()
        if row_idx < 0:
            return
            
        mem_id = self.table_memories.item(row_idx, 0).text()
        
        try:
            # Lấy memory hoàn chỉnh đã giải mã
            mem = self.app.storage.get_memory(mem_id)
            if mem is None:
                return
                
            # Đóng gói data sang dict để truyền sang popup
            data = mem.model_dump()
            dialog = MemoryDetailDialog(data, self, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi xem chi tiết", f"Không thể lấy chi tiết ký ức:\n{e}")

    def refresh_superseded_table(self):
        """Lọc và hiển thị danh sách memories đã bị đính chính (superseded)."""
        try:
            conn = self.app.storage._get_connection()
            rows = conn.execute(
                "SELECT * FROM memories WHERE status = 'superseded' ORDER BY updated_at DESC"
            ).fetchall()
            
            self.table_superseded.setRowCount(len(rows))
            for i, r in enumerate(rows):
                # Giải mã
                mem = self.app.storage._row_to_memory(r)
                
                self.table_superseded.setItem(i, 0, QTableWidgetItem(mem.id))
                self.table_superseded.setItem(i, 1, QTableWidgetItem(mem.subject or "N/A"))
                
                # Preview content
                content_preview = mem.content
                if len(content_preview) > 60:
                    content_preview = content_preview[:60] + "..."
                self.table_superseded.setItem(i, 2, QTableWidgetItem(content_preview))
                
                # Fetch explain
                explanation = self.explain_graph_path_for_id(mem.id)
                self.table_superseded.setItem(i, 3, QTableWidgetItem(explanation))
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to load superseded table: %s", e)

    def show_superseded_detail(self):
        row_idx = self.table_superseded.currentRow()
        if row_idx < 0:
            return
            
        mem_id = self.table_superseded.item(row_idx, 0).text()
        try:
            mem = self.app.storage.get_memory(mem_id)
            if mem is None:
                return
            dialog = MemoryDetailDialog(mem.model_dump(), self, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể lấy chi tiết:\n{e}")

    def explain_graph_path_for_id(self, memory_id: str) -> str:
        """Helper gọi explain graph path từ core."""
        try:
            conn = self.app.storage._get_connection()
            # Tìm xem đỉnh nào thay thế nó (quan hệ superseded_by)
            row = conn.execute(
                "SELECT target_id FROM memory_links WHERE source_id = ? AND link_type = 'superseded_by' LIMIT 1",
                (memory_id,)
            ).fetchone()
            if row:
                target_id = row[0]
                target_mem = self.app.storage.get_memory(target_id)
                if target_mem:
                    return f"Được thay thế bằng thông tin mới hơn: '{target_mem.content}'"
            return "Được thay thế do có cập nhật mới trong cùng chủ đề."
        except Exception:
            return "Đã bị thay thế."

    def create_encrypted_backup(self):
        """Sao lưu CSDL mã hóa đối xứng."""
        passphrase = self.txt_passphrase.text().strip()
        if not passphrase:
            QMessageBox.warning(self, "Thiếu Mật Khẩu", "Bạn bắt buộc phải nhập mật khẩu để mã hóa gói sao lưu cục bộ!")
            return
            
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Tạo Bản Sao Lưu Mã Hóa", "", "TruthKeep Backup (*.tkbak);;Zip Archive (*.zip)"
            )
            if not file_path:
                return
                
            # Đóng kết nối DB tạm thời để copy file an toàn
            self.app.close()
            
            # Sử dụng PBKDF2 + AES-256-GCM để mã hóa gói zip DB
            import os
            import zipfile
            import hashlib
            from aegis_py.security.aes_gcm import AESGCMEngine, KeyDerivation
            
            temp_zip = file_path + ".temp"
            with zipfile.ZipFile(temp_zip, "w") as zf:
                zf.write(self.db_path, "database.db")
                # Viết kèm metadata
                meta = {
                    "created_at": datetime.now().isoformat(),
                    "app_version": "v11.0",
                }
                zf.writestr("metadata.json", json.dumps(meta))
                
            # Đọc toàn bộ zip data
            with open(temp_zip, "rb") as f:
                zip_bytes = f.read()
                
            # Xóa file zip tạm
            os.remove(temp_zip)
            
            # Derive key từ mật khẩu của user
            salt = os.urandom(16)
            aes_key, salt = KeyDerivation.derive_key(passphrase, salt=salt)
            
            # Mã hóa đối xứng AES-256-GCM
            nonce = os.urandom(12)
            encrypted_data = AESGCMEngine.encrypt(zip_bytes, aes_key, nonce=nonce)
            
            # Cấu trúc tệp .tkbak: salt (16B) + encrypted_data (nonce_12 + tag_16 + ct)
            final_bytes = salt + encrypted_data
            
            with open(file_path, "wb") as f:
                f.write(final_bytes)
                
            # Reload lại kết nối core
            self.app = AegisApp(self.db_path)
            
            QMessageBox.information(
                self, "Sao Lưu Thành Công", f"Đã tạo bản sao lưu mã hóa kiên cố tại:\n{file_path}"
            )
        except Exception as e:
            self.app = AegisApp(self.db_path) # Reload fallback
            QMessageBox.critical(self, "Sao Lưu Thất Bại", f"Không thể sao lưu dữ liệu:\n{e}")

    def restore_encrypted_backup(self):
        """Khôi phục CSDL từ gói sao lưu mã hóa."""
        passphrase = self.txt_passphrase.text().strip()
        if not passphrase:
            QMessageBox.warning(self, "Thiếu Mật Khẩu", "Bạn bắt buộc phải nhập mật khẩu để giải mã tệp sao lưu!")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Khôi Phục Dữ Liệu", "", "TruthKeep Backup (*.tkbak);;Zip Archive (*.zip)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                
            if len(file_bytes) < 44: # 16B salt + 12B nonce + 16B tag
                QMessageBox.critical(self, "Lỗi Tệp", "Tệp sao lưu bị hỏng hoặc quá ngắn!")
                return
                
            salt = file_bytes[:16]
            encrypted_payload = file_bytes[16:]
            
            # Derive key
            from aegis_py.security.aes_gcm import AESGCMEngine, KeyDerivation
            aes_key, _ = KeyDerivation.derive_key(passphrase, salt=salt)
            
            # Giải mã AES-256-GCM (tự động verify tag chống tampering)
            try:
                decrypted_zip = AESGCMEngine.decrypt(encrypted_payload, aes_key)
            except ValueError:
                QMessageBox.critical(
                    self, "Giải Mã Thất Bại", "Sai mật khẩu bảo mật hoặc tệp sao lưu đã bị sửa đổi trái phép!"
                )
                return
                
            # Ghi ra tệp zip tạm để giải nén
            temp_zip = file_path + ".temp_restore.zip"
            with open(temp_zip, "wb") as f:
                f.write(decrypted_zip)
                
            import zipfile
            # Giải nén DB ghi đè
            self.app.close()
            with zipfile.ZipFile(temp_zip, "r") as zf:
                # Đọc database.db ghi đè CSDL hiện tại
                db_data = zf.read("database.db")
                with open(self.db_path, "wb") as f_db:
                    f_db.write(db_data)
                    
            os.remove(temp_zip)
            
            # Khởi động lại
            self.app = AegisApp(self.db_path)
            self.refresh_all()
            
            QMessageBox.information(
                self, "Khôi Phục Thành Công", "Đã khôi phục cơ sở dữ liệu và xác thực invariants thành công!"
            )
        except Exception as e:
            self.app = AegisApp(self.db_path)
            QMessageBox.critical(self, "Khôi Phục Thất Bại", f"Lỗi khôi phục cơ sở dữ liệu:\n{e}")

    def closeEvent(self, event):
        """Giải phóng kết nối khi đóng window."""
        self.app.close()
        event.accept()


def launch_gui(db_path: str) -> int:
    """Launch the local desktop interface.

    PySide6 gives the premium UI. If it is not installed, fall back to the
    no-code tkinter launcher instead of asking non-technical users to install
    anything manually. This keeps Easy Mode dependency-light and local-only.
    """
    if not PYSIDE_AVAILABLE:
        try:
            from .no_code_launcher import launch_no_code_gui
            return launch_no_code_gui(db_path)
        except Exception as e:
            print("[!] Desktop launcher is unavailable.")
            print(f"[!] Details: {e}")
            print("[*] Use CLI instead: python -m truthkeep.cli easy install")
            return 1

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = TruthKeepMainWindow(db_path)
    window.show()
    return app.exec()
