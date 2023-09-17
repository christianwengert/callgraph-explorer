#include <iostream>
#include "outside.h"


using namespace std;


bool check_prime(int);


int _inline_adder(int a, int b) {
    return a + b;
}


class AddNumber {
public:
    int add(int a, int b);  // adds something
};

int AddNumber::add(int a, int b) { // implementation
    return _inline_adder(a, b);
}



int main() {

  int n;

  cout << "Enter a positive  integer: ";
  cin >> n;

  if (check_prime(n))
    cout << n << " is a prime number.";
  else
    cout << n << " is not a prime number.";

    auto adder = AddNumber();
    cout << adder.add(4, 4) << endl;

    // now calling something from outside
    int result = outside_add(5, 7); // Call the add function

  return 0;
}

bool check_prime(int n) {
  bool is_prime = true;

  // 0 and 1 are not prime numbers
  if (n == 0 || n == 1) {
    is_prime = false;
  }

  for (int i = 2; i <= n / 2; ++i) {
    if (n % i == 0) {
      is_prime = false;
      break;
    }
  }

  return is_prime;
}