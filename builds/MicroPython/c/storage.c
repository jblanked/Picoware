int main()
{
    lcd_fill(0x0000);
    int file_size = storage_file_size("c-test.txt");
    if (file_size > 0)
    {
        char *buffer = (char *)malloc(file_size);
        if (!buffer)
            return 2;
        int count = storage_file_read("c-test.txt", buffer, file_size);
        if (count == file_size)
        {
            lcd_text(0, 0, buffer, 0xFFFF);
        }
        else
        {
            lcd_text(0, 0, "Failed to read entire file", 0xFFFF);
        }
    }
    else
    {
        int write_success = storage_file_write("c-test.txt", "Hello, World!", 13);
        if (write_success)
        {
            lcd_text(0, 0, "File created and written successfully.", 0xFFFF);
        }
        else
        {
            lcd_text(0, 0, "Failed to create and write the file", 0xFFFF);
        }
    }
    lcd_swap();
    return 0;
}