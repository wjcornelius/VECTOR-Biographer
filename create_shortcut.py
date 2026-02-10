"""Create a desktop shortcut for VECTOR Biographer."""

import os
import sys
from pathlib import Path

def create_shortcut():
    """Create a desktop shortcut to START_BIOGRAPHER.bat"""
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        # Try to install winshell
        print("Installing shortcut creation tools...")
        os.system(f"{sys.executable} -m pip install winshell pywin32")
        try:
            import winshell
            from win32com.client import Dispatch
        except ImportError:
            print("Could not install shortcut tools. Create shortcut manually.")
            return False

    # Paths
    script_dir = Path(__file__).parent.resolve()
    batch_file = script_dir / "START_BIOGRAPHER.bat"
    desktop = Path(winshell.desktop())
    shortcut_path = desktop / "VECTOR Biographer.lnk"

    # Create shortcut
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(batch_file)
    shortcut.WorkingDirectory = str(script_dir)
    shortcut.Description = "Start VECTOR Biographer - Voice-based life story capture"
    shortcut.IconLocation = str(sys.executable)  # Python icon as fallback
    shortcut.save()

    print(f"Desktop shortcut created: {shortcut_path}")
    return True


def create_shortcut_vbs_fallback():
    """Fallback: create shortcut using VBScript (no extra dependencies)."""
    script_dir = Path(__file__).parent.resolve()
    batch_file = script_dir / "START_BIOGRAPHER.bat"

    # Get desktop path
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    if not desktop.exists():
        desktop = Path(os.path.expanduser("~")) / "OneDrive" / "Desktop"

    shortcut_path = desktop / "VECTOR Biographer.lnk"

    # Create VBScript to make shortcut
    vbs_content = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{batch_file}"
oLink.WorkingDirectory = "{script_dir}"
oLink.Description = "Start VECTOR Biographer"
oLink.Save
'''

    vbs_path = script_dir / "make_shortcut.vbs"
    vbs_path.write_text(vbs_content)

    # Run VBScript
    os.system(f'cscript //nologo "{vbs_path}"')
    vbs_path.unlink()  # Clean up

    if shortcut_path.exists():
        print(f"Desktop shortcut created: {shortcut_path}")
        return True
    return False


if __name__ == "__main__":
    # Try winshell method first, fall back to VBScript
    try:
        success = create_shortcut()
    except Exception as e:
        print(f"Primary method failed: {e}")
        success = False

    if not success:
        print("Trying fallback method...")
        success = create_shortcut_vbs_fallback()

    if not success:
        print("\nCould not create shortcut automatically.")
        print("To create manually:")
        print("1. Right-click on your Desktop")
        print("2. Select New > Shortcut")
        print(f"3. Browse to: {Path(__file__).parent / 'START_BIOGRAPHER.bat'}")
        print("4. Name it 'VECTOR Biographer'")
