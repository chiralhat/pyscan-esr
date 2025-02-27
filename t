[1mdiff --git a/esr_notebooks/Pulsed Frequency Sweep.ipynb b/esr_notebooks/Pulsed Frequency Sweep.ipynb[m
[1mindex 1e0aed8..31b7c20 100644[m
[1m--- a/esr_notebooks/Pulsed Frequency Sweep.ipynb[m	
[1m+++ b/esr_notebooks/Pulsed Frequency Sweep.ipynb[m	
[36m@@ -14,11 +14,38 @@[m
   },[m
   {[m
    "cell_type": "code",[m
[31m-   "execution_count": null,[m
[32m+[m[32m   "execution_count": 2,[m
    "metadata": {[m
     "scrolled": true[m
    },[m
[31m-   "outputs": [],[m
[32m+[m[32m   "outputs": [[m
[32m+[m[32m    {[m
[32m+[m[32m     "name": "stdout",[m
[32m+[m[32m     "output_type": "stream",[m
[32m+[m[32m     "text": [[m
[32m+[m[32m      "The autoreload extension is already loaded. To reload it, use:\n",[m
[32m+[m[32m      "  %reload_ext autoreload\n"[m
[32m+[m[32m     ][m
[32m+[m[32m    },[m
[32m+[m[32m    {[m
[32m+[m[32m     "data": {[m
[32m+[m[32m      "text/plain": [[m
[32m+[m[32m       "<Figure size 576x360 with 0 Axes>"[m
[32m+[m[32m      ][m
[32m+[m[32m     },[m
[32m+[m[32m     "metadata": {},[m
[32m+[m[32m     "output_type": "display_data"[m
[32m+[m[32m    },[m
[32m+[m[32m    {[m
[32m+[m[32m     "data": {[m
[32m+[m[32m      "text/plain": [[m
[32m+[m[32m       "<Figure size 576x360 with 0 Axes>"[m
[32m+[m[32m      ][m
[32m+[m[32m     },[m
[32m+[m[32m     "metadata": {},[m
[32m+[m[32m     "output_type": "display_data"[m
[32m+[m[32m    }[m
[32m+[m[32m   ],[m
    "source": [[m
     "%load_ext autoreload\n",[m
     "%autoreload 2\n",[m
[36m@@ -55,6 +82,34 @@[m
     "# display(HTML(\"<style>.container { width:100% !important; }</style>\"))"[m
    ][m
   },[m
[32m+[m[32m  {[m
[32m+[m[32m   "cell_type": "code",[m
[32m+[m[32m   "execution_count": 6,[m
[32m+[m[32m   "metadata": {},[m
[32m+[m[32m   "outputs": [],[m
[32m+[m[32m   "source": [[m
[32m+[m[32m    "from new_gui import *"[m
[32m+[m[32m   ][m
[32m+[m[32m  },[m
[32m+[m[32m  {[m
[32m+[m[32m   "cell_type": "code",[m
[32m+[m[32m   "execution_count": null,[m
[32m+[m[32m   "metadata": {},[m
[32m+[m[32m   "outputs": [[m
[32m+[m[32m    {[m
[32m+[m[32m     "name": "stdout",[m
[32m+[m[32m     "output_type": "stream",[m
[32m+[m[32m     "text": [[m
[32m+[m[32m      "Python 3.10.4 (main, Apr  2 2022, 09:04:19) [GCC 11.2.0] on linux\n",[m
[32m+[m[32m      "Type \"help\", \"copyright\", \"credits\" or \"license\" for more information.\n",[m
[32m+[m[32m      ">>> "[m
[32m+[m[32m     ][m
[32m+[m[32m    }[m
[32m+[m[32m   ],[m
[32m+[m[32m   "source": [[m
[32m+[m[32m    "!python3"[m
[32m+[m[32m   ][m
[32m+[m[32m  },[m
   {[m
    "cell_type": "code",[m
    "execution_count": null,[m
[1mdiff --git a/esr_notebooks/Spin Echo GUI.ipynb b/esr_notebooks/Spin Echo GUI.ipynb[m
[1mindex 88689bd..55d68b9 100644[m
[1m--- a/esr_notebooks/Spin Echo GUI.ipynb[m	
[1m+++ b/esr_notebooks/Spin Echo GUI.ipynb[m	
[36m@@ -14,11 +14,76 @@[m
   },[m
   {[m
    "cell_type": "code",[m
[31m-   "execution_count": null,[m
[32m+[m[32m   "execution_count": 1,[m
    "metadata": {[m
     "scrolled": true[m
    },[m
[31m-   "outputs": [],[m
[32m+[m[32m   "outputs": [[m
[32m+[m[32m    {[m
[32m+[m[32m     "name": "stderr",[m
[32m+[m[32m     "output_type": "stream",[m
[32m+[m[32m     "text": [[m
[32m+[m[32m      "/usr/local/share/pynq-venv/lib/python3.10/site-packages/pyvisa_py/tcpip.py:122: UserWarning: TCPIP::hislip resource discovery requires the zeroconf package to be installed... try 'pip install zeroconf'\n",[m
[32m+[m[32m      "  warnings.warn(\n"[m
[32m+[m[32m     ][m
[32m+[m[32m    },[m
[32m+[m[32m    {[m
[32m+[m[32m     "data": {[m
[32m+[m[32m      "application/javascript": [[m
[32m+[m[32m       "\n",[m
[32m+[m[32m       "try {\n",[m
[32m+[m[32m       "require(['notebook/js/codecell'], function(codecell) {\n",[m
[32m+[m[32m       "  codecell.CodeCell.options_default.highlight_modes[\n",[m
[32m+[m[32m       "      'magic_text/x-csrc'] = {'reg':[/^%%microblaze/]};\n",[m
[32m+[m[32m       "  Jupyter.notebook.events.one('kernel_ready.Kernel', function(){\n",[m
[32m+[m[32m       "      Jupyter.notebook.get_cells().map(function(cell){\n",[m
[32m+[m[32m       "          if (cell.cell_type == 'code'){ cell.auto_highlight(); } }) ;\n",[m
[32m+[m[32m       "  });\n",[m
[32m+[m[32m       "});\n",[m
[32m+[m[32m       "} catch (e) {};\n"[m
[32m+[m[32m      ][m
[32m+[m[32m     },[m
[32m+[m[32m     "metadata": {},[m
[32m+[m[32m     "output_type": "display_data"[m
[32m+[m[32m    },[m
[32m+[m[32m    {[m
[32m+[m[32m     "data": {[m
[32m+[m[32m      "application/javascript": [[m
[32m+[m[32m       "\n",[m
[32m+[m[32m       "try {\n",[m
[32m+[m[32m       "require(['notebook/js/codecell'], function(codecell) {\n",[m
[32m+[m[32m       "  codecell.CodeCell.options_default.highlight_modes[\n",[m
[32m+[m[32m       "      'magic_text/x-csrc'] = {'reg':[/^%%pybind11/]};\n",[m
[32m+[m[32m       "  Jupyter.notebook.events.one('kernel_ready.Kernel', function(){\n",[m
[32m+[m[32m       "      Jupyter.notebook.get_cells().map(function(cell){\n",[m
[32m+[m[32m       "          if (cell.cell_type == 'code'){ cell.auto_highlight(); } }) ;\n",[m
[32m+[m[32m       "  });\n",[m
[32m+[m[32m       "});\n",[m
[32m+[m[32m       "} catch (e) {};\n"[m
[32m+[m[32m      ][m
[32m+[m[32m     },[m
[32m+[m[32m     "metadata": {},[m
[32m+[m[32m     "output_type": "display_data"[m
[32m+[m[32m    },[m
[32m+[m[32m    {[m
[32m+[m[32m     "data": {[m
[32m+[m[32m      "text/plain": [[m
[32m+[m[32m       "<Figure size 576x360 with 0 Axes>"[m
[32m+[m[32m      ][m
[32m+[m[32m     },[m
[32m+[m[32m     "metadata": {},[m
[32m+[m[32m     "output_type": "display_data"[m
[32m+[m[32m    },[m
[32m+[m[32m    {[m
[32m+[m[32m     "data": {[m
[32m+[m[32m      "text/plain": [[m
[32m+[m[32m       "<Figure size 576x360 with 0 Axes>"[m
[32m+[m[32m      ][m
[32m+[m[32m     },[m
[32m+[m[32m     "metadata": {},[m
[32m+[m[32m     "output_type": "display_data"[m
[32m+[m[32m    }[m
[32m+[m[32m   ],[m
    "source": [[m
     "%load_ext autoreload\n",[m
     "%autoreload 2\n",[m
[1mdiff --git a/test.py b/test.py[m
[1mindex 650d9af..64f08f2 100644[m
[1m--- a/test.py[m
[1m+++ b/test.py[m
[36m@@ -1,7 +1 @@[m
[31m-import matplotlib.pyplot as plt[m
[31m-[m
[31m-x = [1, 2, 3, 4, 5][m
[31m-y = [1, 2, 3, 4, 5][m
[31m-[m
[31m-plt.plot(x, y)[m
[31m-plt.show()[m
\ No newline at end of file[m
[32m+[m[32mprint("test - big changes")[m
\ No newline at end of file[m
