# ComfyUI Minimax H3 Prompt Optimizer für LM Studio

## Beschreibung
Dieser Skill analysiert einen Text-Prompt und optimiert ihn für die Verwendung mit dem **Minimax H3**-Modell in einer **ComfyUI**-Pipeline. Er sorgt dafür, dass der Prompt strukturiert ist, relevante Parameter (wie Aspect Ratio, Steps, CFG) berücksichtigt und den Stil klar definiert wird.

## Aufruf
Du kannst diesen Skill im Chat von LM Studio aufrufen mit einem einfachen Prompt wie:

```text
optimize_prompt für "ein futuristischer Cyborg in einer neonbeleuchteten Stadt"
```

Das Skript wird dann:
1. Den Eingabe-Prompt analysieren.
2. Empfehlungen für ComfyUI-Nodes geben (z.B. `CLIPTextEncode`, `KSampler`).
3. Optimierungen vornehmen (z.B. mehr Details hinzufügen, Stil definieren).
4. Eine optimierte Version des Prompts zurückgeben.

## Beispiel-Ergebnis

**Eingabe:**
> "ein futuristischer Cyborg in einer neonbeleuchteten Stadt"

**Optimierter Prompt (für Minimax H3):**
> "Hyperrealistic, 8k, cinematic lighting, a futuristic cyborg with intricate mechanical details standing in the center of a bustling cyberpunk city at night. Neon lights reflect off wet pavement, towering skyscrapers with holographic billboards, flying cars, and a moody atmosphere. Shot on 35mm film, depth of field, highly detailed textures."

**Empfohlene ComfyUI-Parameter:**
- **Model:** `minimax_h3_v1.safetensors` (oder dein gewähltes Modell)
- **Steps:** 20-30
- **CFG Scale:** 7.5
- **Sampler:** `DPM++ SDE Karras`
- **Aspect Ratio:** 16:9 (optional, falls gewünscht)

## Technische Details
Das Skript nutzt eine Kombination aus regelbasierten Optimierungen und optionalen KI-gestützten Vorschlägen, um sicherzustellen, dass der Prompt die Stärken des Minimax H3-Modells (z.B. hohe Detailtreue, gute Textrendering-Fähigkeiten) ausschöpft.

## Nutzung in LM Studio
Um den Skill in LM Studio zu nutzen:
1. Stelle sicher, dass der Ordner `tools/comfyui_prompt_optimizer` im Hauptverzeichnis deines LM Studio-Projekts liegt.
2. Importiere das Skript in dein Python-Umfeld (z.B. über einen MCP-Server oder direkt im Chat).
3. Rufe den Skill mit einem Prompt wie oben beschrieben auf.
