#ifndef PERSON_H
#define PERSON_H
struct Person {
    // Public member variables
    std::string name;
    int age;

    // Constructor
    Person(const std::string& n, int a) {
        name = n;
        age = a;
    }

    void addAge(int yearsToAdd) {
        age += yearsToAdd;
    }
};
#endif
