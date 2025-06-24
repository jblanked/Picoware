#pragma once
#include <Arduino.h>
namespace Picoware
{
    class ViewManager;

    class View
    {
    public:
        explicit View(const char *name, void (*run)(ViewManager *), bool (*start)(ViewManager *) = nullptr, void (*stop)(ViewManager *) = nullptr) noexcept
            : name(name), _run(run), _start(start), _stop(stop)
        {
        }

        bool start(ViewManager *viewManager) const noexcept
        {
            if (_start != nullptr)
            {
                return _start(viewManager);
            }
            return false;
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
        bool (*_start)(ViewManager *);
        void (*_stop)(ViewManager *);
    };
}