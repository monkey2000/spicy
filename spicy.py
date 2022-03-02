#!/usr/bin/env python3
import sys
from collections import namedtuple
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMenu, QAction, QMessageBox, QGridLayout, QGroupBox, QTableView, QWidget, \
    QVBoxLayout, QComboBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, \
    QHeaderView, QApplication


class Component(namedtuple('Component', ['type', 'nid', 'u', 'v', 'val', 'ref_u', 'ref_v', 'ref_comp'])):
    def __eq__(self, other):
        return (self.type + self.nid) == (other.type + other.nid)


class ComponentRegistry(QObject):
    updated = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        self.comps = []
        self.name_to_comps = {}

    def has_component(self, name):
        return name in self.name_to_comps.keys()

    def add_component(self, comp: Component):
        name = comp.type + str(comp.nid)
        if self.has_component(name):
            return False

        self.comps.append(comp)
        self.name_to_comps[name] = comp
        self.updated.emit()
        return True

    def del_component(self, comp: Component):
        name = comp.type + comp.nid
        if not self.has_component(name):
            return False

        self.comps.remove(comp)
        del self.name_to_comps[name]
        self.updated.emit()
        return True


reg = ComponentRegistry()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # Window
        self.resize(1024, 768)
        self.setWindowTitle("Spicy 仿真器")
        self.setCentralWidget(QWidget())

        # File Menu
        self.menu_file = QMenu("文件")
        self.menu_file_open = QAction("打开", self.menu_file)
        self.menu_file_save = QAction("保存", self.menu_file)
        self.menu_exit = QAction("退出", self.menu_file)
        self.menu_file.addActions([self.menu_file_open, self.menu_file_save, self.menu_exit])
        self.menuBar().addMenu(self.menu_file)
        self.menu_exit.triggered.connect(lambda: QApplication.instance().exit(0))

        # About Menu
        self.menu_help = QMenu("帮助")
        self.menu_help_about = QAction("关于", self.menu_help)
        self.menu_help.addActions([self.menu_help_about])
        self.menuBar().addMenu(self.menu_help)
        self.menu_help_about.triggered.connect(self.about)

        # UI
        # - Netlist View
        self.netlist_group = QGroupBox("网表")
        layout = QGridLayout()
        self.netlist_view = QTableWidget()
        self.netlist_view.setColumnCount(5)
        self.netlist_view.setHorizontalHeaderLabels(["元件名称", "起始节点", "终止节点", "参数", "控制"])
        self.netlist_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.netlist_view.horizontalHeader().setVisible(True)
        self.netlist_view.verticalHeader().setVisible(True)
        self.netlist_view.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        layout.addWidget(self.netlist_view, 1, 1, 1, 1)
        self.netlist_group.setLayout(layout)
        reg.updated.connect(self.update_netlist)

        # - Edit View
        self.edit_group = QGroupBox("编辑")
        layout = QHBoxLayout()
        layout_labels = QVBoxLayout()
        layout_inputs = QVBoxLayout()
        layout_actions = QVBoxLayout()
        layout.addLayout(layout_labels)
        layout.addLayout(layout_inputs)
        layout.addLayout(layout_actions)
        self.edit_type = QComboBox()
        self.edit_type.addItems(["R", "VS", "CS", "VCVS", "CCVS", "VCCS", "CCCS", "C", "L"])
        self.edit_type.currentIndexChanged.connect(self.type_changed)
        self.edit_nid = QSpinBox()
        self.edit_from = QSpinBox()
        self.edit_to = QSpinBox()
        self.edit_value = QDoubleSpinBox()
        self.edit_ref_from = QSpinBox()
        self.edit_ref_to = QSpinBox()
        self.edit_ref_comp = QComboBox()
        self.edit_add = QPushButton("添加")
        layout_labels.addWidget(QLabel("元件类型"))
        layout_inputs.addWidget(self.edit_type)
        layout_labels.addWidget(QLabel("元件编号"))
        layout_inputs.addWidget(self.edit_nid)
        layout_labels.addWidget(QLabel("元件起始节点"))
        layout_inputs.addWidget(self.edit_from)
        layout_labels.addWidget(QLabel("元件终止节点"))
        layout_inputs.addWidget(self.edit_to)
        layout_labels.addWidget(QLabel("元件参数"))
        layout_inputs.addWidget(self.edit_value)
        layout_labels.addWidget(QLabel("参考起始节点"))
        layout_inputs.addWidget(self.edit_ref_from)
        layout_labels.addWidget(QLabel("参考终止节点"))
        layout_inputs.addWidget(self.edit_ref_to)
        layout_labels.addWidget(QLabel("参考元件"))
        layout_inputs.addWidget(self.edit_ref_comp)
        layout_actions.addWidget(self.edit_add)
        self.edit_group.setLayout(layout)
        self.type_changed()
        self.edit_add.clicked.connect(self.add_component)
        reg.updated.connect(self.update_ref_comp)

        # - Control View
        self.control_group = QGroupBox("控制")
        layout = QVBoxLayout()
        self.control_start = QPushButton("启动仿真")
        self.control_stop = QPushButton("停止仿真")
        layout.addWidget(self.control_start)
        layout.addWidget(self.control_stop)
        self.control_group.setLayout(layout)

        self.grid = QGridLayout()
        self.grid.addWidget(self.netlist_group, 1, 1, 2, 2)
        self.grid.addWidget(self.edit_group, 3, 1, 1, 1)
        self.grid.addWidget(self.control_group, 3, 2, 1, 1)
        self.centralWidget().setLayout(self.grid)

    def about(self):
        QMessageBox.about(self, "关于 Spicy", "Spicy 是一个简单的瞬态电路仿真器")

    def type_changed(self):
        comp_type = self.edit_type.currentText()
        if comp_type in ["R", "VS", "CS", "C", "L"]:
            self.edit_ref_from.setDisabled(True)
            self.edit_ref_to.setDisabled(True)
            self.edit_ref_comp.setDisabled(True)
        elif comp_type in ["VCVS", "VCCS"]:
            self.edit_ref_from.setDisabled(False)
            self.edit_ref_to.setDisabled(False)
            self.edit_ref_comp.setDisabled(True)
        elif comp_type in ["CCVS", "CCCS"]:
            self.edit_ref_from.setDisabled(True)
            self.edit_ref_to.setDisabled(True)
            self.edit_ref_comp.setDisabled(False)
        else:
            print("ERROR: Unrecognized component type [%s]" % comp_type, file=sys.stderr)

    def update_netlist(self):
        self.netlist_view.setRowCount(0)
        self.netlist_view.setRowCount(len(reg.comps))
        for i, comp in enumerate(reg.comps):
            name = comp.type + str(comp.nid)
            self.netlist_view.setItem(i, 0, QTableWidgetItem(name))
            self.netlist_view.setItem(i, 1, QTableWidgetItem(str(comp.u)))
            self.netlist_view.setItem(i, 2, QTableWidgetItem(str(comp.v)))

            if comp.type in ["VCVS", "VCCS"]:
                self.netlist_view.setItem(i, 3, QTableWidgetItem('%f %d %d' % (comp.val, comp.ref_u, comp.ref_v)))
            elif comp.type in ["CCVS", "CCCS"]:
                self.netlist_view.setItem(i, 3, QTableWidgetItem('%f %s' % (comp.val, comp.ref_comp)))
            else:
                self.netlist_view.setItem(i, 3, QTableWidgetItem(str(comp.val)))

    def add_component(self):
        _type = self.edit_type.currentText()
        nid = self.edit_nid.value()
        u = self.edit_from.value()
        v = self.edit_to.value()
        val = self.edit_value.value()
        ref_u = self.edit_ref_from.value()
        ref_v = self.edit_ref_to.value()
        ref_comp = self.edit_ref_comp.currentText()

        name = _type + str(nid)
        comp = Component(_type, nid, u, v, val, ref_u, ref_v, ref_comp)

        if reg.has_component(name):
            QMessageBox.critical(self, "错误", "元件 %s 重名" % name)
            return

        reg.add_component(comp)

    def update_ref_comp(self):
        names = reg.name_to_comps.keys()
        self.edit_ref_comp.clear()
        self.edit_ref_comp.addItems(names)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec()


if __name__ == '__main__':
    main()
