# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


from prep.app import main

if __name__ == "__main__":
    import sys
    from pathlib import Path

    try:
        sys.path.remove(str(Path(__file__).parent.parent))
        if sys.platform == "win32":
            sys.stdout = sys.stderr = open("CONOUT$", "w")
            sys.stdin = open("CONIN$", "r")
    except Exception:
        pass
    # The launcher package is named ``prep`` (not ``anki``) so it never shadows
    # the real ``anki`` pylib package; drop it from sys.modules for tidiness.
    sys.modules.pop("prep", None)
    sys.modules.pop("prep.app", None)

    main()
