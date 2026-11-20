## Development Guide
Set up the [configuration](Configuration.md), including the required input macros, then:
1. Clone the repository: `git clone https://github.com/jblanked/PicoGTA.git`
2. Create a `PicoGTA` instance (from `src/game.hpp`)
3. Call `PicoGTA::run()` once per application-loop iteration. It initializes drawing and starts the engine with the player and levels on its first call, then reads input, updates, and renders each frame.
4. Stop calling `run()` when `PicoGTA::isActive()` returns `false`, then free the instance.

No separate drawing initialization, input forwarding, or game update call is needed.

Check out [Picoware's version](https://github.com/jblanked/Picoware) for a complete example of how to set up the game on a specific platform. The code in this repository is designed to be portable and can be adapted to various platforms with minimal changes.