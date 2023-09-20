#ifndef PERSON_H
#define PERSON_H

#include <string>

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

    bool neverCalled() {
        return True;
    }
};
#endif
