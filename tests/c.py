from picoware.system.c import C

c = C()

result = c.run("""// C test
int main()
{
    int i = 0;
    for (int j = 0; j < 10; j++)
    {
        i += j;
        i++;
    }
    int x = 5;
    while(i > 50)
    {
        x += i;
        i--;
    }
    return x;
}
""")
print(result)

new_res = c.exec("test.c") # on root of SD card
print(new_res)

del c
c = None
