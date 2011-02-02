OS = $(shell uname -s)
CFLAGS=-O3  -Wall -I/usr/local/include
ifeq ($(OS), IRIX64) 
#  DEFS=-DNEED_BASENAME
  LDFLAGS=-L/usr/freeware/lib32 -lgen
  CFLAGS=-O2
endif
LIBS=-L/usr/local/lib -lz -lm
all: reflbin

reflbin: reflbin.c
	$(CC) $(CFLAGS) $(DEFS) reflbin.c -o reflbin $(LDFLAGS) $(LIBS)

clean: ; rm reflbin
