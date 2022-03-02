#!/usr/bin/env python3
import sys
from collections import namedtuple
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import QMenu, QAction, QMessageBox, QGridLayout, QGroupBox, QTableView, QWidget, \
    QVBoxLayout, QComboBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, \
    QHeaderView, QApplication
import os
import time
import numpy as np
import matplotlib
import matplotlib.pylab as mp
from matplotlib import pyplot as plt
import matplotlib.animation as ma
import solver_12_11
matplotlib.use('Qt5Agg')

class Component(namedtuple('Component', ['type', 'nid', 'u', 'v', 'val', 'factor', 'ref_u', 'ref_v', 'ref_comp'])):
    def __eq__(self, other):
        return (self.type + self.nid) == (other.type + other.nid)

class Displaynode(namedtuple('Displaynode', ['from_node', 'to_node'])):
    pass

class ComponentRegistry(QObject):
    updated = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        self.comps = []
        self.name_to_comps = {}
        self.display_node = []

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

    def add_display_node(self, displaynode: Displaynode):
        self.display_node.append(displaynode)
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
        self.menu_file_save.triggered.connect(self.save)

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
        self.netlist_view.setHorizontalHeaderLabels(["元件名称", "起始节点", "终止节点", "参数",  "特征系数"])
        self.netlist_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.netlist_view.horizontalHeader().setVisible(True)
        self.netlist_view.verticalHeader().setVisible(True)
        self.netlist_view.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        layout.addWidget(self.netlist_view, 1, 1, 1, 1)
        self.netlist_group.setLayout(layout)
        reg.updated.connect(self.update_netlist)

        # - Display nodes view
        self.displayshow_group = QGroupBox("示波器展示节点")
        layout = QGridLayout()
        self.displayshow_view = QTableWidget()
        self.displayshow_view.setColumnCount(2)
        self.displayshow_view.setHorizontalHeaderLabels(["正极节点", "负极节点"])
        self.displayshow_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.displayshow_view.horizontalHeader().setVisible(True)
        self.displayshow_view.verticalHeader().setVisible(True)
        self.displayshow_view.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        layout.addWidget(self.displayshow_view, 1, 1, 1, 1)
        self.displayshow_group.setLayout(layout)
        reg.updated.connect(self.update_displaynode)



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
        self.edit_type.addItems(["R", "VS", "CS", "VCVS", "CCVS", "VCCS", "CCCS", "C", "L", "AC"])
        self.edit_type.currentIndexChanged.connect(self.type_changed)
        self.edit_nid = QSpinBox()
        self.edit_from = QSpinBox()
        self.edit_to = QSpinBox()
        self.edit_value = QDoubleSpinBox()
        self.edit_value.setMaximum(9999999)
        self.edit_value.setMinimum(-9999999)
        self.edit_value.setDecimals(6)
        self.edit_ref_from = QSpinBox()
        self.edit_factor = QDoubleSpinBox()
        self.edit_factor.setMaximum(9999999)
        self.edit_factor.setMinimum(-9999999)
        self.edit_factor.setDecimals(6)
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
        layout_labels.addWidget(QLabel("元件特征系数"))
        layout_inputs.addWidget(self.edit_factor)
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
        self.control_start.clicked.connect(self.start)
        self.control_stop.clicked.connect(self.stop)

        # - Display View
        self.display_group = QGroupBox("示波器参数")
        layout = QHBoxLayout()
        layout_labels = QVBoxLayout()
        layout_inputs = QVBoxLayout()
        layout_actions = QVBoxLayout()
        layout.addLayout(layout_labels)
        layout.addLayout(layout_inputs)
        layout.addLayout(layout_actions)
        self.display_from = QSpinBox()
        self.display_to = QSpinBox()
        self.display_add = QPushButton("添加")
        layout_labels.addWidget(QLabel("正极节点数"))
        layout_inputs.addWidget(self.display_from)
        layout_labels.addWidget(QLabel("负极节点数"))
        layout_inputs.addWidget(self.display_to)
        layout_actions.addWidget(self.display_add)
        self.display_group.setLayout(layout)
        self.display_add.clicked.connect(self.add_display_node)

        self.grid = QGridLayout()
        self.grid.addWidget(self.netlist_group, 1, 1, 2, 5)
        self.grid.addWidget(self.displayshow_group, 1, 6, 2, 1)
        self.grid.addWidget(self.edit_group, 3, 1, 1, 3)
        self.grid.addWidget(self.display_group, 3, 4, 1, 2)
        self.grid.addWidget(self.control_group, 3, 6, 1, 1)
        self.centralWidget().setLayout(self.grid)

        # Status
        self.running = False

    def about(self):
        QMessageBox.about(self, "关于 Spicy", "Spicy 是一个简单的瞬态电路仿真器")

    def type_changed(self):
        comp_type = self.edit_type.currentText()
        if comp_type in ["R", "VS", "CS"]:
            self.edit_ref_from.setDisabled(True)
            self.edit_ref_to.setDisabled(True)
            self.edit_ref_comp.setDisabled(True)
            self.edit_factor.setDisabled(True)
        elif comp_type in ["C", "L"]:
            self.edit_ref_from.setDisabled(True)
            self.edit_ref_to.setDisabled(True)
            self.edit_ref_comp.setDisabled(True)
            self.edit_factor.setDisabled(False)
        elif comp_type in ["VCVS", "VCCS"]:
            self.edit_ref_from.setDisabled(False)
            self.edit_ref_to.setDisabled(False)
            self.edit_ref_comp.setDisabled(True)
            self.edit_factor.setDisabled(True)
        elif comp_type in ["CCVS", "CCCS"]:
            self.edit_ref_from.setDisabled(True)
            self.edit_ref_to.setDisabled(True)
            self.edit_ref_comp.setDisabled(False)
            self.edit_factor.setDisabled(True)
        elif comp_type in ["AC"]:
            self.edit_ref_from.setDisabled(True)
            self.edit_ref_to.setDisabled(True)
            self.edit_ref_comp.setDisabled(True)
            self.edit_factor.setDisabled(False)
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
            elif comp.type in ["C", "L"]:
                self.netlist_view.setItem(i, 3, QTableWidgetItem('%f' % comp.val))
                self.netlist_view.setItem(i, 4, QTableWidgetItem('%f' % comp.factor))
            elif comp.type in ["AC"]:
                self.netlist_view.setItem(i, 3, QTableWidgetItem('%f' % comp.val))
                self.netlist_view.setItem(i, 4, QTableWidgetItem('%f' % comp.factor))
            else:
                self.netlist_view.setItem(i, 3, QTableWidgetItem(str(comp.val)))

    def update_displaynode(self):
        self.displayshow_view.setRowCount(0)
        self.displayshow_view.setRowCount(len(reg.display_node))
        for i, displaynode in enumerate(reg.display_node):
            self.displayshow_view.setItem(i, 0, QTableWidgetItem(str(displaynode.from_node)))
            self.displayshow_view.setItem(i, 1, QTableWidgetItem(str(displaynode.to_node)))

    def save(self):
        if len(reg.display_node) != 0:
            with open('input.txt', 'w') as f:
                for i in range(0, len(reg.comps), 1):
                    for j in range(0, 5, 1):
                        if self.netlist_view.item(i, j):
                            f.write(self.netlist_view.item(i, j).text())
                            f.write(' ')
                    f.write('\n')
            f.close()
        else:
            QMessageBox.critical(self, "错误", "请输入示波器检测点")

    def start(self):
        # 这里加入求逆和b的内容
        solver_12_11.file_input('input.txt')
        solver_12_11.solve()
        t = 0
        delta_t = 1e-4
        tt = []
        seq_list = [[] for i in range(0, len(reg.display_node), 1)]
        plt.figure(figsize=(6, 4))
        legends = []
        for disp in reg.display_node:
            plt.plot([], [])
            legends.append('node %d to %d' % (disp.from_node, disp.to_node))
        plt.legend(legends)
        plt.pause(0.001)
        tick = 0
        self.running = True
        while self.running:
            x = solver_12_11.reg.inv_A.dot(solver_12_11.reg.b)
            tt.append(t)
            for i, disp in enumerate(reg.display_node):
                seq_list[i].append(x[disp.from_node] - x[disp.to_node])
            if tick % 1000 == 0:
                plt.clf()
                for i, disp in enumerate(reg.display_node):
                    plt.plot(tt, seq_list[i])
                plt.title('time = %f' % t)
                plt.legend(legends)
                plt.pause(0.001)
                print(tick)
            for comp in solver_12_11.reg.comps:
                name = comp.type + str(comp.nid)
                if comp.type == 'C':
                    comp.val += -x[solver_12_11.reg.current_note[name]] / comp.factor * delta_t
                    solver_12_11.reg.b[solver_12_11.reg.dynamic_place[name]] = comp.val
                elif comp.type == 'L':
                    comp.val += (x[comp.v] - x[comp.u]) / comp.factor * delta_t
                    solver_12_11.reg.b[solver_12_11.reg.dynamic_place[name]] = comp.val
                elif comp.type == 'AC':
                    solver_12_11.reg.b[solver_12_11.reg.dynamic_place[name]] = np.cos(comp.factor * t) * comp.val
            t += delta_t
            tick += 1
        plt.show()

    def stop(self):
        self.running = False

    def add_display_node(self):
        from_node = self.display_from.value()
        to_node = self.display_to.value()
        displaynode = Displaynode(from_node, to_node)
        reg.add_display_node(displaynode)

    def add_component(self):
        _type = self.edit_type.currentText()
        nid = self.edit_nid.value()
        u = self.edit_from.value()
        v = self.edit_to.value()
        val = self.edit_value.value()
        factor = self.edit_factor.value()
        ref_u = self.edit_ref_from.value()
        ref_v = self.edit_ref_to.value()
        ref_comp = self.edit_ref_comp.currentText()

        name = _type + str(nid)
        comp = Component(_type, nid, u, v, val, factor, ref_u, ref_v, ref_comp)

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
