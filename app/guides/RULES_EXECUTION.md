# Règles d'exécution des commandes

1. **Toujours revenir au prompt PowerShell ou CMD avant d'exécuter des commandes shell.**
   - Si l'invite affiche `>>>`, vous êtes dans l'interpréteur Python.  
   - Tapez `exit()` ou faites `Ctrl+Z` puis Entrée pour revenir au prompt normal.

2. **Ne pas lancer de commandes `cd`, `git`, `python`, etc. depuis `>>>`.**
   - L'interpréteur Python les traite comme du code et déclenche des `SyntaxError`.

3. **Exécuter les scripts Python depuis le prompt système :**
   ```powershell
   cd "C:\Users\SZERTYUIOPMLMM\Desktop\APP\app"
   C:\Python314\python.exe script.py
   ```

4. **Utiliser les fichiers `.bat` fournis pour automatiser les tests :**
   - `TEST_FINAL.bat`, `UNIFY_PASSWORDS.bat`, `COMPARE_EXCEL.bat`, `RUN_DB_TEST.bat`, etc.

5. **Ne jamais mélanger interpréteurs :**
   - Prompt Python (`>>>`) pour exécuter du code Python interactif.
   - Prompt PowerShell/CMD (`PS C:\...>` ou `C:\...>`) pour les commandes système.

