import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore

class CalendarPopup(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calendar = QtWidgets.QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.show()
        self.calendar.setFocusPolicy(QtCore.Qt.StrongFocus)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.calendar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setFixedSize(300, 300)
        self.task_window = None

class SchedulerApp:
    def __init__(self):
        # Create app, keep it running in bg even if window closed
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Calendar dialog
        self.calendar_popup = CalendarPopup()
        self.calendar_popup.calendar.selectionChanged.connect(self.highlight_task_dates)
        
        # Create system tray icon
        self.tray_icon = QtWidgets.QSystemTrayIcon()
        self.tray_icon.setIcon(QtGui.QIcon.fromTheme("dialog-information"))
        self.tray_icon.setToolTip("Task Scheduler")
        self.tray_icon.show()
        
        # Right-click context menu
        self.tray_menu = QtWidgets.QMenu()
        self.quit_action = self.tray_menu.addAction("Quit")
        self.tray_icon.setContextMenu(self.tray_menu)
                
        # Connect actions to functions
        self.tray_icon.activated.connect(self.handle_tray_click)
        self.quit_action.triggered.connect(self.quit_app)
        self.calendar_popup.calendar.clicked.connect(self.task_manager) #add_task)

        # Notification when app is launched
        self.tray_icon.showMessage(
            "Task Scheduler",
            "Scheduler is now running in the background",
            QtGui.QIcon.fromTheme("dialog-information"),
            3000
        )

        # Initialize task storage
        self.tasks = self.load_tasks()
        
        # Highlight format for dates with tasks
        self.task_format = QtGui.QTextCharFormat()
        self.task_format.setBackground(QtGui.QColor("#90EE90"))
        self.task_format.setFontWeight(75)  # Bold
        
        # Highlight format for current date if it has a task
        self.ctask_format = QtGui.QTextCharFormat()
        self.ctask_format.setBackground(QtGui.QColor("#06402B"))
        self.ctask_format.setFontWeight(75)  # Bold

        # Highlight existing tasks
        self.highlight_task_dates()

    # Load tasks from JSON file
    def load_tasks(self):
        try:
            with open("tasks.json", "r") as file:
                data = json.load(file)
                return {
                    QtCore.QDate.fromString(date, "yyyy-MM-dd"): tasks
                    for date, tasks in data.items()
                }
        except FileNotFoundError:
            return {}
    
    # Save tasks to JSON file.
    def save_tasks(self):
        data = {date.toString("yyyy-MM-dd"): tasks for date, tasks in self.tasks.items()}
        with open("tasks.json", "w") as file:
            json.dump(data, file, indent=4)
    
    # Task manager window
    def task_manager(self,date):
        self.task_date = date

        layout0 = QtWidgets.QHBoxLayout()
        layout1 = QtWidgets.QVBoxLayout()
        layout2 = QtWidgets.QVBoxLayout()
        
        self.task_popup = QtWidgets.QDialog(self.calendar_popup)
        self.task_popup.setLayout(layout0)
        
        task_list_entries = QtWidgets.QWidget(self.task_popup)
        task_list_buttons = QtWidgets.QWidget(self.task_popup)
        
        self.task_list = QtWidgets.QListWidget(task_list_entries)
        self.task_input = QtWidgets.QLineEdit(task_list_entries)
        self.task_input.setPlaceholderText("Enter a new task")
        self.add_button = QtWidgets.QPushButton("Add Task", task_list_buttons)
        self.edit_button = QtWidgets.QPushButton("Edit Task", task_list_buttons)
        self.delete_button = QtWidgets.QPushButton("Delete Task", task_list_buttons)
        self.add_button.setShortcut("Enter")
        
        self.add_button.clicked.connect(self.add_task)
        self.delete_button.clicked.connect(self.delete_task)
        
        self.update_task_list()
        
        layout0.addWidget(task_list_entries)
        layout0.addWidget(task_list_buttons)
        
        layout1.addWidget(self.task_list)
        layout1.addWidget(self.task_input)
        
        layout2.addWidget(self.delete_button)
        layout2.addWidget(self.edit_button)
        layout2.addWidget(self.add_button)
        
        task_list_entries.setLayout(layout1)
        task_list_buttons.setLayout(layout2)

        #self.task_popup.show()
        self.task_popup.exec_()
        self.task_popup.setFocus()
    
    # Add a task.
    def add_task(self):
        t = self.task_input.text()
        d = self.task_date
        if d in self.tasks:
            if t in self.tasks[d]:
                m = QtWidgets.QMessageBox()
                m.setWindowTitle("Warning!")
                m.setIcon(QtWidgets.QMessageBox.Information)
                m.setText("Task already exists!")
                m.exec()
                return
            else:
                self.tasks[d].append(t)
        else:
            self.tasks[d] = [t]
        self.task_input.clear()
        self.update_task_list()
        self.save_tasks()
    
    # Update list of tasks when modified
    def update_task_list(self):
        self.task_list.clear()
        d = self.task_date
        if self.tasks.get(d):
            for t in self.tasks[d]:
                self.task_list.addItem(t)
    
    # Delete the selected task
    def delete_task(self):
        if not self.task_list.selectedItems():
            return
        t = self.task_list.selectedItems()[0].text()
        m = QtWidgets.QMessageBox()
        m.setWindowTitle("Warning!")
        m.setIcon(QtWidgets.QMessageBox.Warning)
        m.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        m.setText("Are you sure you want to delete the task \'"+t+"\'?")
        response = m.exec()
        if response == QtWidgets.QMessageBox.Yes:
            self.tasks[self.task_date].remove(t)
            self.save_tasks()
            self.update_task_list()
        else:
            return
    
    # Highlight dates with tasks on the calendar.
    def highlight_task_dates(self):
        d = self.calendar_popup.calendar.selectedDate()
        for date in self.tasks.keys():
            if date == d:
                self.calendar_popup.calendar.setDateTextFormat(date, self.ctask_format)
            else:
                self.calendar_popup.calendar.setDateTextFormat(date, self.task_format)
    
    # Function for when user left clicks tray icon
    def handle_tray_click(self, reason):
        print(self.tray_menu)
        if reason == QtWidgets.QSystemTrayIcon.Trigger : # i.e. if left-clicked
            if self.calendar_popup.isVisible():
                self.calendar_popup.hide()
            else:
                self.calendar_popup.show()
                self.calendar_popup.raise_()
                self.highlight_task_dates()

    def quit_app(self):
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    app = SchedulerApp()
    app.run()
