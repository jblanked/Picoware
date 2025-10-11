// Original from https://github.com/Bodmer/TFT_eSPI/blob/master/examples/480%20x%20320/Demo_3D_cube/Demo_3D_cube.ino

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../system/psram.hpp"

namespace Cube
{
    int inc = -2;

    float xx, xy, xz;
    float yx, yy, yz;
    float zx, zy, zz;

    float fact;

    int Xan, Yan;

    int Xoff;
    int Yoff;
    int Zoff;

    struct Point3d
    {
        int x;
        int y;
        int z;
    };

    struct Point2d
    {
        int x;
        int y;
    };

    static const uint8_t linestoRender = 12; // lines to render.

    struct Line3d
    {
        Point3d p0;
        Point3d p1;
    };

    struct Line2d
    {
        Point2d p0;
        Point2d p1;
    };

    static uint32_t psram_lines_addr = 0;
    static uint32_t psram_render_addr = 0;
    static bool psram_data_valid = false;

    void initializePSRAM()
    {
        psram_data_valid = false;

        // Initialize PSRAM hardware if needed (the constructor does this)
        PSRAM psram;

        if (psram_lines_addr == 0 && PSRAM::isReady())
        {
            // Define the cube lines as uint32_t array (coordinates are positive/negative, but we'll cast)
            uint32_t lines_data[72] = {
                // 12 lines to render (each line has 6 values: p0.x,y,z + p1.x,y,z)
                // Note: negative values are cast to uint32_t (will be cast back when read)
                // Front Face.
                static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), // Line 0
                static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(50),   // Line 1
                static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50),   // Line 2
                static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), // Line 3
                // Back Face.
                static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), // Line 4
                static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50),   // Line 5
                static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50),   // Line 6
                static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), // Line 7
                // Edge Lines.
                static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50), // Line 8
                static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(-50),   // Line 9
                static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50),   // Line 10
                static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(50), static_cast<uint32_t>(-50)      // Line 11
            };

            // Calculate the size we need: 72 uint32_t values
            uint32_t size_needed = 72 * sizeof(uint32_t);

            // Allocate PSRAM for cube lines
            psram_lines_addr = PSRAM::malloc(size_needed);
            if (psram_lines_addr != 0)
            {
                // Copy the data to PSRAM using the new uint32 array method
                PSRAM::writeUint32Array(psram_lines_addr, lines_data, 72);
                psram_data_valid = true;
            }
        }

        // Allocate PSRAM for render array
        if (psram_render_addr == 0 && PSRAM::isReady())
        {
            uint32_t render_size = sizeof(Line2d) * linestoRender;
            psram_render_addr = PSRAM::malloc(render_size);
        }
    }

    Line3d getLine(uint8_t index)
    {
        Line3d line = {{0, 0, 0}, {0, 0, 0}};

        if (psram_data_valid && psram_lines_addr != 0 && index < linestoRender)
        {
            // Read the line data using the new uint32 array method
            uint32_t line_data[6];
            uint32_t start_index = index * 6; // Each line has 6 int values

            PSRAM::readUint32Array(psram_lines_addr + (start_index * sizeof(uint32_t)), line_data, 6);

            // Cast back to signed integers
            line.p0.x = static_cast<int>(line_data[0]);
            line.p0.y = static_cast<int>(line_data[1]);
            line.p0.z = static_cast<int>(line_data[2]);
            line.p1.x = static_cast<int>(line_data[3]);
            line.p1.y = static_cast<int>(line_data[4]);
            line.p1.z = static_cast<int>(line_data[5]);
        }

        return line;
    }

    /***********************************************************************************************************************************/
    void RenderImage(Draw *tft)
    {
        tft->fillScreen(TFT_BLACK); // clear the screen before drawing the new lines.

        // Process all lines and convert 3D to 2D
        for (uint8_t i = 0; i < linestoRender; i++)
        {
            // Get line data from PSRAM
            Line3d vec = getLine(i);

            float zvt1;
            int xv1, yv1, zv1;
            float zvt2;
            int xv2, yv2, zv2;
            int rx1, ry1;
            int rx2, ry2;
            int x1 = vec.p0.x;
            int y1 = vec.p0.y;
            int z1 = vec.p0.z;
            int x2 = vec.p1.x;
            int y2 = vec.p1.y;
            int z2 = vec.p1.z;
            int Ok = 0; // defaults to not OK

            xv1 = (x1 * xx) + (y1 * xy) + (z1 * xz);
            yv1 = (x1 * yx) + (y1 * yy) + (z1 * yz);
            zv1 = (x1 * zx) + (y1 * zy) + (z1 * zz);

            zvt1 = zv1 - Zoff;

            if (zvt1 < -5)
            {
                rx1 = 256 * (xv1 / zvt1) + Xoff;
                ry1 = 256 * (yv1 / zvt1) + Yoff;
                Ok = 1; // ok we are alright for point 1.
            }

            xv2 = (x2 * xx) + (y2 * xy) + (z2 * xz);
            yv2 = (x2 * yx) + (y2 * yy) + (z2 * yz);
            zv2 = (x2 * zx) + (y2 * zy) + (z2 * zz);

            zvt2 = zv2 - Zoff;

            if (zvt2 < -5)
            {
                rx2 = 256 * (xv2 / zvt2) + Xoff;
                ry2 = 256 * (yv2 / zvt2) + Yoff;
            }
            else
            {
                Ok = 0;
            }

            if (Ok == 1)
            {
                // Store render data in PSRAM if available, otherwise just draw directly
                if (psram_render_addr != 0)
                {
                    Line2d render_line;
                    render_line.p0.x = rx1;
                    render_line.p0.y = ry1;
                    render_line.p1.x = rx2;
                    render_line.p1.y = ry2;
                    PSRAM::write(psram_render_addr + (i * sizeof(Line2d)), &render_line, sizeof(Line2d));
                }

                uint16_t color = TFT_BLUE; // shows up as teal on VGM
                if (i < 4)
                    color = TFT_RED; // cyan (shows up as white on VGM)
                if (i > 7)
                    color = TFT_DARKGREEN; // shows up as red on VGM
                tft->drawLineCustom(Vector(rx1, ry1), Vector(rx2, ry2), color);
            }
        }

        tft->swap(); // swap the buffers to show the new lines.
    }

    /***********************************************************************************************************************************/
    // Sets the global vars for the 3d transform. Any points sent through "process" will be transformed using these figures.
    // only needs to be called if Xan or Yan are changed.
    void SetVars(void)
    {
        float Xan2, Yan2, Zan2;
        float s1, s2, s3, c1, c2, c3;

        Xan2 = Xan / fact; // convert degrees to radians.
        Yan2 = Yan / fact;

        // Zan is assumed to be zero

        s1 = sin(Yan2);
        s2 = sin(Xan2);

        c1 = cos(Yan2);
        c2 = cos(Xan2);

        xx = c1;
        xy = 0;
        xz = -s1;

        yx = (s1 * s2);
        yy = c2;
        yz = (c1 * s2);

        zx = (s1 * c2);
        zy = -s2;
        zz = (c1 * c2);
    }

    bool cubeStart(ViewManager *viewManager)
    {
        auto draw = viewManager->getDraw();

        draw->fillScreen(TFT_BLACK);
        draw->swap();

        // Initialize PSRAM storage for cube data
        initializePSRAM();

        fact = 180 / 3.14159259; // conversion from degrees to radians.

        Xoff = 240; // Position the centre of the 3d conversion space into the centre of the TFT screen.
        Yoff = 160;
        Zoff = 550;  // Z offset in 3D space (smaller = closer and bigger rendering)
        return true; // return true to indicate the start was successful.
    }

    void cubeRun(ViewManager *viewManager)
    {
        auto input = viewManager->getInputManager()->getLastButton();
        if (input == BUTTON_LEFT || input == BUTTON_BACK)
        {
            viewManager->back();
            viewManager->getInputManager()->reset();
            return;
        }

        // Rotate around x and y axes in 1 degree increments
        Xan++;
        Yan++;

        Yan = Yan % 360;
        Xan = Xan % 360; // prevents overflow.

        SetVars(); // sets up the global vars to do the 3D conversion.

        // Zoom in and out on Z axis within limits
        // the cube intersects with the screen for values < 160
        Zoff += inc;
        if (Zoff > 500)
            inc = -1; // Switch to zoom in
        else if (Zoff < 160)
            inc = 1; // Switch to zoom out

        RenderImage(viewManager->getDraw()); // go draw it!
    }

    void cubeStop(ViewManager *viewManager)
    {
        auto draw = viewManager->getDraw();
        draw->fillScreen(viewManager->getBackgroundColor());
        draw->swap();

        // Clean up PSRAM allocations
        if (psram_lines_addr != 0)
        {
            PSRAM::free(psram_lines_addr);
            psram_lines_addr = 0;
        }
        if (psram_render_addr != 0)
        {
            PSRAM::free(psram_render_addr);
            psram_render_addr = 0;
        }
    }
} // namespace Cube

static const View cubeView = View("Cube", Cube::cubeRun, Cube::cubeStart, Cube::cubeStop);
