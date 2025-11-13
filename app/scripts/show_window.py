import win32gui
import win32con


def find_and_show_window():
    """Trouve et affiche la fenêtre de l'application"""

    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Payroll" in title or "Python" in title:
                windows.append((hwnd, title))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)

    if windows:
        for hwnd, title in windows:
            print(f"Fenêtre trouvée: {title}")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            print("✅ Fenêtre affichée au premier plan")
            return True
    else:
        print("❌ Aucune fenêtre Payroll trouvée")
        return False


if __name__ == "__main__":
    find_and_show_window()
