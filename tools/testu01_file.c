/*
 * Run TestU01 batteries/tests on a finite file of random bits.
 *
 * The file is a raw bitstream, packed MSB-first (numpy.packbits order).
 * Every 4 bytes are read big-endian as one 32-bit output, so the first bit of
 * the stream is the most significant bit of the first word -- the bits that
 * TestU01 looks at first.
 *
 * The file is NEVER rewound: if a test asks for more words than the file holds,
 * the program prints EXHAUSTED and exits with status 3. (Wrapping around would
 * replay data and produce false failures, a classic mistake with file input.)
 *
 * Usage:
 *   testu01_file smallcrush <file>
 *   testu01_file rabbit     <file> [nbits]     (default: all bits in file)
 *   testu01_file alphabit   <file> [nbits]
 *   testu01_file lincomp    <file>             (BigCrush's two LinearComp tests)
 *
 * The whole file is loaded into memory (Windows builds: files up to 2 GB).
 *
 * Machine-readable lines on stdout:
 *   RESULT<TAB><test name><TAB><p-value>
 *   WORDS_USED<TAB><count>
 *
 * Build (after tools/build_testu01_mingw.sh, or a normal TestU01 install):
 *   gcc -O2 -std=gnu99 -I<inc> tools/testu01_file.c <lib>/libtestu01.a -lm -o testu01_file
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "unif01.h"
#include "bbattery.h"
#include "scomp.h"
#include "swrite.h"
#include "gofw.h"

static uint32_t *words;
static long n_words, pos;

static unsigned int next_word(void)
{
   if (pos >= n_words) {
      fflush(stdout);
      printf("\nEXHAUSTED\t%ld\n", n_words);
      fprintf(stderr, "testu01_file: file exhausted after %ld 32-bit words; "
              "generate more data for this test.\n", n_words);
      exit(3);
   }
   return words[pos++];
}

static void load(const char *path)
{
   FILE *f = fopen(path, "rb");
   if (!f) { perror(path); exit(2); }
   fseek(f, 0, SEEK_END);
   long bytes = ftell(f);
   fseek(f, 0, SEEK_SET);
   n_words = bytes / 4;
   unsigned char *buf = malloc((size_t)n_words * 4);
   words = malloc((size_t)n_words * sizeof(uint32_t));
   if (!buf || !words) { fprintf(stderr, "out of memory\n"); exit(2); }
   if (fread(buf, 4, (size_t)n_words, f) != (size_t)n_words) { perror("fread"); exit(2); }
   fclose(f);
   for (long i = 0; i < n_words; i++)
      words[i] = ((uint32_t)buf[4*i] << 24) | ((uint32_t)buf[4*i+1] << 16) |
                 ((uint32_t)buf[4*i+2] << 8) | (uint32_t)buf[4*i+3];
   free(buf);
}

static void print_battery(void)
{
   for (int i = 0; i < bbattery_NTests; i++)
      if (bbattery_TestNames[i])
         printf("RESULT\t%s\t%.6g\n", bbattery_TestNames[i], bbattery_pVal[i]);
}

static void lincomp(unif01_Gen *gen, long n, int r)
{
   char name[64];
   scomp_Res *res = scomp_CreateRes();
   scomp_LinearComp(gen, res, 1, n, r, 1);
   snprintf(name, sizeof name, "LinearComp r=%d s=1 n=%ld (jump count)", r, n);
   printf("RESULT\t%s\t%.6g\n", name, res->JumpNum->pVal2[gofw_Mean]);
   snprintf(name, sizeof name, "LinearComp r=%d s=1 n=%ld (jump size)", r, n);
   printf("RESULT\t%s\t%.6g\n", name, res->JumpSize->pVal2[gofw_Mean]);
   scomp_DeleteRes(res);
}

int main(int argc, char **argv)
{
   if (argc < 3) {
      fprintf(stderr, "usage: %s smallcrush|rabbit|alphabit|lincomp <file> [nbits]\n", argv[0]);
      return 2;
   }
   const char *mode = argv[1];
   load(argv[2]);
   double nbits = argc > 3 ? atof(argv[3]) : 32.0 * n_words;
   unif01_Gen *gen = unif01_CreateExternGenBits((char *)argv[2], next_word);

   if (!strcmp(mode, "smallcrush")) {
      bbattery_SmallCrush(gen);
      print_battery();
   } else if (!strcmp(mode, "rabbit")) {
      bbattery_Rabbit(gen, nbits);
      print_battery();
   } else if (!strcmp(mode, "alphabit")) {
      bbattery_Alphabit(gen, nbits, 0, 32);
      print_battery();
   } else if (!strcmp(mode, "lincomp")) {
      swrite_Basic = FALSE;
      lincomp(gen, 400020, 0);    /* parameters used in BigCrush */
      lincomp(gen, 400020, 29);
   } else {
      fprintf(stderr, "unknown mode %s\n", mode);
      return 2;
   }
   printf("WORDS_USED\t%ld\n", pos);
   unif01_DeleteExternGenBits(gen);
   return 0;
}
