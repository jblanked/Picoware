// Original from https://github.com/Bodmer/TFT_eSPI/blob/master/examples/480%20x%20320/Demo_3D_cube/Demo_3D_cube.ino

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"

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

    static const Line3d Lines[12] = {
        // 12 lines to render.
        // Front Face.
        {
            {-50, -50, 50}, {50, -50, 50}},
        {{50, -50, 50}, {50, 50, 50}},
        {{50, 50, 50}, {-50, 50, 50}},
        {{-50, 50, 50}, {-50, -50, 50}},
        // Back Face.
        {
            {-50, -50, -50}, {50, -50, -50}},
        {{50, -50, -50}, {50, 50, -50}},
        {{50, 50, -50}, {-50, 50, -50}},
        {{-50, 50, -50}, {-50, -50, -50}},
        // Edge Lines.
        {
            {-50, -50, 50}, {-50, -50, -50}},
        {{50, -50, 50}, {50, -50, -50}},
        {{-50, 50, 50}, {-50, 50, -50}},
        {{50, 50, 50}, {50, 50, -50}}};

    /***********************************************************************************************************************************/
    void RenderImage(Draw *tft)
    {
        tft->fillScreen(TFT_BLACK); // clear the screen before drawing the new lines.

        Line2d render[12];

        // Process all lines and convert 3D to 2D
        for (uint8_t i = 0; i < linestoRender; i++)
        {
            Line3d vec = Lines[i];
            Line2d *ret = &render[i];

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
                ret->p0.x = rx1;
                ret->p0.y = ry1;
                ret->p1.x = rx2;
                ret->p1.y = ry2;
                uint16_t color = TFT_BLUE; // shows up as teal on VGM
                if (i < 4)
                    color = TFT_RED; // cyan (shows up as white on VGM)
                if (i > 7)
                    color = TFT_DARKGREEN; // shows up as red on VGM
                tft->drawLineCustom(Vector(ret->p0.x, ret->p0.y), Vector(ret->p1.x, ret->p1.y), color);
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
            viewManager->getInputManager()->reset(true);
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

        sleep_ms(14); // Delay to reduce loop rate (reduces flicker caused by aliasing with TFT screen refresh rate)
    }

    void cubeStop(ViewManager *viewManager)
    {
        auto draw = viewManager->getDraw();
        draw->fillScreen(viewManager->getBackgroundColor());
        draw->swap();
    }
} // namespace Cube

static const View cubeView = View("Cube", Cube::cubeRun, Cube::cubeStart, Cube::cubeStop);
