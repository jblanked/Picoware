## Development Guide
This is a basic guide that provides instructions for setting up a development environment for the project. Other than setting up the [configuration](Configuration.md), you can follow the steps below to get started:
1. Clone the repository: `git clone https://github.com/jblanked/PicoGTA.git`
2. Create a new `PicoGTA` instance (from `src/game.hpp`)
3. Call `PicoGTA::initDraw()` to initialize the drawing system
4. Call `PicoGTA::updateDraw()` in a loop (for rendering) and call `PicoGTA::updateInput()` when input is received (for handling input)
5. Free resources and clean up when done

Check out [Picoware's version](https://github.com/jblanked/Picoware) for a complete example of how to set up the game on a specific platform. The code in this repository is designed to be portable and can be adapted to various platforms with minimal changes.