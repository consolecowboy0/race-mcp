"""Simple Tkinter GUI to launch the Race MCP server."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText


class MCPServerGUI:
    """Basic GUI for starting and stopping the Race MCP server."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Race MCP Server")

        self.start_button = tk.Button(
            root, text="Start MCP Server", command=self.start_server
        )
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(
            root, text="Stop MCP Server", command=self.stop_server, state=tk.DISABLED
        )
        self.stop_button.pack(pady=5)

        self.log_output = ScrolledText(root, state="disabled", height=20, width=80)
        self.log_output.pack(padx=5, pady=5)

        self.process: subprocess.Popen[str] | None = None
        self.reader_thread: threading.Thread | None = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_server(self) -> None:
        """Launch the MCP server in a subprocess."""
        if self.process is not None:
            return

        cmd = [sys.executable, "-m", "race_mcp_server.main"]
        env = os.environ.copy()
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
        )
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

    def _read_output(self) -> None:
        """Read server output and display it in the log window."""
        assert self.process is not None and self.process.stdout is not None
        for line in self.process.stdout:
            self.log_output.configure(state="normal")
            self.log_output.insert(tk.END, line)
            self.log_output.configure(state="disabled")
            self.log_output.yview(tk.END)

    def stop_server(self) -> None:
        """Terminate the MCP server process."""
        if self.process is None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        finally:
            self.process = None
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def on_close(self) -> None:
        """Handle window close by stopping the server and closing GUI."""
        self.stop_server()
        self.root.destroy()


def main() -> None:
    """Run the GUI application."""
    root = tk.Tk()
    MCPServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
