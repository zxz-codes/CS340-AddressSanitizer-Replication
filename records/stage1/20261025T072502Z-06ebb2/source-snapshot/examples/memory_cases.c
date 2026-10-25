/* CS340 educational cases, authored for this replication. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static volatile int global_buffer[8];
static volatile int sink;
__attribute__((noinline)) static void exercise(const char *kind, int index) {
    volatile int stack_buffer[8] = {0};
    int *p = malloc(8 * sizeof(*p));
    if (!p) exit(2);
    for (int i = 0; i < 8; ++i) p[i] = i;
    if (!strcmp(kind, "heap")) sink = p[index];
    else if (!strcmp(kind, "stack")) sink = stack_buffer[index];
    else if (!strcmp(kind, "global")) sink = global_buffer[index];
    else if (!strcmp(kind, "uaf")) { free(p); sink = p[index]; return; }
    else if (!strcmp(kind, "double_free")) { free(p); free(p); return; }
    else if (!strcmp(kind, "fixed")) { sink = p[index < 8 ? index : 7]; free(p); return; }
    else { free(p); exit(2); }
    free(p);
}
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    exercise(argv[1], atoi(argv[2]));
    puts("completed");
    return 0;
}
