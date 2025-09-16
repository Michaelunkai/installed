Parsec Portable
---------------

This archive contains all of the subcomponents of a Parsec installation on Windows:

1. The root directory of the archive contains appdata.json, parsecd.exe, the parsecd-XXX-XX.dll SDK & app bundle, and this document. If these files are put together in the same directory, Parsec will operate in "portable" mode, confining itself to the directory where parsecd.exe is run from. The normal Parsec installation installs parsecd.exe to "Program Files" and uses the current user's %APPDATA% directory (usually Users\YOU\AppData\Roaming\) for the Parsec SDK and app bundle.

2. The "service" directory contains pservice.exe, the Parsec System Service required to elevate the parsecd.exe application so it can interact with the secure desktop. This is necessary to remotely access UAC prompts.

3. The "vusb" directory contains the Parsec Virtual USB driver used for wacom and gamepad input.

If you have issues using Parsec (or questions), contact us at support@parsec.app, or visit our Discord server at https://discord.gg/GxGfffY.
