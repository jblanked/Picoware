#include "../../internal/system/bluetooth.hpp"
#if ENABLE_CLASSIC != 0
namespace Picoware
{
    void Bluetooth::begin()
    {
        l2cap_init();
        sm_init();
        gap_set_default_link_policy_settings(LM_LINK_POLICY_ENABLE_SNIFF_MODE | LM_LINK_POLICY_ENABLE_ROLE_SWITCH);
        hci_set_master_slave_policy(HCI_ROLE_MASTER);
        hci_set_inquiry_mode(INQUIRY_MODE_RSSI_AND_EIR);

        hci.install();
        hci.begin();
    }
    void Bluetooth::beginBLE()
    {
        l2cap_init();
        gatt_client_init();
        sm_init();
        sm_set_io_capabilities(IO_CAPABILITY_NO_INPUT_NO_OUTPUT);
        gap_set_default_link_policy_settings(LM_LINK_POLICY_ENABLE_SNIFF_MODE | LM_LINK_POLICY_ENABLE_ROLE_SWITCH);
        hci_set_master_slave_policy(HCI_ROLE_MASTER);
        hci_set_inquiry_mode(INQUIRY_MODE_RSSI_AND_EIR);

        hci.setBLEName("Pico BLE Scanner");
        hci.install();
        hci.begin();
    }
    void Bluetooth::beginKeyboardBLE(const char *name)
    {
        KeyboardBLE.begin(name);
        KeyboardBLE.setBattery(100);
    }
    void Bluetooth::beginMouseBLE(const char *name)
    {
        MouseBLE.begin(name);
        MouseBLE.setBattery(100);
    }
    void Bluetooth::keyboardPrint(const char *text)
    {
        KeyboardBLE.print(text);
    }
    void Bluetooth::moveMouse(int x, int y, int wheel)
    {
        MouseBLE.move(x, y, wheel);
    }
    String Bluetooth::scan()
    {
        auto l = hci.scan(BluetoothHCI::any_cod);
        String json = "{\"devices\":[";
        bool first = true;
        for (auto e : l)
        {
            if (!first)
            {
                json += ",";
            }
            json += "\"";
            json += e.name();
            json += "\"";
            first = false;
        }
        json += "]}";
        // reset
        hci.scanFree();
        hci.uninstall();
        sm_deinit();
        l2cap_deinit();
        return json;
    }
    String Bluetooth::scanBLE()
    {
        auto l = hci.scanBLE(BluetoothHCI::any_cod);
        String json = "{\"devices\":[";
        bool first = true;
        for (auto e : l)
        {
            if (!first)
            {
                json += ",";
            }
            json += "\"";
            json += e.name();
            json += "\"";
            first = false;
        }
        json += "]}";
        // reset
        hci.scanFree();
        hci.uninstall();
        sm_deinit();
        l2cap_deinit();
        return json;
    }
    void Bluetooth::stopKeyboardBLE()
    {
        KeyboardBLE.end();
    }
    void Bluetooth::stopMouseBLE()
    {
        MouseBLE.end();
    }
} // namespace Picoware
#endif