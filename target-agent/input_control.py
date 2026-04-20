from __future__ import annotations

import pyautogui


pyautogui.FAILSAFE = False

KEY_MAP = {
    "ArrowUp": "up",
    "ArrowDown": "down",
    "ArrowLeft": "left",
    "ArrowRight": "right",
    "Escape": "esc",
    "Enter": "enter",
    "Backspace": "backspace",
    "Delete": "delete",
    "Tab": "tab",
    "Shift": "shift",
    "Control": "ctrl",
    "Alt": "alt",
    "Meta": "win",
    " ": "space",
}


def normalize_key(key: str) -> str:
    if len(key) == 1:
        return key.lower()
    return KEY_MAP.get(key, key.lower())


def apply_input(message: dict) -> None:
    kind = message.get("type")

    if kind == "mouse":
        x = int(message.get("x", 0))
        y = int(message.get("y", 0))
        action = message.get("action", "move")
        button = message.get("button", "left")
        pyautogui.moveTo(x, y)
        if action == "down":
            pyautogui.mouseDown(button=button)
        elif action == "up":
            pyautogui.mouseUp(button=button)
        elif action == "wheel":
            pyautogui.scroll(-200 if int(message.get("deltaY", 0)) > 0 else 200)
        return

    if kind == "key":
        key = normalize_key(str(message.get("key", "")))
        action = message.get("action", "down")
        if action == "down":
            pyautogui.keyDown(key)
        elif action == "up":
            pyautogui.keyUp(key)
