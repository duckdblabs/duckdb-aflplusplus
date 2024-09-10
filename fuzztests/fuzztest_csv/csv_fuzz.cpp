#include <iostream>
#include <string>

void fuzz_filereaders(std::string filereadFunction);

int main()
{
    std::string filereadFunction = "read_csv";
    fuzz_filereaders(filereadFunction);
    return 0;
}
