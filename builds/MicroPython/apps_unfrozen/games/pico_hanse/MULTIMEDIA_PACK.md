# Pico Hanse optional multimedia pack

Pico Hanse never requires this pack. If any expected file is absent, the game
starts normally and runs silently. A prepared SD card or simulator may keep all
files in:

`/picoware/apps/games/pico_hanse/audio/`

For file-by-file `mpremote` deployment on a PicoCalc, the runtime also supports
these three directories:

- `/picoware/apps/games/ph_a1/`: `bell.wav`, `build.wav`, `coin.wav`,
  `election.wav`, `guild_theme.wav`
- `/picoware/apps/games/ph_a2/`: `harbor_autumn.wav`, `harbor_spring.wav`,
  `harbor_summer.wav`, `harbor_winter.wav`, `menu_theme.wav`
- `/picoware/apps/games/ph_a3/`: `mission.wav`, `sail.wav`, `sea_theme.wav`,
  `tavern_theme.wav`, `warning.wav`

Use RIFF WAV, unsigned 8-bit PCM, mono, 11025 Hz. Music may be rendered at a
higher quality first, but the files placed on the PicoCalc should use this
compact format.

## Original music direction

The score should evoke the restrained Hanseatic trading-game atmosphere of
early Patrician-era games without copying melodies, arrangements, recordings,
or recognizable themes. Write wholly original modal chamber pieces using a
small palette such as lute, recorder, viol, quiet shawm, psaltery, hand drum,
and occasional town bells. Prefer patient 6/8 or 3/4 motion, modest dynamics,
short memorable motifs, and plenty of breathing room over heroic orchestral
music.

- `menu_theme.wav` — 30 seconds; dignified guild motif.
- `harbor_spring.wav` — 45 seconds; light recorder and lute.
- `harbor_summer.wav` — 45 seconds; warm strings and gentle hand drum.
- `harbor_autumn.wav` — 45 seconds; lower viol and measured lute.
- `harbor_winter.wav` — 45 seconds; sparse psaltery, bell, and cold recorder.
- `sea_theme.wav` — 40 seconds; rolling 6/8 pulse with restrained tension.
- `guild_theme.wav` — 35 seconds; formal, deliberate civic chamber music.
- `tavern_theme.wav` — 30 seconds; intimate dance tune, never boisterous.

Make every music file loop cleanly at the stated duration.

## Sound effects

Keep effects short, dry, and readable on the PicoCalc speaker:

- `coin.wav` — trade confirmation.
- `sail.wav` — canvas and rope departure cue.
- `bell.wav` — arrival or ordinary notification.
- `build.wav` — hammer and timber construction cue.
- `mission.wav` — guild mission or civic-project completion flourish.
- `warning.wav` — storm, pirate, expiry, or urgent alert.
- `election.wav` — short ceremonial town fanfare.

The runtime enables audio only after all fifteen files pass the existence
check. Music can be toggled quickly with `P` anywhere in the game. Press `B`
on the mode screen for separate music and effects switches plus five volume
levels. These preferences persist independently of campaign saves.
