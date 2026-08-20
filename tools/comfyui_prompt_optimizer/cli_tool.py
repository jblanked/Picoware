# cli_tool.py - Der einfachste Weg: Nur den Prompt eingeben!
import sys
from prompt_optimizer import MinimaxH3PromptOptimizer

def optimize_prompt(prompt_text: str) -> str:
    optimizer = MinimaxH3PromptOptimizer()
    return optimizer.analyze_and_optimize(prompt_text)

# Beispiel-Aufruf (wird automatisch ausgeführt, wenn das Skript direkt aufgerufen wird)
if __name__ == "__main__":
    # Prüfe, ob ein Prompt als Argument übergeben wurde
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        # Standard-Beispiel-Prompt
        user_prompt = "ein futuristischer Cyborg in einer neonbeleuchteten Stadt"

    optimized_result = optimize_prompt(user_prompt)
    print(optimized_result)
