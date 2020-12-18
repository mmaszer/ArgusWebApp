from __future__ import absolute_import

from django.db import models


import os.path
import random
import shutil
import string
import subprocess
import tempfile
import Pmw
import cv2
import numpy as np
import pkg_resources
import psutil
import six.moves.cPickle
# import six.moves.tkinter_messagebox
from tkinter import messagebox
import six.moves.tkinter_tkfiledialog as tkFileDialog
from moviepy.editor import *
from six.moves import map
from six.moves import range
from six.moves.tkinter import *
import six.moves.tkinter_ttk as ttk

# Create your models here.
class GUI(object):
    """Base class for all Argus GUI objects.
    Methods:
        - __init __ : makes a Tkinter window called root for subclass to populate, also makes list to keep track of temporary directories
        - about : bring up a Tkinter window that displays the license and authorship information of this Python package
        - quit_all : kills all subprocesses and this process, destroys all temporary directories, and obliterates the Tkinter window
        - kill_proc_tree : cross platform way to ensure death of all child processes with psutil
        - go : takes a cmd from a subclass and executes in a way such that the output is either piped to the console (debug) or routed nowhere (release)
        - set_in_file_name : used by subclasses to set filenames for readables
        - set_out_file_name : used by subclasses to set filenames for writables

    """

    def __init__(self):
        self.root = Tk()
        self.root.resizable(width=FALSE, height=FALSE)
        self.root.protocol('WM_DELETE_WINDOW', self.quit_all)

        self.tmps = list()
        self.pids = list()

        self.root.wm_title("Argus")

    @staticmethod
    def about():
        lic = Tk()
        scrollbar = Scrollbar(lic)
        scrollbar.pack(side=RIGHT, fill=Y, padx=10, pady=10)
        log = Text(lic, yscrollcommand=scrollbar.set, bg="black", fg="green", width=100)
        scrollbar.config(command=log.yview)
        log.pack()

        lic.resizable(width=FALSE, height=FALSE)
        lic.wm_title('License')

        fo = open(os.path.join(RESOURCE_PATH, 'LICENSE.txt'))
        line = fo.readline()
        while line != '':
            log.insert(END, line)
            line = fo.readline()

    def quit_all(self):
        # Destroy the GUI and get out of dodge
        self.root.quit()
        self.root.destroy()
        self.kill_pids()

        for tmp in self.tmps:
            # Delete temporary directory in use if it still exists
            if os.path.isdir(tmp):
                shutil.rmtree(tmp)
        # me = os.getpid()
        # self.kill_proc_tree(me)

    def kill_proc_tree(self, pid, including_parent=True):
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        # psutil.wait_procs(children, timeout=5)
        if including_parent:
            parent.kill()
            parent.wait(5)

    def kill_pids(self):
        for pid in self.pids:
            try:
                self.kill_proc_tree(pid)
            except:
                pass

    def go(self, cmd, wlog=False, mode='DEBUG'):
        cmd = [str(wlog), ''] + cmd

        rcmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-log')]

        rcmd = rcmd + cmd

        startupinfo = None
        if sys.platform == "win32" or sys.platform == "win64":  # Make it so subprocess brings up no console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        print(type(rcmd), rcmd)
        print(type(subprocess.PIPE))
        print(type(startupinfo))

        proc = subprocess.Popen(rcmd, stdout=subprocess.PIPE, shell=False, startupinfo=startupinfo)
        self.pids.append(proc.pid)

    def set_in_filename(self, var, filetypes=None):
        # linux needs another window
        if 'linux' in sys.platform:
            root = Tk()
            root.withdraw()
        filename = tkFileDialog.askopenfilename()
        var.set(filename)

    def set_out_filename(self, var, filetypes=None):
        if 'linux' in sys.platform:
            root = Tk()
            root.withdraw()
        filename = tkFileDialog.asksaveasfilename()
        var.set(filename)

