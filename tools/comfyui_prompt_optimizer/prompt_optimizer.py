# prompt_optimizer.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import json
from typing import Dict, Any

class MinimaxH3PromptOptimizer:
    def __init__(self):
        # Beispielhafte Konfiguration für Minimax H3 (anpassbar)
        self.default_params = {
            "steps": 25,
            "cfg_scale": 7.5,
            "sampler": "DPM++ SDE Karrar",
            "model_name": "minimax_h3_v1"
        }

    def analyze_and_optimize(self, prompt_text: str) -> str:
        # 1. Analyse des Eingabe-Prompts (für Regelentscheidungen)
        analysis = self._analyze_prompt(prompt_text)

        # 2. Optimierung (regelbasiert + KI-gestützte Vorschläge)
        optimized_prompt = self._optimize_prompt(analysis)

        return optimized_prompt

    def _analyze_prompt(self, text: str) -> Dict[str, Any]:
        # Einfache Analyse (z.B. Länge, Schlüsselwörter, Stil)
        words = len(text.split())
        has_style = any(keyword in text.lower() for keyword in ["cinematic", "photorealistic", "oil painting", "anime"])

        return {
            "word_count": words,
            "has_style_hint": has_style,
            "length_category": "short" if words < 10 else ("medium" if words < 30 else "long"),
            "original_text": text
        }

    def _optimize_prompt(self, analysis: Dict[str, Any]) -> str:
        # Regelbasierte Optimierung für Minimax H3 Syntax (Two-Block Formula)
        original_text = analysis["original_text"]

        # Block 1: Optionaler Referenzmaterialien-Bereich
        block1 = ""
        if analysis["length_category"] == "short":
            block1 = f"[Block 1]: Reference material notes: The scene should include detailed environmental context and atmospheric elements.\n\n"

        # Block 2: Hauptbeschreibung und Stil-Anweisungen
        block2_content = original_text

        # Füge Details hinzu, falls der Prompt zu kurz ist
        if analysis["length_category"] == "short":
            details = [
                "Hyperrealistic",
                "8k resolution",
                "cinematic lighting",
                "intricate details"
            ]
            block2_content += ", ".join(details)

        # Füge Stil hinzu, falls nicht vorhanden
        if not analysis["has_style_hint"]:
            block2_content += ", cinematic photography style"

        return f"{block1}[Block 2]: {block2_content}"



# Beispiel-Aufruf für LM Studio (wird im Chat aufgerufen)
if __name__ == "__main__":
    optimizer = MinimaxH3PromptOptimizer()

    # Eingabe-Prompt (von ComfyUI oder Benutzer)
    user_prompt = "ein futuristischer Cyborg in einer neonbeleuchteten Stadt"

    optimized_result = optimizer.analyze_and_optimize(user_prompt)

    print("=== Optimierter Prompt ===")
    print(optimized_result)
