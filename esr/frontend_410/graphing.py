"""
graphing.py

This module defines custom QWidget-based classes for live scientific plotting in the experiment GUI:
- GraphWidget: For real-time line plots of signal data (I/Q/Amplitude traces).
- SweepPlotWidget: For real-time 2D color plots and 1D sweep plots during experiment sweeps.

Dependencies:
- PyQt5
- Matplotlib
"""

import pyscan as ps

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QMenu)
from PyQt5.QtGui import QPixmap

from PyQt5.QtCore import Qt, pyqtSlot

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import io
import numpy as np

class GraphWidget(QWidget):
    """ A QWidget subclass that embeds a Matplotlib figure for real-time plotting.
        This widget provides a graphical interface for visualizing experimental data,
        such as I/Q signals and amplitude over time. It contains a Matplotlib figure
        canvas and a vertical layout to integrate smoothly with PyQt5-based GUIs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set the background to transparent and remove any borders or margins
        self.setStyleSheet("background: transparent; border: none;")

        # Create the Figure and Axes safely without using pyplot
        self.figure = Figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)

        # Layout for the graphing widget
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)

        # Enable custom context menu
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.show_context_menu)

    def update_canvas_se(self, sig, task_name):
        """Clears the current plot and renders new data traces for CH1, CH2, and amplitude."""

        # Flatten the lists for plotting
        time = sig.time
        i = sig.i
        q = sig.q
        x = sig.x
        
        self.ax.clear()
        self.ax.plot(time, i, label='CH1', color='yellow')
        self.ax.plot(time, q, label='CH2', color='blue')
        self.ax.plot(time, x, label='AMP', color='green')
        self.ax.set_xlabel('Time (μs)')
        self.ax.set_ylabel('Signal (a.u.)')
        self.ax.legend()
        self.canvas.draw()
    
    def update_canvas_psweep(self, sig, task_name):
        self.ax.clear()
        print("Updating pulse sweep canvas")

        if task_name == "read_processed":
            try:
                fit, err = ps.plot_exp_fit_norange(np.array([sig.time, sig.x]), sig.freq, 1, plt=self.ax)
                sig.fit = fit
                self.ax.plot(sig.time, sig.x, label="Signal")  # This line is crucial for legend
                fitstr = f'A={sig.fit[1]:.3g} V, t={sig.fit[2]:.3g} μs, Q={sig.fit[-1]:.3g}'
                freqstr = f'freq (MHz): {sig.freq}'

                self.ax.text(0.5, 0.95, fitstr, transform=self.ax.transAxes, ha='center', va='top')  # Near the top, inside
                self.ax.text(0.5, 0.90, freqstr, transform=self.ax.transAxes, ha='center', va='top')  # Slightly below the fitstr
            except Exception as e:
                self.updateStatus.emit(f"Error in plotting read_processed pulse frequency sweep: {e}\n")
        
        elif task_name == "read_unprocessed":
            self.ax.plot(sig.time, sig.i, color='yellow', label='CH1')
            self.ax.plot(sig.time, sig.q, color='b', label='CH2')
            self.ax.plot(sig.time, sig.x, color='g', label='AMP')

        self.ax.set_xlabel('Time (μs)')
        self.ax.set_ylabel('Signal (a.u.)')
        self.ax.legend()
        self.canvas.draw()
    
    def show_context_menu(self, pos):
        menu = QMenu()
        copy_action = menu.addAction("Copy graph to clipboard")
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == copy_action:
            self.copy_to_clipboard()

    def copy_to_clipboard(self):
        # Save current canvas to QPixmap
        buf = io.BytesIO()
        self.figure.savefig(buf, format='png')
        buf.seek(0)
        image = QPixmap()
        image.loadFromData(buf.getvalue())

        # Copy to clipboard
        QApplication.clipboard().setPixmap(image)
        print("Copied graph to clipboard.")

        
class SweepPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # --- cache artists ---
        self.mesh = None          # for the 2D colormesh
        self.colorbar = None
        self.line, = self.ax.plot([], [], 'o-')  # for the 1D sweep

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        
        # Enable custom context menu
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.show_context_menu)

    @pyqtSlot(object)
    def on_live_plot_2D(self, pg):
        print("Updating 2D plot\n")
        if pg is None or pg.data.size == 0:
            return

        # First time: create the QuadMesh
        if self.mesh is None:
            self.mesh = self.ax.pcolormesh(
                pg.x, pg.y, pg.data.T,
                shading='auto',
                vmin=pg.get_data_range()[0],
                vmax=pg.get_data_range()[1]
            )
            self.colorbar = self.figure.colorbar(self.mesh, ax=self.ax)
        else:
            # Only update the array & color scale
            self.mesh.set_array(pg.data.T.ravel())
            vmin, vmax = pg.get_data_range()
            self.mesh.set_clim(vmin, vmax)
            # no need to recreate colorbar

        self.ax.set_title(pg.get_title())
        self.ax.set_xlabel(pg.get_xlabel())
        self.ax.set_ylabel(pg.get_ylabel())

        # Non‐blocking redraw
        self.canvas.draw_idle()

    @pyqtSlot(object)
    def on_live_plot_1D(self, pg):
        print("Updating 1D plot\n")
        if pg is None or pg.data is None or pg.x is None or pg.data.size == 0:
            return

        # Update the Line2D data
        self.line.set_data(pg.x, pg.data)

        # Rescale axes
        self.ax.relim()
        self.ax.autoscale_view()

        self.ax.set_title(pg.get_title())
        self.ax.set_xlabel(pg.get_xlabel())
        self.ax.set_ylabel(pg.get_ylabel())

        # Non‐blocking redraw
        self.canvas.draw_idle()

    def show_context_menu(self, pos):
        menu = QMenu()
        copy_action = menu.addAction("Copy graph to clipboard")
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == copy_action:
            self.copy_to_clipboard()

    def copy_to_clipboard(self):
        # Save current canvas to QPixmap
        buf = io.BytesIO()
        self.figure.savefig(buf, format='png')
        buf.seek(0)
        image = QPixmap()
        image.loadFromData(buf.getvalue())

        # Copy to clipboard
        QApplication.clipboard().setPixmap(image)
        print("Copied graph to clipboard.")
 