class WandGUI(GUI):
    def __init__(self):
        super(WandGUI, self).__init__()

        tooltips = Pmw.Balloon(self.root)

        group = LabelFrame(self.root, text="Options", padx=5, pady=5, fg='#56A0D3')

        self.intModeDict = {
            "Optimize none": '0',
            "Optimize focal length": '1',
            "Optimize focal length and principal point": '2'
        }

        self.disModeDict = {
            "Optimize none": '0',
            "Optimize r2": '1',
            "Optimize r2, r4": '2',
            "Optimize all distortion coefficients": '3'
        }
        
        # maybe don't need this?
        self.refModeDict = {
            "Axis points": '0',
            "Gravity": '1',
            "Plane": '2'
        }

        self.ppts = StringVar(self.root)
        self.uppts = StringVar(self.root)
        self.cams = StringVar(self.root)
        self.scale = StringVar(self.root)
        self.intrinsic_fixes = StringVar(self.root)
        self.distortion_fixes = StringVar(self.root)
        self.display = StringVar(self.root)
        self.ref = StringVar(self.root)
        self.tag = StringVar(self.root)
        self.report_on_outliers = StringVar(self.root)
        self.should_log = StringVar(self.root)
        self.output_camera_profiles = StringVar(self.root)
        self.choose = StringVar(self.root)
        self.reference_type = StringVar(self.root)
        self.freq = StringVar(self.root)

        self.intrinsic_fixes.set("Optimize none")
        self.distortion_fixes.set("Optimize none")
        self.display.set('1')
        self.report_on_outliers.set('1')
        self.scale.set('1.0')
        self.should_log.set('0')
        self.output_camera_profiles.set('0')
        self.choose.set('1')
        self.reference_type.set("Axis points")
        self.freq.set('100')

        Label(self.root, text="Argus-Wand", font=("Helvetica", 40), fg='#56A0D3').grid(row=0, column=0, padx=20,
                                                                                       pady=20, columnspan=2)

        about_button = Button(self.root, text="About", command=self.about, padx=15, pady=15)
        about_button.grid(row=0, column=1, sticky=E, padx=5, pady=5)

        find_in_file = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.cams), padx=10, pady=10,
                            width=10, height=1)
        find_in_file.grid(row=1, column=0, padx=190, sticky=W)
        clear_b = Button(self.root, text="Clear", command=lambda: self.clear_var(self.cams), padx=10, pady=10, width=10,
                         height=1)
        clear_b.grid(row=1, column=0, padx=60, sticky=E)
        tooltips.bind(find_in_file, 'Open a CSV file with camera intrinsic and extrinsics')
        Label(self.root, text="Input cameras:").grid(row=1, column=0, padx=35, sticky=W)

        in_file_entry = Entry(self.root, textvariable=self.cams, width=20)
        in_file_entry.grid(row=2, column=0, padx=10, pady=10, sticky=EW)
        tooltips.bind(in_file_entry, 'Path to CSV file with intrinsic and extrinsic estimates')

        find_in_file = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.ppts), padx=10, pady=10,
                            width=10, height=1)
        find_in_file.grid(row=3, column=0, padx=190, sticky=W)
        clear_b = Button(self.root, text="Clear", command=lambda: self.clear_var(self.ppts), padx=10, pady=10, width=10,
                         height=1)
        clear_b.grid(row=3, column=0, padx=60, sticky=E)
        tooltips.bind(find_in_file, 'Open a CSV file with paired pixel coordinates')

        Label(self.root, text="Input paired points:").grid(row=3, column=0, padx=35, sticky=W)

        in_file_entry = Entry(self.root, textvariable=self.ppts, width=20)
        in_file_entry.grid(row=4, column=0, padx=10, pady=10, sticky=EW)
        tooltips.bind(in_file_entry, 'Path to paired points CSV file')

        find_in_file = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.uppts), padx=10, pady=10,
                            width=10, height=1)
        find_in_file.grid(row=5, column=0, padx=190, sticky=W)
        clear_b = Button(self.root, text="Clear", command=lambda: self.clear_var(self.uppts), padx=10, pady=10, width=10,
                         height=1)
        clear_b.grid(row=5, column=0, padx=60, sticky=E)
        tooltips.bind(find_in_file, 'Open a CSV file with unpaired pixel coordinates')

        Label(self.root, text="Input unpaired points:").grid(row=5, column=0, padx=35, sticky=W)

        in_file_entry = Entry(self.root, textvariable=self.uppts, width=20)
        in_file_entry.grid(row=6, column=0, padx=10, pady=10, sticky=EW)
        tooltips.bind(in_file_entry, 'Path to unpaired points CSV file')

        find_in_file = Button(self.root, text="Open", command=lambda: self.set_in_filename(self.ref), padx=10, pady=10,
                            width=10, height=1)
        find_in_file.grid(row=5, column=1, padx=190, sticky=W)
        clear_b = Button(self.root, text="Clear", command=lambda: self.clear_var(self.ref), padx=10, pady=10, width=10,
                         height=1)
        clear_b.grid(row=5, column=1, padx=60, sticky=E)
        tooltips.bind(find_in_file, 'Open a CSV file with axes pixel coordinates')

        Label(self.root, text="Input reference points:").grid(row=5, column=1, padx=35, sticky=W)

        in_file_entry = Entry(self.root, textvariable=self.ref, width=20)
        in_file_entry.grid(row=6, column=1, padx=10, pady=10, sticky=EW)
        tooltips.bind(in_file_entry, 'Path to reference points text file')

        # mini func to control editable state of freq entry based on ref point option
        def freqBoxState(*args):
            if self.reference_type.get() == 'Gravity':
                freq_entry.config(state=NORMAL)
            else:
                freq_entry.config(state=DISABLED)
        # Add new reference point options
        Label(self.root, text="Reference point type:").grid(row=7, column=1, padx=30, sticky=W)
        option_menu_window = OptionMenu(self.root, self.reference_type, "Axis points","Gravity","Plane", )
        option_menu_window.grid(row=7,column=1,padx=190,sticky=W)
        # trace the variable to control state of recording frequency box
        self.reference_type.trace("w", freqBoxState)
        tooltips.bind(option_menu_window,'Set the reference type. Axis points are 1-4 points defining the origin and axes, \nGravity is an object accelerating due to gravity, Plane are 3+ points that define the X-Y plane')
        Label(self.root, text="Recording frequency (Hz):").grid(row=8, column=1, padx=30, sticky=W)
        freq_entry = Entry(self.root, textvariable=self.freq, width=7, bd=3)
        freq_entry.grid(row=8, column=1, padx=200, sticky=W)
        tooltips.bind(freq_entry,'Recording frequency for gravity calculation.')
        # disable the box until "gravity" is selected
        freq_entry.config(state=DISABLED)

        group.grid(row=1, column=1, rowspan=3, padx=5, sticky=EW)

        Label(group, text="Scale (m): ").grid(row=0, column=0)
        row_entry = Entry(group, textvariable=self.scale, width=7, bd=3)
        row_entry.grid(row=0, column=1, sticky=W)
        tooltips.bind(row_entry, 'Distance between paired points (Wand length)')

        Label(group, text="Intrinsics: ").grid(row=1, column=0)
        option_menu_window = OptionMenu(group, self.intrinsic_fixes, "Optimize none", "Optimize focal length",
                       "Optimize focal length and principal point")
        option_menu_window.grid(row=1, column=1, sticky=W, pady=10)

        Label(group, text="Distortion: ").grid(row=2, column=0)
        option_menu_window = OptionMenu(group, self.distortion_fixes, "Optimize none", "Optimize r2", "Optimize r2, r4",
                       "Optimize all distortion coefficients")
        option_menu_window.grid(row=2, column=1, sticky=W)

        outlier_check = Checkbutton(group, text="Report on outliers", variable=self.report_on_outliers)
        outlier_check.grid(row=3, column=1, padx=10, pady=10, sticky=W)

        choose_check = Checkbutton(group, text="Choose reference camera", variable=self.choose)
        choose_check.grid(row=3, column=2, padx=10, pady=10, sticky=W)

        camera_check = Checkbutton(group, text="Output camera profiles", variable=self.output_camera_profiles)
        camera_check.grid(row=4, column=1, padx=10, sticky=W)

        find_in_file = Button(self.root, text="Specify", command=lambda: self.set_out_filename(self.tag), padx=10,
                            pady=10, width=10, height=1)
        find_in_file.grid(row=11, column=0, padx=10, pady=10)

        Label(self.root, text="Output tag and location:").grid(row=11, column=0, padx=20, pady=10, sticky=W)

        in_file_entry = Entry(self.root, textvariable=self.tag, width=40)
        in_file_entry.grid(row=12, column=0, columnspan=2, padx=10, pady=5, sticky=EW)

        write_log_check = Checkbutton(self.root, text='Write log', variable=self.should_log)
        write_log_check.grid(row=13, column=0, padx=20, pady=5, sticky=W)

        go = Button(self.root, text="Go", command=self.go, width=6, height=3)
        go.grid(row=14, column=0, padx=5, pady=5, sticky=W)

        quit_button = Button(self.root, text="Quit", command=self.quit_all, width=6, height=3)
        quit_button.grid(row=14, column=1, sticky=E, padx=5, pady=5)

        self.root.mainloop()

    @staticmethod
    def clear_var(var):
        var.set('')

    def go(self):
        try:
            float(self.scale.get())
        except Exception as e:
            print(e)
            six.moves.tkinter_messagebox.showwarning(
                "Error",
                "Scale must be a floating point number"
            )
            return

        cmd = [sys.executable, os.path.join(RESOURCE_PATH, 'scripts/argus-wand')]
        tmp = tempfile.mkdtemp()
        write_bool = False

        #args = [self.cams.get(), '--intrinsics_opt', self.intModeDict[self.intrinsic_fixes.get()], '--distortion_opt',
        #        self.disModeDict[self.distortion_fixes.get()], self.tag.get(), '--paired_points', self.ppts.get(),
        #        '--unpaired_points', self.uppts.get(), '--scale', self.scale.get(), '--reference_points',
        #        self.ref.get(), '--tmp', tmp]
        args = [self.cams.get(), '--intrinsics_opt', self.intModeDict[self.intrinsic_fixes.get()], '--distortion_opt',
                self.disModeDict[self.distortion_fixes.get()], self.tag.get(), '--paired_points', self.ppts.get(),
                '--unpaired_points', self.uppts.get(), '--scale', self.scale.get(), '--reference_points',
                self.ref.get(), '--reference_type', self.reference_type.get(), '--recording_frequency', self.freq.get(), 
                '--tmp', tmp]

        if self.should_log.get() == '1':
            write_bool = True

        if self.display.get() == '1':
            args = args + ['--graph']

        if self.report_on_outliers.get() == '1':
            args = args + ['--outliers']

        if self.output_camera_profiles.get() == '1':
            args = args + ['--output_camera_profiles']

        if self.choose.get() == '1':
            args = args + ['--choose_reference']

        cmd = cmd + args
        print(cmd) # TY DEBUG

        super(WandGUI, self).go(cmd, write_bool)
