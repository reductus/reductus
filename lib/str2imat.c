/* public domain

jazz:
  LIBZ="-L/data/people/pkienzle/packages/zlib-1.4.4 -lz"
  cc -O2 reflbin.c -o ~/bin/reflbin -lgen -lm $LIBZ

linux, macosx:
  gcc -Wall -O2 reflbin.c -o ~/bin/reflbin -lm -lz

MinGW:
  LIBZ="-L/usr/local/lib -lz"
  gcc -Wall -O2 -I/usr/local/include reflbin.c -o reflbin.exe -lm $LIBZ

Compile with -DDEBUG to show input and output.
*/

#include <ctype.h>
#include <stdio.h>

void str2imat(const char str[], int size, int imat[], int *rows, int *columns)
/*
 * Converts a string of the form ###, ###,###,###;###,###,###
 * to an array of integers, returning the number of rows and columns.
 * There may be any amount of whitespace within and between the digits
 * of the number.
 */
{
  int i = 0;      /* Current character position */
  int nr=0, nc=0; /* Number of rows/columns */
  int number = 0; /* Number being formed */
  int k = 0;      /* Target position for the next number */
  *rows = -1;     /* Fail if *rows < 0 */
  *columns = 1;   /* Make sure columns is initialized */
  while (1) {
    const char c = str[i];
    if (!c) break;
    if (isdigit(c)) {
      number = number*10 + c - '0';
    } else if (c==',') {
      if (k == size) return;
      imat[k++] = number;
      number = 0;
      nc++;
    } else if (c == ';') {
      if (k == size) return;
      imat[k++] = number;
      number = 0;
      nc = 0;
      nr++;
    }
    i++;
  }
  *columns = ++nc;
  *rows = ++nr;
}
