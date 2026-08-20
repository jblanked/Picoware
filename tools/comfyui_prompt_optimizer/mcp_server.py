# mcp_server.py - Ein einfacher MCP-Server für LM Studio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_optimizer import MinimaxH3PromptOptimizer
from typing import Dict, Any

class ComfyUIPromptOptimizerMCP:
    def __init__(self):
        self.optimizer = MinimaxH3PromptOptimizer()

    def handle_prompt(self, text: str) -> str:
        optimized_result = self.optimizer.analyze_and_optimize(text)

        return optimized_result

# Beispiel-Aufruf
if __name__ == "__main__":
    server = ComfyUIPromptOptimizerMCP()

    # Test mit einem Beispiel-Prompt
    user_prompt = "ein futuristischer Cyborg in einer neonbeleuchteten Stadt"

    optimized_result = server.handle_prompt(user_prompt)

    print("=== Optimierter Prompt ===")
    print(optimized_result)
