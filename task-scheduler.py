import sys
import json
import os
from PyQt5 import QtWidgets, QtGui, QtCore

class CalendarPopup(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calendar")
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
        layout0 = QtWidgets.QHBoxLayout()
        layout1 = QtWidgets.QVBoxLayout()
        layout2 = QtWidgets.QVBoxLayout()
        
        self.task_popup = QtWidgets.QDialog(self.calendar_popup)
        self.task_popup.setLayout(layout0)
        taskman = self.task_popup
        taskman.setWindowTitle("Task Manager")
        
        taskman.task_date = date
        taskman.task_area = QtWidgets.QWidget(taskman)
        taskman.button_area = QtWidgets.QWidget(taskman)
        
        taskman.task_list = QtWidgets.QListWidget(taskman.task_area)
        #taskman.task_input = QtWidgets.QLineEdit(taskman.button_area)
        #taskman.task_input.setPlaceholderText("Enter a new task")
        self.TASK_add_button = QtWidgets.QPushButton("Add Task", taskman.button_area)
        self.TASK_edit_button = QtWidgets.QPushButton("Edit Task", taskman.button_area)
        self.TASK_delete_button = QtWidgets.QPushButton("Delete Task", taskman.button_area)
        
        self.TASK_add_button.setShortcut("Return")
        self.TASK_add_button.clicked.connect(self.add_task_window)
        self.TASK_delete_button.clicked.connect(self.delete_task)
        
        self.update_task_list()
        
        layout0.addWidget(taskman.task_area)
        layout0.addWidget(taskman.button_area)
        
        layout1.addWidget(taskman.task_list)
        #layout1.addWidget(taskman.task_input)
        
        layout2.addWidget(self.TASK_delete_button)
        layout2.addWidget(self.TASK_edit_button)
        layout2.addWidget(self.TASK_add_button)
        
        taskman.task_area.setLayout(layout1)
        taskman.button_area.setLayout(layout2)

        taskman.exec_()
        taskman.setFocus()
    
    def need_reminder(self,state):
        addtask = self.task_popup.add_task_popup
        if state == QtCore.Qt.Checked:
            addtask.reminder_area.show()
        else:
            addtask.reminder_area.hide()
    
    def add_task_window(self):
        self.task_popup.add_task_popup = QtWidgets.QDialog(self.task_popup)
        addtask = self.task_popup.add_task_popup
        addtask.setWindowTitle("Add Task")
        
        addtask.time_area = QtWidgets.QWidget(addtask)
        addtask.reminder_area = QtWidgets.QWidget(addtask)
        addtask.button_area = QtWidgets.QWidget(addtask)
        
        layout0 = QtWidgets.QVBoxLayout(addtask)
        layout1 = QtWidgets.QVBoxLayout(addtask.time_area)
        layout2 = QtWidgets.QVBoxLayout(addtask.reminder_area)
        layout3 = QtWidgets.QVBoxLayout(addtask.button_area)
        
        task_label = QtWidgets.QLabel("Task Name: ",addtask.time_area)
        time_label = QtWidgets.QLabel("Start time of task: ",addtask.time_area)
        addtask.task_name = QtWidgets.QLineEdit(addtask.time_area)
        addtask.task_name.setPlaceholderText("Enter name of the task")
        addtask.reminder_required = QtWidgets.QCheckBox("Reminder",addtask)
        addtask.reminder_required.stateChanged.connect(self.need_reminder)
        addtask.reminder_label = QtWidgets.QLabel("Remind me x hours before: ",addtask)
        
        task_time = QtCore.QTime(0,0)
        task_reminder = QtCore.QTime(0,0)
        addtask.time_box = QtWidgets.QTimeEdit(task_time,addtask)
        addtask.time_box.setDisplayFormat("hh:mm AP")
        addtask.reminder_box = QtWidgets.QTimeEdit(task_time,addtask)
        addtask.reminder_box.setDisplayFormat("hh:mm")
        
        self.ADD_add_button = QtWidgets.QPushButton("Add Task", addtask.button_area)
        self.ADD_cancel_button = QtWidgets.QPushButton("Cancel", addtask.button_area)
        
        self.ADD_add_button.setShortcut("Return")
        self.ADD_add_button.clicked.connect(self.add_task)
        self.ADD_cancel_button.clicked.connect(addtask.close)
        
        layout0.addWidget(addtask.time_area,0)
        layout0.addWidget(addtask.reminder_area)
        layout0.addStretch(1)
        layout0.addWidget(addtask.button_area)
        layout1.addWidget(task_label)
        layout1.addWidget(addtask.task_name)
        layout1.addWidget(time_label)
        layout1.addWidget(addtask.time_box)
        layout1.addWidget(addtask.reminder_required)
        layout2.addWidget(addtask.reminder_label)
        layout2.addWidget(addtask.reminder_box)
        layout3.addWidget(self.ADD_add_button)
        layout3.addWidget(self.ADD_cancel_button)
        
        addtask.show()
        addtask.reminder_area.hide()
    
    # Add a task.
    def add_task(self):
        addtask = self.task_popup.add_task_popup
        d = self.task_popup.task_date
        t = addtask.task_name.text()
        # If no task name is given
        taskobj = [t,]
        if not t:
            w = QtWidgets.QMessageBox()
            w.setWindowTitle("Warning!")
            w.setText("Task name is empty!")
            w.setIcon(QtWidgets.QMessageBox.Information)
            w.exec_()
            return
        if d in self.tasks:
            # If task name exists already
            if t in self.tasks[d]:
                m = QtWidgets.QMessageBox()
                m.setWindowTitle("Warning!")
                m.setText("Task already exists!")
                m.setIcon(QtWidgets.QMessageBox.Information)
                m.exec_()
                return
            else:
                pass
    
    def JUNKadd_task(self):
        taskman = self.task_popup
        t = taskman.task_input.text()
        d = taskman.task_date
        if not t:
            w = QtWidgets.QMessageBox()
            w.setWindowTitle("Warning!")
            w.setText("Task name is empty!")
            w.setIcon(QtWidgets.QMessageBox.Information)
            w.exec_()
            return
        if d in self.tasks:
            if t in self.tasks[d]:
                m = QtWidgets.QMessageBox()
                m.setWindowTitle("Warning!")
                m.setText("Task already exists!")
                m.setIcon(QtWidgets.QMessageBox.Information)
                m.exec_()
                return
            else:
                self.tasks[d].append(t)
        else:
            self.tasks[d] = [t]
        taskman.task_input.clear()
        self.update_task_list()
        self.save_tasks()
    
    # Update list of tasks when modified
    def update_task_list(self):
        taskman = self.task_popup
        taskman.task_list.clear()
        d = taskman.task_date
        if self.tasks.get(d):
            for t in self.tasks[d]:
                taskman.task_list.addItem(t)
    
    # Delete the selected task
    def delete_task(self):
        taskman = self.task_popup
        if not taskman.task_list.selectedItems():
            return
        t = taskman.task_list.selectedItems()[0].text()
        m = QtWidgets.QMessageBox()
        m.setWindowTitle("Warning!")
        m.setIcon(QtWidgets.QMessageBox.Warning)
        m.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        m.setText("Are you sure you want to delete the task \'"+t+"\'?")
        response = m.exec()
        if response == QtWidgets.QMessageBox.Yes:
            self.tasks[taskman.task_date].remove(t)
            if not self.tasks[taskman.task_date]:
                del self.tasks[taskman.task_date]
            self.save_tasks()
            self.update_task_list()
            self.highlight_task_dates()
        else:
            return
    
    # Highlight dates with tasks on the calendar.
    def highlight_task_dates(self):
        d = self.calendar_popup.calendar.selectedDate()
        for date in self.tasks.keys():
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
