#pragma once
#include <Arduino.h>
namespace Picoware
{
    class ViewManager;

    class View
    {
    public:
        explicit View(const char *name, void (*run)(ViewManager *), void (*start)(ViewManager *) = nullptr, void (*stop)(ViewManager *) = nullptr) noexcept
            : name(name), _run(run), _start(start), _stop(stop)
        {
        }

        void start(ViewManager *viewManager) const noexcept
        {
            if (_start != nullptr)
            {
                _start(viewManager);
            }
        }

        void stop(ViewManager *viewManager) const noexcept
        {
            if (_stop)
            {
                _stop(viewManager);
            }
        }

        void run(ViewManager *viewManager) const noexcept
        {
            if (_run)
            {
                _run(viewManager);
            }
        }

        const char *name;

    private:
        void (*_run)(ViewManager *);
        void (*_start)(ViewManager *);
        void (*_stop)(ViewManager *);
    };
}