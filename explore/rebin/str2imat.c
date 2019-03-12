/* This program is public domain */

#include <ctype.h>
#include <stdio.h>

void str2imat(const char str[], int size, int imat[], int *rows, int *columns)
/*
 * Converts a string of the form ###, ###,#,####;###,###,###,##
 * to an array of integers, returning the number of rows and columns.
 * There may be any amount of whitespace within and between the digits
 * of the number.
 *
 * Note that only the first 'size' numbers are preserved, so size should be the
 * number of values in imat, or 0 if you just want to count the number of rows/
 * columns in the block.
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
      if (k < size) imat[k++] = number;
      number = 0;
      nc++;
    } else if (c == ';') {
      if (k < size) imat[k++] = number;
      number = 0;
      nc = 0;
      nr++;
    }
    i++;
  }
  /* The sequence should have ended with a number, so save it */
  if (k < size) imat[k++] = number;
  *columns = ++nc;
  *rows = ++nr;
}

