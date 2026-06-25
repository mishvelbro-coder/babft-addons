---

## ⚙️ Blender UI Overview (Интерфейс)

Since the plugin interface is in Russian, use this quick reference guide to understand every slider and option:

### 📥 Importer Menu (Меню Импорта)
*   **Лимит блоков (Block Limit):** Sets how many blocks to load (supports from 1 up to 250,000 blocks) to protect Blender from lagging.
*   **Фильтр ID (ID Filter):** Clean-up utility. Values **1–5** automatically delete broken overlapping duplicate blocks from the model. Value **6** turns the filter off.
*   **Импорт невидимых (Import Invisible):** Turn *On* to load all hidden parts, that have 100% transparency.
*   **Использовать цвета (Use Colors):** Turn *On* to transfer the build's original coloring into Blender.
*   **Только механизмы (Only Mechanisms):** If enabled, ignores all walls and armor, loading only pistons, motors, hinges, and logic parts.

### 📤 Exporter Menu (Меню Экспорта)
*   **1.1 Лимит Блоков (Block Limit):** Caps the maximum number of blocks saved to the file (up to 500,000) to prevent game lag.
*   **1.2 Точность округления (Round Precision):** Number of decimal places. 3 or 4 sign digits will close all gaps between blocks in the game.
*   **1.3 Мин. размер блока (Min Block Size):** Automatically ignores tiny junk vertices or sub-pixel geometry shifts (in studs).
*   **1.4 Инверсия оси Y (Invert Y-Axis):** Globally flips the final structure upside down along the game's Y-axis if needed.
*   **2.1 Режим цвета (Color Mode):** *LOCAL* uses paint data from Blender. *GLOBAL* forces the entire model into a single color chosen from the palette.
*   **2.2 Режим материала (Material Mode):** *LOCAL* keeps original block textures. *GLOBAL* turns the whole vehicle into one selected material.
*   **2.3 Включить замену материалов (Change Material):** Drop-down swapping utility. Turn it *On*, choose what to search for (**Искать**, e.g., `Piston`), and what to replace it with (**Заменить на**, e.g., `NeonBlock`) to instantly change block types on the fly.
*   **3.1 Коллизия (Collision):** Forces global `CanCollide` status to *True*, *False*, or leaves it *Local* (per block data).
*   **3.2 Лимит прозрачности (Transparency Limit):** Blocks more transparent than this value will be completely wiped from the final export file.
*   **3.3 Отбрасывание теней (Cast Shadow):** Globally toggles lighting shadows on or off for the whole build.
*   **3.4 Логика механизмов (Export Logic):** Turn *On* to save piston speeds, lengths, and wiring binds. Turn *Off* to strip all wires, making the output file up to **2x lighter** (perfect for decoration models).
*   **4.1 Формат файла (File Format):** Set to *V1_FORMAT* to generate the modern structure with the mandatory strict `"AutoBuild_Version":"v1"` marker at the very end of the JSON line.
