# First run on an unsigned build

PokeMMO Controller is not signed with a paid Windows or Apple certificate (decision of 2026-11-18). The updates it downloads later are still checked against our own key and refused if they do not match; that is a separate check from the one your system shows below. The first time you open a download, your system warns you. Each step below is the whole fix; nothing needs admin rights.

These steps are written from the vendors' own documentation. Screenshots from a real Windows and a real Mac will replace this text-only version; until then they are marked unverified.

## Windows: SmartScreen "Windows protected your PC"

1. Open the download. A blue window says **Windows protected your PC**.
2. Click **More info**. A second line appears under the app name.
3. Click **Run anyway**.
4. The app opens. Windows does not ask again for this file.

If **Run anyway** is missing, right-click the downloaded file, choose **Properties**, tick **Unblock** at the bottom, press **OK**, and open it again.

## macOS: "cannot be opened" (Open Anyway)

1. Open the app. macOS says it cannot verify the app and offers only **Done** (or **Move to Trash**: choose **Done**).
2. Open **System Settings**, then **Privacy & Security**.
3. Scroll to **Security**. A line says the app "was blocked to protect your Mac". Click **Open Anyway**.
4. Enter your password or use Touch ID, then click **Open** in the last window.

On macOS 14 and older the same button is in **System Preferences**, **Security & Privacy**, **General**. Homebrew installs (our own tap) skip this step.

## Linux and Steam Deck

Nothing to approve. Make the AppImage runnable once (right-click, **Properties**, **Permissions**, **Allow executing**), or run the install command from the README.

## What stays true on every system

The app never asks for admin or root, never closes PokeMMO for you, and writes only the files listed in the README's "What it changes". Unverified until a person tests it: Windows 11 wording above on a clean machine, macOS 15 wording above on a clean Mac.
