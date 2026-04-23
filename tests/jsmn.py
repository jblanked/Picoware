from jsmn import value, array_value
import ujson
from utime import ticks_ms

_json = '{"test": 1235, "another": "hello"}'
_json_arr = '{"test": [1235, 567, 689], "another": ["hello", "bye", "lol"]}'

def test():
    now = ticks_ms()

    print(value("test", _json))
    print(value("another", _json))

    print(array_value("test", 2, _json_arr))
    print(array_value("another", 1, _json_arr))
    
    return ticks_ms() - now

print(f"\nJSMN test done in {test()} milliseconds\n")

def test2():
    now = ticks_ms()
    
    _dict = ujson.loads(_json)
    print(_dict["test"])
    print(_dict["another"])
    
    _dict_array = ujson.loads(_json_arr)
    print(_dict_array["test"][2])
    print(_dict_array["another"][1])
    return ticks_ms() - now

print(f"\nUJSON test done in {test2()} milliseconds\n")
