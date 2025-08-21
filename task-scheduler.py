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

"""
class EventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Close:
            print("Window closed!")
            #return True  # Block the event, optional
        return super().eventFilter(obj, event)
"""

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
        
        self.reminders = {}
        self.refresh_reminders()
        # { date: { taskname : [datetime, remyesno, reminderdt] } }
        
        self.rtimer = QtCore.QTimer(self.app)
        self.rtimer.timeout.connect(self.reminder_check)
        self.rtimer.start(1000)
        
        # Highlight format for dates with tasks
        self.task_format = QtGui.QTextCharFormat()
        self.task_format.setBackground(QtGui.QColor("#90EE90"))
        self.task_format.setFontWeight(75)  # Bold

        # Highlight existing tasks
        self.highlight_task_dates()

    def refresh_reminders(self):
        self.reminders.clear()
        for d,task in self.tasks.items(): # t = date, ts = [ { task1: [dt,r,rm], task2: [dt,r,rm],... ]
            for t,ts in task.items():
                if ts[1]:
                    if QtCore.QDateTime.fromString(ts[0]).secsTo(QtCore.QDateTime.currentDateTime()) < 0:
                        self.reminders[ts[2]]=t
    
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
    
    # Check time for reminder
    def reminder_check(self):
        current_time = QtCore.QDateTime.currentDateTime()
        for r,t in self.reminders.copy().items():
            rdt = QtCore.QDateTime.fromString(r)
            if rdt.secsTo(current_time) > 0:        
                tdt = QtCore.QDateTime.fromString(self.tasks[rdt.date()][t][0])        
                self.tray_icon.showMessage(
                    "Reminder!",
                    t+" at "+tdt.time().toString("hh:mm AP")+"!",
                    QtGui.QIcon.fromTheme("dialog-information"),
                    current_time.secsTo(tdt)*1000 # Display reminder till task time
                )
                del self.reminders[r]
    
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
        self.TASK_add_button = QtWidgets.QPushButton("Add Task", taskman.button_area)
        self.TASK_edit_button = QtWidgets.QPushButton("Edit Task", taskman.button_area)
        self.TASK_delete_button = QtWidgets.QPushButton("Delete Task", taskman.button_area)
        
        self.TASK_add_button.setShortcut("Return")
        self.TASK_add_button.clicked.connect(self.add_task_window)
        self.TASK_edit_button.clicked.connect(self.edit_task_window)
        self.TASK_delete_button.clicked.connect(self.delete_task)
        
        self.update_task_list()
        
        layout0.addWidget(taskman.task_area)
        layout0.addWidget(taskman.button_area)
        
        layout1.addWidget(taskman.task_list)
        
        layout2.addWidget(self.TASK_delete_button)
        layout2.addWidget(self.TASK_edit_button)
        layout2.addWidget(self.TASK_add_button)
        
        taskman.task_area.setLayout(layout1)
        taskman.button_area.setLayout(layout2)

        taskman.open()
        taskman.setFocus()
    
    def need_reminder(self,state):
        if hasattr(self.task_popup, "edit_task_popup"):
            taskwin = self.task_popup.edit_task_popup
        else:
            taskwin = self.task_popup.add_task_popup
        if state == QtCore.Qt.Checked:
            taskwin.reminder_area.show()
        else:
            taskwin.reminder_area.hide()
    
    def add_task_window(self):
        self.task_popup.add_task_popup = QtWidgets.QDialog(self.task_popup)
        addtask = self.task_popup.add_task_popup
        addtask.setWindowTitle("Add Task")
        #addtask.setAttribute(QtCore.Qt.WA_DeleteOnClose,True)
        
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
        
        addtask.time_box = QtWidgets.QTimeEdit(QtCore.QTime(0,0),addtask)
        addtask.time_box.setDisplayFormat("hh:mm AP")
        addtask.reminder_box = QtWidgets.QTimeEdit(QtCore.QTime(0,0),addtask)
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
        addtask.setFocus()
        addtask.reminder_area.hide()
    
    # Add a task.
    def add_task(self):
        addtask = self.task_popup.add_task_popup
        tname = addtask.task_name.text()
        d = self.task_popup.task_date
        t = addtask.time_box.time()
        task_dt = QtCore.QDateTime(d,t)
        
        savedate = [task_dt.toString(), addtask.reminder_required.isChecked()]
        if addtask.reminder_required.isChecked():
            r = addtask.reminder_box.time()
            reminder_dt = task_dt.addSecs(-1*QtCore.QTime(0,0,0).secsTo(r)) # reminder alarm
            savedate.append(reminder_dt.toString())
        
        # If no task name is given
        if not tname:
            w = QtWidgets.QMessageBox()
            w.setWindowTitle("Warning!")
            w.setText("Task name is empty!")
            w.setIcon(QtWidgets.QMessageBox.Information)
            w.exec_()
            return
        
        if d in self.tasks:
            # If task name exists already
            if tname in self.tasks[d].keys():
                m = QtWidgets.QMessageBox()
                m.setWindowTitle("Warning!")
                m.setText("Task already exists!")
                m.setIcon(QtWidgets.QMessageBox.Information)
                m.exec_()
                return
            else:
                self.tasks[d][tname]=savedate
                #.append(savedate)
        else:
            self.tasks[d] = { tname : savedate }
        self.update_task_list()
        self.refresh_reminders()
        self.highlight_task_dates()
        self.save_tasks()
        addtask.close()
    
    def edit_task_window(self):
        taskman = self.task_popup
        if not taskman.task_list.selectedItems():
            return
        
        self.task_popup.edit_task_popup = QtWidgets.QDialog(self.task_popup)
        edittask = self.task_popup.edit_task_popup
        #edittask.setWindowModality(QtCore.Qt.WindowModal)
        edittask.setWindowTitle("Edit Task")
        edittask.tname = taskman.task_list.selectedItems()[0].data(QtCore.Qt.UserRole+1)
        task = self.tasks[taskman.task_date][edittask.tname]
        dt = QtCore.QDateTime.fromString(task[0])
                
        edittask.time_area = QtWidgets.QWidget(edittask)
        edittask.reminder_area = QtWidgets.QWidget(edittask)
        edittask.button_area = QtWidgets.QWidget(edittask)
        
        layout0 = QtWidgets.QVBoxLayout(edittask)
        layout1 = QtWidgets.QVBoxLayout(edittask.time_area)
        layout2 = QtWidgets.QVBoxLayout(edittask.reminder_area)
        layout3 = QtWidgets.QVBoxLayout(edittask.button_area)
        
        task_label = QtWidgets.QLabel("Task Name: ",edittask.time_area)
        time_label = QtWidgets.QLabel("Start time of task: ",edittask.time_area)
        edittask.task_name = QtWidgets.QLineEdit(edittask.time_area)
        edittask.task_name.setText(edittask.tname)
        edittask.reminder_required = QtWidgets.QCheckBox("Reminder",edittask)
        edittask.reminder_required.stateChanged.connect(self.need_reminder)
        edittask.reminder_label = QtWidgets.QLabel("Remind me x hours before: ",edittask)
        
        edittask.time_box = QtWidgets.QTimeEdit(dt.time(),edittask)
        edittask.time_box.setDisplayFormat("hh:mm AP")
        edittask.reminder_box = QtWidgets.QTimeEdit(QtCore.QTime(0,0),edittask)
        edittask.reminder_box.setDisplayFormat("hh:mm")
        
        if task[1]:
            r = QtCore.QDateTime.fromString(task[2])
            rm = QtCore.QTime(0,0,0).addSecs(r.secsTo(dt))
            edittask.reminder_required.setCheckState(2)
            edittask.reminder_box.setTime(rm)
        else:
            edittask.reminder_area.hide()
        
        self.EDIT_save_button = QtWidgets.QPushButton("Save Changes", edittask.button_area)
        self.EDIT_cancel_button = QtWidgets.QPushButton("Cancel", edittask.button_area)
        
        self.EDIT_save_button.setShortcut("Return")
        self.EDIT_save_button.clicked.connect(self.modify_task)
        self.EDIT_cancel_button.clicked.connect(edittask.close)
        
        layout0.addWidget(edittask.time_area,0)
        layout0.addWidget(edittask.reminder_area)
        layout0.addStretch(1)
        layout0.addWidget(edittask.button_area)
        layout1.addWidget(task_label)
        layout1.addWidget(edittask.task_name)
        layout1.addWidget(time_label)
        layout1.addWidget(edittask.time_box)
        layout1.addWidget(edittask.reminder_required)
        layout2.addWidget(edittask.reminder_label)
        layout2.addWidget(edittask.reminder_box)
        layout3.addWidget(self.EDIT_save_button)
        layout3.addWidget(self.EDIT_cancel_button)
        
        edittask.open()
        edittask.setFocus()
    
    def modify_task(self):
        edittask = self.task_popup.edit_task_popup
        tname = edittask.task_name.text()
        
        d = self.task_popup.task_date
        t = edittask.time_box.time()
        task_dt = QtCore.QDateTime(d,t)
        
        savedate = [task_dt.toString(), edittask.reminder_required.isChecked()]
        if edittask.reminder_required.isChecked():
            r = edittask.reminder_box.time()
            reminder_dt = task_dt.addSecs(-1*QtCore.QTime(0,0,0).secsTo(r)) # Reminder alarm: Converting "x hours before" to proper datetime
            savedate.append(reminder_dt.toString())
        
        # If no task name is given
        if not tname:
            w = QtWidgets.QMessageBox()
            w.setWindowTitle("Warning!")
            w.setText("Task name is empty!")
            w.setIcon(QtWidgets.QMessageBox.Information)
            w.exec_()
            edittask.task_name.setText(edittask.tname)
            return
        
        # If task name is unchanged on edit
        if tname == edittask.tname:
            self.tasks[d][tname] = savedate
        # If task name was changed & new task name exists already
        elif tname in self.tasks[d].keys():
            m = QtWidgets.QMessageBox()
            m.setWindowTitle("Warning!")
            m.setText("That task name already exists!")
            m.setIcon(QtWidgets.QMessageBox.Information)
            m.exec_()
            edittask.task_name.setText(edittask.tname)
            return
        # If task name was changed without conflicts
        else:
            del self.tasks[d][edittask.tname]
            self.tasks[d][tname] = savedate
        
        self.update_task_list()
        self.refresh_reminders()
        self.highlight_task_dates()
        self.save_tasks()
        edittask.close()
    
    def focus_popups(self):
        pass
    
    # Update list of tasks when modified
    def update_task_list(self):
        taskman = self.task_popup
        taskman.task_list.clear()
        d = taskman.task_date
        if self.tasks.get(d): # { (taskname, [datetime, remreq, remtime]), ... }
            for tname, task in sorted(self.tasks[d].items(),key=lambda item:item[1][0]): # Task list display sorted by date & time
                # Using separate "data" and "text" so that display shows time as well, while allowing modification/deletion with task name
                dt = QtCore.QDateTime.fromString(task[0])
                i = QtWidgets.QListWidgetItem()
                i.setText(tname+" ("+dt.time().toString("h:mm AP")+")")
                i.setData(QtCore.Qt.UserRole+1, tname)
                taskman.task_list.addItem(i)
    
    # Delete the selected task
    def delete_task(self):
        taskman = self.task_popup
        if not taskman.task_list.selectedItems():
            return
        t = taskman.task_list.selectedItems()[0].data(QtCore.Qt.UserRole+1)
        m = QtWidgets.QMessageBox()
        m.setWindowTitle("Warning!")
        m.setIcon(QtWidgets.QMessageBox.Warning)
        m.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        m.setText("Are you sure you want to delete the task \'"+t+"\'?")
        response = m.exec()
        if response == QtWidgets.QMessageBox.Yes:
            del self.tasks[taskman.task_date][t]
            if not self.tasks[taskman.task_date]:
                del self.tasks[taskman.task_date]
                self.calendar_popup.calendar.setDateTextFormat(taskman.task_date,QtGui.QTextCharFormat()) # Reset highlighting when last task is removed
            self.save_tasks()
            self.update_task_list()
            self.refresh_reminders()
            self.highlight_task_dates()
    
    # Highlight dates with tasks on the calendar.
    def highlight_task_dates(self):
        for date in self.tasks.keys():
            self.calendar_popup.calendar.setDateTextFormat(date, self.task_format)
    
    # Function for when user left clicks tray icon
    def handle_tray_click(self, reason):
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
