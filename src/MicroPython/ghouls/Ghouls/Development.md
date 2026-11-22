## Development Guide
Set up the [configuration](Configuration.md), including the required input macros, then:
1. Clone the repository: `git clone https://github.com/jblanked/Ghouls.git`
2. Create a new `GhoulsGame` instance (from `src/game.hpp`)
3. Call `GhoulsGame::run()` once per application-loop iteration. It initializes the drawing system and game engine on its first call, reads input, updates, and draws each frame.
4. Stop calling `run()` when `GhoulsGame::isActive()` returns `false`, then free the instance.

No separate drawing initialization, input forwarding, or draw/update call is needed.

Check out the [Flipper Zero's version](https://github.com/jblanked/Ghouls-Flipper) for a complete example of how to set up the game on a specific platform. The code in this repository is designed to be portable and can be adapted to various platforms with minimal changes.